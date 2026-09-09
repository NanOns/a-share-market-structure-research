"""Build the local, reconstructed M8/M9 preview dataset into DuckDB.

This is intentionally a preview builder: it consumes only checked-in/local
parquet artifacts, never touches a TDX source directory, and binds the new
analysis snapshot to the current publication without replacing its head.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.highs import calculate_high_daily, insert_high_rows
from workbench_analysis.member_state import (
    build_membership_changes,
    build_sector_member_state_daily,
    insert_membership_change_rows,
    insert_member_state_rows,
)
from workbench_analysis.representative_state import build_representative_state_daily, insert_representative_rows
from workbench_analysis.sector_cycle import build_sector_cycle_daily, insert_sector_cycle_rows
from workbench_analysis.strength import insert_strength_rows
from workbench_analysis.structures import (
    build_historical_structure_rows,
    build_structure_summary,
    insert_historical_structure_rows,
    insert_structure_summary_rows,
)
from workbench_analysis.technical import calculate_technical_daily, insert_technical_rows
from workbench_ops.backup import BackupService


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
MEMBERSHIP_PATH = ROOT / "data/sectors/sector_membership_daily.parquet"
SHADOW_ROOT = ROOT / "reports/shadow/v2_runs/20260908"
PREVIEW_PREFIX = "m8-m9-local-reconstructed-preview-v2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return hashlib.sha256(b"EMPTY").hexdigest()
    normalized = frame.copy()
    for column in normalized.columns:
        if pd.api.types.is_datetime64_any_dtype(normalized[column]) or normalized[column].dtype == object:
            normalized[column] = normalized[column].map(
                lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                if isinstance(value, (dict, list, tuple, set))
                else str(value) if value is not None else ""
            )
    payload = normalized.sort_index(axis=1).sort_values(list(normalized.columns), kind="mergesort").to_json(
        orient="records", date_format="iso", force_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_file(name: str) -> Path:
    matches = list(SHADOW_ROOT.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"SHADOW_SOURCE_EXPECTED_ONE:{name}:{len(matches)}")
    return matches[0]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, list[date], dict[str, str]]:
    membership = pd.read_parquet(MEMBERSHIP_PATH)
    membership["trade_date"] = pd.to_datetime(membership.pop("date"), errors="raise").dt.date
    dates = sorted(pd.unique(membership["trade_date"]))
    if not dates or len(dates) != 3:
        raise RuntimeError(f"PREVIEW_DATES_EXPECTED_THREE:{dates}")
    cutoff = max(dates)
    lower = cutoff - timedelta(days=300)

    con = duckdb.connect()
    try:
        raw = con.execute(
            """
            select security_id, date, raw_close, adj_close, raw_amount, raw_volume,
                   universe_status, data_quality_flag, is_synthetic_fill
              from read_parquet(?)
             where date between ? and ?
            """,
            [str(NORMALIZED_PATH), lower, cutoff],
        ).fetch_df()
    finally:
        con.close()
    if raw.empty:
        raise RuntimeError("NORMALIZED_PREVIEW_INPUT_EMPTY")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.date
    raw = raw.sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)
    raw["quote_prev_close"] = raw.groupby("security_id", sort=False)["raw_close"].shift(1)

    membership = membership[membership["trade_date"].isin(dates)].copy()
    membership["security_id"] = membership["security_id"].astype(str)
    membership["sector_id"] = membership["sector_id"].astype(str)
    if membership.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise RuntimeError("MEMBERSHIP_DUPLICATE_PREVIEW_INPUT")
    hashes = {
        "normalized": sha256_file(NORMALIZED_PATH),
        "membership": sha256_file(MEMBERSHIP_PATH),
    }
    return raw, membership, dates, hashes


def build_frames(raw: pd.DataFrame, membership: pd.DataFrame, dates: list[date]) -> dict[str, pd.DataFrame]:
    cutoff = max(dates)
    # Calculate rolling fields over the full local history first, then keep the
    # three published dates.  Calculating only on the preview dates makes every
    # 20/60-day field appear empty even though the local parquet contains the
    # required lookback window.
    technical = calculate_technical_daily(
        raw[["security_id", "date", "raw_close", "adj_close", "raw_amount", "raw_volume", "quote_prev_close", "universe_status", "data_quality_flag", "is_synthetic_fill"]],
        cutoff=cutoff,
    )
    technical = technical[technical["date"].isin(dates)].copy()
    if technical.empty:
        raise RuntimeError("TECHNICAL_PREVIEW_CALCULATION_EMPTY")
    for width in (5, 10, 20, 60):
        technical[f"ret{width}"] = pd.to_numeric(technical[f"ret{width}"], errors="coerce")
        technical[f"rs{width}"] = pd.NA
        technical[f"rps{width}"] = pd.NA
        technical[f"rps_valid_universe_count{width}"] = 0
        technical[f"ma{width}"] = pd.to_numeric(technical[f"ma{width}"], errors="coerce")
        technical[f"amount_ma{width}"] = pd.to_numeric(technical[f"amount_ma{width}"], errors="coerce")
    for trade_date, indexes in technical.groupby("date", sort=False).groups.items():
        subset = technical.loc[list(indexes)]
        eligible = subset.get("universe_status", pd.Series(True, index=subset.index)).eq("IN_NORMAL_UNIVERSE")
        for width in (5, 10, 20, 60):
            values = pd.to_numeric(subset[f"ret{width}"], errors="coerce")
            valid = values[eligible & values.notna()]
            technical.loc[list(indexes), f"rps{width}"] = pd.NA
            technical.loc[list(indexes), f"rps_valid_universe_count{width}"] = int(valid.notna().sum())
            if len(valid) >= 100:
                technical.loc[valid.index, f"rs{width}"] = valid - valid.median()
                technical.loc[valid.index, f"rps{width}"] = valid.rank(method="average") / len(valid)
    technical["validity"] = technical[["ma5", "ma10", "ma20", "ma60"]].notna().all(axis=1).map({True: "VALID", False: "PARTIAL"})
    technical["quote_ret1"] = pd.to_numeric(technical["raw_close"], errors="coerce") / pd.to_numeric(technical["quote_prev_close"], errors="coerce") - 1
    technical["quality_codes"] = technical.apply(
        lambda row: [] if row["validity"] == "VALID" else ["INSUFFICIENT_HISTORY"], axis=1
    )
    technical["basis_json"] = technical.apply(
        lambda row: {"contract_id": "TECHNICAL_HISTORY_V2_1_PREVIEW", "price_basis": "TDX_NATIVE_QFQ", "source": "LOCAL_FACTORS_DAILY"},
        axis=1,
    )
    technical["strength_quality_codes"] = technical.apply(
        lambda row: [f"INSUFFICIENT_RPS_UNIVERSE_{width}" for width in (5, 10, 20, 60) if int(row.get(f"rps_valid_universe_count{width}") or 0) < 100],
        axis=1,
    )
    technical["strength_basis_json"] = technical.apply(
        lambda row: {"contract_id": "TECHNICAL_HISTORY_V2_1_PREVIEW", "price_basis": "TDX_NATIVE_QFQ", "rps_min_universe": 100, "source": "LOCAL_FACTORS_DAILY"},
        axis=1,
    )
    technical["trade_date"] = technical["date"]

    high_all = calculate_high_daily(raw[["security_id", "date", "adj_close"]], cutoff=cutoff)
    high = high_all[high_all["date"].isin(dates)].copy()
    high["trade_date"] = high["date"]

    steady = pd.read_parquet(source_file("STEADY_TREND_V2_SHADOW.parquet"))
    pullback = pd.read_parquet(source_file("STRONG_PULLBACK_V2_SHADOW.parquet"))
    breakout = pd.read_parquet(source_file("BREAKOUT_PREP_V2_SHADOW.parquet"))
    early = pd.read_parquet(source_file("EARLY_MOVER_V2_SHADOW.parquet"))
    leader = pd.read_parquet(source_file("SECTOR_LEADER_V2_SHADOW.parquet"))
    structures_input = steady.copy()
    for extra, columns in (
        (pullback, ["security_id", "date", "segment_status", "depth_status", "volume_status", "v2_pullback_volume_confirmed"]),
        (breakout, ["security_id", "date", "range_status", "vol_status", "v2_breakout_structure_hit"]),
        (early, ["security_id", "date", "v2_sector_context_class", "trend_support", "position_support"]),
        (leader, ["security_id", "date", "v2_primary_sector_semantic", "quality_dimension_strong_support_count", "member_rs20_pct", "sector_rs20_pct"]),
    ):
        extra = extra.copy()
        extra["date"] = pd.to_datetime(extra["date"], errors="raise").dt.date
        structures_input = structures_input.merge(extra[columns], on=["security_id", "date"], how="left")
    structures_input["date"] = pd.to_datetime(structures_input["date"], errors="raise").dt.date
    structures_input = structures_input.rename(
        columns={
            "date": "trade_date",
            "recent_range_10": "range_recent",
            "prior_range_10": "range_prior",
            "range_contraction_ratio": "range_ratio",
            "recent_realized_vol_10": "volume_recent",
            "prior_realized_vol_10": "volume_prior",
            "realized_vol_contraction_ratio": "volume_ratio",
            "days_since_peak_20": "days_since_peak",
            "current_drawdown_from_peak_20": "drawdown",
            "advance_amount_mean": "advance_mean",
            "pullback_amount_mean": "pullback_mean",
            "pullback_amount_ratio": "pullback_volume_ratio",
            "v1_primary_sector_type": "sector_type",
        }
    )
    structures_input["sector_type"] = structures_input.get("sector_type", pd.Series("INDUSTRY", index=structures_input.index)).fillna("INDUSTRY")
    structures_input["has_economic_sector"] = True
    structures_input["economic_sector_stabilizing"] = False
    structures_input["price_style_only"] = False
    structures_input["unknown_sector_only"] = False
    structures_input = structures_input[structures_input["trade_date"].isin(dates)].copy()
    structures = build_historical_structure_rows(structures_input, cutoff=cutoff)
    summary = build_structure_summary(structures)

    member_states = build_sector_member_state_daily(
        technical[["security_id", "trade_date", "ret20", "rs20", "rps20"]],
        membership[["sector_id", "sector_name", "sector_type", "trade_date", "security_id"]],
        structures=structures,
        highs=high,
        cutoff=cutoff,
    )
    changes = build_membership_changes(member_states)
    representatives = build_representative_state_daily(member_states, cutoff=cutoff)
    sector_cycle = build_sector_cycle_daily(
        technical[["security_id", "trade_date", "quote_ret1", "ret5", "ret20", "rs5", "rs20", "raw_amount", "ma20"]],
        membership[["sector_id", "sector_name", "sector_type", "sector_role", "trade_date", "security_id"]],
        cutoff=cutoff,
    )
    return {
        "technical": technical,
        "strength": technical,
        "high": high,
        "structure": structures,
        "summary": summary,
        "member_state": member_states,
        "membership_changes": changes,
        "representative": representatives,
        "sector_cycle": sector_cycle,
    }


def insert_preview(frames: dict[str, pd.DataFrame], dates: list[date], input_hashes: dict[str, str]) -> dict[str, object]:
    cutoff = max(dates)
    snapshot_seed = "|".join([PREVIEW_PREFIX, str(cutoff), *[str(item) for item in dates], *input_hashes.values()])
    snapshot_id = f"{PREVIEW_PREFIX}-{hashlib.sha256(snapshot_seed.encode()).hexdigest()[:16]}"
    contracts = {
        "technical": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "strength": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "high": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "structure": "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED",
        "summary": "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED",
        "member_state": "SECTOR_MEMBER_STATE_V1_0",
        "membership_changes": "SECTOR_MEMBER_STATE_V1_0",
        "representative": "SECTOR_REPRESENTATIVE_STATE_V1_0",
        "sector_cycle": "SECTOR_CYCLE_V1_0_DAILY_VECTOR",
    }
    input_hash = hashlib.sha256(json.dumps(input_hashes, sort_keys=True).encode()).hexdigest()
    manifest_hash = hashlib.sha256(json.dumps({key: frame_hash(value) for key, value in frames.items()}, sort_keys=True).encode()).hexdigest()
    backup = BackupService(ROOT, DB_PATH).create_history_backup(maintenance_window=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        existing = con.execute("select status from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone()
        if existing:
            return {"status": "ALREADY_BUILT", "snapshot_id": snapshot_id, "backup_id": backup["backup_id"]}
        publication = con.execute(
            "select h.publication_id from publication_heads h join publications p using(publication_id) where p.status='SUCCESS' order by h.trade_date desc limit 1"
        ).fetchone()
        if not publication:
            raise RuntimeError("CURRENT_PUBLICATION_HEAD_MISSING")
        publication_id = publication[0]
        now = datetime.now(timezone.utc)
        con.execute("begin transaction")
        con.execute(
            "insert into analysis_snapshots values (?,?,?,?,?,?,?,?)",
            [snapshot_id, cutoff, min(dates), "CN_A_LISTED_V2", input_hash, manifest_hash, "SUCCESS", now],
        )
        writer = {
            "technical": insert_technical_rows,
            "strength": insert_strength_rows,
            "high": insert_high_rows,
            "structure": insert_historical_structure_rows,
            "summary": insert_structure_summary_rows,
            "member_state": insert_member_state_rows,
            "membership_changes": insert_membership_change_rows,
            "representative": insert_representative_rows,
            "sector_cycle": insert_sector_cycle_rows,
        }
        counts: dict[str, int] = {}
        for domain, frame in frames.items():
            slice_id = f"{snapshot_id}-{domain}"
            logical_hash = frame_hash(frame)
            basis = {
                "history_basis": "RECONSTRUCTED",
                "source": "LOCAL_PARQUET_ONLY",
                "tdx_source_modified": False,
                "input_artifacts": input_hashes,
                "preview_window": [str(min(dates)), str(cutoff)],
                "domain": domain,
            }
            con.execute(
                "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, domain, cutoff, contracts[domain], input_hash, manifest_hash, json.dumps(basis, ensure_ascii=False, sort_keys=True), len(frame), logical_hash, "DUCKDB", None, now],
            )
            counts[domain] = writer[domain](con, slice_id, frame)
            con.execute(
                "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
                [slice_id, "LOCAL_NORMALIZED", None, "TDX_NATIVE_QFQ", cutoff, now, 1.0, json.dumps({"preview": True, "history_basis": "RECONSTRUCTED"})],
            )
            for trade_date in sorted(pd.unique(frame["trade_date"])):
                con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, domain, trade_date, slice_id])
        # One publication exposes one active local reconstructed binding.  A
        # rebuilt preview replaces that binding atomically while retaining the
        # previous snapshot rows for audit/rollback.
        con.execute(
            "delete from publication_analysis_snapshots where publication_id=? and domain=?",
            [publication_id, "LOCAL_RECONSTRUCTED"],
        )
        con.execute(
            "insert into publication_analysis_snapshots values (?,?,?,?)",
            [publication_id, "LOCAL_RECONSTRUCTED", snapshot_id, now],
        )
        con.execute("commit")
        return {
            "status": "BUILT",
            "snapshot_id": snapshot_id,
            "publication_id": publication_id,
            "cutoff_date": str(cutoff),
            "query_start": str(min(dates)),
            "counts": counts,
            "backup_id": backup["backup_id"],
            "publication_heads_changed": False,
            "history_basis": "RECONSTRUCTED",
        }
    except Exception:
        try:
            con.execute("rollback")
        except Exception:
            pass
        raise
    finally:
        con.close()


def main() -> None:
    raw, membership, dates, hashes = load_inputs()
    frames = build_frames(raw, membership, dates)
    result = insert_preview(frames, dates, hashes)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

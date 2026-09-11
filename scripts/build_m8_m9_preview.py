"""Build the local, reconstructed M8/M9 preview dataset into DuckDB.

This is intentionally a preview builder: it consumes only checked-in/local
parquet artifacts, never touches a TDX source directory, and binds the new
analysis snapshot to the current publication without replacing its head.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.highs import calculate_high_daily, insert_high_rows
from workbench_analysis.coverage import build_historical_coverage, insert_coverage_rows
from workbench_analysis.history_adapter import build_sector_base, insert_sector_base_rows
from workbench_analysis.hierarchy import CONTRACT_VERSION as HIERARCHY_CONTRACT, ensure_hierarchy
from workbench_analysis.member_state import (
    CONTRACT_VERSION as MEMBER_STATE_CONTRACT,
    build_membership_changes,
    build_sector_member_state_daily,
    insert_membership_change_rows,
    insert_member_state_rows,
)
from workbench_analysis.representative_state import build_representative_state_daily, insert_representative_rows
from workbench_analysis.sector_cycle import CONTRACT_VERSION as SECTOR_CYCLE_CONTRACT, build_sector_cycle_daily, insert_sector_cycle_rows
from workbench_analysis.sector_amount import CONTRACT_VERSION as SECTOR_AMOUNT_CONTRACT, RECONSTRUCTED, build_sector_amount_daily
from workbench_analysis.strength import insert_strength_rows
from workbench_service.semantic import (
    CONTRACT_ID as SEMANTIC_CONTRACT_ID,
    build_semantic_version_rows,
    insert_semantic_version_rows,
    resolve_semantic_records,
)
from workbench_analysis.structures import (
    build_historical_structure_rows,
    build_structure_summary,
    insert_historical_structure_rows,
    insert_structure_summary_rows,
)
from workbench_analysis.technical import calculate_technical_daily, insert_technical_rows
from workbench_ops.backup import BackupService


DB_PATH = ROOT / "data/database/market_research.duckdb"
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
MEMBERSHIP_PATH = ROOT / "data/sectors/sector_membership_daily.parquet"
SHADOW_ROOT = ROOT / "reports/shadow/v2_runs/20260908"
PREVIEW_PREFIX = "m8-m9-local-reconstructed-preview-v2"
PREVIEW_ARTIFACT_VERSION = "M8_M9_PREVIEW_ARTIFACT_V4"
SEMANTIC_SOURCE_ID = "LOCAL_SEMANTIC_REGISTRY"
SLICE_GRANULARITY = "DOMAIN_DATE_BASIS_V1"


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


def split_daily_frames(frame: pd.DataFrame) -> dict[date, pd.DataFrame]:
    """Split one domain frame into immutable, single-trade-date inputs."""
    if "trade_date" not in frame.columns:
        raise ValueError("TRADE_DATE_COLUMN_REQUIRED")
    normalized = frame.copy()
    normalized["trade_date"] = pd.to_datetime(normalized["trade_date"], format="mixed").dt.date
    if normalized["trade_date"].isna().any():
        raise ValueError("TRADE_DATE_REQUIRED_FOR_EVERY_ROW")
    return {
        trade_date: normalized.loc[normalized["trade_date"] == trade_date].copy()
        for trade_date in sorted(normalized["trade_date"].unique())
    }


def apply_quote_quality_gate(frame: pd.DataFrame) -> pd.DataFrame:
    """Bind RET1 to the M7A adjustment-metadata quality gate.

    The normalized parquet contains one row per security and master session,
    including inactive rows.  A positional groupby shift can therefore use a
    non-trading/inactive row as the previous close and, more importantly, can
    calculate raw-close RET1 without proving that the two adjustment states
    are comparable.  This helper resolves the previous master session by
    date, then only exposes ``quote_prev_close`` when the M7A contract allows
    the raw-close fallback.
    """
    required = {
        "security_id", "date", "raw_close", "qfq_mul", "qfq_add",
        "adjustment_status", "adjustment_version", "tradable",
        "has_actual_bar", "data_observed", "is_synthetic_fill",
        "missing_state", "is_master_session",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("QUOTE_INPUT_COLUMNS_MISSING:" + ",".join(missing))

    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"], errors="raise").dt.date
    master_dates = sorted(pd.unique(work.loc[work["is_master_session"].eq(True), "date"]))
    previous_by_date = {
        current: previous
        for previous, current in zip(master_dates, master_dates[1:])
    }
    work["previous_session_date"] = work["date"].map(previous_by_date)

    previous_columns = [
        "security_id", "date", "raw_close", "qfq_mul", "qfq_add",
        "adjustment_status", "adjustment_version", "tradable",
        "has_actual_bar", "data_observed", "is_synthetic_fill", "missing_state",
    ]
    previous = work[previous_columns].rename(
        columns={
            "date": "previous_date",
            "raw_close": "previous_raw_close",
            "qfq_mul": "previous_qfq_mul",
            "qfq_add": "previous_qfq_add",
            "adjustment_status": "previous_adjustment_status",
            "adjustment_version": "previous_adjustment_version",
            "tradable": "previous_tradable",
            "has_actual_bar": "previous_has_actual_bar",
            "data_observed": "previous_data_observed",
            "is_synthetic_fill": "previous_is_synthetic_fill",
            "missing_state": "previous_missing_state",
        }
    )
    work = work.merge(
        previous,
        left_on=["security_id", "previous_session_date"],
        right_on=["security_id", "previous_date"],
        how="left",
        sort=False,
    )

    def _present(values: pd.Series) -> pd.Series:
        return values.notna() & values.astype("string").str.strip().ne("")

    current_raw = pd.to_numeric(work["raw_close"], errors="coerce")
    previous_raw = pd.to_numeric(work["previous_raw_close"], errors="coerce")
    current_ordinary = (
        work["has_actual_bar"].eq(True)
        & work["tradable"].eq(True)
        & work["data_observed"].eq(True)
        & current_raw.notna()
        & ~work["is_synthetic_fill"].eq(True)
        & work["missing_state"].fillna("BAR").astype(str).str.upper().eq("BAR")
    )
    previous_ordinary = (
        work["previous_has_actual_bar"].eq(True)
        & work["previous_tradable"].eq(True)
        & work["previous_data_observed"].eq(True)
        & previous_raw.notna()
        & ~work["previous_is_synthetic_fill"].eq(True)
        & work["previous_missing_state"].fillna("BAR").astype(str).str.upper().eq("BAR")
    )
    comparable_adjustments = pd.Series(True, index=work.index)
    adjustment_changed = pd.Series(False, index=work.index)
    for column in ("qfq_mul", "qfq_add", "adjustment_status", "adjustment_version"):
        current_value = work[column]
        previous_value = work[f"previous_{column}"]
        comparable_adjustments &= _present(current_value) & _present(previous_value)
        adjustment_changed |= current_value.astype("string").fillna("") != previous_value.astype("string").fillna("")

    comparable_bars = current_ordinary & previous_ordinary
    safe = comparable_bars & comparable_adjustments & ~adjustment_changed
    corporate_action = comparable_bars & comparable_adjustments & adjustment_changed
    adjustment_unknown = comparable_bars & ~comparable_adjustments

    work["quote_prev_close"] = pd.NA
    work["quote_ret1_basis"] = "UNAVAILABLE"
    work["quote_state"] = "NO_ACTUAL_BAR"
    work.loc[current_raw.notna(), "quote_ret1_basis"] = "NO_VERIFIED_PREVIOUS_CLOSE"
    work.loc[current_raw.notna(), "quote_state"] = "MISSING_PREVIOUS_CLOSE"
    work.loc[safe, "quote_prev_close"] = previous_raw.loc[safe]
    work.loc[safe, "quote_ret1_basis"] = "RAW_CLOSE_PREVIOUS_TRADING_DAY"
    work.loc[safe, "quote_state"] = "VALID_DEGRADED"
    work.loc[corporate_action, "quote_ret1_basis"] = "CORPORATE_ACTION_UNSAFE"
    work.loc[corporate_action, "quote_state"] = "UNKNOWN_CORPORATE_ACTION"
    work.loc[adjustment_unknown, "quote_ret1_basis"] = "ADJUSTMENT_METADATA_UNAVAILABLE"
    work.loc[adjustment_unknown, "quote_state"] = "UNKNOWN_CORPORATE_ACTION"

    return work.drop(
        columns=[
            "previous_session_date", "previous_date", "previous_raw_close",
            "previous_qfq_mul", "previous_qfq_add", "previous_adjustment_status",
            "previous_adjustment_version", "previous_tradable",
            "previous_has_actual_bar", "previous_data_observed",
            "previous_is_synthetic_fill", "previous_missing_state",
        ],
        errors="ignore",
    )


def source_file(name: str) -> Path:
    matches = list(SHADOW_ROOT.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"SHADOW_SOURCE_EXPECTED_ONE:{name}:{len(matches)}")
    return matches[0]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, list[date], date, dict[str, str], dict[str, str]]:
    membership = pd.read_parquet(MEMBERSHIP_PATH)
    membership["trade_date"] = pd.to_datetime(membership.pop("date"), errors="raise").dt.date
    dates = sorted(pd.unique(membership["trade_date"]))[-3:]
    if not dates:
        raise RuntimeError(f"PREVIEW_DATES_EMPTY:{dates}")
    cutoff = max(dates)
    global SHADOW_ROOT
    SHADOW_ROOT = ROOT / "reports/shadow/v2_runs" / cutoff.strftime("%Y%m%d")
    if not SHADOW_ROOT.is_dir():
        raise RuntimeError(f"SHADOW_ROOT_MISSING:{SHADOW_ROOT}")
    lower = cutoff - timedelta(days=300)

    con = duckdb.connect()
    try:
        raw = con.execute(
            """
            select security_id, date, raw_close, adj_close, raw_amount, raw_volume,
                   qfq_mul, qfq_add, adjustment_status, adjustment_version,
                   tradable, has_actual_bar, data_observed,
                   universe_status, data_quality_flag, is_synthetic_fill,
                   missing_state, is_master_session
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
    raw = apply_quote_quality_gate(raw)

    membership = membership[membership["trade_date"].isin(dates)].copy()
    membership["security_id"] = membership["security_id"].astype(str)
    membership["sector_id"] = membership["sector_id"].astype(str)
    if membership.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise RuntimeError("MEMBERSHIP_DUPLICATE_PREVIEW_INPUT")
    shadow_names = (
        "STEADY_TREND_V2_SHADOW.parquet",
        "STRONG_PULLBACK_V2_SHADOW.parquet",
        "BREAKOUT_PREP_V2_SHADOW.parquet",
        "EARLY_MOVER_V2_SHADOW.parquet",
        "SECTOR_LEADER_V2_SHADOW.parquet",
    )
    hashes = {
        "normalized": sha256_file(NORMALIZED_PATH),
        "membership": sha256_file(MEMBERSHIP_PATH),
    }
    for name in shadow_names:
        hashes[f"shadow:{name}"] = sha256_file(source_file(name))
    hierarchy_paths = {
        "tdxhy.cfg": ROOT / "data/input_staging/metadata" / cutoff.strftime("%Y%m%d") / "T0002/hq_cache/tdxhy.cfg",
        "tdxzs.cfg": ROOT / "data/input_staging/metadata" / cutoff.strftime("%Y%m%d") / "T0002/hq_cache/tdxzs.cfg",
        "infoharbor_block.dat": ROOT / "data/input_staging/metadata" / cutoff.strftime("%Y%m%d") / "T0002/hq_cache/infoharbor_block.dat",
    }
    hierarchy_hashes: dict[str, str] = {}
    for name, path in hierarchy_paths.items():
        if path.is_file():
            hierarchy_hashes[name] = sha256_file(path)
    if not hierarchy_hashes:
        hierarchy_hashes["membership_fallback"] = hashes["membership"]
    hashes["hierarchy"] = hashlib.sha256(json.dumps(hierarchy_hashes, sort_keys=True).encode()).hexdigest()
    return raw, membership, dates, raw["date"].min(), hashes, hierarchy_hashes


def build_frames(
    raw: pd.DataFrame,
    membership: pd.DataFrame,
    dates: list[date],
    *,
    membership_snapshot_id: str,
) -> dict[str, pd.DataFrame]:
    cutoff = max(dates)
    # Calculate rolling fields over the full local history first, then keep the
    # three published dates.  Calculating only on the preview dates makes every
    # 20/60-day field appear empty even though the local parquet contains the
    # required lookback window.
    technical_full = calculate_technical_daily(
        raw[[
            "security_id", "date", "raw_close", "adj_close", "raw_amount", "raw_volume",
            "quote_prev_close", "quote_ret1_basis", "quote_state", "universe_status",
            "data_quality_flag", "is_synthetic_fill",
        ]],
        cutoff=cutoff,
    )
    technical = technical_full[technical_full["date"].isin(dates)].copy()
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
    technical["quality_codes"] = technical.apply(
        lambda row: sorted(
            set(
                ([] if row["validity"] == "VALID" else ["INSUFFICIENT_HISTORY"])
                + ([str(row["quote_ret1_basis"])] if str(row.get("quote_ret1_basis")) in {
                    "ADJUSTMENT_METADATA_UNAVAILABLE", "CORPORATE_ACTION_UNSAFE"
                } else [])
            )
        ),
        axis=1,
    )
    technical["basis_json"] = technical.apply(
        lambda row: {
            "contract_id": "TECHNICAL_HISTORY_V2_1_PREVIEW",
            "price_basis": "TDX_NATIVE_QFQ",
            "source": "LOCAL_FACTORS_DAILY",
            "quote_ret1_basis": row.get("quote_ret1_basis") or "UNAVAILABLE",
            "quote_state": row.get("quote_state") or "NO_ACTUAL_BAR",
        },
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
    technical["price_basis"] = "TDX_NATIVE_QFQ"
    membership = membership.copy()
    membership["membership_snapshot_id"] = membership_snapshot_id
    semantic_records = resolve_semantic_records(membership.to_dict("records"))
    semantic_by_id = {record["sector_id"]: record for record in semantic_records}
    membership["semantic_bucket"] = membership["sector_id"].map(
        lambda value: semantic_by_id[str(value)]["bucket"]
    )
    membership["semantic_version"] = membership["sector_id"].map(
        lambda value: semantic_by_id[str(value)]["semantic_version"]
    )
    membership["semantic_rule_id"] = membership["sector_id"].map(
        lambda value: semantic_by_id[str(value)]["rule_id"]
    )
    membership["semantic_reason"] = membership["sector_id"].map(
        lambda value: semantic_by_id[str(value)]["reason"]
    )
    membership["semantic_override"] = membership["sector_id"].map(
        lambda value: semantic_by_id[str(value)]["override"]
    )

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

    sector_base = build_sector_base(
        technical,
        membership,
        membership_basis="RECONSTRUCTED",
        membership_snapshot_id=membership_snapshot_id,
        semantic_version=SEMANTIC_CONTRACT_ID,
    )
    coverage = build_historical_coverage(
        technical,
        membership,
        structures,
        cutoff=cutoff,
        price_basis="TDX_NATIVE_QFQ",
        expected_security_ids=sorted(technical["security_id"].astype(str).unique()),
        observed_membership_dates=(),
    )

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
        technical[["security_id", "trade_date", "quote_ret1", "ret5", "ret20", "rs5", "rs20", "raw_amount", "amount_vs_prior20", "ma20"]],
        membership[["sector_id", "sector_name", "sector_type", "sector_role", "trade_date", "security_id"]],
        cutoff=cutoff,
        member_states=member_states,
        highs=high,
    )
    # Formal M10 amount A is built from the complete local master-session
    # history and one fixed reconstructed membership snapshot.  It is merged
    # only into new, explicitly named columns; the legacy amount_vs_prior20
    # vector remains untouched as a diagnostic/compatibility field.
    master_calendar = sorted(
        pd.unique(raw.loc[raw["is_master_session"].eq(True), "date"])
    )
    if not master_calendar:
        raise RuntimeError("MASTER_CALENDAR_EMPTY_FOR_SECTOR_AMOUNT")
    fixed_snapshot = membership[
        membership["trade_date"].eq(max(membership["trade_date"]))
    ][["sector_id", "security_id"]].drop_duplicates().copy()
    formal_amount = build_sector_amount_daily(
        raw.loc[raw["date"].isin(master_calendar), ["security_id", "date", "raw_amount", "is_synthetic_fill"]]
        .rename(columns={"date": "trade_date"}),
        fixed_snapshot,
        master_calendar,
        mode=RECONSTRUCTED,
        membership_snapshot=fixed_snapshot,
        membership_snapshot_id=membership_snapshot_id,
        cutoff=cutoff,
        target_dates=dates,
    )
    formal_amount = formal_amount[formal_amount["trade_date"].isin(dates)].copy()
    formal_columns = [
        column for column in formal_amount.columns
        if column not in {"sector_id", "trade_date", "member_amount_sum", "amount_valid_count"}
    ]
    sector_cycle["member_amount_ratio_median_vs_prior20"] = sector_cycle["amount_vs_prior20"]
    sector_cycle = sector_cycle.merge(
        formal_amount[["sector_id", "trade_date", *formal_columns]],
        on=["sector_id", "trade_date"],
        how="left",
        validate="one_to_one",
    )
    return {
        "technical": technical,
        "strength": technical,
        "high": high,
        "structure": structures,
        "summary": summary,
        "sector_base": sector_base,
        "coverage": coverage,
        "member_state": member_states,
        "membership_changes": changes,
        "representative": representatives,
        "sector_cycle": sector_cycle,
    }


def insert_preview(
    frames: dict[str, pd.DataFrame],
    dates: list[date],
    query_start: date,
    input_hashes: dict[str, str],
    membership: pd.DataFrame,
    hierarchy_hashes: dict[str, str],
    membership_snapshot_id: str,
) -> dict[str, object]:
    cutoff = max(dates)
    snapshot_seed = json.dumps(
        {
            "prefix": PREVIEW_PREFIX,
            "artifact_version": PREVIEW_ARTIFACT_VERSION,
            "hierarchy_contract": HIERARCHY_CONTRACT,
            "semantic_contract": SEMANTIC_CONTRACT_ID,
            "semantic_source_id": SEMANTIC_SOURCE_ID,
            "sector_cycle_contract": SECTOR_CYCLE_CONTRACT,
            "sector_amount_contract": SECTOR_AMOUNT_CONTRACT,
            "member_state_contract": MEMBER_STATE_CONTRACT,
            "slice_granularity": SLICE_GRANULARITY,
            "cutoff": str(cutoff),
            "dates": [str(item) for item in dates],
            "inputs": input_hashes,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    snapshot_id = f"{PREVIEW_PREFIX}-{hashlib.sha256(snapshot_seed.encode()).hexdigest()[:16]}"
    contracts = {
        "technical": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "strength": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "high": "TECHNICAL_HISTORY_V2_1_PREVIEW",
        "structure": "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED",
        "summary": "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED",
        "member_state": MEMBER_STATE_CONTRACT,
        "membership_changes": MEMBER_STATE_CONTRACT,
        "representative": "SECTOR_REPRESENTATIVE_STATE_V1_0",
        "sector_cycle": SECTOR_CYCLE_CONTRACT,
        "sector_amount": SECTOR_AMOUNT_CONTRACT,
        "sector_base": "HISTORICAL_SECTOR_ADAPTER_V1_0",
        "coverage": "HISTORICAL_COVERAGE_V2_1_RECONSTRUCTED",
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
            [snapshot_id, cutoff, query_start, "CN_A_LISTED_V2", input_hash, manifest_hash, "SUCCESS", now],
        )
        hierarchy_version, hierarchy_source_hash, hierarchy_count = ensure_hierarchy(
            con,
            membership,
            source_hashes=hierarchy_hashes,
            source_path=f"data/input_staging/metadata/{cutoff.strftime('%Y%m%d')}/T0002/hq_cache/tdxhy.cfg",
            now=now,
        )
        con.execute(
            "insert into analysis_snapshot_hierarchy values (?,?,?,?)",
            [snapshot_id, hierarchy_version, hierarchy_source_hash, now],
        )
        semantic_rows = build_semantic_version_rows(
            membership.to_dict("records"),
            observed_at=now,
            source_id=SEMANTIC_SOURCE_ID,
            valid_from=min(dates),
        )
        semantic_count = insert_semantic_version_rows(con, semantic_rows)
        writer = {
            "technical": insert_technical_rows,
            "strength": insert_strength_rows,
            "high": insert_high_rows,
            "structure": insert_historical_structure_rows,
            "summary": insert_structure_summary_rows,
            "sector_base": insert_sector_base_rows,
            "coverage": insert_coverage_rows,
            "member_state": insert_member_state_rows,
            "membership_changes": insert_membership_change_rows,
            "representative": insert_representative_rows,
            "sector_cycle": insert_sector_cycle_rows,
        }
        storage_multipliers = {"high": 4}
        counts: dict[str, int] = {}
        slice_ids: dict[str, dict[date, str]] = {}
        date_sets: dict[str, set[date]] = {}
        for domain, frame in frames.items():
            daily_frames = split_daily_frames(frame)
            date_sets[domain] = set(daily_frames)
            slice_ids[domain] = {}
            counts[domain] = 0
            for trade_date, daily_frame in daily_frames.items():
                slice_id = f"{snapshot_id}-{domain}-{trade_date.strftime('%Y%m%d')}"
                slice_ids[domain][trade_date] = slice_id
                logical_hash = frame_hash(daily_frame)
                basis = {
                    "history_basis": "RECONSTRUCTED",
                    "artifact_version": PREVIEW_ARTIFACT_VERSION,
                    "source": "LOCAL_PARQUET_ONLY",
                    "tdx_source_modified": False,
                    "input_artifacts": input_hashes,
                    "preview_window": [str(min(dates)), str(cutoff)],
                    "query_start": str(query_start),
                    "hierarchy_version": hierarchy_version,
                    "hierarchy_source_hash": hierarchy_source_hash,
                    "membership_snapshot_id": membership_snapshot_id,
                    "semantic_version": SEMANTIC_CONTRACT_ID,
                    "semantic_source_id": SEMANTIC_SOURCE_ID,
                    "sector_amount_contract": SECTOR_AMOUNT_CONTRACT,
                    "slice_granularity": SLICE_GRANULARITY,
                    "domain": domain,
                    "trade_date": str(trade_date),
                }
                declared_row_count = len(daily_frame) * storage_multipliers.get(domain, 1)
                con.execute(
                    "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [slice_id, domain, trade_date, contracts[domain], input_hash, hashlib.sha256(b"[]").hexdigest(), json.dumps(basis, ensure_ascii=False, sort_keys=True), declared_row_count, logical_hash, "DUCKDB", None, now],
                )
                counts[domain] += writer[domain](con, slice_id, daily_frame)
                con.execute(
                    "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
                    [slice_id, "LOCAL_NORMALIZED", membership_snapshot_id, "TDX_NATIVE_QFQ", trade_date, now, 1.0, json.dumps({"preview": True, "history_basis": "RECONSTRUCTED", "hierarchy_version": hierarchy_version, "hierarchy_source_hash": hierarchy_source_hash, "semantic_version": SEMANTIC_CONTRACT_ID, "semantic_source_id": SEMANTIC_SOURCE_ID, "slice_granularity": SLICE_GRANULARITY, "trade_date": str(trade_date)}, ensure_ascii=False, sort_keys=True)],
                )
                con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, domain, trade_date, slice_id])

        dependencies: dict[str, tuple[str, ...]] = {
            "strength": ("technical",),
            "sector_base": ("technical",),
            "coverage": ("technical", "structure", "sector_base"),
            "summary": ("structure",),
            "member_state": ("technical", "high", "structure"),
            "membership_changes": ("member_state",),
            "representative": ("member_state",),
            "sector_cycle": ("technical", "sector_base", "member_state", "high"),
        }
        for domain, input_domains in dependencies.items():
            records = []
            for trade_date in sorted(date_sets[domain]):
                output_slice_id = slice_ids[domain][trade_date]
                for input_domain in input_domains:
                    if trade_date in date_sets[input_domain]:
                        records.append((output_slice_id, input_domain, trade_date, slice_ids[input_domain][trade_date]))
            for record in records:
                con.execute("insert into analysis_slice_dependencies values (?,?,?,?)", list(record))
            records_by_slice: dict[str, list[tuple[str, str, date, str]]] = {}
            for record in records:
                records_by_slice.setdefault(record[0], []).append(record)
            for output_slice_id, slice_records in records_by_slice.items():
                dependency_hash = hashlib.sha256(json.dumps(slice_records, default=str, sort_keys=True).encode()).hexdigest()
                con.execute("update analysis_slices set dependency_hash=? where slice_id=?", [dependency_hash, output_slice_id])
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
            "query_start": str(query_start),
            "hierarchy_version": hierarchy_version,
            "hierarchy_source_hash": hierarchy_source_hash,
            "hierarchy_node_count": hierarchy_count,
            "semantic_row_count": semantic_count,
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
    raw, membership, dates, query_start, hashes, hierarchy_hashes = load_inputs()
    membership_snapshot_id = "reconstructed-membership-" + hashes["membership"][:24]
    frames = build_frames(raw, membership, dates, membership_snapshot_id=membership_snapshot_id)
    result = insert_preview(frames, dates, query_start, hashes, membership, hierarchy_hashes, membership_snapshot_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

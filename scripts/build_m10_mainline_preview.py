"""Bind the M10 mainline page to the current local reconstructed snapshot.

This is the single 10-04 delivery step: it reuses already-built local M8/M9
sector-cycle and member-state slices, creates a new preview snapshot, and adds
only the mainline domain.  It never reads or writes a TDX source directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.mainline import build_mainline_state_daily, config_hash, insert_mainline_rows, mainline_history_policy


DB_PATH = Path(os.environ.get("WORKBENCH_COMPUTE_DUCKDB", str(ROOT / "data/database/market_research.duckdb"))).resolve()
CONFIG_PATH = ROOT / "config/mainline-v2.4-preview.yaml"
CONTRACT_ID = "MAINLINE_STATE_V2_4_PREVIEW"
AMOUNT_CONTRACT_ID = "SECTOR_AMOUNT_COMMON_AGG_V1"
ARTIFACT_VERSION = "M10_PREVIEW_ARTIFACT_V6"
SLICE_GRANULARITY = "DOMAIN_DATE_BASIS_V1"


def _digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _frame_digest(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values(["trade_date", "sector_id"], kind="mergesort").reset_index(drop=True)
    payload = ordered.to_json(orient="records", force_ascii=False, date_format="iso")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_binding(connection: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    row = connection.execute(
        """
        select pas.publication_id, pas.snapshot_id
          from publication_analysis_snapshots pas
          join publication_heads h on h.publication_id=pas.publication_id
          join publications p on p.publication_id=pas.publication_id
         where pas.domain='LOCAL_RECONSTRUCTED' and p.status='SUCCESS'
         order by h.trade_date desc
         limit 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("LOCAL_RECONSTRUCTED_BINDING_MISSING")
    return row[0], row[1]


def _mainline_artifact(connection: duckdb.DuckDBPyConnection, snapshot_id: str) -> tuple[pd.DataFrame, dict[str, object], object | None]:
    rows = connection.execute(
        """
        select e.trade_date, e.slice_id, s.basis_json
          from analysis_snapshot_entries e
          join analysis_slices s on s.slice_id=e.slice_id
         where e.snapshot_id=? and e.domain='mainline'
         order by e.trade_date desc, e.slice_id
        """,
        [snapshot_id],
    ).fetchall()
    cutoff_row = connection.execute("select cutoff_date from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone()
    if not rows:
        return pd.DataFrame(), {}, cutoff_row[0] if cutoff_row else None
    frame = connection.execute(
        """
        select m.*
          from analysis_snapshot_entries e
          join mainline_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date
         where e.snapshot_id=? and e.domain='mainline'
         order by m.trade_date, m.sector_id
        """,
        [snapshot_id],
    ).fetchdf()
    basis = json.loads(rows[0][2]) if rows[0][2] else {}
    return frame, basis, cutoff_row[0] if cutoff_row else None


def split_mainline_daily_frames(frame: pd.DataFrame) -> dict[object, pd.DataFrame]:
    """Split the mainline output into immutable, single-date slices."""
    if "trade_date" not in frame.columns:
        raise ValueError("MAINLINE_TRADE_DATE_COLUMN_REQUIRED")
    normalized = frame.copy()
    normalized["trade_date"] = pd.to_datetime(normalized["trade_date"], format="mixed", errors="raise").dt.date
    if normalized["trade_date"].isna().any():
        raise ValueError("MAINLINE_TRADE_DATE_REQUIRED_FOR_EVERY_ROW")
    return {
        trade_date: normalized.loc[normalized["trade_date"] == trade_date].copy()
        for trade_date in sorted(normalized["trade_date"].unique())
    }


def build() -> dict[str, object]:
    con = duckdb.connect(str(DB_PATH))
    try:
        publication_id, previous_snapshot_id = _latest_binding(con)
        base_snapshot_id = previous_snapshot_id
        previous_mainline, bound_basis, previous_cutoff = _mainline_artifact(con, previous_snapshot_id)
        existing_mainline = con.execute(
            "select e.slice_id from analysis_snapshot_entries e where e.snapshot_id=? and e.domain='mainline' and e.trade_date=(select cutoff_date from analysis_snapshots where snapshot_id=?) limit 1",
            [base_snapshot_id, base_snapshot_id],
        ).fetchone()
        if existing_mainline:
            base_snapshot_id = str(bound_basis.get("base_snapshot_id") or base_snapshot_id)
        base = con.execute(
            "select cutoff_date, query_start, universe_contract, config_hash, manifest_hash from analysis_snapshots where snapshot_id=?",
            [base_snapshot_id],
        ).fetchone()
        if not base:
            raise RuntimeError("BASE_ANALYSIS_SNAPSHOT_MISSING")
        cutoff, query_start, universe_id, base_input_hash, base_manifest_hash = base
        hierarchy_binding = con.execute(
            "select hierarchy_version, source_hash from analysis_snapshot_hierarchy where snapshot_id=?",
            [base_snapshot_id],
        ).fetchone()
        cycle_slices = con.execute(
            "select trade_date, slice_id from analysis_snapshot_entries where snapshot_id=? and domain='sector_cycle' order by trade_date, slice_id",
            [base_snapshot_id],
        ).fetchall()
        member_slices = con.execute(
            "select trade_date, slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date, slice_id",
            [base_snapshot_id],
        ).fetchall()
        if not cycle_slices or not member_slices:
            raise RuntimeError("M10_MAINLINE_INPUT_SLICE_MISSING")
        cycle_slice_by_date = {row[0]: row[1] for row in cycle_slices}
        member_slice_by_date = {row[0]: row[1] for row in member_slices}
        cycle_slice_ids = sorted(set(cycle_slice_by_date.values()))
        member_slice_ids = sorted(set(member_slice_by_date.values()))
        sector_cycle = con.execute(
            """
            select c.*
            from analysis_snapshot_entries e
            join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date
            where e.snapshot_id=? and e.domain='sector_cycle'
            order by c.trade_date, c.sector_id
            """,
            [base_snapshot_id],
        ).fetchdf()
        member_states = con.execute(
            """
            select m.*
            from analysis_snapshot_entries e
            join member_state_result_daily m on m.slice_id=e.slice_id and m.trade_date=e.trade_date
            where e.snapshot_id=? and e.domain='member_state'
            order by m.trade_date, m.sector_id, m.security_id
            """,
            [base_snapshot_id],
        ).fetchdf()
        cfg_hash = config_hash(CONFIG_PATH)

        if (
            bound_basis.get("artifact_version") == ARTIFACT_VERSION
            and bound_basis.get("config_hash") == cfg_hash
            and bound_basis.get("base_snapshot_id") == base_snapshot_id
        ):
            return {"status": "ALREADY_BUILT", "publication_id": publication_id, "snapshot_id": previous_snapshot_id, "rows": len(previous_mainline)}

        comparison_snapshot_id = previous_snapshot_id
        comparison_mainline = previous_mainline
        comparison_basis = bound_basis
        comparison_cutoff = previous_cutoff
        visited: set[str] = set()
        while not comparison_mainline.empty and comparison_snapshot_id not in visited:
            visited.add(comparison_snapshot_id)
            latest_identity = comparison_mainline.sort_values(["sector_id", "trade_date"], kind="mergesort").groupby("sector_id", sort=False).tail(1)
            same_identity = bool(
                not latest_identity.empty
                and (latest_identity["contract_id"].astype(str) == CONTRACT_ID).all()
                and (latest_identity["config_hash"].astype(str) == cfg_hash).all()
                and (latest_identity["history_basis"].astype(str) == "RECONSTRUCTED").all()
            )
            if not same_identity or comparison_cutoff is None or comparison_cutoff < cutoff:
                break
            ancestor = comparison_basis.get("previous_snapshot_id")
            if not ancestor:
                comparison_mainline = pd.DataFrame()
                break
            comparison_snapshot_id = str(ancestor)
            comparison_mainline, comparison_basis, comparison_cutoff = _mainline_artifact(con, comparison_snapshot_id)

        previous_latest = comparison_mainline.sort_values(["sector_id", "trade_date"], kind="mergesort").groupby("sector_id", sort=False).tail(1) if not comparison_mainline.empty else pd.DataFrame()
        identity_changed = bool(
            not previous_latest.empty
            and (
                (previous_latest["contract_id"].astype(str) != CONTRACT_ID).any()
                or (previous_latest["config_hash"].astype(str) != cfg_hash).any()
                or (previous_latest["history_basis"].astype(str) != "RECONSTRUCTED").any()
            )
        )
        cross_snapshot_comparison = bool(
            not comparison_mainline.empty
            and (comparison_cutoff is None or cutoff > comparison_cutoff or identity_changed)
        )
        frame = build_mainline_state_daily(
            sector_cycle,
            member_states=member_states,
            config=CONFIG_PATH,
            previous_frame=comparison_mainline if cross_snapshot_comparison else None,
        )
        if frame.empty:
            raise RuntimeError("M10_MAINLINE_FRAME_EMPTY")

        seed = {
            "artifact_version": ARTIFACT_VERSION,
            "base_snapshot_id": base_snapshot_id,
            "contract_id": CONTRACT_ID,
            "config_hash": cfg_hash,
            "amount_contract_id": AMOUNT_CONTRACT_ID,
            "frame_hash": _frame_digest(frame),
        }
        snapshot_id = "m10-mainline-preview-" + _digest(seed)[:16]
        existing = con.execute("select status from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone()
        if existing:
            current_binding = con.execute(
                "select snapshot_id from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'",
                [publication_id],
            ).fetchone()
            if not current_binding or current_binding[0] != snapshot_id:
                now = datetime.now(timezone.utc)
                con.execute("begin transaction")
                con.execute("delete from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id])
                con.execute("insert into publication_analysis_snapshots values (?,?,?,?)", [publication_id, "LOCAL_RECONSTRUCTED", snapshot_id, now])
                con.execute("commit")
                return {"status": "REBOUND", "publication_id": publication_id, "snapshot_id": snapshot_id, "rows": len(frame)}
            return {"status": "ALREADY_BUILT", "publication_id": publication_id, "snapshot_id": snapshot_id, "rows": len(frame)}

        now = datetime.now(timezone.utc)
        input_hash = _digest({"base_input_hash": base_input_hash, "sector_cycle_slices": cycle_slice_ids, "member_state_slices": member_slice_ids})
        manifest_hash = _digest({"base_manifest_hash": base_manifest_hash, "mainline_frame_hash": _frame_digest(frame)})
        inherited_mainline_dates = {
            row[0] for row in con.execute(
                "select trade_date from analysis_snapshot_entries where snapshot_id=? and domain='mainline'",
                [base_snapshot_id],
            ).fetchall()
        }
        daily_frames = {
            trade_date: daily_frame
            for trade_date, daily_frame in split_mainline_daily_frames(frame).items()
            if trade_date not in inherited_mainline_dates
        }
        input_basis_rows = con.execute(
            """
            select e.trade_date, e.domain, e.slice_id, s.basis_json,
                   b.universe_basis, b.membership_snapshot_id, b.price_basis,
                   b.adjustment_as_of, b.source_observed_at, b.coverage,
                   b.capabilities_json
              from analysis_snapshot_entries e
              join analysis_slices s on s.slice_id=e.slice_id
              left join analysis_daily_basis b on b.slice_id=e.slice_id
             where e.snapshot_id=? and e.domain in ('sector_cycle', 'member_state')
             order by e.trade_date, e.domain
            """,
            [base_snapshot_id],
        ).fetchall()
        input_basis_by_date: dict[object, dict[str, dict[str, object]]] = {}
        for row in input_basis_rows:
            trade_date, domain, slice_id, basis_json, universe_basis, membership_snapshot_id, price_basis, adjustment_as_of, source_observed_at, coverage, capabilities_json = row
            input_basis_by_date.setdefault(trade_date, {})[domain] = {
                "slice_id": slice_id,
                "basis": json.loads(basis_json) if basis_json else {},
                "universe_basis": universe_basis,
                "membership_snapshot_id": membership_snapshot_id,
                "price_basis": price_basis,
                "adjustment_as_of": adjustment_as_of,
                "source_observed_at": source_observed_at,
                "coverage": coverage,
                "capabilities": json.loads(capabilities_json) if capabilities_json else {},
            }

        con.execute("begin transaction")
        con.execute(
            "insert into analysis_snapshots values (?,?,?,?,?,?,?,?)",
            [snapshot_id, cutoff, query_start, universe_id, cfg_hash, manifest_hash, "SUCCESS", now],
        )
        # Reuse the already published M8/M9 slices in this new snapshot.  The
        # new mainline slices are the only newly materialized analytical domain.
        con.execute(
            "insert into analysis_snapshot_entries select ?, domain, trade_date, slice_id from analysis_snapshot_entries where snapshot_id=?",
            [snapshot_id, base_snapshot_id],
        )
        if hierarchy_binding:
            con.execute(
                "insert into analysis_snapshot_hierarchy values (?,?,?,?)",
                [snapshot_id, hierarchy_binding[0], hierarchy_binding[1], now],
            )
        inserted = 0
        for trade_date, daily_frame in daily_frames.items():
            slice_id = f"{snapshot_id}-mainline-{trade_date.strftime('%Y%m%d')}"
            input_basis = input_basis_by_date.get(trade_date, {})
            cycle_basis = input_basis.get("sector_cycle", {})
            member_basis = input_basis.get("member_state", {})
            membership_snapshot_id = member_basis.get("membership_snapshot_id") or cycle_basis.get("membership_snapshot_id")
            semantic_version = (
                member_basis.get("basis", {}).get("semantic_version")
                or cycle_basis.get("basis", {}).get("semantic_version")
                or member_basis.get("capabilities", {}).get("semantic_version")
                or cycle_basis.get("capabilities", {}).get("semantic_version")
            )
            price_basis = cycle_basis.get("price_basis") or member_basis.get("price_basis") or "TDX_NATIVE_QFQ"
            adjustment_as_of = cycle_basis.get("adjustment_as_of") or member_basis.get("adjustment_as_of") or trade_date
            source_observed_at = cycle_basis.get("source_observed_at") or member_basis.get("source_observed_at") or now
            coverage_values = [
                value.get("coverage")
                for value in (cycle_basis, member_basis)
                if value.get("coverage") is not None
            ]
            coverage = min(float(value) for value in coverage_values) if coverage_values else 1.0
            input_slices = {
                "sector_cycle": cycle_slice_by_date.get(trade_date),
                "member_state": member_slice_by_date.get(trade_date),
            }
            dependency_records = [
                (slice_id, domain, trade_date, input_slice)
                for domain, input_slice in input_slices.items()
                if input_slice
            ]
            dependency_hash = _digest(dependency_records)
            basis = {
                "artifact_version": ARTIFACT_VERSION,
                "config_hash": cfg_hash,
                "history_policy": mainline_history_policy(CONFIG_PATH),
                "history_basis": "RECONSTRUCTED",
                "previous_snapshot_id": comparison_snapshot_id if cross_snapshot_comparison else previous_snapshot_id,
                "source_binding_snapshot_id": previous_snapshot_id,
                "source": "LOCAL_DUCKDB_ANALYSIS_SLICES",
                "tdx_source_modified": False,
                "base_snapshot_id": base_snapshot_id,
                "input_slices": input_slices,
                "amount_contract_id": AMOUNT_CONTRACT_ID,
                "membership_snapshot_id": membership_snapshot_id,
                "semantic_version": semantic_version,
                "slice_granularity": SLICE_GRANULARITY,
                "domain": "mainline",
                "trade_date": str(trade_date),
                "stage": "M10-04",
            }
            con.execute(
                "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, "mainline", trade_date, CONTRACT_ID, _digest({"base_input_hash": input_hash, "trade_date": str(trade_date), "input_slices": input_slices}), dependency_hash, json.dumps(basis, ensure_ascii=False, sort_keys=True), len(daily_frame), _frame_digest(daily_frame), "DUCKDB", None, now],
            )
            inserted += insert_mainline_rows(con, slice_id, daily_frame)
            for record in dependency_records:
                con.execute("insert into analysis_slice_dependencies values (?,?,?,?)", list(record))
            capabilities = {
                "stage": "M10-04",
                "history_basis": "RECONSTRUCTED",
                "config_hash": cfg_hash,
                "amount_contract_id": AMOUNT_CONTRACT_ID,
                "membership_snapshot_id": membership_snapshot_id,
                "semantic_version": semantic_version,
                "input_slices": input_slices,
                "slice_granularity": SLICE_GRANULARITY,
                "domain": "mainline",
                "trade_date": str(trade_date),
            }
            con.execute(
                "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
                [slice_id, "LOCAL_RECONSTRUCTED", membership_snapshot_id, price_basis, adjustment_as_of, source_observed_at, coverage, json.dumps(capabilities, ensure_ascii=False, sort_keys=True)],
            )
            con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, "mainline", trade_date, slice_id])
        con.execute("delete from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id])
        con.execute("insert into publication_analysis_snapshots values (?,?,?,?)", [publication_id, "LOCAL_RECONSTRUCTED", snapshot_id, now])
        con.execute("commit")
        return {"status": "BUILT", "publication_id": publication_id, "snapshot_id": snapshot_id, "base_snapshot_id": base_snapshot_id, "rows": inserted, "sectors": int(frame["sector_id"].nunique()), "dates": sorted(str(value) for value in frame["trade_date"].unique()), "history_basis": "RECONSTRUCTED", "stage": "M10-04"}
    except Exception:
        try:
            con.execute("rollback")
        except Exception:
            pass
        raise
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, default=str))

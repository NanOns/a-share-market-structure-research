"""Freeze a read-only P12-01 baseline for the latest complete V3 research run."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from time import monotonic

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/market_research.duckdb"
PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
DOCS = [
    "AGENTS.md",
    "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md",
    "docs/V3_TODAY_RESEARCH_PRIORITY_AUDIT_CHANGELOG_20260914.md",
    "docs/ALGO_R1_CORRECTNESS_RECEIPT_20260914.md",
    "reports/phase0_2c/PHASE0_2C_RELEASE_SEAL.json",
]
OUT = ROOT / "reports/p12_01/baseline_v2.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    started = monotonic()
    seal = json.loads((ROOT / DOCS[-1]).read_text(encoding="utf-8"))
    if not seal["phase0_closed"] or not seal["adjusted_dataset_allowed"]:
        raise RuntimeError("Phase 0 does not permit the adjusted dataset")
    with duckdb.connect(str(DB), read_only=True) as con:
        run = con.execute("""
            SELECT run_id, trade_date, publication_id, snapshot_id,
                   membership_snapshot_id, algorithm_version, parameter_hash,
                   dependency_bindings, history_basis, status
            FROM research_runs WHERE status='COMPLETE'
            ORDER BY trade_date DESC, completed_at DESC, run_id DESC LIMIT 1
        """).fetchone()
        if run is None:
            raise RuntimeError("No complete research run")
        keys = ["run_id", "trade_date", "publication_id", "snapshot_id",
                "membership_snapshot_id", "algorithm_version", "parameter_hash",
                "dependency_bindings", "history_basis", "status"]
        identity = dict(zip(keys, run))
        identity["trade_date"] = identity["trade_date"].isoformat()
        identity["dependency_bindings"] = json.loads(identity["dependency_bindings"])
        rid = identity["run_id"]
        pub = identity["publication_id"]

        def one(sql: str, *args: object) -> object:
            return con.execute(sql, list(args)).fetchone()[0]

        stock = con.execute("""
            SELECT count(*), count_if(setup), count_if(breakout), count_if(recovery),
                   count_if(trend_background), count_if(structure_break),
                   count_if(quality='READY'), count_if(quality='PARTIAL'),
                   count(bias20), count(sigma20), count(extension_z20),
                   count(dist_high20), count(range5), count(range20),
                   count(rps5_delta3), count(liquidity20_amount)
            FROM research_stock_states WHERE run_id=?
        """, [rid]).fetchone()
        sector = con.execute("""
            SELECT count(*), count_if(current_eligible), count_if(potential_eligible),
                   count(dq5_3), count(b_delta3), count(ma20_delta3),
                   count(ma20_width), count(amount_a), count(current_rank),
                   count(potential_rank), count_if(quality='READY')
            FROM research_sector_states WHERE run_id=?
        """, [rid]).fetchone()
        shortlist = con.execute("""
            SELECT list_type, count(*) FROM research_shortlist
            WHERE run_id=? GROUP BY list_type ORDER BY list_type
        """, [rid]).fetchall()
        loo = con.execute("""
            SELECT count(*),
                   count_if(contains(selection_reason::VARCHAR, 'LOO_COMMON_SUPPORT')),
                   count_if(contains(selection_reason::VARCHAR, 'TRACK_ROLE_ELIGIBLE'))
            FROM research_shortlist WHERE run_id=?
        """, [rid]).fetchone()
        publication = con.execute("""
            SELECT trade_date, status, source_manifest_sha256, source_identity_sha256,
                   computation_identity_sha256
            FROM publications WHERE publication_id=?
        """, [pub]).fetchone()
        rows = con.execute("""
            SELECT count(*), count_if(has_actual_bar),
                   count_if(universe_status='IN_NORMAL_UNIVERSE')
            FROM read_parquet(?) WHERE date=?
        """, [str(PARQUET), identity["trade_date"]]).fetchone()
        result = {
            "stage_contract": "P12-01_BASELINE_V2",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "consulted_versions": {name: sha256(ROOT / name) for name in DOCS},
            "phase0": {k: seal[k] for k in ["final_status", "phase0_closed",
                       "adjusted_dataset_allowed", "adjustment_contract_version"]},
            "input_identity": identity,
            "publication": {
                "trade_date": publication[0].isoformat(), "status": publication[1],
                "source_manifest_sha256": publication[2],
                "source_identity_sha256": publication[3],
                "computation_identity_sha256": publication[4],
            },
            "baseline": {
                "old_candidate_rows": one("SELECT count(*) FROM candidate_daily WHERE publication_id=?", pub),
                "stock_fields": dict(zip(["rows", "setup_true", "breakout_true", "recovery_true",
                    "trend_background_true", "structure_break_true", "ready", "partial",
                    "bias20_nonnull", "sigma20_nonnull", "extension_z20_nonnull",
                    "dist_high20_nonnull", "range5_nonnull", "range20_nonnull",
                    "rps5_delta3_nonnull", "liquidity20_amount_nonnull"], stock)),
                "sector_fields": dict(zip(["rows", "current_true", "potential_true",
                    "dq5_3_nonnull", "b_delta3_nonnull", "ma20_delta3_nonnull",
                    "ma20_width_nonnull", "amount_a_nonnull", "current_rank_nonnull",
                    "potential_rank_nonnull", "ready"], sector)),
                "shortlist_by_type": dict(shortlist),
                "shortlist_loo_funnel": dict(zip(["rows", "loo_common_support_reason",
                    "track_role_eligible_reason"], loo)),
                "adjusted_daily_date": dict(zip(["rows", "actual_bar", "normal_universe"], rows)),
                "complete_run_distinct_dates": one("SELECT count(DISTINCT trade_date) FROM research_runs WHERE status='COMPLETE'"),
            },
            "resource_baseline": {
                "database_bytes": DB.stat().st_size,
                "adjusted_daily_bytes": PARQUET.stat().st_size,
                "duckdb_version": duckdb.__version__,
            },
            "dependency_lock_draft": {
                "bound_run": rid,
                "bound_parameter_hash": identity["parameter_hash"],
                "adjusted_daily_sha256": identity["dependency_bindings"].get("adjusted_daily_sha256"),
                "historical_membership": identity["dependency_bindings"].get("historical_membership"),
                "new_contract_source_hashes": "PENDING_P12_02",
                "runtime_and_numeric_library_lock": "PENDING_P12_02",
            },
            "counterexample_register": "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md §18 items 1-25",
            "effect_pre_registration": {"minimum_signal_days": 20, "minimum_episodes": 50,
                "scenario_counts_required": True, "current_status": "EFFECT_PENDING"},
            "query_elapsed_seconds": round(monotonic() - started, 3),
            "acceptance_result": "DEGRADED_PASS",
            "acceptance_scope": "Read-only identity and baseline freeze; historical PIT and new full-population LOO remain unavailable",
            "next_stage": "P12-02_FACTOR_V3_3",
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    actual_parquet_sha256 = sha256(PARQUET)
    result["resource_baseline"]["adjusted_daily_actual_sha256"] = actual_parquet_sha256
    result["resource_baseline"]["adjusted_daily_matches_run"] = (
        actual_parquet_sha256 == result["dependency_lock_draft"]["adjusted_daily_sha256"]
    )
    if not result["resource_baseline"]["adjusted_daily_matches_run"]:
        result["acceptance_result"] = "BLOCKED"
        result["acceptance_scope"] = "Adjusted daily file differs from bound research run"
        result["next_stage"] = "P12-01_RECONCILE_INPUT_IDENTITY"
    fd, tmp = tempfile.mkstemp(prefix="baseline_v2.", suffix=".tmp", dir=OUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(OUT)


if __name__ == "__main__":
    main()

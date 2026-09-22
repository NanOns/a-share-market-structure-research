import json
from pathlib import Path

import duckdb
import pytest

from workbench_service.research_bundle_v3_3 import activate_bundle, build_bundle
from workbench_service.research_registry_v3_3 import ResearchRegistryV33Error, register_active_bundle


SCHEMA = Path(__file__).resolve().parents[2] / "src/workbench_db/migrations/035_v3_3_research_registry.sql"


def identity():
    return {
        "publication_id": "pub-1", "snapshot_id": "snap-1", "membership_snapshot_id": "members-1",
        "research_run_id": "run-1", "parameter_hash": "params-1", "dependency_lock_hash": "deps-1",
        "history_basis": "LOCAL_CLOSE_ONLY", "trade_date": "2026-09-15",
    }


def result(security_id="SZ.000001"):
    return {
        "security_id": security_id, "security_name": "平安银行", "trade_date": "2026-09-15",
        "primary_category": "LAUNCH_CONFIRM", "matched_categories": ["LAUNCH_CONFIRM"],
        "category_rank": 1, "category_score": 88.5, "rank_status": "SCORED",
        "selection_mode": "SUPPORTED", "sector_support_status": "CONFIRMED", "risk_codes": [],
        "factor_evidence": {"quality": "READY"}, "scanner_evidence": {"launch": {"eligible": True}},
    }


def setup(tmp_path, rows=None):
    bundle = build_bundle(tmp_path / "bundles", identity(), rows or [result()], {}, bundle_contract="TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02")
    pointer = tmp_path / "active.json"
    activate_bundle(Path(bundle["path"]), pointer)
    connection = duckdb.connect(":memory:")
    connection.execute(SCHEMA.read_text(encoding="utf-8"))
    return connection, pointer, bundle


def test_registers_verified_bundle_and_full_payload_idempotently(tmp_path):
    connection, pointer, bundle = setup(tmp_path)
    first = register_active_bundle(connection, pointer)
    second = register_active_bundle(connection, pointer)
    assert first["result_count"] == 1 and not first["reused"] and second["reused"]
    stored = connection.execute("select security_name,primary_category,result_payload from research_candidates_v3_3").fetchone()
    assert stored[:2] == ("平安银行", "LAUNCH_CONFIRM")
    assert json.loads(stored[2])["factor_evidence"]["quality"] == "READY"
    assert connection.execute("select bundle_digest,result_count,status from research_runs_v3_3").fetchone() == (bundle["output_digest"], 1, "COMPLETE")


def test_rejects_cross_date_row_without_partial_database_write(tmp_path):
    bad = result()
    bad["trade_date"] = "2026-09-14"
    connection, pointer, _ = setup(tmp_path, [bad])
    with pytest.raises(ResearchRegistryV33Error, match="DATE_MISMATCH"):
        register_active_bundle(connection, pointer)
    assert connection.execute("select count(*) from research_runs_v3_3").fetchone()[0] == 0
    assert connection.execute("select count(*) from research_candidates_v3_3").fetchone()[0] == 0

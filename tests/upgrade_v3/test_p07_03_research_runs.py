from pathlib import Path

import duckdb
import pytest

from workbench_service.research_runs import ResearchRunError, ResearchRunStore, validate_research_job
from workbench_service import research_builder


def store():
    connection = duckdb.connect(":memory:")
    return connection, ResearchRunStore(connection)


def body(**updates):
    value = {"job_type": "BUILD_RESEARCH_V3", "publication_id": "pub", "trade_date": "2026-09-10", "algorithm_version": "RESEARCH_V3_PREVIEW_1", "parameter_hash": "hash", "snapshot_id": "snap", "membership_snapshot_id": "members", "dependency_bindings": {"technical": "slice-a", "roles": "SECTOR_MEMBER_ROLES_PREVIEW_1"}}
    value.update(updates)
    return value


def test_input_key_is_stable_and_same_run_is_idempotently_reused():
    connection, runs = store()
    first = runs.start(body())
    second = runs.start(body())
    assert first["run_id"] == second["run_id"]
    assert second["reused"] is True
    with pytest.raises(ResearchRunError, match="NOT_VISIBLE"):
        runs.visible(first["run_id"])
    complete = runs.complete(first["run_id"])
    assert complete["status"] == "COMPLETE"
    assert runs.visible(first["run_id"])["status"] == "COMPLETE"
    assert runs.start(body())["reused"] is True
    connection.close()


def test_complete_is_atomic_and_failed_run_is_not_visible():
    connection, runs = store()
    started = runs.start(body(publication_id="pub-2"))
    with pytest.raises(Exception):
        runs.complete(started["run_id"], shortlists=[{"list_type": "CURRENT_FOCUS", "security_id": "S", "rank": 1}, {"list_type": "CURRENT_FOCUS", "security_id": "S", "rank": 2}])
    assert connection.execute("select status from research_runs where run_id=?", [started["run_id"]]).fetchone()[0] == "BUILDING"
    runs.fail(started["run_id"], "BUILD_FAILED")
    with pytest.raises(ResearchRunError, match="NOT_VISIBLE"):
        runs.visible(started["run_id"])
    connection.close()


def test_complete_seals_compact_sector_role_and_shortlist_rows_in_one_visibility_boundary():
    connection, runs = store()
    started = runs.start(body(publication_id="pub-compact"))
    result = runs.complete(
        started["run_id"],
        sector_states=[{"sector_id": "A", "quality": "READY"}],
        member_roles=[{"sector_id": "A", "security_id": "S", "role": "TODAY_LEADER", "role_rank": 1}],
        shortlists=[{"list_type": "CURRENT_FOCUS", "security_id": "S", "rank": 1}],
    )
    assert result["status"] == "COMPLETE"
    assert connection.execute("select count(*) from research_sector_states where run_id=?", [started["run_id"]]).fetchone()[0] == 1
    assert connection.execute("select count(*) from research_sector_member_roles where run_id=?", [started["run_id"]]).fetchone()[0] == 1
    assert connection.execute("select count(*) from research_shortlist where run_id=?", [started["run_id"]]).fetchone()[0] == 1
    connection.close()


def test_job_contract_rejects_unknown_and_invalid_date():
    assert validate_research_job(body())["job_type"] == "BUILD_RESEARCH_V3"
    with pytest.raises(ResearchRunError, match="UNKNOWN_FIELD"):
        validate_research_job(body(extra="no"))
    with pytest.raises(ResearchRunError, match="TRADE_DATE_INVALID"):
        validate_research_job(body(trade_date="2026-99-10"))


def test_builder_declares_the_complete_stage_order_and_job_entrypoint():
    source = Path(research_builder.__file__).read_text(encoding="utf-8")
    ordered = ["build_stock_research_features(", "classify_stock_frame(", "build_sector_current(",
               "build_sector_potential(", "progress_potential_episode(", "build_sector_member_roles(",
               "select_associations_and_shortlists(", "store.complete("]
    positions = [source.index(marker) for marker in ordered]
    assert positions == sorted(positions)
    app_source = (Path(__file__).parents[2] / "src/workbench_service/app.py").read_text(encoding="utf-8")
    assert "'/api/v3/research/jobs'" in app_source
    assert "build_latest_research_run(root,db)" in app_source
    assert "lag(raw_close) over(partition by security_id order by date) as quote_prev_close" in source
    assert "e.snapshot_id=? and e.domain='technical' and e.trade_date=?" in source
    assert 'rename(columns={"date": "trade_date", "quote_ret1": "ret1"})' in source

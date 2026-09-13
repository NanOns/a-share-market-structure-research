from datetime import date
from pathlib import Path

import duckdb
import pytest

from workbench_service.research_signal_evaluation import (
    CONTRACT_ID,
    EVAL_VERSION,
    ResearchSignalEvaluationTask,
    ResearchSignalOutcomeStore,
    SignalEvaluationError,
    build_equal_size_baselines,
    build_outcome_rows,
    episode_first_signals,
    signal_identity_hash,
)
from workbench_service.research_context import ResearchContextReader
from workbench_service.research_queries import ResearchQueries
from workbench_service.research_runs import ResearchRunStore


ROOT = Path(__file__).resolve().parents[2]


SESSIONS = ["2026-09-10", "2026-09-11", "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17"]


def signal(**updates):
    value = {
        "signal_run_id": "run-1",
        "sector_id": "THEME:A",
        "episode_id": "episode-a",
        "signal_date": "2026-09-10",
        "sector_type": "THEME",
        "potential_eligible": True,
        "current_eligible": False,
        "potential_branch": "BASE_BUILD",
        "algorithm_version": "v3",
        "parameter_hash": "params-1",
        "snapshot_id": "snap-1",
        "membership_snapshot_id": "members-1",
        "evaluation_basis": "HISTORICAL_RECONSTRUCTED",
    }
    value.update(updates)
    return value


def future_rows(current_dates=("2026-09-11", "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17"), current_on=()):
    return [{"sector_id": "THEME:A", "trade_date": item, "current_eligible": item in current_on} for item in current_dates]


def prices():
    return [
        {"security_id": "S1", "trade_date": "2026-09-10", "adj_close": 10},
        {"security_id": "S1", "trade_date": "2026-09-14", "adj_close": 11},
        {"security_id": "S1", "trade_date": "2026-09-15", "adj_close": 11},
        {"security_id": "S1", "trade_date": "2026-09-16", "adj_close": 12},
        {"security_id": "S1", "trade_date": "2026-09-17", "adj_close": 12},
        {"security_id": "S2", "trade_date": "2026-09-10", "adj_close": 20},
        {"security_id": "S2", "trade_date": "2026-09-14", "adj_close": 21},
        {"security_id": "S2", "trade_date": "2026-09-15", "adj_close": 21},
        {"security_id": "S2", "trade_date": "2026-09-16", "adj_close": 22},
        {"security_id": "S2", "trade_date": "2026-09-17", "adj_close": 22},
    ]


def test_first_signal_deduplicates_repeated_episode_days_and_excludes_signal_day_current():
    rows = episode_first_signals([signal(), signal(signal_date="2026-09-11"), signal(episode_id="episode-current", current_eligible=True, signal_date="2026-09-10")])
    assert len(rows) == 1
    assert rows[0]["episode_id"] == "episode-a"
    assert rows[0]["signal_date"] == date(2026, 9, 10)


def test_pending_and_observed_outcomes_keep_fixed_member_diagnostic():
    pending = build_outcome_rows([signal()], sessions=SESSIONS[:2], future_rows=future_rows(current_dates=("2026-09-11",)), members_by_episode={"episode-a": ["S1", "S2"]}, prices=prices(), as_of_date="2026-09-11")
    assert [row["status"] for row in pending] == ["PENDING", "PENDING"]
    observed = build_outcome_rows([signal()], sessions=SESSIONS, future_rows=future_rows(current_on=("2026-09-14",)), members_by_episode={"episode-a": ["S1", "S2"]}, prices=prices(), as_of_date="2026-09-17")
    assert observed[0]["status"] == "OBSERVED"
    assert observed[0]["confirmed_date"] == date(2026, 9, 14)
    assert observed[0]["lead_sessions"] == 2
    assert observed[0]["confirmed_within_h"] is True
    assert observed[0]["member_forward_median"] == pytest.approx((0.1 + 0.05) / 2)
    assert observed[0]["member_forward_coverage"] == 1.0
    assert observed[1]["confirmed_within_h"] is True


def test_missing_future_date_or_member_basis_is_data_gap_not_negative_confirmation():
    missing_date = build_outcome_rows([signal()], sessions=SESSIONS, future_rows=future_rows(current_dates=("2026-09-11", "2026-09-14")), members_by_episode={"episode-a": ["S1"]}, prices=prices(), as_of_date="2026-09-17")
    assert all(row["status"] == "DATA_GAP" for row in missing_date)
    assert any("DUE_DATE_DATA_MISSING" in row["evidence"]["status_reasons"] for row in missing_date)
    missing_member_basis = build_outcome_rows([signal()], sessions=SESSIONS, future_rows=future_rows(), members_by_episode={"episode-a": None}, prices=prices(), as_of_date="2026-09-17")
    assert all(row["status"] == "DATA_GAP" for row in missing_member_basis)
    assert all("MEMBER_BASIS_UNKNOWN" in row["evidence"]["status_reasons"] for row in missing_member_basis)


def test_unknown_future_current_state_is_data_gap_not_false_confirmation():
    rows = future_rows()
    rows[0]["current_eligible"] = None
    outcomes = build_outcome_rows([signal()], sessions=SESSIONS, future_rows=rows, members_by_episode={"episode-a": ["S1", "S2"]}, prices=prices(), as_of_date="2026-09-17")
    assert all(row["status"] == "DATA_GAP" for row in outcomes)
    assert all("CURRENT_STATE_DATA_MISSING" in row["evidence"]["status_reasons"] for row in outcomes)


def test_future_payload_cannot_change_signal_hash():
    base = signal()
    with_future = {**base, "t_plus_5_current": True, "future_return": 0.25, "outcome_status": "OBSERVED"}
    assert signal_identity_hash(base) == signal_identity_hash(with_future)


def test_three_baselines_use_same_day_type_and_target_equal_size():
    targets = [signal(sector_id="THEME:A", episode_id="ea"), signal(sector_id="THEME:B", episode_id="eb")]
    universe = [
        {"sector_id": "THEME:A", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": 0.90, "dq5_3": 0.10},
        {"sector_id": "THEME:B", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": 0.80, "dq5_3": 0.20},
        {"sector_id": "THEME:C", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": 0.70, "dq5_3": 0.30},
        {"sector_id": "THEME:D", "trade_date": "2026-09-10", "sector_type": "THEME", "current_eligible": False, "potential_eligible": True, "q20": 0.60, "dq5_3": 0.40},
        {"sector_id": "INDUSTRY:X", "trade_date": "2026-09-10", "sector_type": "INDUSTRY", "current_eligible": False, "potential_eligible": True, "q20": 0.99, "dq5_3": 0.99},
    ]
    baselines = build_equal_size_baselines(targets, universe)
    assert all(len(baselines[name]) == 2 for name in ("NON_CURRENT_QUALIFIED", "Q20_NON_CURRENT", "DQ5_3_NON_CURRENT"))
    assert [row["sector_id"] for row in baselines["Q20_NON_CURRENT"]] == ["THEME:C", "THEME:D"]
    assert all(row["sector_id"].startswith("THEME:") for rows in baselines.values() for row in rows)


def test_outcome_store_is_idempotent_and_never_updates_signal_state():
    connection = duckdb.connect(":memory:")
    connection.execute("create table research_sector_signal_state(run_id varchar, sector_id varchar, lifecycle varchar)")
    connection.execute("insert into research_sector_signal_state values ('run-1','THEME:A','QUALIFIED')")
    outcome = build_outcome_rows([signal()], sessions=SESSIONS[:2], future_rows=future_rows(current_dates=("2026-09-11",)), members_by_episode={"episode-a": ["S1"]}, prices=prices(), as_of_date="2026-09-11")
    store = ResearchSignalOutcomeStore(connection)
    assert store.upsert(outcome) == {"inserted": 2, "updated": 0, "unchanged": 0}
    assert store.upsert(outcome) == {"inserted": 0, "updated": 0, "unchanged": 2}
    assert connection.execute("select count(*) from research_signal_outcomes").fetchone()[0] == 2
    assert connection.execute("select lifecycle from research_sector_signal_state").fetchone()[0] == "QUALIFIED"
    with pytest.raises(SignalEvaluationError, match="OUTCOME_IDENTITY_CONFLICT"):
        store.upsert([{**outcome[0], "episode_id": "episode-other"}])
    connection.close()


def test_task_can_persist_and_reports_effect_gate_without_claiming_effect():
    connection = duckdb.connect(":memory:")
    result = ResearchSignalEvaluationTask(connection).run(signal_rows=[signal()], sessions=SESSIONS[:2], future_rows=future_rows(current_dates=("2026-09-11",)), members_by_episode={"episode-a": ["S1"]}, prices=prices(), as_of_date="2026-09-11")
    assert result["contract_id"] == CONTRACT_ID
    assert result["eval_version"] == EVAL_VERSION
    assert result["sample_gate"]["status"] == "EFFECT_INSUFFICIENT"
    assert result["sample_gate"]["can_claim_effect"] is False
    assert connection.execute("select count(*) from research_signal_outcomes").fetchone()[0] == 2
    connection.close()


def test_read_only_query_exposes_pending_gate_and_v3_page_status():
    connection = duckdb.connect(":memory:")
    store = ResearchRunStore(connection)
    started = store.start({"job_type": "BUILD_RESEARCH_V3", "publication_id": "pub-eval", "trade_date": "2026-09-10", "algorithm_version": "v3", "parameter_hash": "p", "snapshot_id": "snap", "membership_snapshot_id": "members", "dependency_bindings": {}})
    store.complete(
        started["run_id"],
        sector_states=[{"sector_id": "THEME:A", "potential_eligible": True, "potential_branch": "BASE_BUILD", "quality": "READY"}],
        signal_states=[{"sector_id": "THEME:A", "episode_id": "episode-a", "first_seen_date": "2026-09-10", "lifecycle": "QUALIFIED", "history_complete": False}],
    )
    context = ResearchContextReader().resolve_request("pub-eval", "2026-09-10", connection=connection)
    result = ResearchQueries().signal_evaluation(context["context_id"], connection=connection)
    assert result["status"] == "PENDING"
    assert result["sample_gate"]["display_status"] == "规则观察·效果验证中"
    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    assert 'id="evaluation-heading"' in page
    assert "/api/v3/research/evaluation" in page
    assert "规则观察·效果验证中" in page
    connection.close()

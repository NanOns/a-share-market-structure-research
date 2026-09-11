from datetime import date
from pathlib import Path

import pytest

from workbench_service.app import Api
from workbench_service.window_planner import CONTRACT_VERSION, load_dependencies, plan_window


ROOT = Path(__file__).parents[2]


def test_window_plan_uses_longest_dependency_and_separates_output_from_read_window():
    sessions = [date(2026, 1, 1) + __import__('datetime').timedelta(days=i) for i in range(300)]
    sessions = [value for value in sessions if value.weekday() < 5]
    plan = plan_window(sessions, cutoff_date=sessions[-1], output_days=50, dependencies=load_dependencies(ROOT))
    assert plan["contract_version"] == CONTRACT_VERSION
    assert plan["output_days"] == 50
    assert plan["required_history"] == 100
    assert sessions.index(date.fromisoformat(plan["output_start"])) - sessions.index(date.fromisoformat(plan["read_start"])) == 100
    high = next(item for item in plan["domains"] if item["domain"] == "high")
    assert high["windows"] == [20, 30, 60, 100]
    assert high["required_history"] == 100


def test_window_plan_reports_missing_observed_sessions_without_filling_them():
    sessions = [date(2026, 1, 2) + __import__('datetime').timedelta(days=i) for i in range(15)]
    sessions = [value for value in sessions if value.weekday() < 5]
    observed = sessions[:-1]
    plan = plan_window(sessions, cutoff_date=sessions[-1], output_days=5, observed_sessions=observed, dependencies=load_dependencies(ROOT))
    assert plan["missing_dates"] == [sessions[-1].isoformat()]
    assert plan["field_coverage"]["input"] < 1
    assert all(item["analysis_capability"] == "NOT_BUILT" for item in plan["domains"])


def test_window_plan_validates_maximum_output_window():
    with pytest.raises(ValueError, match="OUTPUT_DAYS_OUT_OF_RANGE"):
        plan_window([date(2026, 1, 1)], cutoff_date=date(2026, 1, 1), output_days=251)


def test_api03_returns_publication_bound_plan():
    api = Api(ROOT / "data/database/market_research.duckdb")
    publication = api.publications()["items"][0]["publication_id"]
    result = api.history_coverage(publication, 30)
    item = result["item"]
    assert result["publication_id"] == publication
    assert item["output_days_requested"] == 30
    assert item["required_history"] == 100
    assert item["snapshot_id"] == api._analysis_bindings(publication)["LOCAL_RECONSTRUCTED"]["snapshot_id"]
    assert item["snapshot_capability"] == "AVAILABLE"
    assert item["api_contract"] == "workbench-api-v2.1"
    assert item["resolved_basis"] == "RECONSTRUCTED"
    assert item["supported_basis"] == ["OBSERVED", "RECONSTRUCTED"]

from datetime import date, timedelta

from workbench_service.build_planner import (
    CONTRACT_VERSION,
    DependencySummary,
    build_plan,
)


def _sessions(count=140):
    values = []
    cursor = date(2026, 1, 2)
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return values


def _summary(sessions, *, quote=None, relationships=None, sector_names=None, hierarchy=None, parameters=None, adjustments=None):
    return DependencySummary(
        trading_days=tuple(sessions),
        quote=quote or {},
        relationships=relationships or {},
        sector_names=sector_names or {},
        hierarchy=hierarchy or {},
        parameters=parameters or {},
        adjustments=adjustments or {},
    )


def _kwargs(sessions):
    return {
        "sessions": sessions,
        "security_ids": ["A", "B", "C"],
        "sector_ids": ["S1"],
        "security_to_sectors": {"A": ["S1"], "B": ["S1"], "C": ["S1"]},
        "sector_members": {"S1": ["A", "B", "C"]},
        "cutoff_date": sessions[-1],
    }


def test_new_trading_day_only_appends_the_new_day():
    sessions = _sessions()
    previous = _summary(sessions[:-1])
    current = _summary(sessions)
    plan = build_plan(previous, current, **_kwargs(sessions))

    assert plan["contract_version"] == CONTRACT_VERSION
    assert plan["status"] == "PLANNED"
    assert {item["trade_date"] for item in plan["tasks"]} == {sessions[-1]}
    assert {item["domain"] for item in plan["tasks"]} >= {"technical", "strength", "high", "member_state", "structure", "summary"}


def test_sector_name_change_does_not_recompute_stock_indicators():
    sessions = _sessions()
    previous = _summary(sessions, sector_names={"S1": "name-v1"})
    current = _summary(sessions, sector_names={"S1": "name-v2"})
    plan = build_plan(previous, current, **_kwargs(sessions))

    assert {item["domain"] for item in plan["tasks"]} == {"sector_base"}
    assert all(item["reason_codes"] == ["SECTOR_NAME_CHANGE"] for item in plan["tasks"])


def test_relation_change_stays_inside_affected_sector_and_has_no_technical_work():
    sessions = _sessions()
    key = f"{sessions[50]}|S1|A"
    previous = _summary(sessions, relationships={key: "edge-v1"})
    current = _summary(sessions, relationships={key: "edge-v2"})
    plan = build_plan(previous, current, **_kwargs(sessions))

    assert {item["domain"] for item in plan["tasks"]} <= {"sector_base", "sector_cycle", "mainline", "member_state", "structure", "summary"}
    assert not any(item["domain"] in {"quote", "technical", "strength", "high"} for item in plan["tasks"])
    assert {item["sector_id"] for item in plan["tasks"]} == {"S1"}


def test_price_revision_replans_rps_cross_section_and_propagates_state():
    sessions = _sessions()
    changed_day = sessions[50]
    key = f"{changed_day}|A"
    previous = _summary(sessions, quote={key: "price-v1"})
    current = _summary(sessions, quote={key: "price-v2"})
    plan = build_plan(previous, current, **_kwargs(sessions))

    strength = [item for item in plan["tasks"] if item["domain"] == "strength"]
    strength_by_date = {}
    for item in strength:
        strength_by_date.setdefault(item["trade_date"], set()).add(item["security_id"])
    assert strength_by_date
    assert all(ids == {"A", "B", "C"} for ids in strength_by_date.values())
    assert min(strength_by_date) == changed_day
    assert max(strength_by_date) == sessions[50 + 60 - 1]

    technical = [item for item in plan["tasks"] if item["domain"] == "technical"]
    assert {item["security_id"] for item in technical} == {"A"}
    assert all(item["security_id"] != "B" for item in plan["tasks"] if item["domain"] in {"high", "structure", "summary"})
    assert any(item["reason_codes"] == ["RPS_CROSS_SECTION"] for item in strength)


def test_identical_dependency_input_has_no_work_and_is_idempotent():
    sessions = _sessions()
    summary = _summary(sessions, quote={f"{sessions[20]}|A": "price"})
    first = build_plan(summary, summary, **_kwargs(sessions))
    second = build_plan(summary.to_payload(), summary.to_payload(), **_kwargs(sessions))

    assert first["status"] == "NO_WORK"
    assert first["tasks"] == []
    assert first["events"] == []
    assert first["plan_id"] == second["plan_id"]


def test_adjustment_anchor_change_reaches_cutoff_without_rewriting_unrelated_stock_history():
    sessions = _sessions()
    changed_day = sessions[70]
    key = f"A|{changed_day}"
    previous = _summary(sessions, adjustments={key: "anchor-v1"})
    current = _summary(sessions, adjustments={key: "anchor-v2"})
    plan = build_plan(previous, current, **_kwargs(sessions))

    technical = [item for item in plan["tasks"] if item["domain"] == "technical"]
    assert {item["security_id"] for item in technical} == {"A"}
    assert max(item["trade_date"] for item in technical) == sessions[-1]
    strength_dates = {item["trade_date"] for item in plan["tasks"] if item["domain"] == "strength"}
    assert min(strength_dates) == changed_day
    assert max(strength_dates) == sessions[-1]

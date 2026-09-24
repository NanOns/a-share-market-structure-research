import pytest

from src.focus_tracker.predicate_requirements import plan_predicate_requirements
from src.focus_tracker.predicates import compile_v3_3_invalidation


def test_launch_requires_two_sessions_and_frozen_price():
    plan = plan_predicate_requirements(compile_v3_3_invalidation("LAUNCH_CONFIRM", {}))
    assert plan.required_sessions == 2
    assert plan.required_fields == {"structure_break_v3", "close", "has_actual_bar",
                                    "session_state"}
    assert plan.required_frozen_facts == {"frozen_phh20"}


def test_recovery_requires_dynamic_ma_history_and_rps_delta():
    plan = plan_predicate_requirements(compile_v3_3_invalidation(
        "RECOVERY_TURN", {"reclaimed_ma_kind": "MA20"}))
    assert plan.required_sessions == 21
    assert plan.required_fields == {"close", "has_actual_bar", "session_state", "dynamic_ma20",
                                    "rps20_delta3"}
    assert plan.required_frozen_facts == {"reclaimed_ma_kind"}


def test_nested_consecutive_windows_overlap():
    ast = {"op": "CONSECUTIVE", "sessions": 3, "predicate": {
        "op": "CONSECUTIVE", "sessions": 2, "predicate": {
            "op": "LT", "field": "close", "mode": "CURRENT_FIELD", "value": 10}}}
    assert plan_predicate_requirements(ast).required_sessions == 4


@pytest.mark.parametrize("ast", [
    {"op": "CONSECUTIVE", "sessions": True, "predicate": {}},
    {"op": "OR", "args": []},
    {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
     "anchor": "x", "anchor_mode": "UNSUPPORTED"},
])
def test_invalid_ast_fails_closed(ast):
    with pytest.raises(ValueError):
        plan_predicate_requirements(ast)

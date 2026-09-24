from datetime import date, timedelta

import pytest

from src.focus_tracker.predicates import Tri, evaluate
from src.focus_tracker.session_gap_semantics import (
    SessionState, assess_gap_sequence, classify_session_state)


def test_session_classification_keeps_suspension_gap_and_source_unavailable_distinct():
    assert classify_session_state({"has_actual_bar": True}) == SessionState.ACTUAL_BAR
    assert classify_session_state({"has_actual_bar": False,
                                   "missing_state": "CONFIRMED_SUSPENSION",
                                   "trade_status_known": True,
                                   "is_synthetic_fill": True}) == SessionState.SUSPENDED
    assert classify_session_state({"has_actual_bar": False,
                                   "missing_state": "MISSING_DATA"}) == SessionState.DATA_GAP
    assert classify_session_state({"has_actual_bar": False,
                                   "missing_state": "FILE_MISSING"}) == SessionState.SOURCE_UNAVAILABLE
    assert classify_session_state(None) == SessionState.SOURCE_UNAVAILABLE


def test_unverified_suspension_markers_fail_closed():
    with pytest.raises(ValueError, match="status evidence inconsistent"):
        classify_session_state({"has_actual_bar": False,
                                "missing_state": "CONFIRMED_SUSPENSION",
                                "trade_status_known": False,
                                "is_synthetic_fill": True})


@pytest.mark.parametrize("operation", ["CONSECUTIVE", "ROLLING"])
def test_session_predicates_do_not_skip_confirmed_suspension(operation):
    result = assess_gap_sequence(operation=operation,
                                 states=[SessionState.ACTUAL_BAR,
                                         SessionState.SUSPENDED,
                                         SessionState.ACTUAL_BAR])
    assert not result.usable
    assert result.reason == "SUSPENDED"
    assert result.suspended_positions == (1,)


def test_price_path_bridges_only_internal_confirmed_suspensions():
    result = assess_gap_sequence(operation="PATH", states=[
        SessionState.ACTUAL_BAR, SessionState.SUSPENDED, SessionState.ACTUAL_BAR])
    assert result.usable
    assert result.suspended_positions == (1,)
    assert not assess_gap_sequence(operation="PATH", states=[
        SessionState.ACTUAL_BAR, SessionState.DATA_GAP,
        SessionState.ACTUAL_BAR]).usable
    assert not assess_gap_sequence(operation="PATH", states=[
        SessionState.SUSPENDED, SessionState.ACTUAL_BAR]).usable


@pytest.mark.parametrize("state", ["SUSPENDED", "DATA_GAP", "SOURCE_UNAVAILABLE"])
def test_consecutive_predicate_is_unknown_with_auditable_gap_reason(state):
    day1 = date(2026, 9, 23)
    day2 = day1 + timedelta(days=1)
    result, evidence = evaluate(
        {"op": "CONSECUTIVE", "sessions": 2,
         "predicate": {"op": "GT", "field": "close",
                       "mode": "CURRENT_FIELD", "value": 0}},
        trade_date=day2, sessions=[day1, day2],
        facts_by_date={day1: {"has_actual_bar": True, "close": 10},
                       day2: {"has_actual_bar": False, "close": None,
                              "session_state": state}},
        frozen_signal={}, frozen_episode={})
    assert result == Tri.UNKNOWN
    assert evidence["children"][1]["reason"] == state
    assert evidence["session_gap_contract_id"] == "FOCUS_SESSION_GAP_SEMANTICS_V1"

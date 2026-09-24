import pytest

from focus_tracker.path_state_v2 import (classify_stock_v2, resolve_evidence_v2,
                                         resolve_v2)
from focus_tracker.predicates import Tri
from focus_tracker.states import PathDecision


def test_unresolved_higher_priority_keeps_confirmed_candidate():
    result = classify_stock_v2(
        {"has_actual_bar": True, "source_extended": True},
        invalidation=Tri.UNKNOWN,
        applicable=frozenset({"STRUCTURE_DAMAGED", "TOO_EXTENDED"}))
    assert result.resolved_primary_state is None
    assert result.best_confirmed_state == "TOO_EXTENDED"
    assert result.higher_priority_unresolved == ("STRUCTURE_DAMAGED",)
    assert result.path_resolution == "PARTIAL"
    assert result.confirmed_secondary_states == ("TOO_EXTENDED",)


def test_lower_priority_unknown_does_not_block_confirmed_primary():
    result = resolve_v2(PathDecision("STRUCTURE_DAMAGED", "INVALIDATED", (), (),
                                     {"STRUCTURE_DAMAGED": "TRUE",
                                      "TREND_ACCELERATING": "UNKNOWN"}))
    assert result.resolved_primary_state == "STRUCTURE_DAMAGED"
    assert result.higher_priority_unresolved == ()
    assert result.path_resolution == "READY"


def test_false_higher_priority_allows_lower_true_primary():
    result = resolve_v2(PathDecision("TREND_ACCELERATING", "VALID", (), (),
                                     {"STRUCTURE_DAMAGED": "FALSE",
                                      "TREND_ACCELERATING": "TRUE"}))
    assert result.path_resolution == "READY"
    assert result.resolved_primary_state == "TREND_ACCELERATING"


def test_higher_priority_true_wins_over_lower_true():
    result = resolve_v2(PathDecision("STRUCTURE_DAMAGED", "INVALIDATED", (), (),
                                     {"STRUCTURE_DAMAGED": "TRUE",
                                      "TREND_ACCELERATING": "TRUE"}))
    assert result.path_resolution == "READY"
    assert result.resolved_primary_state == "STRUCTURE_DAMAGED"
    assert result.confirmed_secondary_states == (
        "STRUCTURE_DAMAGED", "TREND_ACCELERATING")


def test_resolution_uses_versioned_order_not_json_object_key_order():
    evidence = {"TREND_ACCELERATING": "TRUE",
                "STRUCTURE_DAMAGED": "UNKNOWN"}
    result = resolve_v2(PathDecision("DATA_UNAVAILABLE", "UNKNOWN", (), (), evidence))
    assert result.path_resolution == "PARTIAL"
    assert result.best_confirmed_state == "TREND_ACCELERATING"
    assert result.higher_priority_unresolved == ("STRUCTURE_DAMAGED",)


def test_no_confirmed_predicate_with_gap_is_unavailable():
    result = resolve_v2(PathDecision("DATA_UNAVAILABLE", "UNKNOWN", (), (),
                                     {"actual_bar": "UNKNOWN"}))
    assert result.resolved_primary_state is None
    assert result.best_confirmed_state is None
    assert result.path_resolution == "UNAVAILABLE"


def test_all_false_is_ready_unclassified():
    result = resolve_v2(PathDecision("UNCLASSIFIED", "VALID", (), (),
                                     {"STRUCTURE_DAMAGED": "FALSE",
                                      "TOO_EXTENDED": "NOT_APPLICABLE"}))
    assert result.resolved_primary_state is None
    assert result.path_resolution == "READY"


def test_same_priority_confirmed_states_are_ambiguous():
    resolved, best, unresolved, resolution, confirmed = resolve_evidence_v2(
        evidence={"A": "TRUE", "B": "TRUE", "C": "FALSE"},
        priority_groups=(("A", "B"), ("C",)))
    assert resolved is None
    assert best is None
    assert unresolved == ()
    assert resolution == "AMBIGUOUS"
    assert confirmed == ("A", "B")


def test_higher_unknown_with_same_tier_confirmed_states_is_partial():
    resolved, best, unresolved, resolution, confirmed = resolve_evidence_v2(
        evidence={"TOP": "UNKNOWN", "A": "TRUE", "B": "TRUE"},
        priority_groups=(("TOP",), ("A", "B")))
    assert resolved is None
    assert best is None
    assert unresolved == ("TOP",)
    assert resolution == "PARTIAL"
    assert confirmed == ("A", "B")


def test_incomplete_priority_contract_is_rejected():
    with pytest.raises(ValueError, match="does not match priority contract"):
        resolve_evidence_v2(evidence={"A": "TRUE", "B": "FALSE"},
                            priority_groups=(("A",),))

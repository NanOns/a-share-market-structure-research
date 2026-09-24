from datetime import date

import pytest

from src.focus_tracker.contracts import FocusKey
from src.focus_tracker.lifecycle import Decision
from src.focus_tracker.materialize import StockFact
from src.focus_tracker.observation import assemble_observation
from src.focus_tracker.predicates import Tri


V3 = "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"
V33 = "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"
DAY = date(2026, 9, 22)


def _decision(family="V3_3_TODAY_CANDIDATE", membership="CANDIDATE"):
    key = FocusKey(family, "STOCK", "000001.SZ", "V3_3" if family.startswith("V3_3") else "V3_SHORTLIST")
    return Decision(key, membership, "NEW", "episode-1", None, (), "SOURCE_MEMBERSHIP")


def _fact(quality="READY"):
    return StockFact("000001.SZ", DAY, DAY, quality, "BAR" if quality == "READY" else "MISSING_DATA",
                     "10.00" if quality == "READY" else None, "0", "0.01", "-0.01",
                     "0", "0", "local-v1", "a" * 64)


def test_six_dimensions_keep_missing_factor_as_unknown():
    result = assemble_observation(decision=_decision(), source_contract_id=V33,
                                  stock_fact=_fact(), predicate_facts={},
                                  invalidation=Tri.UNKNOWN)
    assert (result.source_membership_state, result.membership_phase,
            result.validity_state, result.followup_state,
            result.current_path_state, result.lifetime_path_tags) == (
                "CANDIDATE", "NEW", "UNKNOWN", "ACTIVE_FOCUS",
                "DATA_UNAVAILABLE", ())
    assert result.evidence["path_predicates"]["STRUCTURE_DAMAGED"] == "UNKNOWN"
    assert result.evidence["validity_capability"]["status"] == "UNAVAILABLE"


def test_nonapplicable_structure_branch_is_explicit():
    result = assemble_observation(decision=_decision("V3_SHORTLIST_STOCK", "CURRENT"),
                                  source_contract_id=V3, stock_fact=_fact(),
                                  predicate_facts={}, invalidation=Tri.UNKNOWN)
    assert result.evidence["path_predicates"]["STRUCTURE_DAMAGED"] == "NOT_APPLICABLE"
    assert result.validity_state == "UNKNOWN"
    assert result.evidence["validity_capability"]["status"] == "NOT_APPLICABLE"


def test_price_fact_cannot_be_overridden_by_predicate_inputs():
    result = assemble_observation(decision=_decision(), source_contract_id=V33,
                                  stock_fact=_fact("DATA_UNAVAILABLE"),
                                  predicate_facts={"has_actual_bar": True,
                                                   "close": "99", "mfe": "1",
                                                   "invalidation_evidence": {
                                                       "contract_id": "FOCUS_INVALIDATION_AST_V2",
                                                       "result": "FALSE",
                                                       "ast_digest": "a" * 64}},
                                  invalidation=Tri.FALSE)
    assert result.current_path_state == "DATA_UNAVAILABLE"
    assert result.evidence["predicate_facts"]["close"] is None
    assert result.evidence["predicate_facts"]["has_actual_bar"] is False


def test_active_membership_cannot_be_marked_complete():
    with pytest.raises(ValueError, match="cannot complete"):
        assemble_observation(decision=_decision(), source_contract_id=V33,
                             stock_fact=_fact(), predicate_facts={},
                             invalidation=Tri.UNKNOWN, settlement_complete=True)


def test_unknown_high_priority_keeps_known_lower_priority_evidence():
    result = assemble_observation(decision=_decision(), source_contract_id=V33,
                                  stock_fact=_fact(),
                                  predicate_facts={"exited": True},
                                  invalidation=Tri.UNKNOWN)
    assert result.current_path_state == "DATA_UNAVAILABLE"
    assert result.evidence["path_predicates"]["STRUCTURE_DAMAGED"] == "UNKNOWN"
    assert result.evidence["path_predicates"]["EXITED_FOLLOW_UP"] == "TRUE"
    path_v2 = result.evidence["path_state_v2"]
    assert path_v2["contract_id"] == "FOCUS_PATH_STATE_V2"
    assert path_v2["resolved_primary_state"] is None
    assert path_v2["best_confirmed_state"] == "EXITED_FOLLOW_UP"
    assert path_v2["higher_priority_unresolved"] == ["STRUCTURE_DAMAGED"]
    assert path_v2["confirmed_secondary_states"] == ["EXITED_FOLLOW_UP"]
    assert path_v2["path_resolution"] == "PARTIAL"

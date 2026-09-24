import pytest

from src.focus_tracker.predicates import Tri
from src.focus_tracker.validity_capability import validity_capability


def test_v3_formal_rule_is_not_applicable():
    for family in ("V3_SHORTLIST_STOCK", "V3_SHORTLIST_INDIVIDUAL",
                   "V3_SECTOR_TRACK"):
        item = validity_capability(source_family=family, invalidation=Tri.UNKNOWN)
        assert item["status"] == "NOT_APPLICABLE"
        assert item["rule_contract_id"] is None
        assert len(item["digest"]) == 64


def test_v33_missing_window_is_unavailable():
    item = validity_capability(
        source_family="V3_3_TODAY_CANDIDATE", invalidation=Tri.UNKNOWN,
        invalidation_evidence={"result": "UNKNOWN", "children": [
            {"result": "FALSE"}, {"result": "UNKNOWN",
                                     "reason": "INSUFFICIENT_CALENDAR_SESSIONS"}]})
    assert item["status"] == "UNAVAILABLE"
    assert item["reason_codes"] == ["INSUFFICIENT_CALENDAR_SESSIONS"]


def test_v33_known_rule_result_is_applicable():
    for result in (Tri.TRUE, Tri.FALSE):
        item = validity_capability(source_family="V3_3_TODAY_CANDIDATE",
                                   invalidation=result,
                                   invalidation_evidence={
                                       "contract_id": "FOCUS_INVALIDATION_AST_V2",
                                       "result": result.value,
                                       "ast_digest": "a" * 64})
        assert item["status"] == "APPLICABLE"
        assert item["reason_codes"] == []


def test_v3_cannot_claim_executable_invalidation():
    with pytest.raises(ValueError, match="no executable"):
        validity_capability(source_family="V3_SECTOR_TRACK", invalidation=Tri.TRUE)


def test_known_result_without_rule_evidence_fails_closed():
    with pytest.raises(ValueError, match="evidence incomplete"):
        validity_capability(source_family="V3_3_TODAY_CANDIDATE",
                            invalidation=Tri.FALSE)

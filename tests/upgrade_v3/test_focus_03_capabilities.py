import pytest

from src.focus_tracker.source_capabilities import (applicable_path_predicates,
                                                   capability_evidence)


V3 = "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"
V33 = "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO"


def test_unpublished_extended_and_unstructured_v3_invalidation_are_not_applicable():
    stock = capability_evidence("V3_SHORTLIST_STOCK", V3)
    candidate = capability_evidence("V3_3_TODAY_CANDIDATE", V33)
    sector = capability_evidence("V3_SECTOR_TRACK", V3)
    assert stock["predicates"]["TOO_EXTENDED"] == "NOT_APPLICABLE"
    assert stock["predicates"]["STRUCTURE_DAMAGED"] == "NOT_APPLICABLE"
    assert candidate["predicates"]["STRUCTURE_DAMAGED"] == "APPLICABLE"
    assert sector["predicates"]["SECTOR_STRUCTURE_DAMAGED"] == "NOT_APPLICABLE"


def test_unknown_source_contract_fails_closed():
    with pytest.raises(ValueError, match="unregistered"):
        applicable_path_predicates("V3_SHORTLIST_STOCK", "future-contract")

import pytest

from src.focus_tracker.source_capabilities import (applicable_path_predicates,
                                                   capability_evidence,
                                                   require_runtime_fact_providers)


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


def test_unprovided_paths_are_not_advertised():
    candidate = capability_evidence("V3_3_TODAY_CANDIDATE", V33)
    sector = capability_evidence("V3_SECTOR_TRACK", V3)
    assert candidate["contract_id"] == "FOCUS_SOURCE_PATH_CAPABILITIES_V3"
    assert candidate["predicates"]["TREND_ACCELERATING"] == "NOT_APPLICABLE"
    assert candidate["predicates"]["PULLBACK_HEALTHY"] == "APPLICABLE"
    assert sector["predicates"]["SECTOR_ACCELERATING"] == "NOT_APPLICABLE"
    assert sector["predicates"]["SECTOR_PERSISTENT"] == "APPLICABLE"


def test_runtime_missing_provider_is_contract_error_but_null_value_is_allowed():
    facts = {"has_actual_bar": False, "drawdown_current": None,
             "close": None, "ma20": None,
             "structure_break": None, "exited": False}
    require_runtime_fact_providers("V3_3_TODAY_CANDIDATE", V33, facts,
                                   invalidation_supplied=True)
    del facts["structure_break"]
    with pytest.raises(ValueError, match="CAPABILITY_CONTRACT_BROKEN:PULLBACK_HEALTHY"):
        require_runtime_fact_providers("V3_3_TODAY_CANDIDATE", V33, facts,
                                       invalidation_supplied=True)


def test_static_claim_without_registered_provider_is_contract_error(monkeypatch):
    from src.focus_tracker import source_capabilities as caps
    monkeypatch.setitem(caps._MAPPING, ("V3_3_TODAY_CANDIDATE", V33),
                        frozenset({"TREND_ACCELERATING"}))
    with pytest.raises(ValueError, match="CAPABILITY_CONTRACT_BROKEN:TREND_ACCELERATING"):
        applicable_path_predicates("V3_3_TODAY_CANDIDATE", V33)

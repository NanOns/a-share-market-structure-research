import pytest

from workbench_service.research_v3_contracts import (
    ContractValidationError,
    load_contract_bundle,
    parameter_hash,
    validate_contract_bundle,
    validate_object,
    validate_reason,
    validate_request,
)


def _sector_card(**overrides):
    value = {
        "sector_id": "sector-1",
        "name": "测试板块",
        "type": "CONCEPT",
        "track": "CURRENT",
        "branch": None,
        "lifecycle": "CONFIRMED",
        "signal_date": "2026-09-10",
        "m1": None,
        "b1": None,
        "rel1": None,
        "amount_sum": None,
        "amount_coverage": None,
        "amount_A": None,
        "quote_coverage": None,
        "member_count": 0,
        "today_leader_count": 0,
        "early_watch_count": 0,
        "reasons": [],
        "waiting_for": [],
        "invalid_if": [],
        "preview_members": [],
        "quote_as_of": None,
        "local_as_of": "2026-09-10",
    }
    value.update(overrides)
    return value


def test_p00_03_contract_bundle_is_frozen_and_single_sourced():
    bundle = load_contract_bundle()
    config = bundle["config"]

    assert validate_contract_bundle(bundle) is bundle
    assert config["parameter_hash"] == parameter_hash(config)
    assert config["contracts"]["features"] == "RESEARCH_FEATURES_PREVIEW_1"
    assert config["thresholds"]["coverage"]["min_amount_coverage"] == 0.8
    assert config["thresholds"]["current"]["b1_gte"] == 0.6
    assert config["thresholds"]["potential_branches"]["BREADTH_BUILD"]["amount_A_gte"] == 1.05
    assert config["thresholds"]["stock_signals"]["risk"]["extension_z20_gte"] == 1.5
    assert config["null_logic"]["price_rounding"] == "NONE_BEFORE_COMPARISON"


def test_p00_03_reason_catalog_labels_are_stable():
    bundle = load_contract_bundle()
    reasons = bundle["reasons"]["reasons"]
    assert len(reasons) == len({item["code"] for item in reasons})
    assert len(reasons) == len({item["label"] for item in reasons})
    assert {item["code"] for item in reasons} >= {
        "BREADTH_IMPROVING",
        "CURRENT_QUALIFIED",
        "EARLY_WATCH",
        "TODAY_LEADER",
        "AMOUNT_A_MISSING",
    }


def test_p00_03_synthetic_fixture_set_is_not_market_evidence():
    bundle = load_contract_bundle()
    cases = bundle["fixtures"]["cases"]
    assert bundle["fixtures"]["is_synthetic"] is True
    assert bundle["fixtures"]["not_market_data"] is True
    assert {case["fixture_id"] for case in cases} == {
        "S_CURRENT",
        "S_BUILD",
        "S_BASE",
        "S_FALSE",
        "S_NULL",
        "STOCK_SETUP",
        "STOCK_HIGH",
    }
    setup = next(case for case in cases if case["fixture_id"] == "STOCK_SETUP")
    assert setup["expected"]["setup"] is True
    assert setup["expected"]["early_watch"] is True
    assert setup["input"]["ret1"] < 0
    high = next(case for case in cases if case["fixture_id"] == "STOCK_HIGH")
    assert high["expected"]["today_leader"] is True
    assert high["expected"]["current_research"] is False


def test_p00_03_request_schema_rejects_invalid_enum_and_unknown_field():
    valid = {"context_id": "fixture-context", "track": "POTENTIAL", "page": 1, "page_size": 20}
    assert validate_request("research_list", valid)["track"] == "POTENTIAL"

    with pytest.raises(ContractValidationError, match="ENUM_INVALID|TYPE_INVALID"):
        validate_request("research_list", {**valid, "track": "INVALID_TRACK"})
    with pytest.raises(ContractValidationError, match="UNKNOWN_FIELD"):
        validate_request("research_list", {**valid, "unexpected": "must-fail"})
    with pytest.raises(ContractValidationError, match="REQUIRED_FIELD_MISSING"):
        validate_request("research_list", {"context_id": "fixture-context", "page": 1})


def test_p00_03_dto_rejects_null_nonnullable_and_reason_label_drift():
    bundle = load_contract_bundle()
    with pytest.raises(ContractValidationError, match="NULL_NOT_ALLOWED"):
        validate_object({"status": "READY", "total_eligible": None, "returned_count": 0, "total": 0, "page": 1, "page_size": 20, "has_more": False, "items": [], "context": None}, "PageEnvelope", bundle)
    with pytest.raises(ContractValidationError, match="REASON_LABEL_MISMATCH"):
        validate_reason({"code": "BREADTH_IMPROVING", "label": "错误标签", "observed": 0.12, "operator": ">=", "threshold": 0.1, "unit": "RATIO", "as_of": "2026-09-10"}, bundle)
    assert validate_reason({"code": "BREADTH_IMPROVING", "label": "上涨宽度改善", "observed": 0.12, "operator": ">=", "threshold": 0.1, "unit": "RATIO", "as_of": "2026-09-10"}, bundle)["code"] == "BREADTH_IMPROVING"


def test_c20_01_date_requires_real_calendar_day_and_accepts_leap_day():
    bundle = load_contract_bundle()
    valid = {"code": "BREADTH_IMPROVING", "label": "上涨宽度改善", "observed": 0.12, "operator": ">=", "threshold": 0.1, "unit": "RATIO", "as_of": "2024-02-29"}
    assert validate_object(valid, "Reason", bundle)["as_of"] == "2024-02-29"
    for invalid in ("2026-02-29", "2026-99-99", "2026-2-9"):
        with pytest.raises(ContractValidationError, match="TYPE_INVALID"):
            validate_object({**valid, "as_of": invalid}, "Reason", bundle)


def test_c20_01_timestamp_requires_iso8601_timezone():
    bundle = load_contract_bundle()
    assert validate_object(_sector_card(quote_as_of="2026-09-10T12:30:00+08:00"), "SectorCard", bundle)["quote_as_of"] == "2026-09-10T12:30:00+08:00"
    for invalid in ("NOT A TIMESTAMP", "2026-09-10 12:30:00+08:00", "2026-09-10T12:30:00", "2026-99-99T12:30:00+08:00"):
        with pytest.raises(ContractValidationError, match="TYPE_INVALID"):
            validate_object(_sector_card(quote_as_of=invalid), "SectorCard", bundle)


def test_c20_01_numbers_and_scalar_numbers_must_be_finite():
    bundle = load_contract_bundle()
    for invalid in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ContractValidationError, match="TYPE_INVALID"):
            validate_object(_sector_card(m1=invalid), "SectorCard", bundle)
        with pytest.raises(ContractValidationError, match="TYPE_INVALID"):
            validate_object({"code": "BREADTH_IMPROVING", "label": "上涨宽度改善", "observed": invalid, "operator": ">=", "threshold": 0.1, "unit": "RATIO", "as_of": "2026-09-10"}, "Reason", bundle)
    assert validate_object(_sector_card(m1=1.25), "SectorCard", bundle)["m1"] == 1.25
    assert validate_object(_sector_card(m1=10**400), "SectorCard", bundle)["m1"] == 10**400

from decimal import Decimal

import pytest

from workbench_analysis.limit_rules import (
    LimitRuleError,
    LimitStateService,
    compute_limit_prices,
    round_to_tick,
    validate_rule_versions,
)


def _rules():
    return [
        {"rule_id": "A-10", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "valid_from": "2026-09-01", "valid_to": "2026-09-30", "limit_ratio": "0.10", "tick": "0.01", "rounding_mode": "HALF_UP", "special_period_policy": {}, "source_ref": "fixture:standard"},
        {"rule_id": "A-ST-05", "exchange": "SH", "board": "MAIN", "risk_status": "ST", "valid_from": "2026-09-01", "valid_to": "2026-09-30", "limit_ratio": "0.05", "tick": "0.01", "rounding_mode": "HALF_UP", "special_period_policy": {}, "source_ref": "fixture:st"},
        {"rule_id": "A-NEW", "exchange": "SH", "board": "MAIN", "risk_status": "NEW", "valid_from": "2026-09-01", "valid_to": "2026-09-30", "limit_ratio": None, "tick": "0.01", "rounding_mode": "HALF_UP", "special_period_policy": {"limit_state": "NO_LIMIT"}, "source_ref": "fixture:new"},
    ]


def test_decimal_prices_and_exact_limit_state_have_no_float_tolerance():
    service = LimitStateService(_rules())
    result = service.evaluate({"security_id": "SH.600001", "trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10.00", "close": "11.00"})
    assert result["limit_up_price"] == Decimal("11.00") and result["limit_down_price"] == Decimal("9.00")
    assert result["limit_state"] == "LIMIT_UP" and result["streak_known"] is True
    assert service.evaluate({"security_id": "SH.600001", "trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10.00", "close": "11.001"})["limit_state"] == "NOT_LIMIT"


def test_st_rule_is_selected_by_versioned_risk_status_and_new_period_is_unknown_not_none():
    service = LimitStateService(_rules())
    st = service.evaluate({"trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "ST", "quote_prev_close": "10", "close": "10.50"})
    new = service.evaluate({"trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NEW", "quote_prev_close": "10", "close": "12"})
    assert st["rule_id"] == "A-ST-05" and st["limit_state"] == "LIMIT_UP"
    assert new["limit_state"] == "UNKNOWN" and new["reason"] == "NO_APPLICABLE_LIMIT_RULE"


def test_missing_rule_reference_and_ex_rights_are_unknown():
    service = LimitStateService(_rules())
    missing = service.evaluate({"trade_date": "2026-09-08", "exchange": "SZ", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10", "close": "11"})
    ex_rights = service.evaluate({"trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10", "close": "11", "ex_rights_reference_unknown": True})
    assert missing["limit_state"] == "UNKNOWN" and missing["reason"] == "RULE_NOT_FOUND"
    assert ex_rights["limit_state"] == "UNKNOWN" and ex_rights["reason"] == "EX_RIGHTS_REFERENCE_UNKNOWN"


def test_string_boolean_flags_are_parsed_explicitly():
    service = LimitStateService(_rules())
    not_suspended = service.evaluate({"trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10", "close": "10", "suspended": "false"})
    invalid = service.evaluate({"trade_date": "2026-09-08", "exchange": "SH", "board": "MAIN", "risk_status": "NORMAL", "quote_prev_close": "10", "close": "10", "suspended": "maybe"})
    assert not_suspended["limit_state"] == "NOT_LIMIT"
    assert invalid["limit_state"] == "UNKNOWN" and invalid["reason"] == "SUSPENDED_INVALID"


def test_rule_ranges_must_not_overlap_and_rounding_is_decimal():
    overlap = _rules()[:1] + [{**_rules()[0], "rule_id": "A-10-OVERLAP", "valid_from": "2026-09-15"}]
    with pytest.raises(LimitRuleError, match="OVERLAP"):
        validate_rule_versions(overlap)
    assert round_to_tick(Decimal("10.005"), Decimal("0.01"), "HALF_UP") == Decimal("10.01")
    standard = next(rule for rule in validate_rule_versions(_rules()) if rule.rule_id == "A-10")
    up, down = compute_limit_prices("10.00", standard)
    assert (up, down) == (Decimal("11.00"), Decimal("9.00"))

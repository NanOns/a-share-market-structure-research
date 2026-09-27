from __future__ import annotations

from decimal import Decimal
from workbench_analysis.price_limit_exception_gate import is_range_exception_audit_closed
from workbench_analysis.special_price_phases import (
    SpecialPhaseEvent, SpecialPricePhase, official_reference, phase_limit_ratio,
    resolve_phase, special_limit_prices,
)


def phase_event(phase=SpecialPricePhase.DELISTING_FIRST_DAY, **overrides):
    row = {
        "security_id": "SEC-1", "trade_date": "2024-06-06", "phase": phase.value,
        "source_ref": "https://exchange.example/notice", "source_capture_sha256": "a" * 64,
        "effective_date": "2024-06-06", "observed_at": "2026-09-27T00:00:00+00:00",
    }
    row.update(overrides)
    return SpecialPhaseEvent.from_mapping(row)


def test_delisting_first_day_is_no_limit():
    event = phase_event()
    phase = resolve_phase([event], "SEC-1", "2024-06-06", ["2024-06-05", "2024-06-06", "2024-06-07"])
    assert phase == SpecialPricePhase.DELISTING_FIRST_DAY
    assert phase_limit_ratio("SZ_MAIN", phase, "0.10", "NORMAL") is None


def test_delisting_phase_is_not_projected_before_effective_date():
    event = phase_event()
    phase = resolve_phase([event], "SEC-1", "2024-06-05", ["2024-06-05", "2024-06-06", "2024-06-07"])
    assert phase == SpecialPricePhase.REGULAR


def test_delisting_second_day_uses_delisting_period_rule():
    event = phase_event()
    phase = resolve_phase([event], "SEC-1", "2024-06-07", ["2024-06-06", "2024-06-07"])
    assert phase == SpecialPricePhase.DELISTING_PERIOD
    assert phase_limit_ratio("SZ_MAIN", phase, "0.05", "RISK_WARNING") == Decimal("0.10")


def test_delisting_period_does_not_use_st_5pct_by_default():
    event = phase_event()
    phase = resolve_phase([event], "SEC-1", "2024-06-07", ["2024-06-06", "2024-06-07"])
    assert phase_limit_ratio("SH_MAIN", phase, "0.05", "RISK_WARNING") == Decimal("0.10")


def test_chinext_delisting_period_uses_20pct():
    event = phase_event()
    phase = resolve_phase([event], "SEC-1", "2024-06-07", ["2024-06-06", "2024-06-07"])
    assert phase_limit_ratio("CHINEXT", phase, "0.20", "NORMAL") == Decimal("0.20")


def test_relisting_first_day_is_no_limit():
    event = phase_event(SpecialPricePhase.RELISTING_FIRST_DAY)
    phase = resolve_phase([event], "SEC-1", "2024-06-06", ["2024-06-06"])
    assert phase == SpecialPricePhase.RELISTING_FIRST_DAY
    assert phase_limit_ratio("SZ_MAIN", phase, "0.10", "NORMAL") is None


def test_special_reference_reset_uses_official_reference():
    event = phase_event(SpecialPricePhase.SPECIAL_REFERENCE_RESET, official_reference_price="12.34")
    assert official_reference(event) == Decimal("12.34")
    assert special_limit_prices(official_reference(event), phase_limit_ratio("SZ_MAIN", SpecialPricePhase.REGULAR, "0.10", "NORMAL")) == (Decimal("13.57"), Decimal("11.11"))


def test_special_reference_missing_fails_closed():
    event = phase_event(SpecialPricePhase.SPECIAL_REFERENCE_RESET)
    assert official_reference(event) is None
    assert phase_limit_ratio("SZ_MAIN", SpecialPricePhase.SPECIAL_REFERENCE_RESET, "0.10", "NORMAL") is None


def test_all_range_exceptions_have_disposition():
    audit = {"status": "CLOSED", "scope": {"row_count": 2}, "dispositions": [
        {"disposition": "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT"},
        {"disposition": "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED", "evidence_availability_review": "official primary sources reviewed", "unknown_reason": "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"},
    ]}
    assert is_range_exception_audit_closed(audit)


def test_final_gate_ignores_resolved_fail_closed_exception():
    audit = {"status": "CLOSED", "scope": {"row_count": 1}, "dispositions": [
        {"disposition": "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED", "evidence_availability_review": "bounded review complete", "unknown_reason": "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"},
    ]}
    assert is_range_exception_audit_closed(audit)


def test_final_gate_rejects_undispositioned_exception():
    audit = {"status": "CLOSED", "scope": {"row_count": 1}, "dispositions": [
        {"disposition": None, "evidence_availability_review": "pending", "unknown_reason": ""},
    ]}
    assert not is_range_exception_audit_closed(audit)

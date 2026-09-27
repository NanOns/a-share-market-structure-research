from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

from workbench_analysis.price_limit_exception_gate import is_range_exception_audit_closed
from workbench_analysis.special_price_phases import (
    PhasePolicyRegistry, SpecialPhaseEvent, SpecialPhaseEventStore, SpecialPricePhase,
    apply_phase_event, official_reference, resolve_event_phase,
)

ROOT = Path(__file__).resolve().parents[2]


def policy_registry():
    return PhasePolicyRegistry.from_json(ROOT / "config/special_price_phase_policy_v1.json")


def phase_event(phase=SpecialPricePhase.DELISTING_FIRST_DAY, **overrides):
    row = {
        "event_id": "event-fixture", "security_id": "SYNTH-R4-1", "trade_date": "2024-06-06", "phase": phase.value,
        "phase_effective_from": "2024-06-06", "phase_effective_to": None,
        "exchange": "XCH", "board": "SZ_MAIN", "board_scope": "SZ_MAIN", "event_type": "FIXTURE_EVENT",
        "source_ref": "https://exchange.example/notice", "source_capture_path": "fixture/notice.pdf",
        "source_capture_sha256": "a" * 64, "observed_at": "2026-09-27T00:00:00+00:00",
        "system_available_at": "2026-09-27T00:00:00+00:00", "quality": "TEST_FIXTURE",
        "contract_id": "SPECIAL_PRICE_PHASE_EVENT_V1", "revision": 1,
    }
    row.update(overrides)
    return SpecialPhaseEvent.from_mapping(row)


def test_delisting_first_day_is_no_limit():
    event = phase_event()
    policy = policy_registry()
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([event]), event.security_id, "2024-06-06",
                                         ["2024-06-05", "2024-06-06", "2024-06-07"], policy)
    output = apply_phase_event({"trade_date": "2024-06-06", "board_scope": "SZ_MAIN"}, phase, selected, policy)
    assert phase == SpecialPricePhase.DELISTING_FIRST_DAY
    assert output["limit_status"] == "NO_LIMIT"


def test_delisting_phase_is_not_projected_before_effective_date():
    event = phase_event()
    phase, _ = resolve_event_phase(SpecialPhaseEventStore([event]), event.security_id, "2024-06-05",
                                   ["2024-06-05", "2024-06-06", "2024-06-07"], policy_registry())
    assert phase == SpecialPricePhase.REGULAR


def test_delisting_second_day_uses_effective_board_policy():
    event = phase_event()
    policy = policy_registry()
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([event]), event.security_id, "2024-06-07",
                                         ["2024-06-06", "2024-06-07"], policy)
    output = apply_phase_event({"trade_date": "2024-06-07", "board_scope": "SZ_MAIN", "reference_price": "10.00"},
                               phase, selected, policy, close="10.00")
    assert phase == SpecialPricePhase.DELISTING_PERIOD
    assert output["limit_up_price"] == "11.00"
    assert output["risk_status"] == "NORMAL"


def test_relisting_first_day_is_consumed_as_no_limit():
    event = phase_event(SpecialPricePhase.RELISTING_FIRST_DAY)
    policy = policy_registry()
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([event]), event.security_id, "2024-06-06", ["2024-06-06"], policy)
    output = apply_phase_event({"trade_date": "2024-06-06", "board_scope": "SZ_MAIN"}, phase, selected, policy)
    assert output["limit_status"] == "NO_LIMIT"


def test_special_reference_reset_uses_official_reference():
    event = phase_event(SpecialPricePhase.SPECIAL_REFERENCE_RESET, official_reference_price="12.34")
    assert official_reference(event) == Decimal("12.34")
    policy = policy_registry()
    phase, selected = resolve_event_phase(SpecialPhaseEventStore([event]), event.security_id, "2024-06-06", ["2024-06-06"], policy)
    output = apply_phase_event({"trade_date": "2024-06-06", "board_scope": "SZ_MAIN"}, phase, selected, policy,
                               close="12.50",
                               regular_rule={"limit_ratio": "0.10", "tick": "0.01", "rounding_mode": "HALF_UP",
                                             "minimum_price_movement_ticks": 1, "rule_id": "fixture-rule"})
    assert output["reference_price"] == "12.34"
    assert output["limit_up_price"] == "13.57"


def test_special_reference_missing_fails_closed():
    event = phase_event(SpecialPricePhase.SPECIAL_REFERENCE_RESET)
    policy = policy_registry()
    output = apply_phase_event({"trade_date": "2024-06-06", "board_scope": "SZ_MAIN"},
                               SpecialPricePhase.SPECIAL_REFERENCE_RESET, event, policy)
    assert official_reference(event) is None
    assert output["limit_status"] == "UNKNOWN"
    assert output["reason"] == "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"


def test_range_exception_audit_gate_requires_complete_disposition():
    audit = {"status": "CLOSED", "scope": {"row_count": 1}, "dispositions": [
        {"disposition": "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED", "evidence_availability_review": "bounded review complete",
         "unknown_reason": "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"}]}
    assert is_range_exception_audit_closed(audit)
    audit["dispositions"].append({"disposition": None})
    assert not is_range_exception_audit_closed(audit)

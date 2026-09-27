from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_v4_02_price_limits_generic as builder
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver
from workbench_analysis.special_price_phases import PhasePolicyRegistry, SpecialPhaseEvent, SpecialPhaseEventStore, SpecialPricePhase


def event(phase: SpecialPricePhase, sid="SYNTH-R6-1", day="2031-04-07", **overrides):
    row = {"event_id": f"evt-{sid}-{phase.value}", "security_id": sid, "trade_date": day,
           "phase": phase.value, "phase_effective_from": day, "phase_effective_to": None,
           "exchange": "SZ", "board": "CHINEXT", "board_scope": "CHINEXT", "event_type": "SYNTHETIC_TEST_EVENT",
           "source_ref": "https://fixture.example/event", "source_capture_path": "tests/fixture.pdf",
           "source_capture_sha256": "d" * 64, "observed_at": "2031-04-06T10:00:00+00:00",
           "system_available_at": "2031-04-06T10:00:00+00:00", "quality": "SYNTHETIC_FIXTURE",
           "contract_id": "SPECIAL_PRICE_PHASE_EVENT_V1", "revision": 1}
    row.update(overrides)
    return SpecialPhaseEvent.from_mapping(row)


def context():
    policy = PhasePolicyRegistry.from_json(ROOT / "config/special_price_phase_policy_r6.json")
    sessions = ["2031-04-07", "2031-04-08", "2031-04-09", "2031-04-10", "2031-04-11"]
    return policy, sessions


def test_generic_builder_invokes_phase_runtime(monkeypatch):
    policy, sessions = context()
    start = event(SpecialPricePhase.DELISTING_FIRST_DAY)
    store = SpecialPhaseEventStore([start])
    original = builder.phase_runtime.apply_phase_event
    calls = []

    def observed(*args, **kwargs):
        calls.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(builder.phase_runtime, "apply_phase_event", observed)
    for day in sessions[:2]:
        builder.apply_row_runtime({"security_id": start.security_id, "trade_date": day, "board_scope": "CHINEXT",
                                   "reference_price": "10.00", "reason": None}, store, policy, sessions,
                                 close_lookup={(start.security_id, day): "10.00"})
    assert calls == [SpecialPricePhase.DELISTING_FIRST_DAY, SpecialPricePhase.DELISTING_PERIOD]


def test_generic_builder_delisting_first_day_recomputes_no_limit():
    policy, sessions = context()
    start = event(SpecialPricePhase.DELISTING_FIRST_DAY)
    base = {"security_id": start.security_id, "trade_date": sessions[0], "board_scope": "CHINEXT",
            "limit_status": "LIMIT_UP", "reason": "BASE_CALCULATION", "reference_price": "9.99",
            "limit_up_price": "11.98", "limit_down_price": "7.99", "rule_id": "BASE_RULE"}
    output, phase, called = builder.apply_row_runtime(base, SpecialPhaseEventStore([start]), policy, sessions,
                                                      close_lookup={(start.security_id, sessions[0]): "10.00"})
    assert called and phase == SpecialPricePhase.DELISTING_FIRST_DAY
    assert output["limit_status"] == "NO_LIMIT"
    assert output["reason"] == "DELISTING_FIRST_DAY_NO_LIMIT"
    assert output["rule_id"] == "SPECIAL_PRICE_PHASE_V1_DELISTING_FIRST_DAY"
    assert output["limit_up_price"] is None and output["limit_down_price"] is None


def test_generic_builder_delisting_period_recomputes_prices_from_policy_and_close():
    policy, sessions = context()
    start = event(SpecialPricePhase.DELISTING_FIRST_DAY)
    base = {"security_id": start.security_id, "trade_date": sessions[1], "board_scope": "CHINEXT",
            "reference_price": "10.00", "risk_status": "RISK_WARNING", "limit_status": "LIMIT_UP"}
    output, phase, called = builder.apply_row_runtime(base, SpecialPhaseEventStore([start]), policy, sessions,
        close_lookup={(start.security_id, sessions[1]): "11.50"})
    assert called and phase == SpecialPricePhase.DELISTING_PERIOD
    assert output["limit_up_price"] == "12.00"
    assert output["limit_down_price"] == "8.00"
    assert output["limit_status"] == "NOT_LIMIT"
    assert output["risk_status"] == "NORMAL"
    assert output["rule_id"] == "SZSE_GROWTH_NORMAL_20230704_V1"


def test_generic_builder_relisting_recomputes_no_limit():
    policy, sessions = context()
    relist = event(SpecialPricePhase.RELISTING_FIRST_DAY, sid="SYNTH-RELIST")
    row = {"security_id": relist.security_id, "trade_date": sessions[0], "board_scope": "CHINEXT",
           "limit_status": "LIMIT_DOWN", "reason": None, "reference_price": "10.00"}
    output, phase, called = builder.apply_row_runtime(row, SpecialPhaseEventStore([relist]), policy, sessions)
    assert called and phase == SpecialPricePhase.RELISTING_FIRST_DAY
    assert output["limit_status"] == "NO_LIMIT"


def test_generic_builder_special_reference_reset_uses_formula_and_standard_rule():
    policy, sessions = context()
    reset = event(SpecialPricePhase.SPECIAL_REFERENCE_RESET, sid="SYNTH-RESET",
                  official_reference_formula={"op": "ADD", "left": {"op": "CONST", "value": "4.00"},
                                              "right": {"op": "CONST", "value": "1.00"}})
    row = {"security_id": reset.security_id, "trade_date": sessions[0], "board_scope": "CHINEXT",
           "risk_status": "NORMAL", "reason": "BASE", "limit_status": "NOT_LIMIT"}
    standard = [{"exchange": "SZ", "board": "GROWTH", "risk_status": "NORMAL", "valid_from": "2023-07-04",
                 "valid_to": None, "limit_ratio": "0.20", "tick": "0.01", "rounding_mode": "HALF_UP", "rule_id": "RULE-GROWTH-NORMAL"}]
    output, phase, called = builder.apply_row_runtime(row, SpecialPhaseEventStore([reset]), policy, sessions,
        close_lookup={(reset.security_id, sessions[0]): "5.00"}, standard_rules=standard)
    assert called and phase == SpecialPricePhase.SPECIAL_REFERENCE_RESET
    assert output["reference_price"] == "5.00"
    assert output["limit_up_price"] == "6.00" and output["limit_down_price"] == "4.00"
    assert output["rule_id"] == "RULE-GROWTH-NORMAL"


def test_generic_builder_unknown_phase_is_fail_closed():
    policy, sessions = context()
    unknown = event(SpecialPricePhase.UNKNOWN_SPECIAL_PHASE, sid="SYNTH-UNKNOWN")
    row = {"security_id": unknown.security_id, "trade_date": sessions[0], "board_scope": "CHINEXT",
           "limit_status": "LIMIT_UP", "reason": None, "limit_up_price": "11.00", "limit_down_price": "9.00"}
    output, phase, called = builder.apply_row_runtime(row, SpecialPhaseEventStore([unknown]), policy, sessions)
    assert called and phase == SpecialPricePhase.UNKNOWN_SPECIAL_PHASE
    assert output["limit_status"] == "UNKNOWN"
    assert output["reason"] == "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE"
    assert output["limit_up_price"] is None and output["limit_down_price"] is None


def test_generic_builder_does_not_copy_r4_specialized_output_as_truth():
    policy, sessions = context()
    start = event(SpecialPricePhase.DELISTING_FIRST_DAY, sid="SYNTH-NO-COPY")
    row = {"security_id": start.security_id, "trade_date": sessions[0], "board_scope": "CHINEXT",
           "limit_status": "LIMIT_DOWN", "reason": "PRECOMPUTED_R4_VALUE", "limit_up_price": "11.00",
           "limit_down_price": "9.00", "rule_id": "PRECOMPUTED_RULE"}
    output, _, called = builder.apply_row_runtime(row, SpecialPhaseEventStore([start]), policy, sessions)
    assert called
    assert output["limit_status"] == "NO_LIMIT"
    assert output["reason"] != "PRECOMPUTED_R4_VALUE"
    assert output["rule_id"] != "PRECOMPUTED_RULE"


def test_generic_builder_validates_dated_alias_facts_without_symbol_guessing():
    policy, sessions = context()
    fact = {"security_id": "SYNTH-ALIAS", "source_security_key": "X.OLD", "effective_from": "2030-01-01",
            "effective_to": None, "exchange": "X", "board": "CHINEXT", "alias_role": "PRIMARY",
            "source_revision": "rev-1", "evidence_ref": "fixture://identity", "evidence_hash": "e" * 64}
    resolver = DatedSecurityAliasResolver([fact])
    row = {"security_id": "SYNTH-ALIAS", "source_security_key": "X.OLD", "trade_date": sessions[0],
           "board_scope": "CHINEXT", "reason": "IPO_FIRST_5_TRADING_DAYS", "limit_status": "NO_LIMIT"}
    output, phase, called = builder.apply_row_runtime(row, SpecialPhaseEventStore([]), policy, sessions,
                                                       alias_resolver=resolver)
    assert called and phase == SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS
    assert output["special_price_phase"] == "IPO_FIRST_5_TRADING_DAYS"
    bad = {**row, "source_security_key": "X.BAD"}
    with pytest.raises(ValueError, match="ALIAS_BINDING_MISMATCH"):
        builder.apply_row_runtime(bad, SpecialPhaseEventStore([]), policy, sessions, alias_resolver=resolver)

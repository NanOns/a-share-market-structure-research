from decimal import Decimal

from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver
from workbench_analysis.price_limit_exception_gate import is_range_exception_audit_closed
from workbench_analysis.price_reference_state import PreviousCloseState


def test_suspension_carries_previous_close_state():
    state = PreviousCloseState.known("10.00")
    state.carry_no_trade()
    assert state.value == Decimal("10.00")


def test_multiple_suspended_sessions_carry_previous_close():
    state = PreviousCloseState.known("10.00")
    for _ in range(4):
        state.carry_no_trade()
    assert state.value == Decimal("10.00")


def test_supported_xrxd_during_reference_chain_updates_reference():
    state = PreviousCloseState.known("10.00")
    updated = state.apply_actions(
        [("PRICE_AFFECTING_SUPPORTED", {"cash": "1.00"})],
        lambda prior, events: prior - Decimal(events[0]["cash"]),
    )
    assert updated == Decimal("9.00")
    assert state.value == Decimal("9.00")


def test_unsupported_action_blocks_reference_chain():
    state = PreviousCloseState.known("10.00")
    assert state.apply_actions([("PRICE_AFFECTING_UNSUPPORTED", None)], lambda prior, events: prior) is None
    assert state.unknown_reason() == "REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION"


def test_resume_day_uses_carried_previous_close_not_previous_market_session_bar():
    state = PreviousCloseState.known("10.00")
    state.carry_no_trade()
    state.carry_no_trade()
    reference = state.apply_actions([], lambda prior, events: prior)
    assert reference == Decimal("10.00")


def test_dated_alias_resolution_is_data_driven():
    rows = [
        {"security_id": "SYNTH-ALIAS-7", "source_security_key": "XCH.OLDKEY", "effective_from": "2020-01-01",
         "effective_to": "2025-02-16", "exchange": "XCH", "board": "GROWTH", "alias_role": "PRIMARY",
         "source_revision": "fixture-a", "evidence_ref": "fixture://alias-a", "evidence_hash": "a" * 64},
        {"security_id": "SYNTH-ALIAS-7", "source_security_key": "XCH.NEWKEY", "effective_from": "2025-02-17",
         "effective_to": None, "exchange": "XCH", "board": "GROWTH", "alias_role": "PRIMARY",
         "source_revision": "fixture-b", "evidence_ref": "fixture://alias-b", "evidence_hash": "b" * 64},
    ]
    resolver = DatedSecurityAliasResolver(rows)
    assert resolver.resolve_alias("SYNTH-ALIAS-7", "2025-02-16") == "XCH.OLDKEY"
    assert resolver.resolve_alias("SYNTH-ALIAS-7", "2025-02-17") == "XCH.NEWKEY"
    assert resolver.resolve_board("SYNTH-ALIAS-7", "2025-02-17") == "GROWTH"


def test_final_gate_rejects_open_engineering_price_limit_exception():
    audit = {"status": "OPEN", "scope": {"row_count": 1},
             "dispositions": [{"disposition": "RESOLVED_IDENTITY_BOARD"}]}
    assert not is_range_exception_audit_closed(audit)
    audit["status"] = "CLOSED"
    assert is_range_exception_audit_closed(audit)

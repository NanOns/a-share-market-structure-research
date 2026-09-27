from decimal import Decimal

from workbench_analysis.dated_security_alias import (
    board_scope_for_security,
    historical_exchange_symbol,
    stable_security_id_for_code_change,
)
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


def test_302132_board_is_chinext():
    assert board_scope_for_security(stable_security_id_for_code_change("SZ.302132")) == "CHINEXT"


def test_302132_alias_not_effective_before_20250217():
    assert historical_exchange_symbol("2025-02-14") == "SZ.300114"
    assert historical_exchange_symbol("2025-02-17") == "SZ.302132"


def test_code_change_does_not_change_stable_security_identity():
    assert stable_security_id_for_code_change("SZ.300114") == stable_security_id_for_code_change("SZ.302132")


def test_price_limit_range_exception_302132_resolved():
    finding = {"security_id": stable_security_id_for_code_change("SZ.302132"),
               "historical_exchange_symbol": historical_exchange_symbol("2024-10-08"),
               "board_scope": board_scope_for_security(stable_security_id_for_code_change("SZ.302132")),
               "disposition": "RESOLVED_IDENTITY_BOARD"}
    assert finding["historical_exchange_symbol"] == "SZ.300114"
    assert finding["board_scope"] == "CHINEXT"
    assert finding["disposition"] in {"RESOLVED_IDENTITY_BOARD", "RESOLVED_ALIAS_INTERVAL"}


def test_final_gate_rejects_open_engineering_price_limit_exception():
    audit = {"status": "OPEN", "scope": {"row_count": 1},
             "dispositions": [{"disposition": "RESOLVED_IDENTITY_BOARD"}]}
    assert not is_range_exception_audit_closed(audit)
    audit["status"] = "CLOSED"
    assert is_range_exception_audit_closed(audit)

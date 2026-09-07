from phase0_1_status import decide_status


def test_degraded_to_full_transition() -> None:
    common = dict(day_contract_ok=True, calendar_ok=True, source_unchanged=True)
    assert decide_status(
        **common,
        ui_crosscheck="PENDING",
        adjustment_reproducible=False,
        adjustment_ui_validated=False,
    ) == "DEGRADED_PASS"
    assert decide_status(
        **common,
        ui_crosscheck="PASS",
        adjustment_reproducible=True,
        adjustment_ui_validated=True,
    ) == "FULL_PASS"


def test_failed_day_ui_check_blocks() -> None:
    assert decide_status(
        day_contract_ok=True,
        ui_crosscheck="FAIL",
        calendar_ok=True,
        source_unchanged=True,
        adjustment_reproducible=False,
        adjustment_ui_validated=False,
    ) == "BLOCKED"


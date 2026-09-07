from __future__ import annotations


def decide_status(
    *,
    day_contract_ok: bool,
    ui_crosscheck: str,
    calendar_ok: bool,
    source_unchanged: bool,
    adjustment_reproducible: bool,
    adjustment_ui_validated: bool,
) -> str:
    if not day_contract_ok or ui_crosscheck == "FAIL" or not calendar_ok or not source_unchanged:
        return "BLOCKED"
    if adjustment_reproducible and adjustment_ui_validated and ui_crosscheck == "PASS":
        return "FULL_PASS"
    return "DEGRADED_PASS"


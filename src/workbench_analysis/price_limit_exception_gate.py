from __future__ import annotations

"""Acceptance checks for the separately tracked engineering range exceptions."""

ALLOWED_DISPOSITIONS = {
    "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT",
    "RESOLVED_DELISTING_PERIOD_RULE",
    "RESOLVED_RELISTING_FIRST_DAY_NO_LIMIT",
    "RESOLVED_SPECIAL_REFERENCE_RESET",
    "RESOLVED_IDENTITY_BOARD",
    "RESOLVED_CORPORATE_ACTION_REFERENCE",
    "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED",
    # Historical R1/R3 aliases remain readable for their immutable receipts.
    "RESOLVED_IDENTITY_BOARD",
    "RESOLVED_ALIAS_INTERVAL",
    "RESOLVED_LISTING_PHASE",
    "RESOLVED_CORPORATE_ACTION_REFERENCE",
    "RESOLVED_RULE_SELECTION",
    "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED",
}


def is_range_exception_audit_closed(audit: dict) -> bool:
    if audit.get("status") != "CLOSED":
        return False
    rows = audit.get("dispositions")
    if not isinstance(rows, list):
        rows = list(audit.get("r1_dispositions", [])) + list(audit.get("r3_findings", []))
    expected = audit.get("scope", {}).get("row_count")
    if not isinstance(rows, list) or not rows or expected != len(rows):
        return False
    for row in rows:
        if not isinstance(row, dict):
            return False
        disposition = row.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            return False
        if disposition == "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED":
            if not row.get("evidence_availability_review") or not row.get("unknown_reason"):
                return False
    return True

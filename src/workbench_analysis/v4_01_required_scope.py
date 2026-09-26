"""Pure R6 scope and dated-roster completeness rules for V4-01."""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Iterable


REQUIRED_BOARD_KEYS = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")


def required_board(identity: dict[str, Any]) -> str | None:
    """Admit an identity only with explicit A-stock type, exchange and board."""
    if str(identity.get("security_type") or "").upper() != "A_STOCK":
        return None
    exchange = str(identity.get("exchange") or "").upper()
    board = str(identity.get("board") or "").upper()
    if exchange == "SH" and board == "MAIN":
        return "SH_MAIN"
    if exchange == "SZ" and board == "MAIN":
        return "SZ_MAIN"
    if exchange == "SZ" and board == "CHINEXT":
        return "CHINEXT"
    if exchange == "SH" and board == "STAR":
        return "STAR"
    return None


def active_on(identity: dict[str, Any], day: str) -> bool:
    start = identity.get("symbol_effective_from") or identity.get("list_date")
    end = identity.get("symbol_effective_to")
    return bool(start and str(start) <= day and (not end or day <= str(end)))


def roster_suspicion_flags(
    *, row_count: int, prior_row_count: int | None, required_lifecycle_count: int,
    page_multiple: int = 2000, large_drop: int = 500, large_lifecycle_gap: int = 500,
) -> list[str]:
    """Emit review triggers; only revalidation evidence can clear a trigger."""
    flags: list[str] = []
    if row_count > 0 and row_count % page_multiple == 0:
        flags.append("SUSPICIOUS_PROVIDER_PAGE_BOUNDARY")
    if prior_row_count is not None and prior_row_count - row_count >= large_drop:
        flags.append("LARGE_DAY_OVER_DAY_DROP")
    if required_lifecycle_count - row_count >= large_lifecycle_gap:
        flags.append("LARGE_REQUIRED_LIFECYCLE_COUNT_GAP")
    return flags


def required_scope_counts(identities: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {board: Counter() for board in REQUIRED_BOARD_KEYS}
    seen_keys: set[str] = set()
    seen_ids: dict[str, set[str]] = {board: set() for board in REQUIRED_BOARD_KEYS}
    for identity in identities:
        board = required_board(identity)
        if board is None:
            continue
        key = str(identity.get("source_security_key") or identity.get("symbol") or "").upper()
        security_id = str(identity.get("security_id") or "")
        if not key or not security_id or not identity.get("list_date") or not identity.get("source_revision_id"):
            counts[board]["unresolved_identity_rows"] += 1
            continue
        if key in seen_keys:
            counts[board]["unresolved_identity_rows"] += 1
            continue
        seen_keys.add(key)
        counts[board]["security_keys"] += 1
        if security_id not in seen_ids[board]:
            seen_ids[board].add(security_id)
            counts[board]["unique_security_ids"] += 1
    return {board: {"required": True, "security_keys": counts[board]["security_keys"],
                    "unique_security_ids": counts[board]["unique_security_ids"],
                    "unresolved_identity_rows": counts[board]["unresolved_identity_rows"]}
            for board in REQUIRED_BOARD_KEYS}


def classify_unknown_roster_code(_code: str) -> str:
    """Unknown instruments are withheld from the required A-share universe."""
    return "OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION"


def missing_traded_required_codes(traded_required_codes: set[str], roster_codes: set[str]) -> set[str]:
    return {str(code).lower() for code in traded_required_codes} - {str(code).lower() for code in roster_codes}


def classify_bse_scope(unresolved_identity_rows: int, lifecycle_complete: bool) -> dict[str, Any]:
    if unresolved_identity_rows == 0 and lifecycle_complete:
        return {"required": False, "status": "PASS", "unresolved_identity_rows": 0}
    return {"required": False, "status": "DEGRADED_BSE", "unresolved_identity_rows": unresolved_identity_rows}


def validate_fresh_roster_runs(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    failures = []
    if first.get("row_count") != second.get("row_count"):
        failures.append("FRESH_SESSION_ROW_COUNT_MISMATCH")
    if first.get("codes_sha256") != second.get("codes_sha256"):
        failures.append("FRESH_SESSION_DIGEST_MISMATCH")
    if first.get("duplicate_count", 0) or second.get("duplicate_count", 0):
        failures.append("FRESH_SESSION_DUPLICATE_CODES")
    return failures


def required_identity_missing_from_roster(identities: Iterable[dict[str, Any]], day: str,
                                          roster_codes: set[str]) -> set[str]:
    expected = {str(row.get("source_security_key") or row.get("symbol") or "").lower()
                for row in identities if required_board(row) and active_on(row, day)}
    return expected - roster_codes


def split_roster_scope(codes: Iterable[str], identities_by_key: dict[str, dict[str, Any]], day: str,
                       noncore_by_key: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    result = {"required": [], "bse_optional": [], "noncore": [], "pending": []}
    for raw_code in sorted({str(code).lower() for code in codes}):
        row = identities_by_key.get(raw_code)
        if row and active_on(row, day):
            if required_board(row):
                result["required"].append(raw_code)
            elif str(row.get("exchange", "")).upper() == "BJ" and row.get("security_type") == "A_STOCK":
                result["bse_optional"].append(raw_code)
            else:
                result["pending"].append(raw_code)
        elif noncore_by_key.get(raw_code, {}).get("classification") == "BAOSTOCK_NON_A_STOCK_TYPE":
            result["noncore"].append(raw_code)
        else:
            result["pending"].append(raw_code)
    return result


def required_scope_digest(rows: Iterable[dict[str, Any]]) -> str:
    import hashlib
    material = "\n".join(
        f"{row['trade_date']}\0{row['board_scope']}\0{row['source_security_key']}\0{row['security_id']}"
        for row in rows
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def suspicious_day_accepted(first: dict[str, Any], second: dict[str, Any], *,
                            provider_ok: bool, market_crosscheck_ok: bool,
                            missing_lifecycle: set[str], missing_traded: set[str],
                            unknown_traded: set[str]) -> bool:
    return (not validate_fresh_roster_runs(first, second) and provider_ok and market_crosscheck_ok
            and not missing_lifecycle and not missing_traded and not unknown_traded)


def parse_day(value: str) -> date:
    return date.fromisoformat(value)

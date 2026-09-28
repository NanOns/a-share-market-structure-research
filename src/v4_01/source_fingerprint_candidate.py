from __future__ import annotations

"""Research-only source fingerprint candidate detector.

This module does not resolve identity and is not imported by production paths.
It consumes frozen source-behavior reports and emits candidate evidence only.
"""

from decimal import Decimal, InvalidOperation
from typing import Any


TDX_OHLC_AMOUNT_FIELDS = ("open", "high", "low", "close", "amount")
BAOSTOCK_BUSINESS_FIELDS = (
    "open", "high", "low", "close", "preclose", "volume", "amount",
    "tradestatus", "isST",
)


def _equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def _blank_or_zero(value: Any) -> bool:
    if value is None or value == "":
        return True
    try:
        return Decimal(str(value)) == 0
    except (InvalidOperation, ValueError):
        return False


def _index_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for row in rows:
        day = str(row.get("date", ""))
        if not day:
            continue
        if day in indexed:
            duplicate_count += 1
        else:
            indexed[day] = row
    return indexed, duplicate_count


def analyze_source_fingerprint(
    report: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Return observable fingerprint features and candidate-only disposition."""
    inputs = report.get("inputs", {})
    old_code = str(inputs.get("old_code", "")).upper()
    new_code = str(inputs.get("new_code", "")).upper()
    same_exchange = bool(old_code and new_code and old_code.split(".", 1)[0] == new_code.split(".", 1)[0])
    effective = str(inputs.get("effective_date", ""))
    previous_session = str(inputs.get("previous_session", ""))
    old_meta = report.get("tdx", {}).get("files", {}).get(old_code, {})
    new_meta = report.get("tdx", {}).get("files", {}).get(new_code, {})
    overlap = report.get("tdx", {}).get("overlap", {})
    old_tdx_present = bool(old_meta.get("exists"))
    new_tdx_present = bool(new_meta.get("exists"))
    new_tdx_prehistory = bool(new_meta.get("first_date") and new_meta["first_date"] < effective)

    tdx_overlap_count = int(overlap.get("overlap_session_count", 0) or 0)
    tdx_mismatch_fields = overlap.get("mismatch_field_counts", {}) or {}
    tdx_required_fields_exact = all(
        int(tdx_mismatch_fields.get(field, 0) or 0) == 0
        for field in TDX_OHLC_AMOUNT_FIELDS
    )
    tdx_volume_exact_ratio = (
        1.0 - int(tdx_mismatch_fields.get("volume", 0) or 0) / tdx_overlap_count
        if tdx_overlap_count else None
    )
    thresholds = contract.get("research_thresholds", {})
    min_shared = int(thresholds.get("minimum_shared_sessions", 20))
    min_volume_ratio = float(thresholds.get("tdx_volume_exact_ratio_minimum", 0.95))
    tdx_direct_semantic_overlap = bool(
        old_tdx_present
        and new_tdx_present
        and new_tdx_prehistory
        and tdx_overlap_count >= min_shared
        and tdx_required_fields_exact
        and tdx_volume_exact_ratio is not None
        and tdx_volume_exact_ratio >= min_volume_ratio
    )

    baostock = report.get("baostock", {})
    old_query = (baostock.get("long_history", {}).get(old_code.lower(), {}) or {})
    new_query = (baostock.get("long_history", {}).get(new_code.lower(), {}) or {})
    old_rows, old_duplicate_count = _index_rows(old_query.get("raw_rows", []) or [])
    new_rows, new_duplicate_count = _index_rows(new_query.get("raw_rows", []) or [])
    history_query_complete = not baostock.get("query_failures", []) and all(
        query
        and str(query.get("metadata", {}).get("error_code", "0")) == "0"
        and query.get("raw_rows")
        for query in (old_query, new_query)
    )
    provider_return_codes_match = all(
        str(row.get("code", "")).lower() == expected
        for expected, rows in ((old_code.lower(), old_rows.values()), (new_code.lower(), new_rows.values()))
        for row in rows
    )
    common_dates = sorted(set(old_rows) & set(new_rows))
    pre_effective_dates = [day for day in common_dates if day < effective]
    active_both: list[str] = []
    active_exact = 0
    active_mismatch_days: list[dict[str, Any]] = []
    normalized_suspended_rows = 0
    other_suspended_mismatch_days: list[str] = []
    status_boundary_days: list[str] = []
    for day in pre_effective_dates:
        left, right = old_rows[day], new_rows[day]
        left_status, right_status = str(left.get("tradestatus", "")), str(right.get("tradestatus", ""))
        if left_status == right_status == "1":
            active_both.append(day)
            differing = [
                field for field in BAOSTOCK_BUSINESS_FIELDS
                if not _equal(left.get(field, ""), right.get(field, ""))
            ]
            if differing:
                active_mismatch_days.append({
                    "date": day,
                    "fields": differing,
                    "values": {field: [left.get(field, ""), right.get(field, "")] for field in differing},
                })
            else:
                active_exact += 1
        elif left_status == right_status == "0":
            differing = []
            for field in BAOSTOCK_BUSINESS_FIELDS:
                left_value, right_value = left.get(field, ""), right.get(field, "")
                if field in {"volume", "amount"} and _blank_or_zero(left_value) and _blank_or_zero(right_value):
                    continue
                if not _equal(left_value, right_value):
                    differing.append(field)
            if differing:
                other_suspended_mismatch_days.append(day)
            else:
                normalized_suspended_rows += 1
        else:
            status_boundary_days.append(day)

    active_exact_ratio = active_exact / len(active_both) if active_both else None
    minimum_active_exact_ratio = float(thresholds.get("baostock_active_exact_ratio_minimum", 0.99))
    baostock_new_backfills = any(day < effective for day in new_rows)
    baostock_pre_effective_overlap_signal = bool(
        baostock_new_backfills
        and len(active_both) >= min_shared
        and active_exact_ratio is not None
        and active_exact_ratio >= minimum_active_exact_ratio
        and not old_duplicate_count
        and not new_duplicate_count
        and not other_suspended_mismatch_days
    )

    metadata = baostock.get("stock_basic_metadata_continuity", {}) or {}
    old_ipo = metadata.get("old_ipoDate")
    new_ipo = metadata.get("new_ipoDate")
    lifecycle_continuity = bool(
        old_ipo
        and old_ipo == new_ipo
        and metadata.get("old_outDate") == effective
        and str(metadata.get("new_status", "")) == "1"
    )
    new_tdx_start_matches_ipo = bool(new_meta.get("first_date") and old_ipo == new_meta.get("first_date"))
    roster_matrix = baostock.get("roster_matrix", {}) or {}
    previous_roster = roster_matrix.get(previous_session, {}) or {}
    effective_roster = roster_matrix.get(effective, {}) or {}
    roster_atomic_flip = bool(
        previous_roster.get(old_code.lower()) is True
        and previous_roster.get(new_code.lower()) is False
        and effective_roster.get(old_code.lower()) is False
        and effective_roster.get(new_code.lower()) is True
    )
    current_master = report.get("tdx", {}).get("current_security_master", {}).get("securities", {}) or {}
    old_master = current_master.get(old_code, {}) or {}
    new_master = current_master.get(new_code, {}) or {}

    duplicate_identical_bar_days: list[str] = []
    substantive_dual_trade_days: list[str] = []
    window_history = baostock.get("window_history", {}) or {}
    for day, roster in roster_matrix.items():
        if roster.get(old_code.lower()) is not True or roster.get(new_code.lower()) is not True:
            continue
        left_query = window_history.get(old_code.lower(), {}) or {}
        right_query = window_history.get(new_code.lower(), {}) or {}
        left_rows = [row for row in left_query.get("raw_rows", []) if row.get("date") == day]
        right_rows = [row for row in right_query.get("raw_rows", []) if row.get("date") == day]
        if not left_rows or not right_rows:
            continue
        left, right = left_rows[0], right_rows[0]
        if str(left.get("tradestatus", "")) != "1" or str(right.get("tradestatus", "")) != "1":
            continue
        try:
            if Decimal(str(left.get("volume", "0") or "0")) <= 0 or Decimal(str(right.get("volume", "0") or "0")) <= 0:
                continue
        except (InvalidOperation, ValueError):
            continue
        if all(_equal(left.get(field, ""), right.get(field, "")) for field in BAOSTOCK_BUSINESS_FIELDS):
            duplicate_identical_bar_days.append(day)
        else:
            substantive_dual_trade_days.append(day)

    missing_old_tdx_backfill_path = bool(
        not old_tdx_present
        and new_tdx_prehistory
        and new_tdx_start_matches_ipo
        and lifecycle_continuity
    )
    fingerprint_candidate = bool(
        same_exchange
        and new_tdx_prehistory
        and history_query_complete
        and provider_return_codes_match
        and baostock_pre_effective_overlap_signal
        and (tdx_direct_semantic_overlap or missing_old_tdx_backfill_path)
        and not substantive_dual_trade_days
    )
    if substantive_dual_trade_days:
        disposition = "UNRESOLVED_SUBSTANTIVE_DUAL_TRADING_CONFLICT"
    elif not history_query_complete or not provider_return_codes_match:
        disposition = "INCOMPLETE_OR_UNRESOLVED_SOURCE_FINGERPRINT"
    elif fingerprint_candidate:
        disposition = "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
    elif not new_tdx_prehistory and not baostock_new_backfills:
        disposition = "NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE"
    else:
        disposition = "INCOMPLETE_OR_UNRESOLVED_SOURCE_FINGERPRINT"

    return {
        "old_code": old_code,
        "new_code": new_code,
        "effective_date": effective,
        "features": {
            "same_exchange": same_exchange,
            "old_tdx_file_present": old_tdx_present,
            "new_tdx_file_present": new_tdx_present,
            "new_tdx_pre_effective_history": new_tdx_prehistory,
            "tdx_old_file_ends_previous_session": (
                old_meta.get("last_date") == previous_session if old_tdx_present and previous_session else None
            ),
            "tdx_overlap_session_count": tdx_overlap_count,
            "tdx_ohlc_amount_exact_on_all_shared_dates": tdx_required_fields_exact if tdx_overlap_count else None,
            "tdx_volume_exact_ratio": tdx_volume_exact_ratio,
            "tdx_exact_raw_overlap_ratio": overlap.get("exact_raw_overlap_ratio"),
            "tdx_longest_raw_prefix_records": overlap.get("longest_common_prefix_in_records"),
            "tdx_direct_semantic_overlap_signal": tdx_direct_semantic_overlap,
            "tdx_new_file_starts_at_shared_ipo_date": new_tdx_start_matches_ipo,
            "current_tdx_master_old_code_present": old_master.get("current_tnf_present"),
            "current_tdx_master_new_code_present": new_master.get("current_tnf_present"),
            "baostock_roster_previous_session": {
                "old_present": previous_roster.get(old_code.lower()),
                "new_present": previous_roster.get(new_code.lower()),
            },
            "baostock_roster_effective_session": {
                "old_present": effective_roster.get(old_code.lower()),
                "new_present": effective_roster.get(new_code.lower()),
            },
            "baostock_roster_atomic_flip": roster_atomic_flip,
            "baostock_new_query_backfills_pre_effective_history": baostock_new_backfills,
            "baostock_history_queries_complete": history_query_complete,
            "provider_returned_codes_match_query_codes": provider_return_codes_match,
            "baostock_pre_effective_common_dates": len(pre_effective_dates),
            "baostock_pre_effective_active_both_days": len(active_both),
            "baostock_active_exact_business_days": active_exact,
            "baostock_active_exact_ratio": active_exact_ratio,
            "baostock_normalized_suspended_representation_days": normalized_suspended_rows,
            "baostock_other_suspended_mismatch_days": other_suspended_mismatch_days,
            "baostock_active_mismatch_samples": active_mismatch_days[:10],
            "baostock_status_boundary_days": status_boundary_days[:25],
            "baostock_pre_effective_overlap_signal": baostock_pre_effective_overlap_signal,
            "metadata_lifecycle_continuity_support": lifecycle_continuity,
            "duplicate_identical_bar_days": sorted(duplicate_identical_bar_days),
            "substantive_dual_trade_days": sorted(substantive_dual_trade_days),
        },
        "disposition": disposition,
        "candidate_signal_strength": "STRONG_CANDIDATE_ONLY" if fingerprint_candidate else "NOT_ESTABLISHED",
        "candidate_auto_link_allowed": False,
        "production_identity_mutation_authorized": False,
        "owner_gate_cleared": False,
    }

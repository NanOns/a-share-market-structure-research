from __future__ import annotations

"""Pure planning and QA rules for the V4-DM-01 daily incremental lane."""

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from workbench_analysis.daily_data_head import CAPABILITIES, CAPABILITY_STATUSES, validate_capabilities

SHANGHAI = ZoneInfo("Asia/Shanghai")
BAR_STATUS_ACTUAL = "ACTUAL_TRADED"
BAR_STATUS_SUSPENDED = "SUSPENDED"
BAR_STATUS_UNKNOWN = "UNKNOWN"


class MaintenanceError(ValueError):
    pass


def iso_day(value: object) -> date:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise MaintenanceError("TRADE_DATE_INVALID") from exc


def latest_completed_session(
    sessions: Iterable[str],
    *,
    now: datetime,
    market_close: time = time(15, 0),
) -> str | None:
    """Use official session dates and the Shanghai close time, never bar presence."""
    if now.tzinfo is None:
        raise MaintenanceError("RUNTIME_CLOCK_MUST_HAVE_TIMEZONE")
    local = now.astimezone(SHANGHAI)
    complete = [
        iso_day(day) for day in sessions
        if iso_day(day) < local.date()
        or (iso_day(day) == local.date() and local.time().replace(tzinfo=None) >= market_close)
    ]
    return max(complete).isoformat() if complete else None


def official_weekday_sessions(
    start_date: str,
    end_date: str,
    *,
    official_closures: Iterable[Mapping[str, str]],
    source_revision: str,
    source_sha256: str,
) -> list[str]:
    """Expand a versioned official closure schedule over the bounded interval."""
    if not source_revision or len(source_sha256) != 64:
        raise MaintenanceError("OFFICIAL_CALENDAR_EVIDENCE_REQUIRED")
    start, end = iso_day(start_date), iso_day(end_date)
    if end < start:
        raise MaintenanceError("CALENDAR_RANGE_REVERSED")
    closed: set[date] = set()
    for row in official_closures:
        left, right = iso_day(row["start"]), iso_day(row["end"])
        if right < left:
            raise MaintenanceError("CALENDAR_CLOSURE_RANGE_REVERSED")
        cursor = left
        while cursor <= right:
            closed.add(cursor)
            cursor += timedelta(days=1)
    result = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5 and cursor not in closed:
            result.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return result


def plan_catch_up(
    *,
    official_sessions: Iterable[str],
    last_accepted_trade_date: str,
    target_cutoff: str,
    blocked_sessions: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a strict ordered catch-up plan; no later session skips a blocked day."""
    last, target = iso_day(last_accepted_trade_date), iso_day(target_cutoff)
    if target < last:
        raise MaintenanceError("CATCH_UP_TARGET_BEFORE_ACCEPTED_HEAD")
    sessions = sorted({iso_day(value) for value in official_sessions})
    blocked = {iso_day(value) for value in blocked_sessions}
    if target not in sessions and target != last:
        raise MaintenanceError("CATCH_UP_TARGET_NOT_OFFICIAL_SESSION")
    candidates = [day for day in sessions if last < day <= target]
    first_blocked = next((index for index, day in enumerate(candidates) if day in blocked), None)
    if first_blocked is None:
        ready, held = candidates, []
        status = "READY"
    else:
        ready, held = candidates[:first_blocked], candidates[first_blocked:]
        status = "BLOCKED_GAP"
    return {
        "status": status,
        "last_accepted_trade_date": last.isoformat(),
        "target_cutoff": target.isoformat(),
        "candidate_sessions": [day.isoformat() for day in candidates],
        "staging_sessions": [day.isoformat() for day in candidates],
        "promotable_sessions": [day.isoformat() for day in ready],
        "blocked_sessions": [day.isoformat() for day in held],
        "strictly_sequential": True,
        "skip_after_blocked_forbidden": True,
    }


def choose_tdx_record(
    *,
    local_record: Mapping[str, Any] | None,
    accepted_package_record: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Local accepted TDX wins conflicts; package data fills local gaps only."""
    if local_record is not None:
        conflict = (
            accepted_package_record is not None
            and local_record.get("sha256") != accepted_package_record.get("sha256")
        )
        return {
            "status": "LOCAL_WINS_CONFLICT" if conflict else "LOCAL_SELECTED",
            "selected": dict(local_record),
            "conflict_receipt_required": conflict,
        }
    if accepted_package_record is not None:
        return {"status": "PACKAGE_FILLED_LOCAL_MISSING", "selected": dict(accepted_package_record),
                "conflict_receipt_required": False}
    return {"status": "SOURCE_NOT_READY", "selected": None, "conflict_receipt_required": False}


def source_readiness(
    *,
    trade_date: str,
    tdx_available_through: str | None,
    accepted_package_available_through: str | None,
    calendar_session_confirmed: bool,
) -> dict[str, Any]:
    if not calendar_session_confirmed:
        return {"status": "BLOCKED", "reason": "OFFICIAL_SESSION_UNKNOWN"}
    sources = [value for value in (tdx_available_through, accepted_package_available_through) if value]
    latest = max((iso_day(value) for value in sources), default=None)
    target = iso_day(trade_date)
    if latest is None or latest < target:
        return {"status": "BLOCKED", "reason": "SOURCE_NOT_READY", "trade_date": target.isoformat(),
                "latest_tdx_or_accepted_package_date": latest.isoformat() if latest else None}
    return {"status": "READY", "trade_date": target.isoformat(),
            "latest_tdx_or_accepted_package_date": latest.isoformat()}


def classify_trading_status(
    *,
    calendar_is_session: bool,
    lifecycle_active: bool,
    actual_bar_present: bool,
    dated_provider_tradestatus: str | None,
    previous_official_close: float | None = None,
) -> dict[str, Any]:
    """A missing bar is unknown unless dated status evidence proves suspension."""
    if not calendar_is_session:
        return {"status": "NO_SESSION", "close_carry": None}
    if not lifecycle_active:
        return {"status": "NOT_LISTED", "close_carry": None}
    if actual_bar_present:
        return {"status": BAR_STATUS_ACTUAL, "close_carry": None}
    if dated_provider_tradestatus == "0":
        return {"status": BAR_STATUS_SUSPENDED, "close_carry": previous_official_close}
    return {"status": BAR_STATUS_UNKNOWN, "close_carry": None}


def identity_delta_events(
    *,
    previous_active: Mapping[str, Mapping[str, Any]],
    current_active: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit generic listing, delisting and adjacent symbol-change candidates."""
    old_keys, new_keys = set(previous_active), set(current_active)
    events: list[dict[str, Any]] = []
    for key in sorted(new_keys - old_keys):
        events.append({"event_type": "NEW_LISTING_CANDIDATE", "source_security_key": key,
                       "security_id": current_active[key].get("security_id")})
    for key in sorted(old_keys - new_keys):
        events.append({"event_type": "DELISTING_CANDIDATE", "source_security_key": key,
                       "security_id": previous_active[key].get("security_id")})
    exited = sorted(old_keys - new_keys)
    entered = sorted(new_keys - old_keys)
    for old in exited:
        for new in entered:
            left, right = previous_active[old], current_active[new]
            same_exchange = str(left.get("exchange") or old.split(".", 1)[0]).upper() == str(
                right.get("exchange") or new.split(".", 1)[0]
            ).upper()
            if same_exchange:
                events.append({"event_type": "CODE_CHANGE_CANDIDATE",
                               "old_source_security_key": old, "new_source_security_key": new,
                               "shared_bar_sessions": 0})
    return events


def lineage_for_bridge_date(
    trade_date: str,
    *,
    pit_eligible_from: str,
    frozen_source_set_digest: str | None,
) -> str:
    if iso_day(trade_date) < iso_day(pit_eligible_from):
        return "RECONSTRUCTED_ASOF" if frozen_source_set_digest else "DIAGNOSTIC_NON_PIT"
    return "PIT_OBSERVED" if frozen_source_set_digest else "DIAGNOSTIC_NON_PIT"


def adjustment_impact_set(
    old_rows_by_security: Mapping[str, Iterable[Mapping[str, Any]]],
    new_rows_by_security: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    source_snapshot_id: str,
    old_adjustment_revision: str,
    new_adjustment_revision: str,
    reason: str,
) -> list[dict[str, Any]]:
    """Return only identities whose historical adjusted-series digest changed."""
    result = []
    all_ids = set(old_rows_by_security) | set(new_rows_by_security)
    for security_id in sorted(all_ids):
        old_rows = list(old_rows_by_security.get(security_id, ()))
        new_rows = list(new_rows_by_security.get(security_id, ()))
        old_digest = _rows_digest(old_rows)
        new_digest = _rows_digest(new_rows)
        if old_digest == new_digest:
            continue
        dates = [iso_day(row["trade_date"]) for row in [*old_rows, *new_rows] if row.get("trade_date")]
        result.append({
            "security_id": security_id,
            "affected_from": min(dates).isoformat() if dates else None,
            "affected_to": max(dates).isoformat() if dates else None,
            "source_snapshot_id": source_snapshot_id,
            "old_adjustment_revision": old_adjustment_revision,
            "new_adjustment_revision": new_adjustment_revision,
            "row_count_changed": len(new_rows) - len(old_rows),
            "old_digest": old_digest,
            "new_digest": new_digest,
            "reason": reason,
        })
    return result


def period_view_status(
    *,
    period_last_session: str,
    target_trade_date: str,
    current_status: str | None = None,
) -> str:
    if current_status == "CLOSED_ONLY_READY" and iso_day(period_last_session) < iso_day(target_trade_date):
        return "CLOSED_ONLY_READY"
    return "CLOSED_ONLY" if iso_day(period_last_session) <= iso_day(target_trade_date) else "AS_OF_PARTIAL"


def period_is_mutable(*, is_current_period: bool, period_status: str) -> bool:
    return is_current_period and period_status == "AS_OF_PARTIAL"


def adjustment_capability_status(*, supported: bool, rows_ready: bool, reason: str | None = None) -> dict[str, Any]:
    if not supported or not rows_ready:
        return {"status": "BLOCKED", "reason": reason or "UNSUPPORTED_ADJUSTMENT_FAIL_CLOSED"}
    return {"status": "FULL_PASS", "reason": None}


def isst_change(previous: str | None, current: str | None) -> dict[str, Any]:
    if previous not in {"0", "1"} or current not in {"0", "1"}:
        return {"status": "UNKNOWN", "changed": None}
    return {"status": "KNOWN", "changed": previous != current,
            "previous_is_st": previous, "current_is_st": current}


def special_phase_increment(
    *,
    security_id: str,
    trade_date: str,
    events: Iterable[Mapping[str, Any]],
    evidence_complete: bool,
) -> dict[str, Any]:
    matches = [
        row for row in events
        if str(row.get("security_id") or "") == security_id
        and str(row.get("effective_date") or "")[:10] == trade_date
    ]
    if matches and evidence_complete:
        return {"status": "KNOWN_EVENT", "events": [dict(row) for row in matches]}
    if evidence_complete:
        return {"status": "NO_EVENT", "events": []}
    return {"status": "UNKNOWN_SPECIAL_PHASE", "events": []}


def require_source_freeze_before_component_build(source_freeze: Mapping[str, Any]) -> None:
    from workbench_analysis.daily_source_freeze import source_freeze_complete

    if not source_freeze_complete(source_freeze):
        raise MaintenanceError("SOURCE_FREEZE_MUST_COMPLETE_BEFORE_COMPONENT_BUILD")


def idempotency_key(trade_date: str, source_manifest_digest: str, contract_digest: str) -> str:
    if len(source_manifest_digest) != 64 or len(contract_digest) != 64:
        raise MaintenanceError("IDEMPOTENCY_DIGEST_INVALID")
    material = f"{iso_day(trade_date).isoformat()}|{source_manifest_digest}|{contract_digest}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def resume_reference_close(previous_official_close: float | None, *, actual_bar_present: bool) -> float | None:
    return previous_official_close if actual_bar_present else None


def append_adjustment_revision(
    history: Iterable[Mapping[str, Any]], new_revision: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Append immutable revisions and mark the prior one superseded by identity."""
    rows = [dict(row) for row in history]
    security_id = str(new_revision.get("security_id") or "")
    if not security_id or not new_revision.get("revision_id"):
        raise MaintenanceError("ADJUSTMENT_REVISION_IDENTITY_REQUIRED")
    if any(row.get("revision_id") == new_revision["revision_id"] for row in rows):
        return rows
    for row in rows:
        if row.get("security_id") == security_id and not row.get("superseded_by"):
            row["superseded_by"] = new_revision["revision_id"]
    rows.append(dict(new_revision))
    return rows


def cross_component_postcheck(
    *,
    universe_keys: Iterable[tuple[str, str]],
    trading_status_keys: Iterable[tuple[str, str]],
    isst_keys: Iterable[tuple[str, str]],
    price_limit_keys: Iterable[tuple[str, str]],
    actual_traded_keys: Iterable[tuple[str, str]],
    bar_keys: Iterable[tuple[str, str]],
    suspended_keys: Iterable[tuple[str, str]],
    fabricated_zero_return_keys: Iterable[tuple[str, str]],
    adjusted_ready_keys: Iterable[tuple[str, str]],
    adjusted_raw_fallback_keys: Iterable[tuple[str, str]],
    period_max_source_dates: Iterable[str],
    head_cutoff: str,
    tdx_root_write_count: int,
) -> dict[str, Any]:
    universe = set(universe_keys)
    status, isst, limits = set(trading_status_keys), set(isst_keys), set(price_limit_keys)
    actual, bars = set(actual_traded_keys), set(bar_keys)
    suspended, zero_returns = set(suspended_keys), set(fabricated_zero_return_keys)
    adjusted, raw_fallback = set(adjusted_ready_keys), set(adjusted_raw_fallback_keys)
    checks = {
        "trading_status_key_set_matches_universe": status == universe,
        "isst_key_set_matches_universe": isst == universe,
        "price_limit_key_set_matches_universe": limits == universe,
        "actual_traded_has_bar": actual <= bars,
        "suspended_not_fabricated_zero_return": not (suspended & zero_returns),
        "adjusted_readiness_never_falls_back_to_raw": not raw_fallback,
        "period_source_not_after_head_cutoff": all(
            iso_day(value) <= iso_day(head_cutoff) for value in period_max_source_dates
        ),
        "tdx_root_write_count_zero": tdx_root_write_count == 0,
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "checks": {key: "PASS" if value else "BLOCKED" for key, value in checks.items()},
        "key_counts": {
            "universe": len(universe), "trading_status": len(status), "isst": len(isst),
            "price_limit": len(limits), "actual_traded": len(actual), "bars": len(bars),
        },
    }


def validate_daily_promotion(
    *,
    component_permissions: Mapping[str, Any],
    source_freeze_pass: bool,
    independent_postcheck_status: str,
    candidate_manifest_status: str,
) -> list[str]:
    errors = validate_capabilities(component_permissions, required=CAPABILITIES)
    if not source_freeze_pass:
        errors.append("SOURCE_FREEZE_INCOMPLETE")
    if independent_postcheck_status != "PASS":
        errors.append("INDEPENDENT_POSTCHECK_NOT_PASS")
    if candidate_manifest_status != "CANDIDATE_MANIFEST_READY":
        errors.append("CANDIDATE_MANIFEST_NOT_READY")
    return errors


def _rows_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    canonical = json.dumps(list(rows), sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

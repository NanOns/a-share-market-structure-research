from __future__ import annotations

"""Contract checks for the versioned official security code-change index."""

from datetime import date, datetime
from typing import Iterable, Mapping

CONTRACT_ID = "OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1"
CONTRACT_VERSION = "1.0.0"
REQUIRED_EXCHANGES = frozenset({"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"})
REQUIRED_EVENT_FIELDS = (
    "exchange", "old_source_security_key", "new_source_security_key", "effective_date",
    "source_ref", "source_capture_path", "source_capture_sha256", "published_at",
    "observed_at", "system_available_at",
)


def _day(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _aware_timestamp(value: object) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_index_coverage(
    *,
    coverage_records: Iterable[Mapping[str, object]],
    events: Iterable[Mapping[str, object]],
    window_start: str = "2023-07-04",
    window_end: str = "2026-09-24",
) -> dict[str, object]:
    """Validate exchange/window receipts without inferring coverage from event rows."""
    start, end = _day(window_start), _day(window_end)
    if start is None or end is None or start > end:
        raise ValueError("OFFICIAL_CODE_CHANGE_INDEX_WINDOW_INVALID")

    by_exchange: dict[str, list[Mapping[str, object]]] = {}
    event_rows = list(events)
    event_counts: dict[str, int] = {}
    for event in event_rows:
        exchange = str(event.get("exchange") or "").upper()
        event_counts[exchange] = event_counts.get(exchange, 0) + 1
    for row in coverage_records:
        by_exchange.setdefault(str(row.get("exchange") or "").upper(), []).append(row)
    unresolved: list[dict[str, object]] = []
    normalized_coverage: list[dict[str, object]] = []
    failed_query_count = 0
    for exchange in sorted(REQUIRED_EXCHANGES):
        rows = by_exchange.get(exchange, [])
        if len(rows) != 1:
            unresolved.append({"exchange": exchange, "reason": "MISSING_OR_DUPLICATE_COVERAGE_RECEIPT",
                               "window_start": window_start, "window_end": window_end})
            continue
        row = rows[0]
        failures = int(row.get("failed_query_count") or 0)
        failed_query_count += failures
        row_start, row_end = _day(row.get("window_start")), _day(row.get("window_end"))
        unresolved_windows = list(row.get("unresolved_source_windows") or [])
        try:
            reported_event_count = int(row.get("event_count") or 0)
        except (TypeError, ValueError):
            reported_event_count = -1
        event_count_matches = reported_event_count == event_counts.get(exchange, 0)
        complete = (
            row_start is not None and row_end is not None
            and row_start <= start and row_end >= end
            and row.get("coverage_complete") is True
            and bool(row.get("query_or_index_method"))
            and bool(row.get("source_revision"))
            and failures == 0
            and not unresolved_windows
            and event_count_matches
        )
        normalized_coverage.append({key: row.get(key) for key in (
            "exchange", "window_start", "window_end", "coverage_complete",
            "query_or_index_method", "source_revision", "event_count",
            "failed_query_count", "unresolved_source_windows",
        )})
        if not complete:
            unresolved.append({
                "exchange": exchange,
                "reason": "INCOMPLETE_SOURCE_COVERAGE",
                "window_start": window_start,
                "window_end": window_end,
                "reported_window_start": row.get("window_start"),
                "reported_window_end": row.get("window_end"),
                "coverage_complete": row.get("coverage_complete") is True,
                "failed_query_count": failures,
                "reported_event_count": reported_event_count,
                "observed_event_count": event_counts.get(exchange, 0),
                "event_count_matches": event_count_matches,
                "unresolved_source_windows": unresolved_windows,
            })

    malformed_event_count = 0
    for row in event_rows:
        effective = _day(row.get("effective_date"))
        digest = str(row.get("source_capture_sha256") or "").lower()
        if (
            any(not str(row.get(field) or "").strip() for field in REQUIRED_EVENT_FIELDS)
            or effective is None or effective < start or effective > end
            or str(row.get("exchange") or "").upper() not in REQUIRED_EXCHANGES
            or not _aware_timestamp(row.get("observed_at"))
            or not _aware_timestamp(row.get("system_available_at"))
            or len(digest) != 64
            or str(row.get("old_source_security_key") or "").upper()
            == str(row.get("new_source_security_key") or "").upper()
        ):
            malformed_event_count += 1
    status = "PASS" if not unresolved and failed_query_count == 0 and malformed_event_count == 0 else "BLOCKED"
    return {
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "coverage_status": status,
        "required_exchanges": sorted(REQUIRED_EXCHANGES),
        "history_window": {"start": window_start, "end": window_end},
        "coverage_receipts": normalized_coverage,
        "event_count": len(event_rows),
        "failed_query_count": failed_query_count,
        "unresolved_source_windows": unresolved,
        "malformed_event_count": malformed_event_count,
        "event_index_completeness_pass": status == "PASS",
    }

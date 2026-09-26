from __future__ import annotations

"""Small deterministic helpers shared by V4-02 closure builders and regressions."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping


TEMPORAL_REQUIRED_CASES = (
    "WEEKLY_MONDAY",
    "WEEKLY_WEDNESDAY",
    "WEEKLY_FRIDAY",
    "MONTH_START",
    "MONTH_MIDDLE",
    "MONTH_END",
    "HOLIDAY_SHORTENED_WEEK",
    "NONTRADING_CALENDAR_MONTH_END",
)


def classify_dated_status(source_bar_present: bool, provider_tradestatus: Any = None) -> str:
    if source_bar_present:
        return "ACTUAL_TRADED"
    value = str(provider_tradestatus).strip() if provider_tradestatus is not None else ""
    if value == "0":
        return "SUSPENDED"
    if value == "1":
        return "DATA_GAP"
    return "UNKNOWN"


def adjusted_value_or_none(quality: str, value: Any) -> Any:
    return value if str(quality) == "READY" else None


def closed_only_disposition(gap_statuses: Iterable[str]) -> str:
    values = tuple(str(value).upper() for value in gap_statuses)
    if any(value in {"UNKNOWN", "DATA_GAP"} for value in values):
        return "BLOCKED"
    return "CLOSED_ONLY"


def asof_visible_rows(rows: Iterable[Mapping[str, Any]], asof_date: str) -> list[Mapping[str, Any]]:
    return [row for row in rows if str(row.get("trade_date", "")) <= asof_date]


def category_disposition_for_security(dispositions: Mapping[str, str], security_id: str) -> str:
    return str(dispositions.get(security_id, "READY"))


def historical_adjusted_lineage(snapshot_available_at: str | None, observation_cutoff: str) -> str:
    if snapshot_available_at and snapshot_available_at <= observation_cutoff:
        return "PIT_OBSERVED"
    return "DIAGNOSTIC_NON_PIT"


def validate_snapshot_hash_binding(manifest: Mapping[str, Any], observed_hashes: Mapping[str, str]) -> bool:
    files = manifest.get("files")
    if not isinstance(files, Mapping) or not files:
        return False
    for name, record in files.items():
        if not isinstance(record, Mapping) or observed_hashes.get(str(name)) != record.get("sha256"):
            return False
    return True


def ex_right_reference_price(previous_close: Any, events: Iterable[Any], tick: Any = "0.01") -> Decimal:
    """Apply the accepted XRXD affine transform to previous close, rounded to tick."""
    price = Decimal(str(previous_close))
    if not price.is_finite() or price <= 0:
        raise ValueError("PREVIOUS_CLOSE_INVALID")
    for event in events:
        m, c = event.mc()
        price = (price - c) / m
    quantum = Decimal(str(tick))
    if quantum <= 0:
        raise ValueError("TICK_INVALID")
    return (price / quantum).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * quantum

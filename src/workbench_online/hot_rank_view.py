"""Explainable, source-separated M14-03 hot-rank views."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo


CONTRACT_ID = "M14_HOT_RANK_VIEW_V1_0"
DEFAULT_COMPARISON_WINDOW_MINUTES = 15
SOURCE_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _parse_time(value: object, *, source_time: bool = False) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("HOT_RANK_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SOURCE_TIMEZONE if source_time else timezone.utc)
    return parsed


def _validate_batch(batch: dict) -> None:
    required = {"batch_id", "source_id", "list_type", "source_as_of", "observed_at_utc", "rows"}
    if not isinstance(batch, dict) or not required.issubset(batch):
        raise ValueError("HOT_RANK_BATCH_SCHEMA_INVALID")
    if batch.get("personal_research_only") is not True or batch.get("publication_enabled") is not False:
        raise ValueError("HOT_RANK_BATCH_NOT_ISOLATED")
    if not isinstance(batch["rows"], list) or not batch["rows"]:
        raise ValueError("HOT_RANK_BATCH_EMPTY")
    _parse_time(batch["source_as_of"], source_time=True)
    _parse_time(batch["observed_at_utc"])
    seen = set()
    for index, row in enumerate(batch["rows"], start=1):
        if not isinstance(row, dict) or not {"source_code", "platform_rank", "source_row_order"}.issubset(row):
            raise ValueError("HOT_RANK_ROW_SCHEMA_INVALID")
        source_code = str(row["source_code"])
        if source_code in seen:
            raise ValueError("HOT_RANK_DUPLICATE_SOURCE_CODE")
        seen.add(source_code)
        if int(row["platform_rank"]) <= 0 or int(row["source_row_order"]) != index:
            raise ValueError("HOT_RANK_PLATFORM_ORDER_INVALID")


def _batch_time(batch: dict) -> datetime:
    return _parse_time(batch["source_as_of"], source_time=True) or _parse_time(batch["observed_at_utc"])


def _row_key(row: dict) -> str:
    return str(row.get("security_id") or f"SOURCE:{row['source_code']}")


def build_hot_rank_view(
    batches: Iterable[dict],
    *,
    source_id: str,
    list_type: str | None = None,
    page: int = 1,
    comparison_window_minutes: int = DEFAULT_COMPARISON_WINDOW_MINUTES,
    batch_id: str | None = None,
) -> dict:
    if not source_id or comparison_window_minutes <= 0:
        raise ValueError("HOT_RANK_VIEW_ARGUMENT_INVALID")
    candidates = []
    for batch in batches:
        _validate_batch(batch)
        if batch["source_id"] != source_id or (list_type and batch["list_type"] != list_type):
            continue
        if int(batch.get("page", 1)) != page:
            continue
        candidates.append(batch)
    if not candidates:
        raise ValueError("HOT_RANK_NO_BATCH_FOR_SOURCE")
    candidates.sort(key=lambda item: (_batch_time(item), _parse_time(item["observed_at_utc"])))
    if batch_id:
        indexes = [index for index, item in enumerate(candidates) if item["batch_id"] == batch_id]
        if not indexes:
            raise ValueError("HOT_RANK_BATCH_NOT_FOUND")
        current_index = indexes[-1]
        current = candidates[current_index]
        previous = candidates[current_index - 1] if current_index > 0 else None
    else:
        current_index = len(candidates) - 1
        current = candidates[current_index]
        previous = candidates[current_index - 1] if current_index > 0 else None
    current_source_time = _parse_time(current["source_as_of"], source_time=True)
    previous_source_time = _parse_time(previous["source_as_of"], source_time=True) if previous else None
    comparison_status = "UNAVAILABLE_NO_PREVIOUS_BATCH"
    comparison_batch_id = None
    rank_change_basis = None
    if current_source_time is None:
        comparison_status = "UNAVAILABLE_SOURCE_AS_OF_MISSING"
    elif previous_source_time is None:
        comparison_status = "UNAVAILABLE_COMPARISON_SOURCE_AS_OF_MISSING"
    else:
        delta = current_source_time - previous_source_time
        if delta < timedelta(0):
            comparison_status = "UNAVAILABLE_COMPARISON_NOT_PRIOR"
        elif delta > timedelta(minutes=comparison_window_minutes):
            comparison_status = "UNAVAILABLE_COMPARISON_WINDOW_EXCEEDED"
        else:
            comparison_status = "COMPARABLE"
            comparison_batch_id = previous["batch_id"]
            rank_change_basis = "PREVIOUS_CAPTURE"
    previous_by_key = {_row_key(row): row for row in previous["rows"]} if comparison_batch_id else {}
    rows = []
    for row in current["rows"]:
        previous_row = previous_by_key.get(_row_key(row))
        previous_rank = int(previous_row["platform_rank"]) if previous_row else None
        current_rank = int(row["platform_rank"])
        rows.append(
            {
                "source_code": str(row["source_code"]),
                "security_id": row.get("security_id"),
                "platform_rank": current_rank,
                "previous_rank": previous_rank,
                "rank_delta": previous_rank - current_rank if previous_rank is not None else None,
                "comparison_batch_id": comparison_batch_id,
                "rank_change_basis": rank_change_basis,
                "source_rank_change": row.get("rank_change"),
                "security_name": row.get("security_name"),
                "source_row_order": int(row["source_row_order"]),
            }
        )
    return {
        "contract_id": CONTRACT_ID,
        "source_id": current["source_id"],
        "dataset": current.get("dataset", "HOT_RANKINGS"),
        "list_type": current["list_type"],
        "page": int(current.get("page", page)),
        "batch_id": current["batch_id"],
        "source_as_of": current["source_as_of"],
        "observed_at_utc": current["observed_at_utc"],
        "time_semantics": "SOURCE_AS_OF" if current_source_time else "OBSERVED_AT_ONLY",
        "comparison_window_minutes": comparison_window_minutes,
        "comparison_status": comparison_status,
        "comparison_batch_id": comparison_batch_id,
        "rank_change_basis": rank_change_basis,
        "capability_status": "PERSONAL_RESEARCH_ONLY",
        "personal_research_only": True,
        "publication_enabled": False,
        "rows": rows,
    }

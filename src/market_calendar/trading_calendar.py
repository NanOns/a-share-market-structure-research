from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import struct

from tdx.day_reader import DAY_RECORD_LENGTH


DATE_STRUCT = struct.Struct("<I")


def int_to_date(value: int) -> date:
    return date(value // 10000, (value // 100) % 100, value % 100)


def date_to_int(value: date) -> int:
    return value.year * 10000 + value.month * 100 + value.day


def read_day_dates(path: Path) -> list[int]:
    raw = path.read_bytes()
    if len(raw) % DAY_RECORD_LENGTH:
        raise ValueError(f"incomplete .day record in {path}")
    return [DATE_STRUCT.unpack_from(raw, offset)[0] for offset in range(0, len(raw), DAY_RECORD_LENGTH)]


@dataclass(frozen=True)
class StockTimeline:
    security_id: str
    first_date: int | None
    last_date: int | None
    record_count: int
    recent_dates: frozenset[int]
    file_exists: bool = True
    structurally_valid: bool = True
    current_member: bool = True


def build_master_calendar(
    *,
    primary_index_dates: dict[str, set[int]],
    a_stock_bar_counts: Counter[int],
    stock_intervals: list[tuple[int, int]],
    minimum_majority: float = 0.50,
    minimum_absolute_confirmation: int = 20,
) -> list[dict]:
    evidence_dates = set(a_stock_bar_counts)
    for dates in primary_index_dates.values():
        evidence_dates.update(dates)
    if not evidence_dates:
        return []

    starts = Counter(first for first, _last in stock_intervals)
    ends = Counter(last for _first, last in stock_intervals)
    start = int_to_date(min(evidence_dates))
    end = int_to_date(max(evidence_dates))
    eligible = 0
    rows: list[dict] = []
    current = start
    while current <= end:
        encoded = date_to_int(current)
        eligible += starts[encoded]
        index_ids = sorted(name for name, dates in primary_index_dates.items() if encoded in dates)
        index_confirmation_count = len(index_ids)
        stock_confirmation_count = a_stock_bar_counts[encoded]
        coverage = stock_confirmation_count / eligible if eligible else 0.0
        majority_confirmation = (
            stock_confirmation_count >= minimum_absolute_confirmation and coverage >= minimum_majority
        )
        is_open = bool(index_confirmation_count or majority_confirmation)
        if index_confirmation_count == len(primary_index_dates) and primary_index_dates:
            basis = "BOTH_PRIMARY_INDICES_AND_A_STOCKS"
        elif index_confirmation_count:
            basis = "PRIMARY_INDEX_AND_A_STOCKS"
        elif majority_confirmation:
            basis = "A_STOCK_MAJORITY_ONLY"
        else:
            basis = "NO_LOCAL_OPEN_EVIDENCE"
        rows.append(
            {
                "calendar_date": encoded,
                "is_market_open": is_open,
                "source_basis": basis,
                "confirmation_count": index_confirmation_count + stock_confirmation_count,
                "index_confirmation_count": index_confirmation_count,
                "confirming_indices": ",".join(index_ids),
                "a_stock_confirmation_count": stock_confirmation_count,
                "eligible_a_stock_count": eligible,
                "a_stock_confirmation_ratio": round(coverage, 8),
            }
        )
        eligible -= ends[encoded]
        current += timedelta(days=1)
    return rows


def classify_missing_state(timeline: StockTimeline, session: int) -> str:
    if not timeline.file_exists:
        return "FILE_MISSING"
    if not timeline.structurally_valid or timeline.first_date is None or timeline.last_date is None:
        return "MISSING_DATA"
    if session < timeline.first_date:
        return "NOT_LISTED_YET"
    if session > timeline.last_date:
        return "MISSING_DATA" if timeline.current_member else "DELISTED_OR_INACTIVE"
    if session not in timeline.recent_dates:
        # A later bar in the same local file is direct evidence that trading resumed.
        return "SUSPENDED"
    return "BAR"


def align_recent_bars(
    sessions: list[int],
    bars: dict[int, dict[str, float]],
    timeline: StockTimeline,
) -> list[dict]:
    result = []
    previous_close: float | None = None
    for session in sessions:
        if session in bars:
            bar = bars[session]
            close = float(bar["close"])
            previous_return = 0.0 if previous_close in (None, 0) else close / previous_close - 1
            result.append(
                {
                    "calendar_date": session,
                    "status": "BAR",
                    "aligned_close": close,
                    "aligned_return": previous_return,
                    "aligned_volume": float(bar.get("volume", 0)),
                    "aligned_amount": float(bar.get("amount", 0)),
                    "is_synthetic_fill": False,
                    "tradable": True,
                }
            )
            previous_close = close
            continue
        status = classify_missing_state(timeline, session)
        can_fill = status == "SUSPENDED" and previous_close is not None
        result.append(
            {
                "calendar_date": session,
                "status": status,
                "aligned_close": previous_close if can_fill else None,
                "aligned_return": 0.0 if can_fill else None,
                "aligned_volume": 0.0 if can_fill else None,
                "aligned_amount": 0.0 if can_fill else None,
                "is_synthetic_fill": can_fill,
                "tradable": False,
            }
        )
    return result


"""M13A market-cycle aggregation from one bound local technical snapshot."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable


CONTRACT_ID = "M13_MARKET_CYCLE_V1"


def _finite(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _coverage(valid: int, display: int) -> float | None:
    return valid / display if display else None


def _deduplicate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one deterministic row per security for a market point."""
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(rows):
        security_id = row.get("security_id")
        key = ("security", str(security_id)) if security_id not in (None, "") else ("row", str(index))
        selected.setdefault(key, row)
    return list(selected.values())


def aggregate_market_point(trade_date: str, rows: Iterable[dict[str, Any]], *, high_counts: dict[str, dict[str, int]] | None = None, queue_counts: dict[str, int] | None = None, queue_unique_count: int | None = None, sector_state_counts: dict[str, int] | None = None, limit_rows: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Aggregate per-stock rows while preserving field-specific denominators."""
    values = _deduplicate_rows(rows)
    display_count = len(values)
    valid_quote = [row for row in values if _finite(row.get("quote_ret1"))]
    up_count = sum(float(row["quote_ret1"]) > 0 for row in valid_quote)
    down_count = sum(float(row["quote_ret1"]) < 0 for row in valid_quote)
    flat_count = sum(float(row["quote_ret1"]) == 0 for row in valid_quote)
    if up_count + down_count + flat_count != len(valid_quote):
        raise ValueError("MARKET_BREADTH_IDENTITY_FAILED")
    amount_values = [float(row["raw_amount"]) for row in values if _finite(row.get("raw_amount"))]
    ma20_values = [row for row in values if _finite(row.get("adj_close")) and _finite(row.get("ma20"))]
    ma60_values = [row for row in values if _finite(row.get("adj_close")) and _finite(row.get("ma60"))]
    limit_values = list(limit_rows) if limit_rows is not None else []
    limit_up_count = sum(str(row.get("limit_state") or "UNKNOWN").upper() == "UP" for row in limit_values)
    limit_down_count = sum(str(row.get("limit_state") or "UNKNOWN").upper() == "DOWN" for row in limit_values)
    unknown_limit_count = sum(str(row.get("limit_state") or "UNKNOWN").upper() == "UNKNOWN" for row in limit_values)
    point = {
        "trade_date": str(trade_date),
        "contract_id": CONTRACT_ID,
        "display_count": display_count,
        "quote_valid_count": len(valid_quote),
        "up_count": up_count,
        "down_count": down_count,
        "flat_count": flat_count,
        "amount_sum": sum(amount_values) if amount_values else None,
        "amount_valid_count": len(amount_values),
        "ma20_above_count": sum(float(row["adj_close"]) > float(row["ma20"]) for row in ma20_values),
        "ma20_valid_count": len(ma20_values),
        "ma60_above_count": sum(float(row["adj_close"]) > float(row["ma60"]) for row in ma60_values),
        "ma60_valid_count": len(ma60_values),
        "new_high_counts": high_counts or {},
        "queue_counts": queue_counts or {},
        "queue_unique_count": queue_unique_count,
        "sector_state_counts": sector_state_counts,
        "limit_up_count": limit_up_count if limit_rows is not None else None,
        "limit_down_count": limit_down_count if limit_rows is not None else None,
        "unknown_limit_count": unknown_limit_count if limit_rows is not None else None,
        "field_coverage": {
            "quote_ret1": _coverage(len(valid_quote), display_count),
            "raw_amount": _coverage(len(amount_values), display_count),
            "ma20": _coverage(len(ma20_values), display_count),
            "ma60": _coverage(len(ma60_values), display_count),
        },
        "capabilities": {
            "limit_state": ("BOUND" if limit_rows is not None and unknown_limit_count == 0 else "PARTIAL") if limit_rows is not None else "NOT_BUILT",
            "queue_state": "AVAILABLE" if queue_counts is not None else "NOT_BUILT",
            "sector_state": "AVAILABLE" if sector_state_counts is not None else "NOT_BUILT",
        },
    }
    return point


def group_queue_counts(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, int], int]:
    counts: dict[str, int] = defaultdict(int)
    unique: set[str] = set()
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if row.get("hit") is True:
            queue = str(row.get("queue_name") or "UNKNOWN")
            security_id = row.get("security_id")
            key = (str(security_id), queue) if security_id not in (None, "") else (f"__row_{index}", queue)
            if key in seen:
                continue
            seen.add(key)
            counts[queue] += 1
            unique.add(str(security_id))
    return dict(sorted(counts.items())), len(unique)


def group_sector_state_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Count one state per sector, preserving NULL state as UNKNOWN."""
    counts: dict[str, int] = defaultdict(int)
    seen: set[str] = set()
    for row in rows:
        sector_id = str(row.get("sector_id"))
        if sector_id in seen:
            continue
        seen.add(sector_id)
        state = str(row.get("diffusion_state") or "UNKNOWN")
        counts[state] += 1
    return dict(sorted(counts.items()))

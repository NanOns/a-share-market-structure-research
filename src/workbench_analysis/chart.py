"""M8A-03 single-security chart transformation with one adjustment anchor."""

from __future__ import annotations

from collections import OrderedDict
from datetime import date
from typing import Any, Iterable

import numpy as np
import pandas as pd


CONTRACT_VERSION = "TECHNICAL_CHART_V2_1_PREVIEW"
MAX_DAYS = 250
PRICE_BASES = {"RAW": "RAW", "ADJUSTED": "TDX_NATIVE_QFQ", "TDX_NATIVE_QFQ": "TDX_NATIVE_QFQ"}
FIELDS = {"ohlc", "ma", "amount", "rps"}


def chart_cache_key(snapshot_id: str, security_id: str, price_basis: str, adjustment_as_of: str | None, days: int, fields: Iterable[str]) -> tuple:
    return (str(snapshot_id), str(security_id), str(price_basis), adjustment_as_of, int(days), tuple(sorted(set(fields))), CONTRACT_VERSION)


class ChartCache:
    """Small LRU cache with both entry and approximate byte limits."""

    def __init__(self, *, max_entries: int = 128, max_bytes: int = 32 * 1024 * 1024):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._items: OrderedDict[tuple, tuple[dict, int]] = OrderedDict()
        self._bytes = 0

    def get(self, key: tuple) -> dict | None:
        item = self._items.get(key)
        if item is None:
            return None
        self._items.move_to_end(key)
        return item[0]

    def put(self, key: tuple, value: dict) -> None:
        size = len(repr(value).encode("utf-8"))
        old = self._items.pop(key, None)
        if old:
            self._bytes -= old[1]
        self._items[key] = (value, size)
        self._bytes += size
        while len(self._items) > self.max_entries or self._bytes > self.max_bytes:
            _, (_, removed) = self._items.popitem(last=False)
            self._bytes -= removed


def _number(value: Any) -> float | None:
    try:
        return None if pd.isna(value) or not np.isfinite(float(value)) else float(value)
    except (TypeError, ValueError):
        return None


def build_chart_points(
    frame: pd.DataFrame,
    *,
    cutoff: date,
    days: int = 20,
    price_basis: str = "ADJUSTED",
    fields: Iterable[str] = ("ohlc", "ma", "amount", "rps"),
    expected_dates: Iterable[date] | None = None,
    rps_by_date: dict[date, float | None] | None = None,
) -> dict[str, Any]:
    """Create chart points, retaining explicit gap points and one price basis."""
    if price_basis not in PRICE_BASES:
        raise ValueError("PRICE_BASIS_UNSUPPORTED")
    if not 1 <= int(days) <= MAX_DAYS:
        raise ValueError("CHART_DAYS_OUT_OF_RANGE")
    fields = tuple(sorted(set(str(value) for value in fields)))
    if not fields or not set(fields).issubset(FIELDS):
        raise ValueError("CHART_FIELDS_UNSUPPORTED")
    work = frame.copy()
    if "date" not in work or (pd.to_datetime(work["date"]).dt.date > cutoff).any():
        raise ValueError("FUTURE_CHART_INPUT")
    work["date"] = pd.to_datetime(work["date"]).dt.date
    work = work[work["date"] <= cutoff].sort_values("date", kind="mergesort").drop_duplicates("date", keep="last")
    close_name = "raw_close" if PRICE_BASES[price_basis] == "RAW" else "adj_close"
    available_dates = list(work["date"])
    expected = sorted(set(expected_dates if expected_dates is not None else available_dates))
    if expected:
        work["_source_present"] = True
        work = work.set_index("date").reindex(expected).rename_axis("date").reset_index()
        work["_source_present"] = work["_source_present"].fillna(False)
    close = pd.to_numeric(work.get(close_name, pd.Series(np.nan, index=work.index)), errors="coerce")
    for width in (5, 10, 20, 60):
        work[f"ma{width}"] = close.rolling(width, min_periods=width).mean()
    display_dates = expected[-int(days):]
    by_date = work.set_index("date") if not work.empty else pd.DataFrame()
    points = []
    gaps = []
    for trade_date in display_dates:
        row = by_date.loc[trade_date] if trade_date in by_date.index else None
        has_row = row is not None and bool(row.get("_source_present", True))
        chosen_close = _number(row.get(close_name)) if has_row else None
        gap = not has_row or chosen_close is None
        if gap:
            gaps.append({"date": trade_date.isoformat(), "reason": "NO_VALID_PRICE" if has_row else "NO_SECURITY_ROW"})
        point: dict[str, Any] = {"date": trade_date.isoformat(), "gap": gap, "gap_reason": gaps[-1]["reason"] if gap else None}
        if "ohlc" in fields:
            point.update({name: _number(row.get(f"{prefix}_{name}")) if has_row else None for name, prefix in (("open", "raw"), ("high", "raw"), ("low", "raw"), ("close", "raw"))})
            if PRICE_BASES[price_basis] != "RAW":
                point.update({name: _number(row.get(f"adj_{name}")) if has_row else None for name in ("open", "high", "low", "close")})
        if "ma" in fields:
            point.update({f"ma{width}": _number(row.get(f"ma{width}")) if has_row else None for width in (5, 10, 20, 60)})
        if "amount" in fields:
            point.update({"amount": _number(row.get("raw_amount")) if has_row else None, "volume": _number(row.get("raw_volume")) if has_row else None})
        if "rps" in fields:
            point["rps20"] = (rps_by_date or {}).get(trade_date)
        points.append(point)
    return {
        "contract_id": CONTRACT_VERSION,
        "price_basis": PRICE_BASES[price_basis],
        "adjustment_as_of": cutoff.isoformat() if PRICE_BASES[price_basis] != "RAW" else None,
        "chart_basis": "RAW_UNADJUSTED" if PRICE_BASES[price_basis] == "RAW" else f"{PRICE_BASES[price_basis]}@{cutoff.isoformat()}",
        "fields": list(fields),
        "returned_range": {"start": display_dates[0].isoformat() if display_dates else None, "end": display_dates[-1].isoformat() if display_dates else None},
        "gaps": gaps,
        "points": points,
    }

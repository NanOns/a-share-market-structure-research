"""M8A-01 technical history contract and deterministic factor producer."""

from __future__ import annotations

import json
from typing import Any, Iterable

import numpy as np
import pandas as pd


CONTRACT_VERSION = "TECHNICAL_HISTORY_V2_1_PREVIEW"
PRICE_BASIS = "TDX_NATIVE_QFQ"
WINDOWS = (5, 10, 20, 60)


def _finite(value: Any) -> bool:
    try:
        return bool(pd.notna(value) and np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _window_complete(values: pd.Series, width: int) -> pd.Series:
    return values.rolling(width, min_periods=width).count().eq(width)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator / denominator
    return result.where(denominator > 0)


def amount_class(value: Any) -> str | None:
    if not _finite(value):
        return None
    value = float(value)
    if value < 1.5:
        return "NORMAL"
    if value < 2:
        return "INCREASED"
    if value < 3:
        return "NOTABLE"
    return "SIGNIFICANT"


def ma_alignment(values: Iterable[Any]) -> str | None:
    values = tuple(values)
    if any(not _finite(value) for value in values):
        return None
    ma5, ma10, ma20, ma60 = (float(value) for value in values)
    if ma5 > ma10 > ma20 > ma60:
        return "BULLISH"
    if ma5 < ma10 < ma20 < ma60:
        return "BEARISH"
    return "MIXED"


def _quality_for_row(row: pd.Series) -> list[str]:
    flags: set[str] = set()
    for name in ("ma5", "ma10", "ma20", "ma60", "ret5", "ret10", "ret20", "ret60"):
        if not _finite(row.get(name)):
            flags.add("INSUFFICIENT_HISTORY")
    if not _finite(row.get("raw_close")) or not _finite(row.get("adj_close")):
        flags.add("MISSING_CLOSE")
    quality = row.get("data_quality_flag")
    if quality not in (None, "", "OK"):
        flags.add(str(quality))
    if row.get("is_synthetic_fill") is True:
        flags.add("SYNTHETIC_INPUT_PRESENT")
    return sorted(flags)


def calculate_technical_daily(frame: pd.DataFrame, *, cutoff: Any | None = None) -> pd.DataFrame:
    """Calculate M8A-01 factors without skipping missing rows or future data."""
    required = {"security_id", "date", "adj_close", "raw_close", "raw_amount", "raw_volume"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("TECHNICAL_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    if cutoff is not None:
        cutoff_date = pd.Timestamp(cutoff).date()
        if (work["date"] > cutoff_date).any():
            raise ValueError("FUTURE_TECHNICAL_INPUT")
    work = work.sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)
    outputs: list[pd.DataFrame] = []
    for security_id, group in work.groupby("security_id", sort=False, dropna=False):
        group = group.copy().reset_index(drop=True)
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        amount = pd.to_numeric(group["raw_amount"], errors="coerce")
        volume = pd.to_numeric(group["raw_volume"], errors="coerce")
        previous = pd.to_numeric(group["quote_prev_close"], errors="coerce") if "quote_prev_close" in group else pd.Series(np.nan, index=group.index)
        group["quote_ret1"] = pd.to_numeric(group["raw_close"], errors="coerce") / previous - 1
        for width in WINDOWS:
            group[f"ma{width}"] = close.rolling(width, min_periods=width).mean()
            group[f"ret{width}"] = close / close.shift(width) - 1
            group.loc[~_window_complete(close, width + 1), f"ret{width}"] = np.nan
            group[f"amount_ma{width}"] = amount.rolling(width, min_periods=width).mean()
        group["amount_ratio20"] = _safe_ratio(amount, group["amount_ma20"])
        group["amount_vs_prior20"] = _safe_ratio(amount, amount.shift(1).rolling(20, min_periods=20).mean())
        group["volume_vs_prior20"] = _safe_ratio(volume, volume.shift(1).rolling(20, min_periods=20).mean())
        group["amount_class"] = group["amount_vs_prior20"].map(amount_class)
        group["ma_alignment"] = group[[f"ma{n}" for n in WINDOWS]].apply(ma_alignment, axis=1)
        group["validity"] = "INSUFFICIENT"
        group.loc[group[[f"ma{n}" for n in WINDOWS]].notna().any(axis=1), "validity"] = "PARTIAL"
        group.loc[group[[f"ma{n}" for n in WINDOWS]].notna().all(axis=1), "validity"] = "VALID"
        group["security_id"] = security_id
        outputs.append(group)
    result = pd.concat(outputs, ignore_index=True) if outputs else work.copy()
    result["technical_contract_id"] = CONTRACT_VERSION
    result["price_basis"] = PRICE_BASIS
    result["quality_codes"] = result.apply(_quality_for_row, axis=1)
    result["basis_json"] = result.apply(lambda row: {
        "contract_id": CONTRACT_VERSION,
        "price_basis": PRICE_BASIS,
        "calendar_basis": "MASTER_TRADING_CALENDAR",
        "include_current_observation": True,
        "amount_ratio20": "CURRENT_DIVIDED_BY_CURRENT_INCLUSIVE_20_DAY_MEAN",
        "amount_vs_prior20": "CURRENT_DIVIDED_BY_PRIOR_EXCLUSIVE_20_DAY_MEAN",
        "volume_vs_prior20": "CURRENT_DIVIDED_BY_PRIOR_EXCLUSIVE_20_DAY_MEAN",
    }, axis=1)
    return result.sort_values(["date", "security_id"], kind="mergesort").reset_index(drop=True)


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    """Convert calculated rows into the immutable 008 table shape."""
    names = (
        "raw_close", "adj_close", "quote_ret1", "raw_amount", "raw_volume",
        "ma5", "ma10", "ma20", "ma60", "ret5", "ret10", "ret20", "ret60",
        "rs5", "rs10", "rs20", "rs60", "amount_ma5", "amount_ma10", "amount_ma20",
        "amount_ratio20", "amount_vs_prior20", "volume_vs_prior20",
    )
    rows = []
    for _, row in frame.iterrows():
        values = [None if not _finite(row.get(name)) else float(row[name]) for name in names]
        rows.append(tuple(
            [slice_id, row["security_id"], row["date"], CONTRACT_VERSION, PRICE_BASIS]
            + values
            + [row.get("amount_class"), row.get("ma_alignment"), row["validity"],
               json.dumps(row["quality_codes"], ensure_ascii=False),
               json.dumps(row["basis_json"], ensure_ascii=False, sort_keys=True)]
        ))
    return rows


def insert_technical_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert a complete immutable slice, rejecting any existing conflict."""
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select security_id,trade_date from stock_technical_daily where slice_id=?", [slice_id]
    ).fetchall()
    expected_keys = {(str(row[1]), str(row[2])) for row in rows}
    actual_keys = {(str(row[0]), str(row[1])) for row in existing}
    if actual_keys and actual_keys != expected_keys:
        raise ValueError("TECHNICAL_SLICE_IDENTITY_CONFLICT")
    if actual_keys:
        return len(rows)
    connection.executemany(
        "insert into stock_technical_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)

"""M8A-02 close-based new-high states."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "TECHNICAL_HISTORY_V2_1_PREVIEW"
PRICE_BASIS = "TDX_NATIVE_QFQ"
WINDOWS = (20, 30, 60, 100)


def _finite(value: Any) -> bool:
    try:
        return bool(pd.notna(value) and np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def calculate_high_daily(frame: pd.DataFrame, *, cutoff: Any | None = None) -> pd.DataFrame:
    """Calculate strict prior-window close highs without using the current bar."""
    required = {"security_id", "date", "adj_close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("HIGH_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    if cutoff is not None and (work["date"] > pd.Timestamp(cutoff).date()).any():
        raise ValueError("FUTURE_HIGH_INPUT")
    work = work.sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)
    outputs: list[pd.DataFrame] = []
    for security_id, group in work.groupby("security_id", sort=False, dropna=False):
        group = group.copy().reset_index(drop=True)
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        for width in WINDOWS:
            prior = close.shift(1).rolling(width, min_periods=width).max()
            valid_n = close.shift(1).rolling(width, min_periods=0).count().astype(int)
            complete = valid_n.eq(width) & close.notna() & prior.notna()
            new_high = (close > prior).where(complete)
            at_prior_high = (close == prior).where(complete)
            streak: list[int | None] = []
            for index, is_new in enumerate(new_high.tolist()):
                if is_new is not True:
                    streak.append(0 if is_new is False else None)
                    continue
                previous = streak[index - 1] if index else None
                previous_new = bool(new_high.iloc[index - 1]) if index else False
                streak.append(int(previous) + 1 if previous_new and previous is not None else 1)
            group[f"prior_max_close_{width}"] = prior
            group[f"new_high_{width}"] = new_high
            group[f"at_prior_high_{width}"] = at_prior_high
            group[f"high_streak_{width}"] = streak
            group[f"is_left_censored_{width}"] = ~complete & (valid_n < width)
            group[f"dist_prior_high_{width}"] = (close / prior - 1).where(complete & (prior > 0))
            group[f"high_valid_n_{width}"] = valid_n
        group["security_id"] = security_id
        outputs.append(group)
    result = pd.concat(outputs, ignore_index=True) if outputs else work.copy()
    result["high_contract_id"] = CONTRACT_VERSION
    result["high_price_basis"] = PRICE_BASIS
    return result.sort_values(["date", "security_id"], kind="mergesort").reset_index(drop=True)


def high_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    rows = []
    for _, row in frame.iterrows():
        for width in WINDOWS:
            values = [row.get(f"prior_max_close_{width}"), row.get(f"dist_prior_high_{width}")]
            values = [None if not _finite(value) else float(value) for value in values]
            valid_n = int(row.get(f"high_valid_n_{width}") or 0)
            quality = [] if valid_n == width and _finite(row.get("adj_close")) else ["INSUFFICIENT_HISTORY"]
            rows.append((
                slice_id, row["security_id"], row["date"], width, CONTRACT_VERSION, PRICE_BASIS,
                values[0], None if pd.isna(row.get(f"new_high_{width}")) else bool(row[f"new_high_{width}"]),
                None if pd.isna(row.get(f"at_prior_high_{width}")) else bool(row[f"at_prior_high_{width}"]),
                None if pd.isna(row.get(f"high_streak_{width}")) else int(row[f"high_streak_{width}" ]),
                bool(row[f"is_left_censored_{width}"]), values[1], valid_n,
                json.dumps(quality), json.dumps({
                    "contract_id": CONTRACT_VERSION, "price_basis": PRICE_BASIS,
                    "comparison": "ADJ_CLOSE_T_GREATER_THAN_PRIOR_N_CLOSES",
                    "ties_are_not_new_high": True, "window": width,
                }, sort_keys=True),
            ))
    return rows


def insert_high_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = high_rows_for_storage(frame, slice_id)
    existing = connection.execute('select * from stock_high_daily where slice_id=?', [slice_id]).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3), conflict_code="HIGH_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany("insert into stock_high_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)

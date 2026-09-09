"""M8A-02 cross-sectional RS/RPS calculations."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .technical import CONTRACT_VERSION, PRICE_BASIS, WINDOWS, calculate_technical_daily


def average_rank_percentile(values: pd.Series) -> pd.Series:
    """Average-tie rank divided by N, as required by the public contract."""
    return values.rank(method="average", ascending=True, na_option="keep") / values.notna().sum()


def calculate_strength_daily(frame: pd.DataFrame, *, cutoff: Any | None = None, min_universe: int = 100) -> pd.DataFrame:
    """Add RS and RPS using only same-date eligible securities."""
    result = calculate_technical_daily(frame, cutoff=cutoff)
    for width in WINDOWS:
        ret = f"ret{width}"
        rs = f"rs{width}"
        rps = f"rps{width}"
        count_name = f"rps_valid_universe_count{width}"
        result[count_name] = 0
        result[rps] = np.nan
        result[rs] = np.nan
        for trade_date, indexes in result.groupby("date", sort=False).groups.items():
            subset = result.loc[list(indexes)]
            if "universe_status" in subset:
                eligible = subset["universe_status"].eq("IN_NORMAL_UNIVERSE")
            else:
                eligible = pd.Series(True, index=subset.index)
            eligible &= subset[ret].notna()
            valid = subset.loc[eligible, ret]
            count = int(valid.notna().sum())
            result.loc[list(indexes), count_name] = count
            if count < min_universe:
                continue
            median = float(valid.median())
            result.loc[valid.index, rs] = valid - median
            result.loc[valid.index, rps] = average_rank_percentile(valid)
    result["strength_contract_id"] = CONTRACT_VERSION
    result["strength_price_basis"] = PRICE_BASIS
    result["strength_quality_codes"] = result.apply(lambda row: [f"INSUFFICIENT_RPS_UNIVERSE_{width}" for width in WINDOWS if int(row[f"rps_valid_universe_count{width}"]) < min_universe], axis=1)
    result["strength_basis_json"] = result.apply(lambda row: {
        "contract_id": CONTRACT_VERSION, "price_basis": PRICE_BASIS,
        "rps": "AVERAGE_TIE_RANK_DIVIDED_BY_SAME_DATE_VALID_N",
        "rps_min_universe": min_universe, "rs": "RET_MINUS_SAME_DATE_VALID_MEDIAN",
    }, axis=1)
    return result


def strength_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    rows = []
    factor_names = tuple(f"ret{n}" for n in WINDOWS) + tuple(f"rs{n}" for n in WINDOWS) + tuple(f"rps{n}" for n in WINDOWS)
    for _, row in frame.iterrows():
        values = [None if pd.isna(row.get(name)) else float(row[name]) for name in factor_names]
        counts = [int(row.get(f"rps_valid_universe_count{n}") or 0) for n in WINDOWS]
        rows.append(tuple(
            [slice_id, row["security_id"], row["date"], CONTRACT_VERSION, PRICE_BASIS]
            + values + counts
            + [json.dumps(row["strength_quality_codes"], ensure_ascii=False), json.dumps(row["strength_basis_json"], ensure_ascii=False, sort_keys=True)]
        ))
    return rows


def insert_strength_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = strength_rows_for_storage(frame, slice_id)
    existing = connection.execute("select security_id,trade_date from stock_strength_daily where slice_id=?", [slice_id]).fetchall()
    expected = {(str(row[1]), str(row[2])) for row in rows}
    actual = {(str(row[0]), str(row[1])) for row in existing}
    if actual and actual != expected:
        raise ValueError("STRENGTH_SLICE_IDENTITY_CONFLICT")
    if actual:
        return len(rows)
    connection.executemany("insert into stock_strength_daily values (?,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?,?,? ,?,?)", rows)
    return len(rows)

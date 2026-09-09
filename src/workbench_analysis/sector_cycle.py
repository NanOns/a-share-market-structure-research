"""M9-01 deterministic sector-day vectors.

This module only computes the daily sector vector.  It does not infer member
state changes, representatives, or mainline classes, and it never treats a
member statistic as a board quote.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "SECTOR_CYCLE_V1_0_DAILY_VECTOR"
HISTORY_BASIS = "RECONSTRUCTED"


class SectorCycleError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _median(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce")
    values = values[np.isfinite(values)]
    return float(values.median()) if len(values) else None


def _percentile(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    valid = numeric.notna() & np.isfinite(numeric)
    n = int(valid.sum())
    if n:
        result.loc[valid] = numeric.loc[valid].rank(method="average", ascending=True) / n
    return result


def _normalise(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise SectorCycleError(f"{label}_COLUMNS_MISSING:" + ",".join(missing))
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    if result["trade_date"].isna().any():
        raise SectorCycleError(f"{label}_DATE_INVALID")
    if "security_id" in result:
        result["security_id"] = result["security_id"].astype(str)
    return result


def _validate_cutoff(frame: pd.DataFrame, cutoff: Any | None) -> None:
    if cutoff is not None and (frame["trade_date"] > pd.Timestamp(cutoff).date()).any():
        raise SectorCycleError("FUTURE_SECTOR_CYCLE_INPUT")


def build_sector_cycle_daily(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    cutoff: Any | None = None,
    board_quotes: pd.DataFrame | None = None,
    history_basis: str = HISTORY_BASIS,
) -> pd.DataFrame:
    """Build one explainable vector per sector and trading date.

    ``memberships`` is the point-in-time membership input.  A security is
    counted once per sector/date, while a security shared by different sectors
    remains present in each sector.  ``board_quotes`` is optional and is kept
    separate from member distribution statistics.
    """
    if history_basis != HISTORY_BASIS:
        raise SectorCycleError("SECTOR_CYCLE_REQUIRES_RECONSTRUCTED_HISTORY")
    tech = _normalise(technical, ("security_id", "trade_date"), "TECHNICAL")
    members = _normalise(memberships, ("security_id", "trade_date", "sector_id"), "MEMBERSHIP")
    _validate_cutoff(tech, cutoff)
    _validate_cutoff(members, cutoff)
    if tech.duplicated(["security_id", "trade_date"]).any():
        raise SectorCycleError("TECHNICAL_DUPLICATE_SECURITY_DATE")
    if members.duplicated(["sector_id", "security_id", "trade_date"]).any():
        duplicate = members[members.duplicated(["sector_id", "security_id", "trade_date"], keep=False)]
        stable_columns = [column for column in ("sector_name", "sector_type", "sector_role") if column in duplicate.columns]
        if stable_columns and duplicate.groupby(["sector_id", "security_id", "trade_date"])[stable_columns].nunique(dropna=False).max().max() > 1:
            raise SectorCycleError("MEMBERSHIP_DUPLICATE_CONFLICT")
        members = members.drop_duplicates(["sector_id", "security_id", "trade_date"], keep="first")
    if board_quotes is not None:
        quotes = _normalise(board_quotes, ("sector_id", "trade_date"), "BOARD_QUOTE")
        _validate_cutoff(quotes, cutoff)
        if quotes.duplicated(["sector_id", "trade_date"]).any():
            raise SectorCycleError("BOARD_QUOTE_DUPLICATE_SECTOR_DATE")
    else:
        quotes = pd.DataFrame(columns=["sector_id", "trade_date", "board_quote_ret1", "board_quote_source"])

    join_columns = ["security_id", "trade_date"]
    merged = members.merge(tech, on=join_columns, how="left", suffixes=("", "_technical"))
    if "sector_type" not in merged:
        merged["sector_type"] = "OTHER"
    merged["sector_type"] = merged["sector_type"].fillna("OTHER").astype(str)
    if "sector_name" not in merged:
        merged["sector_name"] = merged["sector_id"].astype(str)
    merged["sector_name"] = merged["sector_name"].fillna(merged["sector_id"]).astype(str)

    def column(*names: str) -> pd.Series:
        for name in names:
            if name in merged:
                return pd.to_numeric(merged[name], errors="coerce")
        return pd.Series(np.nan, index=merged.index, dtype="float64")

    merged["member_ret1"] = column("ret1", "RET1", "quote_ret1")
    merged["member_ret5"] = column("ret5", "RET5")
    merged["member_ret20"] = column("ret20", "RET20")
    merged["member_rs5"] = column("rs5", "stock_rs5")
    merged["member_rs20"] = column("rs20", "stock_rs20")
    merged["member_amount"] = column("raw_amount", "amount", "turnover_amount")
    merged["member_ma20"] = column("ma20")

    rows: list[dict[str, Any]] = []
    for (sector_id, trade_date), group in merged.groupby(["sector_id", "trade_date"], sort=True):
        group = group.copy()
        sector_type = str(group["sector_type"].iloc[0])
        sector_name = str(group["sector_name"].iloc[0])
        quote = quotes[(quotes.sector_id == sector_id) & (quotes.trade_date == trade_date)]
        board_ret = quote.iloc[0].get("board_quote_ret1") if len(quote) else None
        board_source = quote.iloc[0].get("board_quote_source") if len(quote) and "board_quote_source" in quote else None
        ret1_valid = group.member_ret1.map(_finite)
        ret20_valid = group.member_ret20.map(_finite)
        amount_valid = group.member_amount.map(_finite) & group.member_amount.gt(0)
        ma_valid = group.member_ma20.map(_finite) & group.member_ret1.map(_finite)
        rs5 = group.member_rs5.where(group.member_rs5.map(_finite), group.member_ret5)
        rs20 = group.member_rs20.where(group.member_rs20.map(_finite), group.member_ret20)
        vector_rs5 = _median(rs5)
        vector_rs20 = _median(rs20)
        rows.append({
            "sector_id": str(sector_id), "trade_date": trade_date, "sector_name": sector_name,
            "sector_type": sector_type, "history_basis": history_basis, "contract_id": CONTRACT_VERSION,
            "board_quote_ret1": float(board_ret) if _finite(board_ret) else None,
            "board_quote_source": str(board_source) if board_source is not None else None,
            "member_ret1_median": _median(group.member_ret1), "member_ret5_median": _median(group.member_ret5),
            "member_ret20_median": _median(group.member_ret20),
            "member_amount_sum": float(group.loc[amount_valid, "member_amount"].sum()) if amount_valid.any() else None,
            "amount_valid_count": int(amount_valid.sum()), "total_member_count": int(len(group)),
            "quote_valid_count": int(ret1_valid.sum()), "factor_valid_count": int(ret20_valid.sum()),
            "coverage": float(ret20_valid.sum() / len(group)) if len(group) else None,
            "breadth_ret1": float((group.loc[ret1_valid, "member_ret1"] > 0).mean()) if ret1_valid.any() else None,
            "breadth_ma20": float((group.loc[ma_valid, "member_ret1"] > group.loc[ma_valid, "member_ma20"]).mean()) if ma_valid.any() else None,
            "sector_rs5": vector_rs5, "sector_rs20": vector_rs20,
            "amount_vs_prior20": None, "rank": None, "rank_change": None,
            "window_stats": json.dumps({str(window): {"valid_days": None, "on_list_days": None, "consecutive_on_list": None, "rank_pct_mean": None, "rank_pct_first": None, "rank_pct_last": None, "breadth_change": None, "amount_change": None} for window in (5, 10, 20, 30)}, sort_keys=True),
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["sector_rs5_pct"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs5"].transform(_percentile)
    result["sector_rs20_pct"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs20"].transform(_percentile)
    result["rank"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs20"].rank(method="average", ascending=False, na_option="keep")
    result["rank"] = result["rank"].where(result["rank"].notna(), None)
    result["rank_change"] = result.sort_values(["sector_id", "trade_date"]).groupby("sector_id")["rank"].shift(1) - result["rank"]
    result = result.sort_values(["trade_date", "sector_type", "rank" , "sector_id"], na_position="last", kind="mergesort").reset_index(drop=True)
    return result


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    columns = ("sector_id", "trade_date", "sector_name", "sector_type", "history_basis", "contract_id", "board_quote_ret1", "board_quote_source", "member_ret1_median", "member_ret5_median", "member_ret20_median", "member_amount_sum", "amount_valid_count", "total_member_count", "quote_valid_count", "factor_valid_count", "coverage", "breadth_ret1", "breadth_ma20", "sector_rs5", "sector_rs20", "sector_rs5_pct", "sector_rs20_pct", "amount_vs_prior20", "rank", "rank_change", "window_stats")
    return [tuple([slice_id] + [row.get(column) for column in columns]) for _, row in frame.iterrows()]


def insert_sector_cycle_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from sector_cycle_daily where slice_id=?", [slice_id]).fetchall()
    try:
        present = immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="SECTOR_CYCLE_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise SectorCycleError(str(exc)) from exc
    if present:
        return len(rows)
    connection.executemany("insert into sector_cycle_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)

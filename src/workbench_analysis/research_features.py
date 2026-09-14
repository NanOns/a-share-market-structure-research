"""V3 P05-01 run-bound stock research feature inputs.

Pure calculation only: no database, network, publication lookup, or writes.
Windows align to the supplied master sessions, so missing sessions are not
silently compressed out of rolling calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Iterable

import numpy as np
import pandas as pd


CONTRACT_ID = "RESEARCH_FEATURES_PREVIEW_1"
PRICE_BASIS = "TDX_NATIVE_QFQ"


class ResearchFeatureError(ValueError):
    pass


@dataclass(frozen=True)
class ResearchFeatureContext:
    run_id: str
    publication_id: str
    snapshot_id: str
    relation_revision: str
    calendar_id: str
    cutoff_date: str

    def __post_init__(self) -> None:
        for name in ("run_id", "publication_id", "snapshot_id", "relation_revision", "calendar_id"):
            if not str(getattr(self, name)).strip():
                raise ResearchFeatureError(f"CONTEXT_ID_REQUIRED:{name}")
        try:
            normalized = date.fromisoformat(str(self.cutoff_date)).isoformat()
        except ValueError as exc:
            raise ResearchFeatureError(f"CUTOFF_DATE_INVALID:{self.cutoff_date}") from exc
        object.__setattr__(self, "cutoff_date", normalized)


def _date_column(frame: pd.DataFrame) -> str:
    for name in ("trade_date", "date"):
        if name in frame.columns:
            return name
    raise ResearchFeatureError("TRADE_DATE_COLUMN_REQUIRED")


def _sessions(values: Iterable[date | str], cutoff: str) -> tuple[str, ...]:
    result = []
    for value in values:
        try:
            item = value.isoformat() if isinstance(value, date) else date.fromisoformat(str(value)).isoformat()
        except ValueError as exc:
            raise ResearchFeatureError(f"CALENDAR_DATE_INVALID:{value}") from exc
        if item <= cutoff:
            result.append(item)
    ordered = tuple(sorted(set(result)))
    if not ordered or ordered[-1] != cutoff:
        raise ResearchFeatureError("CUTOFF_NOT_IN_MASTER_CALENDAR")
    return ordered


def _number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if math.isfinite(result) else np.nan


def _ratio(numerator: float, denominator: float) -> float | None:
    if np.isfinite(numerator) and np.isfinite(denominator) and denominator > 0:
        return float(numerator / denominator)
    return None


def build_stock_research_features(
    raw_daily: pd.DataFrame,
    relative_strength: pd.DataFrame,
    master_sessions: Iterable[date | str],
    context: ResearchFeatureContext,
    *, liquidity20_amount_gte: float = 20_000_000.0,
) -> pd.DataFrame:
    """Return one cutoff feature row per stock from raw run-bound inputs."""

    raw_date = _date_column(raw_daily)
    missing = sorted({"security_id", raw_date, "adj_close", "raw_amount"} - set(raw_daily.columns))
    if missing:
        raise ResearchFeatureError("RAW_COLUMNS_MISSING:" + ",".join(missing))
    rs_date = _date_column(relative_strength)
    missing = sorted({"security_id", rs_date, "rps5", "rps20"} - set(relative_strength.columns))
    if missing:
        raise ResearchFeatureError("RS_COLUMNS_MISSING:" + ",".join(missing))
    sessions = _sessions(master_sessions, context.cutoff_date)

    raw = raw_daily.copy()
    raw[raw_date] = pd.to_datetime(raw[raw_date], errors="raise").dt.date.astype(str)
    raw["security_id"] = raw["security_id"].astype(str)
    raw = raw[raw[raw_date] <= context.cutoff_date].copy()
    if raw.duplicated(["security_id", raw_date]).any():
        raise ResearchFeatureError("RAW_DUPLICATE_KEY")
    rs = relative_strength.copy()
    rs[rs_date] = pd.to_datetime(rs[rs_date], errors="raise").dt.date.astype(str)
    rs["security_id"] = rs["security_id"].astype(str)
    rs = rs[rs[rs_date] <= context.cutoff_date].copy()
    if rs.duplicated(["security_id", rs_date]).any():
        raise ResearchFeatureError("RS_DUPLICATE_KEY")

    rows = []
    security_ids = sorted(set(raw.loc[raw[raw_date].eq(context.cutoff_date), "security_id"]))
    raw_by_security = {key: group for key, group in raw.groupby("security_id", sort=False)}
    rs_by_security = {key: group for key, group in rs.groupby("security_id", sort=False)}
    for security_id in security_ids:
        stock = raw_by_security[security_id].set_index(raw_date).reindex(sessions)
        close = stock.adj_close.map(_number).astype(float)
        amount = stock.raw_amount.map(_number).astype(float)
        actual = pd.Series(True, index=stock.index)
        for column in ("has_actual_bar", "tradable", "data_observed"):
            if column in stock:
                actual &= stock[column].eq(True)
        if "is_synthetic_fill" in stock:
            actual &= ~stock.is_synthetic_fill.eq(True)
        close = close.where(actual)
        amount = amount.where(actual)
        bases = stock.price_basis.astype("string") if "price_basis" in stock else pd.Series(pd.NA, index=stock.index)
        statuses = stock.adjustment_status.astype("string") if "adjustment_status" in stock else pd.Series(pd.NA, index=stock.index)
        projects = stock.project_price_basis.astype("string") if "project_price_basis" in stock else pd.Series(pd.NA, index=stock.index)
        versions = stock.adjustment_version.astype("string") if "adjustment_version" in stock else pd.Series(pd.NA, index=stock.index)
        observed_window = actual.iloc[-101:]
        basis_valid = bool(observed_window.any()) and bool(bases.iloc[-101:][observed_window].eq(PRICE_BASIS).fillna(False).all())
        basis_valid &= bool(statuses.iloc[-101:][observed_window].eq("VERIFIED_REPRODUCIBLE_TDX_NATIVE").fillna(False).all())
        basis_valid &= bool(projects.iloc[-101:][observed_window].eq("FORWARD_ADJUSTED").fillna(False).all())
        version_values = versions.iloc[-101:][observed_window]
        basis_valid &= bool(version_values.notna().all() and len(version_values.unique()) == 1)
        if not basis_valid:
            close[:] = np.nan

        ma5 = close.rolling(5, min_periods=5).mean()
        ma20 = close.rolling(20, min_periods=20).mean()
        current = close.iloc[-1]
        prior_high = close.shift().rolling(20, min_periods=20).max().iloc[-1]
        prior_amount_mean = amount.shift().rolling(20, min_periods=20).mean().iloc[-1]
        prior_amount_median = amount.shift().rolling(20, min_periods=20).median().iloc[-1]
        sigma = np.log(close / close.shift()).rolling(20, min_periods=20).std(ddof=0).iloc[-1]
        r5min, r5max = close.rolling(5, min_periods=5).min().iloc[-1], close.rolling(5, min_periods=5).max().iloc[-1]
        r20min, r20max = close.rolling(20, min_periods=20).min().iloc[-1], close.rolling(20, min_periods=20).max().iloc[-1]
        bias_ratio = _ratio(current, ma20.iloc[-1])
        bias20 = None if bias_ratio is None else bias_ratio - 1.0
        sigma20 = float(sigma) if np.isfinite(sigma) else None
        extension = None
        if bias_ratio is not None and sigma20 is not None and sigma20 > 0:
            extension = float(math.log(bias_ratio) / (sigma20 * math.sqrt(20)))

        stock_rs_source = rs_by_security.get(security_id)
        stock_rs = (
            stock_rs_source.set_index(rs_date).reindex(sessions)
            if stock_rs_source is not None
            else pd.DataFrame(index=sessions, columns=["rps5", "rps20"])
        )
        rps5 = stock_rs.rps5.map(_number).astype(float)
        rps20 = stock_rs.rps20.map(_number).astype(float)
        rps_delta = None
        if len(sessions) >= 4 and np.isfinite(rps5.iloc[-1]) and np.isfinite(rps5.iloc[-4]):
            rps_delta = float(rps5.iloc[-1] - rps5.iloc[-4])

        turnover = _number(stock.turnover.iloc[-1]) if "turnover" in stock else np.nan
        turnover_basis = str(stock.turnover_basis.iloc[-1]) if "turnover_basis" in stock and pd.notna(stock.turnover_basis.iloc[-1]) else None
        if np.isfinite(turnover) and not turnover_basis:
            raise ResearchFeatureError(f"TURNOVER_BASIS_REQUIRED:{security_id}")
        quality_codes = []
        if not basis_valid:
            quality_codes.append("PRICE_BASIS_MISMATCH")
        if not np.isfinite(current):
            quality_codes.append("CURRENT_QUOTE_UNAVAILABLE")
        high100_complete = bool(len(sessions) >= 101 and close.iloc[-101:].notna().all())
        if not high100_complete:
            quality_codes.append("HIGH100_INPUT_INCOMPLETE")

        ret5_ratio = _ratio(current, close.iloc[-6]) if len(sessions) >= 6 else None
        high_ratio = _ratio(current, prior_high)
        range5_ratio, range20_ratio = _ratio(r5max, r5min), _ratio(r20max, r20min)
        rows.append({
            "contract_id": CONTRACT_ID,
            "run_id": context.run_id,
            "publication_id": context.publication_id,
            "snapshot_id": context.snapshot_id,
            "relation_revision": context.relation_revision,
            "calendar_id": context.calendar_id,
            "trade_date": context.cutoff_date,
            "security_id": security_id,
            "price_basis": PRICE_BASIS if basis_valid else None,
            "close": float(current) if np.isfinite(current) else None,
            "close_prior1": float(close.iloc[-2]) if len(sessions) >= 2 and np.isfinite(close.iloc[-2]) else None,
            "ret5": None if ret5_ratio is None else ret5_ratio - 1.0,
            "ma5": float(ma5.iloc[-1]) if np.isfinite(ma5.iloc[-1]) else None,
            "ma5_prior1": float(ma5.iloc[-2]) if len(sessions) >= 2 and np.isfinite(ma5.iloc[-2]) else None,
            "ma20": float(ma20.iloc[-1]) if np.isfinite(ma20.iloc[-1]) else None,
            "ma20_prior1": float(ma20.iloc[-2]) if len(sessions) >= 2 and np.isfinite(ma20.iloc[-2]) else None,
            "ma20_prior3": float(ma20.iloc[-4]) if len(sessions) >= 4 and np.isfinite(ma20.iloc[-4]) else None,
            "ma20_prior5": float(ma20.iloc[-6]) if len(sessions) >= 6 and np.isfinite(ma20.iloc[-6]) else None,
            "bias20": bias20,
            "sigma20": sigma20,
            "extension_z20": extension,
            "dist_high20": None if high_ratio is None else high_ratio - 1.0,
            "prior_high20": float(prior_high) if np.isfinite(prior_high) else None,
            "range5": None if range5_ratio is None else range5_ratio - 1.0,
            "range20": None if range20_ratio is None else range20_ratio - 1.0,
            "amount": float(amount.iloc[-1]) if np.isfinite(amount.iloc[-1]) else None,
            "amount_prior20_median": float(prior_amount_median) if np.isfinite(prior_amount_median) else None,
            "amount_vs_prior20": _ratio(amount.iloc[-1], prior_amount_mean),
            "liquidity20": None if not np.isfinite(prior_amount_median) else bool(prior_amount_median >= liquidity20_amount_gte),
            "rps5": float(rps5.iloc[-1]) if np.isfinite(rps5.iloc[-1]) else None,
            "rps20": float(rps20.iloc[-1]) if np.isfinite(rps20.iloc[-1]) else None,
            "rps5_delta3": rps_delta,
            "turnover": float(turnover) if np.isfinite(turnover) else None,
            "turnover_basis": turnover_basis,
            "high100_input_complete": high100_complete,
            "quality": "READY" if not quality_codes else "PARTIAL",
            "quality_codes": quality_codes,
        })
    return pd.DataFrame(rows)


__all__ = ["CONTRACT_ID", "PRICE_BASIS", "ResearchFeatureContext", "ResearchFeatureError", "build_stock_research_features"]

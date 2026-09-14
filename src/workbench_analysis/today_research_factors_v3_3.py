"""P12-02 candidate facts on a single, cutoff-anchored master-calendar window.

No source lookup, database access, sector membership, or publication side effect.
The caller supplies adjusted OHLC rebuilt at the target cutoff and one slot for
every master session; a missing real bar invalidates only the affected window.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from statistics import mean, median, pstdev, stdev
from typing import Any


CONTRACT_ID = "TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01"
PRICE_BASIS = "TDX_NATIVE_AFFINE_QFQ"


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _actual(row: Mapping[str, Any]) -> bool:
    return row.get("has_actual_bar") is True and row.get("is_synthetic_fill") is not True


def _window(rows: Sequence[Mapping[str, Any]], start: int, end: int,
            fields: tuple[str, ...]) -> list[Mapping[str, Any]] | None:
    selected = list(rows[start:end])
    if len(selected) != end - start or not all(_actual(row) for row in selected):
        return None
    if any(_positive(row.get(field)) is None for row in selected for field in fields):
        return None
    return selected


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    return numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None


def _or(left: bool | None, right: bool | None) -> bool | None:
    if left is True or right is True:
        return True
    if left is None or right is None:
        return None
    return False


def calculate_today_facts(rows: Sequence[Mapping[str, Any]], *,
                          liquidity20_amount_gte: float = 20_000_000.0,
                          drop_floor_pct: float = 0.04,
                          drop_cap_pct: float = 0.08,
                          drop_z: float = 2.0) -> dict[str, Any]:
    """Calculate target-day facts; rows end at t and contain master-session slots."""
    if not 0 < drop_floor_pct <= drop_cap_pct < 1 or drop_z <= 0 or liquidity20_amount_gte <= 0:
        raise ValueError("INVALID_RISK_PARAMETERS")
    if not rows:
        raise ValueError("EMPTY_MASTER_WINDOW")
    dates = [str(row["date"]) for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError("MASTER_WINDOW_NOT_STRICTLY_ORDERED")
    if any(row.get("anchor_cutoff") != dates[-1] for row in rows):
        raise ValueError("FACTOR_PRICE_ANCHOR_MISMATCH")
    indexes = [row.get("session_index") for row in rows]
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indexes) or indexes != list(range(indexes[0], indexes[0] + len(rows))):
        raise ValueError("FACTOR_MASTER_SESSION_GAP")
    if any(row.get("price_basis") != PRICE_BASIS for row in rows if _actual(row)):
        raise ValueError("MIXED_PRICE_BASIS")
    for row in rows:
        if _actual(row):
            o, hi, lo, close = (_positive(row.get(field)) for field in ("open", "high", "low", "close"))
            if all(value is not None for value in (o, hi, lo, close)) and (
                hi < max(o, lo, close) or lo > min(o, hi, close)
            ):
                raise ValueError("INVALID_ADJUSTED_OHLC")

    t = len(rows)
    today = _window(rows, t - 1, t, ("open", "high", "low", "close", "raw_open", "raw_close", "amount", "volume")) if t >= 1 else None
    prior20 = _window(rows, t - 21, t - 1, ("close", "high", "amount", "volume")) if t >= 21 else None
    ma20_window = _window(rows, t - 20, t, ("close",)) if t >= 20 else None
    ma10_window = _window(rows, t - 10, t, ("close",)) if t >= 10 else None
    ma5_window = _window(rows, t - 5, t, ("close",)) if t >= 5 else None
    prior_ma20_window = _window(rows, t - 21, t - 1, ("close",)) if t >= 21 else None
    prior_ma10_window = _window(rows, t - 11, t - 1, ("close",)) if t >= 11 else None
    prior_ma5_window = _window(rows, t - 6, t - 1, ("close",)) if t >= 6 else None
    hl20_window = _window(rows, t - 20, t, ("high", "low", "close")) if t >= 20 else None
    hl5_window = _window(rows, t - 5, t, ("high", "low", "close")) if t >= 5 else None
    prior5 = _window(rows, t - 6, t - 1, ("amount",)) if t >= 6 else None
    diagnostic_current3 = _window(rows, t - 3, t, ("amount",)) if t >= 3 else None
    diagnostic_prior5 = _window(rows, t - 8, t - 3, ("amount",)) if t >= 8 else None
    prior_sigma_window = _window(rows, t - 22, t - 1, ("close",)) if t >= 22 else None
    sigma_window = _window(rows, t - 21, t, ("close",)) if t >= 21 else None
    c = _positive(today[0]["close"]) if today else None
    h = _positive(today[0]["high"]) if today else None
    l = _positive(today[0]["low"]) if today else None
    amount = _positive(today[0]["amount"]) if today else None
    volume = _positive(today[0]["volume"]) if today else None
    prior_close = _positive(rows[t - 2].get("close")) if t >= 2 and _actual(rows[t - 2]) else None

    ma20 = mean(float(row["close"]) for row in ma20_window) if ma20_window else None
    ma10 = mean(float(row["close"]) for row in ma10_window) if ma10_window else None
    ma5 = mean(float(row["close"]) for row in ma5_window) if ma5_window else None
    prior_ma20 = mean(float(row["close"]) for row in prior_ma20_window) if prior_ma20_window else None
    prior_ma10 = mean(float(row["close"]) for row in prior_ma10_window) if prior_ma10_window else None
    prior_ma5 = mean(float(row["close"]) for row in prior_ma5_window) if prior_ma5_window else None
    phc20 = max(float(row["close"]) for row in prior20) if prior20 else None
    phh20 = max(float(row["high"]) for row in prior20) if prior20 else None
    prior_amount_mean = mean(float(row["amount"]) for row in prior20) if prior20 else None
    prior_amount_median = median(float(row["amount"]) for row in prior20) if prior20 else None
    prior_volume_mean = mean(float(row["volume"]) for row in prior20) if prior20 else None
    ret1 = _ratio(c, prior_close)
    ret1 = ret1 - 1 if ret1 is not None else None
    logret1 = math.log(c / prior_close) if c is not None and prior_close is not None else None
    bias20 = _ratio(c, ma20)
    bias20 = bias20 - 1 if bias20 is not None else None

    def sigma(window: list[Mapping[str, Any]] | None, ddof: int) -> float | None:
        if window is None:
            return None
        closes = [float(row["close"]) for row in window]
        returns = [math.log(right / left) for left, right in zip(closes, closes[1:])]
        if len(returns) != 20:
            return None
        return pstdev(returns) if ddof == 0 else stdev(returns)

    sigma20 = sigma(sigma_window, 0)
    sigma20_prior = sigma(prior_sigma_window, 0)
    vol20_sample = sigma(sigma_window, 1)
    z20 = math.log(c / ma20) / (sigma20 * math.sqrt(20)) if c and ma20 and sigma20 else None
    clv = (c - l) / (h - l) if c and h and l and h > l else None
    absolute_drop = ret1 <= -drop_cap_pct if ret1 is not None else None
    relative_limit = max(-math.log(1 - drop_floor_pct), drop_z * sigma20_prior) if sigma20_prior is not None else None
    relative_drop = logret1 <= -relative_limit if logret1 is not None and relative_limit is not None else None
    severe_drop = _or(absolute_drop, relative_drop)
    first_day_damage = c / ma20 < 0.97 if c is not None and ma20 is not None else None
    weak_close = clv < 0.30 if clv is not None else None
    amr20 = _ratio(amount, prior_amount_mean)
    heavy_weak = (weak_close and amr20 >= 1.5 and ret1 < 0) if weak_close is not None and amr20 is not None and ret1 is not None else None

    def position(window: list[Mapping[str, Any]] | None) -> float | None:
        if window is None or c is None:
            return None
        low = min(float(row["low"]) for row in window)
        high = max(float(row["high"]) for row in window)
        return (c - low) / (high - low) if high > low else None

    def trend(window: list[Mapping[str, Any]] | None) -> tuple[float | None, float | None]:
        if window is None:
            return None, None
        y = [math.log(float(row["close"])) for row in window]
        xbar = (len(y) - 1) / 2
        ybar = mean(y)
        denom = sum((x - xbar) ** 2 for x in range(len(y)))
        beta = sum((x - xbar) * (value - ybar) for x, value in enumerate(y)) / denom
        sst = sum((value - ybar) ** 2 for value in y)
        if sst == 0:
            return beta, None
        sse = sum((value - ybar - beta * (x - xbar)) ** 2 for x, value in enumerate(y))
        return beta, 1 - sse / sst

    def range_close(window: list[Mapping[str, Any]] | None) -> float | None:
        if window is None:
            return None
        values = [float(row["close"]) for row in window]
        return max(values) / min(values) - 1

    def mdd_close(window: list[Mapping[str, Any]] | None) -> float | None:
        if window is None:
            return None
        peak = 0.0
        drawdowns = []
        for row in window:
            value = float(row["close"])
            peak = max(peak, value)
            drawdowns.append(value / peak - 1)
        return min(drawdowns)

    slope20, r2_20 = trend(ma20_window)
    slope20_prior, r2_20_prior = trend(prior_ma20_window)
    ret3_window = _window(rows, t - 4, t, ("close",)) if t >= 4 else None
    ret5_window = _window(rows, t - 6, t, ("close",)) if t >= 6 else None
    ret20_window = _window(rows, t - 21, t, ("close",)) if t >= 21 else None
    ret3 = _ratio(c, float(ret3_window[0]["close"])) if ret3_window else None
    ret5 = _ratio(c, float(ret5_window[0]["close"])) if ret5_window else None
    ret20 = _ratio(c, float(ret20_window[0]["close"])) if ret20_window else None
    accel = math.log(ret5) / 5 - math.log(ret20) / 20 if ret5 and ret20 else None
    concentration = None
    if sigma_window:
        closes = [float(row["close"]) for row in sigma_window]
        positives = [max(right / left - 1, 0) for left, right in zip(closes, closes[1:])]
        concentration = max(positives) / sum(positives) if sum(positives) > 0 else None
    return {
        "contract_id": CONTRACT_ID, "date": dates[-1], "price_basis": PRICE_BASIS,
        "phc20": phc20, "phh20": phh20,
        "break_margin_close20": (_ratio(c, phc20) - 1) if _ratio(c, phc20) is not None else None,
        "break_margin_high20": (_ratio(c, phh20) - 1) if _ratio(c, phh20) is not None else None,
        "break_high20": c > phh20 if c is not None and phh20 is not None else None,
        "intraday_reject_high20": h > phh20 and c <= phh20 if h is not None and c is not None and phh20 is not None else None,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "bias20": bias20,
        "slope20": slope20, "r2_20": r2_20,
        "slope20_prior": slope20_prior, "r2_20_prior": r2_20_prior,
        "pos5_hl": position(hl5_window), "pos20_hl": position(hl20_window),
        "dist_high20_hl": c / max(float(row["high"]) for row in hl20_window) - 1 if c is not None and hl20_window else None,
        "mdd20_close": mdd_close(ma20_window),
        "range5_close": range_close(ma5_window), "range20_close": range_close(ma20_window),
        "return_concentration20": concentration,
        "clv": clv, "body_ret_raw": (_ratio(_positive(today[0]["raw_close"]), _positive(today[0]["raw_open"])) - 1) if today else None,
        "reclaim_ma5": (prior_close <= prior_ma5 and c > ma5) if prior_close is not None and prior_ma5 is not None and c is not None and ma5 is not None else None,
        "reclaim_ma20": (prior_close <= prior_ma20 and c > ma20) if prior_close is not None and prior_ma20 is not None and c is not None and ma20 is not None else None,
        "touch_reclaim10": (l <= 1.01 * prior_ma10 and c >= prior_ma10) if l is not None and prior_ma10 is not None and c is not None else None,
        "amr5_mean_prior": _ratio(amount, mean(float(row["amount"]) for row in prior5)) if prior5 else None,
        "amr20_mean_prior": amr20, "amr20_median_prior": _ratio(amount, prior_amount_median),
        "pb_amr3_5_diagnostic": _ratio(mean(float(row["amount"]) for row in diagnostic_current3),
                                        mean(float(row["amount"]) for row in diagnostic_prior5))
            if diagnostic_current3 and diagnostic_prior5 else None,
        "liq20_amount": prior_amount_median,
        "liq20": prior_amount_median >= liquidity20_amount_gte if prior_amount_median is not None else None,
        "vr20_mean_prior": _ratio(volume, prior_volume_mean),
        "ret1_adj": ret1, "logret1": logret1,
        "ret3_adj": ret3 - 1 if ret3 is not None else None,
        "ret5_adj": ret5 - 1 if ret5 is not None else None,
        "ret20_adj": ret20 - 1 if ret20 is not None else None,
        "accel_log5_20": accel,
        "sigma20_v3": sigma20, "sigma20_prior": sigma20_prior, "vol20_sample": vol20_sample,
        "extension_z20": z20,
        "absolute_severe_drop": absolute_drop, "relative_severe_drop": relative_drop,
        "severe_drop": severe_drop, "first_day_damage": first_day_damage,
        "weak_close": weak_close, "heavy_weak": heavy_weak,
        "quality": "READY" if today and prior20 and prior_sigma_window else "PARTIAL",
    }


def comparable_rps_delta(today_rps: float | None, prior_rps: float | None,
                         today_universe: set[str], prior_universe: set[str], *,
                         today_basis: str = "UNVERIFIED",
                         prior_basis: str = "UNVERIFIED",
                         max_change: float = 0.10, min_jaccard: float = 0.90) -> dict[str, Any]:
    """Expose arithmetic diagnostically; formal delta requires PIT-as-of inputs."""
    union = today_universe | prior_universe
    sizes = max(len(today_universe), len(prior_universe))
    change = abs(len(today_universe) - len(prior_universe)) / sizes if sizes else None
    jaccard = len(today_universe & prior_universe) / len(union) if union else None
    comparable = bool(sizes and change <= max_change and jaccard >= min_jaccard)
    valid = all(value is not None and math.isfinite(value) for value in (today_rps, prior_rps))
    diagnostic_delta = today_rps - prior_rps if comparable and valid else None
    formal = comparable and today_basis == prior_basis == "PIT_ASOF"
    return {"delta": diagnostic_delta if formal else None,
            "diagnostic_delta": diagnostic_delta,
            "comparable": comparable, "formal_comparable": formal,
            "today_basis": today_basis, "prior_basis": prior_basis,
            "today_count": len(today_universe),
            "prior_count": len(prior_universe), "size_change": change, "jaccard": jaccard}

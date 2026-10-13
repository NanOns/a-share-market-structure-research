"""V4-03 CORE_FACTOR_V1 calculations over explicitly classified market sessions.

Input rows must already come from accepted V4-01/V4-02 producers. This module
does not infer suspensions, identity, adjustment coordinates, or calendars.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from statistics import fmean, pstdev
from typing import Mapping, Sequence

from .parameters import contract_literal


CONTRACT_ID = "CORE_FACTOR_V1"
PARAMETER_SET_ID = "V4_03_CORE_FACTOR_PARAMETER_SET_V1"
TECHNICAL = "TECHNICAL_BAR_WINDOW_V1"
CROSS_SECTION = "CROSS_SECTION_SESSION_WINDOW_V1"


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: float
    adjustment_basis_id: str
    source_digest: str


@dataclass(frozen=True)
class Observation:
    trade_date: str
    state: str  # ACTUAL, CONFIRMED_SUSPENSION, UNKNOWN, PRE_LISTING, ADJUSTMENT_UNKNOWN, IDENTITY_UNKNOWN
    bar: Bar | None = None


@dataclass(frozen=True)
class FactorValue:
    value: float | bool | None
    quality_state: str
    unknown_reason: str | None
    window_identity: str
    window_start_trade_date: str | None
    window_end_trade_date: str | None
    calendar_span: int
    actual_count: int
    suspended_count: int
    input_digest: str
    output_digest: str
    contract_id: str = CONTRACT_ID
    parameter_set_id: str = PARAMETER_SET_ID


def _digest(parts: object) -> str:
    return sha256(json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _result(value: float | bool | None, reason: str | None, rows: Sequence[Observation], kind: str,
            field: str, security_id: str) -> FactorValue:
    payload = {"value": value, "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
               "window_identity": _digest([kind, field, security_id, [(r.trade_date, r.state,
               r.bar.adjustment_basis_id if r.bar else None,
               r.bar.source_digest if r.bar else None) for r in rows]]),
               "window_start_trade_date": rows[0].trade_date if rows else None,
               "window_end_trade_date": rows[-1].trade_date if rows else None,
               "calendar_span": len(rows), "actual_count": sum(r.state == "ACTUAL" for r in rows),
               "suspended_count": sum(r.state == "CONFIRMED_SUSPENSION" for r in rows),
               "input_digest": _digest([(r.trade_date, r.bar.source_digest if r.bar else r.state) for r in rows]),
               "contract_id": CONTRACT_ID, "parameter_set_id": PARAMETER_SET_ID}
    payload["output_digest"] = _digest(payload)
    return FactorValue(**payload)


def _derived(value: float | bool | None, reason: str | None, field: str,
             security_id: str, dependencies: Sequence[FactorValue]) -> FactorValue:
    starts = [x.window_start_trade_date for x in dependencies if x.window_start_trade_date]
    ends = [x.window_end_trade_date for x in dependencies if x.window_end_trade_date]
    payload = {"value": value, "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
               "window_identity": _digest([CONTRACT_ID, field, security_id, [x.window_identity for x in dependencies]]),
               "window_start_trade_date": min(starts) if starts else None,
               "window_end_trade_date": max(ends) if ends else None,
               "calendar_span": max((x.calendar_span for x in dependencies), default=0),
               "actual_count": max((x.actual_count for x in dependencies), default=0),
               "suspended_count": max((x.suspended_count for x in dependencies), default=0),
               "input_digest": _digest([x.input_digest for x in dependencies]),
               "contract_id": CONTRACT_ID, "parameter_set_id": PARAMETER_SET_ID}
    payload["output_digest"] = _digest(payload)
    return FactorValue(**payload)


def _valid(rows: Sequence[Observation], *, price: bool = True) -> str | None:
    if any(r.state != "ACTUAL" or r.bar is None for r in rows):
        return "MISSING_OR_SUSPENDED_ENDPOINT"
    bars = [r.bar for r in rows]
    if any(not b.adjustment_basis_id or not b.source_digest for b in bars):
        return "ADJUSTMENT_OR_SOURCE_IDENTITY_UNKNOWN"
    if len({b.adjustment_basis_id for b in bars}) != 1:
        return "MIXED_ADJUSTMENT_IDENTITY"
    if any(not all(math.isfinite(x) for x in (b.open, b.high, b.low, b.close, b.amount, b.volume)) for b in bars):
        return "NONFINITE_INPUT"
    if price and any(min(b.open, b.high, b.low, b.close) <= 0 or b.high < b.low for b in bars):
        return "INVALID_PRICE"
    return None


def _tech(history: Sequence[Observation], n: int, *, exclude_current: bool = False) -> tuple[list[Observation], str | None]:
    end = len(history) - (1 if exclude_current else 0)
    if end <= 0:
        return [], "INSUFFICIENT_HISTORY"
    if not exclude_current and history[end - 1].state in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN", "PRE_LISTING"}:
        row = history[end - 1]
        return [row], row.state if row.state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} else "CURRENT_BAR_UNAVAILABLE"
    actual = []
    start = end
    for i in range(end - 1, -1, -1):
        row = history[i]
        if row.state in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}:
            return list(history[i:end]), "UNEXPLAINED_DATA_GAP" if row.state == "UNKNOWN" else row.state
        if row.state == "PRE_LISTING":
            break
        if row.state == "ACTUAL":
            actual.append(row)
            if len(actual) == n:
                start = i
                break
    if len(actual) < n:
        return list(history[max(0, start):end]), "INSUFFICIENT_HISTORY"
    return list(history[start:end]), None


def _bars(rows: Sequence[Observation]) -> list[Bar]:
    return [r.bar for r in rows if r.state == "ACTUAL" and r.bar is not None]


def _session(history: Sequence[Observation], n: int) -> tuple[list[Observation], str | None]:
    if len(history) < n + 1:
        return list(history), "INSUFFICIENT_SESSION_HISTORY"
    rows = list(history[-n - 1:])
    if rows[0].state != "ACTUAL" or rows[-1].state != "ACTUAL":
        reason = next((r.state for r in (rows[0], rows[-1]) if r.state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}), None)
        return rows, reason or "MISSING_OR_SUSPENDED_ENDPOINT"
    if any(r.state in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} for r in rows):
        reason = next((r.state for r in rows if r.state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}), None)
        return rows, reason or "UNEXPLAINED_DATA_GAP"
    return rows, None


def compute_core(history: Sequence[Observation], security_id: str, *, asof: str | None = None) -> dict[str, FactorValue]:
    """Compute named V4-03 fields as of the last supplied market session."""
    if not history or any(a.trade_date >= b.trade_date for a, b in zip(history, history[1:])):
        raise ValueError("history must contain unique ascending market sessions")
    if asof is not None:
        history = [row for row in history if row.trade_date <= asof]
        if not history or history[-1].trade_date != asof:
            raise ValueError("asof must be an explicit market-session endpoint")
    out: dict[str, FactorValue] = {}

    def put(field: str, n: int, formula, *, prior: bool = False,
            current_required: bool = False, extra: int = 0):
        rows, error = _tech(history, n + extra, exclude_current=prior)
        reason = error or _valid([r for r in rows if r.state == "ACTUAL"])
        if current_required:
            current_state = history[-1].state
            current_error = (current_state if current_state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}
                             else "CURRENT_BAR_UNAVAILABLE" if current_state != "ACTUAL"
                             else _valid(history[-1:]))
            reason = reason or current_error
            if not reason and rows and _bars(rows)[-1].adjustment_basis_id != history[-1].bar.adjustment_basis_id:
                reason = "MIXED_ADJUSTMENT_IDENTITY"
        bars = _bars(rows)
        if not reason:
            try:
                value = formula(bars)
                if value is None or isinstance(value, float) and not math.isfinite(value):
                    reason = "ZERO_DENOMINATOR"
            except ZeroDivisionError:
                value, reason = None, "ZERO_DENOMINATOR"
        else:
            value = None
        recorded_rows = [*rows, history[-1]] if prior and field.startswith(("amount_ratio", "volume_ratio")) else rows
        out[field] = _result(value if not reason else None, reason, recorded_rows, TECHNICAL, field, security_id)

    for n in (5, 20, 60):
        put(f"ma{n}", n, lambda b: fmean(x.close for x in b))
    for n in (5, 20, 60):
        put(f"hhv{n}", n, lambda b: max(x.high for x in b))
        put(f"llv{n}", n, lambda b: min(x.low for x in b))
    for n in (5, 20, 60):
        put(f"prior_high{n}", n, lambda b: max(x.high for x in b), prior=True)
        put(f"prior_low{n}", n, lambda b: min(x.low for x in b), prior=True)
    for n in (5, 20):
        put(f"amount_ratio{n}", n, lambda b: history[-1].bar.amount / fmean(x.amount for x in b)
            if fmean(x.amount for x in b) != 0 else None, prior=True, current_required=True)
        put(f"volume_ratio{n}", n, lambda b: history[-1].bar.volume / fmean(x.volume for x in b)
            if fmean(x.volume for x in b) != 0 else None, prior=True, current_required=True)
    for n in (1, 3, 5, 20):
        rows, error = _session(history, n)
        reason = error or _valid([rows[0], rows[-1]]) if rows else error
        if not reason and rows[0].bar.close == 0:
            reason = "ZERO_DENOMINATOR"
        out[f"ret{n}"] = _result(None if reason else rows[-1].bar.close / rows[0].bar.close - 1,
                                  reason, rows, CROSS_SECTION, f"ret{n}", security_id)
    for n in (5, 20):
        rows, error = _session(history, n)
        reason = error or _valid(rows) if rows else error
        value = None if reason else pstdev(math.log(b.close / a.close) for a, b in zip(_bars(rows), _bars(rows)[1:]))
        out[f"vol{n}"] = _result(value, reason, rows, CROSS_SECTION, f"vol{n}", security_id)
    put("tr", 1, lambda b: max(b[-1].high - b[-1].low,
                                  abs(b[-1].high - b[-2].close),
                                  abs(b[-1].low - b[-2].close)), current_required=True, extra=1)
    for n in (5, 20):
        put(f"atr{n}", n, lambda b: fmean(max(x.high - x.low, abs(x.high - p.close), abs(x.low - p.close))
            for p, x in zip(b[:-1], b[1:])), extra=1)
    for n, offset in ((20, 5), (60, 10)):
        rows, error = _tech(history, n + offset)
        reason = error or _valid([r for r in rows if r.state == "ACTUAL"])
        bars = _bars(rows)
        atr = out["atr20"]
        reason = reason or atr.unknown_reason
        value = None
        if not reason:
            if atr.value <= 0:
                reason = "ZERO_ATR"
            else:
                current_ma = fmean(x.close for x in bars[-n:])
                earlier_ma = fmean(x.close for x in bars[-n-offset:-offset])
                value = (current_ma - earlier_ma) / atr.value
        out[f"slope{n}"] = _result(value, reason, rows, TECHNICAL, f"slope{n}", security_id)
    put("hh_progress", 10, lambda b: max(x.high for x in b[-5:]) > max(x.high for x in b[:5]))
    put("ll_progress", 10, lambda b: min(x.low for x in b[-5:]) < min(x.low for x in b[:5]))
    put("clv", 1, lambda b: (b[-1].close - b[-1].low) / (b[-1].high - b[-1].low)
        if b[-1].high != b[-1].low else None, current_required=True)
    prior_rows, prior_error = _tech(history, 60, exclude_current=True)
    prior_reason = prior_error or _valid([r for r in prior_rows if r.state == "ACTUAL"])
    prior_bars = _bars(prior_rows)
    percentile = None
    if not prior_reason:
        current = history[-1].bar.close if history[-1].bar else None
        prior_reason = _valid(history[-1:])
        if not prior_reason and prior_bars[-1].adjustment_basis_id != history[-1].bar.adjustment_basis_id:
            prior_reason = "MIXED_ADJUSTMENT_IDENTITY"
        if not prior_reason:
            closes = [b.close for b in prior_bars]
            percentile = 100 * (sum(x < current for x in closes) + 0.5 * sum(x == current for x in closes)) / 60
    out["prior60_percentile"] = _result(percentile, prior_reason, [*prior_rows, history[-1]], TECHNICAL,
                                           "prior60_percentile", security_id)
    for name, numerator, denominator in (
        ("pos60", "llv60", "hhv60"), ("range_ratio", "hhv5", "hhv20"),
        ("atr_ratio", "atr5", "atr20"), ("vol_ratio", "vol5", "vol20")):
        deps = [out[numerator], out[denominator]]
        if name in ("pos60", "range_ratio"):
            deps += [out["llv5" if name == "range_ratio" else "llv60"], out["llv20" if name == "range_ratio" else "hhv60"]]
        reason = next((x.unknown_reason for x in deps if x.unknown_reason), None)
        value = None
        if not reason:
            if name == "pos60":
                den = out["hhv60"].value - out["llv60"].value
                if history[-1].state != "ACTUAL" or history[-1].bar is None:
                    reason = history[-1].state if history[-1].state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} else "CURRENT_BAR_UNAVAILABLE"
                elif den == 0:
                    reason = "ZERO_DENOMINATOR"
                else:
                    value = (history[-1].bar.close - out["llv60"].value) / den
            elif name == "range_ratio":
                den = out["hhv20"].value - out["llv20"].value
                value = (out["hhv5"].value - out["llv5"].value) / den if den else None
            else:
                den = out[denominator].value
                value = out[numerator].value / den if den and den > 0 else None
            if value is None and reason is None:
                reason = "ZERO_DENOMINATOR"
        out[name] = _derived(value, reason, name, security_id, deps)
    deps = [out["prior_low20"], out["atr20"], out["ret1"]]
    reason = next((x.unknown_reason for x in deps if x.unknown_reason), None)
    value = None if reason else (history[-1].bar.close < out["prior_low20"].value - contract_literal("core_price_damage_atr_multiple") * out["atr20"].value
                                  and out["ret1"].value < 0)
    out["core_price_damage"] = _derived(value, reason, "core_price_damage", security_id, deps)
    return out


def rps_midrank(returns: Mapping[str, float | None], universe: Sequence[str]) -> tuple[dict[str, float | None], dict]:
    """PIT evaluable subset only; order and display tie breaks cannot change values."""
    members = sorted(set(universe))
    values = {s: returns.get(s) for s in members if returns.get(s) is not None and math.isfinite(returns[s])}
    n = len(values)
    result = {}
    for s in members:
        v = values.get(s)
        if n < 2 or v is None:
            result[s] = None
        else:
            less = sum(x < v for x in values.values())
            equal = sum(x == v for x in values.values())
            result[s] = 100 * (less + 0.5 * (equal - 1)) / (n - 1)
    return result, {"universe_count": len(members), "evaluable_count": n,
                    "missing_count": len(members) - n, "coverage": n / len(members) if members else None,
                    "evaluable_set_identity": _digest(sorted(values))}


def market_reference(returns: Mapping[str, float | None], start_universe: Sequence[str]) -> tuple[float | None, dict]:
    """Equal-weight endpoint return, distinct from a daily rebalanced path."""
    missing_limit = contract_literal("market_reference_max_missing_fraction")
    members = sorted(set(start_universe))
    values = {s: returns.get(s) for s in members if returns.get(s) is not None and math.isfinite(returns[s])}
    count, n = len(members), len(values)
    missing = count - n
    reason = "EMPTY_START_UNIVERSE" if count == 0 else "MISSING_COVERAGE_EXCEEDED" if missing / count > missing_limit else None
    return (fmean(values.values()) if not reason and n else None,
            {"contract_id": "MARKET_RELATIVE_REFERENCE_V1", "parameter_set_id": PARAMETER_SET_ID,
             "universe_count": count, "evaluable_count": n, "missing_count": missing,
             "coverage": n / count if count else None, "unknown_reason": reason,
             "evaluable_set_identity": _digest(sorted(values))})

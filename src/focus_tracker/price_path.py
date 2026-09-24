"""FOCUS_PATH_PRICE_BASIS_V1 rolling affine local price path."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping, Sequence

from .session_gap_semantics import (SessionState, assess_gap_sequence,
                                   classify_session_state)


CONTRACT_ID = "FOCUS_PATH_PRICE_BASIS_V1"
ACTUAL_TRADED_CONTRACT_ID = "FOCUS_ACTUAL_TRADED_PATH_V1"
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Bar:
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    has_actual_bar: bool = True


@dataclass(frozen=True)
class AdjustmentEvent:
    effective_date: date
    m: Decimal
    c: Decimal


@dataclass(frozen=True)
class ActualTradedPath:
    bars: tuple[Bar, ...] | None
    gap_count: int
    suspended_sessions: tuple[date, ...]
    unverified_gap_sessions: tuple[date, ...]
    actual_sessions: tuple[date, ...]


def reanchor_actual_traded_path(*, sessions: Sequence[date],
                                rows: Mapping[date, Mapping[str, object]]) -> ActualTradedPath:
    """Bridge proven suspensions only; keep every unverified gap fail-closed.

    The master session list remains available to consecutive-day predicates.
    This projection is solely for return and high/low path measurements.
    """
    if not sessions or list(sessions) != sorted(set(sessions)):
        raise ValueError("invalid actual-traded session path")
    states = {day: classify_session_state(rows.get(day)) for day in sessions}
    assessment = assess_gap_sequence(operation="PATH",
                                     states=[states[day] for day in sessions])
    traded, suspended, uncertain = [], [], []
    for day in sessions:
        state = states[day]
        if state == SessionState.ACTUAL_BAR:
            traded.append(day)
        elif state == SessionState.SUSPENDED:
            suspended.append(day)
        else:
            uncertain.append(day)
    complete = assessment.usable and not uncertain
    bars = (tuple(reanchor_from_frozen_coefficients(sessions=traded, rows=rows) or ())
            if complete else None)
    if complete and not bars:
        raise ValueError("actual-traded path disappeared despite complete bars")
    return ActualTradedPath(bars, len(suspended) + len(uncertain),
                            tuple(suspended), tuple(uncertain), tuple(traded))


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def due_date(calendar: Sequence[date], anchor_date: date, horizon: int) -> date | None:
    if horizon not in {1, 3, 5, 10, 20}:
        raise ValueError("unsupported focus horizon")
    if len(set(calendar)) != len(calendar) or list(calendar) != sorted(calendar):
        raise ValueError("calendar must be strictly increasing")
    try:
        position = calendar.index(anchor_date)
    except ValueError as exc:
        raise ValueError("anchor not on frozen calendar") from exc
    target = position + horizon
    return calendar[target] if target < len(calendar) else None


def reanchor_path(*, sessions: Sequence[date], bars: Mapping[date, Bar],
                  events: Sequence[AdjustmentEvent]) -> list[Bar] | None:
    """Adjust all bars to the final session's local raw price basis.

    Return None for any missing actual bar. No synthetic fill, forward event,
    or external adjustment service enters the path.
    """
    if not sessions or list(sessions) != sorted(set(sessions)):
        raise ValueError("invalid session path")
    if len({event.effective_date for event in events}) != len(events):
        raise ValueError("duplicate adjustment event date")
    for event in events:
        if not event.m.is_finite() or event.m <= 0 or not event.c.is_finite():
            raise ValueError("invalid adjustment event")
        if event.effective_date > sessions[-1]:
            raise ValueError("future adjustment event in input")
    ordered_events = sorted(events, key=lambda item: item.effective_date, reverse=True)
    a, b = Decimal(1), Decimal(0)
    event_index = 0
    adjusted: list[Bar] = []
    for day in reversed(sessions):
        while event_index < len(ordered_events) and ordered_events[event_index].effective_date > day:
            event = ordered_events[event_index]
            a = a / event.m
            b = b - a * event.c
            event_index += 1
        raw = bars.get(day)
        if raw is None or not raw.has_actual_bar or raw.trade_date != day:
            return None
        values = (raw.open, raw.high, raw.low, raw.close)
        if any(not value.is_finite() or value <= 0 for value in values):
            raise ValueError("invalid actual bar price")
        transformed = [_money(a * value + b) for value in values]
        if any(value <= 0 for value in transformed) or transformed[2] > transformed[1]:
            raise ValueError("invalid adjusted OHLC")
        adjusted.append(Bar(day, *transformed))
    adjusted.reverse()
    return adjusted


def reanchor_from_frozen_coefficients(*, sessions: Sequence[date],
                                      rows: Mapping[date, Mapping[str, object]]) -> list[Bar] | None:
    """Reanchor frozen local QFQ coefficients to the observation date.

    A normalized dataset may be anchored later than the requested observation
    day. The affine coordinate change removes all events after that day:
    ``P[j|t]=(A[j]*RAW[j]+B[j]-B[t])/A[t]``. Both A and B must come from the
    same verified local adjustment artifact; mixed versions fail closed.
    """
    if not sessions or list(sessions) != sorted(set(sessions)):
        raise ValueError("invalid session path")
    last = rows.get(sessions[-1])
    if not last or last.get("has_actual_bar") is not True:
        return None
    try:
        a_t = Decimal(str(last["qfq_mul"]))
        b_t = Decimal(str(last["qfq_add"]))
    except (KeyError, ArithmeticError, ValueError, TypeError) as exc:
        raise ValueError("observation anchor coefficients missing") from exc
    if not a_t.is_finite() or a_t <= 0 or not b_t.is_finite():
        raise ValueError("invalid observation anchor coefficients")
    version = last.get("adjustment_version")
    if not version or not str(last.get("adjustment_status", "")).startswith("VERIFIED"):
        raise ValueError("unverified local adjustment")
    result = []
    for day in sessions:
        row = rows.get(day)
        if row is None or row.get("has_actual_bar") is not True:
            return None
        if row.get("adjustment_version") != version or not str(row.get("adjustment_status", "")).startswith("VERIFIED"):
            raise ValueError("mixed local adjustment identity")
        try:
            a_j, b_j = Decimal(str(row["qfq_mul"])), Decimal(str(row["qfq_add"]))
            raw = [Decimal(str(row[f"raw_{field}"])) for field in ("open", "high", "low", "close")]
        except (KeyError, ArithmeticError, ValueError, TypeError) as exc:
            raise ValueError("raw price or affine coefficient missing") from exc
        if not a_j.is_finite() or a_j <= 0 or not b_j.is_finite() or any(
            not value.is_finite() or value <= 0 for value in raw
        ):
            raise ValueError("invalid normalized local row")
        transformed = [_money((a_j * value + b_j - b_t) / a_t) for value in raw]
        if any(value <= 0 for value in transformed) or transformed[2] > transformed[1]:
            raise ValueError("invalid reanchored OHLC")
        result.append(Bar(day, *transformed))
    return result


def path_metrics(path: Sequence[Bar]) -> dict[str, Decimal]:
    if not path or any(not bar.has_actual_bar for bar in path):
        raise ValueError("complete actual bar path required")
    first = path[0].close
    if first <= 0:
        raise ValueError("nonpositive anchor close")
    peak_close = first
    worst_drawdown = Decimal(0)
    maximum_high = path[0].high
    minimum_low = path[0].low
    for bar in path:
        peak_close = max(peak_close, bar.close)
        worst_drawdown = min(worst_drawdown, bar.close / peak_close - 1)
        maximum_high = max(maximum_high, bar.high)
        minimum_low = min(minimum_low, bar.low)
    return {
        "return_close": path[-1].close / first - 1,
        "mfe": maximum_high / first - 1,
        "mae": minimum_low / first - 1,
        "peak_close": peak_close,
        "drawdown_current": path[-1].close / peak_close - 1,
        "mdd_close": worst_drawdown,
    }

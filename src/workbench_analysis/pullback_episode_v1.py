"""Bounded, sequential P12-02 pullback episode diagnostic.

Prices for one trace must be transformed to the same target cutoff anchor.
The caller supplies frozen per-day strong-seed and structure-break facts. This
module does not infer historical PIT availability from a current source.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from statistics import mean
from typing import Any


CONTRACT_ID = "PULLBACK_EPISODE_V1_CANDIDATE_01"
TERMINAL = frozenset({"CONFIRMED", "INVALIDATED", "RESET_NEW_HIGH", "EXPIRED"})


def _number(row: Mapping[str, Any], key: str) -> float | None:
    try:
        result = float(row.get(key))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def _known_day(row: Mapping[str, Any]) -> bool:
    return (row.get("has_actual_bar") is True and row.get("is_synthetic_fill") is not True
            and all(_number(row, key) is not None for key in ("high", "close", "ma20", "amount"))
            and row.get("structure_break") is not None)


def trace_pullback_episode(days: Sequence[Mapping[str, Any]], *,
                           max_event_sessions: int = 20,
                           max_pullback_sessions: int = 10) -> list[dict[str, Any]]:
    """Trace one stock from an explicitly supplied master-session history."""
    if max_event_sessions < 2 or max_pullback_sessions < 1:
        raise ValueError("INVALID_EPISODE_LIMIT")
    if not days:
        return []
    dates = [str(day["date"]) for day in days]
    if dates != sorted(set(dates)):
        raise ValueError("EPISODE_DATES_NOT_ORDERED")
    if any(day.get(key) is not None and type(day.get(key)) is not bool
           for day in days for key in ("strong_seed", "structure_break")):
        raise ValueError("EPISODE_SIGNAL_TYPE_INVALID")
    if any(day.get("anchor_cutoff") != dates[-1] or
           day.get("price_basis") != "TDX_NATIVE_AFFINE_QFQ" for day in days):
        raise ValueError("EPISODE_PRICE_ANCHOR_MISMATCH")
    indexes = [day.get("session_index") for day in days]
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indexes) or indexes != list(range(indexes[0], indexes[0] + len(days))):
        raise ValueError("EPISODE_MASTER_SESSION_GAP")
    state = "IDLE"
    a = h = p = None
    peak = peak_close = None
    result = []
    for i, day in enumerate(days):
        if state in TERMINAL:
            state, a, h, p, peak, peak_close = "IDLE", None, None, None, None, None
        if state in ("DATA_GAP", "LEFT_CENSORED"):
            if day.get("strong_seed") is False and _known_day(day):
                state = "IDLE"
            else:
                result.append({"date": dates[i], "state": state, "confirmed": False,
                               "seed_date": dates[a] if a is not None else None})
                continue
        reason = None
        confirmed = False
        evidence: dict[str, Any] = {}
        if not _known_day(day):
            state = "DATA_GAP"
            if day.get("structure_break") is True:
                reason = "STRUCTURE_DAMAGED_KNOWN_WITH_DATA_GAP"
        elif day["structure_break"] is True or _number(day, "close") / _number(day, "ma20") < 0.97:
            state = "INVALIDATED" if a is not None else "IDLE"
            reason = "STRUCTURE_DAMAGED"
        elif state == "IDLE":
            if day.get("strong_seed") is None:
                state = "DATA_GAP"
            elif day.get("strong_seed") is True:
                if i == 0:
                    state = "LEFT_CENSORED"
                else:
                    state, a, h, peak, peak_close = (
                        "ADVANCING", i, i, _number(day, "high"), _number(day, "close"))
        elif a is not None and i - a + 1 > max_event_sessions:
            state, reason = "EXPIRED", "EVENT_WINDOW_EXCEEDED"
        elif state == "ADVANCING":
            high = _number(day, "high")
            close = _number(day, "close")
            if high >= peak:
                h, peak, peak_close = i, high, close
            elif i > h and close < _number(days[i - 1], "close") and close < peak_close:
                p, state = h + 1, "PULLING_BACK"
        elif state == "PULLING_BACK":
            high = _number(day, "high")
            close = _number(day, "close")
            if high >= peak:
                state, reason = "RESET_NEW_HIGH", "PEAK_REVISITED"
            elif i - p + 1 > max_pullback_sessions:
                state, reason = "EXPIRED", "PULLBACK_WINDOW_EXCEEDED"
            elif i > p and h >= 4:
                pre = days[h - 4:h + 1]
                pull = days[p:i]
                if all(_known_day(row) for row in pre + pull):
                    pre_amount = mean(_number(row, "amount") for row in pre)
                    pull_amount = mean(_number(row, "amount") for row in pull)
                    contraction = pull_amount / pre_amount
                    confirm_ratio = _number(day, "amount") / pull_amount
                    depth = 1 - close / peak
                    controlled = (0.03 <= depth <= 0.12
                                  and all(_number(row, "close") / _number(row, "ma20") >= 0.97
                                          for row in days[p:i + 1]))
                    slope = day.get("slope20_prior")
                    r2 = day.get("r2_20_prior")
                    controlled = controlled and slope is not None and slope > 0 and r2 is not None and r2 >= 0.40
                    confirmed = (controlled and _number(days[i - 1], "close") < peak_close
                                 and contraction <= 0.85 and confirm_ratio >= 1
                                 and close >= _number(days[i - 1], "close")
                                 and day.get("clv") is not None and day["clv"] >= 0.55
                                 and (day.get("reclaim_ma5") is True or day.get("touch_reclaim10") is True)
                                 and day.get("intraday_reject_high20") is False)
                    evidence = {"pre_pullback_amount": pre_amount, "pullback_amount": pull_amount,
                                "pullback_contraction": contraction, "confirm_amount_ratio": confirm_ratio,
                                "depth": depth, "controlled": controlled,
                                "short_pullback_sample": len(pull) == 1}
                    if confirmed:
                        state = "CONFIRMED"
        result.append({"date": dates[i], "state": state, "confirmed": confirmed,
                       "seed_date": dates[a] if a is not None else None,
                       "peak_date": dates[h] if h is not None else None,
                       "pullback_start": dates[p] if p is not None else None,
                       "peak_high": peak, "reason": reason, "evidence": evidence})
    return result

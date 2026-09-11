"""M13B-01 market-day limit ladder recursion.

The module consumes already-evaluated local M8C limit states.  It never infers
a limit from a percentage move or a stock name and it keeps unknown observations
separate from known non-limit observations.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

import pandas as pd


CONTRACT_VERSION = "LIMIT_LADDER_V1_0"
KNOWN_STATES = ("UP", "DOWN", "NONE", "UNKNOWN", "NO_LIMIT", "SUSPENDED")
KNOWN_BOUNDARIES = frozenset({"DOWN", "NONE", "NO_LIMIT", "SUSPENDED"})


class LimitLadderError(ValueError):
    pass


def _day(value: Any, field: str = "trade_date") -> date:
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError) as exc:
        raise LimitLadderError(f"{field}_INVALID") from exc


def _bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in {"TRUE", "1", "YES", "Y"}:
        return True
    if text in {"FALSE", "0", "NO", "N", ""}:
        return False
    return None


def canonical_limit_state(value: Any) -> str:
    """Map M8C names to the stable M13B ladder vocabulary."""
    text = str(value or "").strip().upper()
    return {
        "LIMIT_UP": "UP",
        "LIMIT_DOWN": "DOWN",
        "NOT_LIMIT": "NONE",
        "NOT_LIMITED": "NONE",
        "SUSPENSION": "SUSPENDED",
    }.get(text, text if text in KNOWN_STATES else "UNKNOWN")


def _input_state(row: Mapping[str, Any]) -> tuple[str, str | None]:
    suspended = _bool(row.get("suspended"))
    if suspended is True:
        return "SUSPENDED", "SUSPENSION_BREAK"
    if "suspended" in row and suspended is None:
        return "UNKNOWN", "SUSPENSION_FLAG_UNKNOWN"
    if row.get("limit_state") in (None, ""):
        if row.get("quote_present") is False or row.get("has_actual_bar") is False:
            return "UNKNOWN", "MISSING_MARKET_OBSERVATION"
        return "UNKNOWN", "LIMIT_STATE_NOT_EVALUATED"
    state = canonical_limit_state(row.get("limit_state"))
    return state, None if state != "UNKNOWN" else str(row.get("reason") or "LIMIT_STATE_UNKNOWN")


def _level(streak: int | None, known: bool, state: str) -> str | None:
    if state != "UP":
        return "UNKNOWN" if state == "UNKNOWN" else None
    if not known or streak is None:
        return "UNKNOWN"
    if streak >= 4:
        return "4PLUS"
    return str(streak)


def _result_base(row: Mapping[str, Any], trade_date: date, state: str, reason: str | None) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_VERSION,
        "security_id": str(row.get("security_id") or ""),
        "trade_date": trade_date.isoformat(),
        "limit_state": state,
        "reference_basis": row.get("reference_basis") or "UNKNOWN",
        "rule_id": row.get("rule_id"),
        "limit_up_price": row.get("limit_up_price"),
        "limit_down_price": row.get("limit_down_price"),
        "streak": None,
        "streak_known": state != "UNKNOWN",
        "streak_min_known": None,
        "previous_state": None,
        "previous_streak": None,
        "ladder_level": _level(None, False, state),
        "promotion_state": "NOT_EVALUATED",
        "denominator_eligible": None,
        "exclusion_reason": reason,
        "association_ref": row.get("association_ref"),
    }


def derive_limit_ladder_rows(
    rows: Iterable[Mapping[str, Any]],
    market_dates: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Recursively derive one ladder row per supplied security and market day.

    A date absent from a security's input is an explicit UNKNOWN observation,
    not a reason to skip the date or borrow the last known close.  The first UP
    in the requested window is left-censored and receives only a minimum known
    streak of one until a known boundary is observed.
    """
    normalized: dict[tuple[str, date], Mapping[str, Any]] = {}
    security_ids: set[str] = set()
    row_dates: set[date] = set()
    for raw in rows:
        security_id = str(raw.get("security_id") or "").strip()
        if not security_id:
            raise LimitLadderError("SECURITY_ID_REQUIRED")
        day = _day(raw.get("trade_date"))
        key = (security_id, day)
        if key in normalized:
            raise LimitLadderError("DUPLICATE_SECURITY_DATE")
        normalized[key] = dict(raw)
        security_ids.add(security_id)
        row_dates.add(day)

    if market_dates is None:
        dates = sorted(row_dates)
    else:
        dates = [_day(value, "market_date") for value in market_dates]
        if len(set(dates)) != len(dates):
            raise LimitLadderError("DUPLICATE_MARKET_DATE")
        dates = sorted(dates)
    if not dates:
        return []

    results: list[dict[str, Any]] = []
    for security_id in sorted(security_ids):
        previous: dict[str, Any] | None = None
        for day in dates:
            raw = normalized.get((security_id, day), {"security_id": security_id, "quote_present": False})
            state, reason = _input_state(raw)
            item = _result_base(raw, day, state, reason)
            item["previous_state"] = previous["limit_state"] if previous else None
            item["previous_streak"] = (
                previous["streak"]
                if previous and previous["limit_state"] == "UP" and previous["streak_known"]
                else None
            )

            if state == "UP":
                if previous and previous["limit_state"] == "UP" and previous["streak_known"] and previous["streak"] is not None:
                    item["streak"] = int(previous["streak"]) + 1
                    item["streak_known"] = True
                    item["streak_min_known"] = item["streak"]
                    item["exclusion_reason"] = None
                elif previous and previous["limit_state"] in KNOWN_BOUNDARIES:
                    item["streak"] = 1
                    item["streak_known"] = True
                    item["streak_min_known"] = 1
                    item["exclusion_reason"] = None
                else:
                    item["streak"] = 1
                    item["streak_known"] = False
                    item["streak_min_known"] = 1
                    item["exclusion_reason"] = "LEFT_CENSORED" if previous is None else "UNKNOWN_PREVIOUS_BOUNDARY"
                item["ladder_level"] = _level(item["streak"], item["streak_known"], state)
            elif state == "UNKNOWN":
                item["streak"] = None
                item["streak_known"] = False
                item["ladder_level"] = "UNKNOWN"
            elif state == "SUSPENDED":
                item["streak"] = None
                item["streak_known"] = True
                item["exclusion_reason"] = "SUSPENSION_BREAK"
            else:
                item["streak"] = None
                item["streak_known"] = True

            results.append(item)
            previous = item
    return sorted(results, key=lambda item: (item["trade_date"], item["security_id"]))

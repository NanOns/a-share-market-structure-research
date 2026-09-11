"""M13B-02 descriptive limit-up promotion aggregation."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

import pandas as pd

from workbench_analysis.limit_ladder import canonical_limit_state


CONTRACT_VERSION = "LIMIT_PROMOTION_V1_0"
PROMOTION_LEVELS = ("1", "2", "3", "4PLUS")
JUDGED_STATES = frozenset({"UP", "DOWN", "NONE"})


class LimitPromotionError(ValueError):
    pass


def _day(value: Any, field: str) -> date:
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError) as exc:
        raise LimitPromotionError(f"{field}_INVALID") from exc


def _integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None
    return integer if float(value) == integer else None


def _known(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in {"TRUE", "1", "YES", "Y"}


def _normal_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    security_id = str(raw.get("security_id") or "").strip()
    if not security_id:
        raise LimitPromotionError("SECURITY_ID_REQUIRED")
    trade_date = _day(raw.get("trade_date"), "trade_date")
    state = canonical_limit_state(raw.get("limit_state"))
    return {
        "security_id": security_id,
        "trade_date": trade_date,
        "limit_state": state,
        "streak": _integer(raw.get("streak")),
        "streak_known": _known(raw.get("streak_known")),
        "ladder_level": str(raw.get("ladder_level") or "UNKNOWN").strip().upper(),
    }


def _empty_point(previous_date: date, trade_date: date, level: str) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_VERSION,
        "previous_trade_date": previous_date.isoformat(),
        "trade_date": trade_date.isoformat(),
        "previous_level": level,
        "previous_up_count": 0,
        "previous_unconfirmed_count": 0,
        "success_count": 0,
        "eligible_count": 0,
        "excluded_unknown": 0,
        "excluded_suspended": 0,
        "excluded_no_limit": 0,
        "rate": None,
    }


def build_promotion_points(
    rows: Iterable[Mapping[str, Any]],
    market_dates: Iterable[Any] | None = None,
    previous_levels: Iterable[str] = PROMOTION_LEVELS,
) -> list[dict[str, Any]]:
    """Build one descriptive point for every adjacent supplied market date pair."""
    normalized: dict[tuple[str, date], dict[str, Any]] = {}
    row_dates: set[date] = set()
    security_ids: set[str] = set()
    for raw in rows:
        item = _normal_row(raw)
        key = (item["security_id"], item["trade_date"])
        if key in normalized:
            raise LimitPromotionError("DUPLICATE_SECURITY_DATE")
        normalized[key] = item
        security_ids.add(item["security_id"])
        row_dates.add(item["trade_date"])

    levels = tuple(dict.fromkeys(str(level).strip().upper() for level in previous_levels))
    if not levels or any(level not in PROMOTION_LEVELS for level in levels):
        raise LimitPromotionError("PROMOTION_LEVEL_UNSUPPORTED")
    supplied_dates = list(market_dates) if market_dates is not None else None
    dates = sorted({_day(value, "market_date") for value in supplied_dates} if supplied_dates is not None else row_dates)
    if len(dates) < 2:
        return []
    if supplied_dates is not None and len(dates) != len(supplied_dates):
        raise LimitPromotionError("DUPLICATE_MARKET_DATE")

    points: list[dict[str, Any]] = []
    for previous_date, trade_date in zip(dates, dates[1:]):
        previous_rows = {security_id: normalized.get((security_id, previous_date)) for security_id in security_ids}
        current_rows = {security_id: normalized.get((security_id, trade_date)) for security_id in security_ids}
        previous_up_rows = {
            security_id: row
            for security_id, row in previous_rows.items()
            if row and row["limit_state"] == "UP"
        }
        previous_unconfirmed_count = sum(
            not (
                row["streak_known"]
                and row["streak"] is not None
                and row["ladder_level"] in PROMOTION_LEVELS
            )
            for row in previous_up_rows.values()
        )
        for level in levels:
            point = _empty_point(previous_date, trade_date, level)
            point["previous_up_count"] = len(previous_up_rows)
            point["previous_unconfirmed_count"] = previous_unconfirmed_count
            for security_id in sorted(previous_up_rows):
                previous = previous_up_rows[security_id]
                previous_streak = previous["streak"]
                confirmed = (
                    previous["streak_known"]
                    and previous_streak is not None
                    and previous["ladder_level"] == level
                )
                if not confirmed:
                    continue

                current = current_rows[security_id]
                current_state = current["limit_state"] if current else "UNKNOWN"
                if current_state == "UNKNOWN" or (current_state == "UP" and not current["streak_known"]):
                    point["excluded_unknown"] += 1
                    continue
                if current_state == "SUSPENDED":
                    point["excluded_suspended"] += 1
                    continue
                if current_state == "NO_LIMIT":
                    point["excluded_no_limit"] += 1
                    continue
                if current_state not in JUDGED_STATES:
                    point["excluded_unknown"] += 1
                    continue

                point["eligible_count"] += 1
                if (
                    current_state == "UP"
                    and current["streak_known"]
                    and current["streak"] is not None
                    and current["streak"] == previous_streak + 1
                ):
                    point["success_count"] += 1
            if point["eligible_count"]:
                point["rate"] = point["success_count"] / point["eligible_count"]
            points.append(point)
    return points


def annotate_promotion_states(
    rows: Iterable[Mapping[str, Any]],
    market_dates: Iterable[Any] | None = None,
) -> list[dict[str, Any]]:
    """Annotate ladder rows with the row-level state used by API34 filters.

    Aggregate promotion history remains the source for counts and rates.  This
    companion state is only a descriptive per-security label, so the ladder
    page can distinguish SUCCESS, NOT_ELIGIBLE and excluded observations.
    """
    normalized = []
    for raw in rows:
        item = _normal_row(raw)
        # Keep M13B-01 evidence fields intact while normalizing only the
        # fields used by the promotion contract.
        for key in ("reference_basis", "rule_id", "limit_up_price", "limit_down_price", "streak_min_known", "previous_state", "previous_streak", "denominator_eligible", "exclusion_reason", "association_ref", "contract_id"):
            if key in raw:
                item[key] = raw[key]
        normalized.append(item)
    by_key = {(row["security_id"], row["trade_date"]): row for row in normalized}
    security_ids = sorted({row["security_id"] for row in normalized})
    supplied_dates = list(market_dates) if market_dates is not None else sorted({row["trade_date"] for row in normalized})
    dates = sorted({_day(value, "market_date") for value in supplied_dates})
    output = [dict(row, promotion_state="NOT_EVALUATED") for row in normalized]
    output_by_key = {(row["security_id"], row["trade_date"]): row for row in output}
    for previous_date, trade_date in zip(dates, dates[1:]):
        for security_id in security_ids:
            previous = by_key.get((security_id, previous_date))
            current = by_key.get((security_id, trade_date))
            if not previous or previous["limit_state"] != "UP":
                continue
            if not (
                previous["streak_known"]
                and previous["streak"] is not None
                and previous["ladder_level"] in PROMOTION_LEVELS
            ):
                continue
            state = current["limit_state"] if current else "UNKNOWN"
            if state == "UNKNOWN" or (state == "UP" and not current["streak_known"]):
                promotion_state = "UNKNOWN"
            elif state == "SUSPENDED":
                promotion_state = "SUSPENDED"
            elif state == "NO_LIMIT":
                promotion_state = "NO_LIMIT"
            elif state in JUDGED_STATES:
                promotion_state = (
                    "SUCCESS"
                    if state == "UP"
                    and current["streak_known"]
                    and current["streak"] is not None
                    and current["streak"] == previous["streak"] + 1
                    else "NOT_ELIGIBLE"
                )
            else:
                promotion_state = "UNKNOWN"
            if current:
                output_by_key[(security_id, trade_date)]["promotion_state"] = promotion_state
    return sorted(output, key=lambda item: (item["trade_date"], item["security_id"]))

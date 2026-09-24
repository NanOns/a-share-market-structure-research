"""Minimum daily operands from one verified, bounded normalized slice."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Sequence

from .contracts import digest
from .materialize import VerifiedNormalizedSlice
from .session_gap_semantics import CONTRACT_ID as GAP_CONTRACT, classify_session_state


CONTRACT_ID = "FOCUS_PREDICATE_FACTS_BY_DATE_V2"
CENT = Decimal("0.01")


def _decimal(value: Any) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid local adjustment operand") from exc
    if not number.is_finite():
        raise ValueError("nonfinite local adjustment operand")
    return number


def _coordinate(rows: Mapping[date, Mapping[str, Any]], *, day: date,
                observation_day: date) -> tuple[Decimal, Decimal, Decimal] | None:
    anchor = rows.get(observation_day)
    row = rows.get(day)
    if not anchor or anchor.get("has_actual_bar") is not True:
        return None
    if not row or row.get("has_actual_bar") is not True:
        return None
    version = anchor.get("adjustment_version")
    if (not version or row.get("adjustment_version") != version or
            not str(anchor.get("adjustment_status", "")).startswith("VERIFIED") or
            not str(row.get("adjustment_status", "")).startswith("VERIFIED")):
        raise ValueError("predicate local adjustment identity mismatch")
    a_j, b_j = _decimal(row.get("qfq_mul")), _decimal(row.get("qfq_add"))
    a_t, b_t = _decimal(anchor.get("qfq_mul")), _decimal(anchor.get("qfq_add"))
    if a_j <= 0 or a_t <= 0:
        raise ValueError("nonpositive local adjustment multiplier")
    return a_j / a_t, (b_j - b_t) / a_t, _decimal(row.get("raw_close"))


def reanchor_frozen_price(*, normalized: VerifiedNormalizedSlice,
                          security_id: str, signal_day: date,
                          trade_date: date, value: str | None) -> str | None:
    """Move a signal-day price to the observation-day local affine basis."""
    if value is None:
        return None
    rows = normalized.by_security.get(security_id, {})
    coordinate = _coordinate(rows, day=signal_day, observation_day=trade_date)
    if coordinate is None:
        return None
    a, b, _ = coordinate
    price = _decimal(value)
    if price <= 0:
        raise ValueError("invalid frozen signal price")
    adjusted = (a * price + b).quantize(CENT, rounding=ROUND_HALF_UP)
    return str(adjusted) if adjusted > 0 else None


def build_predicate_facts_by_date(*, normalized: VerifiedNormalizedSlice,
                                  security_id: str, trade_date: date,
                                  sessions: Sequence[date],
                                  required_fields: frozenset[str],
                                  structure_break_v3: bool | None = None,
                                  ) -> tuple[dict[date, dict[str, Any]], str]:
    """Materialize only the requested calendar span and fields.

    Missing bars remain explicit. RPS history has no accepted per-day provider in
    this contract and is left unavailable; no source-day value is backfilled.
    """
    if (not sessions or sessions[-1] != trade_date or
            normalized.calendar[-1] != trade_date or
            tuple(sessions) != tuple(sorted(set(sessions))) or
            any(day not in normalized.calendar for day in sessions)):
        raise ValueError("predicate window outside verified master calendar")
    if security_id not in normalized.by_security:
        raise ValueError("predicate security absent from verified slice")
    rows = normalized.by_security[security_id]
    need_price = bool(required_fields & {"close", "dynamic_ma5", "dynamic_ma20"})
    closes: dict[date, Decimal | None] = {}
    if need_price:
        # Formation history precedes the episode's evaluation window. It may
        # form a moving average, but cannot count as a post-signal observation.
        formation = (20 if "dynamic_ma20" in required_fields else
                     5 if "dynamic_ma5" in required_fields else 1)
        first_position = normalized.calendar.index(sessions[0])
        history_start = normalized.calendar[max(0, first_position - formation + 1)]
        for day in normalized.calendar:
            if day < history_start:
                continue
            if day > trade_date:
                break
            coordinate = _coordinate(rows, day=day, observation_day=trade_date)
            if coordinate is None:
                closes[day] = None
            else:
                a, b, raw = coordinate
                value = (a * raw + b).quantize(CENT, rounding=ROUND_HALF_UP)
                if value <= 0:
                    raise ValueError("nonpositive reanchored predicate close")
                closes[day] = value
    positions = {day: i for i, day in enumerate(normalized.calendar)}
    facts: dict[date, dict[str, Any]] = {}
    for day in sessions:
        row = rows.get(day)
        daily: dict[str, Any] = {}
        if "has_actual_bar" in required_fields:
            daily["has_actual_bar"] = bool(row and row.get("has_actual_bar") is True)
        if "session_state" in required_fields:
            daily["session_state"] = classify_session_state(row).value
        if "close" in required_fields:
            close = closes.get(day)
            daily["close"] = str(close) if close is not None else None
        for field, length in (("dynamic_ma5", 5), ("dynamic_ma20", 20)):
            if field not in required_fields:
                continue
            end = positions[day]
            window = normalized.calendar[max(0, end - length + 1):end + 1]
            values = [closes.get(part) for part in window]
            daily[field] = (str(sum(values) / length)
                            if len(values) == length and all(v is not None for v in values)
                            else None)
        if "structure_break_v3" in required_fields:
            daily["structure_break_v3"] = structure_break_v3 if day == trade_date else None
        if "rps20_delta3" in required_fields:
            daily["rps20_delta3"] = None
        unknown = required_fields - set(daily)
        if unknown:
            raise ValueError("predicate field provider missing: " + ",".join(sorted(unknown)))
        facts[day] = daily
    fact_digest = digest({"contract_id": CONTRACT_ID, "session_gap_contract_id": GAP_CONTRACT,
                          "artifact_sha256": normalized.artifact_sha256,
                          "security_id": security_id, "trade_date": trade_date,
                          "required_fields": sorted(required_fields),
                          "facts_by_date": {day.isoformat(): value
                                            for day, value in facts.items()}})
    return facts, fact_digest

from __future__ import annotations

"""Versioned special price-phase resolution for the V4-02 price-limit path."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Iterable, Mapping


class SpecialPricePhase(str, Enum):
    REGULAR = "REGULAR"
    IPO_FIRST_5_TRADING_DAYS = "IPO_FIRST_5_TRADING_DAYS"
    DELISTING_FIRST_DAY = "DELISTING_FIRST_DAY"
    DELISTING_PERIOD = "DELISTING_PERIOD"
    RELISTING_FIRST_DAY = "RELISTING_FIRST_DAY"
    SPECIAL_REFERENCE_RESET = "SPECIAL_REFERENCE_RESET"
    UNKNOWN_SPECIAL_PHASE = "UNKNOWN_SPECIAL_PHASE"


@dataclass(frozen=True)
class SpecialPhaseEvent:
    security_id: str
    trade_date: str
    phase: SpecialPricePhase
    source_ref: str
    source_capture_sha256: str
    effective_date: str
    observed_at: str
    event_type: str = ""
    official_reference_price: str | None = None
    official_reference_formula: Mapping[str, str] | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "SpecialPhaseEvent":
        phase = SpecialPricePhase(str(row.get("phase", "")))
        event = cls(
            security_id=str(row.get("security_id") or ""),
            trade_date=str(row.get("trade_date") or ""), phase=phase,
            source_ref=str(row.get("source_ref") or ""),
            source_capture_sha256=str(row.get("source_capture_sha256") or ""),
            effective_date=str(row.get("effective_date") or ""),
            observed_at=str(row.get("observed_at") or ""),
            event_type=str(row.get("event_type") or ""),
            official_reference_price=(str(row["official_reference_price"]) if row.get("official_reference_price") is not None else None),
            official_reference_formula=(row.get("official_reference_formula") if isinstance(row.get("official_reference_formula"), Mapping) else None),
        )
        if not all((event.security_id, event.trade_date, event.effective_date, event.observed_at)):
            raise ValueError("SPECIAL_PHASE_IDENTITY_AND_DATES_REQUIRED")
        if phase in {SpecialPricePhase.DELISTING_FIRST_DAY, SpecialPricePhase.RELISTING_FIRST_DAY, SpecialPricePhase.SPECIAL_REFERENCE_RESET}:
            if not event.source_ref or len(event.source_capture_sha256) != 64:
                raise ValueError("SPECIAL_PHASE_OFFICIAL_SOURCE_AND_CAPTURE_HASH_REQUIRED")
        if phase == SpecialPricePhase.SPECIAL_REFERENCE_RESET and not (event.official_reference_price or event.official_reference_formula):
            # A phase can be known while its special reference is not. It must
            # fail closed until an official value or reproducible formula exists.
            return event
        return event


def _date(value: str) -> str:
    return str(value).replace("-", "")


def resolve_phase(events: Iterable[SpecialPhaseEvent], security_id: str, trade_date: str,
                  sessions: Iterable[str], delisting_period_sessions: int = 15) -> SpecialPricePhase:
    day = _date(trade_date)
    session_list = [_date(x) for x in sessions]
    try:
        index = session_list.index(day)
    except ValueError:
        return SpecialPricePhase.UNKNOWN_SPECIAL_PHASE
    for event in events:
        if event.security_id != security_id:
            continue
        start = _date(event.trade_date)
        if event.phase == SpecialPricePhase.DELISTING_FIRST_DAY and start in session_list:
            offset = index - session_list.index(start)
            if offset == 0:
                return SpecialPricePhase.DELISTING_FIRST_DAY
            if 0 < offset < delisting_period_sessions:
                return SpecialPricePhase.DELISTING_PERIOD
        elif day == start and event.phase in {SpecialPricePhase.RELISTING_FIRST_DAY, SpecialPricePhase.SPECIAL_REFERENCE_RESET}:
            return event.phase
    return SpecialPricePhase.REGULAR


def phase_limit_ratio(board_scope: str, phase: SpecialPricePhase, default_ratio: str | Decimal | None,
                      risk_status: str) -> Decimal | None:
    if phase in {SpecialPricePhase.DELISTING_FIRST_DAY, SpecialPricePhase.RELISTING_FIRST_DAY,
                 SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS}:
        return None
    if phase == SpecialPricePhase.DELISTING_PERIOD:
        return Decimal("0.20") if board_scope in {"CHINEXT", "STAR"} else Decimal("0.10") if board_scope in {"SH_MAIN", "SZ_MAIN"} else None
    if phase in {SpecialPricePhase.UNKNOWN_SPECIAL_PHASE, SpecialPricePhase.SPECIAL_REFERENCE_RESET}:
        return None
    if default_ratio is None:
        return None
    # Regular phase preserves the effective official risk-status rule.
    return Decimal(str(default_ratio))


def official_reference(event: SpecialPhaseEvent, formula_evaluator=None) -> Decimal | None:
    if event.official_reference_price is not None:
        value = Decimal(event.official_reference_price)
        return value if value > 0 else None
    if event.official_reference_formula and formula_evaluator:
        value = Decimal(str(formula_evaluator(event.official_reference_formula)))
        return value if value > 0 else None
    return None


def special_limit_prices(reference: str | Decimal, ratio: Decimal, tick: Decimal = Decimal("0.01")) -> tuple[Decimal, Decimal]:
    reference = Decimal(str(reference))
    if reference <= 0 or ratio <= 0 or ratio >= 1 or tick <= 0:
        raise ValueError("SPECIAL_LIMIT_INPUT_INVALID")
    up = ((reference * (Decimal("1") + ratio) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * tick
    down = ((reference * (Decimal("1") - ratio) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * tick
    return up, down

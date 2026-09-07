from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Iterable, Mapping

from tdx.gbbq_reader import GbbqRecord


TEN = Decimal("10")
CENT = Decimal("0.01")
ADJUSTMENT_VERSION = "tdx-affine-qfq-v0.2"


def _decimal(value: Decimal | float | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_half_up_price(value: Decimal | float | int | str) -> Decimal:
    """Round a CNY price to cents, using TDX's half-up convention."""
    return _decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class XrxdEvent:
    security_id: str
    ex_day: int
    cash_dividend_per_10: Decimal = Decimal("0")
    rights_price: Decimal = Decimal("0")
    bonus_transfer_per_10: Decimal = Decimal("0")
    rights_ratio_per_10: Decimal = Decimal("0")
    source_record_index: int = -1

    def validate(self) -> None:
        values = (
            self.cash_dividend_per_10,
            self.rights_price,
            self.bonus_transfer_per_10,
            self.rights_ratio_per_10,
        )
        if any(not value.is_finite() for value in values):
            raise ValueError("XRXD parameters must be finite")
        if TEN + self.bonus_transfer_per_10 + self.rights_ratio_per_10 == 0:
            raise ValueError("XRXD share denominator must not be zero")

    def mc(self) -> tuple[Decimal, Decimal]:
        """Return m and c where the theoretical ex-price is (P-c)/m."""
        self.validate()
        m = (TEN + self.bonus_transfer_per_10 + self.rights_ratio_per_10) / TEN
        c = (
            self.cash_dividend_per_10 - self.rights_ratio_per_10 * self.rights_price
        ) / TEN
        return m, c

    def as_dict(self) -> dict:
        return {
            "security_id": self.security_id,
            "event_date": self.ex_day,
            "category": 1,
            "cash_dividend": float(self.cash_dividend_per_10),
            "rights_price": float(self.rights_price),
            "bonus_transfer": float(self.bonus_transfer_per_10),
            "rights_ratio": float(self.rights_ratio_per_10),
            "source_record_index": self.source_record_index,
        }


def xrxd_from_gbbq(record: GbbqRecord) -> XrxdEvent:
    if record.category != 1:
        raise ValueError("only category=1 records can become XRXD events")

    # The audited reference exposes XRXD parameters at two-decimal precision.
    def parameter(value: float) -> Decimal:
        return _decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)

    return XrxdEvent(
        security_id=record.security_id,
        ex_day=record.event_date,
        cash_dividend_per_10=parameter(record.c1),
        rights_price=parameter(record.c2),
        bonus_transfer_per_10=parameter(record.c3),
        rights_ratio_per_10=parameter(record.c4),
        source_record_index=record.source_record_index,
    )


@dataclass(frozen=True)
class AdjustmentFactor:
    trade_date: int
    qfq_mul: Decimal
    qfq_add: Decimal
    hfq_mul: Decimal
    hfq_add: Decimal

    def qfq_price(self, raw_price: Decimal | float | int | str) -> Decimal:
        return round_half_up_price(self.qfq_mul * _decimal(raw_price) + self.qfq_add)

    def hfq_price(self, raw_price: Decimal | float | int | str) -> Decimal:
        return round_half_up_price(self.hfq_mul * _decimal(raw_price) + self.hfq_add)


def build_affine_factors(
    trade_dates: Iterable[int], events: Iterable[XrxdEvent]
) -> dict[int, AdjustmentFactor]:
    """Build date-position-based QFQ/HFQ factors without requiring ex-day bars.

    Events after the latest local trade date are deliberately ignored. For a
    trade date d, every effective event with ex_day > d is composed, including
    multiple events inside one suspension gap.
    """
    dates = sorted(set(trade_dates))
    if not dates:
        return {}
    latest = dates[-1]
    effective = sorted(
        (event for event in events if event.ex_day <= latest),
        key=lambda event: (event.ex_day, event.source_record_index),
    )
    for event in effective:
        event.validate()

    qfq: dict[int, tuple[Decimal, Decimal]] = {}
    a = Decimal("1")
    b = Decimal("0")
    event_index = len(effective) - 1
    with localcontext() as context:
        context.prec = 40
        for trade_date in reversed(dates):
            while event_index >= 0 and effective[event_index].ex_day > trade_date:
                m, c = effective[event_index].mc()
                a = a / m
                b = b - a * c
                event_index -= 1
            qfq[trade_date] = (+a, +b)

        a0, b0 = qfq[dates[0]]
        factors: dict[int, AdjustmentFactor] = {}
        for trade_date in dates:
            qa, qb = qfq[trade_date]
            if a0 == 0:
                ha, hb = Decimal("1"), Decimal("0")
            else:
                ha = qa / a0
                hb = (qb - b0) / a0
            factors[trade_date] = AdjustmentFactor(trade_date, +qa, +qb, +ha, +hb)
    return factors


def adjust_ohlc(
    raw_ohlc: Mapping[str, Decimal | float | int | str], factor: AdjustmentFactor, *, qfq: bool = True
) -> dict[str, Decimal]:
    price = factor.qfq_price if qfq else factor.hfq_price
    return {field: price(raw_ohlc[field]) for field in ("open", "high", "low", "close")}

"""Frozen-basket sector path from actual member bars and local adjustment."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from .price_path import reanchor_from_frozen_coefficients
from .sector_basket import SectorBasket, SectorOneDay, one_day_sector_return


CONTRACT_ID = "FOCUS_FROZEN_SECTOR_PATH_V1"


@dataclass(frozen=True)
class SectorPathDay:
    trade_date: date
    one_day: SectorOneDay | None
    nav: Decimal | None
    drawdown_current: Decimal | None
    mdd_close: Decimal | None
    continuity_quality: str


def frozen_sector_path(*, basket: SectorBasket, sessions: Sequence[date],
                       member_rows: Mapping[str, Mapping[date, Mapping[str, object]]],
                       minimum_coverage: Decimal = Decimal("0.80")) -> tuple[SectorPathDay, ...]:
    """A failed day breaks subsequent NAV; it cannot be bridged retroactively."""
    if not sessions or list(sessions) != sorted(set(sessions)):
        raise ValueError("invalid sector session path")
    anchor_valid = sum(
        reanchor_from_frozen_coefficients(
            sessions=[sessions[0]], rows=member_rows.get(security, {})) is not None
        for security in basket.security_ids)
    if not basket.security_ids:
        raise ValueError("empty frozen sector basket")
    base_ready = (Decimal(anchor_valid) / Decimal(len(basket.security_ids))
                  >= minimum_coverage)
    nav: Decimal | None = Decimal(1) if base_ready else None
    days = [SectorPathDay(sessions[0], None, nav,
                          Decimal(0) if base_ready else None,
                          Decimal(0) if base_ready else None,
                          "BASE_ANCHOR" if base_ready else "PATH_GAP")]
    peak = Decimal(1)
    mdd = Decimal(0)
    for previous, today in zip(sessions, sessions[1:]):
        member_returns: dict[str, Decimal | None] = {}
        for security in basket.security_ids:
            rows = member_rows.get(security, {})
            path = reanchor_from_frozen_coefficients(
                sessions=[previous, today], rows=rows)
            member_returns[security] = (path[1].close / path[0].close - 1
                                        if path is not None else None)
        one_day = one_day_sector_return(basket, member_returns,
                                        minimum_coverage=minimum_coverage)
        if nav is None or one_day.quality_status != "READY":
            nav = None
            days.append(SectorPathDay(today, one_day, None, None, None,
                                      "PATH_GAP"))
            continue
        nav *= Decimal(1) + one_day.median_return
        if nav <= 0:
            raise ValueError("nonpositive sector NAV")
        peak = max(peak, nav)
        drawdown = nav / peak - 1
        mdd = min(mdd, drawdown)
        days.append(SectorPathDay(today, one_day, nav, drawdown, mdd,
                                  "CONTINUOUS"))
    return tuple(days)

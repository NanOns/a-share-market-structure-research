from datetime import date, timedelta

import pytest

from src.v4.profile_primitives import derive_daily


def fixture(extra_statuses=(), missing_status=False, short=False, suspended_t=False):
    actual = 9 if short else 21
    first = date(2026, 1, 1)
    days = [(first + timedelta(days=i)).isoformat() for i in range(actual + len(extra_statuses) + int(suspended_t))]
    extras = dict(extra_statuses)
    if suspended_t:
        extras[days[-1]] = "SUSPENDED"
    elif extras:
        extras = {days[14 + i]: status for i, (_, status) in enumerate(extra_statuses)}
    bars = []
    statuses = []
    for day in days:
        if day in extras:
            if not missing_status:
                statuses.append((day, extras[day]))
            continue
        statuses.append((day, "ACTUAL_TRADED"))
        bars.append(dict(trade_date=day, qfq_close=10.0, qfq_high=11.0, qfq_low=9.0,
                         adjusted_quality="READY", amount=30_000_000.0))
    factors = {"amount_ratio20": {"value": 1.0, "quality_state": "OBSERVED"}}
    return bars, statuses, days, factors


@pytest.mark.parametrize("extra,missing,short,suspended_t,quality,suspended", [
    ((), False, False, False, "OBSERVED", 0),
    ((("x", "SUSPENDED"),), False, False, False, "OBSERVED", 1),
    ((("x", "SUSPENDED"), ("y", "SUSPENDED")), False, False, False, "OBSERVED", 2),
    ((("x", "UNKNOWN"),), False, False, False, "UNKNOWN", 0),
    ((("x", "SUSPENDED"),), True, False, False, "UNKNOWN", 0),
    ((), False, True, False, "UNKNOWN", 0),
    ((), False, False, True, "UNKNOWN", 0),
])
def test_ma10_and_prior20_status_gate(extra, missing, short, suspended_t, quality, suspended):
    bars, statuses, calendar, factors = fixture(extra, missing, short, suspended_t)
    result = derive_daily(bars, factors, statuses, calendar[-1], calendar)
    for name, count in (("ma10", 10), ("minimum_liquidity", 20)):
        item = result[name]
        assert item.quality == quality
        assert item.actual_count == min(count, len(bars) if name == "ma10" else max(0, len(bars) - 1)) or suspended_t
        assert item.field_window_mapping_id == "V4_04_FIELD_WINDOW_MAPPING_V1"
        assert item.window_contract_id == "TECHNICAL_BAR_WINDOW_V1"
        assert len(item.window_identity) == 64
        if not short and not suspended_t:
            assert item.suspended_count == suspended
            assert item.calendar_span == count + len(extra)
            assert item.window_end_trade_date == (bars[-1]["trade_date"] if name == "ma10" else bars[-2]["trade_date"])
            assert item.window_start_trade_date == (bars[-count]["trade_date"] if name == "ma10" else bars[-count-1]["trade_date"])

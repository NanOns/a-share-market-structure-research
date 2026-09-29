from src.v4.profile_primitives import derive_closed_period, derive_daily
from datetime import date, timedelta


def test_prior20_excludes_current_and_missing_window_unknown():
    bars = [dict(trade_date=f"2026-09-{d:02d}", qfq_close=10.0, qfq_high=11.0,
                 qfq_low=9.0, adjusted_quality="READY", amount=20_000_000.0)
            for d in range(1, 22)]
    bars[-1]["amount"] = 1_000_000_000.0
    factors = {"ma20": {"value": 10, "quality_state": "OBSERVED"},
               "atr20": {"value": 1, "quality_state": "OBSERVED"},
               "prior_high20": {"value": 11, "quality_state": "OBSERVED"},
               "amount_ratio20": {"value": 50, "quality_state": "OBSERVED"}}
    output = derive_daily(bars, factors, ["ACTUAL_TRADED"] * 21, "2026-09-21")
    assert output["minimum_liquidity"].value is True
    assert output["ma10"].value == 10
    assert output["pos250"].value is None
    assert output["bias20_atr"].value == 0
    assert output["dist_high20_atr"].value == 1
    assert derive_daily(bars[:10], factors, [], "2026-09-10")["minimum_liquidity"].quality == "UNKNOWN"


def test_formal_closed_period_filter_and_blocked_period():
    periods = [dict(period_last_session=f"2026-0{i}-28", period_view="CLOSED_ONLY",
                    period_status="CLOSED_ONLY_READY", price_basis="QFQ", close=float(i))
               for i in range(1, 7)]
    periods.append(dict(period_last_session="2026-09-30", period_view="ASOF_PARTIAL",
                        period_status="ASOF_PARTIAL_READY", price_basis="QFQ", close=100.0))
    output = derive_closed_period(periods, 5, "2026-09-24")
    assert output["close"] == 6
    assert output["ma5"] == 4
    periods[5]["period_status"] = "BLOCKED_BY_ADJUSTMENT"
    assert derive_closed_period(periods, 5, "2026-09-24")["period_view"] == "UNKNOWN"


def test_ma10_is_independent_of_unavailable_ma20():
    bars = [dict(trade_date=f"2026-09-{d:02d}", qfq_close=float(d), qfq_high=float(d + 1),
                 qfq_low=float(d - 1), adjusted_quality="READY", amount=20_000_000.0)
            for d in range(1, 16)]
    result = derive_daily(bars, {"ma20": {"value": None, "quality_state": "UNKNOWN"}},
                          ["ACTUAL_TRADED"] * 15, "2026-09-15")
    assert result["ma10"].quality == "OBSERVED"
    assert result["ma10"].value == sum(range(6, 16)) / 10
    assert result["ma10"].window_start_trade_date == "2026-09-06"
    assert result["ma10"].window_end_trade_date == "2026-09-15"


def test_window_traceability_with_confirmed_suspension_and_unknown_gap():
    start = date(2025, 1, 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range(252)]
    suspended = {days[80], days[81]}
    bars = [dict(trade_date=day, qfq_close=10.0 + i / 100, qfq_high=11.0 + i / 100,
                 qfq_low=9.0 + i / 100, adjusted_quality="READY", amount=30_000_000.0)
            for i, day in enumerate(days) if day not in suspended]
    statuses = [(day, "SUSPENDED" if day in suspended else "ACTUAL_TRADED") for day in days]
    factors = {"amount_ratio20": {"value": 1.0, "quality_state": "OBSERVED"}}
    good = derive_daily(bars, factors, statuses, days[-1])["pos250"]
    assert good.quality == "OBSERVED"
    assert good.actual_count == 250 and good.calendar_span == 252 and good.suspended_count == 2
    assert (good.window_start_trade_date, good.window_end_trade_date) == (days[0], days[-1])
    bad_statuses = [(d, "UNKNOWN" if d == days[80] else s) for d, s in statuses]
    assert derive_daily(bars, factors, bad_statuses, days[-1])["pos250"].quality == "UNKNOWN"
    assert derive_daily(bars[:9], factors, statuses[:9], bars[8]["trade_date"])["ma10"].quality == "UNKNOWN"
    assert derive_daily(bars[:-1], factors, statuses[:-1], days[-1])["ma10"].quality == "UNKNOWN"


def test_monthly_closed_period_lineage_input():
    periods = [dict(period_last_session=f"2026-0{i}-28", period_view="CLOSED_ONLY",
                    period_status="CLOSED_ONLY_READY", price_basis="QFQ", close=float(i),
                    source_daily_digest=f"daily-{i}") for i in range(1, 5)]
    result = derive_closed_period(periods, 3, "2026-09-24")
    assert result["period_view"] == "CLOSED_ONLY" and result["ma3"] == 3

from src.v4.profile_primitives import derive_closed_period, derive_daily


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

import pytest

from src.v4.profile_core import (
    closed_period_trend, compression, drawdown, extension_risk, ma_structure,
    near_high, participation, position, ratio_state, relative, severe_extension, trend,
)


def test_first_true_precedence_and_unknown_gates():
    row = dict(close=110, ma20=100, ma60=95, slope20=.2, slope60=.2,
               hh_progress=True, ll_progress=False, core_price_damage=False,
               atr20=2, bias20_atr=3.1, pos60=.9, ma5=105, ma10=102,
               range_ratio=.3, atr_ratio=.6, vol_ratio=.6,
               amount_ratio20=.7, minimum_liquidity=True, ret1=1, clv=.8,
               rps5=85, rps20=83, rps20_delta3=11, rel_market_1=.01,
               rel_market_5=.02, ret5=.04)
    assert trend(row).value == "UPTREND_STRONG"
    assert position(row).value == "EXTENDED"
    assert ma_structure(row).value == "BULL_ALIGNED"
    assert compression(row).value == "COMPRESSING_STRONG"
    assert relative(row, "COMPRESSING_STRONG", "BULL_ALIGNED").value == "ACTIVE_EMERGENCE"
    assert relative(row, "COMPRESSING_STRONG", "BULL_ALIGNED").evidence["compression_state"] == "COMPRESSING_STRONG"
    assert compression(row).evidence["minimum_liquidity"] is True
    assert ratio_state(row, "amount_ratio20").value == "CONTRACTED"
    assert participation(row).value == "LOW_PARTICIPATION_ADVANCE"
    assert extension_risk(row).value == "HIGH"
    assert severe_extension(extension_risk(row)).value is False
    row["atr_ratio"] = 1.5
    assert compression(row).value == "EXPANDING_EXTREME"
    row["amount_ratio20"] = 1.3
    row.pop("clv")
    assert participation(row).value == "UNKNOWN"
    assert participation(row).unknown_reason == "CLV_REQUIRED_FOR_BRANCH"
    row.pop("ma10")
    assert ma_structure(row).value == "UNKNOWN"


def test_no_unearned_risk_or_trend():
    assert extension_risk({"bias20_atr": 4}).value == "EXTREME"
    assert severe_extension(extension_risk({"bias20_atr": 4})).value is True
    assert severe_extension(extension_risk({"bias20_atr": 1})).value is None
    assert extension_risk({"bias20_atr": 1}).value == "UNKNOWN"
    assert trend({"close": 1}).value == "UNKNOWN"


def test_closed_period_and_position_descriptions():
    assert closed_period_trend({"period_view": "CLOSED_ONLY", "close": 12, "ma5": 11, "previous_ma5": 10}, "weekly").value == "WEEKLY_UP"
    assert closed_period_trend({"period_view": "ASOF_PARTIAL", "close": 12, "ma5": 11, "previous_ma5": 10}, "weekly").value == "UNKNOWN"
    assert closed_period_trend({"period_view": "CLOSED_ONLY", "close": 8, "ma3": 9, "previous_ma3": 10}, "monthly").value == "MONTHLY_DOWN"
    assert near_high({"prior_high20": 10, "close": 11, "atr20": 2}, 20).value == "ABOVE_PRIOR_HIGH"
    assert near_high({"prior_high20": 10, "close": 9, "atr20": 0}, 20).value == "UNKNOWN"
    assert drawdown({"close": 8, "hhv60": 10}, 60).value == "DEEP"
    with pytest.raises(ValueError):
        ratio_state({}, "arbitrary_key")

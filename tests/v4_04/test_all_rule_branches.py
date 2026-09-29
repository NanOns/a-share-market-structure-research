"""REV2 first-true branch, boundary and UNKNOWN vectors."""

import pytest

from src.v4.profile_core import (closed_period_trend, compression, drawdown,
                                 extension_risk, ma_structure, near_high,
                                 participation, position, ratio_state, relative,
                                 trend)


@pytest.mark.parametrize("override,expected", [
    ({"close": 90, "slope20": -.2, "slope60": -.2, "ll_progress": True}, "DOWNTREND_STRONG"),
    ({"close": 110, "slope20": .2, "slope60": .2, "hh_progress": True}, "UPTREND_STRONG"),
    ({"close": 90, "slope20": -.2}, "DOWNTREND"),
    ({"close": 110, "slope20": .2}, "UPTREND"),
    ({"close": 90, "slope20": -.1}, "SIDEWAYS_WEAK"),
    ({"close": 110, "slope20": .1}, "SIDEWAYS_STRONG"),
    ({"close": 100}, "SIDEWAYS"),
    ({"close": 110, "slope20": .2, "core_price_damage": True}, "SIDEWAYS_STRONG"),
    ({"core_price_damage": None}, "UNKNOWN"),
])
def test_trend_branches(override, expected):
    row = dict(close=100, ma20=100, ma60=95, slope20=0, slope60=0,
               hh_progress=False, ll_progress=False, core_price_damage=False, atr20=2)
    row.update(override)
    assert trend(row).value == expected


@pytest.mark.parametrize("bias,pos,expected", [
    (3, .1, "EXTENDED"), (0, .8, "HIGH_ZONE"), (0, .6, "MID_HIGH"),
    (0, .4, "MID_ZONE"), (0, .2, "MID_LOW"), (0, .1999, "LOW_ZONE"),
])
def test_position_buckets(bias, pos, expected):
    assert position({"bias20_atr": bias, "pos60": pos}).value == expected


@pytest.mark.parametrize("ma5,ma10,ma20,slope,expected", [
    (12, 11, 10, .01, "BULL_ALIGNED"), (8, 9, 10, -.01, "BEAR_ALIGNED"),
    (12, 13, 10, 0, "BULL_TRANSITION"), (8, 7, 10, 0, "BEAR_TRANSITION"),
    (10, 10, 10, 0, "MIXED"),
])
def test_ma_structure_branches(ma5, ma10, ma20, slope, expected):
    assert ma_structure(dict(ma5=ma5, ma10=ma10, ma20=ma20, slope20=slope)).value == expected


@pytest.mark.parametrize("atr,vol,ran,amount,liquid,expected", [
    (1.5, .5, .3, .5, True, "EXPANDING_EXTREME"),
    (1.1, .5, .3, .5, True, "EXPANDING"),
    (.7, .7, .35, .8, True, "COMPRESSING_STRONG"),
    (.9, .9, .6, 2, True, "COMPRESSING"),
    (.7, .7, .35, .8, False, "NORMAL"),
])
def test_compression_branches(atr, vol, ran, amount, liquid, expected):
    row = dict(atr_ratio=atr, vol_ratio=vol, range_ratio=ran,
               amount_ratio20=amount, minimum_liquidity=liquid)
    assert compression(row).value == expected


@pytest.mark.parametrize("ratio,expected", [
    (.49, "VERY_DRY"), (.5, "CONTRACTED"), (.8, "NORMAL"),
    (1.2, "EXPANDED"), (2, "VERY_EXPANDED"),
])
def test_amount_volume_buckets(ratio, expected):
    assert ratio_state({"amount_ratio20": ratio}, "amount_ratio20").value == expected
    assert ratio_state({"volume_ratio20": ratio}, "volume_ratio20").value == expected


@pytest.mark.parametrize("amount,ret,clv,expected", [
    (1.2, -.01, .8, "HIGH_PARTICIPATION_REVERSAL"),
    (1.2, .01, .7, "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE"),
    (1.2, .01, .6, "HIGH_PARTICIPATION_LOW_EFFICIENCY"),
    (.7, .01, .5, "LOW_PARTICIPATION_ADVANCE"),
    (.7, -.01, .5, "LOW_PARTICIPATION_DECLINE"),
    (1, 0, .5, "NORMAL_PARTICIPATION"),
    (1.2, .01, None, "UNKNOWN"),
])
def test_participation_branches(amount, ret, clv, expected):
    assert participation(dict(amount_ratio20=amount, ret1=ret, clv=clv)).value == expected


@pytest.mark.parametrize("delta,rps,rel,comp,ma,expected", [
    (10, 50, 0, "COMPRESSING", "MIXED", "ACTIVE_EMERGENCE"),
    (0, 50, .1, "NORMAL", "MIXED", "PASSIVE_RESILIENCE"),
    (1, 80, 0, "NORMAL", "MIXED", "LEADING_ACCELERATING"),
    (-3, 80, 0, "NORMAL", "MIXED", "LEADING_STABLE"),
    (4, 50, 0, "NORMAL", "MIXED", "IMPROVING"),
    (-4, 50, 0, "NORMAL", "MIXED", "WEAKENING"),
    (0, 19, 0, "NORMAL", "MIXED", "LAGGING"),
    (0, 50, 0, "NORMAL", "MIXED", "NEUTRAL"),
    (10, 50, 0, "UNKNOWN", "MIXED", "UNKNOWN"),
])
def test_relative_branches(delta, rps, rel, comp, ma, expected):
    row = dict(rps5=50, rps20=rps, rps20_delta3=delta,
               rel_market_1=rel, rel_market_5=0)
    assert relative(row, comp, ma).value == expected


@pytest.mark.parametrize("bias,ret5,amount,ret1,expected", [
    (4, None, None, None, "EXTREME"), (3, None, None, None, "HIGH"),
    (1, .4, 2, 0, "HIGH"), (2, 0, 1, 0, "MEDIUM"),
    (1, 0, 1, 0, "LOW"), (1, None, 1, 0, "UNKNOWN"),
])
def test_extension_branches(bias, ret5, amount, ret1, expected):
    row = dict(bias20_atr=bias, ret5=ret5, atr20=1, close=10,
               amount_ratio20=amount, ret1=ret1)
    assert extension_risk(row).value == expected


@pytest.mark.parametrize("close,expected_near,expected_draw", [
    (11, "ABOVE_PRIOR_HIGH", "SHALLOW"),
    (9, "NEAR", "MODERATE"),
    (7, "BELOW", "DEEP"),
])
def test_position_descriptions(close, expected_near, expected_draw):
    row = dict(close=close, prior_high20=10, atr20=2, hhv20=10)
    assert near_high(row, 20).value == expected_near
    assert drawdown(row, 20).value == expected_draw


def test_closed_period_boundaries():
    assert closed_period_trend(dict(period_view="CLOSED_ONLY", close=10, ma5=10, previous_ma5=9), "weekly").value == "WEEKLY_FLAT"
    assert closed_period_trend(dict(period_view="CLOSED_ONLY", close=11, ma3=10, previous_ma3=9), "monthly").value == "MONTHLY_UP"

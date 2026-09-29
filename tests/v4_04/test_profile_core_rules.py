from src.v4.profile_core import (
    compression, extension_risk, ma_structure, participation, position,
    ratio_state, relative, trend,
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
    assert ratio_state(row, "amount_ratio20").value == "CONTRACTED"
    assert participation(row).value == "LOW_PARTICIPATION_ADVANCE"
    assert extension_risk(row).value == "HIGH"
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
    assert extension_risk({"bias20_atr": 1}).value == "UNKNOWN"
    assert trend({"close": 1}).value == "UNKNOWN"

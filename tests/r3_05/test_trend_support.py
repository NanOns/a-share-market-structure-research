from shadow_v2.early_mover import trend_support
def test_bands():assert [trend_support(x) for x in (.39,.4,.55)]==["TREND_WEAK","TREND_MODERATE","TREND_STRONG"]

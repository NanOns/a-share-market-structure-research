from shadow_v2.breakout_prep import classify
def test_range_only_is_hit(): assert classify(True,"RANGE_CONTRACTED","VOL_NOT_CONTRACTED")==("BREAKOUT_RANGE_ONLY",True)

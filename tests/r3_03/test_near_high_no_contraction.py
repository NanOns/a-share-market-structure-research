from shadow_v2.breakout_prep import classify
def test_neither(): assert classify(True,"RANGE_NOT_CONTRACTED","VOL_NOT_CONTRACTED")==("NEAR_HIGH_NO_CONTRACTION",False)

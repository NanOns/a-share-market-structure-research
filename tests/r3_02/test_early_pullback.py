from shadow_v2.strong_pullback import classify
def test_one_day_is_not_mature():
 assert classify(True,"EARLY_PULLBACK","DEPTH_IN_V1_BAND","VOLUME_CONTRACTED")==("EARLY_PULLBACK",False,False)

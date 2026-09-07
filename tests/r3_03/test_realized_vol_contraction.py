from shadow_v2.breakout_prep import vol_status
def test_vol_threshold():
 assert vol_status(.9,1,.9)=="VOL_CONTRACTED" and vol_status(1,1,1)=="VOL_NOT_CONTRACTED"

from shadow_v2.breakout_prep import range_status
def test_range_threshold():
 assert range_status(.9,1,.9)=="RANGE_CONTRACTED" and range_status(1,1,1)=="RANGE_NOT_CONTRACTED"

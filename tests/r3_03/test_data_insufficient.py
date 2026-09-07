import math
from shadow_v2.breakout_prep import classify,range_status
def test_missing_first_class():
 r=range_status(math.nan,1,math.nan)
 assert classify(True,r,"VOL_CONTRACTED")==("DATA_INSUFFICIENT",False)

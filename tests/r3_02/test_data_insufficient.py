import math
from shadow_v2.strong_pullback import classify,volume_status
def test_missing_amount_is_not_zero_filled():
 v=volume_status(10,math.nan,math.nan)
 assert v=="VOLUME_DATA_INSUFFICIENT"
 assert classify(True,"ESTABLISHED_PULLBACK","DEPTH_IN_V1_BAND",v)==("DATA_INSUFFICIENT",False,False)

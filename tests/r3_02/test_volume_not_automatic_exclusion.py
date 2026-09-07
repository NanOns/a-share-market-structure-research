from shadow_v2.strong_pullback import VOLUME_NOT_CONTRACTED_IS_NOT_AUTOMATIC_EXCLUSION,classify,volume_status
def test_volume_is_independent_confirmation():
 assert VOLUME_NOT_CONTRACTED_IS_NOT_AUTOMATIC_EXCLUSION
 assert volume_status(100,100,1)=="VOLUME_NOT_CONTRACTED"
 assert classify(True,"ESTABLISHED_PULLBACK","DEPTH_IN_V1_BAND","VOLUME_NOT_CONTRACTED")[1] is True

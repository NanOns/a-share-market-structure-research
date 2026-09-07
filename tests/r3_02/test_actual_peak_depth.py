from shadow_v2.strong_pullback import depth_status
def test_frozen_depth_boundaries():
 assert depth_status(-.03)=="DEPTH_IN_V1_BAND" and depth_status(-.18)=="DEPTH_IN_V1_BAND"
 assert depth_status(-.029)=="DEPTH_TOO_SHALLOW" and depth_status(-.181)=="DEPTH_TOO_DEEP"

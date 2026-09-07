from shadow_v2.strong_pullback import classify
def test_core_fixture():
 assert classify(True,"ESTABLISHED_PULLBACK","DEPTH_IN_V1_BAND","VOLUME_CONTRACTED")==("PULLBACK_CORE",True,True)

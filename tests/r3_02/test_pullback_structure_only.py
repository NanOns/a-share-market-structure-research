from shadow_v2.strong_pullback import classify
def test_noncontracted_structure_fixture():
 assert classify(True,"ESTABLISHED_PULLBACK","DEPTH_IN_V1_BAND","VOLUME_NOT_CONTRACTED")==("PULLBACK_STRUCTURE_ONLY",True,False)

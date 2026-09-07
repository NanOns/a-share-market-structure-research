from shadow_v2.strong_pullback import classify
def test_shallow_and_deep_mismatch():
 for depth in ("DEPTH_TOO_SHALLOW","DEPTH_TOO_DEEP"):
  assert classify(True,"ESTABLISHED_PULLBACK",depth,"VOLUME_CONTRACTED")[0]=="DEPTH_MISMATCH"

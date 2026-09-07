from shadow_v2.strong_pullback import segment_status
def test_duration_bands():
 assert [segment_status(x) for x in (0,1,2)]==["NO_PULLBACK_SEGMENT","EARLY_PULLBACK","ESTABLISHED_PULLBACK"]

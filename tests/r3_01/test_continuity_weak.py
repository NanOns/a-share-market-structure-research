from shadow_v2.steady_trend import classify, continuity_class
def test_weak():
    assert continuity_class(.4999,20,1) == "CONTINUITY_WEAK"
    assert classify(True,"CONTINUITY_WEAK","PULSE_LOW") == ("CONTINUITY_WEAK",False)


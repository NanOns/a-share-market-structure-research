from shadow_v2.steady_trend import classify
def test_acceptable_and_base_gate():
    assert classify(True,"CONTINUITY_MODERATE","PULSE_LOW") == ("STEADY_ACCEPTABLE",True)
    assert classify(False,"CONTINUITY_STRONG","PULSE_LOW") == ("OUTSIDE_V1_STEADY",False)


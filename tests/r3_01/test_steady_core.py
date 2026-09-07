from shadow_v2.steady_trend import classify
def test_core():
    assert classify(True,"CONTINUITY_STRONG","PULSE_MODERATE") == ("STEADY_CORE",True)


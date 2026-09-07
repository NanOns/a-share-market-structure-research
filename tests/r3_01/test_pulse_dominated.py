from shadow_v2.steady_trend import classify, pulse_class
def test_single_pulse_is_diagnostic():
    assert pulse_class(.50001) == "PULSE_HIGH"
    assert classify(True,"CONTINUITY_STRONG","PULSE_HIGH") == ("PULSE_DOMINATED",False)


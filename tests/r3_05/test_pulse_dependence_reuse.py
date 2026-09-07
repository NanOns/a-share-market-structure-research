from shadow_v2.steady_trend import pulse_class
def test_reuse():assert pulse_class(.5)=="PULSE_MODERATE" and pulse_class(.51)=="PULSE_HIGH"

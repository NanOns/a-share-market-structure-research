import math
from shadow_v2.steady_trend import classify, continuity_class, pulse_class
def test_missing_does_not_become_zero_or_pulse():
    c=continuity_class(math.nan,20,1);p=pulse_class(math.nan)
    assert c == "CONTINUITY_DATA_INSUFFICIENT"
    assert p == "PULSE_DATA_INSUFFICIENT"
    assert classify(True,c,"PULSE_LOW") == ("DATA_INSUFFICIENT",False)


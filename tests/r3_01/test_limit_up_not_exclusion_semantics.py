from shadow_v2.steady_trend import LIMIT_UP_IS_NOT_AN_EXCLUSION, classify
def test_large_day_does_not_exist_as_classifier_input():
    assert LIMIT_UP_IS_NOT_AN_EXCLUSION is True
    assert classify(True,"CONTINUITY_STRONG","PULSE_MODERATE") == ("STEADY_CORE",True)


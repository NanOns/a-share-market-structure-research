from shadow_v2.steady_trend import continuity_class
def test_validity_is_first_class():
    assert continuity_class(.80, 14, .70) == "CONTINUITY_DATA_INSUFFICIENT"
    assert continuity_class(.60, 15, .75) == "CONTINUITY_STRONG"


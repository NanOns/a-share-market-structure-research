from forward.observation import transition
def test_unavailable():assert transition({}, {},data_available=False)=="DATA_UNAVAILABLE"

from forward.observation import transition
def test_model_change():assert transition({}, {},model_identity_same=False)=="SOURCE_REVISED"

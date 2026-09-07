from forward.observation import transition
def test_revision():assert transition({}, {},same_cutoff_revision=True)=="SOURCE_REVISED"

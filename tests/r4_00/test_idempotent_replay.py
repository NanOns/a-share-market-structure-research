from forward.observation import replay_status
def test_same():assert replay_status("a","b","a","b")=="VERIFIED_NO_NEW_FORWARD_OBSERVATION"

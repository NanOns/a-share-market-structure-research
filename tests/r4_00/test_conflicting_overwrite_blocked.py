from forward.observation import replay_status
def test_diff():assert replay_status("a","b","a","c")=="CONFLICT_BLOCKED"

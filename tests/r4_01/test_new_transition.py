from forward.live import states_for_union
def test_new():assert states_for_union([], [{"security_id":"SH.1"}])[0]["candidate_state"]=="NEW"

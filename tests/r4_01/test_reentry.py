from forward.live import states_for_union
def test_reentry():assert states_for_union([], [{"security_id":"SH.1"}],{"SH.1"})[0]["candidate_state"]=="REENTERED"

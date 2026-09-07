from forward.live import states_for_union
def test_exit():assert states_for_union([{"security_id":"SH.1"}],[])[0]["candidate_state"]=="EXITED"

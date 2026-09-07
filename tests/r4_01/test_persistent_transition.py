from forward.live import states_for_union
def test_persistent():
 x={"security_id":"SH.1","shadow_research_band":"CORE"};assert states_for_union([x],[x])[0]["candidate_state"]=="PERSISTENT"

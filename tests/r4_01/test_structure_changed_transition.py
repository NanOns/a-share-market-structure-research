from forward.live import states_for_union
def test_changed():
 a={"security_id":"SH.1","shadow_research_band":"CORE"};b={**a,"shadow_research_band":"SUPPORTED"};assert states_for_union([a],[b])[0]["candidate_state"]=="STRUCTURE_CHANGED"

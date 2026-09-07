from forward.observation import transition
def test_persistent():assert transition({"shadow_research_band":"A"},{"shadow_research_band":"A"})=="PERSISTENT"

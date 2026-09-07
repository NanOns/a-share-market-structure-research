from forward.observation import transition
def test_changed():assert transition({"shadow_research_band":"SUPPORTED_RESEARCH"},{"shadow_research_band":"CORE_RESEARCH"})=="STRUCTURE_CHANGED"

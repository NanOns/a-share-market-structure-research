from shadow_v2.research_priority import research_band
def test_missing_not_input():assert research_band(["SUPPORTED",None])=="SUPPORTED_RESEARCH"

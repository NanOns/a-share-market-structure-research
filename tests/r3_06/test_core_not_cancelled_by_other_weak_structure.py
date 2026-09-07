from shadow_v2.research_priority import research_band
def test_no_cancel():assert research_band(["CORE",None,None])=="CORE_RESEARCH"

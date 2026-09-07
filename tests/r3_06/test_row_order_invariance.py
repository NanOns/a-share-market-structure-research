from shadow_v2.research_priority import research_band
def test_order():assert research_band(["SUPPORTED","CORE",None])==research_band([None,"CORE","SUPPORTED"])

from shadow_v2.research_priority import STRUCTURE_COUNT_STACKING,research_band
def test_no_stack():assert not STRUCTURE_COUNT_STACKING and research_band(["CORE"])==research_band(["CORE"]*3)

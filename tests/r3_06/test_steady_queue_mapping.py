from shadow_v2.research_priority import queue_tier
def test_map():assert queue_tier("STEADY_QUEUE","STEADY_CORE")=="CORE" and queue_tier("STEADY_QUEUE","CONTINUITY_WEAK") is None

from shadow_v2.early_mover import classify
def test_uncertain():assert classify(True,"PRICE_BEHAVIOR_STYLE_ONLY","TREND_STRONG","CONTINUITY_STRONG","PULSE_LOW","POSITION_HEALTHY")==("CONTEXT_UNCERTAIN",False)

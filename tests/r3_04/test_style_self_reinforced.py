from shadow_v2.sector_leader import classify
def test_style(): assert classify(True,"PRICE_BEHAVIOR_STYLE",["STRONG_SUPPORT"]*4)==("STYLE_SELF_REINFORCED",False)

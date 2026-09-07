from shadow_v2.sector_leader import classify
def test_supported(): assert classify(True,"NON_PRICE_STYLE",["STRONG_SUPPORT","MODERATE_SUPPORT","WEAK_SUPPORT","WEAK_SUPPORT"])==("LEADER_SUPPORTED",True)

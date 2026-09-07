from shadow_v2.sector_leader import classify
def test_core(): assert classify(True,"ECONOMIC_SECTOR",["STRONG_SUPPORT"]*2+["MODERATE_SUPPORT","WEAK_SUPPORT"])==("LEADER_CORE",True)

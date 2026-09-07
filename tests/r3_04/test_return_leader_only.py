from shadow_v2.sector_leader import classify
def test_return_only(): assert classify(True,"ECONOMIC_SECTOR",["WEAK_SUPPORT"]*4)==("RETURN_LEADER_ONLY",False)

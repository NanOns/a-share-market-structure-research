from shadow_v2.sector_leader import classify
def test_unknown(): assert classify(True,"UNKNOWN_STYLE",["STRONG_SUPPORT"]*4)==("DATA_INSUFFICIENT",False)

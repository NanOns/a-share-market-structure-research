from shadow_v2.early_mover import classify
def test_stabilizing_priority():assert classify(True,"SECTOR_STABILIZING","TREND_STRONG","CONTINUITY_WEAK","PULSE_HIGH","POSITION_HEALTHY")[0]=="SECTOR_ALREADY_STABILIZING"

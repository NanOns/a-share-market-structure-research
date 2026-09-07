from shadow_v2.early_mover import classify
def test_missing():assert classify(True,"NO_SECTOR_SIGNAL","TREND_DATA_INSUFFICIENT","CONTINUITY_STRONG","PULSE_LOW","POSITION_HEALTHY")==("DATA_INSUFFICIENT",False)

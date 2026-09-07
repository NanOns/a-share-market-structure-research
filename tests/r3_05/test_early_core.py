from shadow_v2.early_mover import classify
def test_core():assert classify(True,"NO_SECTOR_SIGNAL","TREND_MODERATE","CONTINUITY_MODERATE","PULSE_LOW","POSITION_HEALTHY")==("EARLY_CORE",True)

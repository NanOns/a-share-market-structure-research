from shadow_v2.early_mover import classify
def test_pulse():assert classify(True,"NO_SECTOR_SIGNAL","TREND_STRONG","CONTINUITY_WEAK","PULSE_HIGH","POSITION_HEALTHY")==("SHORT_TERM_PULSE",False)

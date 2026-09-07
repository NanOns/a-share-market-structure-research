from shadow_v2.early_mover import classify

def test_supported_requires_trend_or_position_support():
    assert classify(True,"NO_SECTOR_SIGNAL","TREND_MODERATE","CONTINUITY_MODERATE","PULSE_LOW","POSITION_NOT_CONFIRMED")==("EARLY_SUPPORTED",True)
    assert classify(True,"NO_SECTOR_SIGNAL","TREND_WEAK","CONTINUITY_MODERATE","PULSE_LOW","POSITION_NOT_CONFIRMED")==("SHORT_TERM_PULSE",False)

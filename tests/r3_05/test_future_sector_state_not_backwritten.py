from shadow_v2.early_mover import classify
def test_current_inputs_only():
 args=(True,"NO_SECTOR_SIGNAL","TREND_MODERATE","CONTINUITY_MODERATE","PULSE_LOW","POSITION_HEALTHY");assert classify(*args)==classify(*args)

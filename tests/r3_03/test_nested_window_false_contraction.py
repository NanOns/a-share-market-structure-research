from shadow_v2.breakout_prep import range_status
def test_old_extreme_rollout_does_not_override_nonoverlap_evidence():
 assert range_status(1.1,1.0,1.1)=="RANGE_NOT_CONTRACTED"

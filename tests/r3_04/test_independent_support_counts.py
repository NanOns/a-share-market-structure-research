from shadow_v2.sector_leader import support_counts
def test_counts(): assert support_counts(["STRONG_SUPPORT","STRONG_SUPPORT","MODERATE_SUPPORT","WEAK_SUPPORT"])==(2,3)

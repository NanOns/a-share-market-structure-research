from production.daily import freshness_decision
def test_computation_revision_is_not_no_data():
    old={'cutoff_date':'20260904','source_fingerprint':'s','computation_identity':{'sha256':'old'},'render_identity':{'sha256':'r'}}
    cur={'source_fingerprint':'s','computation_identity':{'sha256':'new'},'render_identity':{'sha256':'r'}}
    assert freshness_decision(True,'20260904',old,cur)=='SAME_CUTOFF_COMPUTATION_REVISION'

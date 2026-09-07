from production.daily import freshness_decision
def test_revision_not_no_data():assert freshness_decision(True,'20260904',{'cutoff_date':'20260904','source_fingerprint':'a'},{'source_fingerprint':'b'})=='SAME_CUTOFF_SOURCE_REVISION'

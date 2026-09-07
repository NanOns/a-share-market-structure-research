from production.daily import freshness_decision
def test_same_is_no_data():assert freshness_decision(True,'20260904',{'cutoff_date':'20260904','source_fingerprint':'x'},{'source_fingerprint':'x'})=='VERIFIED_NO_NEW_DATA'

from production.daily import freshness_decision,changed_components
def test_membership_revision():
 old={'cutoff_date':'20260904','source_fingerprint':'a','source_fingerprint_components':{'tdxzs':'a'}};new={'source_fingerprint':'b','source_fingerprint_components':{'tdxzs':'b'}};assert freshness_decision(True,'20260904',old,new)=='SAME_CUTOFF_SOURCE_REVISION' and changed_components(old,new)==['tdxzs']

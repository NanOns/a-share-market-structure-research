from production.daily import phase6_gate
def test_gate():assert phase6_gate({'fingerprint':True,'leader':True})=='PASS'

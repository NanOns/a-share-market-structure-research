from production.daily import phase6_gate
def test_gate():assert phase6_gate({'x':True})=='PASS' and phase6_gate({'x':False})=='BLOCKED'

from candidates.research_priority import phase5_gate
def test_gate():assert phase5_gate({'x':True})=='PASS' and phase5_gate({'x':False})=='BLOCKED'

from sector.phase2 import phase2_gate

def test_gate():
    assert phase2_gate({'hash':True,'tests':True})=='PASS'
    assert phase2_gate({'hash':False,'tests':True})=='BLOCKED'

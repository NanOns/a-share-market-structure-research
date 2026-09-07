def gate(checks):return 'PASS' if all(checks.values()) else 'BLOCKED'
def test_gate_requires_every_principle():
    assert gate({'coverage':True,'breadth':True,'ties':True,'leader':True,'identity':True})=='PASS'
    assert gate({'coverage':True,'breadth':False,'ties':True,'leader':True,'identity':True})=='BLOCKED'

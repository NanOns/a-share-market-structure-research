from sector.phase2 import validity

def test_coverage_inclusive_boundary():
    assert validity(10,7,'STYLE')[0]
    assert not validity(10,6,'STYLE')[0]
    assert not validity(0,0,'THEME')[0]

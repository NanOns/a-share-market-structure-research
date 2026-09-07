from sector.phase2 import validity

def test_minimums_and_excluded():
    assert validity(5,5,'INDUSTRY')[0]
    assert not validity(7,7,'THEME')[0]
    assert not validity(100,100,'EXCLUDE_FROM_THEME_RANK')[0]

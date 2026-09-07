from scanner.sector_scanner import scan_row

def test_low_coverage_boundaries(strong):
    strong['coverage']=.70
    assert scan_row(strong)['low_coverage']
    strong['coverage']=.85
    assert not scan_row(strong)['low_coverage']

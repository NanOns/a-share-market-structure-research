from scanner.sector_scanner import scan_row

def test_current_strength_all_conditions(strong):
    assert scan_row(strong)['current_strength']
    strong['sector_ret20_median']=0
    assert not scan_row(strong)['current_strength']

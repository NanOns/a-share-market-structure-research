from scanner.sector_scanner import scan_row

def test_high_concentration_boundary_and_non_veto(strong):
    strong['top3_concentration']=.60
    row=scan_row(strong)
    assert row['high_concentration'] and row['current_strength']
    assert 'HIGH_CONCENTRATION_WARNING' in row['reason_codes']

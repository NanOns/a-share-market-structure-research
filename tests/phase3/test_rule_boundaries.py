from scanner.sector_scanner import scan_row

def test_current_exact_rs_and_strict_mdd(strong):
    strong.update(sector_rs20_pct=.80,sector_mdd20_median=-.149999)
    assert scan_row(strong)['current_strength']
    strong['sector_mdd20_median']=-.15
    assert not scan_row(strong)['current_strength']

def test_stabilization_exact_delta(strong):
    strong.update(sector_rs20_pct=.5,sector_rs5_pct=.6,sector_ret20_median=0,
      sector_breadth_ret5_pos=.60,sector_breadth_ret20_pos=.50,sector_amount_ratio_median=.9)
    assert scan_row(strong)['stabilization']

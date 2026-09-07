from scanner.sector_scanner import scan_row

def test_stabilization_requires_prior_damage(strong):
    strong.update(sector_rs20_pct=.5,sector_rs5_pct=.7,sector_breadth_ret5_pos=.65,
                  sector_breadth_ret20_pos=.5,sector_ret20_median=-.01,sector_pos60_median=.7,
                  sector_mdd20_median=-.02,sector_amount_ratio_median=.9)
    assert scan_row(strong)['stabilization']
    strong.update(sector_ret20_median=.01,sector_pos60_median=.7,sector_mdd20_median=-.02)
    assert not scan_row(strong)['stabilization']

def test_prior_damage_value_and_coverage_must_come_from_same_branch(strong):
    strong.update(sector_rs20_pct=.5,sector_rs5_pct=.7,
                  sector_breadth_ret5_pos=.65,sector_breadth_ret20_pos=.5,
                  sector_ret20_median=-.01,sector_ret20_median__valid_count=2,
                  sector_ret20_median__valid_ratio=.2,
                  sector_pos60_median=.7,sector_pos60_median__valid_count=9,
                  sector_pos60_median__valid_ratio=.9,
                  sector_mdd20_median=-.02,sector_amount_ratio_median=.9)
    assert not scan_row(strong)['stabilization']

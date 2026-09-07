from scanner.sector_scanner import scan_row

def test_reacceleration_requires_pullback(strong):
    assert scan_row(strong)['reacceleration']
    strong.update(sector_mdd20_median=-.02,sector_dist_high20_median=-.02)
    assert not scan_row(strong)['reacceleration']

def test_pullback_value_and_coverage_must_come_from_same_branch(strong):
    strong.update(sector_mdd20_median=-.04,
                  sector_mdd20_median__valid_count=2,
                  sector_mdd20_median__valid_ratio=.2,
                  sector_dist_high20_median=-.01,
                  sector_dist_high20_median__valid_count=9,
                  sector_dist_high20_median__valid_ratio=.9)
    assert not scan_row(strong)['reacceleration']

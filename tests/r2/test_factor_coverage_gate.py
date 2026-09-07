from scanner.sector_scanner import scan_row
def test_low_required_factor_coverage_cannot_hit(sector_row):
    sector_row['sector_ret20_median__valid_count']=2;sector_row['sector_ret20_median__valid_ratio']=.25
    out=scan_row(sector_row);assert not out['current_strength'] and out['scanner_quality_status']=='DATA_INSUFFICIENT'

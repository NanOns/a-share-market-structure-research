from scanner.sector_scanner import scan_row
def test_common_coverage_required(sector_row):
    sector_row['breadth_5_20_common_valid_count']=4;sector_row['breadth_5_20_common_valid_ratio']=.5
    out=scan_row(sector_row);assert not out['stabilization'] and not out['reacceleration']

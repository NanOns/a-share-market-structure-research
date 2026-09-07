from scanner.sector_scanner import scan_row
def test_insufficient_is_not_none_semantics(sector_row):
    sector_row['current_strength_joint_valid_count']=2
    out=scan_row(sector_row);assert out['scanner_quality_status']=='DATA_INSUFFICIENT' and 'FAIL_FACTOR_COVERAGE' in out['failed_conditions']

from scanner.stock_scanner import scan_row
def test_warning(base): base['leader_sector_count']=2;assert 'MULTIPLE_LEADER_SECTORS' in scan_row(base)['warning_codes']

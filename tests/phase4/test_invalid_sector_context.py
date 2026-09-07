from scanner.stock_scanner import scan_row
def test_no_leader_without_valid_context(base): base['leader_eligible']=False;assert not scan_row(base)['sector_leader']

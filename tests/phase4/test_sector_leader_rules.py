from scanner.stock_scanner import scan_row
def test_leader(base): assert scan_row(base)['sector_leader']

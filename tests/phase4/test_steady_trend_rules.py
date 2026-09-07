from scanner.stock_scanner import scan_row
def test_steady(base): assert scan_row(base)['steady_trend']

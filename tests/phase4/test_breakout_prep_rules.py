from scanner.stock_scanner import scan_row
def test_breakout(base): base.update(DIST_HIGH20=-.04);assert scan_row(base)['breakout_prep']

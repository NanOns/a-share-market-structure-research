from scanner.stock_scanner import scan_row
def test_pullback(base): base.update(RET5=.01,DIST_HIGH20=-.10,POS20=.7);assert scan_row(base)['strong_pullback']

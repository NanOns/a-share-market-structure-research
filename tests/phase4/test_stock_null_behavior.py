from scanner.stock_scanner import scan_row
def test_null_never_zero(base): base['RET20']=None; r=scan_row(base);assert not r['steady_trend'] and not r['breakout_prep']

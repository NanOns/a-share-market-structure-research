from scanner.stock_scanner import scan_row
def test_gate(base): base['universe_status']='OTHER';assert scan_row(base)['scanner_hits']==''

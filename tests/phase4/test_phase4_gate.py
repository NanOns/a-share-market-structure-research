from scanner.stock_scanner import phase4_gate
def test_gate(): assert phase4_gate({'a':True})=='PASS' and phase4_gate({'a':False})=='BLOCKED'

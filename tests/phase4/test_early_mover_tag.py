from scanner.stock_scanner import scan_row
def test_tag(base): base.update(RET5=.12,RET20=.1,has_current_strength_sector=False,leader_eligible=False);assert scan_row(base)['early_mover']

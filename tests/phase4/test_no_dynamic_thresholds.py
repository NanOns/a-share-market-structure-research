from scanner.stock_scanner import RULES
def test_thresholds_static(): assert all(not callable(x[2]) for rules in RULES.values() for x in rules)

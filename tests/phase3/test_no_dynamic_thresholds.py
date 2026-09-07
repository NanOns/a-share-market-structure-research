from scanner.sector_scanner import THRESHOLDS,RULE_VERSION

def test_frozen_constants():
    assert RULE_VERSION=='sector-scanner-ruleset-v1.2-evidence-binding'
    assert THRESHOLDS['current_rs20_pct']==.80
    assert THRESHOLDS['high_concentration']==.60

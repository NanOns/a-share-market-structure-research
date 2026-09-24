from datetime import date

import pytest

from src.focus_tracker.v33_scanner_facts import (SOURCE_SCANNER_CONTRACT,
                                                bridge_scanner_facts)


DAY = date(2026, 9, 22)


def _evidence(value=True):
    return {"contract_id": SOURCE_SCANNER_CONTRACT, "security_id": "000001.SZ",
            "trade_date": DAY.isoformat(),
            "launch": {"checks": {"NOT_STRUCTURE_BREAK": value}},
            "pullback": {"checks": {"NOT_STRUCTURE_BREAK": value}}}


def test_exact_source_check_inverts_to_structure_break():
    result = bridge_scanner_facts(evidence=_evidence(True),
                                  security_id="000001.SZ", trade_date=DAY)
    assert result["structure_break_v3"] is False
    assert result["quality"] == "READY"


def test_missing_check_stays_unknown():
    result = bridge_scanner_facts(evidence=_evidence(None),
                                  security_id="000001.SZ", trade_date=DAY)
    assert result["structure_break_v3"] is None
    assert result["quality"] == "UNKNOWN"


def test_conflicting_branches_and_wrong_identity_fail_closed():
    evidence = _evidence(True)
    evidence["pullback"]["checks"]["NOT_STRUCTURE_BREAK"] = False
    with pytest.raises(ValueError, match="conflicting"):
        bridge_scanner_facts(evidence=evidence, security_id="000001.SZ", trade_date=DAY)
    with pytest.raises(ValueError, match="identity"):
        bridge_scanner_facts(evidence=_evidence(), security_id="000002.SZ", trade_date=DAY)

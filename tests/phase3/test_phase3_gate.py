import pytest
from scanner.sector_scanner import phase3_gate,snapshot_guard

def test_gate_and_snapshot_semantics():
    assert phase3_gate({'a':True,'b':True})=='PASS'
    assert phase3_gate({'a':True,'b':False})=='BLOCKED'
    snapshot_guard(['2026-09-04'],20260904,20260904)
    with pytest.raises(ValueError): snapshot_guard(['2026-09-03'],20260904,20260904)

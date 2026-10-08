import pytest
from workbench_service.raw_turnover import cells
from workbench_service.current_v4_context import SourceInvalid

def test_no_scaling_and_no_fake_zero_when_source_invalid():
    result=cells(dict(trade_date='2026-09-30',amount=82291392.0,volume=6221484),'2026-09-30','SHARES','CNY')
    assert result['amount']['value']==82291392.0 and result['volume']['value']==6221484
    result=cells(dict(trade_date='2026-09-30',amount=float('nan'),volume=-1),'2026-09-30','SHARES','CNY')
    assert all(x['quality']=='UNKNOWN' and x['value'] is None and x['reason'] for x in result.values())

def test_wrong_day_or_undeclared_unit_fail_closed():
    with pytest.raises(SourceInvalid,match='DATE_MISMATCH'):cells(dict(trade_date='2026-10-09'),'2026-09-30','SHARES','CNY')
    with pytest.raises(SourceInvalid,match='UNIT_CONTRACT_REQUIRED'):cells(dict(trade_date='2026-09-30'),'2026-09-30','TDX_SOURCE_NATIVE','CNY')

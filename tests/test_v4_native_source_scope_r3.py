from copy import deepcopy
import pytest
from workbench_analysis.native_source_reconciliation_r3 import reconcile,BOARDS
POLICY=dict(contract_id='TDX_A_STOCK_DELTA_SCOPE_POLICY_V2',required_boards=sorted(BOARDS),unknown_identity='QUARANTINE_NEVER_INVENT_CANONICAL_ID')
def inputs():
    bar=dict(source_security_key='SH.600000',trade_date='2026-10-09',open=10,high=12,low=9,close=11,volume=100)
    daily=dict(code='sh.600000',date='2026-10-09',tradestatus='1',open='10.0000',high='12',low='9',close='11',volume='100')
    return [bar,dict(bar,source_security_key='BJ.920000')],[daily],{'SH.600000'}
def test_exact_required_scope_with_all_raw_rows_and_quarantine_retained():
    native,daily,codes=inputs();result=reconcile(native,daily,codes,POLICY,'2026-10-09')
    assert result['status']=='SCOPED_REQUIRED_PROVIDER_FACTS_RECONCILED'
    assert result['raw_native_rows']==2 and result['raw_daily_rows']==1 and result['compared_values']==5
    assert result['quarantined_native_rows']==[dict(code='BJ.920000',reason='OUTSIDE_CURRENT_FOUR_BOARD_IDENTITY_SCOPE',formal_consumer_allowed=False)]
    assert result['all_market_scope_pass'] is False
@pytest.mark.parametrize('case',['new_sh','duplicate_bj','tiny_decimal_difference','missing_active','suspended_with_bar','nonfinite','wrong_date'])
def test_raw_scope_and_exact_value_negatives(case):
    native,daily,codes=inputs()
    if case=='new_sh':native.append(dict(native[0],source_security_key='SH.600001'))
    if case=='duplicate_bj':native.append(dict(native[1]))
    if case=='tiny_decimal_difference':daily[0]['close']='11.000000000000000001'
    if case=='missing_active':native=native[1:]
    if case=='suspended_with_bar':daily[0]['tradestatus']='0'
    if case=='nonfinite':daily[0]['close']='NaN'
    if case=='wrong_date':daily[0]['date']='2026-10-08'
    assert reconcile(native,daily,codes,POLICY,'2026-10-09')['status']=='SOURCE_RECONCILIATION_FAILED'

def test_current_engineering_replay_cannot_reach_promotion_or_read_before_scope_guard(tmp_path,monkeypatch):
    from workbench_analysis.operational_daily_executor_v1 import derive_ready_sources
    from workbench_analysis.operational_daily_ready_owner_v2 import build
    monkeypatch.delenv('R4_NATIVE_ISOLATION',raising=False)
    with pytest.raises(ValueError,match='ENGINEERING_REPLAY_CANNOT_PROMOTE'):
        derive_ready_sources(tmp_path,'2026-10-09',{},engineering_replay_current=True)
    with pytest.raises(ValueError,match='ISOLATED_ENGINEERING_CURRENT_REPLAY_REQUIRED'):
        build(tmp_path,{},source_readiness={},engineering_replay_current=True)
    monkeypatch.setenv('R4_NATIVE_ISOLATION','1')
    with pytest.raises(ValueError,match='ENGINEERING_REPLAY_CANNOT_PROMOTE'):
        derive_ready_sources(tmp_path,'2026-10-09',{},engineering_replay_current=True,readback_url='http://127.0.0.1:1')

def test_same_payload_different_location_or_dependency_cannot_borrow_ready_gate():
    from workbench_analysis.operational_daily_executor_v1 import readiness_binding_revision
    frozen={'path':'source/a.json','sha256':'a'*64}
    dependencies={'identity':{'path':'identity.json','sha256':'b'*64}}
    original=readiness_binding_revision('same_source',frozen,dependencies)
    assert original==readiness_binding_revision('same_source',dict(frozen),dict(dependencies))
    assert original!=readiness_binding_revision('same_source',dict(frozen,path='source/b.json'),dependencies)
    assert original!=readiness_binding_revision('same_source',frozen,{'identity':{'path':'identity.json','sha256':'c'*64}})

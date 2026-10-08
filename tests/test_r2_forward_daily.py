import copy
import pytest
from workbench_service.current_v4_context import SourceInvalid
from workbench_service.forward_daily import calendar_extension,verify_due_settlement,CONTRACT,ForwardStore,OperationalForwardAuthority,LocalForwardPriceSource
from workbench_analysis.v4_15_settlement_successor import price_path

def test_calendar_only_appends_accepted_sessions():
    old=['2026-09-28','2026-09-29'];new=old+['2026-09-30']
    assert calendar_extension(old,new,old[-1],new[-1])==new
    with pytest.raises(SourceInvalid,match='PREFIX_REWRITE'):calendar_extension(old,['2026-09-25']+new,old[-1],new[-1])
    with pytest.raises(SourceInvalid,match='FROZEN_CALENDAR_REWRITE'):calendar_extension(new,[old[0],new[-1]],old[0],new[-1])

def test_due_missing_price_is_not_pending():
    row=dict(verified_identity=False,verified_adjustment=False,evaluation_basis_date='2026-09-30')
    result=price_path(10,[row],'2026-09-30')
    assert result['outcome_status']!='PENDING' and result['R_N'] is None
    plan=dict(enrollment_id='e',horizon=1,due_date='2026-09-30')
    outcome=dict(plan,adapter_contract_id=CONTRACT,report_cutoff='2026-09-30',outcome_status=result['outcome_status'])
    assert verify_due_settlement(dict(plans=[plan],outcomes=[outcome]),'2026-09-30')==1
    with pytest.raises(SourceInvalid):verify_due_settlement(dict(plans=[plan],outcomes=[]),'2026-09-30')
    outcome['outcome_status']='PENDING'
    with pytest.raises(SourceInvalid):verify_due_settlement(dict(plans=[plan],outcomes=[outcome]),'2026-09-30')

def test_no_due_requires_no_maturity():
    assert verify_due_settlement(dict(plans=[dict(due_date=None)],outcomes=[]),'2026-09-30')==0

def test_frozen_t0_is_append_only(tmp_path):
    store=ForwardStore(tmp_path,'journal')
    frozen=dict(T0='2026-09-29',members=['a','b'],reference=10)
    binding=store.append('t0_freezes','e',frozen)
    assert store.append('t0_freezes','e',copy.deepcopy(frozen))==binding
    with pytest.raises(SourceInvalid,match='IDENTITY_CONFLICT'):store.append('t0_freezes','e',dict(frozen,reference=11))
    assert store.read(binding)==frozen

def test_same_raw_source_pending_advances_with_calendar_and_cutoff(tmp_path):
    from types import SimpleNamespace
    from workbench_analysis.v4_15_settlement import VectorPriceSource,freeze_basket
    from workbench_analysis.v4_15_settlement_successor import SettlementRuntime
    store=ForwardStore(tmp_path,'journal')
    snap=store.append('snapshots','s',dict(universe=[dict(security_id='S',close=10)]))
    frozen=store.append('t0_freezes','e',dict(T0='2026-09-29',enrollment_id='e',signal_id='S',comparison_reference=10,snapshot=snap,
        market=freeze_basket([],'2026-09-29'),sector=freeze_basket([],'2026-09-29','SECTOR'),
        controls=dict(assignment_digest='frozen',**{k:dict(control_entity_ids=[],control_assignment_id=k) for k in ('A','B','C')})))
    old=LocalForwardPriceSource(tmp_path,{},'2026-09-29','2026-09-29',accepted_paths=SimpleNamespace(bindings={},calendar=['2026-09-29']))
    new=LocalForwardPriceSource(tmp_path,{},'2026-09-29','2026-09-30',accepted_paths=SimpleNamespace(bindings={},calendar=['2026-09-29','2026-09-30']))
    assert old.binding['sha256']!=new.binding['sha256']
    row=dict(close=11,high=12,low=9,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,
        adjustment_identity='test',evaluation_basis_date='2026-09-30',transform_coefficients=dict(alpha=1,beta=0))
    a=OperationalForwardAuthority(tmp_path,['2026-09-29'],{})
    pending=SettlementRuntime(a,store).settle(frozen,VectorPriceSource({},old.binding),'2026-09-29',horizons=(1,))
    assert store.read(pending[0])['outcome_status']=='PENDING'
    a.sessions.append('2026-09-30');source=VectorPriceSource({'S':{'2026-09-30':row}},new.binding)
    runtime=SettlementRuntime(a,store);observed=runtime.settle(frozen,source,'2026-09-30',horizons=(1,))
    assert store.read(observed[0])['outcome_status']=='OBSERVED' and store.read(observed[0])['revision_sequence']==2
    assert runtime.settle(frozen,source,'2026-09-30',horizons=(1,))==observed
    assert len(store.refs('outcomes'))==2

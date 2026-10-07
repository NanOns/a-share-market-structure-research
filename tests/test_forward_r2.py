"""Required R2 counterexamples and inherited candidate vectors."""
import copy
import pickle
from types import FunctionType
from pathlib import Path
import pytest
from tests.test_full_chain_repair import shadow
from tests import forward_p1_vectors as p1
from workbench_analysis import v4_15_forward_r2 as candidate
from workbench_analysis import v4_15_forward_p1 as previous

# Reuse all externally audited inputs/assertions against the new candidate.
g=dict(p1.__dict__,candidate=candidate)
for name in ('runtime_fixture','revision_vector','stock_vector','sector_vector'):
    fn=getattr(p1,name)
    g[name]=FunctionType(fn.__code__,g,name,fn.__defaults__)

@pytest.mark.parametrize('number',range(1,13))
def test_pass_keep_stock(number): g['stock_vector'](number)
@pytest.mark.parametrize('number',range(1,13))
def test_pass_keep_sector(number): g['sector_vector'](number)

def state_vector(number,tmp_path):
    runtime,store,freeze,source,enrollment,snapshot=g['runtime_fixture']()
    pending=runtime.settle(freeze,source,'2030-01-01',(3,))[0]
    pending_bytes=pickle.dumps(store.read(pending))
    assert store.read(pending)['outcome_status']=='PENDING'
    assert runtime.settle(freeze,source,'2030-01-02',(3,))[0]==pending
    # A real filesystem snapshot/reopen between states, rather than same-object retry.
    path=tmp_path/'restart.pkl';path.write_bytes(pickle.dumps(store.data))
    reopened=p1.MemoryStore();reopened.data=pickle.loads(path.read_bytes())
    runtime=candidate.SettlementRuntime(p1.FixtureAuthority(),reopened);store=reopened
    due=runtime.settle(freeze,source,p1.BASIS,(3,))[0]
    assert due!=pending and store.read(due)['outcome_status']=='OBSERVED'
    assert runtime.settle(freeze,source,p1.BASIS,(3,))[0]==due
    assert runtime.settle(freeze,source,'2030-01-01',(3,))[0]==pending
    assert pickle.dumps(store.read(pending))==pending_bytes
    first=store.read(due)
    source.rows['A'][p1.BASIS].update(close=12,high=13)
    source.binding={'sha256':p1.historical.digest(source.rows)}
    corrected=runtime.settle(freeze,source,p1.BASIS,(3,))[0]
    readback=runtime.readback(freeze,p1.BASIS)
    assert corrected!=due and store.read(due)==first
    assert store.read(corrected)['supersedes']==due
    assert store.read(corrected)['first_observed_id']==first['outcome_revision_id']
    assert readback['FIRST_OBSERVED'][3]==first
    assert readback['LATEST_CORRECTED'][3]==store.read(corrected)
    assert readback['pending_items']==[] and len(readback['pending_history'])==1
    identity=[first['enrollment_id'],3,candidate.CONTRACT_ID,first['evaluation_source_digest'],'DUE',p1.BASIS,p1.historical.digest(runtime.authority.sessions)]
    assert p1.historical.digest(identity)==first['outcome_revision_id']
    return dict(id=f'I3-{number:02}',input=dict(sessions=runtime.authority.sessions,source=first['evaluation_source_digest'],restart_file=str(path)),pending=store.read(pending),due=first,corrected=store.read(corrected),readback=readback,historical_pending_bytes_unchanged=True,repeated_pre_due_same_ref=True,repeated_due_same_ref=True,wall_clock_random_used=False)

@pytest.mark.parametrize('number',range(1,11))
def test_state_vector(number,tmp_path):state_vector(number,tmp_path)

def price_vector(number):
    endpoint=p1.row();rows=[endpoint];reference=10
    patches={1:dict(close=-1),2:dict(close=0),3:dict(high=10),4:dict(low=12),5:dict(low=13,high=12),
        6:dict(transform_coefficients={'alpha':1,'beta':-20},T0_transform_coefficients={'alpha':1,'beta':0}),7:dict(close=float('nan')),
        9:dict(status='DELISTED',terminal_value=0,terminal_verified=True,terminal_evidence='VERIFIED_FIXTURE'),
        10:dict(status='DELISTED',terminal_value=0,terminal_verified=False,terminal_evidence='UNVERIFIED'),
        11:dict(status='CONFIRMED_SUSPENSION',close=None,high=None,low=None)}
    endpoint.update(patches.get(number,{}))
    if number==12:rows=[dict(p1.row(),close=-1),endpoint]
    new=candidate.price_path(reference,rows,p1.BASIS);old=previous.price_path(reference,rows,p1.BASIS)
    if number in (1,2,3,4,5,6,7,10,11): assert new['R_N'] is None and new['outcome_status']!='OBSERVED'
    elif number==9: assert new['R_N']==-1
    elif number==8: assert new==old
    else: assert abs(new['R_N']-.1)<1e-12 and new['MFE_N'] is None
    # JSON receipts represent nonfinite inputs explicitly, not invalid JSON tokens.
    serial=copy.deepcopy(rows)
    if number==7:serial[0]['close']='NaN'
    return dict(id=f'I4-{number:02}',input=dict(reference=reference,rows=serial),old_result=clean(old),new_result=clean(new),expected='Verified terminal zero allowed; invalid ordinary prices/envelope fail closed; interior never clears verified endpoint')

def clean(value):
    import math
    if isinstance(value,float) and not math.isfinite(value):return str(value)
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    return value

@pytest.mark.parametrize('number',range(1,13))
def test_price_vector(number):price_vector(number)

@pytest.mark.parametrize('patch',[dict(close=float('inf')),dict(high=float('-inf')),dict(open=0),dict(open=99),dict(terminal_value=-1,status='DELISTED',terminal_verified=True,terminal_evidence='X')])
def test_extra_domain_boundaries(patch):assert candidate.price_path(10,[dict(p1.row(),**patch)],p1.BASIS)['R_N'] is None

def test_sector_successor_negative_member_and_terminal_zero():
    members=[dict(security_id=s,close=10,adjustment_identity='AFFINE_A',source_identity='LOCAL_SOURCE_A') for s in ('A','B')]
    basket=candidate.freeze_sector_basket(members,'2030-01-01','IND',{'sha256':'fixture'})
    assert basket['basket_contract_id']=='SECTOR_BASKET_FORWARD_PATH_V2'
    points=[dict(trade_date=p1.BASIS,members={s:p1.row() for s in ('A','B')})]
    points[0]['members']['A']['close']=-1
    assert candidate.sector_path(basket,points,p1.BASIS,{'sha256':'fixture'})['R_N'] is None
    points[0]['members']['A'].update(status='DELISTED',terminal_value=0,terminal_verified=True,terminal_evidence='VERIFIED')
    assert candidate.sector_path(basket,points,p1.BASIS,{'sha256':'fixture'})['R_N']==pytest.approx(-.45)

def test_worker_r2_simulation_and_retry(shadow):
    from tests.test_full_chain_repair import future
    from scripts.v4_16_forward_r2_worker import DurableSettlementWorker
    from scripts.v4_16_shadow_runtime import digest
    db,_=shadow;authority,source=future(db)
    worker=DurableSettlementWorker(db,'FORWARD_R2_FIXTURE')
    due=next(d for d in db.rows('due') if d['horizon']==1)
    sha=source.binding['sha256'];key=worker.enqueue(digest([due['enrollment_id'],1]),sha,'2026-10-09')
    result=worker.deliver(key,sha,authority,lambda:source,'2026-10-09')
    assert result['outcome_contract_id']==candidate.CONTRACT_ID
    assert worker.deliver(key,sha,authority,lambda:source,'2026-10-09')==result
    db.controller.simulation=False
    with pytest.raises(ValueError,match='R2_INDEPENDENT_ACCEPTANCE_REQUIRED'):
        worker.deliver(key,sha,authority,lambda:(_ for _ in ()).throw(AssertionError('SOURCE_OPENED')),'2026-10-09')


def test_historical_pending_and_observed_contracts_remain_immutable():
    runtime,store,freeze,source,enrollment,snapshot=g['runtime_fixture']()
    old=previous.SettlementRuntime(runtime.authority,store)
    old_freeze=old.freeze_t0(enrollment,snapshot)
    old_pending=old.settle(old_freeze,source,'2030-01-01',(3,))[0]
    old_bytes=pickle.dumps(store.read(old_pending))
    runtime.settle(freeze,source,'2030-01-01',(3,))
    observed=store.read(runtime.settle(freeze,source,p1.BASIS,(3,))[0])
    assert pickle.dumps(store.read(old_pending))==old_bytes
    assert observed['revision_sequence']==2
    assert observed['first_observed_id']==observed['outcome_revision_id']
    assert runtime.readback(freeze,p1.BASIS)['FIRST_OBSERVED'][3]==observed

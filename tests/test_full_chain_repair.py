"""Direct database, crash/restart, capability and numerical repair proofs."""
import copy
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from scripts.full_chain_repair_io import ROOT
from scripts.v4_16_capability_resolution import resolve,admission
from scripts.v4_16_shadow_runtime import canonical,digest
from scripts.v4_16_settlement_worker_v2 import DurableSettlementWorker
from workbench_analysis.v4_15_settlement_successor import price_path,benchmark,validate_affine
from workbench_analysis import v4_15_settlement as old

def load(path):return json.loads((ROOT/path).read_bytes())

@pytest.mark.parametrize('case',range(1,9))
def test_capability_block(case):
    contract=load('config/v4_16_runtime_capability_resolution_v1.json');head=load(contract['current_audit_head']['path'])
    requested=['PURE_CORE_STOCK']
    if case==1:requested=['V4_09_N01_CURRENT_RUNTIME_PREWATCH']
    if case==3:contract['runtime_capability_dependency_graph']['UNRELATED']=[];requested=['UNRELATED']
    if case==4:
        head['entries']['A08_CURRENT_RUNTIME'].update(current_state='CLOSED_EXTERNAL',blocks_affected_capability_in_shadow=False)
        contract['current_audit_issue_resolution']['A08_CURRENT_RUNTIME'].update(current_state='CLOSED_EXTERNAL',blocks_affected_capability_in_shadow=False)
    if case==5:
        contract['blocked_issue_ids'].append('MISSING');contract['current_audit_issue_resolution']['MISSING']={}
        with pytest.raises(ValueError,match='UNKNOWN_AUDIT_ISSUE'):resolve(contract,head,requested)
        return
    if case==6:
        contract['current_audit_issue_resolution']['A08_CURRENT_RUNTIME']['affected_capabilities']=[]
        with pytest.raises(ValueError,match='PROJECTION_DRIFT'):resolve(contract,head,requested)
        return
    if case==8:requested=['AMOUNT_A_H21_FORMAL_CONSUMER']
    result=resolve(contract,head,requested)
    assert result['admitted']==(case in (3,4))
    assert result['permission_granted'] is False
    if case in (1,2,7):assert 'PURE_CORE_STOCK' in result['effective_blocked_runtime_capabilities']
    if case==7:
        from scripts.validate_r25_preflight import inspect_inputs
        with pytest.raises(ValueError,match='CURRENT_AUDIT_CAPABILITY_BLOCKED'):
            inspect_inputs(ROOT,{'grant':{'capability_scope':['PURE_CORE_STOCK']}},None,None,None,None,None)

def row():
    return dict(close=11,high=12,low=10,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,
                evaluation_basis_date='2030-01-03',adjustment_identity='LOCAL_AFFINE_V1',transform_coefficients={'alpha':1,'beta':0})

INVALID=[{'alpha':0,'beta':0},{'alpha':-1,'beta':0},{'alpha':float('nan'),'beta':0},{'alpha':float('inf'),'beta':0},
         {'alpha':1,'beta':float('nan')},{'beta':0},{'alpha':1},{'alpha':True,'beta':0},None,{'alpha':1,'beta':0,'extra':0}]

@pytest.mark.parametrize('coeff',INVALID)
@pytest.mark.parametrize('placement',['endpoint','interior','T0','benchmark'])
def test_affine(coeff,placement):
    r=row();r0=row()
    if placement=='T0':r['T0_transform_coefficients']=coeff
    elif placement=='interior':r0['transform_coefficients']=coeff
    else:r['transform_coefficients']=coeff
    if placement=='benchmark':
        basket=old.freeze_basket([dict(security_id='S',close=10)],'2030-01-02')
        result=benchmark(basket,{'S':r},.1,'2030-01-03')
        assert result['return'] is None and result['benchmark_unknown_weight']==1
    else:
        assert price_path(10,[r0,r],'2030-01-03')['outcome_status']=='ADJUSTMENT_UNKNOWN'

@pytest.mark.parametrize('case',['basis','identity','T0_nan','overflow'])
def test_affine_other(case):
    rows=[row(),row()];reference=10
    if case=='basis':rows[0]['evaluation_basis_date']='2030-01-02'
    if case=='identity':rows[0]['adjustment_identity']='MIXED'
    if case=='T0_nan':reference=float('nan')
    if case=='overflow':rows[0]['transform_coefficients']['alpha']=1e308
    assert price_path(reference,rows,'2030-01-03')['outcome_status']=='ADJUSTMENT_UNKNOWN'

@pytest.mark.parametrize('case',['actual','suspended','delisted','identity','adjustment','missing','sector_small','sector','exclude'])
def test_benchmark_contract(case):
    members=[dict(security_id='A',close=10),dict(security_id='B',close=10)]
    kind='SECTOR' if case.startswith('sector') or case=='exclude' else 'MARKET'
    if case=='sector_small':members=members[:1]
    basket=old.freeze_basket(members,'2030-01-02',kind)
    rows={m['security_id']:row() for m in members}
    if case=='suspended':rows['A']['status']='CONFIRMED_SUSPENSION'
    if case=='delisted':rows['A'].update(status='DELISTED',terminal_verified=True,terminal_evidence='EXACT_TERMINAL',terminal_value=0)
    if case=='identity':rows['A']['verified_identity']=False
    if case=='adjustment':rows['A']['verified_adjustment']=False
    if case=='missing':rows['A']['close']=None
    out=benchmark(basket,rows,.1,'2030-01-03')
    fields=load('config/v4_15_forward_market_benchmark_contract_v1.json')
    for key in ('benchmark_id','benchmark_members','initial_weights','fixed_shares','benchmark_constituent_policy','benchmark_valuation_coverage','benchmark_marked_weight','quote_age','quote_trade_date'):
        assert key in out
    assert not out['marked_permission'] and out['benchmark_marked_weight']==0 and out['relative_market_return_marked'] is None
    assert 'relative_return' not in out
    assert ('relative_sector_return' if kind=='SECTOR' else 'relative_market_return') in out
    if kind=='SECTOR':assert out['sector_benchmark_id']==basket['benchmark_id']
    if case in ('suspended','identity','adjustment','missing','sector_small'):assert out['return'] is None
    if case=='exclude':assert 'TARGET' not in out['sector_members']

@pytest.fixture
def shadow():
    from scripts.r24r1_simulation import prepare,controller,SimulationClock
    from scripts.r24r1_io import ref
    from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SuccessorDatabase
    def current_fixture_bindings(authority,deps,sources,seed):
        deps['bindings']=[ref(b['path']) for b in deps['bindings']]
    x=prepare(changes=current_fixture_bindings);c=controller(x)
    c.deps.update(queue_migration=ref('migrations/v4_16_settlement_queue_v2.sql'),integrity_migration=ref('migrations/v4_16_real_shadow_integrity_v2.sql'))
    db=SuccessorDatabase(c,ROOT/x['database'])
    try:
        OneSessionLaunchController(db).run(x['request'],clock=SimulationClock())
        yield db,x
    finally:db.close()

@pytest.mark.parametrize('case',['publication','enrollment','slot_revision','event','due','horizon','outcome','evaluation','state','admission_manifest'])
def test_direct_db_reject(shadow,case):
    db,x=shadow
    kind={'slot_revision':'realtime_admission','event':'enrollment','horizon':'due','evaluation':'outcome','admission_manifest':'realtime_admission'}.get(case,case)
    if kind=='outcome':
        due=db.rows('due')[0]
        payload=dict(enrollment_id=due['enrollment_id'],horizon=due['horizon'],due_date=due['due_date'],frozen_t0=due['frozen_t0'],evaluation_source_digest='a'*64,evaluation_source={'sha256':'a'*64})
    else:payload=copy.deepcopy(db.rows(kind)[0])
    if case=='publication':payload['slot_id']='ORPHAN'
    elif case=='enrollment':payload['logical_event_id']='ORPHAN';payload['owner_logical_event']='ORPHAN'
    elif case=='slot_revision':payload['observation_slot']['revision']=99
    elif case=='event':payload['owner_logical_event']='WRONG'
    elif case=='due':payload['enrollment_id']='ORPHAN'
    elif case=='horizon':payload['horizon']=2
    elif case=='outcome':payload['enrollment_id']='ORPHAN'
    elif case=='evaluation':payload['horizon']=3
    elif case=='state':payload['model_contract_id']='WRONG'
    elif case=='admission_manifest':payload['source_manifest_digest']='WRONG'
    # New identity avoids relying only on a duplicate-key rejection.
    if kind=='enrollment':payload['enrollment_id']='NEGATIVE'
    if kind=='due':payload['enrollment_id']='NEGATIVE' if case=='horizon' else payload['enrollment_id']
    if kind=='realtime_admission':payload['enrollment_id']='NEGATIVE'
    if kind=='publication':payload['revision']=99
    with pytest.raises(sqlite3.IntegrityError):db.transaction(lambda:db.append(kind,'NEGATIVE_'+case,payload))

def future(db):
    from workbench_analysis.v4_15_settlement import VectorPriceSource
    authority=copy.copy(db.controller.authority);authority.daily=dict(authority.daily,target_trade_date='2026-10-09')
    binding=db.controller.sources['future_binding'];authority.data=dict(authority.data,component_artifacts={'ADJUSTED_DAILY':binding})
    source=VectorPriceSource(load(binding['path'])['rows'],binding)
    return authority,source

@pytest.mark.parametrize('case',['enqueue','restart','CAS','claim_crash','result_crash','idempotent','corrected','predue','no_UI','stop','retry'])
def test_settlement_queue(shadow,case):
    db,x=shadow;authority,source=future(db);worker=DurableSettlementWorker(db,'W1',lease_seconds=60)
    due=next(d for d in db.rows('due') if d['horizon']==1);due_id=digest([due['enrollment_id'],1]);sha=source.binding['sha256']
    if case=='predue':
        with pytest.raises(ValueError,match='PRE_DUE'):worker.enqueue(due_id,sha,'2026-10-08')
        assert not source.read_log;return
    key=worker.enqueue(due_id,sha,'2026-10-09')
    if case=='enqueue':assert worker.row(key,sha)['status']=='READY';return
    if case=='restart':
        second=sqlite3.connect(db.path,isolation_level=None);assert second.execute('select count(*) from settlement_queue_v2').fetchone()[0]==1;second.close()
    if case=='CAS':
        token=worker.claim(key,sha);other=DurableSettlementWorker(db,'W2')
        assert token and other.claim(key,sha) is None;return
    if case=='claim_crash':
        with pytest.raises(RuntimeError,match='AFTER_CLAIM'):worker.deliver(key,sha,authority,lambda:source,'2026-10-09',fail_at='claim')
        db.conn.execute('update settlement_queue_v2 set lease_until=0 where queue_key=?',(key,))
    if case=='stop':db.append('control','STOP',dict(stop_new_acceptance=True))
    if case=='retry':
        with pytest.raises(ValueError):worker.deliver(key,sha,authority,lambda:object(),'2026-10-09')
        assert worker.row(key,sha)['retry_count']==1 and worker.row(key,sha)['backlog_reason']
    if case=='result_crash':
        with pytest.raises(RuntimeError,match='AFTER_RESULT'):worker.deliver(key,sha,authority,lambda:source,'2026-10-09',fail_at='result')
        assert worker.row(key,sha)['status']=='SETTLED'
    result=worker.deliver(key,sha,authority,lambda:source,'2026-10-09')
    assert worker.row(key,sha)['status']=='ACKED'
    assert worker.deliver(key,sha,authority,lambda:source,'2026-10-09')==result
    assert len([o for o in db.rows('outcome') if o['enrollment_id']==due['enrollment_id']])==1
    if case=='corrected':
        source.binding=dict(source.binding,sha256=digest('CORRECTED_VECTOR_ONLY'))
        authority.data['component_artifacts']['ADJUSTED_DAILY']=source.binding
        sha2=source.binding['sha256'];key2=worker.enqueue(due_id,sha2,'2026-10-09')
        corrected=worker.deliver(key2,sha2,authority,lambda:source,'2026-10-09')
        assert corrected['evaluation_revision']==2 and corrected['first_observed_id']==result['outcome_revision_id']

def test_legacy_fixture_gate():
    from workbench_analysis.fep_e5.ledger import Ledger
    pg=MagicMock();pg.info.dbname='production'
    for op in ('install','put','cas'):
        ledger=Ledger(pg)
        args=() if op=='install' else ('models','id',{}) if op=='put' else ('grant','request',0,'ALLOW','2026-10-06T00:00:00Z')
        with pytest.raises(ValueError,match='FIXTURE_ONLY'):getattr(ledger,op)(*args)
    with pytest.raises(ValueError,match='PRODUCTION_DSN'):Ledger(pg,historical_fixture=True).install()
    pg.info.dbname='fep_e5_legacy_fixture';Ledger(pg,historical_fixture=True).install();assert pg.execute.called

def test_disabled_successor_no_database():
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import RealShadowController
    with pytest.raises(ValueError,match='NOT_AUTHORIZED'):RealShadowController(ROOT)
    assert not (ROOT/'data/v4/shadow_real_v1').exists()

def test_two_actual_worker_connections_one_CAS_winner(shadow):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    db,x=shadow;authority,source=future(db)
    due=next(d for d in db.rows('due') if d['horizon']==1)
    worker=DurableSettlementWorker(db,'SETUP');sha=source.binding['sha256']
    key=worker.enqueue(digest([due['enrollment_id'],1]),sha,'2026-10-09')
    barrier=Barrier(2)
    def claim(owner):
        local=copy.copy(db);local.conn=sqlite3.connect(db.path,isolation_level=None)
        try:
            barrier.wait();return DurableSettlementWorker(local,owner).claim(key,sha)
        finally:local.conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(claim,['W1','W2']))
    assert sum(r is not None for r in results)==1

def test_old_V3_obligation_authority_rejected(shadow):
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SettlementObligationControllerR4R2
    db,x=shadow
    with pytest.raises(ValueError,match='STALE_OBLIGATION_DEPENDENCY|EXACT_DEPENDENCY_MISMATCH'):
        SettlementObligationControllerR4R2(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])

def test_V5_obligation_restart_after_stop_without_new_activation():
    from scripts.r24r1_simulation import prepare,controller,SimulationClock
    from scripts.r24r1_io import ref
    from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SuccessorDatabase,SettlementObligationControllerR4R2
    def v5_fixture(authority,deps,sources,seed):
        deps['contract_id']='V4_16_RUNTIME_DEPENDENCIES_V5'
        deps['bindings']=[ref(b['path']) for b in deps['bindings']]
        deps.update(queue_migration=ref('migrations/v4_16_settlement_queue_v2.sql'),integrity_migration=ref('migrations/v4_16_real_shadow_integrity_v2.sql'))
    x=prepare(changes=v5_fixture);c=controller(x);db=SuccessorDatabase(c,ROOT/x['database'])
    launch=OneSessionLaunchController(db);launch.run(x['request'],clock=SimulationClock());launch.stop()
    due=next(d for d in db.rows('due') if d['horizon']==1);authority,source=future(db)
    worker=DurableSettlementWorker(db,'FIRST');sha=source.binding['sha256'];key=worker.enqueue(digest([due['enrollment_id'],1]),sha,'2026-10-09')
    db.close()
    resumed=SettlementObligationControllerR4R2(ROOT,ROOT/x['database'],simulation=True,simulation_dependencies=x['manifest'])
    db=resumed.database(ROOT/x['database'])
    try:
        assert db.rows('control') and DurableSettlementWorker(db,'RESUMED').row(key,sha)['status']=='READY'
        outcome=DurableSettlementWorker(db,'RESUMED').deliver(key,sha,authority,lambda:source,'2026-10-09')
        assert outcome['enrollment_id']==due['enrollment_id']
        with pytest.raises(ValueError,match='SETTLEMENT_ONLY'):resumed.verify_request(x['request'])
    finally:db.close()

def test_roll_back_publication_keeps_zero_queue(shadow):
    db,x=shadow
    assert db.conn.execute('SELECT count(*) FROM settlement_queue_v2').fetchone()[0]==0
    from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController
    from scripts.r24r1_simulation import SimulationClock
    before={k:db.rows(k) for k in ('publication','enrollment','due','outcome')}
    publication=db.rows('publication')[0]
    request=dict(x['request'],revision=2,expected_head=publication['publication_id'])
    with pytest.raises(ValueError,match='INJECTED_TRANSACTION_FAILURE'):
        OneSessionLaunchController(db).run(request,clock=SimulationClock(),fail_at='head')
    assert before=={k:db.rows(k) for k in before}

def test_unknown_due_session_appends_delivery_revision(shadow):
    from datetime import date,timedelta
    db,x=shadow;authority,source=future(db)
    enrollment=db.rows('enrollment')[0]
    original=next(d for d in db.rows('due') if d['enrollment_id']==enrollment['enrollment_id'] and d['horizon']==10)
    assert original['due_date'] is None
    sessions=list(authority.sessions)
    for i in range(16):sessions.append((date.fromisoformat(sessions[-1])+timedelta(days=1)).isoformat())
    for index,day in enumerate(sessions):db.conn.execute('INSERT OR IGNORE INTO integrity_calendar_v2 VALUES(?,?)',(index,day))
    due_date=sessions[sessions.index(enrollment['T0'])+10]
    derived=dict(original,due_date=due_date,outcome_status='DUE')
    key=digest([enrollment['enrollment_id'],10,due_date,enrollment['frozen_t0']])
    db.transaction(lambda:db.append('due_revision',key,derived))
    authority.sessions=sessions;authority.daily=dict(authority.daily,target_trade_date=due_date)
    worker=DurableSettlementWorker(db,'CALENDAR_EXTENSION')
    queue=worker.enqueue(key,source.binding['sha256'],due_date,due_kind='due_revision')
    result=worker.deliver(queue,source.binding['sha256'],authority,lambda:source,due_date)
    assert result['due_date']==due_date and result['horizon']==10
    assert db.get('due',digest([enrollment['enrollment_id'],10]))==original

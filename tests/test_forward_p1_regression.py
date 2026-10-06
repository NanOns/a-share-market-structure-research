import copy
import pytest
from tests.forward_p1_vectors import row, BASIS, runtime_fixture, MemoryStore, FixtureAuthority
from workbench_analysis import v4_15_forward_p1 as candidate
from workbench_analysis import v4_15_settlement_successor as previous
from workbench_analysis import v4_15_settlement as historical

@pytest.mark.parametrize('patch', [dict(verified_identity=False),dict(verified_adjustment=False),
    dict(T0_basis_verified=False),dict(close=None),dict(adjustment_identity=''),
    dict(evaluation_basis_date='WRONG'),dict(transform_coefficients={'alpha':True,'beta':0}),
    dict(T0_transform_coefficients={'alpha':1,'beta':float('nan')})])
def test_endpoint_strictness(patch):
    endpoint=dict(row(),**patch)
    assert candidate.price_path(10,[{},endpoint],BASIS)['R_N'] is None

@pytest.mark.parametrize('patch', [dict(verified_identity=False),dict(verified_adjustment=False),
    dict(adjustment_identity='OTHER'),dict(transform_coefficients=None),dict(close=float('nan')),
    dict(evaluation_basis_date='WRONG')])
def test_interior_only_degrades_path(patch):
    result=candidate.price_path(10,[dict(row(),**patch),row()],BASIS)
    assert abs(result['R_N']-.1)<1e-12 and result['MFE_N'] is None

@pytest.mark.parametrize('kind',['negative_price','invalid_ohlc','terminal_zero'])
def test_ia04_remains_open(kind):
    endpoint=row()
    if kind=='negative_price':endpoint.update(close=-1,high=0,low=-2)
    if kind=='invalid_ohlc':endpoint.update(close=11,high=9,low=12)
    if kind=='terminal_zero':endpoint.update(status='DELISTED',terminal_verified=True,terminal_evidence='fixture',terminal_value=0)
    old=previous.price_path(10,[endpoint],BASIS)
    new=candidate.price_path(10,[endpoint],BASIS)
    assert old['R_N']==new['R_N'] and old['outcome_status']==new['outcome_status']

def test_ia03_same_source_pending_due_still_open():
    runtime,store,freeze,source,*_=runtime_fixture()
    first=runtime.settle(freeze,source,'2030-01-01',(3,))[0]
    second=runtime.settle(freeze,source,BASIS,(3,))[0]
    assert first==second and store.read(second)['outcome_status']=='PENDING'

def test_fep_new_exact_revision_requires_owner_acceptance():
    from workbench_analysis.fep_e1.labels import project_with_owner_time, project
    from workbench_analysis.fep_e1.contracts import digest
    from scripts.full_chain_repair_io import ROOT
    runtime,store,freeze,source,*_=runtime_fixture()
    source.rows['A']['2030-01-02']={}
    outcome=store.read(runtime.settle(freeze,source,BASIS,(3,))[0])
    result=project_with_owner_time(ROOT,outcome,dict(family='ABS_RETURN_N',horizon=3),authority_head={'PROVED_HORIZONS':[]},cutoff='2030-01-06T00:00:00Z')
    assert result['training_allowed'] is False and result['reason']=='NO_EXACT_OWNER_TIME_RECEIPTS'
    times={t:'2030-01-06T00:00:00Z' for t in ('source_fact_available_at','label_training_mature_at','label_revision_available_at')}
    times['upstream_digest']=digest(outcome)
    endpoint=project(outcome,dict(family='ABS_RETURN_N',horizon=3),authority_head={'PROVED_HORIZONS':[]},time_authority=times)
    path=project(outcome,dict(family='MFE_N',horizon=3),authority_head={'PROVED_HORIZONS':[]},time_authority=times)
    assert endpoint['training_allowed'] and not path['training_allowed']

def test_worker_keeps_queue_fencing_and_contract_is_additive(shadow):
    from tests.test_full_chain_repair import future
    from scripts.v4_16_forward_p1_worker import DurableSettlementWorker
    from scripts.v4_16_shadow_runtime import digest
    db,_=shadow;authority,source=future(db)
    worker=DurableSettlementWorker(db,'FORWARD_P1_FIXTURE')
    due=next(d for d in db.rows('due') if d['horizon']==1)
    due_id=digest([due['enrollment_id'],1]);sha=source.binding['sha256']
    key=worker.enqueue(due_id,sha,'2026-10-09')
    result=worker.deliver(key,sha,authority,lambda:source,'2026-10-09')
    assert result['outcome_contract_id']==candidate.CONTRACT_ID
    assert worker.row(key,sha)['status']=='ACKED'
    assert worker.deliver(key,sha,authority,lambda:source,'2026-10-09')==result

from tests.test_full_chain_repair import shadow

@pytest.mark.parametrize('case',['member_source','member_adjustment','member_basis','basket_tamper','basket_source_tamper','wrong_date'])
def test_sector_coordinate_guards(case):
    from tests.forward_p1_vectors import sector_vector
    inputs=sector_vector(1)['input'];basket=inputs['basket'];points=inputs['points']
    endpoint=points[-1]['members']['A']
    if case=='member_source':endpoint['source_identity']='OTHER'
    if case=='member_adjustment':endpoint['adjustment_identity']='OTHER'
    if case=='member_basis':endpoint['evaluation_basis_date']='WRONG'
    if case=='basket_tamper':basket['members'][0]['weight']=1
    if case=='basket_source_tamper':basket['sector_basket_source_digest']='WRONG'
    if case=='wrong_date':points[-1]['trade_date']='2030-01-05'
    result=candidate.sector_path(basket,points,BASIS,{'sha256':'fixture'})
    assert result['R_N'] is None

def test_worker_candidate_cannot_activate_real_delivery():
    from types import SimpleNamespace
    from scripts.v4_16_forward_p1_worker import DurableSettlementWorker
    worker=DurableSettlementWorker(SimpleNamespace(controller=SimpleNamespace(simulation=False)),'fixture')
    with pytest.raises(ValueError,match='INDEPENDENT_ACCEPTANCE_REQUIRED'):
        worker.deliver('key','sha',None,lambda:pytest.fail('source factory was called'),BASIS)

def test_e5_missing_exact_identity_stays_conflict():
    from workbench_analysis.fep_e5.canonical_identity import readback_population,CONFLICT
    class ReadOnlyFixture:
        def execute(self,sql,params):
            assert sql.startswith('select count(*)')
            return self
        def fetchone(self):return (0,)
    result=readback_population(ReadOnlyFixture(),[dict(observation_id='FIXTURE',entity_id='A',trade_date=BASIS,original_e2_row_digest='fixture')],{})
    assert result['status']==CONFLICT and result['population'][0]['canonical_identity'] is None
    assert result['no_database_writes'] and not result['canonical_integration_accepted']

def test_confirmed_suspension_omits_coordinates_without_fabrication():
    suspension=dict(status='CONFIRMED_SUSPENSION',verified_identity=True,verified_adjustment=True,evaluation_basis_date=BASIS)
    old=previous.price_path(10,[suspension,row()],BASIS)
    new=candidate.price_path(10,[suspension,row()],BASIS)
    assert old['MFE_N']==new['MFE_N'] and new['actual_count']==1
    assert new['path_quality']=='CONFIRMED_INTERIOR_SUSPENSION_OMITTED'

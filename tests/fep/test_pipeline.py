import copy
import inspect
import json
from datetime import timedelta
import pytest
from workbench_analysis.fep_e1 import labels, snapshots, observation, datasets
from workbench_analysis.fep_e1.contracts import digest, atomic_json
from workbench_analysis.v4_15_persistence import Store
from .conftest import ROOT,T,SCOPE,contract,rejected


def revisions():
    return [dict(revision=i,source_fact_available_at=(T+timedelta(days=2)).isoformat(),
        label_training_mature_at=(T+timedelta(days=5)).isoformat(),label_revision_available_at=(T+timedelta(days=a)).isoformat(),
        target_digest=digest(i),training_allowed=True,quality='OBSERVED') for i,a in [(1,10),(2,20)]]


def test_asof_revision_and_three_times():
    r=revisions()
    assert datasets.select(r,(T+timedelta(days=10)).isoformat())['selected_label_revision']==1
    assert datasets.select(r,(T+timedelta(days=20)).isoformat())['selected_label_revision']==2
    assert datasets.select(r,(T+timedelta(days=3)).isoformat())['eligibility']=='MISSING_LABEL'
    r[0]['label_revision_available_at']=(T+timedelta(days=2)).isoformat()
    assert datasets.select(r,(T+timedelta(days=3)).isoformat())['eligibility']=='PENDING'


def test_complete_denominator_pending_and_digest():
    o=[dict(observation_id='a',scope_id=SCOPE,entity_id='A',trade_date='2026-09-01',episode_key='e'),
       dict(observation_id='b',scope_id=SCOPE,entity_id='B',trade_date='2026-09-02',episode_key='e')]
    targets=[dict(target_id='t',scope_id=SCOPE,horizon=5)]
    f=[dict(fold_id='A',partition_name='FIT',fold_dataset_cutoff=(T+timedelta(days=10)).isoformat(),
         phase_started_at=(T+timedelta(days=10)).isoformat(),observation_ids=['a','b'])]
    kw=dict(observations=o,targets=targets,folds=f,labels={('a','t'):revisions()},snapshots={'a':{'snapshot_id':'s'}},cutoff=(T+timedelta(days=40)).isoformat())
    result=datasets.assemble(**kw)
    assert len(result['denominator'])==2 and len(result['rows'])==1 and len(result['selections'])==2
    assert result['selections'][1]['eligibility']=='MISSING_LABEL'
    assert datasets.assemble(**kw)==result
    reversed_args=dict(kw,observations=list(reversed(o)))
    assert datasets.assemble(**reversed_args)==result
    kw['folds']=copy.deepcopy(f);kw['folds'][0]['fold_dataset_cutoff']=(T+timedelta(days=9)).isoformat()
    assert datasets.assemble(**kw)['digest']!=result['digest']


def test_observation_revision_is_not_event():
    scope=dict(scope_id=SCOPE,status='ENGINEERING_ENABLED')
    args=dict(entity_id='A',trade_date='2026-09-30',signal_key='signal',episode_key='e',slot_deadline=T.isoformat(),core_signal_contract_id='core')
    a=observation.build(scope,**args);b=observation.build(scope,**args)
    assert a['observation_id']==b['observation_id']
    with pytest.raises(ValueError,match='NOT_ENABLED'):
        observation.build(dict(scope_id='OTHER',status='NOT_ENABLED'),**args)


def test_source_exact_readback_and_no_price_recomputation(tmp_path):
    store=Store(tmp_path,'reports/v4_15_runtime_r20/fep-fixture')
    row=dict(outcome_revision_id='row',evaluation_revision=1,evaluation_source_digest=digest('source'),
             horizon=5,R_N=.2,outcome_status='OBSERVED',evidence_class='ENGINEERING_VECTOR')
    binding=store.append('outcomes','row',row)
    assert labels.read_source(store,binding,'row',1,digest('source'))==row
    with pytest.raises(ValueError,match='REVISION_DIGEST'):
        labels.read_source(store,binding,'row',2,digest('source'))
    target=dict(family='ABS_RETURN_N',horizon=5)
    assert labels.project(row,target,authority_head={'PROVED_HORIZONS':[]})['training_allowed'] is False
    authority=dict(upstream_digest=digest(row),**{k:(T+timedelta(days=n)).isoformat() for k,n in zip(labels.TIMES,[2,5,6])})
    result=labels.project(row,target,authority_head={'PROVED_HORIZONS':[]},time_authority=authority)
    assert result['numeric_value']==.2 and result['evidence_class']=='ENGINEERING_FIXTURE'
    assert 'price_path(' not in inspect.getsource(labels) and 'benchmark(' not in inspect.getsource(labels)


def test_E1_36_real_no_maturity():
    head=json.loads((ROOT/'data/v4/V4_15_ACCEPTED_HEAD.json').read_bytes())
    assert head['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE' and head['PROVED_HORIZONS']==[]
    row=dict(outcome_revision_id='r',evaluation_revision=1,evaluation_source_digest=digest('s'),horizon=5,R_N=.2,
             outcome_status='OBSERVED',evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED')
    authority=dict(upstream_digest=digest(row),**{k:T.isoformat() for k in labels.TIMES})
    result=labels.project(row,dict(family='ABS_RETURN_N',horizon=5),authority_head=head,time_authority=authority)
    assert result==dict(training_allowed=False,quality='PENDING',reason='NO_REAL_MATURITY_EVIDENCE')
    forged=dict(head,PROVED_HORIZONS=[5])
    assert labels.project(row,dict(family='ABS_RETURN_N',horizon=5),authority_head=forged,time_authority=authority)['reason']=='FEP_E1_REAL_ADAPTER_NOT_ENABLED'


def test_snapshot_exact_and_digest_nonsemantic_time(tmp_path):
    payload={'features':{'x':dict(value=1,quality='KNOWN')}}
    atomic_json(tmp_path/'source.json',payload)
    import hashlib
    b=(tmp_path/'source.json').read_bytes();binding=dict(path='source.json',bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),system_available_at=(T-timedelta(days=1)).isoformat())
    dependencies={k:binding for k in snapshots.DEPENDENCIES};dependencies['enrichment_revision']='NONE'
    obs=dict(observation_id='a',scope_id=SCOPE,slot_deadline=T.isoformat())
    registry=dict(fields=[dict(field_name='x',status='IMPLEMENTED_EXACT_MAPPING',allowed_scopes=[SCOPE],quality_allowlist=['KNOWN'],required=True,
                              dependency_key='publication',field_path=['features','x','value'],quality_path=['features','x','quality'],data_type='float64')])
    kwargs=dict(root=tmp_path,observation=obs,revision=1,dependencies=dependencies,values={'x':{'value':1,'quality':'KNOWN'}},registry=registry,
                feature_cutoff=T.isoformat(),created_at=T.isoformat(),evidence_origin='RECONSTRUCTED_ASOF',execution_mode='REPLAY')
    first=snapshots.build(**kwargs);kwargs['created_at']=(T+timedelta(days=1)).isoformat()
    assert snapshots.build(**kwargs)['feature_digest']==first['feature_digest']
    bad=dict(kwargs,values={'x':{'value':9,'quality':'KNOWN'}})
    with pytest.raises(ValueError,match='CONSUMED_VALUE_MISMATCH'):
        snapshots.build(**bad)
    kwargs['evidence_origin']='PIT_OBSERVED'
    with pytest.raises(ValueError,match='PIT_CAPTURE_NOT_ENABLED'):
        snapshots.build(**kwargs)
    kwargs['evidence_origin']='RECONSTRUCTED_ASOF';kwargs['dependencies']=copy.deepcopy(dependencies)
    kwargs['dependencies']['universe']['system_available_at']=(T+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError,match='NOT_VISIBLE'):
        snapshots.build(**kwargs)


def protected():
    from hashlib import sha256
    entry=json.loads((ROOT/'reports/fep_e1/ENTRY_BASELINE.json').read_bytes())
    for binding in entry['protected']:
        b=(ROOT/binding['path']).read_bytes()
        assert len(b)==binding['bytes'] and sha256(b).hexdigest()==binding['sha256']
    return entry['protected']


def test_E1_39_failure_priority_core_isolation(pg):
    before=protected()
    core=pg.execute("select tablename from pg_tables where schemaname='v4' order by tablename").fetchall()
    rejected(pg,lambda:pg.execute('create table fep.rollback_probe (id nonexistent_type)'))
    assert pg.execute("select to_regclass('fep.rollback_probe')").fetchone()[0] is None
    assert pg.execute("select tablename from pg_tables where schemaname='v4' order by tablename").fetchall()==core
    for fault in ['snapshot','label_adapter','dataset']:
        with pytest.raises(ValueError):
            if fault=='snapshot': snapshots.build(ROOT,{},1,{}, {},{},feature_cutoff='',created_at='',evidence_origin='',execution_mode='')
            if fault=='label_adapter': labels.project({'horizon':1},{'horizon':5,'family':'ABS_RETURN_N'},authority_head={})
            if fault=='dataset': datasets.assemble([{'observation_id':'x'},{'observation_id':'x'}],[],[],{}, {},T.isoformat())
        assert protected()==before


def test_E1_40_accepted_bytes_no_new_heads(pg):
    protected()
    assert not (ROOT/'data/v4/V4_16_ACCEPTED_HEAD.json').exists()
    assert not (ROOT/'data/v4/FEP_E1_ACCEPTED_HEAD.json').exists()
    assert pg.execute('select count(*) from fep.permission_keys').fetchone()[0]==0
    for table in ['training_runs','models','model_sets','model_set_members','prediction_runs','predictions','reports','priority_projection','priority_projection_grants']:
        assert pg.execute('select count(*) from fep.'+table).fetchone()[0]==0


def test_persisted_full_denominator_and_atomic_failure(base):
    from workbench_analysis.fep_e1.repository import persist_dataset
    from .conftest import observation,label
    observation(base,'b','SEC-B','2026-09-02','other')
    s=label(base,available=10)
    rev=dict(revision=1,source_fact_available_at=s['source_fact_available_at'],
        label_training_mature_at=s['label_training_mature_at'],label_revision_available_at=s['label_revision_available_at'],
        target_digest=s['target_digest'],training_allowed=True)
    o=[dict(observation_id='o',scope_id=SCOPE,entity_id='SEC-A',trade_date='2026-09-01',episode_key='e'),
       dict(observation_id='b',scope_id=SCOPE,entity_id='SEC-B',trade_date='2026-09-02',episode_key='e')]
    f=[dict(fold_id='A',partition_name='FIT',fold_dataset_cutoff=(T+timedelta(days=10)).isoformat(),phase_started_at=(T+timedelta(days=10)).isoformat(),observation_ids=['o','b'])]
    assembled=datasets.assemble(o,[dict(target_id='ABS:T5',scope_id=SCOPE,horizon=5)],f,{('o','ABS:T5'):[rev]},
        {'o':dict(snapshot_id='snap')},(T+timedelta(days=40)).isoformat())
    result=persist_dataset(base,'persisted',SCOPE,'FEATURE','POLICY',T+timedelta(days=40),T+timedelta(days=40),assembled)
    assert result['denominator']==2 and result['rows']==1
    bad=copy.deepcopy(assembled);bad['rows'][0]['snapshot_id']='nonexistent'
    bad['digest']=digest({k:bad[k] for k in ['denominator','folds','selections','rows']})
    rejected(base,lambda:persist_dataset(base,'failed',SCOPE,'FEATURE','POLICY',T+timedelta(days=40),T+timedelta(days=40),bad))
    assert base.execute("select count(*) from fep.datasets where dataset_id='failed'").fetchone()[0]==0
    assert base.execute("select count(*) from fep.dataset_eligibility_ledger where dataset_id='failed'").fetchone()[0]==0

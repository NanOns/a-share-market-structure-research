import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from workbench_analysis.source_capture_candidate_v1 import capture
from workbench_analysis.full_state_signal_candidate_v1 import produce, freeze
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.producer_bootstrap_v1 import optional_step
from sector.operational_candidate_v1 import create_episode, followup


@pytest.fixture
def capture_args(tmp_path):
    day=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    source=tmp_path/'original';source.write_bytes(b'original bytes')
    binding=publish(tmp_path,'inputs/config.json',dict(version='1'))
    now=datetime.now(timezone.utc).isoformat()
    return tmp_path,dict(trade_date=day,sessions=[day],calendar_binding=binding,
        sources=[dict(name='members',path=str(source),trade_date=day,requested_at=now,received_at=now)],
        security_ids=['S1'],sector_ids=['B1'],model_binding=binding,config_binding=binding)


def test_capture_idempotent_and_changed_bytes_append(capture_args):
    root,args=capture_args
    first=capture(root,**args);assert capture(root,**args)==first
    Path(args['sources'][0]['path']).write_bytes(b'changed')
    second=capture(root,**args);assert second!=first
    assert json.loads((root/first['path']).read_bytes())['production'] is False


@pytest.mark.parametrize('change,error',[
    ('past','REAL_CURRENT_SESSION_REQUIRED'),('future','SOURCE_TIMESTAMP_ORDER_REQUIRED'),
    ('naive','AWARE_TIMESTAMP_REQUIRED'),('sha','SOURCE_SHA_MISMATCH'),
    ('scope','COMPLETE_SCOPE_REQUIRED'),('namespace','ISOLATED_NAMESPACE_REQUIRED'),
    ('duplicate','DUPLICATE_SOURCE_NAME'),('availability','SOURCE_AVAILABILITY_ORDER_REQUIRED')])
def test_capture_rejects(capture_args,change,error):
    root,args=capture_args
    if change=='past':args.update(trade_date='2026-01-01',sessions=['2026-01-01'])
    if change=='future':args['sources'][0]['received_at']='2999-01-01T00:00:00+00:00'
    if change=='naive':args['sources'][0]['requested_at']='2026-01-01T00:00:00'
    if change=='sha':args['sources'][0]['sha256']='0'*64
    if change=='scope':args['security_ids']=['S1','S1']
    if change=='namespace':args['namespace']='data/v4/formal'
    if change=='duplicate':args['sources']*=2
    if change=='availability':args['sources'][0]['first_available']='2999-01-01T00:00:00+00:00'
    with pytest.raises(ValueError,match=error):capture(root,**args)


def test_historical_replay_cannot_be_first_capture(capture_args):
    root,args=capture_args
    args.update(trade_date='2026-10-09',sessions=['2026-10-09'],research_replay=True)
    binding=capture(root,**args);document=json.loads((root/binding['path']).read_bytes())
    assert document['evidence_class']=='RECONSTRUCTED_RESEARCH_ONLY'
    assert document['gaps'] and not document['PIT_ELIGIBLE']


def test_local_read_retry_keeps_original_clock(capture_args):
    root,args=capture_args;args['sources'][0]['timestamp_basis']='LOCAL_READ'
    first=capture(root,**args);assert capture(root,**args)==first


def state_document(states=('TRUE','FALSE','UNKNOWN')):
    rows=[dict(security_id='S1',trade_date='2026-10-09',confirmation=dict(scenario_evidence=[
        dict(scenario=str(i),status=s) for i,s in enumerate(states)]))]
    return produce(rows,universe=['S1','S2'],trade_date='2026-10-09',source_binding={},
        membership_binding={},model_binding={},config_binding={},captured_at='2026-10-10T00:00:00+00:00')


def test_full_universe_reconciliation_and_research_identity():
    doc=state_document();assert doc['signal_count']==4 and doc['missing_state_count']==1
    assert doc['research_eligible_count']==1
    assert all(not r['eligible_at_T0'] and r['ineligibility_reason'] for r in doc['signals'])
    assert doc['observed_count'] is None


def test_signal_freeze_immutable(tmp_path):
    doc=state_document();first=freeze(tmp_path,doc,publication_id='P1',revision='r1')
    assert freeze(tmp_path,doc,publication_id='P1',revision='r1')==first
    doc['signals'][0]['state']='FALSE'
    with pytest.raises(ValueError,match='OVERWRITE'):freeze(tmp_path,doc,publication_id='P1',revision='r1')
    assert freeze(tmp_path,doc,publication_id='P1',revision='r2')!=first


def test_signal_bad_state():
    with pytest.raises(ValueError,match='THREE_VALUE'):state_document(('YES',))


def test_optional_failure_preserves_main_flow():
    def fail():raise ValueError('BROKEN_INPUT')
    result=optional_step(fail);assert not result['main_flow_blocked'] and 'BROKEN_INPUT' in result['reason']


def test_episode_genesis_idempotence_and_pending(capture_args):
    root,args=capture_args;source=capture(root,**args)
    contract=publish(root,'inputs/invalidation.json',dict(version='1',conditions=['BOUND_PRICE']))
    priority=publish(root,'inputs/priority.json',dict(scenario_priority=['LAUNCH_CONFIRM']))
    price_binding=publish(root,'inputs/price.json',dict(T0=args['trade_date'],sector_id='B1',price=1,source_capture=source))
    kwargs=dict(source_capture=source,sector_id='B1',trade_date=args['trade_date'],members=['S1'],
        invalidation_contract=contract,scenario='LAUNCH_CONFIRM',scenario_priority_binding=priority,price=1,sessions=args['sessions'],price_binding=price_binding)
    first=create_episode(root,**kwargs);assert create_episode(root,**kwargs)==first
    episode=json.loads((root/first['path']).read_bytes())
    assert all(r['status']=='PENDING' for r in followup(episode,trade_date=args['trade_date'],sessions=args['sessions']).values())
    kwargs['price']=2
    with pytest.raises(ValueError,match='PRICE_SOURCE'):create_episode(root,**kwargs)


def test_episode_due_unknown_and_source_identity():
    sessions=['2026-10-09','2026-10-12','2026-10-13','2026-10-14','2026-10-15','2026-10-16']
    ep=dict(T0=sessions[0],episode_id='E1')
    assert followup(ep,trade_date=sessions[1],sessions=sessions)['1']['status']=='UNKNOWN'
    assert followup(ep,trade_date=sessions[1],sessions=sessions,settlement={'1':dict(trade_date=sessions[1],episode_id='OTHER',source_binding={})})['1']['status']=='UNKNOWN'


def test_episode_rejects_historical_source(capture_args):
    root,args=capture_args;args['research_replay']=True
    source=capture(root,**args)
    with pytest.raises(ValueError,match='REAL_EPISODE'):
        create_episode(root,source_capture=source,sector_id='B1',trade_date=args['trade_date'],members=['S1'],
            invalidation_contract={},scenario=None,scenario_priority_binding={},price=1,sessions=args['sessions'],price_binding={})


def test_exact_legacy_rank_producer_and_future_rejection(tmp_path):
    from sector.operational_candidate_v1 import produce_rank_window_sources
    from workbench_analysis.v4_14_replay_io import ref
    root=Path(__file__).resolve().parents[1]
    # Algorithm identity lives in the project; synthetic inputs remain on G:.
    sessions=['2026-10-09','2026-10-12','2026-10-13','2026-10-14']
    technical=[];members=[]
    for day in sessions:
        for i in range(2):
            technical.append(dict(security_id=str(i),trade_date=day,rs5=i,rs20=i,ret1=.01))
            members.append(dict(security_id=str(i),trade_date=day,sector_id=str(i),sector_type='THEME'))
    # Source receipts and AST/config are copied only as tiny fixture inputs.
    for path in ('config/v4_08_b2_machine_ast_r5.json','config/research_attention_v3.yaml'):
        dest=tmp_path/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/path).read_bytes())
    tb=publish(tmp_path,'inputs/tech.json',dict(rows=technical))
    mb=publish(tmp_path,'inputs/members.json',dict(rows=members))
    cb=publish(tmp_path,'inputs/calendar.json',dict(session_dates=sessions))
    ab=ref(tmp_path,'config/v4_08_b2_machine_ast_r5.json')
    result=produce_rank_window_sources(tmp_path,technical_binding=tb,memberships_binding=mb,
        calendar_binding=cb,trade_date=sessions[-1],ast_binding=ab)
    assert json.loads((tmp_path/result['0']['q20']['path']).read_bytes())['value']==.5
    assert json.loads((tmp_path/result['1']['q20']['path']).read_bytes())['value']==1
    assert json.loads((tmp_path/result['1']['dq5_3']['path']).read_bytes())['value']==0
    technical[0]['trade_date']='2999-01-01'
    bad=publish(tmp_path,'inputs/future.json',dict(rows=technical))
    with pytest.raises(ValueError,match='FUTURE'):
        produce_rank_window_sources(tmp_path,technical_binding=bad,memberships_binding=mb,
            calendar_binding=cb,trade_date=sessions[-1],ast_binding=ab)


def test_followup_requires_checked_original_settlement(tmp_path):
    sessions=['2026-10-09','2026-10-12'];ep=dict(T0=sessions[0],episode_id='E1')
    original=publish(tmp_path,'inputs/original_settlement.json',dict(trade_date=sessions[1],value=.01))
    sb=publish(tmp_path,'inputs/settlement.json',dict(trade_date=sessions[1],episode_id='E1',source_binding=original,value=.01))
    assert followup(ep,trade_date=sessions[1],sessions=sessions,root=tmp_path,settlement={'1':sb})['1']['status']=='COMPLETE'
    sb['sha256']='0'*64
    with pytest.raises(ValueError):followup(ep,trade_date=sessions[1],sessions=sessions,root=tmp_path,settlement={'1':sb})


def test_frozen_invalidation_ast_and_future_fact(tmp_path):
    from sector.operational_candidate_v1 import evaluate_invalidation
    cb=publish(tmp_path,'inputs/conditions.json',dict(rule_id='invalid',rules={'invalid':dict(
        operator='LT',field_id='price',constant=1,producer='PRICE',time_role='TARGET_CUTOFF',
        quality_requirement=['ACCEPTED'],unknown_behavior='UNKNOWN')}))
    eb=publish(tmp_path,'inputs/episode.json',dict(episode_id='E1',T0='2026-10-09',invalidation_contract=cb))
    facts=dict(price=dict(value=.5,quality='ACCEPTED',producer='PRICE',time_role='TARGET_CUTOFF',max_source_date='2026-10-09'))
    assert evaluate_invalidation(tmp_path,eb,facts,trade_date='2026-10-09',sessions=['2026-10-09'])['value']=='TRUE'
    facts['price']['value']=None;facts['price']['quality']='UNKNOWN'
    assert evaluate_invalidation(tmp_path,eb,facts,trade_date='2026-10-09',sessions=['2026-10-09'])['value']=='UNKNOWN'
    facts['price']['max_source_date']='2026-10-12'
    with pytest.raises(ValueError,match='FUTURE_INVALIDATION'):
        evaluate_invalidation(tmp_path,eb,facts,trade_date='2026-10-09',sessions=['2026-10-09'])

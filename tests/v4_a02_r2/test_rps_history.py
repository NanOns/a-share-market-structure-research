from copy import deepcopy
from pathlib import Path
import json
import pytest
from v4.rps_pit_history_a02_v1 import publish,scores,delta,digest,immutable_json,binding,read_bound
from v4.rps_history_reader_a02_v1 import read_triplet

ROOT=Path(__file__).resolve().parents[2]

def payload(day='2026-09-30'):
    members=['a','b','c','d']
    return dict(trade_date=day,data_authority=dict(accepted_through='2026-09-30'),universe_identity=dict(producer_sha='same',members_digest=digest(members)),calendar_identity='calendar',cutoff_timestamp='2026-10-01T13:34:37+00:00',algorithm_identity='frozen',source_revision='source',sessions=['2026-09-22','2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30'],universe=members,returns={'5':dict(a=.1,b=.1,c=.2,d=None),'20':dict(a=.1,b=.1,c=.2,d=None)},endpoint_evidence={sid:{str(h):dict(unknown_reason='MISSING_OR_SUSPENDED_ENDPOINT' if sid=='d' else None) for h in (5,20)} for sid in members},source_bindings={'frozen':'source'})

def test_frozen_midrank_ties_and_single_evaluable_unknown():
    assert scores({'a':1,'b':1,'c':2,'d':None},['a','b','c','d'])==dict(a=25,b=25,c=100,d=None)
    assert scores({'a':1,'b':None},['a','b'])==dict(a=None,b=None)

def test_strict_compatible_producer_reports_rank_warmup_and_rejects_boolean():
    from v4.rps_history_producer_a02_r2 import publish as strict_publish
    inp=payload()
    for horizon in ('5','20'): inp['returns'][horizon].update(a=.1,b=None,c=None,d=None)
    publication=strict_publish(inp)
    assert publication['rows'][0]['rps5']['unknown_reason']=='INSUFFICIENT_EVALUABLE_UNIVERSE'
    inp['returns']['5']['a']=True
    with pytest.raises(ValueError,match='BOOLEAN'): strict_publish(inp)

def test_append_only_and_tampered_byte_binding(tmp_path):
    path=tmp_path/'pub.json';immutable_json(path,{'a':1});ref=binding(tmp_path,path)
    with pytest.raises(ValueError,match='APPEND_ONLY'): immutable_json(path,{'a':2})
    path.write_text('{"a":2}',encoding='utf8')
    with pytest.raises(ValueError,match='BINDING'): read_bound(tmp_path,ref)

def test_calendar_schema_and_cutoff_fail_closed():
    x=payload();x['sessions'].append(x['sessions'][-1])
    with pytest.raises(ValueError,match='CALENDAR'): publish(x)
    x=payload();x['cutoff_timestamp']='2026-09-29T12:00:00Z'
    with pytest.raises(ValueError,match='CUTOFF'): publish(x)
    x=payload();x['data_authority']['accepted_through']='2026-09-29'
    with pytest.raises(ValueError,match='BEYOND_ACCEPTED'): publish(x)

def test_exact_prior_session_and_warmup():
    now=publish(payload());prior=publish(payload('2026-09-29'));sessions=payload()['sessions']
    out=delta(now,prior,1,sessions)
    assert out[0]['fields']['rps5_delta1']['value']==0
    assert out[-1]['fields']['rps5_delta1']['unknown_reason']=='RPS_ENDPOINT_UNKNOWN'
    assert delta(now,None,3,sessions)[0]['fields']['rps5_delta3']['unknown_reason']=='T_MINUS_3_PUBLICATION_MISSING'
    with pytest.raises(ValueError,match='PRIOR_SESSION'): delta(now,prior,3,sessions)

@pytest.mark.parametrize('field,reason',[('calendar_identity','CALENDAR_REVISION'),('algorithm_identity','ALGORITHM_REVISION'),('universe_identity','UNIVERSE_AUTHORITY_REVISION')])
def test_revision_vectors(field,reason):
    now=publish(payload());prior=publish(payload('2026-09-29'));prior[field]='another-revision'
    assert delta(now,prior,1,payload()['sessions'])[0]['fields']['rps5_delta1']['unknown_reason']==reason

def test_date_effective_universe_new_member_remains_unknown():
    current=publish(payload());prior_payload=payload('2026-09-29');prior_payload['universe']=['a','b','c'];prior_payload['universe_identity']['members_digest']=digest(prior_payload['universe'])
    prior=publish(prior_payload)
    assert delta(current,prior,1,payload()['sessions'])[-1]['fields']['rps5_delta1']['unknown_reason']=='PRIOR_UNIVERSE_MEMBER_MISSING'

def test_reader_consumes_exact_artifacts_and_denies_formal_self_acceptance(tmp_path,monkeypatch):
    now=publish(payload());prior=publish(payload('2026-09-29'))
    current_path=tmp_path/'current.json';prior_path=tmp_path/'prior.json';immutable_json(current_path,now);immutable_json(prior_path,prior)
    ref=binding(tmp_path,current_path);p=binding(tmp_path,prior_path)
    # A reader cannot call the producer or a raw data recalculation.
    import v4.rps_pit_history_a02_v1 as producer
    monkeypatch.setattr(producer,'scores',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('RUNTIME_RECALCULATION')))
    assert read_triplet(tmp_path,ref,{1:p},payload()['sessions'])['T-1']['trade_date']=='2026-09-29'
    with pytest.raises(ValueError,match='EXTERNAL_ACCEPTANCE'): read_triplet(tmp_path,ref,{1:p},payload()['sessions'],formal_consumer=True)
    with pytest.raises(ValueError,match='PRIOR_SESSION'): read_triplet(tmp_path,ref,{3:p},payload()['sessions'])

def test_real_six_publication_source_rank_and_delta_oracle():
    from scripts.verify_a02_a05_candidate_readback_r1 import verify_a02
    proof=verify_a02()
    assert proof['mismatches']==0 and proof['publications']==6 and proof['real_source_rows_reconstructed']==135413

def test_real_downstream_diff_is_amendment_only_and_parameters_frozen():
    proof=json.loads((ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json').read_text(encoding='utf8'))
    assert proof['downstream_replay']['seed_rows']==5222 and proof['downstream_replay']['stock_rows']==5222
    assert proof['downstream_replay']['old_seed_counts']=={'FALSE':2443,'UNKNOWN':2779}
    assert proof['downstream_replay']['new_seed_counts']['TRUE']>0
    assert proof['formal_consumer_enabled'] is False and proof['accepted_head_changed'] is False
    assert proof['AS_RECORDED'] is False and proof['historical_first_availability_proven'] is False
    assert proof['final_revision']=='R3'
    assert proof['downstream_replay']['new_seed_context']['publication_id']!=proof['downstream_replay']['source_context']['publication_id']

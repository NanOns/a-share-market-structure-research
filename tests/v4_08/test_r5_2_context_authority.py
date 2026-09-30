"""TEST_ONLY immutable accepted publications; no static V4-02 head writes."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from sector.accepted_input_r5_1 import load_accepted_current
from sector.accepted_context_r5_2 import resolve_daily_context, CONTRACT_ID
from sector.legacy_b2_r5 import evaluate_b2, build_b2_inputs
from sector.semantic_input_r5_1 import bind_semantic
from sector.native_r5 import build_native
from v4.canonical_governance_hash import canonical_json_file_sha256, canonical_json_sha256

ROOT=Path(__file__).resolve().parents[2]


def write(root,path,payload):
    path=root/path;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
    return dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(payload).hexdigest())


def publication(root,date,amount=10,snapshot=None,inject_boolean=False):
    timestamp=date+'T08:00:00+08:00';prefix='test_only_publications/'+date+'/'
    snapshot=snapshot or 'sha256-'+hashlib.sha256(date.encode()).hexdigest()
    ids=[f'TEST_ONLY_MEMBER_{i}' for i in range(8)]
    raw=[];price=[];factors=[];profiles=[]
    for sid in ids:
        raw.append(dict(canonical_security_id=sid,trade_date=int(date.replace('-','')),amount=amount,trading_status='ACTUAL_TRADED',adjustment_source_revision='TEST_ONLY_REVISION_'+date))
        price.append(dict(security_id=sid,target_trade_date=int(date.replace('-','')),max_source_trade_date=int(date.replace('-','')),coordinate_basis='T0_CURRENT_COORDINATE',adjustment_snapshot_id=snapshot,adjustment_snapshot_digest=hashlib.sha256(date.encode()).hexdigest(),adjusted_quality='ADJUSTED_READY',qfq_ohlc=['11']*4,formal_publication_at=timestamp,system_available_at=timestamp,adjustment_source_available_at=timestamp,adjustment_system_available_at=timestamp))
        factors.append(dict(security_id=sid,trade_date=date,fields={k:dict(value=v,quality_state='OBSERVED',source_asof=date) for k,v in dict(ret1=.1,ret5=.1,ret20=.1,ret60=.1,amount_ratio20=99,rps20=20).items()}))
        if inject_boolean:
            factors[-1]['legacy_valid_member']=dict(value=True,quality='ACCEPTED',producer_contract='sector-factor-contract-v1.1-correctness',max_source_date=date)
        profiles.append(dict(security_id=sid,trade_date=date,states={'trend_state':{'evidence':dict(close=11,ma20=10)}}))
    def save(name,rows):
        payload=b''.join(json.dumps(r,sort_keys=True,separators=(',',':')).encode()+b'\n' for r in rows)
        return write(root,prefix+name+'.jsonl.gz',gzip.compress(payload,mtime=0)),hashlib.sha256(payload).hexdigest()
    raw_binding,raw_logical=save('raw',raw);price_binding,price_logical=save('price',price)
    factors_binding,_=save('factors',factors);profiles_binding,_=save('profiles',profiles)
    immutable=write(root,prefix+'acceptance.json',json.dumps(dict(external_acceptance='EXTERNALLY_ACCEPTED',accepted_trade_date=date)).encode())
    context=dict(contract_id=CONTRACT_ID,context_id='TEST_ONLY_CONTEXT_'+date,accepted_trade_date=date,scope='ENGINEERING_REPLAY_ONLY',daily_production_authority=False,
        raw_daily=dict(**raw_binding,source_digest=raw_binding['sha256'],logical_digest=raw_logical,logical_digest_algorithm='JSONL_BYTES_SHA256',available_at=timestamp,capability='FULL_PASS',revision_semantics='PER_ROW_adjustment_source_revision'),
        adjusted_price=dict(**price_binding,source_digest=price_logical,logical_digest=price_logical,available_at=timestamp,capability='FULL_PASS',revision_semantics='adjustment_snapshot_digest',coordinate_identity='coordinate_basis:adjustment_snapshot_id'),
        governance=dict(source_head_path=immutable['path'],source_head_digest=canonical_json_file_sha256(root/immutable['path']),parent_identity=None))
    core=dict(external_acceptance='EXTERNALLY_ACCEPTED',accepted_artifacts={'full_scope_factors':factors_binding},accepted_artifact=profiles_binding)
    return core,context,ids


def load(root,core,context,target=None):
    target=target or context['accepted_trade_date']
    return load_accepted_current(root,core,target=target,cutoff=target+'T23:59:59+08:00',accepted_input_context=context)


def daily_head(root,context):
    date=context['accepted_trade_date'];parent=None
    path=root/'data/v4/V4_DATA_ACCEPTED_HEAD.json'
    if path.exists():parent=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=write(root,'test_only_publications/'+date+'/daily_manifest.json',json.dumps(dict(status='PASS',accepted_input_context={k:context[k] for k in ('raw_daily','adjusted_price')}),sort_keys=True).encode())
    head=dict(contract_id='V4_DATA_ACCEPTED_HEAD_V1',accepted_trade_date=date,source_revision='TEST_ONLY_'+date,canonical_data_revision=canonical_json_sha256(context),manifest_path=manifest['path'],manifest_sha256=manifest['sha256'],parent_head_sha256=parent,
              component_permissions={k:dict(status=context[s]['capability']) for k,s in [('RAW_DAILY','raw_daily'),('ADJUSTED_DAILY','adjusted_price')]})
    write(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json',json.dumps(head,sort_keys=True).encode())


def test_multi_context_without_source_or_fixed_heads_edits(tmp_path):
    source=(ROOT/'src/sector/accepted_input_r5_1.py').read_bytes()
    core_t,t,ids=publication(tmp_path,'2026-09-30',amount=10)
    core_next,nxt,_=publication(tmp_path,'2026-10-01',amount=25)
    first,binding=load(tmp_path,core_t,t);second,next_binding=load(tmp_path,core_next,nxt)
    assert first[ids[0]]['fields']['amount']['value']==10
    assert second[ids[0]]['fields']['amount']['value']==25
    assert first[ids[0]]['price_basis_id']!=second[ids[0]]['price_basis_id']
    assert binding['context_digest']!=next_binding['context_digest']
    assert t['raw_daily']['path']!=nxt['raw_daily']['path'] and t['raw_daily']['sha256']!=nxt['raw_daily']['sha256']
    assert not (tmp_path/'data/v4').exists()
    assert (ROOT/'src/sector/accepted_input_r5_1.py').read_bytes()==source


def test_frozen_t_result_and_digest_survive_t_plus_one_change(tmp_path):
    core,t,ids=publication(tmp_path,'2026-09-30');next_core,nxt,_=publication(tmp_path,'2026-10-01',amount=20)
    before=load(tmp_path,core,t);frozen=copy.deepcopy(before);digest=canonical_json_sha256(before)
    path=tmp_path/nxt['raw_daily']['path'];rows=[json.loads(r) for r in gzip.decompress(path.read_bytes()).splitlines()]
    for row in rows:row['amount']=50
    payload=b''.join(json.dumps(r).encode()+b'\n' for r in rows);path.write_bytes(gzip.compress(payload,mtime=0))
    nxt['raw_daily'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_digest=hashlib.sha256(path.read_bytes()).hexdigest(),logical_digest=hashlib.sha256(payload).hexdigest())
    assert load(tmp_path,next_core,nxt)[0][ids[0]]['fields']['amount']['value']==50
    assert before==frozen and canonical_json_sha256(before)==digest
    assert load(tmp_path,core,t)==before


def test_daily_moving_head_routes_both_sessions(tmp_path):
    core,t,ids=publication(tmp_path,'2026-09-30',amount=10);next_core,nxt,_=publication(tmp_path,'2026-10-01',amount=30)
    daily_head(tmp_path,t);ctx_t=resolve_daily_context(tmp_path,target='2026-09-30');first,_=load(tmp_path,core,ctx_t)
    daily_head(tmp_path,nxt);ctx_next=resolve_daily_context(tmp_path,target='2026-10-01');second,binding=load(tmp_path,next_core,ctx_next)
    assert first[ids[0]]['fields']['amount']['value']==10 and second[ids[0]]['fields']['amount']['value']==30
    assert binding['daily_production_authority'] is True
    assert ctx_next['governance']['parent_identity'] is not None
    assert not list((tmp_path/'data/v4').glob('V4_02_*.json'))


def test_daily_stale_head_no_static_fallback(tmp_path):
    oldcore,old,_=publication(tmp_path,'2026-09-29');core,_,ids=publication(tmp_path,'2026-09-30');daily_head(tmp_path,old)
    ctx=resolve_daily_context(tmp_path,target='2026-09-30');current,binding=load(tmp_path,core,ctx,'2026-09-30')
    assert binding['availability']=='TARGET_ACCEPTED_DATA_UNAVAILABLE'
    assert current[ids[0]]['fields']['amount']['reason_code']=='TARGET_ACCEPTED_DATA_UNAVAILABLE'
    assert current[ids[0]]['price_basis_id'] is None and current[ids[0]]['fields']['ret1']['quality']=='ACCEPTED'


@pytest.mark.parametrize('patch,reason',[
    ('future_date','FUTURE_ACCEPTED_CONTEXT_DATE'),('sha','DIGEST'),('raw_logical','LOGICAL_DIGEST'),('price_logical','LOGICAL_DIGEST'),('future_revision','FUTURE_ACCEPTED_CONTEXT_REVISION')])
def test_context_negative_vectors(tmp_path,patch,reason):
    core,ctx,_=publication(tmp_path,'2026-09-30')
    if patch=='future_date':ctx['accepted_trade_date']='2026-10-01'
    if patch=='sha':ctx['raw_daily']['sha256']='invalid'
    if patch=='raw_logical':ctx['raw_daily']['logical_digest']='invalid'
    if patch=='price_logical':ctx['adjusted_price']['logical_digest']='invalid'
    if patch=='future_revision':ctx['adjusted_price']['available_at']='2026-10-01T00:00:00+08:00'
    with pytest.raises(ValueError,match=reason):load(tmp_path,core,ctx,'2026-09-30')


@pytest.mark.parametrize('component,field',[('raw_daily','amount'),('adjusted_price','close')])
def test_blocked_component_preserves_independent_core(tmp_path,component,field):
    core,ctx,ids=publication(tmp_path,'2026-09-30');ctx[component]['capability']='BLOCKED'
    # Blocked source may be unreadable; no request or fallback is attempted.
    ctx[component]['path']='test_only_missing_payload'
    current,_=load(tmp_path,core,ctx)
    assert current[ids[0]]['fields'][field]['quality']=='UNKNOWN'
    assert current[ids[0]]['fields']['ret1']['quality']=='ACCEPTED'


def test_daily_context_cannot_override_manifest_bindings(tmp_path):
    core,ctx,_=publication(tmp_path,'2026-09-30');daily_head(tmp_path,ctx)
    daily=resolve_daily_context(tmp_path,target='2026-09-30');daily['raw_daily']['path']='unaccepted_path'
    with pytest.raises(ValueError,match='NOT_BOUND'):load(tmp_path,core,daily)


def test_b05_capability_downgrade_ignores_final_boolean_injection(tmp_path):
    core,ctx,ids=publication(tmp_path,'2026-09-30',inject_boolean=True);current,_=load(tmp_path,core,ctx)
    assert all(r['legacy_valid_member']['value'] is None and r['legacy_valid_member']['quality']=='UNKNOWN' for r in current.values())
    params=json.loads((ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_text(encoding='utf8'))
    members=[dict(sector_id='TEST_ONLY',sector_type='INDUSTRY',sector_name='GENERIC',security_id=sid,snapshot_id='TEST_ONLY',target_trade_date='2026-09-30') for sid in ids]
    rows=build_native(members,current,target='2026-09-30',snapshot_id='TEST_ONLY',publication_id='TEST_ONLY',parameter_set=params,source_bindings={})
    cfg=json.loads((ROOT/'config/research_attention_v3.yaml').read_text(encoding='utf8'));inputs=build_b2_inputs(rows,current,'2026-09-30',cfg,bind_semantic(members,current,'2026-09-30'))['TEST_ONLY']
    ast=json.loads((ROOT/'config/v4_08_b2_machine_ast_r5.json').read_text(encoding='utf8'));sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    result=evaluate_b2(inputs,ast,source_sha256=sha(ast['source_path']),source_parameter_sha256=sha(ast['source_parameter_path']),parameter_set_sha256=sha('config/v4_08_algorithm_parameter_set_r5.json'))
    assert result['confirmed_raw']=='UNKNOWN' and result['warm_raw']=='UNKNOWN'
    assert result['capabilities']==dict(B2_NON_AMOUNT_A='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE',B2_AMOUNT_A='DIAGNOSTIC_AUDIT_OPEN')
    assert inputs['normal_rank_eligible']['value'] is None

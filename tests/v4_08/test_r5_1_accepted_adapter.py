"""TEST_ONLY accepted-source fixtures; never publish fixture heads/artifacts."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from sector.accepted_input_r5_1 import load_accepted_current
from sector.semantic_input_r5_1 import bind_semantic
from sector.phase2 import VERSION
from v4.canonical_governance_hash import canonical_json_file_sha256
from sector.native_r5 import build_native
from sector.legacy_b2_r5 import build_b2_inputs, evaluate_b2
from sector.rotation_r5 import advance_rotation, evaluate_b0, resolve_package
from workbench_analysis.sector_attention import build_sector_current

ROOT = Path(__file__).resolve().parents[2]
TARGET = '2026-09-30'


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf8'))


def fixture(root, *, date=TARGET, amounts=None, snapshot='sha256-fixture-adjustment', unknown_valid=False, valid=True, ret1=.1, id_prefix=''):
    """Exercise production authority lookup, byte verification and row adapter."""
    def save(path, value, zipped=False):
        dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
        payload=(b''.join(json.dumps(r,sort_keys=True,separators=(',',':')).encode()+b'\n' for r in value) if zipped else json.dumps(value).encode())
        dest.write_bytes(gzip.compress(payload,mtime=0) if zipped else payload)
        return dict(path=path,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    ids=[f'{id_prefix}TEST_ONLY_MEMBER_{i}' for i in range(8)]
    timestamp=date+'T08:00:00+08:00'
    amounts=amounts if amounts is not None else [10]*8
    factors=[];profiles=[];daily=[];prices=[]
    for i,sid in enumerate(ids):
        factors.append(dict(security_id=sid,trade_date=date,fields={k:dict(value=v,quality_state='OBSERVED',source_asof=date) for k,v in dict(ret1=ret1,ret5=.1,ret20=.1,ret60=.1,rps20=20,amount_ratio20=99).items()}))
        profiles.append(dict(security_id=sid,trade_date=date,states={'trend_state':{'evidence':dict(close=11,ma20=10)}}))
        daily.append(dict(canonical_security_id=sid,trade_date=int(date.replace('-','')),amount=amounts[i],trading_status='ACTUAL_TRADED',adjustment_source_revision='fixture-source-revision',adjusted_quality='READY',price_basis='TDX_NATIVE_AFFINE_QFQ'))
        prices.append(dict(security_id=sid,target_trade_date=int(date.replace('-','')),max_source_trade_date=int(date.replace('-','')),coordinate_basis='T0_CURRENT_COORDINATE',adjustment_snapshot_id=snapshot,adjustment_snapshot_digest='fixture-revision',adjusted_quality='ADJUSTED_READY',qfq_ohlc=['11']*4,formal_publication_at=timestamp,system_available_at=timestamp,adjustment_source_available_at=timestamp,adjustment_system_available_at=timestamp))
    daily_path='data/test_only/daily.parquet';(root/'data/test_only').mkdir(parents=True,exist_ok=True)
    pq.write_table(pa.Table.from_pylist(daily),root/daily_path)
    daily_binding=dict(path=daily_path,sha256=hashlib.sha256((root/daily_path).read_bytes()).hexdigest())
    manifest=save('reports/test_only/canonical_manifest.json',dict(components={'DAILY_R7':daily_binding}))
    save('data/v4/V4_02_ACCEPTED_HEAD.json',dict(external_acceptance='EXTERNALLY_ACCEPTED',manifest_path=manifest['path'],manifest_sha256=manifest['sha256'],accepted_at_utc=timestamp))
    price_binding=save('data/test_only/prices.jsonl.gz',prices,True)
    logical=hashlib.sha256(gzip.decompress((root/price_binding['path']).read_bytes())).hexdigest()
    save('data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json',dict(external_acceptance='EXTERNALLY_ACCEPTED',accepted_candidate=price_binding,logical_digest=logical))
    core=dict(external_acceptance='EXTERNALLY_ACCEPTED',accepted_artifacts={'full_scope_factors':save('data/test_only/factors.jsonl.gz',factors,True)},accepted_artifact=save('data/test_only/profile.jsonl.gz',profiles,True))
    core['accepted_input_context']=dict(contract_id='V4_08_ACCEPTED_INPUT_CONTEXT_R5_2',context_id='TEST_ONLY_ENGINEERING_CONTEXT',accepted_trade_date=date,scope='ENGINEERING_REPLAY_ONLY',daily_production_authority=False,
        raw_daily=dict(**daily_binding,source_digest=daily_binding['sha256'],available_at=timestamp,capability='FULL_PASS',revision_semantics='PER_ROW_adjustment_source_revision'),
        adjusted_price=dict(**price_binding,source_digest=logical,logical_digest=logical,available_at=timestamp,capability='FULL_PASS',revision_semantics='adjustment_snapshot_digest',coordinate_identity='coordinate_basis:adjustment_snapshot_id'),
        governance=dict(source_head_path='data/v4/V4_02_ACCEPTED_HEAD.json',source_head_digest=canonical_json_file_sha256(root/'data/v4/V4_02_ACCEPTED_HEAD.json'),parent_identity=None))
    return core, ids


def adapt(root,core,target=TARGET):
    return load_accepted_current(root,core,target=target,cutoff=target+'T23:59:59+08:00',accepted_input_context=core['accepted_input_context'])[0]


def native(current,ids,target=TARGET):
    members=[dict(sector_id='TEST_ONLY_SECTOR',sector_name='GENERIC INDUSTRY',sector_type='INDUSTRY',security_id=m,snapshot_id='TEST_ONLY',target_trade_date=target) for m in ids]
    rows=build_native(members,current,target=target,snapshot_id='TEST_ONLY',publication_id='TEST_ONLY',parameter_set=read('config/v4_08_algorithm_parameter_set_r5.json'),source_bindings={})
    return members,rows


@pytest.mark.parametrize('amounts,top1,top3,quality,reason',[
    ([10]*8,1/8,3/8,'ACCEPTED',None),
    ([None]+[10]*7,1/7,3/7,'ACCEPTED',None),
    ([0]*8,None,None,'UNKNOWN','ZERO_OR_UNKNOWN_AMOUNT_DENOMINATOR'),
    ([0]+[10]*7,1/7,3/7,'ACCEPTED',None),
    ([-1]+[10]*7,1/7,3/7,'ACCEPTED',None)])
def test_raw_amount_adapter_concentration(tmp_path,amounts,top1,top3,quality,reason):
    core,ids=fixture(tmp_path,amounts=amounts);current=adapt(tmp_path,core)
    _,rows=native(current,ids)
    for k,expected in [(1,top1),(3,top3)]:
        field=rows[0]['fields'][f'top{k}_concentration']
        assert field['value']==expected and field['quality']==quality and field['reason_code']==reason
    assert current[ids[0]]['fields']['amount']['value']==(None if amounts[0] is not None and amounts[0]<0 else amounts[0])


def test_target_date_mismatch_unknown(tmp_path):
    core,ids=fixture(tmp_path,date='2026-09-29')
    # Accepted target factors exist; canonical raw and prices are prior-day.
    target_root=tmp_path/'target';target_core,_=fixture(target_root)
    for key in ('accepted_artifacts','accepted_artifact'):
        core[key]=target_core[key]
    for name in ('factors.jsonl.gz','profile.jsonl.gz'):
        (tmp_path/'data/test_only'/name).write_bytes((target_root/'data/test_only'/name).read_bytes())
    current=adapt(tmp_path,core);_,rows=native(current,ids)
    assert all(r['fields']['amount']['quality']=='UNKNOWN' and r['price_basis_id'] is None for r in current.values())
    assert rows[0]['fields']['top1_concentration']['reason_code']=='ZERO_OR_UNKNOWN_AMOUNT_DENOMINATOR'


def test_future_source_rejected(tmp_path):
    core,_=fixture(tmp_path,date='2026-10-01')
    with pytest.raises(ValueError,match='FUTURE'):adapt(tmp_path,core)


def test_digest_mismatch_rejected(tmp_path):
    core,_=fixture(tmp_path)
    with (tmp_path/'data/test_only/daily.parquet').open('ab') as stream:stream.write(b'X')
    with pytest.raises(ValueError,match='DIGEST'):adapt(tmp_path,core)


def test_price_logical_digest_mismatch_rejected(tmp_path):
    core,_=fixture(tmp_path)
    path=tmp_path/'data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json'
    head=json.loads(path.read_text());core['accepted_input_context']['adjusted_price']['logical_digest']='invalid'
    with pytest.raises(ValueError,match='LOGICAL_DIGEST'):adapt(tmp_path,core)


def test_unaccepted_source_rejected(tmp_path):
    core,_=fixture(tmp_path);core['external_acceptance']='PENDING'
    with pytest.raises(ValueError,match='UNACCEPTED'):adapt(tmp_path,core)


def test_missing_source_payload_degrades_unknown(tmp_path):
    core,ids=fixture(tmp_path)
    (tmp_path/'data/test_only/daily.parquet').unlink()
    (tmp_path/'data/test_only/prices.jsonl.gz').unlink()
    current=adapt(tmp_path,core)
    assert all(row['fields']['amount']['quality']=='UNKNOWN' and row['fields']['close']['quality']=='UNKNOWN' and row['price_basis_id'] is None for row in current.values())
    _,rows=native(current,ids)
    assert rows[0]['fields']['top1_concentration']['value'] is None


def test_accepted_head_newline_identity_uses_existing_canonical_policy(tmp_path):
    core,_=fixture(tmp_path)
    before=load_accepted_current(tmp_path,core,target=TARGET,cutoff=TARGET+'T23:59:59+08:00',accepted_input_context=core['accepted_input_context'])
    for name in ('V4_02_ACCEPTED_HEAD.json','V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json'):
        path=tmp_path/'data/v4'/name
        text=json.dumps(json.loads(path.read_text(encoding='utf8')),indent=2)+'\n'
        path.write_bytes(text.replace('\n','\r\n').encode('utf8'))
    after=load_accepted_current(tmp_path,core,target=TARGET,cutoff=TARGET+'T23:59:59+08:00',accepted_input_context=core['accepted_input_context'])
    assert before==after


@pytest.mark.parametrize('snapshot,expected', [('sha256-fixture-adjustment','ROTATION_PULSE'),('sha256-new-corporate-action','UNKNOWN'),(None,'UNKNOWN')])
def test_price_basis_pulse_adapter(tmp_path,snapshot,expected):
    old='2026-09-29';oldroot=tmp_path/'old';newroot=tmp_path/'new'
    oldcore,ids=fixture(oldroot,date=old);core,_=fixture(newroot,snapshot=snapshot)
    prior_core=adapt(oldroot,oldcore,old);current=adapt(newroot,core)
    _,rows=native(current,ids);row=rows[0]
    registry=read('config/v4_08_sector_field_registry_r5.json');params=read('config/v4_08_algorithm_parameter_set_r5.json');contract=read('config/v4_08_rotation_core_contract_r5.json')
    values,fields=resolve_package(contract,params,(ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes(),registry)
    # Prior-PIT derived pulse triggers are independent of the repaired
    # canonical price/amount fields; the latter are never hand-injected.
    for name,value in dict(dq5=12,breadth_delta1=.1,net_entered_count=1).items():
        row['fields'][name]={**fields[name], 'value':value,'quality':'ACCEPTED'}
    prior=dict(acceptance='ACCEPTED',target_trade_date=old,membership_snapshot_id='TEST_ONLY_PRIOR',output_state='NONE',native_fields={'dq5':{'value':0}},episode=None)
    result=advance_rotation(row,current,prior_publication=prior,prior_members=ids,prior_core=prior_core,calendar_sessions=[old,TARGET],contract=contract,registry=registry,parameters=values,prior_maturity='NONE')
    assert result['output_state']==expected
    if expected=='ROTATION_PULSE':
        assert result['episode']['pulse_baseline']==dict.fromkeys(ids,11)
        assert set(result['episode']['price_basis_ids'].values())=={'T0_CURRENT_COORDINATE:sha256-fixture-adjustment'}
    else:
        assert result['episode'] is None and 'MIXED_PRICE_BASIS' in result['reason_codes']


def test_future_adjustment_revision_rejected(tmp_path):
    core,_=fixture(tmp_path)
    headpath=tmp_path/'data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json';head=json.loads(headpath.read_text());path=tmp_path/head['accepted_candidate']['path']
    rows=[json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]
    rows[0]['adjustment_source_available_at']='2026-10-01T08:00:00+08:00'
    payload=b''.join(json.dumps(r).encode()+b'\n' for r in rows);path.write_bytes(gzip.compress(payload,mtime=0));head['accepted_candidate']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();head['logical_digest']=hashlib.sha256(payload).hexdigest();headpath.write_text(json.dumps(head));core['accepted_input_context']['adjusted_price'].update(sha256=head['accepted_candidate']['sha256'],logical_digest=head['logical_digest'])
    with pytest.raises(ValueError,match='FUTURE_ACCEPTED_PRICE_REVISION'):adapt(tmp_path,core)


@pytest.mark.parametrize('unknown,valid,expected',[(False,True,None),(False,False,None),(True,True,None)])
def test_semantic_mapping_formal_producer_unavailable(tmp_path,unknown,valid,expected):
    core,ids=fixture(tmp_path,unknown_valid=unknown,valid=valid);current=adapt(tmp_path,core);members,rows=native(current,ids)
    sem=bind_semantic(members,current,TARGET)
    facts=build_b2_inputs(rows,current,TARGET,read('config/research_attention_v3.yaml'),sem)['TEST_ONLY_SECTOR']
    assert facts['normal_rank_eligible']['value'] is expected
    if expected is None:
        assert eval_b2(facts)['confirmed_raw']=='UNKNOWN'
    # Same accepted-source adapter flows into Native, B0, Rotation and B2.
    params=read('config/v4_08_algorithm_parameter_set_r5.json');registry=read('config/v4_08_sector_field_registry_r5.json');contract=read('config/v4_08_sector_prewatch_contract_r5.json')
    values,_=resolve_package(contract,params,(ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes(),registry)
    assert evaluate_b0(rows[0],contract,values)['output_state']=='UNKNOWN'


def eval_b2(facts):
    ast=read('config/v4_08_b2_machine_ast_r5.json')
    sha=lambda path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    return evaluate_b2(facts,ast,source_sha256=sha(ast['source_path']),source_parameter_sha256=sha(ast['source_parameter_path']),parameter_set_sha256=sha('config/v4_08_algorithm_parameter_set_r5.json'))


@pytest.mark.parametrize('normal_count',[4,5])
def test_actual_legacy_current_function_against_pit_adapter(tmp_path,normal_count):
    cfg=read('config/research_attention_v3.yaml');native_rows=[];quotes=[];legacy_members=[];current={};semantic={}
    specs=[('NORMAL_ATTRIBUTE',True,'GENERIC THEME')]*normal_count+[('NORMAL_ATTRIBUTE',True,'ST\u677f\u5757'),('NORMAL_ATTRIBUTE',False,'GENERIC THEME'),('UNKNOWN_TAG',True,'GENERIC THEME')]
    for index,(bucket,valid,name) in enumerate(specs):
        folder=tmp_path/str(index);core,ids=fixture(folder,valid=valid,ret1=10 if name=='ST\u677f\u5757' else .01*(index+1),id_prefix=f'{index}_');adapted=adapt(folder,core)
        for sid,row in adapted.items():
            quotes.append(dict(security_id=sid,trade_date=TARGET,ret1=row['fields']['ret1']['value']))
        current.update(adapted)
        sector=f'TEST_ONLY_SECTOR_{index}'
        membership=[dict(sector_id=sector,sector_type='THEME',sector_name=name,semantic_bucket=bucket,security_id=m,snapshot_id='TEST_ONLY',target_trade_date=TARGET) for m in ids]
        # Pure algorithm golden: explicit legacy semantic records are unit
        # inputs, not a claim that the accepted producer is implemented.
        semantic[sector]=dict(sector_id=sector,sector_type='THEME',sector_name=name,semantic_bucket=bucket,sector_valid=valid)
        sem=semantic[sector]
        legacy_members.extend(dict(**q,**sem) for q in quotes[-len(ids):])
        native_rows.extend(build_native(membership,current,target=TARGET,snapshot_id='TEST_ONLY',publication_id='TEST_ONLY',parameter_set=read('config/v4_08_algorithm_parameter_set_r5.json'),source_bindings={}))
    inputs=build_b2_inputs(native_rows,current,TARGET,cfg,semantic)
    actual=build_sector_current(pd.DataFrame(legacy_members),pd.DataFrame(quotes),cfg)
    for row in actual.to_dict('records'):
        facts=inputs[row['sector_id']]
        assert facts['normal_rank_eligible']['value']==row['normal_rank_eligible']
        assert facts['type_cross_section_coverage']['value']==row['type_cross_section_coverage']
        value=facts['p1']['value'];assert (value is None and pd.isna(row['p1'])) or value==row['p1']
        expected='TRUE' if row['current'] is True else 'FALSE' if row['current'] is False else 'UNKNOWN'
        assert eval_b2(facts)['confirmed_diagnostic']==expected
    excluded=f'TEST_ONLY_SECTOR_{normal_count}'
    assert inputs[excluded]['p1']['value'] is None
    without=build_b2_inputs([r for r in native_rows if r['sector_id']!=excluded],current,TARGET,cfg,semantic)
    for index in range(normal_count):
        sid=f'TEST_ONLY_SECTOR_{index}';assert inputs[sid]['p1']==without[sid]['p1']
    # Missing provenance is distinct from the legacy's explicit UNKNOWN_TAG.
    unknown=copy.deepcopy(semantic);unknown[excluded]['sector_valid']=None
    degraded=build_b2_inputs(native_rows,current,TARGET,cfg,unknown)
    assert degraded[excluded]['normal_rank_eligible']['value'] is None
    assert eval_b2(degraded[excluded])['confirmed_raw']=='UNKNOWN'
    assert all(f['p1']['value'] is None for f in degraded.values())

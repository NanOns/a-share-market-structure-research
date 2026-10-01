"""Accepted-producer fixtures with real frozen bytes; never real registration."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import pytest
from workbench_analysis.source_authority_producers_r3 import (
    HEAD_PATH, REGISTRY_PATH, MODE, require_accepted_producer, require_formal_source, OwnerAcceptanceError)
from workbench_analysis.source_authority_governance_r1 import evaluate_consumer_gate
from workbench_analysis.dm01_source_boundary_r2 import require_a12_producer_instances_for_candidate
ROOT=Path(__file__).resolve().parents[2]
P='reports/audits/A10_A12_R3_'
CONSUMER='DM01_FINAL_ALL_NINE'
def read(root,p):return json.loads((root/p).read_text(encoding='utf8'))
def write(root,p,v):
    path=root/p;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(v,sort_keys=True),encoding='utf8')
    return dict(path=p,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def copy_binding_tree(root,binding,seen=None):
    seen=seen if seen is not None else set();p=binding['path']
    if p in seen:return
    seen.add(p);target=root/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    if target.suffix!='.json':return
    def visit(v):
        if isinstance(v,dict):
            if 'path' in v and 'sha256' in v and (ROOT/v['path']).is_file():copy_binding_tree(root,v,seen)
            for x in v.values():visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    value=read(root,p)
    if p.endswith('ACCEPTED_HEAD_R1.json'):
        for key in ('identity_revision','accepted_extension'):
            if key in value:copy_binding_tree(root,value[key],seen)
    elif 'security_entity_map_' not in p and 'market_calendar_' not in p:visit(value)
def install(root):
    manifest=read(ROOT,P+'SOURCE_INSTANCE_MANIFEST_R1.json')
    for fields in manifest['instances'].values():
        for b in fields.values():copy_binding_tree(root,b)
    config=read(ROOT,'config/source_authority_governance_r3.json');owners=[]
    for rule in config['field_rules']:
        if rule['field_id'] not in ('TRADING_STATUS','ISST'):continue
        rule.update(enabled_for_formal_consumer=True,authority_status='EXTERNALLY_ACCEPTED')
        owner=read(ROOT,manifest['producer_candidates'][rule['field_id']]['path'])
        owner.update(external_acceptance='EXTERNALLY_ACCEPTED',formal_consumer_authorization=True,
                     accepted_at='2026-10-01T08:00:00Z',role_binding=rule,fixture_only=True)
        b=write(root,'fixtures/producer_'+rule['field_id']+'.json',owner)
        owners.append(dict(owner_contract_id=owner['contract_id'],producer_contract=b,
            **{k:owner[k] for k in ('field_id','external_acceptance','formal_consumer_authorization',
                 'allowed_consumers','historical_modes','source_instance_policy_id','role_binding','accepted_at')}))
    registry=dict(contract_id='SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V2',version=2,owners=owners,fixture_only=True)
    write(root,HEAD_PATH,dict(contract_id='SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V2',registry=write(root,REGISTRY_PATH,registry)))
    write(root,'config/source_authority_governance_r3.json',config)
    return config,manifest
@pytest.fixture
def fixture(tmp_path):return tmp_path,*install(tmp_path)
@pytest.mark.parametrize('target',['2026-09-28','2026-09-30'])
def test_real_sources_pass_global_and_dm01(fixture,target):
    root,config,manifest=fixture
    for rule in config['field_rules']:
        if rule['field_id'] not in manifest['instances'][target]:continue
        result=evaluate_consumer_gate(rule,project_root=root,consumer_contract_id=CONSUMER,
            target_trade_date=target,availability='AVAILABLE',required=True,
            source_instance_binding=manifest['instances'][target][rule['field_id']])
        assert result['formal_authority_authorized'] and result['status']=='PASS_CORE_SCOPE'
    result=require_a12_producer_instances_for_candidate(root,manifest['instances'][target],target_trade_date=target)
    assert result['all_nine_accepted'] is False
def test_missing_interior_day_global_gate_alone_blocks(fixture):
    root,config,_=fixture
    rule=next(r for r in config['field_rules'] if r['field_id']=='TRADING_STATUS')
    result=evaluate_consumer_gate(rule,project_root=root,consumer_contract_id=CONSUMER,
        target_trade_date='2026-09-29',availability='AVAILABLE',required=True)
    assert not result['formal_authority_authorized']
    assert result['owner_acceptance_reason']=='SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE'
    with pytest.raises(OwnerAcceptanceError,match='SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE'):
        require_a12_producer_instances_for_candidate(root,{},target_trade_date='2026-09-29')
@pytest.mark.parametrize('mutation',['provider_date','target','raw_sha','schema','received','naive_time',
    'revision','identity','calendar','empty','ambiguous','row_date','unbounded','malformed_bit','as_recorded','wrong_field'])
def test_source_negative_vectors(fixture,mutation):
    root,config,manifest=fixture;target='2026-09-28'
    rule=next(r for r in config['field_rules'] if r['field_id']=='TRADING_STATUS')
    b=manifest['instances'][target]['TRADING_STATUS'];instance=read(root,b['path'])
    if mutation=='provider_date':instance['provider_date']='2026-09-29'
    elif mutation=='target':instance['target_trade_date']='2026-09-30'
    elif mutation=='raw_sha':instance['raw_artifact']['sha256']='0'*64
    elif mutation=='schema':instance['schema_contract']['sha256']='0'*64
    elif mutation=='received':instance['received_at']='2026-09-28T00:00:00Z'
    elif mutation=='naive_time':instance['observed_at']='2026-10-01T00:00:00'
    elif mutation=='revision':instance['source_revision']='sha256:'+'0'*64
    elif mutation=='as_recorded':instance['AS_RECORDED']=True
    elif mutation=='wrong_field':instance['field_id']='OHLC_VOLUME_AMOUNT'
    elif mutation in ('identity','calendar'):
        key=mutation+'_binding';doc=read(root,instance[key]['path']);doc['target_trade_date']='2026-09-29'
        instance[key]=write(root,instance[key]['path'],doc)
    else:
        raw=read(root,instance['raw_artifact']['path'])
        if mutation=='empty':raw['rows']=[]
        elif mutation=='ambiguous':raw['rows'][1]=deepcopy(raw['rows'][0])
        elif mutation=='row_date':raw['rows'][0]['date']='2026-09-29'
        elif mutation=='malformed_bit':raw['rows'][0]['tradestatus']=''
        elif mutation=='unbounded':raw['provider_metadata']['page_count']=2
        instance['raw_artifact']=write(root,instance['raw_artifact']['path'],raw)
        instance['source_revision']='sha256:'+instance['raw_artifact']['sha256']
        receipt=read(root,instance['capture_receipt']['path']);receipt['responses']['query_daily_history_k_AStock']['raw_response_binding']=instance['raw_artifact']
        instance['capture_receipt']=write(root,instance['capture_receipt']['path'],receipt)
    b=write(root,b['path'],instance)
    with pytest.raises(OwnerAcceptanceError):require_formal_source(root,rule,consumer_contract_id=CONSUMER,target_trade_date=target,instance_binding=b)
@pytest.mark.parametrize('change',['consumer','AS_RECORDED','OHLC','owner_hash','role'])
def test_producer_scope_fail_closed(fixture,change):
    root,config,manifest=fixture;rule=deepcopy(next(r for r in config['field_rules'] if r['field_id']=='ISST'))
    consumer=CONSUMER;mode=MODE
    if change=='consumer':consumer='UNDECLARED'
    elif change=='AS_RECORDED':mode='AS_RECORDED_PIT_FACT'
    elif change=='OHLC':rule['field_id']='OHLC_VOLUME_AMOUNT'
    elif change=='role':rule['may_change_core_quality']=True
    else:
        registry=read(root,REGISTRY_PATH);registry['owners'][1]['producer_contract']['sha256']='0'*64
        head=read(root,HEAD_PATH);head['registry']=write(root,REGISTRY_PATH,registry);write(root,HEAD_PATH,head)
    with pytest.raises(OwnerAcceptanceError):require_accepted_producer(root,rule,consumer_contract_id=consumer,historical_mode=mode)
def test_real_registry_historical_only_and_old_namespace_preserved():
    registry=read(ROOT,REGISTRY_PATH);assert len(registry['owners'])==2
    assert all(e['registration_scope']=='HISTORICAL_PATH_B_ONLY' for e in registry['owners'])
    assert read(ROOT,'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json')['owners']==[]
    config=read(ROOT,'config/source_authority_governance_r3.json')
    for rule in config['field_rules']:
        if rule['field_id'] in ('TRADING_STATUS','ISST'):
            with pytest.raises(OwnerAcceptanceError):require_accepted_producer(ROOT,rule,consumer_contract_id=CONSUMER)
    for rule in config['historical_field_rules']:
        proof=require_accepted_producer(ROOT,rule,consumer_contract_id=rule['allowed_consumers'][0])
        result=require_formal_source(ROOT,rule,consumer_contract_id=rule['allowed_consumers'][0],target_trade_date='2026-09-24',instance_binding=proof['owner']['historical_source_instance_archive'])
        assert result['instance']['AS_RECORDED'] is False
        with pytest.raises(OwnerAcceptanceError):require_formal_source(ROOT,rule,consumer_contract_id=rule['allowed_consumers'][0],target_trade_date='2026-09-29',instance_binding=proof['owner']['historical_source_instance_archive'])


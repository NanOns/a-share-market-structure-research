"""Synthetic authorization fixtures are not actual owner registrations."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest

from workbench_analysis.source_authority_accepted_owners_v1 import (
    HEAD_PATH, REGISTRY_PATH, HEAD_CONTRACT, REGISTRY_CONTRACT, ERROR, validate_registry_schema,
    require_accepted_owner, OwnerAcceptanceError, load_registered_owners)
from workbench_analysis.source_authority_governance_r1 import evaluate_consumer_gate
from workbench_analysis.dm01_source_boundary_r2 import require_external_a12_owner_for_final_candidate

ROOT=Path(__file__).resolve().parents[2]
TARGET='2026-09-28'
CONSUMER='DM01_FINAL_ALL_NINE'
MODE='TARGET_DATE_QUERYABLE_FACT'

def write(root,path,value):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,sort_keys=True),encoding='utf8')
    return dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def fixture_rule(field):
    return dict(field_id=field,source_family='SYNTHETIC_FIXTURE_ONLY',role='FIELD_AUTHORITY',
        owner_contract_id='SYNTHETIC_OWNER_'+field+'_V2',role_binding_id='SYNTHETIC_ROLE_'+field+'_R2',
        allowed_consumers=[CONSUMER],may_block_core=True,may_change_core_value=True,may_change_core_quality=False,
        historical_retrieval_mode=MODE,pit_requirement='EXPLICIT_KNOWLEDGE_TIME',
        enabled=True,enabled_for_formal_consumer=True,authority_status='EXTERNALLY_ACCEPTED')

def install(root):
    rules=[fixture_rule(f) for f in ('TRADING_STATUS','ISST')]
    owners=[]
    for r in rules:
        owner=dict(contract_id=r['owner_contract_id'],field_id=r['field_id'],external_acceptance='EXTERNALLY_ACCEPTED',
            formal_consumer_authorization=True,allowed_consumers=[CONSUMER],
            effective_scope=dict(start_date='2026-09-24',end_date='2026-09-30'),historical_mode=MODE,
            accepted_at='2026-10-01T01:00:00Z',supersedes=None,role_binding=r,fixture_only=True)
        binding=write(root,'fixtures/'+r['field_id']+'.json',owner)
        owners.append(dict(owner_contract_id=owner['contract_id'],field_id=r['field_id'],artifact=binding,
            role_binding_id=r['role_binding_id'],source_role=r['role'],
            **{k:owner[k] for k in ('external_acceptance','formal_consumer_authorization','allowed_consumers',
                                  'effective_scope','historical_mode','accepted_at','supersedes')}))
    registry=dict(contract_id=REGISTRY_CONTRACT,version=1,owners=owners,fixture_only=True)
    save_registry(root,registry)
    write(root,'config/source_authority_governance_r2.json',dict(field_rules=rules,fixture_only=True))
    return rules,registry

def save_registry(root,registry):
    binding=write(root,REGISTRY_PATH,registry);binding['version']=1
    write(root,HEAD_PATH,dict(contract_id=HEAD_CONTRACT,registry=binding,fixture_only=True))

def gate(root,rule,**kwargs):
    return evaluate_consumer_gate(rule,project_root=root,consumer_contract_id=CONSUMER,availability='AVAILABLE',
        target_trade_date=TARGET,core_value='OLD_CORE',supplemental_value='CANDIDATE',required=True,**kwargs)

def test_exact_external_accepted_fixture_can_authorize(tmp_path):
    rules,registry=install(tmp_path)
    assert validate_registry_schema(registry)
    result=gate(tmp_path,rules[0])
    assert result['status']=='PASS_CORE_SCOPE' and result['formal_authority_authorized']
    assert result['core_value']=='CANDIDATE'

def test_core_authority_also_requires_exact_registered_proof(tmp_path):
    rules,registry=install(tmp_path);r=rules[0];entry=registry['owners'][0]
    r['role']='CORE_AUTHORITY'
    assert gate(tmp_path,r)['status']==ERROR
    p=tmp_path/entry['artifact']['path'];owner=json.loads(p.read_text());owner['role_binding']=r
    entry['artifact']=write(tmp_path,entry['artifact']['path'],owner);entry['source_role']='CORE_AUTHORITY'
    save_registry(tmp_path,registry)
    assert gate(tmp_path,r)['formal_authority_authorized']

def test_promotion_requires_new_exact_accepted_contract_and_role(tmp_path):
    rules,registry=install(tmp_path);r=rules[0];entry=registry['owners'][0]
    previous=write(tmp_path,'fixtures/old_supplemental_v1.json',dict(contract_id='SYNTHETIC_SUPPLEMENTAL_V1',role='SUPPLEMENTAL_CROSSCHECK'))
    entry['supersedes']=previous
    owner=json.loads((tmp_path/entry['artifact']['path']).read_text());owner['supersedes']=previous
    entry['artifact']=write(tmp_path,entry['artifact']['path'],owner);save_registry(tmp_path,registry)
    assert gate(tmp_path,r)['formal_authority_authorized']
    owner['contract_id']='SYNTHETIC_SUPPLEMENTAL_V1';r['owner_contract_id']=owner['contract_id'];owner['role_binding']=r
    entry['owner_contract_id']=owner['contract_id'];entry['artifact']=write(tmp_path,entry['artifact']['path'],owner)
    save_registry(tmp_path,registry)
    assert gate(tmp_path,r)['status']==ERROR

@pytest.mark.parametrize('mutation',[
    'no_registry','external_null','formal_false','other_field','other_consumer','bad_owner_hash',
    'scope_excludes_target','registry_not_in_head','bad_registry_hash','wrong_contract_id','mode_mismatch',
    'unaccepted_role_change','pending_rule','external_boolean','duplicate_owner','malformed_scope',
    'owner_external_null_registry_accepted','registry_version','global_head_contract','missing_accepted_at',
    'path_escape','wrong_field_artifact','non_boolean_formal','owner_formal_integer',
])
def test_owner_proof_negative_vectors_fail_closed(tmp_path,mutation):
    rules,registry=install(tmp_path);r=rules[0];entry=registry['owners'][0]
    if mutation=='no_registry':(tmp_path/REGISTRY_PATH).unlink()
    elif mutation=='external_null':entry['external_acceptance']=None
    elif mutation=='formal_false':entry['formal_consumer_authorization']=False
    elif mutation=='other_field':entry['field_id']='OTHER_FIELD'
    elif mutation=='other_consumer':entry['allowed_consumers']=['OTHER_CONSUMER']
    elif mutation=='bad_owner_hash':entry['artifact']['sha256']='0'*64
    elif mutation=='scope_excludes_target':entry['effective_scope']['end_date']='2026-09-27'
    elif mutation=='wrong_contract_id':
        p=tmp_path/entry['artifact']['path'];v=json.loads(p.read_text());v['contract_id']='OTHER_OWNER'
        entry['artifact']=write(tmp_path,entry['artifact']['path'],v)
    elif mutation=='mode_mismatch':entry['historical_mode']='AS_RECORDED_PIT_FACT'
    elif mutation=='unaccepted_role_change':r['may_change_core_quality']=True
    elif mutation=='pending_rule':r['authority_status']='PENDING_EXTERNAL_ACCEPTANCE'
    elif mutation=='external_boolean':entry['external_acceptance']=True
    elif mutation=='duplicate_owner':registry['owners'].append(deepcopy(entry))
    elif mutation=='malformed_scope':entry['effective_scope']={}
    elif mutation=='owner_external_null_registry_accepted':
        p=tmp_path/entry['artifact']['path'];v=json.loads(p.read_text());v['external_acceptance']=None
        entry['artifact']=write(tmp_path,entry['artifact']['path'],v)
    elif mutation=='registry_version':registry['version']=2
    elif mutation=='missing_accepted_at':del entry['accepted_at']
    elif mutation=='path_escape':entry['artifact']['path']='../outside_owner.json'
    elif mutation=='wrong_field_artifact':entry['artifact']=deepcopy(registry['owners'][1]['artifact'])
    elif mutation=='non_boolean_formal':entry['formal_consumer_authorization']='true'
    elif mutation=='owner_formal_integer':
        p=tmp_path/entry['artifact']['path'];v=json.loads(p.read_text());v['formal_consumer_authorization']=1
        entry['artifact']=write(tmp_path,entry['artifact']['path'],v)
    if mutation!='no_registry':save_registry(tmp_path,registry)
    if mutation in ('registry_not_in_head','bad_registry_hash','global_head_contract'):
        h=json.loads((tmp_path/HEAD_PATH).read_text())
        if mutation=='registry_not_in_head':del h['registry']
        elif mutation=='bad_registry_hash':h['registry']['sha256']='0'*64
        else:h['contract_id']='BUSINESS_STAGE_HEAD'
        write(tmp_path,HEAD_PATH,h)
    before=deepcopy(r);result=gate(tmp_path,r)
    assert result['status']==ERROR and not result['formal_authority_authorized']
    assert result['core_value']=='OLD_CORE' and r==before and result['capability_blocked']

def test_supplemental_cannot_self_promote_by_changing_consumer_rule(tmp_path):
    rules,_=install(tmp_path)
    rule=deepcopy(rules[0]);rule['owner_contract_id']='BAOSTOCK_SUPPLEMENTAL_SOURCE_V1'
    assert gate(tmp_path,rule)['status']==ERROR
    rule=deepcopy(rules[0]);rule['role_binding_id']='NEW_UNREGISTERED_ROLE'
    assert gate(tmp_path,rule)['status']==ERROR

def test_diagnostic_flag_cannot_grant_formal_authority(tmp_path):
    rules,_=install(tmp_path)
    result=gate(tmp_path,rules[0],formal_use=False)
    assert result['status']=='PASS_DIAGNOSTIC_SCOPE'
    assert not result['formal_authority_authorized'] and result['core_value']=='OLD_CORE'

def test_undeclared_consumer_cannot_receive_formal_pass_or_block_other_capabilities(tmp_path):
    rules,_=install(tmp_path)
    result=evaluate_consumer_gate(rules[0],project_root=tmp_path,consumer_contract_id='UNDECLARED',
        availability='AVAILABLE',target_trade_date=TARGET,core_value='CORE',supplemental_value='CANDIDATE')
    assert result['status']==ERROR and not result['formal_authority_authorized']
    assert result['core_value']=='CORE' and not result['capability_blocked'] and not result['global_core_blocked']

@pytest.mark.parametrize('mutation',[None,'external_null','formal_false','binding_wrong','mode_wrong','date_wrong','head_missing'])
def test_dm01_and_generic_gate_share_exact_authorization(tmp_path,mutation):
    rules,registry=install(tmp_path)
    bindings={e['field_id']:deepcopy(e['artifact']) for e in registry['owners']}
    mode=MODE;target=TARGET
    if mutation=='external_null':registry['owners'][1]['external_acceptance']=None
    elif mutation=='formal_false':registry['owners'][1]['formal_consumer_authorization']=False
    elif mutation=='binding_wrong':bindings['ISST']['sha256']='0'*64
    elif mutation=='mode_wrong':mode='AS_RECORDED_PIT_FACT'
    elif mutation=='date_wrong':target='2026-10-01'
    save_registry(tmp_path,registry)
    if mutation=='head_missing':(tmp_path/HEAD_PATH).unlink()
    results=[evaluate_consumer_gate(r,project_root=tmp_path,consumer_contract_id=CONSUMER,availability='AVAILABLE',
        target_trade_date=target,required=True,historical_mode=mode,owner_contract_binding=bindings[r['field_id']]) for r in rules]
    global_allowed=all(r['formal_authority_authorized'] for r in results)
    try:
        require_external_a12_owner_for_final_candidate(tmp_path,bindings,{'forged_legacy_head':True},
            target_trade_date=target,historical_mode=mode)
        private_allowed=True
    except ValueError:private_allowed=False
    assert private_allowed==global_allowed==(mutation is None)

def test_actual_a12_pending_owner_rejected_by_generic_and_private():
    contract=json.loads((ROOT/'config/source_authority_governance_r2.json').read_text(encoding='utf8'))
    registry=load_registered_owners(ROOT)
    assert registry['owners']==[]
    owner_path='config/v4_02_status_st_authority_r1.json'
    binding=dict(path=owner_path,sha256=hashlib.sha256((ROOT/owner_path).read_bytes()).hexdigest())
    for r in contract['field_rules']:
        if r['field_id'] in ('TRADING_STATUS','ISST'):
            assert r['enabled_for_formal_consumer'] is False and r['authority_status']=='PENDING_EXTERNAL_ACCEPTANCE'
            assert gate(ROOT,r)['status']==ERROR
    with pytest.raises(ValueError,match='A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED'):
        require_external_a12_owner_for_final_candidate(ROOT,binding,target_trade_date=TARGET)

def test_scanner_pending_owners_and_unaccepted_supplemental_promotion(tmp_path):
    from scripts.scan_source_authority_governance_r1 import inspect_file
    rule=fixture_rule('TRADING_STATUS')
    categories={f['category'] for f in inspect_file('config/candidate.json',json.dumps(rule).encode(),tmp_path)}
    assert {'FIELD_AUTHORITY_WITHOUT_ACCEPTED_OWNER_BINDING','FORMAL_CONSUMER_USING_PENDING_OWNER'} <= categories
    rule['source_family']='BAOSTOCK'
    findings=inspect_file('config/candidate.json',json.dumps(rule).encode(),tmp_path)
    assert 'SUPPLEMENTAL_ROLE_PROMOTED_WITHOUT_ACCEPTED_OWNER' in {f['category'] for f in findings}
    assert any(f['confidence']=='PENDING_OWNER' for f in findings)

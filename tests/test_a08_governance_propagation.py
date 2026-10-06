"""Additive A08 admission, V6 fail-closed gates and historical restart compatibility."""
import copy,json,os
from pathlib import Path
import pytest
from scripts.full_chain_repair_io import ROOT
from scripts.v4_16_capability_resolution_v2 import resolve,admission,validate_dependencies,validate_grant
from scripts.v4_16_go_forward_shadow_runtime import dependency_digest
from tests.test_settlement_r1r1 import accepted

def load(path):return json.loads((ROOT/path).read_bytes())
def put(root,path,value):
    data=value if isinstance(value,bytes) else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.tmp');temp.write_bytes(data);os.replace(temp,target)
    from scripts.r25_bridge_oracle_r4r2 import binding
    return binding(root,path)

def copy_governance(root):
    deps=load('config/v4_16_runtime_dependencies_v6.json')
    for ref in deps['bindings']:
        put(root,ref['path'],(ROOT/ref['path']).read_bytes())
    put(root,'config/v4_16_runtime_dependencies_v6.json',(ROOT/'config/v4_16_runtime_dependencies_v6.json').read_bytes())
    return deps

def test_exact_head_scope_and_only_A08_diff():
    old=load('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json');new=load('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json')
    assert [k for k in old['entries'] if old['entries'][k]!=new['entries'][k]]==['A08_CURRENT_RUNTIME']
    a08=new['entries']['A08_CURRENT_RUNTIME']
    assert a08['current_state']=='ACCEPTED_SCOPED'
    assert a08['blocks_affected_capability_in_shadow'] is a08['blocks_shadow_entry'] is False
    assert a08['blocks_production_cutover_for_scope'] is True
    assert a08['formal_consumer_permission_granted_by_this_head'] is a08['blocks_v4_16_runtime_activation'] is False
    assert a08['affected_capabilities']==['V4_09_N01_CURRENT_RUNTIME_PREWATCH']
    from scripts.full_chain_repair_io import binding
    ref=a08['current_authority']['current_runtime_external_acceptance'];assert ref==binding(ref['path'])

@pytest.mark.parametrize('capability,blocker',[('PURE_CORE_STOCK',None),('AMOUNT_A_H21_FORMAL_CONSUMER','A04_H21_CONSUMER'),('HISTORICAL_AMOUNT_A_FORMAL_CONSUMER','A04_HISTORICAL_AMOUNT_A')])
def test_capability_scopes(capability,blocker):
    from scripts.full_chain_repair_io import binding
    result=admission(ROOT,binding('config/v4_16_runtime_capability_resolution_v2.json'),[capability])
    assert result['permission_granted'] is False
    assert result['blocking_issue_ids']==([] if blocker is None else [blocker])
    if capability=='PURE_CORE_STOCK':assert 'V4_09_N01_CURRENT_RUNTIME_PREWATCH' in result['required_capabilities']

@pytest.mark.parametrize('case',['unknown_issue','stale_V3_head','mismatched_head_sha','stale_resolver','external_audit_tamper'])
def test_fail_closed_governance(tmp_path,case):
    deps=copy_governance(tmp_path);cap=load(deps['capability_resolution']['path']);head=load(cap['current_audit_head']['path'])
    if case=='unknown_issue':
        head['entries']['UNKNOWN_NEW_BLOCKER']=dict(head['entries']['A04_H21_CONSUMER'])
        with pytest.raises(ValueError,match='UNRESOLVED_CURRENT_AUDIT_ISSUE'):resolve(cap,head,['PURE_CORE_STOCK'])
    elif case=='stale_V3_head':
        with pytest.raises(ValueError,match='STALE_CURRENT_AUDIT_HEAD'):resolve(cap,load('data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json'),['PURE_CORE_STOCK'])
    elif case=='stale_resolver':
        deps['capability_resolution']=load('config/v4_16_runtime_dependencies_v5.json')['capability_resolution']
        with pytest.raises(ValueError,match='STALE_RESOLVER_IN_V6'):validate_dependencies(tmp_path,deps)
    else:
        ref=cap['current_audit_head'] if case=='mismatched_head_sha' else cap['external_acceptance_bindings'][0]
        put(tmp_path,ref['path'],(tmp_path/ref['path']).read_bytes()+b'\nTAMPERED')
        with pytest.raises(ValueError,match='EXACT_DEPENDENCY_MISMATCH'):admission(tmp_path,deps['capability_resolution'],['PURE_CORE_STOCK'])

def test_V5_grant_rejected_by_V6_and_actual_settlement_controller(accepted):
    db,x,a,b,ref=accepted
    from scripts.v4_16_go_forward_shadow_runtime_r4r4 import SettlementObligationControllerR4R2
    with pytest.raises(ValueError,match='V6_GRANT_DEPENDENCY_MISMATCH|STALE_OBLIGATION_DEPENDENCY'):
        SettlementObligationControllerR4R2(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
    grant=copy.deepcopy(db.controller.grant)
    with pytest.raises(ValueError,match='V6_GRANT_DEPENDENCY_MISMATCH'):validate_grant(load('config/v4_16_runtime_dependencies_v6.json'),grant)

def test_V6_grant_rejected_by_historical_V5_actual_restart():
    from scripts.r24r1_simulation import prepare,controller,SimulationClock
    from scripts.r24r1_io import ref
    from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController
    from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SuccessorDatabase,SettlementObligationControllerR4R2 as V5
    from scripts.v4_16_go_forward_shadow_runtime_r4r4 import SettlementObligationControllerR4R2 as V6
    def v6(authority,deps,sources,seed):
        deps['contract_id']='V4_16_RUNTIME_DEPENDENCIES_V6'
        deps['bindings']=[ref(b['path']) for b in deps['bindings']]
        deps.update(queue_migration=ref('migrations/v4_16_settlement_queue_v2.sql'),integrity_migration=ref('migrations/v4_16_real_shadow_integrity_v2.sql'))
    x=prepare(changes=v6);db=SuccessorDatabase(controller(x),ROOT/x['database'])
    try:
        launch=OneSessionLaunchController(db);launch.run(x['request'],clock=SimulationClock());launch.stop()
        assert db.controller.grant['runtime_dependency_contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V6'
        with pytest.raises(ValueError,match='STALE_OBLIGATION_DEPENDENCY'):V5(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
        resumed=V6(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
        assert resumed.grant['runtime_dependency_contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V6'
        with pytest.raises(ValueError,match='SETTLEMENT_ONLY'):resumed.verify_request(x['request'])
    finally:db.close()

def test_V6_real_runtime_disabled_without_source_or_database():
    from scripts.v4_16_go_forward_shadow_runtime_r4r4 import RealShadowController
    with pytest.raises(ValueError,match='NOT_AUTHORIZED_BEFORE_CONSUMPTION'):RealShadowController(ROOT)
    assert not (ROOT/'data/v4/shadow_real_v1').exists()

def test_V6_grant_digest_and_resolver_parity():
    deps=load('config/v4_16_runtime_dependencies_v6.json')
    validate_grant(deps,dict(runtime_dependency_contract_id=deps['contract_id'],dependency_set_digest=dependency_digest(deps)))
    assert validate_dependencies(ROOT,deps)['admitted'] is True
    grant=dict(runtime_dependency_contract_id=deps['contract_id'],dependency_set_digest='0'*64)
    with pytest.raises(ValueError,match='V6_GRANT_DEPENDENCY_MISMATCH'):validate_grant(deps,grant)

def test_V6_r25_selection_waits_for_real_target():
    from scripts.validate_r25_preflight_v6 import selection
    result=selection();assert result['status']=='WAIT_ACCEPTED_DAILY_INPUT'
    assert result['target_trade_date'] is None and result['selected_from_wall_clock'] is False

def test_V6_packet_builder_and_validator_engineering_roundtrip(tmp_path):
    from tests.v4_dm01_r4r2.test_bridge import vector,packet_vector
    from scripts import r25_bridge_oracle_r4r2 as oracle
    from scripts.build_r25_packet_r4r4 import produce_packet
    from scripts.validate_r25_preflight_v6 import inspect_packet
    v=vector.__wrapped__(tmp_path);packet=packet_vector(v,v['d']['target_session_pit_binding'])
    deps=copy_governance(tmp_path)
    packet['daily']['bridge_mode']='ENGINEERING';packet['daily']['daily_input_digest']=oracle.digest({k:x for k,x in packet['daily'].items() if k!='daily_input_digest'})
    daily=put(tmp_path,'vector/v6_daily.json',packet['daily'])
    candidate=packet['candidate'];candidate['grant'].update(runtime_dependency_contract_id=deps['contract_id'],dependency_set_digest=dependency_digest(deps),daily_input_authority=daily,daily_input_digest=packet['daily']['daily_input_digest'])
    candidate_ref=put(tmp_path,'reports/r25/activation_candidate/v6_candidate.json',candidate)
    source_ref=candidate['grant']['source_authority'];predecessor=candidate['grant']['predecessor']
    ref=produce_packet(tmp_path,daily=daily,candidate=candidate_ref,sources=source_ref,predecessor=predecessor,output='reports/r25/activation_candidate/v6_packet.json',engineering=True)
    result=inspect_packet(tmp_path,ref,test_only=True)
    assert result['status']=='PASS_ENGINEERING_VECTOR_NOT_REAL' and result['execution_authorized'] is False
    with pytest.raises(ValueError):inspect_packet(tmp_path,ref)
    assert not (tmp_path/'data/v4/shadow_real_v1').exists()

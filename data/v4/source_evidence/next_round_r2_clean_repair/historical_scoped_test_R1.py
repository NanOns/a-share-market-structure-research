from copy import deepcopy
from datetime import timedelta,datetime
from pathlib import Path
import json
import pytest
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    DISPOSITIONS,PERMISSIONS,OWNER_PATH,READER_PATH,record_path,validate_record,
    validate_accepted_owner_metadata,validate_reader_manifest,
    accepted_forward_append,accepted_adjusted_lineage,read_accepted_history,
)

ROOT=Path(__file__).resolve().parents[2]
def read(path):return json.loads((ROOT/path).read_bytes())

@pytest.mark.parametrize('package',list(DISPOSITIONS))
def test_exact_external_scope_record(package):
    record=read(record_path(package))
    assert validate_record(ROOT,record,package)['disposition']==DISPOSITIONS[package]
    assert record['permissions']==PERMISSIONS

@pytest.mark.parametrize('package',list(DISPOSITIONS))
@pytest.mark.parametrize('fault',['task_authority','audited_head','permission','disposition','hash','evidence_missing','current_state'])
def test_each_acceptance_fail_closed(package,fault):
    record=read(record_path(package))
    if fault=='task_authority':record['external_authority']['authority_kind']='TASK_CARD'
    elif fault=='audited_head':record['external_authority']['audited_head']='0'*40
    elif fault=='permission':record['permissions']['formal_consumer_cutover']=True
    elif fault=='disposition':record['disposition']='PRODUCTION_READY'
    elif fault=='hash':record['evidence_bindings'][0]['sha256']='0'*64
    elif fault=='evidence_missing':record['evidence_bindings']=[]
    elif fault=='current_state':record['current_state']='PRODUCTION_READY'
    with pytest.raises(ValueError):validate_record(ROOT,record,package)

def test_a03_real_immutable_append_and_no_natural_future_engineering_blocker():
    report=read('reports/next_round_r2/scoped_acceptance/INDEPENDENT_READBACK_R2.json')
    assert report['a03']['exact_original_bytes'] and report['a03']['second_append_retry']
    assert report['a03']['new_market_observation_claim'] is False
    original=read(record_path('A03'))
    assert original['current_state']=='ACCUMULATION_CONTINUES'
    assert 'FUTURE_OBSERVATION_COUNT_IS_NOT_ENGINEERING_OPEN_BLOCKER' in original['limitations']
    envelope=read('data/v4/a03_forward_pit_r2/accepted_baseline_capture_envelope.json')
    with pytest.raises(ValueError,match='HISTORICAL_LEDGER'):accepted_forward_append(ROOT,'data/v4/a03_forward_pit_r2',envelope)
    baseline=list((ROOT/'data/v4/a03_scoped_acceptance_r1/accepted_baseline_replay/publications').glob('*.json'))
    before={p:p.read_bytes() for p in baseline}
    changed=deepcopy(envelope);changed['received_at']='2026-10-01T23:59:59+08:00'
    with pytest.raises(ValueError,match='CAPTURE_ID_CONFLICT'):accepted_forward_append(ROOT,'data/v4/a03_scoped_acceptance_r1/accepted_baseline_replay',changed)
    assert before=={p:p.read_bytes() for p in baseline}

def test_a06_accepted_fail_closed_no_threshold_tuning():
    from workbench_analysis.baostock_tolerance_candidate_r2 import validate_policy
    policy=read('config/baostock_binding_tolerance_policy_r2_candidate.json')
    assert all(x['tolerance'] is None for x in policy['fields'].values())
    policy['fields']['amount']['tolerance']='0.01'
    with pytest.raises(ValueError):validate_policy(policy)
    report=read('reports/next_round_r2/scoped_acceptance/INDEPENDENT_READBACK_R2.json')
    assert report['a06']['conflict']['tdx_core_blocked'] is False
    assert report['a06']['conflict']['strict_binding'] is False

def test_a07_exact_capture_time_boundary_and_no_formal_adjusted_consumer():
    capture=read('reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json')['real_capture']
    before=(datetime.fromisoformat(capture['first_available_at'])-timedelta(microseconds=1)).isoformat()
    early=accepted_adjusted_lineage(ROOT,capture,knowledge_time=before)
    after=accepted_adjusted_lineage(ROOT,capture,knowledge_time=capture['first_available_at'])
    assert early['historical_capability']=='PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED'
    assert after['lineage']=='AS_RECORDED' and after['formal_consumer_enabled'] is False
    changed=dict(capture,first_available_at='2026-09-24T00:00:00+08:00',knowledge_time='2026-09-24T00:00:00+08:00')
    assert accepted_adjusted_lineage(ROOT,changed,knowledge_time=changed['knowledge_time'])['lineage']=='RECONSTRUCTED_CORRECTED'

def test_seven_owner_fields_exact_unchanged_inactive_metadata():
    metadata=read(OWNER_PATH)
    assert validate_accepted_owner_metadata(ROOT,metadata)['fields']==7
    assert metadata['owners']==read('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json')['owners']
    assert len(metadata['field_external_dispositions'])==7
    assert metadata['active_global_trust_root'] is False

@pytest.mark.parametrize('fault',['limitation','consumer','scope','active_root','formal_cutover','wrong_active_registry','wrong_candidate_hash'])
def test_accepted_owner_still_rejects_scope_and_activation_changes(fault):
    metadata=read(OWNER_PATH)
    if fault=='limitation':metadata['owners'][0]['known_limitations']=[];metadata['owners'][0]['known_limitations'].append('NEW_VALUE')
    elif fault=='consumer':metadata['owners'][0]['allowed_consumers'].append('V4_11_FORMAL_CONSUMER')
    elif fault=='scope':metadata['owners'][0]['effective_scope']['start_date']='2023-07-04'
    elif fault=='active_root':metadata['active_global_trust_root']=True
    elif fault=='formal_cutover':metadata['permissions']['formal_consumer_cutover']=True
    elif fault=='wrong_active_registry':metadata['active_registry']['path']=OWNER_PATH
    elif fault=='wrong_candidate_hash':metadata['accepted_candidate']['sha256']='0'*64
    with pytest.raises(ValueError):validate_accepted_owner_metadata(ROOT,metadata)

def test_accepted_reader_v2_history_only_and_actual_three_thread_parity():
    assert validate_reader_manifest(ROOT,read(READER_PATH))['production_authorization'] is False
    r=read('reports/next_round_r2/scoped_acceptance/INDEPENDENT_READBACK_R2.json')['reader']
    assert r['distinct_threads']==3 and r['exact_v1_output_parity']
    assert r['current_data_head_date']=='2026-09-30' and r['module_roots_unchanged']
    assert r['concurrent_outputs'][2]['result']['checks']['P19_protected']=='FAIL'
    assert r['wrong_hash_output']['status']=='FAIL'
    assert all(x['status']=='REJECTED' for x in r['negative_cases'])
    with pytest.raises(ValueError):read_accepted_history(ROOT,'V4-12')

@pytest.mark.parametrize('fault',['v1_select','business_scope','production','business_reacceptance','runtime_hash'])
def test_accepted_reader_manifest_never_grants_business_reacceptance(fault):
    manifest=read(READER_PATH)
    if fault=='v1_select':manifest['accepted_reader_version']='v1'
    elif fault=='business_scope':manifest['validation_scope']='CURRENT_BUSINESS_ACCEPTANCE'
    elif fault=='production':manifest['permissions']['production']=True
    elif fault=='business_reacceptance':manifest['business_reacceptance']=True
    elif fault=='runtime_hash':manifest['reader_and_preserved_validator_bindings'][0]['sha256']='0'*64
    with pytest.raises(ValueError):validate_reader_manifest(ROOT,manifest)

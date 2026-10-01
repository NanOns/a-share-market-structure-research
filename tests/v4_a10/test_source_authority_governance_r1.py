from copy import deepcopy
import pytest
from workbench_analysis.source_authority_governance_r1 import (
    SourceRole,Availability,HistoricalMode,AuthorityError,validate_availability,validate_temporal_lineage,evaluate_consumer_gate)

def rule(role='SUPPLEMENTAL_CROSSCHECK',consumers=None):
    authority=role in ('CORE_AUTHORITY','FIELD_AUTHORITY')
    return dict(field_id='status',source_family='SOURCE',role=role,owner_contract_id='OWNER_R1',
        allowed_consumers=consumers or ['STATUS_CONSUMER'],may_block_core=authority,may_change_core_value=authority,
        may_change_core_quality=False,historical_retrieval_mode='TARGET_DATE_QUERYABLE_FACT',pit_requirement='EXPLICIT_KNOWLEDGE_TIME')

def fact():return dict(target_trade_date='2026-09-28',provider_date='2026-09-28',observed_at='2026-10-01T02:00:00Z',
    received_at='2026-10-01T02:00:02Z',origin='DELAYED_HISTORICAL_RETRIEVAL',lineage='RECONSTRUCTED_CORRECTED')

@pytest.mark.parametrize('state',[a.value for a in Availability if a!=Availability.AVAILABLE and a not in
    (Availability.PROVIDER_QUERY_ATTEMPTED_FAILED,Availability.PROVIDER_TARGET_DATE_EMPTY_CONFIRMED,Availability.PROVIDER_SCHEMA_MISMATCH)])
def test_supplemental_missing_never_blocks_or_changes_core(state):
    result=evaluate_consumer_gate(rule(),consumer_contract_id='RAW_DAILY',availability=state,target_trade_date='2026-09-28',core_value=12)
    assert not result['capability_blocked'] and result['core_value']==12 and result['crosscheck']=='UNKNOWN'

def test_supplemental_conflict_retains_core_value_and_quality():
    r=evaluate_consumer_gate(rule(),consumer_contract_id='STATUS_CONSUMER',availability='AVAILABLE',target_trade_date='2026-09-28',core_value='ACTUAL_TRADED',supplemental_value='SUSPENDED')
    assert r['core_value']=='ACTUAL_TRADED' and r['crosscheck']=='CONFLICT' and not r['core_quality_changed']

@pytest.mark.parametrize('permission',['may_block_core','may_change_core_value','may_change_core_quality'])
def test_supplemental_permission_escalation_rejected(permission):
    r=rule();r[permission]=True
    with pytest.raises(AuthorityError):evaluate_consumer_gate(r,consumer_contract_id='RAW_DAILY',availability='AVAILABLE',target_trade_date='2026-09-28')

def test_supplemental_required_dependency_rejected():
    with pytest.raises(AuthorityError,match='SUPPLEMENTAL_MAY_NOT_BLOCK_CORE'):
        evaluate_consumer_gate(rule(),consumer_contract_id='STATUS_CONSUMER',availability='LOCAL_CAPTURE_MISSING',target_trade_date='2026-09-28',required=True)

@pytest.mark.parametrize('state',['PROVIDER_TARGET_DATE_EMPTY_CONFIRMED','PROVIDER_QUERY_ATTEMPTED_FAILED','PROVIDER_SCHEMA_MISMATCH'])
def test_not_queried_cannot_support_provider_conclusion(state):
    with pytest.raises(AuthorityError):validate_availability(state,'2026-09-28')

def test_empty_provider_response_requires_real_exact_target_receipt():
    r=dict(request_count=1,bounded=True,target_trade_date='2026-09-28',provider_date='2026-09-28',observed_at='2026-10-01T02:00Z',
        row_count=0,error_code='0',schema_valid=True,response_sha256='a'*64)
    assert validate_availability('PROVIDER_TARGET_DATE_EMPTY_CONFIRMED','2026-09-28',r)
    r['provider_date']='2026-09-30'
    with pytest.raises(AuthorityError):validate_availability('PROVIDER_TARGET_DATE_EMPTY_CONFIRMED','2026-09-28',r)

def test_catchup_preserves_late_actual_observation():
    f=fact();before=deepcopy(f);assert validate_temporal_lineage(f,'TARGET_DATE_QUERYABLE_FACT');assert f==before

@pytest.mark.parametrize('mutation',[dict(first_available_at='2026-09-28T07:00Z'),dict(AS_RECORDED_AT_CLOSE=True),dict(origin='LIVE_TARGET_DAY'),dict(observed_at='2026-09-27T07:00Z')])
def test_delayed_catchup_cannot_mint_target_knowledge(mutation):
    f=fact();f.update(mutation)
    with pytest.raises(AuthorityError):validate_temporal_lineage(f,'TARGET_DATE_QUERYABLE_FACT')

def test_mutable_snapshot_backdating_and_unproven_pit_rejected():
    f=fact()
    with pytest.raises(AuthorityError):validate_temporal_lineage(f,'MUTABLE_CURRENT_SNAPSHOT')
    f['lineage']='CURRENT_MEMBERSHIP_REPLAY';assert validate_temporal_lineage(f,'MUTABLE_CURRENT_SNAPSHOT')
    with pytest.raises(AuthorityError):validate_temporal_lineage(f,'AS_RECORDED_PIT_FACT')

def test_field_authority_only_blocks_its_declared_capability():
    r=rule('FIELD_AUTHORITY',['ISST','PRICE_LIMIT'])
    blocked=evaluate_consumer_gate(r,consumer_contract_id='ISST',availability='LOCAL_ACCEPTED_ARTIFACT_MISSING',target_trade_date='2026-09-28',required=True)
    unaffected=evaluate_consumer_gate(r,consumer_contract_id='RAW_DAILY',availability='LOCAL_ACCEPTED_ARTIFACT_MISSING',target_trade_date='2026-09-28')
    assert blocked['capability_blocked'] and not blocked['global_core_blocked'] and not unaffected['capability_blocked']
    with pytest.raises(AuthorityError):evaluate_consumer_gate(r,consumer_contract_id='RAW_DAILY',availability='AVAILABLE',target_trade_date='2026-09-28',required=True)

def test_disabled_field_cannot_grant_authority_on_available_provider_data():
    r=rule('FIELD_AUTHORITY');r['enabled']=False
    result=evaluate_consumer_gate(r,consumer_contract_id='STATUS_CONSUMER',availability='AVAILABLE',target_trade_date='2026-09-28',core_value=None,supplemental_value=1,required=True)
    assert result['capability_blocked'] and result['core_value'] is None

def test_structural_scan_detects_contract_escalation_and_no_request_claim():
    from scripts.scan_source_authority_governance_r1 import inspect_file
    import json
    findings=inspect_file('config/input.json',json.dumps(dict(role='SUPPLEMENTAL_CROSSCHECK',required=True,request_count=0,availability='PROVIDER_TARGET_DATE_EMPTY_CONFIRMED')).encode())
    assert {f['category'] for f in findings}=={'C2_SUPPLEMENTAL_PERMISSION_ESCALATION','C1_NOT_QUERIED_AS_CONFIRMED_PROVIDER_EMPTY'}

def test_structural_scan_detects_runtime_time_and_source_gates():
    from scripts.scan_source_authority_governance_r1 import inspect_file
    source=b"REQUIRED_SOURCE_FAMILIES=('BAOSTOCK_DAILY_UPDATE',)\nif now.date().isoformat()!=target_date:\n raise ValueError('BAOSTOCK')\nfact={'observed_at':target_date}\n"
    categories={f['category'] for f in inspect_file('scripts/input.py',source)}
    assert categories=={'C2_SUPPLEMENTAL_IN_GLOBAL_REQUIRED_SOURCE_SET','C3_HISTORICAL_QUERY_SAME_DAY_ONLY_GATE','C4_TARGET_DATE_ASSIGNED_TO_KNOWLEDGE_TIME'}

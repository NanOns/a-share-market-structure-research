"""Independent design expectations; synthetic gates never authorize production."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from reports.r28.design_oracle import CAPS,DEPS,fixture,permissions,proposal,rollback_scope,scenario,vector_result

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/v4_19_focus_source_cutover_contract_v1.json').read_text(encoding='utf8'))


@pytest.mark.parametrize('vector', [f'C{i:02}' for i in range(1,21)])
def test_twenty_independent_design_vectors(vector):
    result=vector_result(vector); p=result['hypothetical_permissions']
    assert result['production_grant'] is False and result['route_changes']==[]
    expected=C['vectors'][int(vector[1:])-1]['expected']
    assert result['design_action']==expected['design_action'] and result['reason']==expected['reason']
    assert p['STOCK_CORE']==expected['stock_core_permission']
    if vector=='C01': assert p['STOCK_CORE'] and result['design_action']=='ELIGIBLE_DESIGN_PROPOSAL'
    if vector in ('C02','C04','C11','C20'):
        assert p['STOCK_CORE'] and not any(p[c] for c in ('SECTOR_STAGE','STOCK_SECTOR_DEPENDENT','ROTATION','SECTOR_RISK_CHANGE'))
    if vector=='C03': assert p['SECTOR_STAGE'] and not p['STOCK_CORE'] and not p['STOCK_SECTOR_DEPENDENT']
    if vector in ('C05','C06','C07','C08','C12','C13','C14','C18','C19'): assert not p['STOCK_CORE'] and result['design_action']=='NO_CUTOVER'
    if vector=='C09': assert result['reason']=='SOURCE_PUBLICATION_IDENTITY_MISMATCH'
    if vector=='C10': assert result['reason']=='ROUTE_CAS_CONFLICT'
    if vector=='C11': assert result['module_labels']['STOCK_CORE']=='PRODUCTION' and result['module_labels']['SECTOR_STAGE']=='SHADOW'
    if vector=='C15': assert result['rollback_affected']==['ROTATION'] and 'pending settlement ownership' in result['rollback_preserves']
    if vector=='C16': assert not any(p.values()) and result['reason']=='GLOBAL_PROMOTION_FORBIDDEN'
    if vector=='C17': assert result['reason']=='RECEIPT_SCHEMA_INCOMPLETE'


@pytest.mark.parametrize('gate,field,value', [('shadow','consecutive_sessions',19),('shadow','missed_sessions',1),('shadow','non_evaluable_sessions',1),('shadow','temporal_leakage',1),('shadow','p0',1),('shadow','rollback_drill',False),('forward','controls_quality_receipt',False),('forward','benchmark_quality_receipt',False),('migration','runtime_external_acceptance',False),('migration','scope','CONTRACT_DESIGN')])
def test_fail_closed_quality_and_runtime_authority(gate,field,value):
    v=fixture(); v['capabilities']['STOCK_CORE'][gate][field]=value
    assert not permissions(v)['STOCK_CORE']


def test_current_all_false_and_no_runtime_interface():
    assert C['policy_id']=='CUTOVER_V2' and C['mode']=='CONTRACT_DESIGN_ONLY'
    assert set(C['current_state']['production_permission'])==set(CAPS)
    assert not any(C['current_state']['production_permission'].values())
    assert C['current_state']['V4_19_ACCEPTED_HEAD']=='NOT_CREATED'
    assert not C['current_state']['focus_source_cutover']
    assert C['implementation_entry']['receipts']==[None]*4
    assert C['implementation_entry']['status']=='BLOCKED_WAIT_REAL_GATES'
    assert not C['cutover_cas']['implemented'] and not C['rollback']['implemented']


def test_contract_graph_registry_and_unfrozen_sector_policy():
    assert C['permission_formula']['dependency_graph']==DEPS
    assert C['permission_formula']['operator']=='AND'
    assert set(C['capability_registry'])==set(CAPS)
    for cap in CAPS:
        row=C['capability_registry'][cap]
        assert row['required_dependencies']==DEPS[cap]
        assert not row['production_permission'] and all(r is None for r in row['accepted_receipts'].values())
        for field in ('shadow_gate','forward_gate','migration_gate','fallback_mode','ui_label','focus_eligibility','rollback_scope'): assert row[field]
    assert all(C['forward_gates'][c]['threshold_receipt'] is None for c in ('sector_stage','rotation','sector_risk_change'))
    assert C['migration_gate']['design_pass_satisfies'] is False


def test_count_diversity_and_revision_dedup():
    v=fixture()
    for row in v['capabilities']['STOCK_CORE']['forward']['events']: row['signal_date']='same_day'
    assert not permissions(v)['STOCK_CORE']
    v=fixture()
    for row in v['capabilities']['STOCK_CORE']['forward']['events']: row['stock_id']='same_stock'
    assert not permissions(v)['STOCK_CORE']
    assert not permissions(scenario('C19'))['STOCK_CORE']


def test_rollback_transitive_dependencies_do_not_disable_stock_core():
    assert rollback_scope('SECTOR_STAGE')==['ROTATION','SECTOR_RISK_CHANGE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT']
    assert rollback_scope('ROTATION')==['ROTATION']


def test_receipt_fields_context_and_prohibitions_complete():
    required={'capability','status','shadow_sessions','unique_signal_dates','matured_events','forward_quality','migration_gate','production_permission','dependency_scope','parameter_digest','model_contract_id','state_lineage_id','source_publication','cutover_authority_id','previous_route','new_route','expected_route_head','receipt_digest'}
    assert set(C['receipt_schema']['required'])==required
    ui=json.loads((ROOT/'config/v4_17_shadow_ui_contract_v1.json').read_text(encoding='utf8'))
    assert C['mixed_ui']['shadow_native_identity_fields']==ui['identity_fields']
    assert not C['mixed_ui']['global_v4_production_label']
    assert 'GLOBAL_V4_PASS' in C['prohibited'] and 'GLOBAL_FOCUS_CUTOVER' in C['prohibited']
    assert [v['id'] for v in C['vectors']]==[f'C{i:02}' for i in range(1,21)]
    for field in C['receipt_schema']['required']+C['receipt_schema']['additional_required']:
        value=fixture(); del value['proposed_receipt'][field]
        assert proposal(value)['reason']=='RECEIPT_SCHEMA_INCOMPLETE'

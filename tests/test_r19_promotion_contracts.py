"""Independent promotion negatives and contract-only oracle mutations."""
from copy import deepcopy
import json
import pytest
from scripts import validate_r19a_promotion as a
from scripts import validate_r19_contracts as v

def test_exact_promotion():assert a.validate()['R19A_V4_14_PROMOTION']=='PASS_LOCAL'

@pytest.mark.parametrize('mutation',['audited','tested','stale_parent','original_v13','missing_rollback','wrong_seal','old_dag','pit','data','production','shadow','focus','runtime','stage_range','stage_prior_field'])
def test_promotion_rejects(mutation):
    h=json.loads((a.ROOT/a.HEAD).read_bytes());s=json.loads((a.ROOT/a.STAGE).read_bytes())
    if mutation=='audited':h['audited_head']='wrong'
    elif mutation=='tested':h['tested_source']='wrong'
    elif mutation=='stale_parent':h['bindings']['parent_stage']['sha256']='0'*64
    elif mutation=='original_v13':h['bindings']['amended_predecessor']['path']='data/v4/V4_13_ACCEPTED_HEAD.json'
    elif mutation=='missing_rollback':h['bindings'].pop('rollback_receipt')
    elif mutation=='wrong_seal':h['bindings']['rollback_complete_seal']['sha256']='0'*64
    elif mutation=='old_dag':h['bindings']['canonical_full_dag_r5']['path']='reports/v4_14_replay_r18/full_dag/completion_gate.json'
    elif mutation=='pit':h['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    elif mutation=='data':h['bindings']['data_head']['sha256']='0'*64
    elif mutation=='runtime':h['V4_15_runtime']=True
    elif mutation=='stage_range':s['accepted_stage_range']='V4_00_TO_V4_15_ACCEPTED'
    elif mutation=='stage_prior_field':s['v4_12_status']='FULL_PASS'
    else:h[mutation]=True
    with pytest.raises(ValueError):a.validate(h,s)

def test_B_contracts():assert v.check_b()['RADAR_COHORT_CONTRACT_COMPLETENESS']=='PASS_LOCAL'
def test_C_contracts():assert v.check_c()['SETTLEMENT_CONTRACT_COMPLETENESS']=='PASS_LOCAL'
def test_D_contracts():assert v.check_d()['V4_15_CONTRACT_COMPLETENESS']=='PASS_READY_FOR_EXTERNAL_AUDIT'

@pytest.mark.parametrize('name,key,value',[
    ('radar_contract','owner_recomputation',True),('radar_contract','complete_ledger',False),
    ('radar_event_registry','persistent_creates_event',True),('radar_event_registry','stock_warm','SYNTHESIZED'),
    ('cohort_contract','ignore_selection',[]),('cohort_contract','exited_invalidated_continue_settlement',False),
    ('why_now_schema','qualification_effect',True),('conflict_hypothesis_schema','fabricate_second_story',True),
    ('due_planner_contract','horizons',[1,5]),('due_planner_contract','endpoint_suspension_shift',True),
    ('forward_price_path_contract','T0_intraday_extrema_included',True),('forward_price_path_contract','common_basis_required',False),
    ('outcome_status_contract','no_terminal_return',0),('outcome_status_contract','states',['RIGHT_CENSORED']),
    ('competing_outcome_contract','price_settlement_continues',False),('competing_outcome_contract','right_censored_is_event',True),
    ('forward_market_benchmark_contract','reweight',True),('forward_market_benchmark_contract','consumer_isolation',False),
    ('forward_sector_benchmark_contract','exclude_signal_stock',False),('rotation_pulse_basket_contract','members','FUTURE_MEMBERS'),
    ('control_assignment_contract','future_refill',True),('control_assignment_contract','assignments_immutable',False),
    ('settlement_revision_contract','overwrite_signal_enrollment',True),('settlement_readback_contract','selection_independent',False),
    ('quality_degradation','marked_coverage_gate',.95),('quality_degradation','marked_quote_age_gate',3),
    ('storage_schema_design','migration_apply',True),('contract_package','runtime_implemented',True),
    ('contract_package','HISTORICAL_PIT_EFFECTIVENESS','PASS')])
def test_semantic_mutation_rejected(name,key,value):
    obj=deepcopy(v.load(name));obj[key]=value
    checker=v.check_b if name in v.B_NAMES else v.check_c if name in v.C_NAMES else v.check_d
    with pytest.raises(ValueError):checker({name:obj})

@pytest.mark.parametrize('name',['radar_cohort_machine_vectors','settlement_machine_vectors','machine_vectors'])
def test_mutated_static_expected_rejected(name):
    obj=deepcopy(v.load(name));vectors=obj['cross_family_vectors' if name=='machine_vectors' else 'vectors'];vectors[0]['expected']={'forged':True}
    with pytest.raises(ValueError):v.check_d({name:obj},verify_bindings=False)

def test_duplicate_authority_is_P0():
    obj=deepcopy(v.load('field_registry'));obj['registry'].append(obj['registry'][0])
    with pytest.raises(ValueError,match='UNION_AUTHORITY_P0'):v.check_d({'field_registry':obj},verify_bindings=False)

def test_self_consistent_missing_field_is_not_complete():
    contract=deepcopy(v.load('outcome_status_contract'));contract['fields'].remove('terminal_evidence')
    registry=deepcopy(v.load('settlement_field_registry'));registry['registry']=[f for f in registry['registry'] if f['field_id']!='terminal_evidence']
    with pytest.raises(ValueError,match='INDEPENDENT_REQUIRED_SCHEMA'):v.check_c({'outcome_status_contract':contract,'settlement_field_registry':registry})

@pytest.mark.parametrize('edge',v.NONEDGES)
def test_forbidden_edge_cannot_be_added(edge):
    obj=deepcopy(v.load('dag_registry'));obj['edges'].append(dict(source=edge[0],target=edge[1]))
    with pytest.raises(ValueError,match='EXACT_DAG_ACYCLIC'):v.check_d({'dag_registry':obj},verify_bindings=False)

def test_missing_nonedge_rejected():
    obj=deepcopy(v.load('dag_registry'));obj['non_edges'].pop()
    with pytest.raises(ValueError,match='NON_EDGES'):v.check_d({'dag_registry':obj},verify_bindings=False)

def test_benchmark_thresholds_remain_unset():
    obj=deepcopy(v.load('forward_market_benchmark_contract'));obj['marked_estimate']['coverage_gate_value']=.99
    with pytest.raises(ValueError,match='NO_THRESHOLD_INVENTION'):v.check_c({'forward_market_benchmark_contract':obj})

def test_independent_oracles_have_no_writer_or_runtime_dependency():
    for path in ['scripts/validate_r19a_promotion.py','scripts/validate_r19_contracts.py']:
        text=(a.ROOT/path).read_text()
        assert 'import scripts.r19a_promote' not in text and 'from scripts.r19a_promote' not in text
        assert 'r19_freeze_contracts import' not in text and 'r19d_integrate import' not in text
        assert 'v4_15_runtime' not in text

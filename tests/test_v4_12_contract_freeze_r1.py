"""Freeze validation, independently authored vectors and negative contract checks."""
from copy import deepcopy
import ast
import json
import subprocess
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, ValidationError
from scripts.validate_v4_12_contract_freeze_r1 import (
    load_configs, literal_audit, dag_audit, schema_registry_audit, vector_oracle,
    FixtureExpressionVerifier, UNKNOWN, validate, validate_envelope_fixture)
from scripts.v4_12_independent_vector_oracle_r1 import vectors

CONFIG=load_configs()

@pytest.mark.parametrize('vector',vectors(),ids=lambda v:v['vector_id'])
def test_independent_contract_vector(vector):
    result=vector_oracle(CONFIG)
    assert next(v for v in result['vectors'] if v['vector_id']==vector['vector_id'])['status']=='PASS'

def test_literal_parameters_and_statuses():
    assert literal_audit(CONFIG)['unbound_literal_count']==0

def test_unbound_literal_rejected():
    bad=deepcopy(CONFIG);bad['machine_ast']['definitions']['close_breach']['args'][1]=.5
    with pytest.raises(AssertionError,match='UNBOUND_AST_LITERAL'):literal_audit(bad)

def test_unregistered_parameter_rejected():
    bad=deepcopy(CONFIG);bad['machine_ast']['definitions']['close_breach']['args'][1]={'parameter_id':'unregistered'}
    with pytest.raises(AssertionError,match='UNREGISTERED_PARAMETER'):literal_audit(bad)

def test_probability_claim_rejected():
    bad=deepcopy(CONFIG);bad['parameter_set']['parameters'][0]['profitability_validated']=True
    with pytest.raises(AssertionError):literal_audit(bad)

def test_downstream_input_rejected():
    bad=deepcopy(CONFIG);bad['machine_ast']['definitions']['close_breach']={'field':'D2_final_eligibility'}
    with pytest.raises(AssertionError):dag_audit(bad)

def test_same_day_anchor_dependency_rejected():
    bad=deepcopy(CONFIG)
    next(r for r in bad['field_registry']['fields'] if r['field']=='prior_support_state')['time_role']='T'
    with pytest.raises(AssertionError):dag_audit(bad)

def test_coefficients_cannot_replace_basis_identity():
    bad=deepcopy(CONFIG);bad['anchor_coordinate_contract']['basis_identity']=['qfq_mul','qfq_add']
    with pytest.raises(AssertionError):dag_audit(bad)

def test_ast_dependency_cycle_rejected():
    bad=deepcopy(CONFIG);bad['machine_ast']['definitions']['touch']={'field':'touch'}
    with pytest.raises(AssertionError,match='AST_DEFINITION_CYCLE'):dag_audit(bad)

def test_unknown_owner_not_reconstructed_or_skipped():
    env={**CONFIG['machine_vectors']['defaults'],'C':11,'MA20':10,'delta3':10,'prior_delta3':0,'rel_market_1':1,'ret1':1}
    assert FixtureExpressionVerifier(CONFIG,env).target('recovery') is UNKNOWN

def test_unknown_session_resets_breach_and_hold_counts():
    env={**CONFIG['machine_vectors']['defaults'],'evaluable':False,'prior_breach_count':1,'prior_held_count':1}
    verifier=FixtureExpressionVerifier(CONFIG,env)
    assert verifier.target('breach_count')==0
    assert verifier.target('held_count')==0
    assert verifier.target('support')=='UNKNOWN'

def test_d2_focus_ui_perturbations_leave_d1_expression_unchanged():
    env={**CONFIG['machine_vectors']['defaults'],'C':11,'prior_high20':10,'ATR20':2}
    baseline=FixtureExpressionVerifier(CONFIG,env).target('breakout')
    for value in ('CONFIRMED','INVALIDATED',None,{'future_return':100}):
        changed={**env,'D2':value,'Focus':value,'UI':value,'same_day_Final_State':value}
        assert FixtureExpressionVerifier(CONFIG,changed).target('breakout')==baseline

def test_oracle_does_not_import_ast_or_implementation_helpers():
    path=Path(__file__).resolve().parents[1]/'scripts/v4_12_independent_vector_oracle_r1.py'
    tree=ast.parse(path.read_text(encoding='utf8'))
    allowed={'decimal','scripts.record_r7_stage_contract','scripts.v4_11_promotion_contract_r1'}
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):assert node.module in allowed
        assert not isinstance(node,ast.Import)

def test_tampered_expected_rejected():
    bad=deepcopy(CONFIG);bad['machine_vectors']['vectors'][0]['expected']='BREAKOUT_ACCEPTED'
    with pytest.raises(AssertionError,match='INDEPENDENT_ORACLE_BOOK_MISMATCH'):vector_oracle(bad)

def test_producer_registry_complete():
    assert schema_registry_audit(CONFIG)['status']=='PASS'

def test_unregistered_producer_rejected():
    bad=deepcopy(CONFIG);bad['producer_registry']['producers'].pop()
    with pytest.raises(AssertionError,match='UNREGISTERED_PRODUCER'):schema_registry_audit(bad)

def envelope(field='C'):
    row=next(r for r in CONFIG['field_registry']['fields'] if r['field']==field)
    return dict(contract_id='V4_12_INPUT_V1',parameter_set_digest='0'*64,observation_trade_date='2026-10-02',
        cutoff='2026-10-02T15:00:00Z',security_id='SYNTHETIC',inputs={field:dict(value=10,quality='KNOWN',unknown_reason=None,
        producer_contract_id=row['producer_contract_id'],publication_id='SYNTHETIC_NOT_ACCEPTED',publication_digest='0'*64,
        trade_date='2026-10-01' if row['time_role']=='T_MINUS_1' else '2026-10-02',available_at='2026-10-02T14:00:00Z',
        source_namespace=row['source_namespace'],time_role=row['time_role'],output_digest='0'*64,price_basis='QFQ',adjustment_source_revision='SYNTHETIC_r1')})

def test_input_metadata_schema_accepts_explicit_fixture():
    assert validate_envelope_fixture(CONFIG,envelope())=='PASS_METADATA_ONLY_NO_RUNTIME_SOURCE_ACCEPTANCE'

def test_future_input_metadata_rejected():
    data=envelope();data['inputs']['C']['available_at']='2026-10-03T00:00:00Z'
    with pytest.raises(ValueError,match='FUTURE_SOURCE'):validate_envelope_fixture(CONFIG,data)

def test_same_day_prior_anchor_rejected():
    data=envelope('lo');data['inputs']['lo']['trade_date']='2026-10-02'
    with pytest.raises(ValueError,match='SAME_DAY_ANCHOR'):validate_envelope_fixture(CONFIG,data)

def test_missing_owner_cannot_be_forged_known():
    data=envelope('close_t_minus_1')
    with pytest.raises(ValueError,match='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'):validate_envelope_fixture(CONFIG,data)

def test_unknown_reason_required():
    data=envelope();data['inputs']['C']['quality']='UNKNOWN';data['inputs']['C']['value']=None
    with pytest.raises(ValueError,match='UNKNOWN_REASON_REQUIRED'):validate_envelope_fixture(CONFIG,data)

def test_wrong_registered_type_rejected():
    data=envelope();data['inputs']['C']['value']='10'
    with pytest.raises(ValueError,match='FIELD_TYPE'):validate_envelope_fixture(CONFIG,data)

def test_downstream_namespace_rejected():
    data=envelope();data['inputs']['C']['source_namespace']='D2'
    with pytest.raises(ValueError,match='NAMESPACE'):validate_envelope_fixture(CONFIG,data)

def test_external_support_today_input_rejected():
    data=envelope();data['inputs']['support_today']=deepcopy(data['inputs']['C'])
    with pytest.raises(ValidationError):validate_envelope_fixture(CONFIG,data)

def test_anchor_schema_complete_machine_types():
    schema=CONFIG['anchor_schema']['schema'];Draft202012Validator.check_schema(schema)
    assert set(schema['required'])==set(schema['properties'])
    invalid={k:None for k in schema['required']}
    with pytest.raises(ValidationError):Draft202012Validator(schema).validate(invalid)

def test_candidate_only_scope_and_protected_heads():
    result=validate()
    assert result['status']=='V4_12_R1_CONTRACT_FREEZE_CANDIDATE_READY_FOR_EXTERNAL_AUDIT'
    assert not result['runtime_implemented'] and not result['runtime_authorized']
    assert all(r['byte_identical'] for r in result['scope_proof']['protected_artifacts'])
    assert not any(result['permissions'].values())

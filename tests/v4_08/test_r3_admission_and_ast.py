import json
from pathlib import Path
import pytest
from sector.membership_admission_r3 import basis_chain_valid,basis_quality_compatible,active_identity_reason,formal_membership_eligible_r3
from sector.machine_ast_r3 import validate_ast,evaluate_ast,ast_digest
from sector.v4_08_rotation_vectors import evaluate_rotation_vector
ROOT=Path(__file__).resolve().parents[2]

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))

def test_B07_accepted_looking_current_revision_is_rejected():
    assert not basis_quality_compatible('CURRENT_TDX_MEMBERSHIP','PIT_OBSERVED_ACCEPTED')
    assert not basis_chain_valid({'membership_basis':'CURRENT_TDX_MEMBERSHIP','revision_quality':'PIT_OBSERVED_ACCEPTED'},{'membership_basis':'PIT_OBSERVED','membership_quality':'PIT_OBSERVED_ACCEPTED'},{'membership_basis':'PIT_OBSERVED','membership_quality':'PIT_OBSERVED_ACCEPTED'})

@pytest.mark.parametrize('quality,basis',[('PIT_OBSERVED_ACCEPTED','PIT_OBSERVED'),('CURRENT_TDX_DIAGNOSTIC','CURRENT_TDX_MEMBERSHIP'),('CURRENT_REPLAY_DIAGNOSTIC','CURRENT_MEMBERSHIP_REPLAY'),('DERIVED_PARENT_DIAGNOSTIC','DERIVED_PARENT_MEMBERSHIP')])
def test_basis_compatible_pairs(quality,basis):
    assert basis_quality_compatible(basis,quality)
    assert not basis_quality_compatible('DERIVED_PARENT_MEMBERSHIP' if basis!='DERIVED_PARENT_MEMBERSHIP' else 'PIT_OBSERVED',quality)

@pytest.mark.parametrize('change,reason',[({'list_date':'2026-10-09'},'NOT_LISTED_AT_TARGET'),({'delist_date':'2026-09-29'},'DELISTED_AT_TARGET'),({'security_type':'ETF'},'NON_EQUITY'),({'board':'BEIJING'},'OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE'),({'system_available_at':'2026-09-30T10:00Z'},'IDENTITY_UNAVAILABLE_AT_CUTOFF')])
def test_active_universe_exclusions(change,reason):
    identity={'security_id':'SEC-A','list_date':'2026-09-29','delist_date':None,'security_type':'A_STOCK','board':'CHINEXT',**change}
    assert active_identity_reason(identity,'2026-09-30','2026-09-30T09:00Z')==reason

def test_formal_eligibility_never_self_promotes_incremental_identity():
    row={'sector_type':'THEME','membership_basis':'PIT_OBSERVED','snapshot_membership_basis':'PIT_OBSERVED','source_revision_membership_basis':'PIT_OBSERVED','membership_quality':'PIT_OBSERVED_ACCEPTED','snapshot_membership_quality':'PIT_OBSERVED_ACCEPTED','source_revision_quality':'PIT_OBSERVED_ACCEPTED','pit_observed':True,'historical_backtest_safe':True,'security_id':'SEC-A','identity_status':'MAPPED','source_revision_chain_valid':True,'provider_available_at':'2026-09-30T01:00Z','system_available_at':'2026-09-30T01:01Z','observed_at':'2026-09-30T01:00Z','cutoff':'2026-09-30T02:00Z','target_trade_date':'2026-09-30','membership_asof_date':'2026-09-30'}
    identity={'security_id':'SEC-A','list_date':'2026-09-29','security_type':'A_STOCK','board':'CHINEXT','acceptance':'CANDIDATE_PENDING_EXTERNAL_PROMOTION'}
    assert not formal_membership_eligible_r3(row,identity)
    assert formal_membership_eligible_r3(row,{**identity,'acceptance':'ACCEPTED'})
    assert not formal_membership_eligible_r3({**row,'source_revision_membership_basis':'CURRENT_TDX_MEMBERSHIP'},{**identity,'acceptance':'ACCEPTED'})
    assert not formal_membership_eligible_r3({**row,'observed_at':'2026-09-29T01:00Z'},{**identity,'acceptance':'ACCEPTED'})

@pytest.mark.parametrize('filename',['v4_08_sector_prewatch_contract_v2.json','v4_08_rotation_core_contract_v2.json'])
def test_machine_ast_is_fully_bound_and_serializable(filename):
    import hashlib
    doc=read('config/'+filename)
    registry=read(doc['field_registry_path']);fields={x['field_id']:x for x in registry['fields']}
    parameters={x['parameter_id']:x['value'] for x in read('config/v4_08_algorithm_parameter_set_v1.json')['parameters']}
    assert validate_ast(doc['rules'],fields,parameters)['status']=='PASS'
    assert doc['ast_digest']==ast_digest(doc['rules'])
    assert doc['field_registry_digest']==hashlib.sha256((ROOT/doc['field_registry_path']).read_bytes()).hexdigest()
    assert doc['machine_vector_set_digest']==hashlib.sha256((ROOT/doc['machine_vector_set_path']).read_bytes()).hexdigest()
    assert not doc['formal_consumer_enabled']

@pytest.mark.parametrize('vector_id',['R1A','R1B','R2','R3'])
def test_independent_rotation_R1A_R1B_R2_R3_vectors(vector_id):
    vector=next(x for x in read('config/v4_08_rotation_machine_vectors_v2.json')['vectors'] if x['id']==vector_id)
    result=evaluate_rotation_vector(vector['scenario'])
    assert {k:result[k] for k in vector['expected']}==vector['expected']
    assert not result['production_authorized']
    for forbidden in ['Focus','Radar','V4_06_turnover','future_outcome','same_day_final_stock_prewatch']:
        assert evaluate_rotation_vector({**vector['scenario'],forbidden:'mutated'})==result

def test_ast_unknown_quality_and_unfrozen_parameters_remain_unknown():
    doc=read('config/v4_08_rotation_core_contract_v2.json');rules=doc['rules']
    registry=read(doc['field_registry_path']);fields={x['field_id']:x for x in registry['fields']}
    params={x['parameter_id']:x['value'] for x in read('config/v4_08_algorithm_parameter_set_v1.json')['parameters']}
    facts={k:{'value':0.8,'quality':'ACCEPTED','producer':v['producer'],'time_role':v['time_role']} for k,v in fields.items()}
    assert evaluate_ast('early_retained',rules,facts,params) is None
    assert len([k for k,v in params.items() if v is None])==5
    facts['strong_prev']['value']=0
    assert evaluate_ast('mature_retained',rules,facts,params) is False

def test_boolean_AST_preserves_valid_OR_and_unknown_AND():
    leaf={'field_id':'x','operator':'GTE','constant':1,'producer':'Core','time_role':'TARGET_CUTOFF','quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'}
    rules={'or':{'operator':'OR','children':[leaf,{**leaf,'field_id':'missing'}]},'and':{'operator':'AND','children':[leaf,{**leaf,'field_id':'missing'}]}}
    facts={'x':{'value':2,'producer':'Core','time_role':'TARGET_CUTOFF','quality':'ACCEPTED'}}
    assert evaluate_ast('or',rules,facts,{}) is True
    assert evaluate_ast('and',rules,facts,{}) is None
    facts['x']['producer']='Focus'
    assert evaluate_ast('or',rules,facts,{}) is None

@pytest.mark.parametrize('exchange',['SH','SZ'])
def test_accepted_MAIN_board_normalization_uses_exchange_contract(exchange):
    assert active_identity_reason({'security_id':'SEC-A','list_date':'2020-01-01','board':'MAIN','exchange':exchange,'security_type':'A_STOCK'},'2026-09-30','2026-09-30T09:00Z') is None

@pytest.mark.parametrize('vector_id',['R1A','R1B','R2','R3'])
def test_canonical_AST_state_qualifications_with_frozen_synthetic_predicate_premises(vector_id):
    doc=read('config/v4_08_rotation_core_contract_v2.json')
    fields={x['field_id']:x for x in read(doc['field_registry_path'])['fields']}
    vector=next(x for x in read('config/v4_08_rotation_machine_vectors_v2.json')['vectors'] if x['id']==vector_id)
    scenario=vector['scenario'];pure=evaluate_rotation_vector(scenario)
    # Only the early-retention premise is supplied by this independent synthetic
    # vector. Pending runtime parameter values are never substituted.
    field=fields['early_retained']
    rules={**doc['rules'],'early_retained':{'operator':'EQ','field_id':'early_retained','constant':True,'producer':field['producer'],'time_role':field['time_role'],'quality_requirement':['ACCEPTED'],'unknown_behavior':'UNKNOWN'}}
    values={'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':scenario['pulse'],'pulse_age_sessions':scenario['pulse_age_sessions'],'early_retained':pure['early_retained'],'strong_prev':scenario['strong_prev'],'prior_rotation_state':scenario.get('prior_state'),'breadth_delta1':scenario.get('breadth_delta1',0.06),'top1_concentration':0.2,'net_entered_count':1,'dq5':12 if scenario['pulse'] else 0,'yesterday_dq5':-1}
    facts={k:{'value':v,'producer':fields[k]['producer'],'time_role':fields[k]['time_role'],'quality':'ACCEPTED'} for k,v in values.items()}
    params={x['parameter_id']:x['value'] for x in read('config/v4_08_algorithm_parameter_set_v1.json')['parameters']}
    mapping={'rotation_in_possible':'ROTATION_IN','rotation_accepted_possible':'ROTATION_ACCEPTED','rotation_expanding_allowed':'ROTATION_EXPANDING','rotation_reaccelerating_allowed':'ROTATION_REACCELERATING'}
    for output,rule in mapping.items():assert evaluate_ast(rule,rules,facts,params)==vector['expected'][output]

@pytest.mark.parametrize('rule,values,expected',[
    ('ROTATION_FAILED',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':True,'pulse_age_sessions':2,'basket_cumulative_return':-0.01,'breadth_delta1':-0.06},True),
    ('ROTATION_FAILED',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':True,'pulse_age_sessions':6,'basket_cumulative_return':-0.01,'breadth_delta1':-0.06},False),
    ('ROTATION_OUT',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'prior_maturity_state':'WARM','negative_out_consecutive_evaluable_sessions':2},True),
    ('UNACCEPTED_EPISODE_EXPIRED',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':True,'pulse_age_sessions':6,'episode_accepted':False},True),
    ('UNACCEPTED_EPISODE_EXPIRED',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':True,'pulse_age_sessions':6,'episode_accepted':True},False),
    ('NO_ACTIVE_EPISODE',{'membership_ready':True,'sector_member_count':8,'sector_quote_coverage':0.9,'pulse_active':False},True),
])
def test_terminal_and_fallback_machine_predicates(rule,values,expected):
    doc=read('config/v4_08_rotation_core_contract_v2.json')
    fields={x['field_id']:x for x in read(doc['field_registry_path'])['fields']}
    facts={k:{'value':v,'producer':fields[k]['producer'],'time_role':fields[k]['time_role'],'quality':'ACCEPTED'} for k,v in values.items()}
    params={x['parameter_id']:x['value'] for x in read('config/v4_08_algorithm_parameter_set_v1.json')['parameters']}
    assert evaluate_ast(rule,doc['rules'],facts,params)==expected

"""R9 independent sequence, counter separation and compatibility rejection gates."""
from copy import deepcopy
import pytest
from scripts.validate_v4_12_contract_freeze_r1 import load_configs
from scripts.validate_v4_12_time_counter_r2_1 import (sequence_actual,time_audit,ast_diff,authority_keep,dimensions,compatible,validate)
from scripts.v4_12_time_counter_oracle_r2_1 import sequence_book,compatibility_vectors

@pytest.mark.parametrize('sequence',sequence_book(),ids=lambda s:s['id'])
def test_independent_sequence(sequence):
    rows=sequence_actual(load_configs(),sequence)
    assert all(r['status']=='PASS' for r in rows)
    for row in rows:
        if row['id'].startswith('C06_'):assert row['counter_baseline_date']<row['date']

@pytest.mark.parametrize('vector',compatibility_vectors(),ids=lambda v:v['id'])
def test_independent_time_domain_vector(vector):
    _,_,fields,parameters=dimensions(load_configs())
    assert compatible(fields[vector['field']],parameters[vector['parameter']])[0] is vector['expected']

def test_missing_breaks_consecutive_not_cumulative():
    sequence=next(s for s in sequence_book() if s['id']=='C08_hold_missing_resume_chain_reset')
    rows={r['id']:r for r in sequence_actual(load_configs(),sequence)}
    assert rows['C08_missing']['preserved_support_state']=='RECLAIMED'
    assert rows['C08_missing']['actual']['evaluable_count']==1
    assert rows['C08_missing']['actual']['held_count']==0
    assert rows['C08_resume']['actual']['held_count']==1
    assert rows['C08_resume']['actual']['evaluable_count']==2

def test_market_age_cannot_replace_pending_count():
    cfg=load_configs();cfg['machine_ast']['machines']['acceptance']['rules'][3]['when']['args'][0]['field']='post_creation_market_sessions'
    assert time_audit(cfg)['incompatible_edges']==1
    with pytest.raises(AssertionError,match='UNAUTHORIZED_AST_CHANGE'):ast_diff(cfg)

def test_evaluable_count_cannot_replace_old_anchor():
    cfg=load_configs();cfg['machine_ast']['definitions']['old_anchor']['args'][0]['field']='post_creation_evaluable_sessions'
    assert time_audit(cfg)['incompatible_edges']==1
    with pytest.raises(AssertionError):ast_diff(cfg)

def test_unit_strings_cannot_hide_wrong_dimension():
    cfg=load_configs();row=next(r for r in cfg['field_registry']['fields'] if r['field']=='post_creation_market_sessions')
    row['unit']='evaluable_sessions'
    _,_,fields,params=dimensions(cfg)
    assert compatible(fields['post_creation_market_sessions'],params['acceptance_consecutive_sessions'])[0] is False

def test_authority_cannot_be_changed_by_time_repair():
    cfg=load_configs();next(r for r in cfg['field_registry']['fields'] if r['field']=='delta3')['producer_contract_id']='CORE_FACTOR_V1'
    with pytest.raises(AssertionError,match='R2_ACCEPTED_OR_BLOCKED_AUTHORITY_CHANGED'):authority_keep(cfg)

def test_full_contract_time_gate():
    result=validate()
    assert result['time_domain_compatibility']['incompatible_edges']==0
    assert result['authority_keep']['status']=='PASS_KEEP'
    assert result['AST_diff']['retention_formula_unchanged']

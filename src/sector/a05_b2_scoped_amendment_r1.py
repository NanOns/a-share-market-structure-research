"""Scoped B2 provenance amendment using unchanged accepted legacy rule AST."""
from copy import deepcopy
from sector.legacy_b2_r5 import evaluate_b2
from sector.machine_ast_r3 import evaluate_ast_explain

def evaluate_current_snapshot(values, ast, *, source_sha256,source_parameter_sha256,parameter_set_sha256,exact_snapshot_scope):
    if exact_snapshot_scope.get('accepted_time_role')!='CURRENT_SNAPSHOT_ONLY' or exact_snapshot_scope.get('target')!=exact_snapshot_scope.get('accepted_snapshot_trade_date'):
        raise ValueError('A05_B2_CURRENT_SNAPSHOT_SCOPE_REQUIRED')
    old=evaluate_b2(values,ast,source_sha256=source_sha256,source_parameter_sha256=source_parameter_sha256,parameter_set_sha256=parameter_set_sha256)
    new=deepcopy(old)
    fact=values.get('normal_rank_eligible',{})
    if fact.get('quality')!='ACCEPTED' or fact.get('value') is None:
        return new
    # Only the former absent-producer override is released. The exact old
    # confirmed_raw rule, semantic exclusion and full-market quality gates remain.
    state=old['confirmed_diagnostic'];new['confirmed_raw']=state
    new['confirmed_reason']='A05_EXACT_CURRENT_SNAPSHOT_PRODUCER_BOUND' if state!='UNKNOWN' else 'OTHER_REQUIRED_B2_FACTS_UNKNOWN'
    new['predicates']['confirmed_raw']=dict(state=state,reason_code=new['confirmed_reason'])
    new['capabilities']['B2_NON_AMOUNT_A']='EXACT_CURRENT_SNAPSHOT_PRODUCER_BOUND_CANDIDATE'
    new['accepted_scope']='CURRENT_SNAPSHOT_ONLY'
    new['historical_PIT_equivalent']=False
    return new

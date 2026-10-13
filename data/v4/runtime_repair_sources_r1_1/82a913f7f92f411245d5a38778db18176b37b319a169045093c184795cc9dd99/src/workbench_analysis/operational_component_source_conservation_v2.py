"""Explicit single-function math correction over the original 604-source scope."""
import ast,json
from .r43_owner_replay import checked

CONTRACT='V4_EXACT_COMPONENT_SOURCE_CONSERVATION_WITH_PROFILE_CORRECTION_R2'
KEY='component_source_conservation'
PROFILE='src/v4/profile_core.py'

def ast_conservation(before,after):
    a=ast.parse(before);b=ast.parse(after)
    old=[n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='extension_risk']
    new=[n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='extension_risk']
    if len(old)!=1 or len(new)!=1:raise ValueError('SINGLE_PROFILE_EXTENSION_FUNCTION_REQUIRED')
    a.body.remove(old[0]);b.body.remove(new[0])
    if ast.dump(a)!=ast.dump(b):raise ValueError('PROFILE_OTHER_NUMERICAL_SOURCE_CHANGED')
    if ast.dump(old[0])==ast.dump(new[0]):raise ValueError('PROFILE_CORRECTION_SOURCE_CHANGE_REQUIRED')

def verify(root,candidate,policy):
    receipt=json.loads(checked(root,candidate[KEY]).read_bytes())
    if receipt.get('contract_id')!=CONTRACT or receipt.get('acceptance')!='PASS_COMPONENT_CONSERVATION_AND_BOUNDED_PROFILE_CORRECTION':raise ValueError('COMPONENT_CONSERVATION_RECEIPT_REQUIRED')
    checkpoint=json.loads(checked(root,receipt['original_checkpoint']).read_bytes())
    old={b['path']:b for b in checkpoint['unchanged_component_sources']};current={b['module_path']:b for b in policy['component_source_bindings']}
    if len(old)!=604 or set(old)!=set(current) or len(current)!=len(policy['component_source_bindings']):raise ValueError('COMPLETE_ORIGINAL_COMPONENT_SCOPE_REQUIRED')
    changed=[name for name in old if old[name]['sha256']!=current[name]['sha256']]
    if changed!=[PROFILE]:raise ValueError('ONLY_DECLARED_PROFILE_MATH_CORRECTION_ALLOWED')
    for binding in current.values():checked(root,binding)
    if receipt['current_component_bindings']!=policy['component_source_bindings'] or receipt['original_profile_source']['sha256']!=old[PROFILE]['sha256']:raise ValueError('COMPONENT_RECEIPT_SOURCE_CONTEXT_MISMATCH')
    ast_conservation(checked(root,receipt['original_profile_source']).read_text('utf8'),checked(root,current[PROFILE]).read_text('utf8'))
    from workbench_db.v4_profile_semantic_corrections_pg_v1 import load
    authority=load(root,candidate)
    if candidate['native_profile_semantic_corrections']!=receipt['profile_correction_authority'] or any(e['producing_source']['sha256']!=current[PROFILE]['sha256'] for e in authority['dates'].values()):raise ValueError('CORRECTION_PRODUCER_SOURCE_BINDING_REQUIRED')
    if sum(len(e['security_ids']) for e in authority['dates'].values())!=27:raise ValueError('FULL_BOUNDED_PROFILE_CORRECTION_SCOPE_REQUIRED')
    source_candidate=json.loads(checked(root,receipt['input_candidate']).read_bytes())
    for key in ('owners','source_registry','membership_snapshot','day_receipt','exact_daily_generation_scope','accepted_trade_date','dates','native_profile_semantic_corrections','native_profile_dependent_corrections'):
        if candidate.get(key)!=source_candidate.get(key):raise ValueError('COMPONENT_CORRECTION_INPUT_CONSERVATION_REQUIRED:'+key)
    for name in ('profile_changed_function_oracle','d2_branch_oracle','forward_branch_conservation','native_dependent_consumers'):
        evidence=json.loads(checked(root,receipt[name]).read_bytes())
        expected={'profile_changed_function_oracle':'PASS_CHANGED_FUNCTION_ONLY','d2_branch_oracle':'PASS_CHANGED_INPUT_BRANCH_SCOPE','forward_branch_conservation':'PASS_AFFECTED_BRANCH_CONSERVATION_ONLY','native_dependent_consumers':'PASS_CHANGED_DEPENDENCIES_ONLY'}[name]
        if evidence.get('acceptance')!=expected or evidence.get('errors'):raise ValueError('BOUNDED_CORRECTION_EVIDENCE_FAILED:'+name)
        if name=='profile_changed_function_oracle' and evidence['source']['sha256']!=current[PROFILE]['sha256']:raise ValueError('INDEPENDENT_ORACLE_SOURCE_MISMATCH')
        if 'candidate' in evidence:
            bound=json.loads(checked(root,evidence['candidate']).read_bytes())
            for key in ('owners','source_registry','membership_snapshot','day_receipt','exact_daily_generation_scope','accepted_trade_date','dates'):
                if bound.get(key)!=candidate.get(key):raise ValueError('BOUNDED_CORRECTION_ORACLE_INPUT_MISMATCH:'+name+':'+key)
    return receipt

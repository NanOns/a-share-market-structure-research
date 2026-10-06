"""Exact V4 audit successor admission; a blocker decision never grants permission."""
import json
from pathlib import Path
from scripts.v4_16_shadow_runtime import check,exact
from scripts.v4_16_capability_resolution import resolve as historical_resolve,FIELDS

def resolve(contract,head,requested):
    check(contract['contract_id']=='V4_16_RUNTIME_CAPABILITY_RESOLUTION_V2','SUCCESSOR_RESOLVER_REQUIRED')
    check(head['contract_id']=='V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4','STALE_CURRENT_AUDIT_HEAD')
    check(contract['current_audit_head']['path']=='data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json','STALE_CURRENT_AUDIT_HEAD')
    a08=head['entries']['A08_CURRENT_RUNTIME']
    check(a08['current_state']=='ACCEPTED_SCOPED' and a08['blocks_affected_capability_in_shadow'] is False and a08['blocks_production_cutover_for_scope'] is True,'A08_SCOPE_DRIFT')
    return historical_resolve(contract,head,requested)

def admission(root,binding,requested):
    root=Path(root).resolve()
    contract=json.loads(exact(root,binding));head=json.loads(exact(root,contract['current_audit_head']))
    authority=json.loads(exact(root,contract['current_audit_authority']))
    check(authority['contract_id']=='V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V4' and authority['current_head']==contract['current_audit_head'],'AUDIT_AUTHORITY_HEAD_SPLIT')
    check(all(authority[k] is False for k in ('business_runtime_authority','automatic_stage_permission','production','focus','shadow')),'AUDIT_AUTHORITY_PERMISSION_OVERCLAIM')
    exact(root,authority['stage_current_authority_unchanged'])
    for ref in contract['external_acceptance_bindings']:exact(root,ref)
    for ref in contract['current_producer_bindings']:exact(root,ref)
    check(head['entries']['A08_CURRENT_RUNTIME']['current_authority']['current_runtime_external_acceptance']==authority['a08_external_acceptance']==contract['external_acceptance_bindings'][0],'EXTERNAL_A08_AUTHORITY_SPLIT')
    return resolve(contract,head,requested)

def require_admission(root,binding,requested):
    result=admission(root,binding,requested)
    check(result['admitted'],'CURRENT_AUDIT_CAPABILITY_BLOCKED:'+','.join(result['blocking_issue_ids']))
    return result

def validate_dependencies(root,deps):
    root=Path(root).resolve()
    check(deps['contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V6','V6_DEPENDENCY_IDENTITY_REQUIRED')
    check(deps['capability_resolution']['path']=='config/v4_16_runtime_capability_resolution_v2.json','STALE_RESOLVER_IN_V6')
    for ref in deps['bindings']:exact(root,ref)
    contract=json.loads(exact(root,deps['capability_resolution']))
    check(deps['current_audit_head']==contract['current_audit_head'] and deps['current_audit_authority']==contract['current_audit_authority'],'AUDIT_DEPENDENCY_SPLIT')
    result=admission(root,deps['capability_resolution'],['PURE_CORE_STOCK'])
    check(set(deps['blocked_issue_ids'])==set(contract['blocked_issue_ids']),'BLOCKING_ISSUE_SET_DRIFT')
    return result

def validate_grant(deps,grant):
    from scripts.v4_16_go_forward_shadow_runtime import dependency_digest
    check(deps['contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V6' and grant['runtime_dependency_contract_id']==deps['contract_id'] and grant['dependency_set_digest']==dependency_digest(deps),'V6_GRANT_DEPENDENCY_MISMATCH')

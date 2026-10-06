"""Separate audit issue identities from transitive runtime capabilities."""
import json
from scripts.v4_16_shadow_runtime import check, exact

FIELDS = ('current_state','affected_capabilities','blocks_affected_capability_in_shadow','blocks_v4_16_runtime_activation')

def resolve(contract, head, requested):
    graph = contract['runtime_capability_dependency_graph']
    check(isinstance(requested,list) and requested and len(requested)==len(set(requested)), 'INVALID_CAPABILITY_REQUEST')
    resolved = set()
    visiting = set()
    def visit(capability):
        check(capability in graph, 'UNKNOWN_RUNTIME_CAPABILITY')
        check(capability not in visiting, 'CAPABILITY_DEPENDENCY_CYCLE')
        if capability in resolved:return
        visiting.add(capability)
        for dependency in graph[capability]:visit(dependency)
        visiting.remove(capability);resolved.add(capability)
    for capability in requested:visit(capability)
    issues = contract['current_audit_issue_resolution']
    check(set(issues)==set(contract['blocked_issue_ids']), 'ISSUE_PROJECTION_INCOMPLETE')
    blockers = []
    effective = set()
    # Check all canonical entries: an omitted newly blocking issue fails closed.
    canonical = {k:v for k,v in head['entries'].items() if not v.get('alias_of')}
    required = {k for k,v in canonical.items() if v.get('blocks_affected_capability_in_shadow') or v.get('blocks_v4_16_runtime_activation')}
    check(required <= set(issues), 'UNRESOLVED_CURRENT_AUDIT_ISSUE')
    for issue_id, projection in issues.items():
        check(issue_id in canonical, 'UNKNOWN_AUDIT_ISSUE')
        entry = canonical[issue_id]
        check(projection=={key:entry.get(key,False) for key in FIELDS}, 'AUDIT_CAPABILITY_PROJECTION_DRIFT')
        affected=entry['affected_capabilities']
        check(isinstance(affected,list) and all(isinstance(c,str) for c in affected),'INVALID_AFFECTED_CAPABILITIES')
        if entry.get('blocks_affected_capability_in_shadow'):
            effective.update(affected)
            if resolved & set(affected):blockers.append(issue_id)
        if entry.get('blocks_v4_16_runtime_activation'):blockers.append(issue_id)
    closures={}
    def dependencies(capability,active=()):
        check(capability in graph,'UNKNOWN_RUNTIME_CAPABILITY')
        check(capability not in active,'CAPABILITY_DEPENDENCY_CYCLE')
        if capability not in closures:
            closures[capability]={capability}
            for child in graph[capability]:closures[capability].update(dependencies(child,active+(capability,)))
        return closures[capability]
    effective_runtime={cap for cap in graph if dependencies(cap)&effective}
    return dict(admitted=not blockers, permission_granted=False, requested_capabilities=sorted(requested), required_capabilities=sorted(resolved),
                blocking_issue_ids=sorted(set(blockers)), effective_blocked_runtime_capabilities=sorted(effective_runtime))

def admission(root, binding, requested):
    contract=json.loads(exact(root,binding))
    head=json.loads(exact(root,contract['current_audit_head']))
    return resolve(contract,head,requested)

def require_admission(root, binding, requested):
    result=admission(root,binding,requested)
    check(result['admitted'], 'CURRENT_AUDIT_CAPABILITY_BLOCKED:'+','.join(result['blocking_issue_ids']))
    return result

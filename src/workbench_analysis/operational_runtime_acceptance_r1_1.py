"""Admit verified runtime IO without pretending a completed generation reran.

Numerical producers and parameters retain exact generation source bytes. Only
explicit read/publication/PG metadata modules may acquire later versions.
"""
import json
from .r43_owner_replay import checked

KEY='runtime_acceptance_preparation_r1_1'
CONTRACT='V4_RUNTIME_ACCEPTANCE_METADATA_CONSERVATION_R1_1'
IO_ONLY={
    'src/workbench_analysis/operational_daily_exact_policy_v2.py',
    'src/workbench_analysis/operational_runtime_acceptance_r1_1.py',
    'src/workbench_analysis/operational_market_context_correction_r1.py',
    'src/workbench_analysis/operational_revision_guard_r1.py',
    # Canonical row-order/duplicate-safe IO preparation, never factor production.
    'src/workbench_analysis/operational_product_pack_v3.py',
    'src/workbench_analysis/operational_successor_release_v1.py',
    'src/workbench_analysis/operational_successor_v1.py',
    'src/workbench_db/v4_native.py',
    'src/workbench_db/v4_membership_reference_pg_v1.py',
    'src/workbench_db/v4_profile_semantic_corrections_pg_v1.py',
    'src/workbench_db/v4_profile_dependent_corrections_pg_v1.py',
    'src/workbench_db/v4_read_index_r1.py',
    'src/workbench_db/v4_read_index_r2.py',
    'src/workbench_service/core_product_bff_r1.py',
    'src/workbench_service/core_product_server_r1.py',
    'src/workbench_service/r43_operational_bff.py',
    'src/workbench_service/native_current_snapshot_v3.py',
    'src/workbench_desktop/source_adapter.py',
    'src/workbench_desktop/storage.py',
    'src/workbench_desktop/jobs.py',
    'src/workbench_analysis/operational_sealed_resume_r1.py',
}


def owner_metadata_cleanup_only(before,after):
    """Exact AST allowance: only two receipt-relocation statements in seal."""
    import ast
    old=ast.parse(before);new=ast.parse(after)
    template=ast.parse("inherited={key:candidate.pop(key) for key in ('sealed_numeric_preparation','component_source_conservation') if key in candidate}\nif inherited:candidate['predecessor_generation_evidence']=dict(predecessor=candidate['predecessor'],receipts=inherited)").body
    def strip(tree):
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='seal']
        if len(functions)!=1:return False
        body=functions[0].body
        matches=[i for i in range(len(body)-1) if ast.dump(body[i])==ast.dump(template[0]) and ast.dump(body[i+1])==ast.dump(template[1])]
        if len(matches)!=1:return False
        i=matches[0]
        # The statements must follow candidate creation and precede owner merge.
        if i+2>=len(body) or not isinstance(body[i+2],ast.Assign) or ast.unparse(body[i+2].targets[0])!="candidate['owners']":return False
        del body[i:i+2]
        return True
    if not strip(new):return False
    # Generation may already include the same conservative metadata cleanup.
    strip(old)
    return ast.dump(old)==ast.dump(new)

def source_conservation(root,generation_policy,runtime_policy,*,candidate=None):
    old={b.get('module_path',b['path']):b for b in generation_policy['accepted_algorithm_bindings']}
    new={b.get('module_path',b['path']):b for b in runtime_policy['accepted_algorithm_bindings']}
    if not set(old)<=set(new):raise ValueError('R1_1_GENERATION_SOURCE_REMOVED')
    additions=set(new)-set(old)
    if additions-IO_ONLY:raise ValueError('R1_1_UNAPPROVED_RUNTIME_SOURCE_ADDITION:'+','.join(sorted(additions-IO_ONLY)))
    market_drivers=set()
    if candidate is not None:
        from .operational_market_context_correction_r1 import KEY as MARKET,DRIVERS,verify as verify_market
        if MARKET in candidate:
            verify_market(root,candidate,runtime_policy);market_drivers=set(DRIVERS)
    changed=[]
    for name,binding in old.items():
        checked(root,binding);checked(root,new[name])
        if binding['sha256']!=new[name]['sha256']:
            metadata_owner=name=='src/workbench_analysis/operational_daily_owner_v1.py' and owner_metadata_cleanup_only(checked(root,binding).read_text(encoding='utf-8'),checked(root,new[name]).read_text(encoding='utf-8'))
            if name not in IO_ONLY and name not in market_drivers and not metadata_owner:raise ValueError('R1_1_NUMERIC_GENERATION_SOURCE_CHANGED:'+name)
            changed.append(name)
    for binding in new.values():checked(root,binding)
    old_components={b['module_path']:b for b in generation_policy['component_source_bindings']}
    new_components={b['module_path']:b for b in runtime_policy['component_source_bindings']}
    if set(old_components)!=set(new_components):raise ValueError('R1_1_COMPONENT_SOURCE_SCOPE_CHANGED')
    for name,binding in old_components.items():
        checked(root,binding);checked(root,new_components[name])
        if binding['sha256']!=new_components[name]['sha256'] and name not in IO_ONLY and name not in market_drivers:
            raise ValueError('R1_1_COMPONENT_GENERATION_SOURCE_CHANGED:'+name)
    return sorted(changed)

def verify(root,candidate,policy):
    receipt=json.loads(checked(root,candidate[KEY]).read_bytes())
    if receipt.get('contract_id')!=CONTRACT or receipt.get('acceptance')!='PASS_METADATA_ONLY':
        raise ValueError('R1_1_METADATA_CONSERVATION_RECEIPT_REQUIRED')
    original=json.loads(checked(root,receipt['generation_candidate']).read_bytes())
    old_policy=json.loads(checked(root,original['release_policy']).read_bytes())
    permitted={'release_policy','accepted_algorithm_bindings',KEY}
    if set(candidate)-set(original)!={KEY} or any(candidate.get(k)!=v for k,v in original.items() if k not in permitted):
        raise ValueError('R1_1_NUMERIC_CANDIDATE_CHANGED')
    generation=json.loads(checked(root,candidate['exact_daily_generation_scope']).read_bytes())
    if generation['adjustment_contract']['policy']!=original['release_policy']:
        raise ValueError('R1_1_GENERATION_POLICY_LINEAGE_MISMATCH')
    if original['accepted_algorithm_bindings']!=old_policy['accepted_algorithm_bindings'] or candidate['accepted_algorithm_bindings']!=policy['accepted_algorithm_bindings']:
        raise ValueError('R1_1_RUNTIME_SOURCE_LINEAGE_MISMATCH')
    changed=source_conservation(root,old_policy,policy,candidate=original)
    if changed!=receipt.get('changed_io_modules') or receipt.get('runtime_bindings')!=policy['accepted_algorithm_bindings']:
        raise ValueError('R1_1_METADATA_IO_SCOPE_MISMATCH')
    return receipt

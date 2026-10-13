"""Admit metadata preparation of immutable completed numerical generation.

This contract does not claim that completed producers executed newer source.
Only the two explicit post-generation IO additions may differ in producer AST.
"""
import ast,json
from pathlib import Path
from .r43_owner_replay import checked

CONTRACT='V4_SEALED_NUMERIC_METADATA_PREPARATION_R1'
KEY='sealed_numeric_preparation'
POLICY_MODULE='src/workbench_analysis/operational_daily_exact_policy_v2.py'
IO_MODULES={
    'src/workbench_analysis/operational_daily_owner_v1.py':frozenset(('workbench_db.v4_operational_owner_authority_v2','workbench_db.v4_membership_reference_pg_v1')),
    'src/workbench_analysis/operational_daily_executor_v1.py':frozenset(('operational_product_pack_v3','workbench_db.v4_membership_reference_pg_v1')),
}
ADDED_MODULES=frozenset((
    'src/workbench_analysis/operational_product_pack_v3.py','src/workbench_analysis/operational_successor_v1.py',
    'src/workbench_db/v4_history_corrections_pg_v2.py','src/workbench_db/v4_history_pg_r1.py',
    'src/workbench_db/v4_membership_reference_pg_v1.py','src/workbench_db/v4_operational_owner_authority_v2.py',
    'src/workbench_db/v4_operational_owner_pg_closeout.py','src/workbench_service/core_product_bff_r1.py',
    'src/workbench_service/core_product_server_r1.py','src/workbench_service/native_product_catalog_v3.py',
    'src/workbench_service/r43_operational_bff.py',
    'src/workbench_analysis/operational_sealed_preparation_v1.py',
    'src/workbench_analysis/producer_bootstrap_v1.py','src/workbench_service/candidate_research_read_v2.py',
))

def source_conservation(root,original,current):
    old={b.get('module_path',b['path']):b for b in original};new={b.get('module_path',b['path']):b for b in current}
    if not set(old)<=set(new) or not set(new)-set(old)<=ADDED_MODULES:raise ValueError('SEALED_PREPARATION_UNAPPROVED_SOURCE_SET')
    proof=[]
    for name,binding in old.items():
        old_path=checked(root,binding);new_path=checked(root,new[name])
        if binding['sha256']==new[name]['sha256']:continue
        if name in (POLICY_MODULE,'src/workbench_analysis/operational_successor_release_v1.py'):
            proof.append(dict(module_path=name,scope='ADMISSION_POLICY_ONLY'));continue
        if name not in IO_MODULES:raise ValueError('SEALED_NUMERIC_PRODUCER_SOURCE_CHANGED:'+name)
        before=ast.parse(old_path.read_text('utf8'));after=ast.parse(new_path.read_text('utf8'));removed=[]
        class StripPreparedIO(ast.NodeTransformer):
            def visit_If(self,node):
                imports={n.module for n in ast.walk(node) if isinstance(n,ast.ImportFrom)}
                if imports & IO_MODULES[name]:
                    expected=ast.parse("context.get('exact_daily_policy')",mode='eval').body
                    if ast.dump(node.test)!=ast.dump(expected) or node.orelse or not imports<=IO_MODULES[name]:raise ValueError('SEALED_PREPARATION_IO_BRANCH_SCOPE')
                    removed.append(ast.dump(node));return None
                return self.generic_visit(node)
        after=StripPreparedIO().visit(after)
        if not 1<=len(removed)<=2 or ast.dump(before)!=ast.dump(after):raise ValueError('SEALED_NUMERIC_AST_CONSERVATION_FAILED:'+name)
        proof.append(dict(module_path=name,scope='POST_GENERATION_IO_ONLY',removed_branches=len(removed)))
    return dict(changed_source_proof=proof,added_read_and_preparation_modules=sorted(set(new)-set(old)))

def verify(root,candidate,policy):
    root=Path(root);receipt=json.loads(checked(root,candidate[KEY]).read_bytes())
    if receipt.get('contract_id')!=CONTRACT or receipt.get('acceptance')!='PASS_METADATA_CONSERVATION_ONLY':raise ValueError('SEALED_PREPARATION_CONTRACT_REQUIRED')
    sealed=json.loads(checked(root,receipt['sealed_candidate']).read_bytes())
    old_policy=json.loads(checked(root,receipt['generation_policy']).read_bytes())
    if receipt['generation_policy']['sha256']!=sealed['release_policy']['sha256'] or receipt['generation_policy']['bytes']!=sealed['release_policy']['bytes']:
        raise ValueError('SEALED_PREPARATION_ORIGINAL_POLICY_MISMATCH')
    permitted={'release_policy','accepted_algorithm_bindings','period_numeric_oracle'}
    for key,value in sealed.items():
        if key not in permitted and candidate.get(key)!=value:raise ValueError('SEALED_NUMERIC_ORIGINAL_FIELD_CHANGED:'+key)
    extra=set(candidate)-set(sealed)
    if extra-{'native_pg_owner_authority','native_product_read_authority','native_membership_reference',KEY,'period_numeric_oracle'}:raise ValueError('SEALED_PREPARATION_UNAPPROVED_FIELD')
    generation=json.loads(checked(root,sealed['exact_daily_generation_scope']).read_bytes())
    if generation['adjustment_contract']['policy']!=sealed['release_policy'] or old_policy['accepted_algorithm_bindings']!=sealed['accepted_algorithm_bindings']:
        raise ValueError('SEALED_PREPARATION_GENERATION_LINEAGE_MISMATCH')
    if receipt['consumer_algorithm_bindings']!=policy['accepted_algorithm_bindings'] or candidate['accepted_algorithm_bindings']!=policy['accepted_algorithm_bindings']:
        raise ValueError('SEALED_PREPARATION_CONSUMER_SOURCE_MISMATCH')
    actual=source_conservation(root,old_policy['accepted_algorithm_bindings'],policy['accepted_algorithm_bindings'])
    if actual!=receipt['source_conservation']:raise ValueError('SEALED_PREPARATION_CONSERVATION_RECEIPT_DIFFERENCE')
    return receipt

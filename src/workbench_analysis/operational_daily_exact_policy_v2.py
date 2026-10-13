"""Explicit exact daily successor admission, separate from historical V1.1."""
from pathlib import Path
from .r43_owner_replay import checked,load,ref

CONTRACT='V4_OPERATIONAL_DAILY_EXACT_RELEASE_POLICY_V2'
PATH='config/operational_daily_exact_release_policy_v2.json'
ARCHIVE='data/v4/exact_daily_policies_v2'
KERNEL='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3'
REQUIRED_SOURCES={
    'src/adjustment/tdx_adjustment_v0_3.py',
    *('src/workbench_analysis/'+name+'.py' for name in (
        'exact_operational_core_candidate_r3','operational_owner_adapter_v1',
        'operational_daily_owner_v1','operational_daily_ready_owner_v2',
        'operational_daily_exact_policy_v2','operational_successor_release_v1',
        'operational_daily_executor_v1','operational_daily_periods_v1',
        'v4_13_descendant_contracts','portable_historical_archives_r1',
        'operational_upstream_checkpoint_r1',
        'r43_owner_replay','r43_structure_replay','r43_focus_replay','r43_market_replay')),
}
REQUIRED_SOURCES.add('config/v4_portable_historical_archive_witness_r1.json')
REQUIRED_SOURCES.update(('config/v4_03_parameter_set_v1.json','config/v4_03_parameter_registry_v1.json'))
REQUIRED_SOURCES.update(('src/workbench_db/v4_operational_owner_authority_v2.py',
    'src/workbench_db/v4_operational_owner_pg_closeout.py',
    'src/workbench_analysis/operational_successor_v1.py',
    'src/workbench_service/core_product_server_r1.py'))
REQUIRED_SOURCES.update(('src/workbench_service/native_product_catalog_v3.py',
    'src/workbench_service/core_product_bff_r1.py',
    'src/workbench_db/v4_history_pg_r1.py','src/workbench_db/v4_history_corrections_pg_v2.py'))
REQUIRED_SOURCES.add('src/workbench_analysis/operational_product_pack_v3.py')
REQUIRED_SOURCES.update(('src/workbench_db/v4_membership_reference_pg_v1.py','src/workbench_service/r43_operational_bff.py'))
REQUIRED_SOURCES.add('src/workbench_analysis/operational_sealed_preparation_v1.py')
REQUIRED_SOURCES.update(('src/workbench_analysis/producer_bootstrap_v1.py','src/workbench_service/candidate_research_read_v2.py'))
REQUIRED_SOURCES.update(('src/v4/profile_core.py','src/workbench_db/v4_profile_semantic_corrections_pg_v1.py',
    'src/workbench_db/v4_profile_dependent_corrections_pg_v1.py',
    'src/workbench_analysis/operational_component_source_conservation_v2.py'))

def verify_loaded_versions(bindings):
    import sys,hashlib
    for item in bindings:
        logical=item.get('module_path',item['path'])
        if not logical.endswith('.py') or not logical.startswith(('src/','scripts/')):continue
        name=(logical[4:-3] if logical.startswith('src/') else logical[:-3]).replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        for alias in (name,'src.'+name) if logical.startswith('src/') else (name,):
            module=sys.modules.get(alias)
            if module is not None and getattr(module,'__file__',None):
                origin=Path(module.__file__)
                if not origin.is_file() or hashlib.sha256(origin.read_bytes()).hexdigest()!=item['sha256']:
                    raise ValueError('EXACT_V2_LOADED_ALGORITHM_VERSION_MISMATCH:'+logical+':'+alias)

def immutable_policy_binding(root,binding=None):
    """Retain exact policy bytes; accepted Heads never depend on a mutable file."""
    import hashlib
    from .tdx_official_daily_source import _atomic_write
    root=Path(root).resolve();binding=binding or ref(root,root/PATH)
    path=checked(root,binding).resolve()
    if path==root/PATH:
        raw=path.read_bytes();archive=root/ARCHIVE/hashlib.sha256(raw).hexdigest()/'POLICY.json'
        if archive.exists():
            if archive.read_bytes()!=raw:raise ValueError('EXACT_V2_IMMUTABLE_POLICY_CONFLICT')
        else:_atomic_write(archive,raw,tdx_root=Path('D:/new_tdx'))
        return ref(root,archive)
    expected=root/ARCHIVE/binding['sha256']/'POLICY.json'
    if path!=expected:raise ValueError('EXACT_V2_DAILY_POLICY_PATH_REQUIRED')
    return binding

def verify(root,binding=None,*,candidate_only=False):
    root=Path(root).resolve()
    binding=immutable_policy_binding(root,binding)
    path=checked(root,binding)
    policy=load(path)
    if policy.get('contract_id')!=CONTRACT or policy.get('adjustment_contract')!=KERNEL:
        raise ValueError('EXACT_V2_DAILY_CONTRACT_REQUIRED')
    if any(policy.get(key) for key in ('historical_PIT_permission','automated_trading_permission','probability_claims')):
        raise ValueError('EXACT_V2_DAILY_SCOPE_ESCALATION')
    checked(root,policy['task_contract'])
    predecessor=checked(root,policy['predecessor_policy'])
    if predecessor.resolve()!=root/'config/read_only_operational_daily_release_policy_v1_1.json':
        raise ValueError('EXACT_V2_DAILY_PREDECESSOR_REQUIRED')
    bindings=policy['accepted_algorithm_bindings']
    paths=[b.get('module_path',b['path']) for b in bindings]
    if len(paths)!=len(set(paths)) or not REQUIRED_SOURCES<=set(paths):
        raise ValueError('EXACT_V2_DAILY_SOURCE_BINDINGS_REQUIRED')
    for item in bindings:checked(root,item)
    components=policy.get('component_source_bindings',[])
    component_paths=[b.get('module_path') for b in components]
    if policy.get('component_source_binding_contract')!='V4_EXACT_COMPONENT_SOURCE_BINDINGS_R2' or len(components)!=604 or len(set(component_paths))!=604:
        raise ValueError('EXACT_V2_COMPLETE_COMPONENT_SOURCE_BINDINGS_REQUIRED')
    for item in components:checked(root,item)
    if not candidate_only:
        if policy.get('publication_ready') is not True:raise ValueError('EXACT_V2_DAILY_ADMISSION_PENDING')
        if 'admission_evidence' not in policy:raise ValueError('EXACT_V2_DAILY_ACCEPTANCE_EVIDENCE_REQUIRED')
        # Existing historical Owner identities retain their original namespace.
        # Current executable versions reside in separate immutable archives.
        for original in load(predecessor)['accepted_algorithm_bindings']:checked(root,original)
        verify_loaded_versions(bindings+policy.get('component_source_bindings',[]))
        evidence=load(checked(root,policy['admission_evidence']))
        if evidence.get('contract_id')!='V4_AUTO_EXACT_RUNTIME_ACCEPTANCE_R1' or evidence.get('acceptance')!='PASS' or evidence.get('accepted_algorithm_bindings')!=bindings:
            raise ValueError('EXACT_V2_DAILY_ACCEPTANCE_EVIDENCE_REQUIRED')
        if evidence.get('component_source_bindings')!=components:raise ValueError('EXACT_V2_COMPONENT_ACCEPTANCE_SOURCE_MISMATCH')
        for key in ('full_numeric_oracle','exact_56_dispositions','native_pg_consumers','field_semantics'):
            result=load(checked(root,evidence[key]))
            if result.get('acceptance')!='PASS':raise ValueError('EXACT_V2_DAILY_REQUIRED_GATE_FAILED:'+key)
            if result.get('accepted_algorithm_bindings')!=bindings or result.get('component_source_bindings')!=components:raise ValueError('EXACT_V2_REQUIRED_GATE_SOURCE_MISMATCH:'+key)
    return policy,binding

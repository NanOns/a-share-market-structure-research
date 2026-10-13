"""Revision checks are anchored to the accepted predecessor, never bootstrap."""
from .r43_owner_replay import checked,load
from .tdx_official_daily_source import sha256_file

CONTRACT='V4_ACCEPTED_PREDECESSOR_REVISION_GUARD_R1'
# Driver admission is checked separately by the release policy. These bindings
# are numerical kernels/parameters and may never borrow that driver exception.
KERNEL_PREFIXES=('src/v4/','src/sector/','src/adjustment/','src/tdx/')
PARAMETERS={'config/v4_02_formal_period_contract_v1.json','config/v4_03_parameter_registry_v1.json','config/v4_03_parameter_set_v1.json'}

def detect(root,parent,gbbq_sha,member_hashes,*,execution_bindings=None):
    from pathlib import Path
    root=Path(root);previous=parent['accepted_trade_date']
    registry=parent.get('source_registry',{}).get(previous,{})
    if not registry.get('generation'):raise ValueError('RANGE_REPAIR_REQUIRED:ACCEPTED_GENERATION_MISSING')
    generation=load(checked(root,registry['generation']))
    revisions=[]
    if generation.get('gbbq')!=gbbq_sha:revisions.append('GBBQ_REVISION')
    if generation.get('member_sources')!=member_hashes:revisions.append('MEMBERSHIP_REVISION')
    kernels=[];drivers=[]
    executed={b.get('module_path',b['path']):b for b in execution_bindings or []}
    for binding in parent.get('accepted_algorithm_bindings',[]):
        name=binding.get('module_path',binding['path'])
        if name.startswith(KERNEL_PREFIXES) or name in PARAMETERS:
            if execution_bindings is not None:
                if name not in executed:raise ValueError('RANGE_REPAIR_REQUIRED:EXECUTED_NUMERIC_BINDING_MISSING:'+name)
                actual=sha256_file(checked(root,executed[name]))
            else:actual=sha256_file(root/name)
            kernels.append(dict(module_path=name,accepted_sha256=binding['sha256'],actual_sha256=actual,executed_binding=executed.get(name),unchanged=actual==binding['sha256']))
            if actual!=binding['sha256']:revisions.append('NUMERIC_ALGORITHM_REVISION:'+name)
        else:drivers.append(name)
    if not kernels:raise ValueError('RANGE_REPAIR_REQUIRED:ACCEPTED_NUMERIC_BINDINGS_MISSING')
    return dict(contract_id=CONTRACT,status='RANGE_REPAIR_REQUIRED' if revisions else 'APPEND_DAY',
        predecessor_trade_date=previous,predecessor_generation=registry['generation'],
        gbbq=dict(accepted=generation.get('gbbq'),actual=gbbq_sha),
        member_sources_unchanged=generation.get('member_sources')==member_hashes,
        revisions=revisions,numeric_bindings=kernels,driver_bindings_separate_admission=drivers,
        history_overlap='REQUIRES_CORE_HISTORY_OVERLAP_CHECK',head_mutated=False)

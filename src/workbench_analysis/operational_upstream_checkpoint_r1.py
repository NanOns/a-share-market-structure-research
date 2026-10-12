"""Reuse completed exact Core/Profile only after source and input conservation."""
import hashlib,json
from pathlib import Path
from .r43_owner_replay import checked,load,ref
from .operational_daily_storage_v1 import atomic_json

CONTRACT='V4_EXACT_CORE_PROFILE_REUSABLE_CHECKPOINT_R1'

def install(root,context,binding):
    root=Path(root).resolve();checkpoint=load(checked(root,binding))
    if checkpoint.get('contract_id')!=CONTRACT or checkpoint.get('publication') is not False:
        raise ValueError('EXACT_UPSTREAM_CHECKPOINT_CONTRACT_REQUIRED')
    old=load(checked(root,checkpoint['original_generation']));new=load(context['folder']/'GENERATION_SCOPE.json')
    for key in ('source_freeze','parent_head','identity','gbbq','member_sources'):
        if old[key]!=new[key]:raise ValueError('UPSTREAM_CHECKPOINT_INPUT_CHANGED:'+key)
    if old.get('adjustment_contract',{}).get('contract')!=new.get('adjustment_contract',{}).get('contract'):
        raise ValueError('UPSTREAM_CHECKPOINT_COORDINATE_CHANGED')
    import sys
    repository=Path(__file__).resolve().parents[2]
    policy=load(checked(root,context['exact_daily_policy']))
    versions={b.get('module_path',b['path']):b for b in policy['accepted_algorithm_bindings']}
    for item in checkpoint['unchanged_component_sources']:
        source=repository/item['path']
        if item['path'] in versions:source=checked(root,versions[item['path']])
        elif not source.is_file():
            source=root/item['path']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('UPSTREAM_CHECKPOINT_COMPONENT_CHANGED:'+item['path'])
    if checkpoint['completed_dates']!=context['dates']:raise ValueError('UPSTREAM_CHECKPOINT_DATES_CHANGED')
    seen=set()
    def verify_refs(value):
        if isinstance(value,dict):
            if 'path' in value and 'sha256' in value:
                key=(value['path'],value['sha256'])
                if key not in seen:
                    path=checked(root,value)
                    if 'bytes' in value and path.stat().st_size!=value['bytes']:
                        raise ValueError('UPSTREAM_CHECKPOINT_BOUND_SIZE_CHANGED')
                    seen.add(key)
            else:
                for child in value.values():verify_refs(child)
        elif isinstance(value,list):
            for child in value:verify_refs(child)
    documents={name:load(checked(root,b)) for name,b in checkpoint['documents'].items()}
    core=documents['CORE_REPLAY.json']
    if len(core['oracle'])!=len(context['dates']) or not all(r['result']=='PASS' and not r['errors'] for r in core['oracle']):
        raise ValueError('UPSTREAM_CHECKPOINT_NUMERIC_FAILURE')
    if [o['trade_date'] for o in core['owners']]!=context['dates'] or [o['owner']['trade_date'] for o in documents['PROFILE_STRUCTURE_REPLAY.json']['owners']]!=context['dates']:
        raise ValueError('UPSTREAM_CHECKPOINT_OWNER_DATES_CHANGED')
    for name,document in documents.items():
        verify_refs(document)
        target=context['folder']/'owner_v3'/name
        if target.exists() and load(target)!=document:raise ValueError('PRESERVE_EXISTING_UPSTREAM_CHECKPOINT')
        if not target.exists():atomic_json(root,target,document)
    receipt=dict(contract_id=CONTRACT,acceptance='PASS_UPSTREAM_REUSE_ONLY',checkpoint=binding,
        previous_generation=checkpoint['original_generation'],current_generation=ref(root,context['folder']/'GENERATION_SCOPE.json'),
        dates=context['dates'],source_hash_checks=len(checkpoint['unchanged_component_sources']),numerical_recomputed=False,publication=False)
    atomic_json(root,context['folder']/'CORE_PROFILE_REUSE_RECEIPT_R1.json',receipt)
    return receipt

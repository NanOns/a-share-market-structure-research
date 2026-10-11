"""Readiness IO adapter; preserves every byte of the accepted V1 owner."""
from pathlib import Path
from . import operational_daily_owner_v1 as owner
from .r43_owner_replay import checked,load,ref
from .tdx_official_daily_source import sha256_file
from .operational_daily_storage_v1 import atomic_json

CONTRACT='DYNAMIC_DAILY_READY_OWNER_ADAPTER_V2'

def build(root,freeze_binding,*,source_readiness,engineering_replay_current=False):
    root=Path(root)
    freeze_document=load(checked(root,freeze_binding))
    exact_candidate=freeze_document.get('engineering_exact_adjustment_candidate')
    if exact_candidate and (not engineering_replay_current or exact_candidate.get('contract')!='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3'):
        raise ValueError('EXACT_CORE_ENGINEERING_CONTRACT_REQUIRED')
    if engineering_replay_current:
        import os
        if os.environ.get('R4_NATIVE_ISOLATION')!='1' or not root.resolve().is_relative_to(Path('G:/codex_tmp').resolve()):
            raise ValueError('ISOLATED_ENGINEERING_CURRENT_REPLAY_REQUIRED')
    gate=load(checked(root,source_readiness))
    if not gate.get('source_ready') or gate.get('source_freeze')!=freeze_binding:
        raise ValueError('OWNER_READY_FREEZE_BINDING_REQUIRED')
    deps=gate['dependency_bindings']
    for key in ('parent_head','lifecycle','identity','membership_snapshot'):checked(root,deps[key])
    if sha256_file(Path(deps['gbbq']['path']))!=deps['gbbq']['sha256']:
        raise ValueError('SOURCE_READY_GBBQ_REVISION_MOVED')
    context=owner.prepare(root,freeze_binding,replay_current=engineering_replay_current)
    if sha256_file(context['folder']/'sources/gbbq')!=deps['gbbq']['sha256']:
        raise ValueError('SOURCE_READY_GBBQ_REVISION_MOVED')
    context['source_readiness']=source_readiness
    produced=owner.replay(root,context['folder'],context['dates'],context['mappings'],
        membership_snapshot=context['snapshot'],seed_registry=context['seed_registry'],
        observed_at=load(checked(root,context['freeze']))['observed_at'],exact_adjustment=bool(exact_candidate))
    return produced,context

def seal(root,context):
    root=Path(root);candidate,binding=owner.seal(root,context)
    receipt_path=checked(root,candidate['day_receipt']);receipt=load(receipt_path)
    atomic_json(root,receipt_path,dict(receipt,source_readiness=context['source_readiness'],readiness_adapter_contract=CONTRACT))
    candidate['day_receipt']=ref(root,receipt_path)
    atomic_json(root,root/binding['path'],candidate)
    return candidate,ref(root,root/binding['path'])

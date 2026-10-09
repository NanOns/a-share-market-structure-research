"""Readiness IO adapter; preserves every byte of the accepted V1 owner."""
from pathlib import Path
from . import operational_daily_owner_v1 as owner
from .r43_owner_replay import checked,load,ref
from .tdx_official_daily_source import sha256_file
from .operational_daily_storage_v1 import atomic_json

CONTRACT='DYNAMIC_DAILY_READY_OWNER_ADAPTER_V2'

def build(root,freeze_binding,*,source_readiness):
    root=Path(root);gate=load(checked(root,source_readiness))
    if not gate.get('source_ready') or gate.get('source_freeze')!=freeze_binding:
        raise ValueError('OWNER_READY_FREEZE_BINDING_REQUIRED')
    deps=gate['dependency_bindings']
    for key in ('parent_head','lifecycle','identity','membership_snapshot'):checked(root,deps[key])
    if sha256_file(Path(deps['gbbq']['path']))!=deps['gbbq']['sha256']:
        raise ValueError('SOURCE_READY_GBBQ_REVISION_MOVED')
    context=owner.prepare(root,freeze_binding)
    if sha256_file(context['folder']/'sources/gbbq')!=deps['gbbq']['sha256']:
        raise ValueError('SOURCE_READY_GBBQ_REVISION_MOVED')
    context['source_readiness']=source_readiness
    produced=owner.replay(root,context['folder'],context['dates'],context['mappings'],
        membership_snapshot=context['snapshot'],seed_registry=context['seed_registry'],
        observed_at=load(checked(root,context['freeze']))['observed_at'])
    return produced,context

def seal(root,context):
    root=Path(root);candidate,binding=owner.seal(root,context)
    receipt_path=checked(root,candidate['day_receipt']);receipt=load(receipt_path)
    atomic_json(root,receipt_path,dict(receipt,source_readiness=context['source_readiness'],readiness_adapter_contract=CONTRACT))
    candidate['day_receipt']=ref(root,receipt_path)
    atomic_json(root,root/binding['path'],candidate)
    return candidate,ref(root,root/binding['path'])

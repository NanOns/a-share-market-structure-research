"""R2 preflight separating local authority from supplemental availability.

This is an additive source gate, not a replacement or acceptance of nine R1
adapters. Final runtime integration must follow external A12 owner acceptance.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path

def verify_binding(root,binding):
    root=Path(root).resolve();path=(root/binding['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ValueError('LOCAL_ACCEPTED_FREEZE_MISSING')
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=binding['sha256']:raise ValueError('SOURCE_BINDING_DIGEST_MISMATCH')
    return path

def source_freeze_complete_v2(root,contract,required_bindings,supplemental_bindings):
    if contract.get('contract_id')!='DM01_SOURCE_AUTHORITY_AND_SUPPLEMENTAL_GATE_R2' or contract.get('supplemental_missing_blocks_core') is not False:
        raise ValueError('SOURCE_ROLE_CONTRACT_INVALID')
    expected=set(contract['required_source_families'])
    if set(required_bindings)!=expected or expected & set(contract['supplemental_source_families']):
        raise ValueError('REQUIRED_SOURCE_FAMILY_SET_INVALID')
    required={};supplemental={}
    for family,binding in required_bindings.items():
        try:verify_binding(root,binding);required[family]='AVAILABLE'
        except (ValueError,KeyError):required[family]='CORE_REQUIRED_SOURCE_UNAVAILABLE'
    for family in contract['supplemental_source_families']:
        binding=supplemental_bindings.get(family)
        if not binding:supplemental[family]='SUPPLEMENTAL_SOURCE_UNAVAILABLE';continue
        try:verify_binding(root,binding);supplemental[family]='AVAILABLE'
        except (ValueError,KeyError):supplemental[family]='SUPPLEMENTAL_SOURCE_UNAVAILABLE'
    return dict(contract_id=contract['contract_id'],required=required,supplemental=supplemental,
        core_source_gate='PASS' if all(s=='AVAILABLE' for s in required.values()) else 'BLOCKED',
        supplemental_can_overwrite_core=False,canonical_adjustment_authority='GBBQ',
        scope='SOURCE_FREEZE_PREFLIGHT_ONLY_NOT_ALL_NINE_ADAPTER_EXECUTION')

def require_external_a12_owner_for_final_candidate(root,owner_contract_binding,global_head):
    path=verify_binding(root,owner_contract_binding);owner=json.loads(path.read_text(encoding='utf8'))
    accepted=global_head.get('accepted_source_authority_owners',{}).get('V4_02_STATUS_ST')
    if owner.get('external_acceptance')!='EXTERNALLY_ACCEPTED' or owner.get('formal_consumer_authorization') is not True or accepted!=owner_contract_binding:
        raise ValueError('A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED')
    if owner.get('trading_status_contract')!='LOCAL_DATED_TRADING_STATUS_V2' or owner.get('st_contract')!='LOCAL_DATED_ST_IDENTITY_V2':
        raise ValueError('A12_OWNER_CONTRACT_IDENTITY_MISMATCH')
    return owner

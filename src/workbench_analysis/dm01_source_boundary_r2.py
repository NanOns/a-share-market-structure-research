"""R2 preflight separating local authority from supplemental availability.

This is an additive source gate, not a replacement or acceptance of nine R1
adapters. Final runtime integration requires both external A10/A12 acceptance.
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

def require_external_a12_owner_for_final_candidate(root,owner_contract_binding,global_head=None,*,
        consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date=None,
        historical_mode='TARGET_DATE_QUERYABLE_FACT'):
    """Use the same proof as A10 for both required fields, with exact input bindings.

    The legacy global_head argument is retained for callers but is not a trust
    root. Only the independently stored authority governance head can register
    owners. A candidate bundle cannot substitute for two field owner bindings.
    """
    from .source_authority_accepted_owners_v1 import require_accepted_owner, OwnerAcceptanceError
    try:
        contract=json.loads((Path(root)/'config/source_authority_governance_r2.json').read_text(encoding='utf8'))
        result={}
        for field in ('TRADING_STATUS','ISST'):
            rule=next(r for r in contract['field_rules'] if r['field_id']==field)
            binding=(owner_contract_binding.get(field,owner_contract_binding)
                if isinstance(owner_contract_binding,dict) else owner_contract_binding)
            result[field]=require_accepted_owner(root,rule,consumer_contract_id=consumer_contract_id,
                target_trade_date=target_trade_date,historical_mode=historical_mode,expected_owner_binding=binding)
        return result
    except (OwnerAcceptanceError,OSError,ValueError,KeyError,TypeError,StopIteration) as exc:
        raise ValueError('A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED:AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED') from exc

def require_a12_producer_instances_for_candidate(root,source_instances,*,target_trade_date,
        consumer_contract_id='DM01_FINAL_ALL_NINE',historical_mode='TARGET_DATE_QUERYABLE_FACT'):
    """R3 field preflight; passing this gate never establishes all-nine acceptance."""
    from .source_authority_producers_r3 import require_accepted_producer,require_source_instance_for_target
    contract=json.loads((Path(root)/'config/source_authority_governance_r3.json').read_text(encoding='utf8'))
    result={}
    for field in ('TRADING_STATUS','ISST'):
        rule=next(r for r in contract['field_rules'] if r['field_id']==field)
        producer=require_accepted_producer(root,rule,consumer_contract_id=consumer_contract_id,historical_mode=historical_mode)
        result[field]=require_source_instance_for_target(root,producer,source_instances.get(field),target_trade_date=target_trade_date)
    return dict(fields=result,scope='FIELD_SOURCE_PREFLIGHT_ONLY',all_nine_accepted=False)

"""Field-scoped candidate validation; this module is never an active trust root."""
from datetime import date
from .dm01_accepted_chain_v1 import bound_path, load, binding

RULES = {
    'OHLC': ('TDX_OFFICIAL_PACKAGE', ['RAW_DAILY', 'PERIOD_RAW']),
    'VOLUME': ('TDX_OFFICIAL_PACKAGE', ['RAW_DAILY', 'PERIOD_RAW']),
    'AMOUNT': ('TDX_OFFICIAL_PACKAGE', ['RAW_DAILY', 'PERIOD_RAW']),
    'QFQ': ('GBBQ_CANONICAL', ['ADJUSTED_DAILY', 'PERIOD_ADJUSTED']),
    'SECURITY_IDENTITY': ('VERSIONED_IDENTITY_LIFECYCLE_WITH_PROVIDER_RECONSTRUCTION', ['IDENTITY_UNIVERSE']),
    'SPECIAL_PHASE': ('ACCEPTED_SPECIAL_PHASE_EVENT_POLICY', ['SPECIAL_PHASE', 'PRICE_LIMIT']),
    'SECTOR_MEMBERSHIP': ('ACCEPTED_V4_08_FORWARD_PIT_MEMBERSHIP', ['V4_08_PIT_MEMBERSHIP_HISTORY_ONLY']),
}


def validate_owner(root, owner, *, field_id, consumer, target_date, historical_mode):
    if field_id not in RULES or owner.get('field_id') != field_id:
        raise ValueError('OWNER_FIELD_MISMATCH')
    family, consumers = RULES[field_id]
    if owner.get('source_family') != family or owner.get('allowed_consumers') != consumers or consumer not in consumers:
        raise ValueError('OWNER_SOURCE_OR_CONSUMER_OUT_OF_SCOPE')
    mode = 'AS_RECORDED_FIRST_OBSERVED_PIT' if field_id == 'SECTOR_MEMBERSHIP' else 'RECONSTRUCTED_CORRECTED'
    if historical_mode != mode or owner.get('historical_mode') != mode:
        raise ValueError('OWNER_HISTORICAL_MODE_OUT_OF_SCOPE')
    scope = owner['effective_scope']
    if scope != dict(start_date='2026-09-30', end_date='2026-09-30') or not date.fromisoformat(scope['start_date']) <= date.fromisoformat(target_date) <= date.fromisoformat(scope['end_date']):
        raise ValueError('OWNER_DATE_OUT_OF_SCOPE')
    if owner.get('external_acceptance') != 'PENDING_INDEPENDENT_EXTERNAL_REAUDIT' or owner.get('formal_consumer_authorization') is not False:
        raise ValueError('OWNER_CANDIDATE_SELF_PROMOTION')
    if any(owner.get(k) is not False for k in ('production', 'shadow', 'focus_cutover', 'global_mandatory_adoption')):
        raise ValueError('OWNER_PERMISSION_OVERCLAIM')
    expected_head = 'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json' if field_id == 'SECTOR_MEMBERSHIP' else 'data/v4/V4_DATA_ACCEPTED_HEAD.json'
    if owner['accepted_head'] != binding(root, expected_head):
        raise ValueError('OWNER_ACCEPTED_HEAD_MISMATCH')
    if not owner['source_bindings']:
        raise ValueError('OWNER_SOURCE_EVIDENCE_REQUIRED')
    head = load(root, owner['accepted_head'])
    for ref in [owner['current_accepted_contract'], owner['artifact'], *owner['source_bindings'], *owner['external_acceptance_evidence']]:
        bound_path(root, ref)
    if field_id == 'SECTOR_MEMBERSHIP':
        if head.get('membership_acceptance_scope') != 'FORWARD_PIT_MEMBERSHIP_ONLY' or owner['artifact'] != head['facts'] or owner['external_acceptance_evidence'] != [head['external_acceptance_evidence']]:
            raise ValueError('MEMBERSHIP_ACCEPTANCE_SCOPE_INVALID')
        if owner.get('mutable_current_snapshot_is_historical_authority') is not False:
            raise ValueError('MUTABLE_MEMBERSHIP_BACKFILL_FORBIDDEN')
    else:
        component = {'OHLC': 'RAW_DAILY', 'VOLUME': 'RAW_DAILY', 'AMOUNT': 'RAW_DAILY', 'QFQ': 'ADJUSTED_DAILY', 'SECURITY_IDENTITY': 'IDENTITY_UNIVERSE', 'SPECIAL_PHASE': 'SPECIAL_PHASE'}[field_id]
        permission = head['component_permissions'][component]
        if head['accepted_trade_date'] != '2026-09-30' or owner['artifact'] != permission['artifact'] or owner['degraded_capability'] != dict(status=permission['status'], unknown_reason_counts=permission['unknown_reason_counts']):
            raise ValueError('OWNER_ARTIFACT_OR_CAPABILITY_MISMATCH')
        record = load(root, head['external_acceptance_record'])
        if owner['external_acceptance_evidence'] != [record['external_authority']['document']]:
            raise ValueError('OWNER_EXTERNAL_EVIDENCE_OUT_OF_SCOPE')
        chain = load(root, head['accepted_chain'])
        context = load(root, chain['source_context'])
        inputs = context['inputs']['2026-09-30']['inputs']
        keys = {'OHLC':['TDX_PACKAGE_DELTA'], 'VOLUME':['TDX_PACKAGE_DELTA'], 'AMOUNT':['TDX_PACKAGE_DELTA'], 'QFQ':['GBBQ','GBBQ_DISPOSITIONS','TDX_PACKAGE_DELTA'], 'SPECIAL_PHASE':['SPECIAL_PRICE_PHASE','PRICE_RULES']}.get(field_id)
        expected_sources = [inputs[k] for k in keys] if keys else [context['inputs']['2026-09-30']['families']['IDENTITY_LIFECYCLE'],head['identity'],binding(root,'reports/audits/A11_STAGE_CLOSURE_R1.json')]
        if owner['source_bindings'] != expected_sources or owner['current_accepted_contract'] != chain['builder_contract']:
            raise ValueError('OWNER_SOURCE_OR_CONTRACT_OUT_OF_SCOPE')
    if field_id == 'AMOUNT' and owner.get('amount_a_formal_authority') is not False:
        raise ValueError('AMOUNT_A_IS_SEPARATE_AUTHORITY')
    if field_id == 'QFQ' and (owner.get('canonical_adjustment') != 'GBBQ_CANONICAL' or owner.get('historical_as_recorded_proven') is not False):
        raise ValueError('QFQ_BASIS_OR_PIT_OVERCLAIM')
    if field_id == 'SECURITY_IDENTITY' and 'HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED' not in owner['known_limitations']:
        raise ValueError('A11_LIMITATION_REQUIRED')
    return dict(status='PASS_SCOPED_CANDIDATE_ONLY', formal_consumer_authorization=False)


def validate_registry(root, registry):
    if registry.get('contract_id') != 'V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE' or registry.get('version') != 4:
        raise ValueError('OWNER_CANDIDATE_REGISTRY_VERSION_INVALID')
    if registry.get('active_global_trust_root') is not False or registry.get('global_mandatory_adoption') is not False:
        raise ValueError('OWNER_GLOBAL_TRUST_ROOT_FORBIDDEN')
    owners = registry['owners']
    if len(owners) != len(RULES) or {x['field_id'] for x in owners} != set(RULES):
        raise ValueError('OWNER_FIELDS_DUPLICATE_OR_MISSING')
    for owner in owners:
        validate_owner(root, owner, field_id=owner['field_id'], consumer=owner['allowed_consumers'][0], target_date='2026-09-30', historical_mode=owner['historical_mode'])
    return dict(status='PASS_SCOPED_CANDIDATE_ONLY', fields=len(owners), active_global_trust_root=False)

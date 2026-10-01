"""Audit each existing accepted field into a non-active owner candidate."""
import json
from pathlib import Path
from scripts.next_round_bundle_r1 import write
from workbench_analysis.dm01_accepted_chain_v1 import binding, load
from workbench_analysis.source_authority_owner_bootstrap_r1 import RULES, validate_registry

ROOT = Path(__file__).resolve().parents[1]
OUT = 'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json'


def build(root=ROOT):
    root = Path(root)
    data_ref = binding(root, 'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    head = load(root, data_ref)
    chain = load(root, head['accepted_chain'])
    context = load(root, chain['source_context'])
    sources = context['inputs']['2026-09-30']['inputs']
    record = load(root, head['external_acceptance_record'])
    membership_ref = binding(root, 'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
    membership = load(root, membership_ref)
    owners = []
    for field, (family, consumers) in RULES.items():
        component = dict(OHLC='RAW_DAILY', VOLUME='RAW_DAILY', AMOUNT='RAW_DAILY', QFQ='ADJUSTED_DAILY', SECURITY_IDENTITY='IDENTITY_UNIVERSE', SPECIAL_PHASE='SPECIAL_PHASE').get(field)
        owner = dict(owner_contract_id='OWNER_SCOPE_BOOTSTRAP_'+field+'_R1', field_id=field,
            source_family=family, allowed_consumers=consumers,
            effective_scope=dict(start_date='2026-09-30', end_date='2026-09-30'),
            historical_mode='AS_RECORDED_FIRST_OBSERVED_PIT' if field == 'SECTOR_MEMBERSHIP' else 'RECONSTRUCTED_CORRECTED',
            external_acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT', formal_consumer_authorization=False,
            production=False, shadow=False, focus_cutover=False, global_mandatory_adoption=False,
            source_role='CORE_AUTHORITY' if field in ('OHLC','VOLUME','AMOUNT','QFQ') else 'FIELD_AUTHORITY',
            historical_scope='Inherited frozen accepted publications only; no backfilled knowledge-time claim',
            go_forward_scope='Exact externally accepted 2026-09-30 artifact only; new dates require their own accepted publication',
            known_limitations=[], inherited_acceptance_is_not_owner_registry_external_acceptance=True)
        if component:
            p = head['component_permissions'][component]
            source_keys = {'OHLC':['TDX_PACKAGE_DELTA'], 'VOLUME':['TDX_PACKAGE_DELTA'], 'AMOUNT':['TDX_PACKAGE_DELTA'], 'QFQ':['GBBQ','GBBQ_DISPOSITIONS','TDX_PACKAGE_DELTA'], 'SECURITY_IDENTITY':['SECURITY_LIFECYCLE'], 'SPECIAL_PHASE':['SPECIAL_PRICE_PHASE','PRICE_RULES']}[field]
            # Lifecycle is separately pinned in the accepted execution context.
            source_refs = [sources[k] for k in source_keys if k in sources]
            if field == 'SECURITY_IDENTITY':
                source_refs = [context['inputs']['2026-09-30']['families']['IDENTITY_LIFECYCLE'], head['identity'], binding(root, 'reports/audits/A11_STAGE_CLOSURE_R1.json')]
            owner.update(accepted_head=data_ref, artifact=p['artifact'], current_accepted_contract=chain['builder_contract'],
                accepted_algorithm_contract=p['accepted_algorithm_contract'], source_bindings=source_refs,
                external_acceptance_evidence=[record['external_authority']['document']],
                degraded_capability=dict(status=p['status'],unknown_reason_counts=p['unknown_reason_counts']),
                market_board_coverage=['SH_MAIN','SZ_MAIN','STAR','CHINEXT'],
                actual_bar_semantics='Native TDX daily price in CNY/share, cumulative native volume/amount; amount is not Amount-A')
        else:
            owner.update(accepted_head=membership_ref,artifact=membership['facts'],current_accepted_contract=binding(root,'config/v4_08_accepted_context_contract_r5_2.json'),
                source_bindings=[membership['source_revision'],membership['snapshot'],membership['source_capture']],
                external_acceptance_evidence=[membership['external_acceptance_evidence']],
                degraded_capability=dict(status='FIRST_OBSERVED_PIT_ONLY',unknown_reason_counts={}),
                mutable_current_snapshot_is_historical_authority=False,
                provider_snapshot_scope='Current mutable snapshot separately captured; accepted membership facts begin at first observation 2026-09-30',
                known_limitations=['NO_HISTORICAL_BACKFILL','FORMAL_CONSUMERS_STILL_DISABLED'])
        if field == 'AMOUNT':
            owner.update(amount_a_formal_authority=False, known_limitations=['AMOUNT_A_FORMAL_BRANCH_REQUIRES_SEPARATE_A04_EXTERNAL_ACCEPTANCE'])
        if field == 'QFQ':
            owner.update(canonical_adjustment='GBBQ_CANONICAL', historical_as_recorded_proven=False,
                known_limitations=['AS_RECORDED_ADJUSTED_HISTORY_NOT_PROVEN','UNSUPPORTED_OR_UNPROVED_ADJUSTMENT_REMAINS_UNKNOWN','BAOSTOCK_ADJUSTMENT_FACTOR_SUPPLEMENTAL_ONLY'])
        if field == 'SECURITY_IDENTITY':
            owner['known_limitations']=['HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED','FIRST_AVAILABLE_AT_TARGET_NOT_PROVEN']
        if field == 'SPECIAL_PHASE':
            owner['known_limitations']=['UNKNOWN_EVENT_OR_RULE_CAPABILITY_RETAINED','NO_FILENAME_EVENT_SEMANTIC_UPGRADE']
        owners.append(owner)
    registry = dict(contract_id='V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE',version=4,
        status='OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        baseline_commit='bc3e398efb4f4a05c20973ff3cb335a6b101ac87',
        active_global_trust_root=False, global_mandatory_adoption=False,
        production=False,shadow=False,focus_cutover=False,
        inherited_active_registry=head['source_authority_registry'], owners=owners)
    result = validate_registry(root, registry)
    write(OUT, registry)
    write('reports/audits/OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_R1.json',dict(
        status=registry['status'],candidate_registry=binding(root,OUT), field_matrix=owners,independent_validation=result,
        unchanged_active_registry=head['source_authority_registry'],stage_head_action='KEEP',data_head_action='KEEP',
        next_stage='INDEPENDENT_EXTERNAL_REAUDIT',external_acceptance='PENDING',migration_required=False))
    return result


if __name__ == '__main__':
    print(json.dumps(build()))

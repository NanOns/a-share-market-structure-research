"""Consolidate externally accepted scopes, preserving every original business head."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.next_round_bundle_r1 import bind, read, write
from workbench_analysis.parallel_scoped_consolidation_r3 import (
    AUDIT, TASK, MASTER, BASELINE, PRIOR, REGISTRY, AUTHORITY, SUMMARY, PREFIX,
    DISPOSITIONS, PERMISSIONS, dispositions, external_authority,
    validate_consolidation, validate_authority_registry, validate_summary, protected_bindings, supersession_map,
    validate_scoped_protected_binding, PROTECTED_REPRESENTATIONS,
)
from workbench_analysis.parallel_scoped_acceptance_r1 import (
    OWNER_PATH, READER_PATH, accepted_adjusted_lineage, read_accepted_history,
)


def prepare():
    for path in (AUDIT, TASK, MASTER):
        bind(path)
    historical_phase0 = 'reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    gate = validate_head_v2(ROOT, read('data/v4/V4_DATA_ACCEPTED_HEAD.json'))
    entry = dict(
        contract_id='PARALLEL_SCOPED_CONSOLIDATION_STAGE_ENTRY_R3', stage_contract=bind(TASK),
        master=bind(MASTER), external_authority=external_authority(ROOT),
        batch_entry=bind('reports/next_round_r3/BATCH_STAGE_ENTRY_R1.json'),
        phase0=dict(status='DEGRADED_PASS', scope='ACCEPTED_INPUT_PREFLIGHT',
                    accepted_data_head_validation=gate, historical_receipt=bind(historical_phase0)),
        protected_bindings=protected_bindings(ROOT), permissions=PERMISSIONS,
        acceptance_result='AUTHORIZED_SCOPED_METADATA_CONSOLIDATION',
        next_stage='UNIFIED_BATCH_COMMIT_PUSH_STOP_AND_INDEPENDENT_EXTERNAL_AUDIT',
    )
    write(PREFIX + 'STAGE_ENTRY_R3.json', entry)
    registry = dict(
        contract_id='PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_R3', version=13,
        status='PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATED', supersedes=bind(PRIOR),
        baseline_commit=BASELINE, external_authority=external_authority(ROOT),
        stage_contract=bind(TASK), master=bind(MASTER), permissions=PERMISSIONS,
        head_action=dict(data='KEEP', stage='KEEP'), v4_12_runtime_authorized=False,
        formal_v4_11_accepted_head_authorized=False, active_business_authority_registry_changed=False,
        protected_bindings=entry['protected_bindings'], entries=deepcopy(read(PRIOR)['entries']),
        next_stage='UNIFIED_BATCH_COMMIT_PUSH_STOP_AND_INDEPENDENT_EXTERNAL_AUDIT',
    )
    for package, row in dispositions(ROOT).items():
        registry['entries'][package].update(row)
    validate_consolidation(ROOT, registry)
    write(REGISTRY, registry)
    authority = dict(
        contract_id='V4_SOURCE_AUTHORITY_SCOPED_DISPOSITION_REGISTRY_R5_INACTIVE', version=5,
        registration_status='SCOPED_ACCEPTED_INACTIVE_METADATA', active_global_trust_root=False,
        active_registry=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json'),
        accepted_owner_metadata=bind(OWNER_PATH), accepted_history_reader=bind(READER_PATH),
        remediation_registry=bind(REGISTRY), scoped_dispositions=dispositions(ROOT), permissions=PERMISSIONS,
    )
    validate_authority_registry(ROOT, authority)
    write(AUTHORITY, authority)
    write(PREFIX + 'SUPERSESSION_MAP_R3.json', supersession_map(ROOT))
    head = dict(
        contract_id='PARALLEL_SCOPED_ACCEPTANCE_SUMMARY_HEAD_R3', version=3,
        status='PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATED', head_kind='SCOPED_METADATA_SUMMARY_ONLY',
        data_head_action='KEEP', stage_head_action='KEEP', dispositions=DISPOSITIONS,
        remediation_registry=bind(REGISTRY), authority_registry=bind(AUTHORITY),
        supersession_map=bind(PREFIX + 'SUPERSESSION_MAP_R3.json'), permissions=PERMISSIONS,
        business_runtime_authority=False, formal_v4_11_accepted_head=False,
    )
    validate_summary(ROOT, head)
    write(SUMMARY, head)


def independent_readback():
    """Reopen serialized bindings and exercise the preserved scope boundaries."""
    entry = read(PREFIX + 'STAGE_ENTRY_R3.json')
    for ref in entry['protected_bindings']:
        validate_scoped_protected_binding(ROOT, ref, approved_representation_map=PROTECTED_REPRESENTATIONS)
    registry = validate_consolidation(ROOT, read(REGISTRY))
    authority = validate_authority_registry(ROOT, read(AUTHORITY))
    summary = validate_summary(ROOT, read(SUMMARY))
    from workbench_analysis.baostock_tolerance_candidate_r2 import validate_policy, decompose
    policy = read('config/baostock_binding_tolerance_policy_r2_candidate.json')
    validate_policy(policy)
    conflict = decompose(
        dict(source_security_key='SYNTHETIC_MECHANISM_VECTOR', trade_date='2026-09-30', close=10, volume=100, amount=1000),
        dict(code='synthetic_mechanism_vector', date='2026-09-30', close='20', volume='300', amount='9000', tradestatus='1', adjustflag='3'),
    )
    if conflict['strict_binding'] or conflict['tdx_core_blocked']:
        raise ValueError('A06_ACCEPTANCE_SCOPE_ESCALATION')
    capture = read('reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_DURABLE_REAL_PROOF_R1.json')['real_capture']
    before_time = (datetime.fromisoformat(capture['first_available_at']) - timedelta(microseconds=1)).isoformat()
    before = accepted_adjusted_lineage(ROOT, capture, knowledge_time=before_time)
    at = accepted_adjusted_lineage(ROOT, capture, knowledge_time=capture['first_available_at'])
    if before['historical_capability'] != 'PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED' or at['lineage'] != 'AS_RECORDED' or at['formal_consumer_enabled']:
        raise ValueError('A07_PERMANENT_CAPABILITY_LIMITATION_LOST')
    from scripts import promote_v4_09_accepted_head as v9, validate_v4_10_promotion_r1 as v10
    roots = (v9.ROOT, v10.ROOT)
    history = {stage: read_accepted_history(ROOT, stage) for stage in ('V4-09', 'V4-10')}
    current = v10.validate()
    if (v9.ROOT, v10.ROOT) != roots or current['checks']['P19_protected'] != 'FAIL':
        raise ValueError('READER_CURRENT_RUNTIME_FALLBACK_FORBIDDEN')
    for result in history.values():
        if result['status'] != 'PASS' or result['validation_scope'] != 'ACCEPTED_PUBLICATION_HISTORY_ONLY' or result['business_reacceptance_performed']:
            raise ValueError('READER_HISTORY_SCOPE_ESCALATION')
    report = dict(
        contract_id='PARALLEL_SCOPED_CONSOLIDATION_INDEPENDENT_READBACK_R3', status='PASS',
        mechanism='SERIALIZED_ARTIFACT_REOPEN_AND_PRESERVED_RUNTIME_BOUNDARY_READBACK',
        observed_at=datetime.now(timezone.utc).isoformat(), registry=registry, authority=authority, summary=summary,
        a03=dict(engineering_task='CLOSED_SCOPED', accumulation='CONTINUES', new_observation_claim=False,
                 future_observation_count_is_engineering_blocker=False),
        a06=dict(tolerances={field: row['tolerance'] for field, row in policy['fields'].items()}, conflict=conflict),
        a07=dict(engineering_task='CLOSED_SCOPED', capability_limitation='PERMANENT_PRECAPTURE_LIMITATION',
                 before_capture=before, at_capture=at),
        owner=dict(fields=len(read(OWNER_PATH)['owners']), inactive_metadata=True, global_authority_consumer=False),
        reader=dict(history=history, current_business_validator=current, module_roots_unchanged=True,
                    silent_fallback=False, explicit_di_only=True),
        protected_bindings=entry['protected_bindings'], protected_bytes_unchanged=True, permissions=PERMISSIONS,
        approved_protected_representation_map=PROTECTED_REPRESENTATIONS,
        representation_scope='EXACT_TWO_PRE_EXISTING_ORIGINAL_ARCHIVE_AND_GIT_BINDINGS; METADATA_VALIDATION_ONLY',
    )
    write(PREFIX + 'INDEPENDENT_READBACK_R3.json', report, immutable=False)
    write(PREFIX + 'STAGE_CLOSURE_R3.json', dict(
        contract_id='PARALLEL_SCOPED_CONSOLIDATION_STAGE_CLOSURE_R3',
        status='PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATED', stage_contract=bind(TASK),
        external_authority=external_authority(ROOT), stage_entry=bind(PREFIX + 'STAGE_ENTRY_R3.json'),
        remediation_registry=bind(REGISTRY), authority_registry=bind(AUTHORITY), summary_head=bind(SUMMARY),
        independent_readback=bind(PREFIX + 'INDEPENDENT_READBACK_R3.json'),
        supersession_map=bind(PREFIX + 'SUPERSESSION_MAP_R3.json'),
        acceptance_result='ENGINEERING_CONSOLIDATION_COMPLETE_WITH_EXTERNAL_R2_SCOPED_DISPOSITIONS',
        applicable_upgrade_document=bind('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        runtime_and_verification_bindings=[bind(path) for path in (
            'src/workbench_analysis/parallel_scoped_consolidation_r3.py',
            'scripts/consolidate_parallel_scoped_formalization_r3.py',
            'tests/v4_parallel_scoped_consolidation_r3/test_consolidation.py',
        )],
        targeted_tests=bind(PREFIX + 'TARGETED_TESTS_R3.xml') if (ROOT / (PREFIX + 'TARGETED_TESTS_R3.xml')).exists() else None,
        new_consolidation_external_reaudit='PENDING_NEXT_INDEPENDENT_EXTERNAL_ACCEPTANCE',
        tests_alone_establish_release_readiness=False, permissions=PERMISSIONS,
        next_stage='UNIFIED_BATCH_COMMIT_PUSH_STOP_AND_INDEPENDENT_EXTERNAL_AUDIT',
    ), immutable=False)
    return report['status']


if __name__ == '__main__':
    prepare()
    print(json.dumps(dict(status=independent_readback(), summary_head=SUMMARY)))

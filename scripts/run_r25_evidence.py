"""R25 WAIT branch evidence; never manufactures a target-specific real packet."""
import tempfile
from pathlib import Path

from scripts.r25_io import ROOT, BASE, atomic, read, ref
from scripts.validate_r25_preflight import selection, protected, digest
from tests.test_r25_packet import negative, REASONS, f12_governance

DOCUMENTS = [
    'V4_NEXT_ROUND_EXECUTION_MASTER_R25_20261004.md',
    'V4_16_R25_FIRST_REAL_SHADOW_ACTIVATION_PACKET_TASK_20261004.md',
    'V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md',
]
UPGRADE = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
REPORTS = [
    'STAGE_CONTRACT_AND_AUDIT_ITEMS', 'TARGET_SESSION_SELECTION', 'DAILY_INPUT_REAL_GATE',
    'SOURCE_AUTHORITY_REAL_GATE', 'PREDECESSOR_GATE', 'STORAGE_IDENTITY_GATE',
    'ACTIVATION_CANDIDATE', 'ACTIVATION_PACKET_MANIFEST', 'TARGET_NEGATIVE_MATRIX',
    'F12_GOVERNANCE', 'INDEPENDENT_R25_PREFLIGHT_ORACLE', 'PROTECTED_BYTES',
]


def run():
    for name in DOCUMENTS:
        original = Path('D:/Users/lps/Desktop/阶段任务') / name
        output = 'docs/evidence/r25/' + name
        if (ROOT / output).exists():
            assert (ROOT / output).read_bytes() == original.read_bytes()
        else:
            atomic(output, original.read_bytes(), raw=True)
    before = protected()
    selected = selection()
    assert selected['status'] == 'WAIT_ACCEPTED_DAILY_INPUT'
    assert not (ROOT / 'reports/r25/activation_candidate/authority.json').exists()
    phase0 = read('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json')
    # Stage receipt is already accepted; this task starts no scanner.
    assert phase0['phase0_status'] in ('FULL_PASS', 'DEGRADED_PASS', 'BLOCKED')
    with tempfile.TemporaryDirectory(prefix='r25-vectors-') as temporary:
        cases = [negative(case, Path(temporary) / case) for case in REASONS]
    f12 = f12_governance()
    after = protected()
    assert before == after
    contract = ref('config/v4_16_r25_packet_preflight_v1.json')
    common = dict(status='WAIT_ACCEPTED_DAILY_INPUT', execution_baseline=BASE, target_trade_date=None,
                  REAL_SHADOW_EXECUTION='NOT_STARTED', REAL_SHADOW_OBSERVATIONS=0, PIT_OBSERVED_REAL_SAMPLES=0,
                  external_acceptance=None, execution_authorized=False, NEXT='RETRY_ON_NEXT_ELIGIBLE_ACCEPTED_MARKET_SESSION')
    payloads = {
        'TARGET_SESSION_SELECTION': selected,
        'DAILY_INPUT_REAL_GATE': dict(daily_input_authority=None, daily_input_digest=None, mandatory_families=['TDX_RAW_DAILY', 'ADJUSTED_DAILY', 'OWNER_OUTPUT', 'T0_SNAPSHOT'],
                                     reasons=selected['reasons'], accepted_contract=ref('config/v4_16_go_forward_input_authority_v1.json'), historical_data_head=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json')),
        'SOURCE_AUTHORITY_REAL_GATE': dict(source_authority=None, source_authority_constructed=False, UPSTREAM_SOURCE_ACCEPTANCE_TIMES='NOT_BOUND_NO_ACCEPTED_TARGET_SOURCE',
                                           RUNTIME_FIRST_OBSERVED_AT='NOT_CREATED', readiness_receipts_created=False, reasons=selected['reasons']),
        'PREDECESSOR_GATE': dict(result='NOT_CONSTRUCTED_NO_TARGET_SESSION', first_trade_date=None, previous_trade_date=None, predecessor=None,
                                counts_as_prior_real_observation=False, initialization_contract=ref('config/v4_16_real_initialization_boundary_v1.json')),
        'STORAGE_IDENTITY_GATE': dict(result='NOT_CONSTRUCTED_NO_TARGET_SESSION', database_path=None, database_created=False, database_opened=False,
                                     accepted_storage=ref('config/v4_16_go_forward_storage_v1.json'), migration=ref('migrations/v4_16_r24_real_shadow_v1.sql')),
        'ACTIVATION_CANDIDATE': dict(result='NOT_CONSTRUCTED_NO_ACCEPTED_REAL_DAILY_INPUT', candidate=None, candidate_digest=None,
                                   candidate_file_created=False, committed_disabled_authority=ref('config/v4_16_runtime_activation_authority_v3.json')),
        'ACTIVATION_PACKET_MANIFEST': dict(result='NOT_CONSTRUCTED_NO_ACCEPTED_REAL_DAILY_INPUT', packet_digest=None, authority_digest=None, daily_input_digest=None,
                                         dependency_set_digest=None, non_executable_wait_receipt=True, runtime_dependencies=ref('config/v4_16_runtime_dependencies_v3.json'),
                                         r24r1_tested_source='3eb148c3c19ca079fd5986aeb3a1922b9bf43075', r24r1_tested_tag='refs/tags/codex/r24r1-go-forward-tested-source-20261004-r3',
                                         r24r1_external_acceptance=ref('docs/evidence/r25/'+DOCUMENTS[2])),
        'TARGET_NEGATIVE_MATRIX': dict(result='PASS_LOCAL_ENGINEERING_NEGATIVES_ONLY', count=len(cases), cases=cases, real_packet_tested=False,
                                       synthetic_vectors_location='REMOVED_TEMPORARY_DIRECTORIES', vector_class='ENGINEERING_VECTOR_NOT_REAL', tests=ref('tests/test_r25_packet.py')),
        'F12_GOVERNANCE': dict(result='PASS_LOCAL_ENGINEERING_GOVERNANCE', **f12),
        'INDEPENDENT_R25_PREFLIGHT_ORACLE': dict(result='WAIT_INDEPENDENTLY_RECOMPUTED', validator=ref('scripts/validate_r25_preflight.py'),
                                               writer_imported=False, database_imported=False, persisted_exact_inventory=selected, real_packet_checked=False,
                                               synthetic_target_checks_only=True, target_checks=['calendar_previous_session', 'daily_digest', 'source_manifest', 'nested_source_dates',
                                               'UTC_timestamp_boundary', 'model_parameters', 'capability', 'storage_root', 'predecessor', 'authority_digest', 'dependency_digest', 'protected_state']),
        'PROTECTED_BYTES': dict(result='PASS_LOCAL', before=before, after=after, unchanged=True),
        'STAGE_CONTRACT_AND_AUDIT_ITEMS': dict(stage_contract=contract, task=ref('docs/evidence/r25/'+DOCUMENTS[1]), master=ref('docs/evidence/r25/'+DOCUMENTS[0]),
                                             latest_upgrade_document=ref(UPGRADE), upgrade_sections=['77B', '78'], acceptance='WAIT_ACCEPTED_DAILY_INPUT',
                                             user_authorization='Standing user request to execute supplied stages, then commit relevant code/evidence and push. Documents define task scope; packet preparation only.',
                                             phase0=dict(binding=ref('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'), status=phase0['phase0_status'], scanner_started=False),
                                             r24r1_closed_external_items=['R24_FORWARD_DAILY_INPUT_AUTHORITY', 'R24_COHORT_ENROLLMENT_IDENTITY', 'R24_REALTIME_ADMISSION_WRAPPER_SEMANTICS'],
                                             separate_audit_items=[dict(id='R25_F12_EXPLICIT_BINDING_GOVERNANCE', inherited_external_finding='F12_P2_NONBLOCKING',
                                                                       scope='Existing valid latest.json decoy; exact runtime binding wins; governance ValueError rejection',
                                                                       acceptance='CLOSED_LOCAL_PENDING_EXTERNAL_AUDIT', evidence_path='reports/r25/F12_GOVERNANCE.json')],
                                             unrelated_v4_17_engineering='NOT_BLOCKED_BY_WAIT', v4_17_acceptance_v4_17g='REQUIRES_REAL_SHADOW_EVIDENCE'),
    }
    for name in REPORTS:
        body = dict(common, **{k: v for k,v in payloads[name].items() if k not in common})
        # Preserve the actual target selection status, not engineering test pass as READY.
        body['wait_receipt_digest'] = digest(body)
        atomic('reports/r25/'+name+'.json', body)
    print(dict(status=selected['status'], negative_cases=len(cases), F12=f12['rejection'], real_database_created=False), flush=True)


if __name__ == '__main__':
    run()

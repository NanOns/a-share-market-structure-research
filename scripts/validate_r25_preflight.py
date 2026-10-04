"""Read-only R25 oracle. No runtime, packet writer, input writer or SQLite imports.

Missing exact upstream inputs produce WAIT; no date or filename discovery occurs.
Synthetic REAL-schema vectors are admitted only by the explicit test-only switch.
They can never yield a real READY result.
"""
import hashlib
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '31db7c17463d7a314c4dbfb10023f701c1a9387b'
WAIT = 'WAIT_ACCEPTED_DAILY_INPUT'


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def binding(root, path):
    raw = (Path(root) / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def exact(root, reference, parse=True):
    check(isinstance(reference, dict) and set(reference) == {'path', 'bytes', 'sha256'}, 'EXACT_BINDING_REQUIRED')
    root = Path(root).resolve()
    path = (root / reference['path']).resolve()
    check(path.is_relative_to(root), 'INPUT_OUTSIDE_REPOSITORY')
    check(path.is_file(), 'EXACT_INPUT_UNAVAILABLE')
    check(binding(root, reference['path']) == reference, 'EXACT_BINDING_MISMATCH')
    raw = path.read_bytes()
    return json.loads(raw) if parse else raw


def load(root, path):
    return json.loads((Path(root) / path).read_bytes())


def utc(value):
    check(isinstance(value, str) and value.endswith('Z'), 'UTC_TIMESTAMP_REQUIRED')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def nested_dates(value):
    dates = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('trade_date', 'event_trade_date', 'source_trade_date', 'source_asof', 'evaluation_basis_date', 'max_source_trade_date') and isinstance(item, str):
                date.fromisoformat(item[:10])
                dates.append(item[:10])
            elif isinstance(item, (dict, list)):
                dates.extend(nested_dates(item))
    elif isinstance(value, list):
        for item in value:
            dates.extend(nested_dates(item))
    return dates


def no_runtime_times(value):
    if isinstance(value, dict):
        check(not set(value) & {'first_observed_at', 'RUNTIME_FIRST_OBSERVED_AT', 'integrity_passed_at', 'runtime_readiness_receipt'}, 'RUNTIME_READINESS_PREFILLED')
        for item in value.values():
            no_runtime_times(item)
    elif isinstance(value, list):
        for item in value:
            no_runtime_times(item)


def no_fixture(value):
    if isinstance(value, dict):
        check(not any(value.get(key) for key in ('fixture_only', 'test_vector', 'not_real_evidence')), 'ENGINEERING_INPUT_FORBIDDEN')
        check(value.get('evidence_class') not in ('ACTIVATION_SIMULATION', 'NOT_REAL_EVIDENCE', 'ENGINEERING_VECTOR', 'R23_ISOLATED_SEED'), 'ENGINEERING_INPUT_FORBIDDEN')
        for item in value.values():
            no_fixture(item)
    elif isinstance(value, list):
        for item in value:
            no_fixture(item)


def dependency_digest(deps):
    values = {key: value for key, value in deps.items() if key not in ('activation', 'bindings')}
    values['bindings'] = [b for b in deps['bindings'] if b != deps['activation']]
    return digest(values)


def disabled(authority):
    check(all(authority[k] is False for k in ('runtime_authorized', 'real_shadow_authorized', 'production', 'shadow', 'focus', 'V4_16')), 'COMMITTED_AUTHORITY_MUTATED')
    check(authority['grant'] is None and authority['external_acceptance'] is None, 'COMMITTED_AUTHORITY_MUTATED')
    check(authority['REAL_SHADOW_OBSERVATIONS'] == authority['PIT_OBSERVED_REAL_SAMPLES'] == 0, 'REAL_COUNTERS_CHANGED')


def protected(root=ROOT):
    root = Path(root)
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=root, text=True, encoding='utf8').splitlines()
    # All historical tracked objects are protected, including earlier tests and evidence.
    changed = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=root, text=True, encoding='utf8').splitlines()
    check(not set(names) & set(changed) - {'.gitattributes', 'AGENTS.md'}, 'HISTORICAL_PROTECTED_BYTES_CHANGED')
    original_rules = subprocess.check_output(['git', 'show', BASE+':AGENTS.md'], cwd=root).replace(b'\r\n', b'\n').rstrip()
    current_rules = (root/'AGENTS.md').read_bytes().replace(b'\r\n', b'\n').rstrip()
    check(current_rules.startswith(original_rules+b'\n10. Use E: or F:'), 'EXISTING_PROJECT_GUARDRAILS_CHANGED')
    disabled(load(root, 'config/v4_16_runtime_activation_authority_v3.json'))
    check(not (root / 'data/v4/V4_16_ACCEPTED_HEAD.json').exists(), 'V4_16_ACCEPTED_HEAD_FORBIDDEN')
    check(not (root / 'data/v4/shadow_real_v1').exists(), 'REAL_STORAGE_FORBIDDEN_IN_R25')
    data = load(root, 'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    check(data['accepted_trade_date'] == '2026-09-30', 'PROTECTED_DATA_CHANGED')
    check(load(root, 'data/v4/V4_STAGE_ACCEPTED_HEAD.json')['accepted_stage_range'] == 'V4_00_TO_V4_15_ACCEPTED', 'PROTECTED_STAGE_CHANGED')
    paths = ['data/v4/V4_STAGE_ACCEPTED_HEAD.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json', 'data/v4/V4_15_ACCEPTED_HEAD.json', 'config/v4_16_runtime_activation_authority_v3.json']
    return dict(execution_baseline=BASE, protected_path_count=len(names), historical_git_diff=[], bindings=[binding(root, p) for p in paths],
                Stage='V4_00_TO_V4_15_ACCEPTED', Data='2026-09-30', V4_16_ACCEPTED_HEAD='NOT_CREATED',
                REAL_SHADOW_OBSERVATIONS=0, PIT_OBSERVED_REAL_SAMPLES=0, real_database_created=False)


def inspect_inputs(root, candidate, daily, sources, deps, contract, predecessor, *, test_only=False):
    """Independent target checks; caller supplies exact objects, never implicit heads."""
    if not test_only:
        for value in (candidate, daily, sources, predecessor):
            no_fixture(value)
    no_runtime_times([candidate, daily, sources, predecessor])
    check(candidate.get('external_acceptance') is None and candidate.get('execution_authorized') is False, 'CANDIDATE_EXECUTION_FORBIDDEN')
    check(candidate['environment_class'] == daily['environment_class'] == sources['environment_class'] == 'REAL', 'REAL_ENVIRONMENT_REQUIRED')
    grant = candidate['grant']
    committed = exact(root, deps['activation'])
    disabled(committed)
    check(set(committed['required_grant_fields']) <= grant.keys(), 'GRANT_INCOMPLETE')
    check(candidate['authority_id'] == grant['authority_id'], 'AUTHORITY_IDENTITY_MISMATCH')
    for key in ('clock', 'slot', 'storage', 'source_adapters', 'initialization_boundary'):
        check(grant[key] == deps[key], 'GRANT_DEPENDENCY_MISMATCH')
    check(grant['runtime_dependency_contract_id'] == deps['contract_id'] and grant['dependency_set_digest'] == dependency_digest(deps), 'DEPENDENCY_DIGEST_MISMATCH')
    check(grant['capability_scope'] == ['PURE_CORE_STOCK'], 'CAPABILITY_EXPANSION_FORBIDDEN')
    check(set(deps['blocked_capabilities']) == {'A04_H21_CONSUMER', 'A04_HISTORICAL_AMOUNT_A', 'A08_CURRENT_RUNTIME'}, 'BLOCKED_SCOPE_CHANGED')
    check(set(contract['required_fields']) <= daily.keys() and daily['contract_id'] == contract['contract_id'], 'DAILY_CONTRACT_INCOMPLETE')
    check(daily['daily_input_digest'] == digest({k: v for k, v in daily.items() if k != 'daily_input_digest'}), 'DAILY_DIGEST_MISMATCH')
    check(grant['daily_input_digest'] == daily['daily_input_digest'], 'GRANT_DAILY_INPUT_MISMATCH')
    target = daily['target_trade_date']
    date.fromisoformat(target)
    check(target == grant['target_trade_date'] == grant['effective_trade_date'] == grant['first_trade_date'], 'TARGET_DATE_MISMATCH')
    check(type(daily['revision']) is int and daily['revision'] >= grant['minimum_daily_input_revision'] >= 1, 'DAILY_REVISION_ROLLBACK')
    boundary = utc(grant['daily_input_boundary'])
    clock = exact(root, deps['clock'])
    check(boundary <= utc(target+'T'+clock['scheduled_source_cutoff_utc']), 'DAILY_BOUNDARY_AFTER_SLOT_CUTOFF')
    check(utc(grant['effective_from']) <= utc(daily['accepted_at']) <= boundary, 'DAILY_ACCEPTANCE_BOUNDARY')
    for key, identity in contract['model_identity'].items():
        check(daily[key] == grant[key] == identity, 'MODEL_PARAMETER_MISMATCH')
    check(daily['immutable_algorithm_bindings'] == contract['immutable_algorithm_bindings'], 'IMMUTABLE_ALGORITHM_MISMATCH')
    for reference in daily['immutable_algorithm_bindings'].values():
        exact(root, reference)
    calendar = exact(root, daily['calendar'])
    if not test_only:
        no_fixture(calendar)
    sessions = [item['trade_date'] if isinstance(item, dict) else item for item in calendar['session_dates']]
    check(sessions == sorted(set(sessions)), 'CALENDAR_ORDER')
    check(target in sessions and daily['target_session_confirmed'] is True, 'TARGET_NOT_CONFIRMED')
    index = sessions.index(target)
    check(index > 0 and daily['previous_trade_date'] == sessions[index - 1], 'PREVIOUS_SESSION_MISMATCH')
    identity = exact(root, daily['identity'])
    if not test_only:
        no_fixture(identity)
    check(identity['accepted'] is True and identity['target_trade_date'] == target, 'IDENTITY_NOT_ACCEPTED')
    universe = identity.get('universe')
    check(isinstance(universe, list) and universe and len(universe) == len(set(universe)), 'UNIVERSE_REQUIRED')
    check(daily['membership'] == 'NOT_REQUIRED_FOR_SCOPE' or isinstance(daily['membership'], dict), 'MEMBERSHIP_SCOPE_MISMATCH')
    if isinstance(daily['membership'], dict):
        membership = exact(root, daily['membership'])
        if not test_only:
            no_fixture(membership)
        check(membership['accepted'] is True and membership['target_trade_date'] == target, 'MEMBERSHIP_NOT_ACCEPTED')
    check(set(contract['mandatory_pure_core_sources']) <= daily['sources'].keys(), 'MANDATORY_SOURCE_UNAVAILABLE')
    for family, source in daily['sources'].items():
        check(source['quality'] == 'ACCEPTED' and source['capability'] == 'PURE_CORE_STOCK', 'TARGET_SOURCE_NOT_READY')
        check(source['target_trade_date'] == target and source['max_source_trade_date'] <= target, 'SOURCE_DATE_MISMATCH')
        check(utc(source['provider_observed_at']) <= utc(source['system_available_at']) <= utc(source['accepted_at']) <= boundary, 'SOURCE_TIMESTAMP_BOUNDARY')
        payload = exact(root, source['binding'])
        if not test_only:
            no_fixture(payload)
            check(payload.get('evidence_class') not in ('RECONSTRUCTED_ASOF', 'RECONSTRUCTED', 'CURRENT_MEMBERSHIP_REPLAY'), 'RECONSTRUCTION_IS_NOT_REAL_SOURCE')
        no_runtime_times(payload)
        check(payload['trade_date'] == target and max(nested_dates(payload), default=target) == source['max_source_trade_date'] <= target, 'NESTED_SOURCE_FUTURE_OR_MISMATCH')
    check(daily['source_manifest_digest'] == digest(daily['sources']), 'SOURCE_MANIFEST_DIGEST_MISMATCH')
    check(daily['max_source_trade_date'] == max(s['max_source_trade_date'] for s in daily['sources'].values()) <= target, 'MAX_SOURCE_DATE_MISMATCH')
    check(daily['quality_capability_matrix'] == {k: dict(quality=v['quality'], capability=v['capability']) for k, v in daily['sources'].items()}, 'QUALITY_MATRIX_MISMATCH')
    package = exact(root, daily['day_package'])
    if not test_only:
        no_fixture(package)
    check(package['trade_date'] == target and package['snapshot_identity'] == daily['snapshot_identity'] and package['sources'] == daily['sources'], 'STALE_DAY_PACKAGE')
    check(sources['adapter_id'] == exact(root, deps['source_adapters'])['adapter_id'] and sources['owner_heads'] == deps['owner_heads'], 'SOURCE_AUTHORITY_IDENTITY')
    check(set(sources['sources']) == {'OWNER_OUTPUT', 'T0_SNAPSHOT'}, 'RUNTIME_SOURCE_SET')
    for family, source in sources['sources'].items():
        check(source['binding'] == daily['sources'][family]['binding'] and source['target_trade_date'] == target, 'SOURCE_AUTHORITY_DATE_BINDING')
        check(all(source.get(key) for key in ('source_identity', 'source_revision', 'provider')), 'SOURCE_PROVIDER_IDENTITY')
    check(sources.get('future_settlement_source_policy') == 'EXACT_ACCEPTED_DUE_ENDPOINT_ONLY_NO_PREFETCH', 'SETTLEMENT_POLICY_REQUIRED')
    storage = exact(root, deps['storage'])
    ident = grant['storage_identity']
    path = (Path(root) / ident['database_path']).resolve()
    check(not any(word in ident['database_path'].lower() for word in ('engineering', 'simulation', 'legacy')), 'STORAGE_CLASS_COLLISION')
    check(path.is_relative_to((Path(root) / storage['real_root']).resolve()) and path != (Path(root) / storage['real_root']).resolve(), 'STORAGE_OUTSIDE_REAL_ROOT')
    check(not path.exists(), 'REAL_DATABASE_ALREADY_EXISTS')
    check((ident['namespace'], ident['execution_mode'], ident['evidence_origin']) == ('SHADOW_V4', 'SHADOW', 'PIT_OBSERVED') and ident['migration'] == deps['migration'], 'STORAGE_IDENTITY_MISMATCH')
    check(grant['expected_prior_activation_head'] is None and grant['rollback_identity'] == 'R24_APPEND_ONLY_STOP_V1', 'PRIOR_OR_ROLLBACK_MISMATCH')
    init = exact(root, deps['initialization_boundary'])
    check(predecessor['trade_date'] == daily['previous_trade_date'] and predecessor['namespace'] == 'SHADOW_V4' and predecessor['evidence_class'] in init['predecessor_evidence_classes'], 'PREDECESSOR_MISMATCH')
    check(predecessor.get('counts_as_prior_real_observation') is False, 'PREDECESSOR_COUNTED_AS_REAL')
    check(all(predecessor.get(key) == grant[key] for key in ('model_contract_id', 'parameter_set_id', 'state_lineage_id')) and 'owner_state' in predecessor, 'PREDECESSOR_IDENTITY')
    check(not any(predecessor.get(key) is not None for key in init['unknown_fields']), 'PREDECESSOR_REAL_HISTORY_FORBIDDEN')
    return dict(status='PASS_ENGINEERING_VECTOR_NOT_REAL' if test_only else 'PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT', target_trade_date=target, previous_trade_date=daily['previous_trade_date'], daily_input_digest=daily['daily_input_digest'], authority_digest=digest({k: v for k, v in candidate.items() if k != 'external_acceptance'}), dependency_set_digest=dependency_digest(deps), execution_authorized=False)


def selection(root=ROOT, exact_daily_input=None):
    """Inventory is restricted to the externally bound heads; no implicit search."""
    state = protected(root)
    deps = load(root, 'config/v4_16_runtime_dependencies_v3.json')
    for reference in deps['bindings']:
        exact(root, reference, parse=False)
    data = exact(root, deps['accepted_data'])
    contract = exact(root, deps['go_forward_input'])
    check(contract['frozen_data_head_role'] == 'HISTORICAL_ACCEPTANCE_ONLY' and contract['implicit_resolution'] == 'FORBIDDEN', 'INPUT_SELECTION_POLICY_CHANGED')
    check(exact_daily_input is None, 'EXPLICIT_INPUT_REQUIRES_COMPLETE_TARGET_PACKET_PREFLIGHT')
    return dict(status=WAIT, target_trade_date=None, previous_trade_date=None, selected_from_wall_clock=False,
                input_selection='EXPLICIT_ACCEPTED_BINDINGS_ONLY', exact_daily_input_authority=None,
                inventory=[deps['accepted_data'], deps['go_forward_input'], deps['activation']],
                historical_accepted_trade_date=data['accepted_trade_date'],
                reasons=['NO_EXACT_ACCEPTED_REAL_SESSION_DAILY_INPUT_SUPPLIED', 'FROZEN_DATA_HEAD_IS_HISTORICAL_ONLY', 'NO_TARGET_DATE_ACCEPTED_OWNER_OUTPUT_AND_T0_SNAPSHOT_BOUND_TO_REAL_AUTHORITY'],
                excluded_inputs=['R23_ISOLATED_SEED', 'R24_ACTIVATION_SIMULATION', 'R24R1_ACTIVATION_SIMULATION', 'LEGACY_PRIOR'],
                protected=state, next='RETRY_ON_NEXT_ELIGIBLE_ACCEPTED_MARKET_SESSION')


def inspect_packet(root, manifest_binding):
    """Complete real packet verification, never creates source receipts or storage."""
    protected(root)
    manifest = exact(root, manifest_binding)
    check(manifest['packet_digest'] == digest({k: v for k, v in manifest.items() if k != 'packet_digest'}), 'PACKET_DIGEST_MISMATCH')
    deps = exact(root, manifest['runtime_dependencies'])
    check(manifest['runtime_dependencies'] == binding(root, 'config/v4_16_runtime_dependencies_v3.json'), 'ACCEPTED_DEPENDENCIES_REQUIRED')
    for reference in deps['bindings']:
        exact(root, reference, parse=False)
    check(manifest['go_forward_contract'] == deps['go_forward_input'], 'GO_FORWARD_CONTRACT_MISMATCH')
    candidate = exact(root, manifest['activation_candidate'])
    check(manifest['activation_candidate']['path'].startswith('reports/r25/activation_candidate/'), 'CANDIDATE_PATH_REQUIRED')
    grant = candidate['grant']
    check(manifest['daily_input_authority'] == grant['daily_input_authority'] and manifest['source_authority'] == grant['source_authority'] and manifest['predecessor'] == grant['predecessor'], 'PACKET_BINDING_MISMATCH')
    result = inspect_inputs(root, candidate, exact(root, grant['daily_input_authority']), exact(root, grant['source_authority']), deps, exact(root, deps['go_forward_input']), exact(root, grant['predecessor']))
    for key in ('authority_digest', 'daily_input_digest', 'dependency_set_digest'):
        check(manifest[key] == result[key], 'PACKET_' + key.upper() + '_MISMATCH')
    check(manifest['storage_identity'] == grant['storage_identity'] and manifest['initialization_boundary'] == deps['initialization_boundary'] and manifest['rollback_identity'] == grant['rollback_identity'], 'PACKET_LAUNCH_IDENTITIES')
    check(manifest['protected_state'] == protected(root), 'PACKET_PROTECTED_STATE_MISMATCH')
    check(manifest['r24r1_tested_source'] == '3eb148c3c19ca079fd5986aeb3a1922b9bf43075' and manifest['r24r1_tested_tag'] == 'refs/tags/codex/r24r1-go-forward-tested-source-20261004-r3', 'ACCEPTED_SOURCE_IDENTITY')
    check(manifest['r24r1_external_acceptance'] == binding(root, 'docs/evidence/r25/V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'), 'EXTERNAL_AUDIT_BINDING')
    return dict(result, packet_digest=manifest['packet_digest'], real_shadow_execution='NOT_STARTED')

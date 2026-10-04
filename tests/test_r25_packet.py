"""R25 fail-closed vectors and F12 exact-binding governance.

REAL-schema vectors live only in pytest temporary directories. Their explicit
ENGINEERING_VECTOR marker forbids production preflight and real READY claims.
"""
import ast
import copy
import json
from pathlib import Path

import pytest
from scripts.validate_r25_preflight import ROOT, digest, binding, inspect_inputs, disabled, selection, exact, no_fixture

REASONS = {
    'R25-01': 'TARGET_SOURCE_NOT_READY',
    'R25-02': 'STALE_DAY_PACKAGE',
    'R25-03': 'TARGET_NOT_CONFIRMED',
    'R25-04': 'PREVIOUS_SESSION_MISMATCH',
    'R25-05': 'DAILY_DIGEST_MISMATCH',
    'R25-06': 'NESTED_SOURCE_FUTURE_OR_MISMATCH',
    'R25-07': 'MODEL_PARAMETER_MISMATCH',
    'R25-08': 'CAPABILITY_EXPANSION_FORBIDDEN',
    'R25-09': 'STORAGE_OUTSIDE_REAL_ROOT',
    'R25-10': 'STORAGE_CLASS_COLLISION',
    'R25-11': 'PREDECESSOR_MISMATCH',
    'R25-12': 'PREDECESSOR_COUNTED_AS_REAL',
    'R25-13': 'RUNTIME_READINESS_PREFILLED',
    'R25-14': 'CANDIDATE_EXECUTION_FORBIDDEN',
    'R25-15': 'COMMITTED_AUTHORITY_MUTATED',
    'R25-16': 'GRANT_DAILY_INPUT_MISMATCH',
}


def vector(root):
    """Synthetic protocol vector, never a real daily input or activation packet."""
    from scripts.validate_r25_preflight import dependency_digest
    root = Path(root)

    def put(path, value):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, sort_keys=True), encoding='utf8')
        return binding(root, path)

    deps = json.loads((ROOT / 'config/v4_16_runtime_dependencies_v3.json').read_bytes())
    contract = json.loads((ROOT / deps['go_forward_input']['path']).read_bytes())
    refs = [deps[k] for k in ('activation', 'storage', 'source_adapters', 'initialization_boundary', 'clock')]
    refs += list(contract['immutable_algorithm_bindings'].values())
    for reference in refs:
        target = root / reference['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / reference['path']).read_bytes())
    target, previous = '2030-01-03', '2030-01-02'  # fictional vector sessions, never target selection
    sources = {}
    for family in contract['mandatory_pure_core_sources']:
        sources[family] = dict(binding=put(f'vector/{family}.json', dict(trade_date=target, rows=[dict(trade_date=target)], evidence_class='ENGINEERING_VECTOR')),
                               target_trade_date=target, max_source_trade_date=target, provider_observed_at=target+'T00:01:00Z', system_available_at=target+'T00:02:00Z', accepted_at=target+'T00:03:00Z', quality='ACCEPTED', capability='PURE_CORE_STOCK')
    daily = dict(contract_id=contract['contract_id'], daily_input_id='R25_ENGINEERING_VECTOR', revision=1, target_trade_date=target, previous_trade_date=previous,
                 target_session_confirmed=True, accepted_at=target+'T00:04:00Z', environment_class='REAL', test_vector=True, evidence_class='ENGINEERING_VECTOR',
                 calendar=put('vector/calendar.json', dict(session_dates=[previous, target], fixture_only=True)),
                 identity=put('vector/identity.json', dict(accepted=True, target_trade_date=target, universe=['VECTOR_STOCK'])), membership='NOT_REQUIRED_FOR_SCOPE', sources=sources,
                 snapshot_identity='ENGINEERING_VECTOR_ONLY', max_source_trade_date=target, source_manifest_digest=digest(sources),
                 quality_capability_matrix={k: dict(quality=v['quality'], capability=v['capability']) for k,v in sources.items()},
                 day_package=put('vector/package.json', dict(trade_date=target, sources=sources, snapshot_identity='ENGINEERING_VECTOR_ONLY')),
                 immutable_algorithm_bindings=contract['immutable_algorithm_bindings'], **contract['model_identity'])
    daily['daily_input_digest'] = digest(daily)
    source_authority = dict(environment_class='REAL', evidence_class='ENGINEERING_VECTOR', adapter_id='ACCEPTED_LOCAL_EXACT_BYTES_V1', owner_heads=deps['owner_heads'],
                            future_settlement_source_policy='EXACT_ACCEPTED_DUE_ENDPOINT_ONLY_NO_PREFETCH',
                            sources={k: dict(binding=sources[k]['binding'], target_trade_date=target, source_identity='VECTOR_'+k, source_revision='VECTOR_R1', provider='ENGINEERING_VECTOR_ONLY') for k in ('OWNER_OUTPUT', 'T0_SNAPSHOT')})
    predecessor = dict(trade_date=previous, namespace='SHADOW_V4', evidence_class='RECONSTRUCTED_ASOF', test_vector=True, counts_as_prior_real_observation=False,
                       state_lineage_id='VECTOR_LINEAGE', owner_state={}, **contract['model_identity'])
    grant = dict(authority_id='R25_VECTOR_ONLY', effective_trade_date=target, target_trade_date=target, first_trade_date=target, effective_from=target+'T00:00:00Z',
                 daily_input_boundary=target+'T01:00:00Z', minimum_daily_input_revision=1, daily_input_authority=put('vector/daily.json', daily), daily_input_digest=daily['daily_input_digest'],
                 state_lineage_id='VECTOR_LINEAGE', capability_scope=['PURE_CORE_STOCK'], runtime_dependency_contract_id=deps['contract_id'], dependency_set_digest=dependency_digest(deps),
                 source_authority=put('vector/sources.json', source_authority), predecessor=put('vector/predecessor.json', predecessor),
                 rollback_identity='R24_APPEND_ONLY_STOP_V1', expected_prior_activation_head=None,
                 storage_identity=dict(database_path='data/v4/shadow_real_v1/VECTOR_NEVER_CREATED.sqlite', namespace='SHADOW_V4', execution_mode='SHADOW', evidence_origin='PIT_OBSERVED', migration=deps['migration']),
                 **contract['model_identity'], **{k: deps[k] for k in ('clock', 'slot', 'storage', 'source_adapters', 'initialization_boundary')})
    candidate = dict(authority_id=grant['authority_id'], environment_class='REAL', evidence_class='ENGINEERING_VECTOR', external_acceptance=None, execution_authorized=False, grant=grant)
    return dict(root=root, candidate=candidate, daily=daily, sources=source_authority, deps=deps, contract=contract, predecessor=predecessor, put=put)


def invoke(v):
    return inspect_inputs(v['root'], *[v[k] for k in ('candidate', 'daily', 'sources', 'deps', 'contract', 'predecessor')], test_only=True)


def negative(case, root):
    v = vector(root)
    d, g, p, put = v['daily'], v['candidate']['grant'], v['predecessor'], v['put']
    if case == 'R25-01': d['sources']['OWNER_OUTPUT']['quality'] = 'NOT_READY'
    if case == 'R25-02':
        package = exact(root, d['day_package']); package['trade_date'] = d['previous_trade_date']
        d['day_package'] = put('vector/package.json', package)
    if case == 'R25-03': d['calendar'] = put('vector/calendar.json', dict(session_dates=[d['previous_trade_date']], fixture_only=True))
    if case == 'R25-04': d['previous_trade_date'] = '2030-01-01'
    if case == 'R25-05': d['daily_input_digest'] = '0'*64
    if case == 'R25-06':
        s = d['sources']['OWNER_OUTPUT']; payload = exact(root, s['binding'])
        payload['rows'][0]['trade_date'] = '2030-01-04'; s['binding'] = put('vector/OWNER_OUTPUT.json', payload)
    if case == 'R25-07': d['parameter_set_id'] = 'OTHER'
    if case == 'R25-08': g['capability_scope'].append('SECTOR_ENHANCED')
    if case == 'R25-09': g['storage_identity']['database_path'] = 'data/v4/other_root/future.sqlite'
    if case == 'R25-10': g['storage_identity']['database_path'] = 'reports/r24r1/activation_simulation/decoy.sqlite'
    if case == 'R25-11': p['trade_date'] = '2030-01-01'
    if case == 'R25-12': p['counts_as_prior_real_observation'] = True
    if case == 'R25-13': v['sources']['sources']['OWNER_OUTPUT']['first_observed_at'] = '2030-01-03T00:00:00Z'
    if case == 'R25-14': v['candidate']['external_acceptance'] = dict(decision='PREFILLED')
    if case == 'R25-15':
        a = exact(root, v['deps']['activation']); a['grant'] = dict(prefilled=True)
        v['deps']['activation'] = put(v['deps']['activation']['path'], a)
    if case == 'R25-16':
        decoy = copy.deepcopy(d); decoy['daily_input_id'] = 'VALID_DECOY_DIFFERENT_EXACT_ID'
        decoy['daily_input_digest'] = digest({k: value for k, value in decoy.items() if k != 'daily_input_digest'})
        put('vector/latest.json', decoy)
        d.update(decoy)  # grant retains the original daily digest
    if case not in ('R25-05', 'R25-16'):
        d['source_manifest_digest'] = digest(d['sources'])
        d['quality_capability_matrix'] = {k: dict(quality=s['quality'], capability=s['capability']) for k,s in d['sources'].items()}
        d['daily_input_digest'] = digest({k: value for k, value in d.items() if k != 'daily_input_digest'})
        g['daily_input_digest'] = d['daily_input_digest']
    with pytest.raises(ValueError, match='^'+REASONS[case]+'$') as caught:
        invoke(v)
    assert not (root / 'data/v4/shadow_real_v1').exists()
    return dict(case=case, status='PASS_ENGINEERING_NEGATIVE_NOT_REAL', rejection=str(caught.value), real_storage_opened=False)


@pytest.mark.parametrize('case', list(REASONS))
def test_target_negative(case, tmp_path):
    negative(case, tmp_path)


def test_vector_is_positive_only_in_test_mode(tmp_path):
    v = vector(tmp_path)
    assert invoke(v)['status'] == 'PASS_ENGINEERING_VECTOR_NOT_REAL'
    with pytest.raises(ValueError, match='ENGINEERING_INPUT_FORBIDDEN'):
        inspect_inputs(tmp_path, *[v[k] for k in ('candidate', 'daily', 'sources', 'deps', 'contract', 'predecessor')])


def f12_governance():
    # Accepted simulation runtime is exercised; no real-mode writer is launched.
    from scripts.r24r1_simulation import prepare, controller, regrant
    from scripts.r24r1_io import read, atomic
    x = prepare()
    deps = read(x['manifest']); grant = read(deps['activation']['path'])['grant']
    original = read(grant['daily_input_authority']['path'])
    decoy = copy.deepcopy(original); decoy['daily_input_id'] += '_VALID_DECOY'
    decoy['daily_input_digest'] = digest({k: value for k, value in decoy.items() if k != 'daily_input_digest'})
    decoy_ref = atomic(x['base'] + '/latest.json', decoy)
    c = controller(x)
    assert c.authority.daily == original and c.authority.daily != decoy
    # Existing, internally valid decoy is bound explicitly, retaining the old grant digest.
    regrant(x, lambda a: a['grant'].update(daily_input_authority=decoy_ref))
    with pytest.raises(ValueError, match='^GRANT_DAILY_INPUT_MISMATCH$') as caught:
        controller(x)
    assert not (ROOT / x['database']).exists()
    return dict(status='PASS_ENGINEERING_SIMULATION_NOT_REAL', decoy_exists=True, decoy_internally_valid=True,
                exact_binding_wins=True, decoy_differs_from_exact_binding=True, rejection=str(caught.value),
                FileNotFoundError=False, real_database_created=False, runtime_changed=False)


def test_f12_valid_latest_decoy():
    f12_governance()


def test_oracle_has_no_writer_or_sqlite_imports():
    tree = ast.parse((ROOT / 'scripts/validate_r25_preflight.py').read_text(encoding='utf8'))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom): names.append(node.module or '')
        if isinstance(node, ast.Import): names.extend(a.name for a in node.names)
    assert not any(any(word in name for word in ('runtime', 'simulation', 'r25_io', 'sqlite', 'go_forward', 'test_')) for name in names)


def test_actual_authority_inventory_waits_without_target():
    result = selection()
    assert result['status'] == 'WAIT_ACCEPTED_DAILY_INPUT' and result['target_trade_date'] is None


def test_user_c_drive_temporary_space_prohibition():
    from scripts.r25_clean_checkout import approved_directory
    with pytest.raises(ValueError, match='USER_REQUIRES_TEMPORARY_SPACE_ON_E_OR_F'):
        approved_directory('C:/Users/lps/r25-temporary-space-must-not-be-created')


@pytest.mark.parametrize('field', ['source', 'daily'])
def test_fractional_boundary_rejected(field, tmp_path):
    v = vector(tmp_path)
    if field == 'source':
        v['daily']['sources']['OWNER_OUTPUT']['accepted_at'] = '2030-01-03T01:00:00.001Z'
    else:
        v['daily']['accepted_at'] = '2030-01-03T01:00:00.001Z'
    d = v['daily']; d['daily_input_digest'] = digest({k: value for k,value in d.items() if k != 'daily_input_digest'})
    v['candidate']['grant']['daily_input_digest'] = d['daily_input_digest']
    with pytest.raises(ValueError, match='SOURCE_TIMESTAMP_BOUNDARY' if field == 'source' else 'DAILY_ACCEPTANCE_BOUNDARY'):
        invoke(v)

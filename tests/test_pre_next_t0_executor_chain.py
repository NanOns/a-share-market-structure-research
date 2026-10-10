"""Real execute_sources -> capture -> Owner adapter -> reconcile, synthetic IO."""
import json
from datetime import datetime, timezone
import pytest
from test_cross_day_capture_repair_v1 import chain
from workbench_analysis import operational_daily_executor_v1 as executor
from workbench_analysis import operational_daily_owner_v1 as owner
from workbench_analysis import operational_successor_release_v1 as release
from workbench_analysis import producer_bootstrap_v1 as bootstrap
from workbench_analysis import tdx_local_daily_fallback_v1 as fallback
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.r43_owner_replay import ref
from scripts import audit_dynamic_daily_period_numbers_v1 as oracle


@pytest.mark.parametrize('gate_ready', [False, True])
def test_full_executor_entry(chain, monkeypatch, gate_ready):
    root, day, freeze, new_head, _ = chain
    artifact = json.loads((root/freeze['path']).read_bytes())
    now = datetime.now(timezone.utc).isoformat()
    package = dict(download={'synthetic': True}, provider_package_date=day, observed_at=now)
    bars = dict(status='TARGET_BARS_EXTRACTED', artifact=artifact['tdx'], source_available_at=now, row_count=2)
    folder = root/'kernel'; (folder/'sources').mkdir(parents=True)
    (folder/'sources/gbbq').write_bytes(b'SYNTHETIC_GBBQ')
    candidate_binding = new_head()
    candidate = json.loads((root/candidate_binding['path']).read_bytes())
    candidate['predecessor'] = ref(root, root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    candidate['day_receipt'] = publish(root, 'inputs/day_receipt.json', {'synthetic_only': True})
    sealed = root/'inputs/sealed.json'; atomic_json(root, sealed, candidate)
    before = (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    calls = []
    monkeypatch.setattr(executor, 'source_readiness', lambda *a: {'time_eligible': True})
    monkeypatch.setattr(executor, 'capture_latest_tdx_package', lambda **k: package)
    monkeypatch.setattr(executor, 'extract_target_session_bars', lambda *a, **k: bars)
    smoke = root/'inputs/sdk_live_smoke_receipt.json'
    daily = artifact['normalized']['daily']['rows']
    raw = dict(target_date=day, observed_at=now, requested_at=now, daily_rows=daily,
               adjustment_factor_rows=[], daily_metadata={}, adjustment_factor_metadata={})
    atomic_json(root, smoke.with_name('sdk_raw_responses.json'), raw)
    atomic_json(root, smoke, dict(observed_at=now))
    manifest = dict(auth_mode='SYNTHETIC', smoke_receipt=ref(root, smoke), live_smoke=dict(target_date=day,
        daily={'response_sha256': executor._canonical_rows_digest(daily)},
        adjustment_factor={'response_sha256': executor._canonical_rows_digest([])}))
    manifest_path = root/'reports/v4_baostock/runtime_acceptance'/day.replace('-', '')/'accepted_runtime_manifest.json'
    atomic_json(root, manifest_path, manifest)
    atomic_json(root, smoke.with_name('sdk_accepted_runtime_manifest.json'), manifest)
    atomic_json(root, root/'config/baostock_dm01_sdk_schema_adapter_v2.json', {})
    monkeypatch.setattr(executor, 'load_runtime_acceptance_manifest', lambda *a, **k: manifest)
    monkeypatch.setattr(executor, 'runtime_acceptance_error', lambda *a, **k: None)
    monkeypatch.setattr(executor, 'package_metadata', lambda: {})
    monkeypatch.setattr(executor, 'normalize_response', lambda rows, *a, **k: (rows, {}))
    monkeypatch.setattr(fallback, 'fallback', lambda p, b, *a, **k: (p, b, None))
    def gate(root, day, artifact, result):
        assert result['first_capture_source_candidate']['candidate']
        calls.append('SOURCE_CAPTURED_BEFORE_GATE')
        deps = {k: candidate_binding for k in ('parent_head', 'lifecycle', 'identity', 'membership_snapshot')}
        deps['gbbq'] = dict(ref(root, folder/'sources/gbbq'), path=str(folder/'sources/gbbq'))
        ready = publish(root, 'inputs/ready.json', dict(source_ready=True, source_freeze=result['source_freeze'], dependency_bindings=deps))
        return dict(result, source_readiness=ready), dict(source_ready=gate_ready, status='WAIT_BAOSTOCK_DAILY', reason='SYNTHETIC_GATE')
    monkeypatch.setattr(executor, 'verify_source_gate', gate)
    def prepare(root, freeze_binding):
        assert gate_ready
        calls.append('OWNER_PREPARE')
        return dict(folder=folder, dates=[day], mappings={}, snapshot=candidate['membership_snapshot'], seed_registry={}, freeze=freeze_binding)
    monkeypatch.setattr(owner, 'prepare', prepare)
    monkeypatch.setattr(owner, 'replay', lambda *a, **k: calls.append('NUMERIC_KERNEL_SYNTHETIC_IO'))
    monkeypatch.setattr(owner, 'seal', lambda *a, **k: (candidate, ref(root, sealed)))
    def audit(*a):
        atomic_json(root, folder/'PERIOD_NUMERIC_ORACLE.json', {'synthetic_only': True})
        return {'acceptance': 'PASS'}
    monkeypatch.setattr(oracle, 'audit', audit)
    monkeypatch.setattr(bootstrap, 'produce_daily_state', lambda *a: candidate_binding)
    monkeypatch.setattr(bootstrap, 'produce_daily_sector', lambda *a: candidate_binding)
    monkeypatch.setattr(release, 'promote', lambda *a, **k: pytest.fail('NO_REAL_CAS_OR_GRANT'))
    result = executor.execute_sources(root, day, 'EXECUTE')
    assert (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes() == before
    assert result['first_capture_source_candidate']['candidate']
    if gate_ready:
        assert 'OWNER_PREPARE' in calls
        strict = result['producer_review_candidates']['candidate']['strict_source']['candidate']
        receipt = json.loads((root/strict['path']).read_bytes())
        assert receipt['scope_reconciliation']['status'] == 'SAME_DAY_SCOPE_RECONCILED'
        assert result['status'] == 'QA_BLOCKED'
    else:
        assert result['status'] == 'WAIT_BAOSTOCK_DAILY'
        assert calls == ['SOURCE_CAPTURED_BEFORE_GATE']

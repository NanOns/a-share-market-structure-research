"""Daily candidate adapter tests; synthetic bytes never issue real authority."""
import hashlib
import json
import pytest
from test_cohort_capture_readiness_r1 import fixture
from workbench_analysis.cohort_capture_readiness_r1 import inspect_daily_candidate


def daily_fixture(root, missing=(), target=None, patch=None):
    args = fixture(root, target, patch)
    path = root / args['accepted_head']['path']
    candidate = json.loads(path.read_bytes())
    candidate['accepted_trade_date'] = args['trade_date']
    for key in missing:
        candidate.pop(key)
    path.write_text(json.dumps(candidate), encoding='utf8')
    return dict(root=root, candidate_binding=dict(path=path.name,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
        trade_date=args['trade_date'], cutoff=args['cutoff'])


@pytest.mark.parametrize('missing', [
    ('owners',), ('cohort_capture_receipts',), ('cohort_write_grants',),
    ('owners', 'cohort_capture_receipts', 'cohort_write_grants'),
])
def test_missing_real_artifacts_preserves_local_flow(tmp_path, missing):
    result = inspect_daily_candidate(**daily_fixture(tmp_path, missing))
    assert result['status'] == 'SOURCE_INCOMPLETE'
    assert result['observed_count'] is None
    assert result['preflight_invoked'] is False
    assert result['blocks_local_daily_publication'] is False


@pytest.mark.parametrize('target,patch', [
    ('grant', {'capability': 'READ_STATISTICS'}),
    ('grant', {'revision': 'r2'}),
    ('grant', {'revoked': True}),
    ('receipt', {'scope': 'FOCUS_TOP_K'}),
    ('row', {'evidence_class': 'RECONSTRUCTED_ASOF'}),
])
def test_denial_is_visible_without_granting_or_blocking(tmp_path, target, patch):
    result = inspect_daily_candidate(**daily_fixture(tmp_path, target=target, patch=patch))
    assert result['status'] == 'CAPTURE_PREFLIGHT_REJECTED'
    assert result['reason']
    assert result['production_write_authorized'] is False
    assert result['blocks_local_daily_publication'] is False


def test_complete_synthetic_candidate_is_isolated_only(tmp_path):
    args = daily_fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = inspect_daily_candidate(**args)
    assert result['status'] == 'ISOLATED_CAPTURE_CANDIDATE_READY'
    assert result['preflight']['eligible_count'] == 1
    assert result['production_write_authorized'] is False
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_exact_candidate_digest_required(tmp_path):
    args = daily_fixture(tmp_path)
    (tmp_path / args['candidate_binding']['path']).write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        inspect_daily_candidate(**args)


def test_target_day_mismatch_is_not_treated_as_missing_source(tmp_path):
    args = daily_fixture(tmp_path)
    args['trade_date'] = '2026-10-09'
    with pytest.raises(ValueError, match='DATE_MISMATCH'):
        inspect_daily_candidate(**args)


def test_actual_daily_executor_surfaces_capture_boundary_before_publication(tmp_path, monkeypatch):
    from workbench_analysis import operational_daily_executor_v1 as executor
    from workbench_analysis import operational_daily_ready_owner_v2 as adapter
    from workbench_analysis import operational_successor_release_v1 as release
    from scripts import audit_dynamic_daily_period_numbers_v1 as oracle
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_analysis.r43_owner_replay import ref
    day = '2026-09-30'
    freeze = tmp_path / 'freeze.json'
    atomic_json(tmp_path, freeze, {'synthetic_only': True})
    binding = ref(tmp_path, freeze)
    monkeypatch.setattr(executor, 'verify_source_gate',
        lambda root, day, artifact, result: (dict(result, source_readiness=binding), {'source_ready': True}))
    monkeypatch.setattr(adapter, 'build',
        lambda *args, **kwargs: ({}, {'folder': tmp_path}))
    candidate = dict(accepted_trade_date=day, owners={day: {}}, predecessor={'sha256': 'a'*64})
    path = tmp_path / 'candidate.json'
    atomic_json(tmp_path, path, candidate)
    monkeypatch.setattr(adapter, 'seal', lambda *args: (candidate, ref(tmp_path, path)))
    atomic_json(tmp_path, tmp_path / 'PERIOD_NUMERIC_ORACLE.json', {'synthetic_only': True})
    monkeypatch.setattr(oracle, 'audit', lambda *args: {'acceptance': 'PASS'})
    monkeypatch.setattr(release, 'promote', lambda *args: pytest.fail('UNAUTHORIZED_REAL_CAS'))
    stages = []
    result = executor.derive_ready_sources(tmp_path, day, {'source_freeze': binding},
        progress=lambda d, s, r: stages.append((s, r)))
    assert result['status'] == 'QA_BLOCKED'
    assert result['cohort_capture_readiness']['status'] == 'SOURCE_INCOMPLETE'
    assert stages[-1][0] == 'DERIVED_READY'
    assert stages[-1][1]['cohort_capture_readiness']['observed_count'] is None

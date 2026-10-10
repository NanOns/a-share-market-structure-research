import gzip
import json
from datetime import datetime
from pathlib import Path
import pytest
from workbench_analysis.full_market_state_publisher_v1 import build
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.r43_owner_replay import ref
from sector.d2_research_source_matrix_v1 import build as matrix

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def publisher_inputs(tmp_path):
    from v4.confirmation import package
    contract, manifest, _, _, _ = package()
    paths = [contract[k]['path'] for k in ('parameters', 'machine_ast', 'legacy_manifest')]
    paths += [manifest['legacy_source']['path'], 'src/workbench_analysis/full_market_state_publisher_v1.py',
              'src/workbench_analysis/r43_focus_replay.py']
    for path in paths:
        target = tmp_path/path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/path).read_bytes())
    head = json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    row = json.loads(gzip.open(ROOT/head['owners']['2026-10-09']['prewatch']['path'], 'rt', encoding='utf8').readline())
    def candidate(rows, ids=None, suffix='base'):
        path = tmp_path/('facts_' + suffix + '.gz')
        path.write_bytes(gzip.compress(b'\n'.join(json.dumps(r).encode() for r in rows)))
        binding = ref(tmp_path, path)
        life = publish(tmp_path, 'life_' + suffix + '.json', {'active_security_ids': ids or [row['security_id']]})
        members = publish(tmp_path, 'members_' + suffix + '.json', {'synthetic': True})
        return publish(tmp_path, 'head_' + suffix + '.json', dict(accepted_trade_date='2026-10-09',
            owners={'2026-10-09': dict(prewatch=binding, core=binding, lifecycle=life)}, membership_snapshot=members))
    return tmp_path, row, candidate


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'foreign', 'future_window', 'cached_status'])
def test_cross_universe_facts_and_contamination(publisher_inputs, change):
    root, row, candidate = publisher_inputs
    rows = [row]
    ids = [row['security_id'], 'SYNTHETIC_NEW_SECURITY'] if change == 'missing' else None
    if change == 'duplicate': rows *= 2
    if change == 'foreign': ids = ['SYNTHETIC_OTHER_UNIVERSE']
    if change == 'future_window': row['target_values']['window_end_trade_date'] = '2026-10-12'
    if change == 'cached_status': row['confirmation']['scenario_evidence'][0]['status'] = 'FALSE'
    binding = candidate(rows, ids)
    if change in ('duplicate', 'foreign', 'future_window'):
        with pytest.raises(ValueError): build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1')
        return
    output = build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1')
    data = json.loads(gzip.decompress((root/output['path']).read_bytes()))
    if change == 'missing':
        unknown = [r for r in data['scenario_outputs'] if r['security_id'] == 'SYNTHETIC_NEW_SECURITY']
        assert len(unknown) == 4 and all(r['state'] == 'UNKNOWN' for r in unknown)
    else:
        assert data['scenario_outputs'][0]['state'] == 'TRUE'


def test_independent_clock_and_historical_laundering(publisher_inputs):
    root, row, candidate = publisher_inputs
    binding = candidate([row])
    now = datetime.fromisoformat('2026-10-09T18:35:00+08:00')
    with pytest.raises(ValueError, match='RECONSTRUCTED'):
        build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1',
              observation_binding=binding, clock=lambda: now)
    row.update(AS_RECORDED=True, PIT_ELIGIBLE=True)
    binding = candidate([row], suffix='observed-synthetic')
    head = json.loads((root/binding['path']).read_bytes())
    observation = publish(root, 'observation.json', dict(T0='2026-10-09',
        sources=dict(facts=head['owners']['2026-10-09']['prewatch'], lifecycle=head['owners']['2026-10-09']['lifecycle'], membership=head['membership_snapshot']),
        cutoff=now.isoformat(), receipts=[dict(source='facts', requested_at=now.isoformat(), received_at='2026-10-09T19:00:00+08:00', first_available=now.isoformat())]))
    with pytest.raises(ValueError, match='INDEPENDENT_SOURCE_CLOCK_INVALID'):
        build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1',
              observation_binding=observation, clock=lambda: now)


def test_model_dependency_change_preserves_frozen_output(publisher_inputs):
    root, row, candidate = publisher_inputs
    binding = candidate([row])
    original = build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1')
    raw = (root/original['path']).read_bytes()
    path = root/'src/workbench_analysis/r43_focus_replay.py'
    path.write_bytes(path.read_bytes() + b'\n# synthetic dependency revision\n')
    revised = build(root, candidate_binding=binding, trade_date='2026-10-09', revision='r1')
    assert original != revised and (root/original['path']).read_bytes() == raw


def test_real_scanner_recomputed_and_retry(publisher_inputs):
    root, _, _ = publisher_inputs
    head_path = ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    document_head = json.loads(head_path.read_bytes())
    bindings = list(document_head['owners']['2026-10-09'][k] for k in ('prewatch', 'lifecycle', 'core'))
    bindings.append(document_head['membership_snapshot'])
    for binding in bindings:
        target = root/binding['path']; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/binding['path']).read_bytes())
    target = root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(head_path.read_bytes())
    head = ref(root, target)
    result = build(root, candidate_binding=head, trade_date='2026-10-09', revision='pytest-r1')
    raw = (root/result['path']).read_bytes()
    document = json.loads(gzip.decompress(raw))
    assert len(document['scenario_outputs']) == 5224 * 4
    assert all(r['episode_id'] is None and r['benchmark'] is None and not r['eligible_at_T0'] for r in document['scenario_outputs'])
    assert sum(r['state'] == 'TRUE' for r in document['scenario_outputs']) == 300
    assert build(root, candidate_binding=head, trade_date='2026-10-09', revision='pytest-r1') == result
    assert (root/result['path']).read_bytes() == raw
    assert document['evidence_class'] == 'RECONSTRUCTED_RESEARCH_ONLY'
    with pytest.raises(ValueError, match='HISTORICAL_OR_FUTURE'):
        build(root, candidate_binding=head, trade_date='2026-10-09', revision='bad', observation_binding=head)


def test_matrix_no_prior_pending_and_unknown(tmp_path):
    candidate = publish(tmp_path, 'candidate.json', dict(T0='2026-10-09', rows=[dict(sector_id='THEME:1', CONFIRMED='TRUE', WARM='UNKNOWN')]))
    result = matrix(tmp_path, candidate_binding=candidate, cutoff='2026-10-09T18:35:00+08:00')
    assert result['rows'][0]['fields']['scenario']['status'] == 'NO_PRIOR_EPISODE'
    prior = publish(tmp_path, 'prior.json', dict(rows=[dict(entity_id='THEME:1', trade_date='2026-10-08',
        AS_RECORDED=True, episode_id='SYNTHETIC', first_available='2026-10-08T18:35:00+08:00',
        due_at='2026-10-12T18:35:00+08:00', scenario='BASE_BUILD', invalidation_contract_id='I1')]))
    result = matrix(tmp_path, candidate_binding=candidate, prior_binding=prior, cutoff='2026-10-09T18:35:00+08:00')
    assert result['rows'][0]['fields']['followup_complete']['status'] == 'PENDING'
    assert result['rows'][0]['fields']['frozen_invalidation']['status'] == 'UNKNOWN'
    assert result['production'] is False

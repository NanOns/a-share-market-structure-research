"""Synthetic-only extraction and DD writer boundary tests."""
import json
import pytest
from test_cohort_admission_r4 import frozen
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.cohort_first_capture_producer_r1 import extract_candidate
from workbench_analysis.cohort_capture_readiness_r1 import inspect_daily_candidate


def setup(root, producer_patch=None, row_patch=None, subset=False):
    row = dict(frozen(), parameters_sha256='a'*64)
    other = dict(row, entity_id='S2', eligible_at_T0=False, ineligibility_reason='SOURCE_INCOMPLETE')
    other.update(row_patch or {})
    rows = [row, other]
    signals = publish(root, 'signals.json', dict(signals=rows[:1] if subset else rows))
    state = publish(root, 'state.json', dict(cohort_signals=rows))
    producer = dict(contract_id='COHORT_COMPLETE_SIGNAL_PRODUCER_R1', T0=row['T0'],
        revision='r1', membership_basis='AS_RECORDED', membership_version='M1',
        evidence_class='PIT_OBSERVED', scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS',
        qualification_source='ACCEPTED_STATE_OWNER', publication_id='P1', frozen_signal_version='V1',
        parameters_sha256='a'*64, first_available=row['asof_first_available'],
        captured_at='2026-09-30T15:30:00+08:00', accepted_at='2026-09-30T15:40:00+08:00',
        source_owner=state, signals=signals, signal_count=2)
    producer.update(producer_patch or {})
    ref = publish(root, 'producer.json', producer)
    head = publish(root, 'candidate.json', dict(accepted_trade_date=row['T0'],
        owners={row['T0']: {'state': state}}, cohort_signal_producers={row['T0']: ref}))
    return dict(root=root, candidate_binding=head, trade_date=row['T0'],
        cutoff=row['frozen_at_T0'], candidate_directory='docs/evidence/test_candidates')


def test_complete_immutable_extraction_and_idempotency(tmp_path):
    args = setup(tmp_path)
    before = (tmp_path/'candidate.json').read_bytes()
    a = extract_candidate(**args)
    assert a == extract_candidate(**args)
    assert (a['eligible_count'], a['ineligible_count']) == (1, 1)
    assert a['production_write_authorized'] is False and a['observed_count'] is None
    assert (tmp_path/'candidate.json').read_bytes() == before
    bundle = json.loads((tmp_path/a['candidate']['path']).read_bytes())
    assert len(bundle['complete_signal_ledger']) == 2
    assert len(bundle['owner']['enrollments']) == 1


@pytest.mark.parametrize('patch', [
    {'scope':'FOCUS_TOP_K'}, {'evidence_class':'RECONSTRUCTED_ASOF'},
    {'qualification_source':'Focus'}, {'membership_basis':'CURRENT'},
    {'parameters_sha256':''}, {'signal_count':1}, {'source_owner':{}},
    {'captured_at':'2026-10-09T15:00:00+08:00'},
    {'first_available':'2026-09-30T15:35:00+08:00'},
])
def test_invalid_producer_creates_no_candidate(tmp_path, patch):
    with pytest.raises(ValueError):
        extract_candidate(**setup(tmp_path, producer_patch=patch))
    assert not (tmp_path/'docs').exists()


@pytest.mark.parametrize('patch', [
    {'eligible_at_T0':None}, {'ineligibility_reason':''}, {'entity_id':'S1'},
    {'parameters_sha256':'b'*64}, {'no_lookahead':False},
    {'qualification_source':'Forward outcome'}, {'frozen_signal_version':'V2'},
    {'asof_first_available':'2026-09-30T15:00:00+08:00'},
])
def test_every_ineligible_row_is_validated(tmp_path, patch):
    with pytest.raises(ValueError):
        extract_candidate(**setup(tmp_path, row_patch=patch))


def test_subset_cannot_claim_full_capture(tmp_path):
    with pytest.raises(ValueError, match='COMPLETE_OWNER_SIGNAL_SET'):
        extract_candidate(**setup(tmp_path, subset=True))


def test_daily_hook_extracts_without_granting_read_or_write(tmp_path):
    args = setup(tmp_path)
    args.pop('candidate_directory')
    result = inspect_daily_candidate(**args)
    assert result['status'] == 'SOURCE_INCOMPLETE'
    assert result['first_capture_extraction']['status'] == 'ISOLATED_FIRST_CAPTURE_EXTRACTED'
    assert result['production_write_authorized'] is False
    assert result['blocks_local_daily_publication'] is False


def test_changed_frozen_bytes_cannot_overwrite_same_slot(tmp_path):
    args = setup(tmp_path)
    result = extract_candidate(**args)
    path = tmp_path/result['candidate']['path']
    path.write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='OVERWRITE_FORBIDDEN'):
        extract_candidate(**args)


def test_tampered_signal_digest_rejected(tmp_path):
    args = setup(tmp_path)
    (tmp_path/'signals.json').write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        extract_candidate(**args)


def test_daily_missing_producer_file_is_nonblocking(tmp_path):
    args = setup(tmp_path)
    args.pop('candidate_directory')
    (tmp_path/'producer.json').unlink()
    result = inspect_daily_candidate(**args)
    assert result['first_capture_extraction']['status'] == 'CAPTURE_PRODUCER_REJECTED'
    assert result['blocks_local_daily_publication'] is False


def test_receipt_collision_creates_no_owner_fragment(tmp_path):
    from workbench_analysis.v4_14_replay_io import digest
    args = setup(tmp_path)
    slot = digest(['2026-09-30', 'P1', 'r1'])
    directory = tmp_path/args['candidate_directory']/slot
    directory.mkdir(parents=True)
    (directory/'capture_receipt.json').write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='OVERWRITE_FORBIDDEN'):
        extract_candidate(**args)
    assert not (directory/'owner.json').exists()


def test_source_freeze_to_extraction_to_separate_writer_preflight(tmp_path):
    from datetime import datetime
    from workbench_analysis.cohort_first_capture_producer_r1 import freeze_source_candidate
    from workbench_analysis.cohort_capture_readiness_r1 import prepare_capture
    row = dict(frozen(), parameters_sha256='a'*64)
    owner = publish(tmp_path, 'real_source_owner.json', dict(cohort_signals=[row]))
    manifest = publish(tmp_path, 'source_manifest.json', dict(
        contract_id='COHORT_FIRST_CAPTURE_SOURCE_MANIFEST_R1', source_owner=owner,
        T0=row['T0'], publication_id='P1', revision='r1', frozen_signal_version='V1',
        parameters_sha256='a'*64, evidence_class='PIT_OBSERVED', membership_basis='AS_RECORDED',
        membership_version='M1', scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS', signal_count=1,
        first_available=row['asof_first_available'], accepted_at='2026-09-30T15:30:00+08:00',
        capture_deadline='2026-09-30T18:00:00+08:00'))
    clock = lambda: datetime.fromisoformat(row['frozen_at_T0'])
    result = freeze_source_candidate(tmp_path, source_owner_binding=owner,
        source_manifest_binding=manifest, candidate_directory='docs/evidence/freeze', clock=clock)
    assert result == freeze_source_candidate(tmp_path, source_owner_binding=owner,
        source_manifest_binding=manifest, candidate_directory='docs/evidence/freeze', clock=clock)
    head = publish(tmp_path, 'next_candidate.json', dict(accepted_trade_date=row['T0'],
        owners={row['T0']:{'state':owner}}, cohort_signal_producers={row['T0']:result['producer']}))
    extracted = extract_candidate(tmp_path, candidate_binding=head, trade_date=row['T0'],
        cutoff=row['frozen_at_T0'], candidate_directory='docs/evidence/extracted')
    grants = dict(contract_id='COHORT_FIRST_CAPTURE_WRITE_GRANT_R1', capability='PREPARE_FIRST_CAPTURE',
        authorized=True, revoked=False, owner=extracted['owner_binding'], source_receipt=extracted['capture_receipt_binding'],
        trade_date=row['T0'], revision='r1', valid_from='2026-09-30T15:00:00+08:00', valid_until='2026-09-30T18:00:00+08:00')
    grant = publish(tmp_path, 'synthetic_grant.json', grants)
    ready_head = publish(tmp_path, 'ready_candidate.json', dict(owners={row['T0']:{'validation_cohort':extracted['owner_binding']}},
        cohort_capture_receipts={row['T0']:extracted['capture_receipt_binding']}, cohort_write_grants={row['T0']:grant}))
    prepared = prepare_capture(tmp_path, accepted_head=ready_head, owner_binding=extracted['owner_binding'],
        trade_date=row['T0'], revision='r1', cutoff=row['frozen_at_T0'])
    assert prepared['eligible_count'] == 1 and prepared['production_write_authorized'] is False
    missing = publish(tmp_path, 'missing_grant_candidate.json', dict(owners={row['T0']:{'validation_cohort':extracted['owner_binding']}},
        cohort_capture_receipts={row['T0']:extracted['capture_receipt_binding']}))
    with pytest.raises(ValueError, match='WRITE_GRANT_REQUIRED'):
        prepare_capture(tmp_path, accepted_head=missing, owner_binding=extracted['owner_binding'],
            trade_date=row['T0'], revision='r1', cutoff=row['frozen_at_T0'])


def test_source_freeze_refuses_historical_capture_today(tmp_path):
    from workbench_analysis.cohort_first_capture_producer_r1 import freeze_source_candidate
    owner = publish(tmp_path, 'source_owner.json', dict(cohort_signals=[]))
    manifest = publish(tmp_path, 'source_manifest.json', dict(T0='2026-09-30'))
    with pytest.raises(ValueError, match='REALTIME_FULL_SOURCE'):
        freeze_source_candidate(tmp_path, source_owner_binding=owner, source_manifest_binding=manifest,
            candidate_directory='docs/evidence/freeze')


@pytest.mark.parametrize('patch', [{'parameters_sha256':''}, {'parameters_sha256':'abc'},
    {'revision':''}, {'membership_version':''}, {'publication_id':''}, {'frozen_signal_version':''}])
def test_source_freeze_validates_complete_contract_before_writing(tmp_path, patch):
    from datetime import datetime
    from workbench_analysis.cohort_first_capture_producer_r1 import freeze_source_candidate
    setup(tmp_path)
    source = json.loads((tmp_path/'producer.json').read_bytes())
    source.update(contract_id='COHORT_FIRST_CAPTURE_SOURCE_MANIFEST_R1',
                  capture_deadline='2026-09-30T18:00:00+08:00')
    source.update(patch)
    binding = publish(tmp_path, 'source_manifest.json', source)
    with pytest.raises(ValueError):
        freeze_source_candidate(tmp_path, source_owner_binding=source['source_owner'],
            source_manifest_binding=binding, candidate_directory='docs/evidence/freeze',
            clock=lambda:datetime.fromisoformat('2026-09-30T16:00:00+08:00'))
    assert not (tmp_path/'docs').exists()


@pytest.mark.parametrize('missing_file', ['producer', 'owner.json', 'receipt.json', 'grant.json'])
def test_actual_daily_executor_continues_after_missing_cohort_source(tmp_path, monkeypatch, missing_file):
    from workbench_analysis import operational_daily_executor_v1 as executor
    from workbench_analysis import operational_daily_ready_owner_v2 as adapter
    from workbench_analysis import operational_successor_release_v1 as release
    from scripts import audit_dynamic_daily_period_numbers_v1 as oracle
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_analysis.r43_owner_replay import ref
    day = '2026-09-30'
    atomic_json(tmp_path, tmp_path/'freeze.json', {'synthetic_only':True})
    binding = ref(tmp_path, tmp_path/'freeze.json')
    monkeypatch.setattr(executor, 'verify_source_gate',
        lambda r,d,a,result: (dict(result, source_readiness=binding), {'source_ready':True}))
    monkeypatch.setattr(adapter, 'build', lambda *a, **k: ({}, {'folder':tmp_path}))
    candidate = dict(accepted_trade_date=day, owners={day:{}}, predecessor={'sha256':'a'*64},
        cohort_signal_producers={day:{'path':'absent.json','sha256':'a'*64}})
    if missing_file != 'producer':
        from test_cohort_daily_capture_boundary_r1 import daily_fixture
        args = daily_fixture(tmp_path)
        candidate = json.loads((tmp_path/args['candidate_binding']['path']).read_bytes())
        candidate['predecessor'] = {'sha256':'a'*64}
        (tmp_path/missing_file).unlink()
    atomic_json(tmp_path, tmp_path/'daily_candidate.json', candidate)
    monkeypatch.setattr(adapter, 'seal', lambda *a: (candidate,ref(tmp_path,tmp_path/'daily_candidate.json')))
    atomic_json(tmp_path, tmp_path/'PERIOD_NUMERIC_ORACLE.json', {'synthetic_only':True})
    monkeypatch.setattr(oracle,'audit',lambda *a:{'acceptance':'PASS'})
    monkeypatch.setattr(release,'promote',lambda *a:pytest.fail('UNAUTHORIZED_REAL_CAS'))
    progress = []
    result = executor.derive_ready_sources(tmp_path,day,{'source_freeze':binding},
        progress=lambda d,s,r:progress.append(s))
    assert result['status'] == 'QA_BLOCKED'
    assert result['reason'] == 'LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED'
    if missing_file == 'producer':
        assert result['cohort_capture_readiness']['first_capture_extraction']['status'] == 'CAPTURE_PRODUCER_REJECTED'
    else:
        assert result['cohort_capture_readiness']['status'] == 'CAPTURE_PREFLIGHT_REJECTED'
    assert progress[-1] == 'DERIVED_READY'

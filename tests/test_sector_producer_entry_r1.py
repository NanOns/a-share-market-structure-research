"""Original-byte boundary vectors; no synthetic vector grants production rights."""
import hashlib
import json

import pytest
from sector.producer_entry_r1 import FIELDS, prepare_entry


def bound(root, name, value, *, jsonl=False):
    raw = (json.dumps(value) + ('\n' if jsonl else '')).encode()
    path = root / name
    path.write_bytes(raw)
    return dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def vector(tmp_path):
    native = dict(entity_type='SECTOR', sector_id='S:1', trade_date='2026-10-09',
        member_ids=['a', 'b', 'c', 'd', 'e'], member_set_asof='M:1009',
        fields={'dq5': {'value': 12, 'quality': 'ISOLATED_TEST_VECTOR'}})
    prior = dict(entity_type='SECTOR', entity_id='S:1', trade_date='2026-10-08',
        member_ids=native['member_ids'], member_set_asof='M:1008', episode_id='EP:1',
        first_available='2026-10-08T16:00:00+08:00',
        invalidation_contract_id='INV:1', invalidation_contract_sha256='a' * 64)
    publishers = {}
    receipts = {}
    for field in FIELDS:
        is_prior = field in ('frozen_invalidation', 'episode_invalidation_contract_id')
        receipt = dict(entity_type='SECTOR', entity_id='S:1', field=field,
            member_ids=native['member_ids'], member_set_asof='M:1008' if is_prior else 'M:1009',
            AS_RECORDED=True, first_available='2026-10-09T16:00:00+08:00',
            trade_date='2026-10-08' if is_prior else '2026-10-09',
            producer_contract_id='ISOLATED_' + field, parameter_set_id='TEST:1',
            window_identity='W:1', quality='ACCEPTED',
            value='INV:1' if field == 'episode_invalidation_contract_id' else
                  'BREADTH_BUILD' if field == 'scenario' else
                  'TRUE' if field in ('CONFIRMED', 'followup_complete') else 'FALSE',
            episode_id='EP:1', invalidation_contract_sha256='a' * 64,
            due_plan={'due_session': '2026-10-09'}, right_censored=False,
            settled_owner_sha256='b' * 64)
        receipts[field] = receipt
        publishers[field] = bound(tmp_path, field + '.json', receipt)
    return tmp_path, native, receipts, dict(
        source_binding=bound(tmp_path, 'native.jsonl', native, jsonl=True),
        cutoff='2026-10-09T23:59:59+08:00', publishers=publishers,
        prior=prior, prior_binding=bound(tmp_path, 'prior.json', prior),
        sessions=['2026-09-30', '2026-10-08', '2026-10-09'])


def test_complete_original_receipt_chain_is_only_candidate(vector):
    root, native, _, args = vector
    result = prepare_entry(root, native, **args)
    assert result['readiness'] == 'CANDIDATE_INPUT_COMPLETE'
    assert not result['accepted'] and not result['formal_consumer_enabled']
    assert not result['production_authorized'] and not result['reducer_invoked']
    assert result['upstream']['CONFIRMED']['value'] == 'TRUE'
    assert result['dq5'] == native['fields']['dq5']


@pytest.mark.parametrize('field', FIELDS)
def test_one_missing_producer_preserves_other_fields(vector, field):
    root, native, _, args = vector
    del args['publishers'][field]
    result = prepare_entry(root, native, **args)
    assert result['missing_fields'] == [field]
    assert result['upstream'][field]['value'] is None


@pytest.mark.parametrize('mutation,reason', [
    ({'first_available': '2026-10-12T16:00:00+08:00'}, 'FIRST_AVAILABLE_AFTER_CUTOFF'),
    ({'AS_RECORDED': False}, 'NON_AS_RECORDED_RECEIPT'),
    ({'member_ids': ['a', 'b', 'c', 'd']}, 'MEMBERSHIP_VERSION_OR_DENOMINATOR_MISMATCH'),
    ({'member_ids': ['a', 'b', 'c', 'd', 'x']}, 'MEMBERSHIP_VERSION_OR_DENOMINATOR_MISMATCH'),
    ({'member_ids': ['a', 'a', 'c', 'd', 'e']}, 'MEMBERSHIP_VERSION_OR_DENOMINATOR_MISMATCH'),
    ({'member_set_asof': 'LATEST_MEMBER_SNAPSHOT'}, 'MEMBERSHIP_VERSION_OR_DENOMINATOR_MISMATCH'),
    ({'trade_date': '2026-10-08'}, 'WRONG_TIME_ROLE'),
    ({'value': 'UNKNOWN'}, 'REQUIRED_VALUE_UNKNOWN'),
    ({'quality': 'PROXY_RECONSTRUCTED'}, 'REQUIRED_QUALITY_UNAVAILABLE'),
])
def test_receipt_negative_matrix(vector, mutation, reason):
    root, native, receipts, args = vector
    receipt = dict(receipts['CONFIRMED'], **mutation)
    args['publishers']['CONFIRMED'] = bound(root, 'CONFIRMED.json', receipt)
    result = prepare_entry(root, native, **args)
    assert result['upstream']['CONFIRMED']['reason'] == reason
    assert result['upstream']['CONFIRMED']['value'] is None


@pytest.mark.parametrize('field', ['frozen_invalidation', 'episode_invalidation_contract_id'])
def test_changed_creation_frozen_contract_fails_closed(vector, field):
    root, native, receipts, args = vector
    args['publishers'][field] = bound(root, field + '.json',
        dict(receipts[field], invalidation_contract_sha256='c' * 64))
    result = prepare_entry(root, native, **args)
    assert result['upstream'][field]['value'] is None


def test_censored_followup_is_not_complete(vector):
    root, native, receipts, args = vector
    args['publishers']['followup_complete'] = bound(root, 'followup_complete.json',
        dict(receipts['followup_complete'], right_censored=True))
    assert prepare_entry(root, native, **args)['upstream']['followup_complete']['value'] is None


@pytest.mark.parametrize('which', ['source_binding', 'prior_binding', 'publisher'])
def test_original_bytes_mutation_detected(vector, which):
    root, native, _, args = vector
    binding = args['publishers']['WARM'] if which == 'publisher' else args[which]
    (root / binding['path']).write_bytes(b'{}')
    with pytest.raises(ValueError, match='SOURCE_BYTES_BINDING_MISMATCH'):
        prepare_entry(root, native, **args)


def test_entity_impersonation_rejected(vector):
    root, native, receipts, args = vector
    args['publishers']['CONFIRMED'] = bound(root, 'CONFIRMED.json',
        dict(receipts['CONFIRMED'], entity_type='STOCK'))
    with pytest.raises(ValueError, match='PRODUCER_ENTITY_FIELD_MISMATCH'):
        prepare_entry(root, native, **args)


def test_exact_prior_session_uses_holiday_calendar(vector):
    root, native, _, args = vector
    args['sessions'] = ['2026-09-30', '2026-10-09']
    with pytest.raises(ValueError, match='EXACT_PRIOR_SESSION_REQUIRED'):
        prepare_entry(root, native, **args)


def test_prior_dictionary_cannot_replace_bound_owner(vector):
    root, native, _, args = vector
    args['prior'] = dict(args['prior'], episode_id='FORGED')
    with pytest.raises(ValueError, match='EXACT_PRIOR_OWNER_BINDING_REQUIRED'):
        prepare_entry(root, native, **args)


def test_same_day_confirmation_invalidation_does_not_activate_entry(vector):
    root, native, receipts, args = vector
    args['publishers']['frozen_invalidation'] = bound(root, 'frozen_invalidation.json',
        dict(receipts['frozen_invalidation'], value='TRUE'))
    result = prepare_entry(root, native, **args)
    assert result['upstream']['CONFIRMED']['value'] == 'TRUE'
    assert result['upstream']['frozen_invalidation']['value'] == 'TRUE'
    assert not result['reducer_invoked'] and result['maturity'] is None
    # Accepted reducer and its invalidation precedence remain the only oracle.


def test_amount_dependent_warm_needs_strict_history(vector):
    root, native, receipts, args = vector
    args['publishers']['WARM'] = bound(root, 'WARM.json',
        dict(receipts['WARM'], value='TRUE', amount_a_required=True,
             strict_h21_verified=False))
    result = prepare_entry(root, native, **args)
    assert result['upstream']['WARM']['reason'] == 'STRICT_AMOUNT_A_HISTORY_UNVERIFIABLE'
    assert result['upstream']['CONFIRMED']['value'] == 'TRUE'


def test_source_path_escape_rejected(vector):
    root, native, _, args = vector
    args['source_binding'] = dict(args['source_binding'], path='../native.jsonl')
    with pytest.raises(ValueError, match='SOURCE_PATH_OUTSIDE_PROJECT_OR_MISSING'):
        prepare_entry(root, native, **args)


def test_stock_scenario_cannot_be_a_sector_producer(vector):
    root, native, receipts, args = vector
    args['publishers']['scenario'] = bound(root, 'scenario.json',
        dict(receipts['scenario'], value='LAUNCH_CONFIRM'))
    result = prepare_entry(root, native, **args)
    assert result['upstream']['scenario']['reason'] == 'SCENARIO_OUTSIDE_FROZEN_DOMAIN'


def test_prior_first_availability_cannot_be_after_cutoff(vector):
    root, native, _, args = vector
    args['prior']['first_available'] = '2026-10-12T16:00:00+08:00'
    args['prior_binding'] = bound(root, 'prior.json', args['prior'])
    with pytest.raises(ValueError, match='PRIOR_FIRST_AVAILABLE_REQUIRED_AT_CUTOFF'):
        prepare_entry(root, native, **args)

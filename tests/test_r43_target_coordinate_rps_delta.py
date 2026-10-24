import hashlib
import json

import pytest

from workbench_analysis.r43_owner_replay import (
    apply_exact_dated_membership_authorities,
    rank_exact_endpoint_rps,
)


def test_endpoint_rps_uses_only_exact_dated_members():
    # The endpoint scores are computed in the current target's QFQ coordinate.
    # A security outside the historical endpoint roster must not change the
    # endpoint denominator or the two eligible members' ranks.
    target_coordinate_returns = {
        'A': 0.20,
        'B': 0.10,
        'C': 0.95,
    }
    endpoint_members = {'A', 'B'}

    scores = rank_exact_endpoint_rps(target_coordinate_returns, endpoint_members)

    assert scores == {'A': 100.0, 'B': 0.0}


def test_exact_lifecycle_membership_overrides_broader_universe_fallback(tmp_path):
    fallback = {'session-a': {'A', 'B', 'C'}}
    payload = {'trade_date': 'session-a', 'active_security_ids': ['A', 'B']}
    source_path = tmp_path / 'lifecycle.json'
    source_path.write_text(json.dumps(payload), encoding='utf-8')
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    authority = {
        'session-a': {
            'trade_date': 'session-a',
            'active_security_ids': ['A', 'B'],
            'source': {'path': source_path.name, 'sha256': source_sha},
        },
    }

    resolved, bindings = apply_exact_dated_membership_authorities(
        fallback, authority, root=tmp_path, required_dates={'session-a'})

    assert resolved == {'session-a': {'A', 'B'}}
    assert bindings['session-a']['member_count'] == 2
    assert bindings['session-a']['source'] == authority['session-a']['source']


@pytest.mark.parametrize('mutate,reason', [
    (lambda item: item.update(trade_date='another-session'), 'DATE_MISMATCH'),
    (lambda item: item.update(active_security_ids=['A', 'A']), 'DUPLICATE_ID'),
    (lambda item: item.update(source={'path': 'candidate/lifecycle.json'}), 'SOURCE_REQUIRED'),
])
def test_exact_lifecycle_membership_authority_rejects_invalid_binding(mutate, reason):
    authority = {
        'trade_date': 'session-a',
        'active_security_ids': ['A'],
        'source': {'path': 'candidate/lifecycle.json', 'sha256': 'a' * 64},
    }
    mutate(authority)

    with pytest.raises(ValueError, match=reason):
        apply_exact_dated_membership_authorities({}, {'session-a': authority}, root='.')


def test_exact_lifecycle_membership_authority_requires_every_endpoint(tmp_path):
    with pytest.raises(ValueError, match='EXACT_DATED_MEMBERSHIP_AUTHORITY_REQUIRED'):
        apply_exact_dated_membership_authorities(
            {}, {}, root=tmp_path, required_dates={'session-a'})


def test_exact_lifecycle_membership_authority_rejects_source_bytes_mismatch(tmp_path):
    source_path = tmp_path / 'lifecycle.json'
    source_path.write_text(json.dumps({'trade_date': 'session-a', 'active_security_ids': ['A']}), encoding='utf-8')
    authority = {'session-a': {
        'trade_date': 'session-a', 'active_security_ids': ['A'],
        'source': {'path': source_path.name, 'sha256': 'a' * 64},
    }}

    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        apply_exact_dated_membership_authorities({}, authority, root=tmp_path)

"""Real PostgreSQL negative availability tests; synthetic seeds are rolled back.

No synthetic seed is admitted as authority for the 205 historical source rows.
"""
import pytest
from tests.fep.conftest import pg, base, observation, snapshot, rejected, SCOPE, T
from workbench_analysis.fep_e5.canonical_identity import readback_population, inventory, CONFLICT


def source(day='2026-09-01'):
    return dict(observation_id='historical-source-event', entity_id='SEC-A', trade_date=day,
                original_e2_row_digest='a' * 64)


def test_N05_missing_historical_authority_retains_population(pg):
    before = inventory(pg)
    rows = [source(), dict(source(), observation_id='missing-second')]
    result = readback_population(pg, rows, {})
    assert result['status'] == CONFLICT and result['affected_observations'] == 2
    assert len(result['population']) == 2 and inventory(pg) == before
    assert all(r['canonical_identity'] is None for r in result['population'])


def test_N04_date_matched_publication_is_not_a_mapping(base):
    result = readback_population(base, [source()], {})
    row = result['population'][0]
    assert row['accepted_publications_on_date_diagnostic_only'] == 1
    assert row['status'] == CONFLICT and row['canonical_identity'] is None


def test_N03_digest_publication_is_rejected(base):
    result = readback_population(base, [source()], {'historical-source-event': dict(publication_id='a' * 64)})
    assert 'DIGEST_IS_NOT_CANONICAL_PUBLICATION_AUTHORITY' in result['population'][0]['reasons']
    assert 'EXACT_CANONICAL_CHAIN_NOT_FOUND' in result['population'][0]['reasons']


def test_N03_canonical_database_rejects_fake_publication(base):
    observation(base, name='fake-pub-event')
    rejected(base, lambda: snapshot(base, name='fake-snap', obs='fake-pub-event', publication='a' * 64), match='no rows')


def test_N04_canonical_database_rejects_wrong_date_publication(base):
    observation(base, name='wrong-date-event', day='2026-09-02')
    rejected(base, lambda: snapshot(base, name='wrong-date-snap', obs='wrong-date-event'), match='PUBLICATION_OBSERVATION_MISMATCH')


@pytest.mark.parametrize('case', ['duplicate', 'foreign_authority'])
def test_identity_population_must_be_exact(pg, case):
    with pytest.raises(ValueError, match='POPULATION_IDENTITY_CONFLICT'):
        readback_population(pg, [source(), source()] if case == 'duplicate' else [source()],
                            {'not-in-source': {}} if case == 'foreign_authority' else {})

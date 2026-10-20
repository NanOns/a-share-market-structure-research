"""Pure fail-closed checks for the unprovisioned fixed v4 FEP storage contract."""

import pytest

from workbench_analysis.fep_e5.canonical_identity import (
    CONFLICT,
    inventory,
    readback_population,
)


def source(observation_id='historical-source-event'):
    return dict(observation_id=observation_id, entity_id='SEC-A', trade_date='2026-09-01',
                original_e2_row_digest='a' * 64)


class NoDatabaseAccess:
    def execute(self, *_args, **_kwargs):
        raise AssertionError('legacy FEP identity reader must not query PostgreSQL')


def test_population_is_retained_but_requires_fixed_v4_fep_migration():
    pg = NoDatabaseAccess()
    rows = [source(), source('missing-second')]

    result = readback_population(pg, rows, {})

    assert result['status'] == CONFLICT
    assert result['affected_observations'] == 2
    assert len(result['population']) == 2
    assert all(item['canonical_identity'] is None for item in result['population'])
    assert all('V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED' in item['reasons']
               for item in result['population'])
    assert result['no_database_writes'] and not result['canonical_integration_accepted']
    assert inventory(pg) == {}


@pytest.mark.parametrize('case', ['duplicate', 'foreign_authority'])
def test_population_identity_must_be_exact(case):
    rows = [source(), source()] if case == 'duplicate' else [source()]
    authorities = {'not-in-source': {}} if case == 'foreign_authority' else {}

    with pytest.raises(ValueError, match='CANONICAL_POPULATION_IDENTITY_CONFLICT'):
        readback_population(NoDatabaseAccess(), rows, authorities)

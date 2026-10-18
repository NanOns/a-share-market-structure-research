from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis.fep_e5.canonical_ledger import apply
from workbench_analysis.fep_e5 import canonical_ledger
from workbench_analysis.fep_e5.trusted_authority import read_canonical_candidate
from workbench_analysis.fep_e5.metadata_binding import register
from workbench_analysis.fep_e1.db import validate_inventory
from workbench_analysis.fep_e1.repository import persist_dataset
from workbench_service.canonical_expectancy_service import CanonicalExpectancyReadAPI


class NoDatabaseAccess:
    def execute(self, *_args, **_kwargs):
        raise AssertionError('FEP API must not query the retired schema')


def test_canonical_fep_migration_refuses_market_research():
    pg = SimpleNamespace(info=SimpleNamespace(dbname='market_research'))
    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'):
        apply(pg, Path(__file__).resolve().parents[2], [])


def test_standalone_fep_fixture_schema_sql_refuses_market_research():
    source = Path(__file__).resolve().parents[2] / 'src/workbench_analysis/fep_e5/schema.sql'
    text = source.read_text(encoding='utf-8')
    assert text.index("RAISE EXCEPTION 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'") < text.index('CREATE SCHEMA')


def test_canonical_expectancy_api_fails_closed_without_database_reads():
    api = CanonicalExpectancyReadAPI(NoDatabaseAccess())

    bootstrap = api.bootstrap('slot')
    projection = api.projection('slot', {}, diagnostic=True)

    assert bootstrap['status'] == 'STORAGE_NOT_READY'
    assert bootstrap['reason'] == 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'
    assert projection['status'] == 'STORAGE_NOT_READY'
    assert projection['MODEL_DISPLAY'] == 'UNGRANTED'
    assert projection['PRIORITY_USE'] == 'UNGRANTED'


def test_remaining_fep_database_consumers_fail_closed_without_database_reads():
    pg = NoDatabaseAccess()

    assert validate_inventory(pg)['status'] == 'STORAGE_NOT_READY'
    result = read_canonical_candidate(pg, dict(
        scope_id='S', target_id='T', horizon=1, feature_contract_id='F',
        model_set_id='M', capability='MODEL_DISPLAY', model_revision=1),
        at='2026-10-19T00:00:00+00:00')
    assert result['status'] == 'STORAGE_NOT_READY'
    assert result['production_authorized'] is False

    for operation in (
        lambda: persist_dataset(pg, 'D', 'S', 'F', 'P', None, None, {}),
        lambda: register(pg, None),
        lambda: canonical_ledger.contract(pg, 'C', {}),
        lambda: canonical_ledger.head(pg),
        lambda: canonical_ledger.accept(pg, {}, {}, {}, None, None),
    ):
        with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'):
            operation()

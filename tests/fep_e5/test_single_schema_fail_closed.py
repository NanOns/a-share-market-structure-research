from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis.fep_e5.canonical_ledger import apply
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
    assert "current_database()='market_research'" in text
    assert "RAISE EXCEPTION 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'" in text


def test_canonical_expectancy_api_fails_closed_without_database_reads():
    api = CanonicalExpectancyReadAPI(NoDatabaseAccess())

    bootstrap = api.bootstrap('slot')
    projection = api.projection('slot', {}, diagnostic=True)

    assert bootstrap['status'] == 'STORAGE_NOT_READY'
    assert bootstrap['reason'] == 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'
    assert projection['status'] == 'STORAGE_NOT_READY'
    assert projection['MODEL_DISPLAY'] == 'UNGRANTED'
    assert projection['PRIORITY_USE'] == 'UNGRANTED'

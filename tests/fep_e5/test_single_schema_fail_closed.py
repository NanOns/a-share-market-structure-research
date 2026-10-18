from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis.fep_e5.canonical_ledger import apply


def test_canonical_fep_migration_refuses_market_research():
    pg = SimpleNamespace(info=SimpleNamespace(dbname='market_research'))
    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'):
        apply(pg, Path(__file__).resolve().parents[2], [])


def test_standalone_fep_fixture_schema_sql_refuses_market_research():
    source = Path(__file__).resolve().parents[2] / 'src/workbench_analysis/fep_e5/schema.sql'
    text = source.read_text(encoding='utf-8')
    assert "current_database()='market_research'" in text
    assert "RAISE EXCEPTION 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'" in text

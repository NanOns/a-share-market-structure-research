import pytest
from types import SimpleNamespace


def test_legacy_fep_schema_migration_is_disabled():
    from workbench_analysis.fep_e5.canonical_ledger import apply

    pg = SimpleNamespace(info=SimpleNamespace(dbname='market_research'))
    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'):
        apply(pg, None, [])

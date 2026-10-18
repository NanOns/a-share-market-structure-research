from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis.fep_e1.db import MIGRATION_VERSION, TABLES, apply, validate_inventory
from workbench_analysis.fep_e5 import canonical_ledger
from workbench_analysis.fep_e5.ledger import Ledger
from workbench_service.canonical_expectancy_service import CanonicalExpectancyReadAPI


class MigrationReadyDB:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=()):
        self.calls.append((str(statement), params))
        if 'schema_migrations' in str(statement):
            return SimpleNamespace(fetchone=lambda: ('a' * 64,))
        raise AssertionError(f'unexpected write or non-migration query: {statement}')


class EmptyReadDB:
    def __init__(self):
        self.queries = []

    def execute(self, statement, params=()):
        self.queries.append(str(statement))
        return SimpleNamespace(fetchall=lambda: [])


def test_fep_migration_consumers_only_verify_central_v4_migration():
    pg = MigrationReadyDB()

    assert apply(pg, None) == [dict(version=MIGRATION_VERSION, sha256='a' * 64, status='ALREADY_APPLIED')]
    assert canonical_ledger.apply(pg, None, []) == [
        dict(version=MIGRATION_VERSION, sha256='a' * 64, status='ALREADY_APPLIED')
    ]
    with pytest.raises(ValueError, match='FEP_MIGRATIONS_MUST_USE_CENTRAL_V4_RUNNER'):
        canonical_ledger.apply(pg, None, [Path('obsolete.sql')])
    assert len(pg.calls) == 2


def test_standalone_fep_fixture_schema_sql_refuses_before_create_schema():
    source = Path(__file__).resolve().parents[2] / 'src/workbench_analysis/fep_e5/schema.sql'
    text = source.read_text(encoding='utf-8')
    assert text.index("RAISE EXCEPTION 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'") < text.index('CREATE SCHEMA')


def test_legacy_e5_ledger_cannot_create_or_read_a_separate_schema():
    pg = SimpleNamespace(info=SimpleNamespace(dbname='fep_e5_legacy_fixture'))
    ledger = Ledger(pg, historical_fixture=True)
    for operation in (ledger.install, lambda: ledger.get('models', 'id'), ledger.inventory):
        with pytest.raises(RuntimeError, match='V4_FEP_CANONICAL_LEDGER_REQUIRED'):
            operation()


def test_fep_inventory_requires_all_fixed_tables_and_guards():
    pg = EmptyReadDB()
    with pytest.raises(ValueError, match='FEP_FIXED_V4_TABLES_MISSING'):
        validate_inventory(pg)
    assert "schemaname='v4'" in pg.queries[0]
    assert all('fep.' not in query for query in pg.queries)


def test_canonical_expectancy_reads_fixed_v4_and_missing_slot_is_not_ready():
    pg = EmptyReadDB()
    api = CanonicalExpectancyReadAPI(pg)

    bootstrap = api.bootstrap('slot')
    projection = api.projection('slot', {}, diagnostic=True)

    assert bootstrap == {'status': 'NOT_READY'}
    assert projection['status'] == 'CONTEXT_MISMATCH'
    assert all('from v4.' in query for query in pg.queries)
    assert all('fep.' not in query for query in pg.queries)


def test_active_fep_modules_have_no_module_schema_consumers():
    root = Path(__file__).resolve().parents[2]
    active = (
        root / 'src/workbench_analysis/fep_e1',
        root / 'src/workbench_analysis/fep_e5/canonical_identity.py',
        root / 'src/workbench_analysis/fep_e5/canonical_ledger.py',
        root / 'src/workbench_analysis/fep_e5/metadata_binding.py',
        root / 'src/workbench_analysis/fep_e5/trusted_authority.py',
        root / 'src/workbench_service/canonical_expectancy_service.py',
    )
    files = [p for entry in active for p in (entry.rglob('*.py') if entry.is_dir() else [entry])]
    text = '\n'.join(p.read_text(encoding='utf-8') for p in files)
    assert 'fep.' not in text
    assert 'fep_e5_engineering' not in text

import pytest


def test_workspace_schema_is_fixed_and_alias_creation_is_disabled(tmp_path):
    from workbench_db.v4_native import register_workspace_schema_alias, workspace_schema

    assert workspace_schema(tmp_path, 'research') == 'v4'
    assert workspace_schema(tmp_path / 'other', 'forward') == 'v4'
    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_WORKSPACE_ALIAS_CREATION_DISABLED'):
        register_workspace_schema_alias(object(), tmp_path, 'research')


def test_schema_creation_guard_rejects_every_noncanonical_schema():
    from workbench_db.v4_native import create_schema

    class NoWrite:
        def execute(self, *_args):
            raise AssertionError('schema guard must run before SQL')

    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_ONLY_SCHEMA_CREATION_BLOCKED'):
        create_schema(NoWrite(), 'v4_research_0123456789abcdef')


def test_runtime_schema_guard_only_verifies_preprovisioned_v4():
    from workbench_db.v4_native import create_schema

    class ExistingSchema:
        def __init__(self): self.queries=[]
        def execute(self, query, params):
            self.queries.append((query,params))
            return self
        def fetchone(self): return ('v4',)

    class MissingSchema(ExistingSchema):
        def fetchone(self): return (None,)

    existing=ExistingSchema()
    create_schema(existing,'v4')
    assert existing.queries==[('SELECT to_regnamespace(%s)',('v4',))]
    with pytest.raises(RuntimeError, match='V4_CANONICAL_SCHEMA_NOT_PROVISIONED'):
        create_schema(MissingSchema(),'v4')


def test_application_connection_rejects_legacy_schemas_before_connect(monkeypatch):
    from workbench_db import v4_native

    def forbidden(*_args, **_kwargs):
        raise AssertionError('legacy schema must be rejected before connecting')

    monkeypatch.setattr(v4_native.psycopg, 'connect', forbidden)
    with pytest.raises(ValueError, match='V4_SINGLE_SCHEMA_CONNECTION_REQUIRED'):
        with v4_native.connection('v4_history_0123456789abcdef', read_only=True):
            pass


def test_dynamic_shadow_exports_are_disabled_before_database_access():
    from workbench_db.v4_shadow_pg_r1 import build_readback_r1
    from workbench_db.v4_shadow_pg_r2 import build_readback

    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_SHADOW_EXPORT_MIGRATION_REQUIRED'):
        build_readback_r1('.', [], environment='REAL', evidence_origin='PIT_OBSERVED')
    with pytest.raises(RuntimeError, match='V4_SINGLE_SCHEMA_SHADOW_EXPORT_MIGRATION_REQUIRED'):
        build_readback('.', [], environment='REAL', evidence_origin='PIT_OBSERVED')


def test_research_builder_stages_locally_and_targets_fixed_schema(monkeypatch, tmp_path):
    from workbench_db import v4_snapshot_pg_r1

    class FakePG:
        def __init__(self): self.queries=[]
        def execute(self, query, *_args): self.queries.append(query); return self

    pg=FakePG()
    monkeypatch.setattr(v4_snapshot_pg_r1.psycopg, 'connect', lambda *_a, **_k: pg)
    builder=v4_snapshot_pg_r1.Builder(tmp_path, 'a'*32)
    assert builder.schema=='v4'
    builder.executescript('CREATE TABLE objects(id text); CREATE TABLE IF NOT EXISTS bars(day date);')
    assert pg.queries[-1]=='CREATE TEMP TABLE objects(id text); CREATE TEMP TABLE IF NOT EXISTS bars(day date);'
    assert not any('CREATE SCHEMA' in str(query).upper() for query in pg.queries)

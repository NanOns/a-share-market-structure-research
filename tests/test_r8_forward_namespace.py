import json
from pathlib import Path

import pytest

from workbench_db.forward_r7_store import ForwardR7Store


def candidate(root: Path, schema: str = 'v4'):
    binding = dict(
        contract_id='R8_ISOLATED_FORWARD_NAMESPACE_R1',
        scope='CANDIDATE_ONLY',
        candidate_root=str(root.resolve()),
        schema=schema,
        origin_namespace='R8_TEST_CANDIDATE',
    )
    path = root / 'config/r8_forward_candidate_namespace_r1.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(binding), encoding='utf-8')
    return path, binding


class ExistingV4FactsTable:
    def __init__(self, *, present=True):
        self.present = present
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params=()):
        self.query = str(query)
        self.params = params
        return self

    def fetchone(self):
        return (1,) if self.present else None


def store(root: Path):
    instance = ForwardR7Store.__new__(ForwardR7Store)
    instance.root = root.resolve()
    instance.dsn = 'injected-test-connection'
    return instance


def test_candidate_uses_fixed_v4_forward_r7_relation(tmp_path, monkeypatch):
    project_root = tmp_path / 'candidate'
    project_root.mkdir()
    candidate(project_root)
    monkeypatch.setattr('common.paths.resolve_ingest_temp_root', lambda _root: tmp_path.resolve())
    pg = ExistingV4FactsTable()
    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect', lambda *_a, **_k: pg)

    assert store(project_root)._resolve_existing_schema() == 'v4'
    assert "table_schema='v4'" in pg.query
    assert "table_name='forward_r7_facts_r1'" in pg.query
    assert pg.params == ()


def test_non_v4_candidate_locator_fails_before_connect(tmp_path, monkeypatch):
    project_root = tmp_path / 'candidate'
    project_root.mkdir()
    candidate(project_root, schema='v4_forward_0123456789abcdef')
    monkeypatch.setattr('common.paths.resolve_ingest_temp_root', lambda _root: tmp_path.resolve())

    def forbidden(*_args, **_kwargs):
        raise AssertionError('invalid legacy locator must fail before PostgreSQL access')

    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect', forbidden)
    with pytest.raises(RuntimeError, match='ISOLATED_FORWARD_NAMESPACE_BINDING_INVALID'):
        store(project_root)._resolve_existing_schema()


def test_candidate_binding_must_match_its_root(tmp_path, monkeypatch):
    project_root = tmp_path / 'candidate'
    project_root.mkdir()
    path, binding = candidate(project_root)
    binding['candidate_root'] = str(tmp_path / 'other-root')
    path.write_text(json.dumps(binding), encoding='utf-8')
    monkeypatch.setattr('common.paths.resolve_ingest_temp_root', lambda _root: tmp_path.resolve())

    def forbidden(*_args, **_kwargs):
        raise AssertionError('mismatched candidate root must fail before PostgreSQL access')

    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect', forbidden)
    with pytest.raises(RuntimeError, match='ISOLATED_FORWARD_NAMESPACE_BINDING_INVALID'):
        store(project_root)._resolve_existing_schema()


def test_missing_fixed_v4_relation_fails_closed(tmp_path, monkeypatch):
    project_root = tmp_path / 'candidate'
    project_root.mkdir()
    candidate(project_root)
    monkeypatch.setattr('common.paths.resolve_ingest_temp_root', lambda _root: tmp_path.resolve())
    pg = ExistingV4FactsTable(present=False)
    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect', lambda *_a, **_k: pg)

    with pytest.raises(RuntimeError, match='V4_FORWARD_R7_SINGLE_SCHEMA_MIGRATION_REQUIRED'):
        store(project_root)._resolve_existing_schema()


def test_unbound_workspace_uses_only_the_preprovisioned_v4_relation(tmp_path, monkeypatch):
    pg = ExistingV4FactsTable()
    monkeypatch.setattr('workbench_db.forward_r7_store.psycopg.connect', lambda *_a, **_k: pg)

    assert store(tmp_path)._resolve_existing_schema() == 'v4'
    assert "table_schema='v4'" in pg.query
    assert "table_name='forward_r7_facts_r1'" in pg.query

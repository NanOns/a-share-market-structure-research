from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db import v4_native
from scripts import apply_v4_phase0_schema
from scripts import apply_focus_pg_schema_v1, apply_pg_runtime_heads_v1


def test_connection_policy_contract_version_tracks_reader_writer_separation():
    assert v4_native.CONTRACT == "V4_NATIVE_POSTGRESQL_CONNECTION_R4"


def test_reader_reuses_existing_workbench_dsn_without_new_config(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_native, "__file__", str(tmp_path / "src/workbench_db/v4_native.py"))
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN", raising=False)
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://reader@example.invalid/market_research"
    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED"):
        v4_native.configured_dsn()


def test_reader_uses_project_dsn_and_ignores_legacy_reader_override(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_native, "__file__", str(tmp_path / "src/workbench_db/v4_native.py"))
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://default@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://native@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_READER_DSN", "postgresql://readonly@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://default@example.invalid/market_research"
    monkeypatch.delenv("WORKBENCH_PG_DSN")
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://native@example.invalid/market_research")
    with pytest.raises(RuntimeError, match="WORKBENCH_PG_DSN_REQUIRED"):
        v4_native.configured_reader_dsn()


def test_writer_requires_explicit_native_dsn(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_native, "__file__", str(tmp_path / "src/workbench_db/v4_native.py"))
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED"):
        v4_native.configured_dsn()


def test_v4_migration_runner_requires_explicit_writer_dsn(monkeypatch, tmp_path):
    monkeypatch.setattr(apply_v4_phase0_schema, "ROOT", tmp_path)
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED"):
        apply_v4_phase0_schema.dsn()

    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")
    assert apply_v4_phase0_schema.dsn() == "postgresql://writer@example.invalid/market_research"


@pytest.mark.parametrize(
    ("module", "resolver"),
    [(apply_focus_pg_schema_v1, "_dsn"), (apply_pg_runtime_heads_v1, "dsn")],
)
def test_v4_schema_migration_helpers_reject_reader_dsn(monkeypatch, tmp_path, module, resolver):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED"):
        getattr(module, resolver)()


def test_reader_does_not_fall_back_to_writer_dsn(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_native, "__file__", str(tmp_path / "src/workbench_db/v4_native.py"))
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN", raising=False)
    monkeypatch.delenv("WORKBENCH_PG_DSN", raising=False)
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")

    with pytest.raises(RuntimeError, match="WORKBENCH_PG_DSN_REQUIRED"):
        v4_native.configured_reader_dsn()


class FakeResult:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row


class FakePg:
    def __init__(self, row): self.row=row; self.queries=[]
    def execute(self, query, params=None):
        self.queries.append((str(query),params))
        return FakeResult(self.row)


def test_native_reader_requires_read_only_transaction():
    class PrivilegedReadOnlyPg(FakePg):
        def execute(self, query, params=None):
            self.queries.append((str(query),params))
            return FakeResult(('on',) if str(query).startswith('SHOW transaction_read_only') else self.row)
    pg=PrivilegedReadOnlyPg(())
    assert v4_native.attest_read_role(pg,'v4_workspace_0123456789abcdef') is True
    assert pg.queries[-1][0]=='SHOW transaction_read_only'

def test_native_reader_rejects_read_write_transaction():
    class PrivilegedReadWritePg(FakePg):
        def execute(self, query, params=None):
            self.queries.append((str(query),params))
            return FakeResult(('off',) if str(query).startswith('SHOW transaction_read_only') else self.row)
    pg=PrivilegedReadWritePg(())
    with pytest.raises(RuntimeError,match='TRANSACTION_NOT_READ_ONLY'):
        v4_native.attest_read_role(pg,'v4_workspace_0123456789abcdef')


def test_native_connection_marks_transaction_read_only_before_attestation(monkeypatch):
    class ReadOnlyPg(FakePg):
        def execute(self, query, params=None):
            self.queries.append((str(query),params))
            return FakeResult(('on',))
    pg=ReadOnlyPg(())
    class Connection:
        def __enter__(self): return pg
        def __exit__(self,*args): pass
    monkeypatch.setenv("WORKBENCH_PG_DSN","postgresql://readonly@example.invalid/market_research")
    monkeypatch.setattr(v4_native.psycopg,"connect",lambda *args,**kwargs:Connection())
    with v4_native.connection("v4_workspace_0123456789abcdef",read_only=True) as received:
        assert received is pg
    assert pg.queries[0][0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert pg.queries[-1][0] == "SHOW transaction_read_only"


def test_workspace_schema_identity_is_root_scoped(tmp_path):
    first=tmp_path/"workspace-a";second=tmp_path/"workspace-b"
    first.mkdir();second.mkdir()
    assert v4_native.workspace_schema(first,"workspace") != v4_native.workspace_schema(second,"workspace")
    identity=v4_native.workspace_namespace_identity(first,"workspace")
    assert identity["schema"] == v4_native.workspace_schema(first,"workspace")
    assert identity["capabilities"]["owner_mapping"] == "MUST_BE_AUTHORITY_BOUND"
    assert "workspace-a" not in repr(identity)


def test_logical_workspace_id_survives_checkout_relocation(tmp_path):
    first = tmp_path / "drive-a" / "repo"
    second = tmp_path / "drive-b" / "repo"
    for checkout in (first, second):
        (checkout / ".git").mkdir(parents=True)
        (checkout / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://github.com/NanOns/a-share-market-structure-research.git\n',
            encoding="utf-8",
        )
        (checkout / "data" / "v4").mkdir(parents=True)

    left = v4_native.workspace_logical_id(first / "data" / "v4")
    right = v4_native.workspace_logical_id(second / "data" / "v4")

    assert left == right
    assert left.startswith("v4w_")
    assert str(first) not in left and str(second) not in right


def test_reader_uses_workbench_not_writer_or_legacy_reader_override(monkeypatch):
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://workbench@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_READER_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://workbench@example.invalid/market_research"

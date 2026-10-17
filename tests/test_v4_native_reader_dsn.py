from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db import v4_native


def test_connection_policy_contract_version_tracks_reader_writer_separation():
    assert v4_native.CONTRACT == "V4_NATIVE_POSTGRESQL_CONNECTION_R4"


def test_reader_reuses_existing_workbench_dsn_without_new_config(monkeypatch):
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN", raising=False)
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://reader@example.invalid/market_research"
    assert v4_native.configured_dsn() == "postgresql://reader@example.invalid/market_research"


def test_explicit_reader_and_native_dsn_take_precedence(monkeypatch):
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://default@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://native@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_READER_DSN", "postgresql://readonly@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://readonly@example.invalid/market_research"
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN")
    assert v4_native.configured_reader_dsn() == "postgresql://default@example.invalid/market_research"


def test_writer_dsn_reuses_the_project_database_unless_overridden(monkeypatch):
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_dsn() == "postgresql://reader@example.invalid/market_research"


def test_reader_uses_the_single_configured_database_when_no_reader_override(monkeypatch):
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN", raising=False)
    monkeypatch.delenv("WORKBENCH_PG_DSN", raising=False)
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://writer@example.invalid/market_research"


class FakeResult:
    def __init__(self, row): self.row = row
    def fetchone(self): return self.row


class FakePg:
    def __init__(self, row): self.row=row; self.queries=[]
    def execute(self, query, params=None):
        self.queries.append((str(query),params))
        return FakeResult(self.row)


@pytest.mark.parametrize("row", [
    (True, False, False, False, False, True, False, False, False),
    (False, True, False, False, False, True, False, False, False),
    (False, False, False, False, False, True, True, False, False),
    (False, False, False, False, False, True, False, True, False),
    (False, False, False, False, False, True, False, False, True),
])
def test_native_reader_role_guard_rejects_privileged_or_writable_roles(row):
    with pytest.raises(RuntimeError, match="PG_READER_ROLE_HAS_WRITE_PRIVILEGES"):
        v4_native.attest_read_role(FakePg(row), "v4_workspace_0123456789abcdef")


def test_native_reader_role_guard_requires_existing_schema():
    with pytest.raises(RuntimeError, match="PG_READER_SCHEMA_MISSING"):
        v4_native.attest_read_role(FakePg((False,False,False,False,False,False,False,False,False)), "v4_workspace_0123456789abcdef")


def test_native_reader_role_guard_accepts_nonprivileged_read_role():
    pg=FakePg((False,False,False,False,False,True,False,False,False))
    assert v4_native.attest_read_role(pg, "v4_workspace_0123456789abcdef") is True
    assert "pg_roles" in pg.queries[0][0] and pg.queries[0][1] == ("v4_workspace_0123456789abcdef",)

def test_native_reader_explicitly_allows_privileged_role_only_in_read_only_transaction(monkeypatch):
    class PrivilegedReadOnlyPg(FakePg):
        def execute(self, query, params=None):
            self.queries.append((str(query),params))
            return FakeResult(('on',) if str(query).startswith('SHOW transaction_read_only') else self.row)
    monkeypatch.setenv('V4_NATIVE_ALLOW_PRIVILEGED_READ_ROLE','1')
    pg=PrivilegedReadOnlyPg((True,True,True,True,True,True,True,True,True))
    assert v4_native.attest_read_role(pg,'v4_workspace_0123456789abcdef') is True
    assert pg.queries[-1][0]=='SHOW transaction_read_only'

def test_native_reader_privileged_opt_in_rejects_read_write_transaction(monkeypatch):
    class PrivilegedReadWritePg(FakePg):
        def execute(self, query, params=None):
            self.queries.append((str(query),params))
            return FakeResult(('off',) if str(query).startswith('SHOW transaction_read_only') else self.row)
    monkeypatch.setenv('V4_NATIVE_ALLOW_PRIVILEGED_READ_ROLE','1')
    pg=PrivilegedReadWritePg((True,True,True,True,True,True,True,True,True))
    with pytest.raises(RuntimeError,match='TRANSACTION_NOT_READ_ONLY'):
        v4_native.attest_read_role(pg,'v4_workspace_0123456789abcdef')


def test_native_connection_marks_transaction_read_only_before_role_query(monkeypatch):
    pg=FakePg((False,False,False,False,False,True,False,False,False))
    class Connection:
        def __enter__(self): return pg
        def __exit__(self,*args): pass
    monkeypatch.setenv("WORKBENCH_PG_DSN","postgresql://readonly@example.invalid/market_research")
    monkeypatch.setattr(v4_native.psycopg,"connect",lambda *args,**kwargs:Connection())
    with v4_native.connection("v4_workspace_0123456789abcdef",read_only=True) as received:
        assert received is pg
    assert pg.queries[0][0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert "pg_roles" in pg.queries[-1][0]


def test_workspace_schema_identity_is_root_scoped(tmp_path):
    first=tmp_path/"workspace-a";second=tmp_path/"workspace-b"
    first.mkdir();second.mkdir()
    assert v4_native.workspace_schema(first,"workspace") != v4_native.workspace_schema(second,"workspace")
    identity=v4_native.workspace_namespace_identity(first,"workspace")
    assert identity["schema"] == v4_native.workspace_schema(first,"workspace")
    assert identity["capabilities"]["owner_mapping"] == "MUST_BE_AUTHORITY_BOUND"
    assert "workspace-a" not in repr(identity)


def test_reader_prefers_explicit_reader_over_workbench_and_writer(monkeypatch):
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://workbench@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_READER_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://reader@example.invalid/market_research"

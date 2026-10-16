from datetime import date
import sys
from types import SimpleNamespace

import pytest

from workbench_db.v4_publication_owners import (
    SECTOR_LIFECYCLE_OWNER_CONTRACT,
    read_sector_lifecycle_owner,
)
from workbench_db.v4_publication_reader import PublicationReadError
from workbench_service.current_v4_context import canonical, digest


IDENTITY = {"database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432}
SCHEMA = "v4_" + "a" * 56
OWNER_VERSION_ID = "sector-r1"
DAY = "2026-10-15"


class SQLText(str):
    def format(self, identifier):
        return SQLText(self.replace("{}", str(identifier)))


class FakeIdentifier:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '"' + self.value.replace('"', '""') + '"'


class Cursor:
    def __init__(self, one=None, all_rows=None):
        self.one, self.all_rows = one, all_rows or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.all_rows


class FakePG:
    def __init__(self, *, corrupt_row=False, writable=False):
        self.statements = []
        self.row = {
            "sector_id": "sector-1", "T0": DAY,
            "contract_id": "SECTOR_LIFECYCLE_RECONSTRUCTED_V1", "health": "STABLE",
        }
        row_digest = digest(canonical(self.row))
        self.rows = [("sector-1", self.row, "f" * 64 if corrupt_row else row_digest)]
        self.material = {
            "owner_contract": SECTOR_LIFECYCLE_OWNER_CONTRACT, "T0": DAY,
            "producer_sha256": "1" * 64, "parameter_digest": "2" * 64,
            "input_digest": "3" * 64, "rows": [self.row],
        }
        self.material.update(dict([("token", OWNER_VERSION_ID)]))
        self.owner_digest = digest(canonical(self.material))
        self.role = (False, False, False, bool(writable), False)

    def execute(self, query, params=None):
        query = str(query)
        self.statements.append((query, params))
        if "inet_server_addr()" in query:
            return Cursor(one=("market_research", 16384, "127.0.0.1", 5432))
        if "FROM pg_roles r" in query:
            return Cursor(one=self.role)
        if "owner_versions" in query:
            return Cursor(one=(self.owner_digest, SECTOR_LIFECYCLE_OWNER_CONTRACT, True, 1, IDENTITY,
                              "1" * 64, "2" * 64, "3" * 64))
        if "owner_rows" in query:
            return Cursor(all_rows=self.rows)
        raise AssertionError(query)


def binding(pg, **changes):
    row = {
        "owner_schema": SCHEMA, "owner_relation": "owner_rows",
        "owner_contract_id": SECTOR_LIFECYCLE_OWNER_CONTRACT,
        "owner_version_token": OWNER_VERSION_ID, "owner_trade_date": date.fromisoformat(DAY),
        "database_identity": IDENTITY, "result_digest": pg.owner_digest, "row_count": 1,
    }
    row.update(changes)
    return row


def install_fake_psycopg(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(sql=SimpleNamespace(SQL=SQLText, Identifier=FakeIdentifier)))


def test_sector_lifecycle_owner_readback_verifies_version_and_every_row(monkeypatch):
    import sys
    install_fake_psycopg(monkeypatch)
    pg = FakePG()
    resolved = read_sector_lifecycle_owner(pg, binding(pg))
    assert resolved["payload"] == [pg.row]
    assert resolved["result_digest"] == pg.owner_digest
    queries = [query for query, _ in pg.statements]
    assert '"' + SCHEMA + '".owner_versions' in queries[2]
    assert '"' + SCHEMA + '".owner_rows' in queries[3]
    assert all("DROP" not in query.upper() for query in queries)


@pytest.mark.parametrize("changes,code", [
    ({"owner_relation": "other_rows"}, "SECTOR_LIFECYCLE_OWNER_LOCATOR_INVALID"),
    ({"owner_contract_id": "OTHER"}, "SECTOR_LIFECYCLE_OWNER_LOCATOR_INVALID"),
    ({"owner_schema": "v4_x;drop"}, "SECTOR_LIFECYCLE_OWNER_LOCATOR_INVALID"),
    ({"row_count": 200001}, "SECTOR_LIFECYCLE_OWNER_ROW_COUNT_INVALID"),
])
def test_sector_owner_rejects_unbound_schema_relation_contract_and_large_read(monkeypatch, changes, code):
    import sys
    install_fake_psycopg(monkeypatch)
    pg = FakePG()
    with pytest.raises(PublicationReadError, match=code):
        read_sector_lifecycle_owner(pg, binding(pg, **changes))
    assert not any("owner_versions" in query for query, _ in pg.statements)


def test_sector_owner_rejects_write_capable_role_and_row_digest_mismatch(monkeypatch):
    import sys
    install_fake_psycopg(monkeypatch)
    with pytest.raises(PublicationReadError, match="PG_READER_ROLE_HAS_OWNER_WRITE_PRIVILEGES"):
        pg = FakePG(writable=True)
        read_sector_lifecycle_owner(pg, binding(pg))
    with pytest.raises(PublicationReadError, match="SECTOR_LIFECYCLE_OWNER_ROW_DIGEST_MISMATCH"):
        pg = FakePG(corrupt_row=True)
        read_sector_lifecycle_owner(pg, binding(pg))

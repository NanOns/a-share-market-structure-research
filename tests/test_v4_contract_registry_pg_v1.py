import hashlib
import pytest

from workbench_analysis.contract_registry_pg_v1 import (
    ContractRegistryError,
    load_publication_contract,
)


class Cursor:
    def __init__(self, publication, row, session=("market_research", "v4_reader", "repeatable read", "on")):
        self.publication = publication
        self.row = row
        self.session = session
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))

    def fetchone(self):
        if len(self.calls) == 1:
            return self.session
        return self.publication if len(self.calls) == 2 else self.row


def test_reads_exact_approved_bytes_pinned_by_publication():
    raw = b'{"rule":"exact bytes"}\n'
    digest = hashlib.sha256(raw).hexdigest()
    cursor = Cursor(
        ({"RULE": {"version": "1.2.0", "raw_sha256": digest}}, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"),
        (raw, digest, "JSON", "1", "PRODUCTION", "APPROVED", "approver", "2026-10-17T00:00:00Z"),
    )
    contract = load_publication_contract(cursor, "publication-1", "RULE")
    assert contract.raw_content == raw
    assert contract.parsed_json == {"rule": "exact bytes"}
    assert contract.publication_id == "publication-1"
    assert contract.trade_date == "2026-10-16"
    assert contract.database_identity == ("market_research", "v4_reader")
    assert [call[1] for call in cursor.calls] == [(), ("publication-1",), ("RULE", "1.2.0", "2026-10-17T00:00:00Z")]


@pytest.mark.parametrize("binding,row,code", [
    ({}, None, "V4_PUBLICATION_CONTRACT_NOT_BOUND"),
    ({"RULE": {"version": "1.2.0", "raw_sha256": "0" * 64}},
     (b"{}", "0" * 64, "JSON", "1", "PRODUCTION", "APPROVED", "approver", "2026-10-17"),
     "V4_PG_CONTRACT_APPROVAL_OR_DIGEST_INVALID"),
])
def test_missing_or_mismatched_contract_fails_closed(binding, row, code):
    cursor = Cursor((binding, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"), row)
    with pytest.raises(ContractRegistryError, match=code):
        load_publication_contract(cursor, "publication-1", "RULE")


def test_contract_registry_schema_absence_does_not_fallback_to_files():
    class MissingRegistry(Cursor):
        def execute(self, query, params=()):
            self.calls.append((query, params))
            if "contract_versions" in query:
                raise RuntimeError("undefined table")

    cursor = MissingRegistry(({"RULE": {"version": "1.2.0", "raw_sha256": "a" * 64}}, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"), None)
    with pytest.raises(ContractRegistryError, match="V4_PG_CONTRACT_REGISTRY_UNAVAILABLE"):
        load_publication_contract(cursor, "publication-1", "RULE")


@pytest.mark.parametrize("session", [
    ("market_research", "v4_reader", "read committed", "on"),
    ("market_research", "v4_reader", "repeatable read", "off"),
])
def test_contract_read_requires_same_readonly_repeatable_read_snapshot(session):
    cursor = Cursor(({}, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"), None, session=session)
    with pytest.raises(ContractRegistryError, match="V4_PG_READONLY_REPEATABLE_READ_REQUIRED"):
        load_publication_contract(cursor, "publication-1", "RULE")


def test_registry_migration_preserves_immutable_bytes_and_historical_acceptance():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "docs/upgrade/R21R3_V4_CONTRACT_REGISTRY_MIGRATION_DRAFT_20261017.sql").read_text(encoding="utf-8")
    assert "contract_approval_events" in sql
    assert "contract_versions_append_only" in sql
    assert "NOT VALID" in sql
    assert "UPDATE OF contract_bindings" not in sql
    assert "BEFORE INSERT OR UPDATE ON v4.publications" in sql

import hashlib
import pytest

from workbench_analysis.contract_registry_pg_v1 import (
    ContractRegistryError,
    load_publication_contract,
    load_publication_contracts,
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
        (raw, digest, "JSON", "1", "PRODUCTION", "revision-1", "APPROVED", "approver",
         "approval-1", "2026-10-17T00:00:00Z", "revision-1", digest, "2026-10-17T00:00:00Z"),
    )
    contract = load_publication_contract(cursor, "publication-1", "RULE")
    assert contract.raw_content == raw
    assert contract.parsed_json == {"rule": "exact bytes"}
    assert contract.publication_id == "publication-1"
    assert contract.trade_date == "2026-10-16"
    assert contract.database_identity == ("market_research", "v4_reader")
    assert contract.approved_by == "approver"
    assert contract.approval_ref == "approval-1"
    assert contract.approval_occurred_at == "2026-10-17T00:00:00Z"
    assert contract.approval_recorded_at == "2026-10-17T00:00:00Z"
    assert contract.approval_source_sha256 == digest
    assert [call[1] for call in cursor.calls] == [(), ("publication-1",),
        ("2026-10-17T00:00:00Z", "2026-10-17T00:00:00Z", "RULE", "1.2.0", digest)]


def test_reads_current_contract_only_after_registry_approval_and_identity_attestation():
    from workbench_analysis.contract_registry_pg_v1 import load_current_approved_contract
    raw=b'{"contract_id":"RUNTIME","contract_version":"1.1.0"}'
    sha=hashlib.sha256(raw).hexdigest()
    identity={"database":"market_research","database_oid":1,"host":"127.0.0.1","port":5432}
    row=(raw,sha,"JSON","1","PRODUCTION","source-r7","APPROVED","owner",
        "approval-r7","2026-10-17T00:00:00Z","source-r7",sha,"2026-10-17T00:00:01Z")

    class Result:
        def __init__(self,value):self.value=value
        def fetchone(self):return self.value
    class ReadSnapshot:
        def execute(self,query,params=()):
            if "current_database()" in query and "transaction_isolation" in query:
                return Result(("market_research","v4_reader","repeatable read","on"))
            if "inet_server_addr()" in query:return Result(("market_research",1,"127.0.0.1",5432))
            if "FROM pg_roles" in query:return Result(("v4_reader",)+tuple(False for _ in range(14)))
            if "FROM v4.contract_versions" in query:
                assert params==("RUNTIME","1.1.0","PRODUCTION")
                return Result(row)
            raise AssertionError(query)

    contract=load_current_approved_contract(ReadSnapshot(),"RUNTIME","1.1.0","PRODUCTION",
        expected_database_identity=identity)
    assert contract.raw_content==raw and contract.parsed_json["contract_version"]=="1.1.0"
    assert contract.publication_id==""
    assert contract.approved_by=="owner" and contract.approval_ref=="approval-r7"


@pytest.mark.parametrize("action,approval_sha",[("REVOKED","a"*64),("APPROVED","0"*64)])
def test_current_contract_reader_rejects_revocation_and_changed_source(action,approval_sha):
    from workbench_analysis.contract_registry_pg_v1 import load_current_approved_contract
    raw=b'{}';sha=hashlib.sha256(raw).hexdigest()
    row=(raw,sha,"JSON","1","PRODUCTION","source-r7",action,"owner",
        "approval-r7","2026-10-17T00:00:00Z","source-r7",approval_sha,"2026-10-17T00:00:01Z")
    identity={"database":"market_research","database_oid":1,"host":"127.0.0.1","port":5432}
    class Result:
        def __init__(self,value):self.value=value
        def fetchone(self):return self.value
    class ReadSnapshot:
        def execute(self,query,params=()):
            if "current_database()" in query and "transaction_isolation" in query:return Result(("market_research","v4_reader","repeatable read","on"))
            if "inet_server_addr()" in query:return Result(("market_research",1,"127.0.0.1",5432))
            if "FROM pg_roles" in query:return Result(("v4_reader",)+tuple(False for _ in range(14)))
            if "FROM v4.contract_versions" in query:return Result(row)
            raise AssertionError(query)
    with pytest.raises(ContractRegistryError,match="APPROVAL_OR_DIGEST_INVALID"):
        load_current_approved_contract(ReadSnapshot(),"RUNTIME","1.1.0","PRODUCTION",
            expected_database_identity=identity)


@pytest.mark.parametrize("binding,row,code", [
    ({}, None, "V4_PUBLICATION_CONTRACT_NOT_BOUND"),
    ({"RULE": {"version": "1.2.0", "raw_sha256": "0" * 64}},
     (b"{}", "0" * 64, "JSON", "1", "PRODUCTION", "revision-1", "APPROVED", "approver",
      "approval-1", "2026-10-17", "revision-1", "0" * 64, "2026-10-17"),
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


@pytest.mark.parametrize("raw", [
    b"<!DOCTYPE contract><contract/>",
    "<!DOCTYPE contract><contract/>".encode("utf-16"),
    "<!ENTITY x 'external'>".encode("utf-32-be"),
])
def test_xml_contract_rejects_dtd_and_entity_in_multibyte_encodings(raw):
    digest = hashlib.sha256(raw).hexdigest()
    cursor = Cursor(
        ({"RULE": {"version": "1.2.0", "raw_sha256": digest}}, "PRODUCTION", "ACCEPTED",
         "2026-10-17T00:00:00Z", "2026-10-16"),
        (raw, digest, "XML", "1", "PRODUCTION", "revision-1", "APPROVED", "approver",
         "approval-1", "2026-10-17T00:00:00Z", "revision-1", digest, "2026-10-17T00:00:00Z"),
    )
    with pytest.raises(ContractRegistryError, match="V4_PG_CONTRACT_XML_DTD_FORBIDDEN"):
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
    assert "contract_approval_events" in sql
    assert "NEW.recorded_at := clock_timestamp()" in sql
    assert "BEFORE TRUNCATE ON v4.contract_versions" in sql
    assert "BEFORE TRUNCATE ON v4.contract_approval_events" in sql
    assert "ORDER BY e.occurred_at DESC, e.recorded_at DESC, e.event_id DESC" in sql
    assert "V4_ACCEPTED_PUBLICATION_IDENTITY_IMMUTABLE" in sql
    assert "V4_ACCEPTED_PUBLICATION_CONTRACT_BINDINGS_IMMUTABLE" in sql
    assert "to_jsonb(NEW) - 'contract_bindings'" in sql
    assert sql.index("V4_ACCEPTED_PUBLICATION_IDENTITY_IMMUTABLE") < sql.index("NEW.contract_bindings IS NULL AND OLD.contract_bindings IS NULL")
    assert "CREATE EXTENSION" not in sql
    assert "encode(sha256(raw_content), 'hex') = raw_sha256" in sql


def test_registry_sql_matches_canonical_publication_schema_after_phase0_alignment():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    foundation = (root / "src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql").read_text(encoding="utf-8")
    alignment = (root / "src/workbench_db/migrations/v4_postgres/003_phase0_contract_alignment.sql").read_text(encoding="utf-8")
    registry = (root / "docs/upgrade/R21R3_V4_CONTRACT_REGISTRY_MIGRATION_DRAFT_20261017.sql").read_text(encoding="utf-8")

    # This draft is applied after the canonical alignment migration, which
    # renames publications.revision and adds the fields it relies on.
    assert "CREATE TABLE IF NOT EXISTS v4.publications" in foundation
    assert "revision integer NOT NULL" in foundation
    assert "RENAME COLUMN revision TO revision_no" in alignment
    assert "ADD COLUMN publication_lineage_id text NOT NULL" in alignment
    assert "ADD COLUMN same_day_revision_parent_id text" in alignment
    assert "p.revision_no" not in registry
    assert "NEW.revision_no" not in registry
    assert "NEW.model_namespace_id" in registry
    assert "NEW.accepted_at" in registry
    assert "v4.model_namespaces" in registry
    assert "CREATE EXTENSION" not in registry


def test_approval_event_selection_is_historical_and_revocation_aware():
    from pathlib import Path

    migration = (Path(__file__).resolve().parents[1] / "docs/upgrade/R21R3_V4_CONTRACT_REGISTRY_MIGRATION_DRAFT_20261017.sql").read_text(encoding="utf-8")
    reader = (Path(__file__).resolve().parents[1] / "src/workbench_analysis/contract_registry_pg_v1.py").read_text(encoding="utf-8")
    assert "e.occurred_at <= NEW.accepted_at" in migration
    assert "e.recorded_at <= NEW.accepted_at" in migration
    assert "e.source_revision = c.source_revision" in migration
    assert "ORDER BY e.occurred_at DESC, e.recorded_at DESC, e.event_id DESC" in migration
    assert "e.occurred_at <= %s" in reader
    assert "e.recorded_at <= %s" in reader
    assert "ORDER BY e.occurred_at DESC, e.recorded_at DESC, e.event_id DESC" in reader
    assert "IF NOT FOUND OR approval.action <> 'APPROVED'" in migration
    assert 'action != "APPROVED"' in reader


def test_registry_catalog_preflight_is_repeatable_read_and_select_only():
    import re
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "docs/upgrade/R21R4_V4_CONTRACT_REGISTRY_PREFLIGHT_READONLY_20261017.sql").read_text(encoding="utf-8")
    statements = re.sub(r"--[^\n]*", "", sql)
    statements = [part.strip().upper() for part in statements.split(";") if part.strip()]
    assert statements[0] == "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert statements[-1] == "COMMIT"
    assert all(statement.startswith(("SELECT ", "WITH ")) for statement in statements[1:-1])
    assert "TO_REGPROCEDURE('SHA256(BYTEA)')" in sql.upper()
    assert "PUBLICATION_BINDINGS_COLUMN_EXISTS" in sql.upper()
    assert "PUBLICATIONS_INSERT" in sql.upper()
    assert "APPROVAL_EVENTS_SELECT" in sql.upper()


def test_registry_rollback_refuses_to_discard_history_or_bound_publications():
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "docs/upgrade/R21R4_V4_CONTRACT_REGISTRY_ROLLBACK_DRAFT_20261017.sql").read_text(encoding="utf-8")
    assert "V4_CONTRACT_REGISTRY_ROLLBACK_REFUSED_DATA_PRESENT" in sql
    assert "FROM v4.contract_versions" in sql
    assert "FROM v4.contract_approval_events" in sql
    assert "contract_bindings IS NOT NULL" in sql
    assert "DROP TABLE v4.contract_approval_events" in sql
    assert "DROP TABLE v4.contract_versions" in sql


@pytest.mark.parametrize("action,source_digest", [("REVOKED", "a" * 64), ("APPROVED", "0" * 64)])
def test_latest_approval_event_must_be_approved_and_bind_exact_source_digest(action, source_digest):
    raw = b'{"rule":"event state"}'
    digest = hashlib.sha256(raw).hexdigest()
    cursor = Cursor(
        ({"RULE": {"version": "1.2.0", "raw_sha256": digest}}, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"),
        (raw, digest, "JSON", "1", "PRODUCTION", "revision-1", action, "approver",
         "approval-1", "2026-10-17T00:00:00Z", "revision-1", source_digest, "2026-10-17T00:00:00Z"),
    )
    with pytest.raises(ContractRegistryError, match="V4_PG_CONTRACT_APPROVAL_OR_DIGEST_INVALID"):
        load_publication_contract(cursor, "publication-1", "RULE")


@pytest.mark.parametrize("approved_by,approval_ref,approval_source_revision", [
    ("   ", "approval-1", "revision-1"),
    ("approver", "  ", "revision-1"),
    ("approver", "approval-1", "different-revision"),
])
def test_approval_event_must_bind_nonblank_identity_and_exact_source_revision(
    approved_by, approval_ref, approval_source_revision
):
    raw = b'{"rule":"source revision binding"}'
    digest = hashlib.sha256(raw).hexdigest()
    cursor = Cursor(
        ({"RULE": {"version": "1.2.0", "raw_sha256": digest}}, "PRODUCTION", "ACCEPTED", "2026-10-17T00:00:00Z", "2026-10-16"),
        (raw, digest, "JSON", "1", "PRODUCTION", "revision-1", "APPROVED", approved_by,
         approval_ref, "2026-10-17T00:00:00Z", approval_source_revision, digest, "2026-10-17T00:00:00Z"),
    )
    with pytest.raises(ContractRegistryError, match="V4_PG_CONTRACT_APPROVAL_OR_DIGEST_INVALID"):
        load_publication_contract(cursor, "publication-1", "RULE")


def test_batch_loader_requires_the_complete_publication_contract_map():
    class BatchCursor:
        def __init__(self, stored, session=("repeatable read", "on")):
            self.stored = stored
            self.session = session
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))

        def fetchone(self):
            query, _ = self.calls[-1]
            if "current_setting('transaction_isolation')" in query:
                return self.session
            return (self.stored,)

    full = {
        "A": {"version": "1.0.0", "raw_sha256": "a" * 64},
        "B": {"version": "2.0.0", "raw_sha256": "b" * 64},
    }
    for supplied in (
        {"A": full["A"]},
        {**full, "C": {"version": "1.0.0", "raw_sha256": "c" * 64}},
        {"A": {"version": "9.9.9", "raw_sha256": "a" * 64}, "B": full["B"]},
    ):
        cursor = BatchCursor(full)
        with pytest.raises(ContractRegistryError, match="V4_PUBLICATION_CONTRACT_BINDINGS_MISMATCH"):
            load_publication_contracts(cursor, "publication-1", 3, supplied)
        assert len(cursor.calls) == 2


def test_batch_loader_requires_repeatable_read_only_scope():
    class BatchCursor:
        def execute(self, query, params=()):
            self.query = query

        def fetchone(self):
            return ("read committed", "on")

    with pytest.raises(ContractRegistryError, match="V4_PG_READONLY_REPEATABLE_READ_REQUIRED"):
        load_publication_contracts(BatchCursor(), "publication-1", 3,
                                   {"A": {"version": "1.0.0", "raw_sha256": "a" * 64}})

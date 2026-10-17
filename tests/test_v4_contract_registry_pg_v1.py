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

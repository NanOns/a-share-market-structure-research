from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "src/workbench_db/migrations/v4_postgres"


def read(path):
    return path.read_text(encoding="utf-8")


def test_final_migrations_define_publication_id_as_identity_and_revision_no_as_sequence():
    m003 = read(MIGRATIONS / "003_phase0_contract_alignment.sql")
    m004 = read(MIGRATIONS / "004_publication_head_revision_identity.sql")
    m008 = read(MIGRATIONS / "008_prior_session_state_freeze_integrity.sql")
    assert "RENAME COLUMN revision TO revision_no" in m003
    assert "PRIMARY KEY (publication_id)" in m003
    assert "publication_heads DROP COLUMN IF EXISTS revision" in m003
    assert "publication_id is the immutable revision identity" in m004.lower()
    assert "state_head_id" in m008 and "state_logical_digest" in m008
    assert "prior_session_state_logical_digest" in m008


def test_candidate_sql_binds_real_owner_families_and_uses_final_publication_identity():
    sql = read(ROOT / "docs/design/sql/V4_PUBLICATION_OWNER_BINDINGS_CANDIDATE_R3.sql")
    assert "REFERENCES v4.publications(publication_id)" in sql
    assert "PRIMARY KEY (publication_id, module_key)" in sql
    assert "REFERENCES v4.publications(publication_id, revision)" not in sql
    assert not re.search(r"\b(?:p|h)\.revision\b", sql)
    assert "revision_no" in sql and "same_day_revision_parent_id" in sql
    assert "research_priority" in sql and "operational_risk" in sql and "sector_lifecycle" in sql
    assert "global required prerequisites" in sql


def test_candidate_sql_serializes_associations_without_invented_seven_owner_completeness():
    sql = read(ROOT / "docs/design/sql/V4_PUBLICATION_OWNER_BINDINGS_CANDIDATE_R3.sql")
    assert sql.count("pg_advisory_xact_lock") >= 2
    assert "V4_PUBLICATION_MODULE_SET_SEALED" in sql
    assert "V4_PUBLICATION_REQUIRED_MODULE_SET_INCOMPLETE" not in sql
    assert "BEFORE UPDATE OR DELETE ON v4.publication_module_results" in sql
    assert "BEFORE TRUNCATE ON v4.publication_module_results" in sql
    assert "not a migration" in sql.lower()


def test_reader_rehashes_sources_in_one_read_only_final_schema_context():
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")
    assert "p.revision_no" in reader
    assert "h.revision" not in reader and "p.revision," not in reader
    assert "v4.state_heads" in reader and "verified_state_digest" in reader
    assert "v4.publication_consumed_sources" in reader and "v4.source_revisions" in reader
    assert "system_available_at" in reader and "provider_available_at" in reader
    assert "has_table_privilege" in reader and "rolsuper" in reader and "rolbypassrls" in reader
    assert 'env.get("V4_NATIVE_PG_DSN")' not in reader
    assert "SOURCE_MANIFEST_REHASH_MISMATCH" in reader
    assert "SOURCE_MANIFEST_CONTRACT_UNSUPPORTED" in reader


def test_manifest_migration_keeps_legacy_unknown_and_requires_r1_on_new_rows():
    migration = read(MIGRATIONS / "010_source_manifest_contract_r1.sql")
    assert "ADD COLUMN source_manifest_contract_id text" in migration
    assert "V4_PG_CONSUMED_SOURCE_MANIFEST_R1" in migration
    assert "BEFORE INSERT ON v4.publications" in migration


def test_contract_models_three_real_owner_families_and_explicit_page_gaps():
    contract = read(ROOT / "src/workbench_db/v4_publication_contract.py")
    assert "V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R3" in contract
    assert "daily_publication_required\": False" in contract
    assert "uncovered_groups" in contract
    assert "SECTOR_LIFECYCLE_SUPPLEMENT_ONLY" in contract
    assert '"entity": MappingProxyType' in contract
    candidate = read(ROOT / "src/workbench_db/v4_publication_candidate.py")
    assert "CANDIDATE_REQUIREMENTS_UNVERIFIED" in candidate
    assert "GLOBAL_REQUIREDNESS_UNVERIFIED" in candidate
    assert 'candidate.get("global_requiredness_status") != "PASS"' in candidate


def test_sector_owner_resolver_uses_fixed_relations_and_quoted_schema_identifier():
    owner = read(ROOT / "src/workbench_db/v4_publication_owners.py")
    assert '"SELECT digest,contract,sealed,row_count,database_identity, "' in owner
    assert '"SELECT sector_id,payload,payload_sha256 FROM {}.owner_rows "' in owner
    assert "sql.Identifier(schema)" in owner
    assert "owner_version_token" in owner and "payload_sha256" in owner
    assert "PG_READER_ROLE_HAS_OWNER_WRITE_PRIVILEGES" in owner


def test_all_current_entries_are_candidate_only_and_default_reader_is_unchanged():
    adapter = read(ROOT / "src/workbench_service/v4_pg_current_adapter.py")
    server = read(ROOT / "src/workbench_service/v4_control_server_v2.py")
    for endpoint in ("summary", "radar", "entity", "sector", "cohort", "settlement", "health"):
        assert f"/api/v4/current/{endpoint}" in adapter
    assert '"status": status' in adapter
    assert '"quality_status": "NOT_VERIFIABLE_PAGE_PARITY"' in adapter
    assert "READY_CURRENT_ACCEPTED" not in adapter
    assert "CurrentAcceptedV4Reader" in server
    assert "PgV4CurrentAdapter" not in server

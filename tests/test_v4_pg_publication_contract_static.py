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


def test_candidate_sql_uses_final_schema_and_single_publication_id_foreign_key():
    sql = read(ROOT / "docs/design/sql/V4_PUBLICATION_MODULE_RESULTS_CANDIDATE_R2.sql")
    assert "REFERENCES v4.publications(publication_id)" in sql
    assert "PRIMARY KEY (publication_id, module_key)" in sql
    assert "REFERENCES v4.publications(publication_id, revision)" not in sql
    assert not re.search(r"\b(?:p|h)\.revision\b", sql)
    assert "revision_no" in sql and "same_day_revision_parent_id" in sql
    assert "state_head_id" in sql and "state_logical_digest" in sql


def test_candidate_sql_serializes_append_seal_and_requires_complete_module_set():
    sql = read(ROOT / "docs/design/sql/V4_PUBLICATION_MODULE_RESULTS_CANDIDATE_R2.sql")
    assert sql.count("pg_advisory_xact_lock") >= 2
    assert "V4_PUBLICATION_MODULE_SET_SEALED" in sql
    assert "V4_PUBLICATION_REQUIRED_MODULE_SET_INCOMPLETE" in sql
    assert "BEFORE UPDATE OR DELETE ON v4.publication_module_results" in sql
    assert "BEFORE TRUNCATE ON v4.publication_module_results" in sql
    assert "CREATE TRIGGER v4_publication_module_set_seal_r2" in sql
    assert "not a migration" in sql.lower()


def test_reader_validates_sources_state_and_reader_role_without_legacy_revision_columns():
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")
    assert "p.revision_no" in reader
    assert "h.revision" not in reader and "p.revision," not in reader
    assert "v4.state_heads" in reader and "verified_state_digest" in reader
    assert "v4.publication_consumed_sources" in reader and "v4.source_revisions" in reader
    assert "system_available_at" in reader and "provider_available_at" in reader
    assert "has_table_privilege" in reader and "rolsuper" in reader and "rolbypassrls" in reader
    assert 'env.get("V4_NATIVE_PG_DSN")' not in reader
    assert "NOT_PROVEN_MANIFEST_SERIALIZATION_UNSPECIFIED" in reader


def test_sector_owner_readback_uses_fixed_relation_and_quoted_schema_identifier():
    owner = read(ROOT / "src/workbench_db/v4_publication_owners.py")
    assert '"SELECT digest,contract,sealed,row_count,database_identity, "' in owner
    assert '"SELECT sector_id,payload,payload_sha256 FROM {}.owner_rows "' in owner
    assert "sql.Identifier(schema)" in owner
    assert "owner_version_token" in owner and "payload_sha256" in owner
    assert "PG_READER_ROLE_HAS_OWNER_WRITE_PRIVILEGES" in owner


def test_all_seven_page_entrypoints_have_explicit_candidate_adapter_and_no_default_wiring():
    adapter = read(ROOT / "src/workbench_service/v4_pg_current_adapter.py")
    server = read(ROOT / "src/workbench_service/v4_control_server_v2.py")
    for endpoint in ("summary", "radar", "entity", "sector", "cohort", "settlement", "health"):
        assert f"/api/v4/current/{endpoint}" in adapter
    assert "candidate_only" in adapter and "module_payloads" in adapter
    assert "CurrentAcceptedV4Reader" in server
    assert "PgV4CurrentAdapter" not in server

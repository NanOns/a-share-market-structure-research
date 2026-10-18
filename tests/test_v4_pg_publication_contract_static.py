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
    contract = read(ROOT / "src/workbench_db/v4_publication_contract.py")
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")
    native = read(ROOT / "src/workbench_db/v4_native.py")
    assert "p.revision_no" in reader
    assert "h.revision" not in reader and "p.revision," not in reader
    assert "v4.state_heads" in reader and "verified_state_digest" in reader
    assert "v4.publication_consumed_sources" in reader and "v4.source_revisions" in reader
    assert "system_available_at" in reader and "provider_available_at" in reader
    assert 'attest_read_role(pg, "v4")' in reader
    assert "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY" in native
    assert "SHOW transaction_read_only" in native
    assert 'env.get("V4_NATIVE_PG_DSN")' not in reader
    assert "SOURCE_MANIFEST_REHASH_MISMATCH" in reader
    assert "SOURCE_MANIFEST_CONTRACT_UNSUPPORTED" in reader


def test_r4_source_and_page_field_map_matches_final_migration_relations():
    m001 = read(MIGRATIONS / "001_v4_phase0_foundation.sql")
    m003 = read(MIGRATIONS / "003_phase0_contract_alignment.sql")
    m016 = read(MIGRATIONS / "016_v4_08_sector_membership.sql")
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")
    contract = read(ROOT / "src/workbench_db/v4_publication_contract.py")
    for field in (
        "logical_fact_id", "revision_no", "digest", "effective_from", "effective_to",
        "provider_available_at", "observed_at", "ingested_at", "system_available_at", "tombstone",
    ):
        assert field in m001
    assert "publication_consumed_sources" in m003 and "source_key" in m001
    assert "v4.event_observations" in reader and "publication_id=%s" in reader
    assert "v4.security_lifecycle_facts" in reader and "source_revision_id=ANY(%s)" in reader
    assert "v4.sector_membership_facts" in m016
    assert "MEMBERSHIP_RELATION_NOT_BOUND_TO_PUBLICATION" in contract


def test_manifest_migration_keeps_legacy_unknown_and_requires_r1_on_new_rows():
    migration = read(MIGRATIONS / "010_source_manifest_contract_r1.sql")
    assert "ADD COLUMN source_manifest_contract_id text" in migration
    assert "V4_PG_CONSUMED_SOURCE_MANIFEST_R1" in migration
    assert "BEFORE INSERT ON v4.publications" in migration


def test_contract_models_three_real_owner_families_and_explicit_page_gaps():
    contract = read(ROOT / "src/workbench_db/v4_publication_contract.py")
    assert "V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R4" in contract
    assert "daily_publication_required\": False" in contract
    assert "uncovered_groups" in contract
    assert "SECTOR_LIFECYCLE_SUPPLEMENT_ONLY" in contract
    assert '"entity": MappingProxyType' in contract
    candidate = read(ROOT / "src/workbench_db/v4_publication_candidate.py")
    assert "CANDIDATE_SOURCE_MANIFEST_UNVERIFIED" in candidate
    assert "build_source_manifest(source_manifest_rows)" in candidate
    assert 'candidate.get("business_publishability_status") != "PUBLISHABLE_BUSINESS_SNAPSHOT"' in candidate
    assert '"business_publishability_status": "PUBLISHABLE_BUSINESS_SNAPSHOT" if publishable else "BLOCKED_CORE_RESULT_NOT_BOUND"' in candidate
    assert 'candidate.get("minimum_publish_contract_id") != MINIMUM_DAILY_PUBLICATION_CONTRACT_ID' in candidate
    assert '"minimum_publish_contract_id": MINIMUM_DAILY_PUBLICATION_CONTRACT_ID' in candidate


def test_r4_owner_binding_relation_is_migrated_for_the_exact_reader_contract():
    migration = read(MIGRATIONS / "038_publication_module_results_r4.sql")
    contract = read(ROOT / "src/workbench_db/v4_publication_contract.py")
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")
    ledger = read(ROOT / "scripts/apply_v4_phase0_schema.py")
    assert "CREATE TABLE v4.publication_module_results" in migration
    assert "V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R4" in migration
    assert "V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R4" in contract
    assert "OWNER_FAMILIES" in reader
    assert "PRIMARY KEY (publication_id, module_key)" in migration
    assert "BEFORE UPDATE OR DELETE ON v4.publication_module_results" in migration
    assert "BEFORE TRUNCATE ON v4.publication_module_results" in migration
    assert "V4_PUBLICATION_MODULE_SET_SEALED" in migration
    assert "research_priority" in migration and "operational_risk" in migration and "sector_lifecycle" in migration
    assert "REQUIRED_MODULE_RESULT" not in migration
    assert '"038_publication_module_results_r4.sql":"V4_PUBLICATION_MODULE_RESULTS_R4"' in ledger


def test_sector_owner_resolver_uses_fixed_relations_and_quoted_schema_identifier():
    owner = read(ROOT / "src/workbench_db/v4_publication_owners.py")
    assert '"SELECT digest,contract,sealed,row_count,database_identity, "' in owner
    assert '"SELECT sector_id,payload,payload_sha256 FROM {}.owner_rows "' in owner
    assert "sql.Identifier(schema)" in owner
    assert "owner_version_token" in owner and "payload_sha256" in owner
    assert "PG_READER_ROLE_HAS_OWNER_WRITE_PRIVILEGES" in owner


def test_all_current_entries_are_candidate_only_and_default_reader_is_unchanged():
    adapter = read(ROOT / "src/workbench_service/v4_pg_current_adapter.py")
    server = read(ROOT / "src/workbench_service/v4_server.py")
    for endpoint in ("summary", "radar", "entity", "sector", "cohort", "settlement", "health"):
        assert f"/api/v4/current/{endpoint}" in adapter
    assert '"status": status' in adapter
    assert '"quality_status": "NOT_VERIFIABLE_PAGE_PARITY"' in adapter
    assert "READY_CURRENT_ACCEPTED" not in adapter
    assert "CurrentAcceptedV4Reader" in server
    assert "pg_candidate" in server
    assert "PG_CANDIDATE_READER_UNAVAILABLE" in server
    assert "allow_pg_candidate=False" in server
    assert "def serve_v4_candidate" in server


def test_r5_source_revision_requires_immutable_accepted_package_and_r2_manifest():
    authority = read(MIGRATIONS / "034_source_package_revision_authority_r2.sql")
    manifest = read(MIGRATIONS / "035_source_manifest_contract_r2.sql")
    assert "ADD COLUMN source_package_id text" in authority
    assert "FOREIGN KEY (source_package_id) REFERENCES v4.source_packages(package_id)" in authority
    assert "V4_SOURCE_PACKAGE_BINDING_REQUIRED" in authority
    assert "V4_SOURCE_PACKAGE_NOT_ACCEPTED" in authority
    assert "source_package_authority_immutable" in authority
    assert "V4_PG_CONSUMED_SOURCE_MANIFEST_R1" in manifest
    assert "V4_PG_CONSUMED_SOURCE_MANIFEST_R2" in manifest
    assert "V4_SOURCE_MANIFEST_R2_CONTRACT_REQUIRED" in manifest

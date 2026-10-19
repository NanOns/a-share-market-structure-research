from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "src/workbench_db/migrations/v4_postgres"


def test_core_result_migration_uses_current_publication_identity_columns():
    sql = (MIGRATION / "037_daily_core_result_binding_r6.sql").read_text(encoding="utf-8").lower()
    assert "references v4.publications(publication_id, revision)" not in sql
    assert "p.revision_no=new.publication_revision" in sql
    assert "where publication_id=new.publication_id and revision_no=new.publication_revision" in sql
    assert "s.publication_revision=new.revision_no" in sql
    assert "cs.revision=" not in sql
    # The primary key already creates the same leading-key index.
    assert "create index ix_daily_core_result_rows_security" not in sql


def test_source_provenance_migration_uses_existing_revision_and_consumed_source_keys():
    sql = (MIGRATION / "036_source_package_fact_provenance_r6.sql").read_text(encoding="utf-8").lower()
    ingest = (ROOT / "src/workbench_db/v4_daily_source_ingest_r6.py").read_text(encoding="utf-8").lower()
    normalized_ingest = " ".join(ingest.split())
    assert "(source_revision_id, logical_fact_id, revision_no, payload, digest," in normalized_ingest
    assert "order by revision_no desc" in ingest
    assert "where publication_id=%s and source_key=%s" in ingest
    assert "(publication_id, source_key, source_revision_id, digest)" in normalized_ingest
    assert "source_package_source_key" in sql
    assert "source_fact_digest" in sql
    assert "and item->'record_locator'=new.record_locator" in " ".join(sql.split())
    assert "where new.publication_id=%s and revision=%s" not in ingest


def test_publication_migration_runner_registers_the_ordered_034_to_039_chain():
    runner = (ROOT / "scripts/apply_v4_phase0_schema.py").read_text(encoding="utf-8")
    normalized = " ".join(runner.split())
    for migration, contract in (
        ("010_source_manifest_contract_r1.sql", "V4_PG_CONSUMED_SOURCE_MANIFEST_R1"),
        ("034_source_package_revision_authority_r2.sql", "V4_SOURCE_PACKAGE_REVISION_AUTHORITY_R2"),
        ("035_source_manifest_contract_r2.sql", "V4_SOURCE_MANIFEST_CONTRACT_R2"),
        ("036_source_package_fact_provenance_r6.sql", "V4_SOURCE_PACKAGE_FACT_PROVENANCE_R6"),
        ("037_daily_core_result_binding_r6.sql", "V4_DAILY_CORE_RESULT_BINDING_R6"),
        ("038_publication_module_results_r4.sql", "V4_PUBLICATION_MODULE_RESULTS_R4"),
        ("039_tdx_package_row_count_authority_r1.sql", "V4_TDX_PACKAGE_ROW_COUNT_AUTHORITY_R1"),
        ("071_v4_publication_owner_canonical_schema_r1.sql", "V4_PUBLICATION_OWNER_CANONICAL_SCHEMA_R1"),
    ):
        assert f'"{migration}":"{contract}"' in normalized
    assert "for filename,version in sorted(VERSIONS.items())" in normalized
    assert "MIGRATIONS.glob(\"*.sql\")" not in runner


def test_publication_owner_locator_migration_requires_only_canonical_schema():
    migration = (MIGRATION / "071_v4_publication_owner_canonical_schema_r1.sql").read_text(encoding="utf-8")
    assert "DROP CONSTRAINT publication_module_results_owner_schema_check" in migration
    assert "CHECK (owner_schema = 'v4')" in migration


def test_migration_schema_normalizer_allows_only_historical_foundation_rewrite():
    import pytest
    from scripts.apply_v4_phase0_schema import VERSIONS, normalize_migration_schema

    legacy = (MIGRATION / "001_v4_phase0_foundation.sql").read_text(encoding="utf-8")
    normalized = normalize_migration_schema("001_v4_phase0_foundation.sql", legacy)
    assert "CREATE SCHEMA IF NOT EXISTS v4_meta" not in normalized
    assert "v4_meta.schema_migrations" not in normalized
    assert "CREATE SCHEMA IF NOT EXISTS v4" in normalized

    ledger = (MIGRATION / "057_v4_schema_migration_ledger_r1.sql").read_text(encoding="utf-8")
    ledger_normalized = normalize_migration_schema("057_v4_schema_migration_ledger_r1.sql", ledger)
    assert "v4_meta" not in ledger_normalized
    assert ledger_normalized.rstrip().endswith("SELECT 1;")
    with pytest.raises(RuntimeError, match="V4_LEGACY_LEDGER_MIGRATION_IDENTITY_MISMATCH"):
        normalize_migration_schema("057_v4_schema_migration_ledger_r1.sql", ledger + "\n-- changed")

    for filename in VERSIONS:
        source = (MIGRATION / filename).read_text(encoding="utf-8")
        executable = normalize_migration_schema(filename, source)
        if filename != "001_v4_phase0_foundation.sql":
            assert "v4_meta" not in executable.casefold(), filename
            assert "CREATE SCHEMA" not in executable.upper(), filename

    with pytest.raises(RuntimeError, match="V4_SINGLE_SCHEMA_MIGRATION_SCHEMA_CREATE_BLOCKED"):
        normalize_migration_schema("071_new.sql", "CREATE SCHEMA v4_test;")
    with pytest.raises(RuntimeError, match="V4_SINGLE_SCHEMA_MIGRATION_SCHEMA_CREATE_BLOCKED"):
        normalize_migration_schema("071_new.sql", "CREATE SCHEMA v4;")
    with pytest.raises(RuntimeError, match="V4_SINGLE_SCHEMA_RETIRED_META_SCHEMA_REFERENCE_BLOCKED"):
        normalize_migration_schema("071_new.sql", "SELECT * FROM v4_meta.schema_migrations;")


def test_phase0_runner_is_not_authorized_and_apply_fails_before_database_access(monkeypatch):
    import pytest
    from scripts import apply_v4_phase0_schema as runner

    calls = []
    monkeypatch.setattr(runner.psycopg, "connect", lambda *args, **kwargs: calls.append((args, kwargs)))
    with pytest.raises(RuntimeError, match="NOT_AUTHORIZED_TO_EXECUTE"):
        runner.apply()
    assert calls == []
    assert len(runner.VERSIONS) > 50

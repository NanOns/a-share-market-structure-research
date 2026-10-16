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
    assert "where new.publication_id=%s and revision=%s" not in ingest

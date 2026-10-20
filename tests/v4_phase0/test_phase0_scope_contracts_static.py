from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "src/workbench_db/migrations/v4_postgres"


def read(path):
    return path.read_text(encoding="utf-8")


def test_lifecycle_schema_contract_is_distinct_from_lifecycle_fact_rows():
    history = read(MIGRATIONS / "010_security_lifecycle_history_r5.sql")
    facts = read(MIGRATIONS / "011_security_membership_interval_r6_2.sql")
    lifecycle_facts = read(MIGRATIONS / "012_provider_lifecycle_fact_r6_2.sql")

    for column in (
        "effective_from", "effective_to", "provider_available_at", "observed_at",
        "ingested_at", "system_available_at", "source_revision_id", "supersedes_revision_id",
    ):
        assert column in history
    assert "PRIMARY KEY (lifecycle_fact_key, source_revision_id)" in history
    assert "ix_security_lifecycle_history_effective" in history
    assert "ix_security_lifecycle_history_cutoff" in history
    assert "system_available_at = GREATEST(observed_at, ingested_at)" in history
    assert "v4_security_lifecycle_history_append_only" in history
    assert "security_membership_interval_history" in facts
    assert "provider_lifecycle_fact_history" in lifecycle_facts
    # These are DDL contract assertions; no assertion here claims production rows exist.


def test_publication_identity_contract_does_not_require_an_accepted_head_row():
    identity = read(MIGRATIONS / "004_publication_head_revision_identity.sql")
    namespace = read(MIGRATIONS / "007_state_and_namespace_publication_identity.sql")
    candidate = read(ROOT / "src/workbench_db/v4_publication_candidate.py")
    reader = read(ROOT / "src/workbench_db/v4_publication_reader.py")

    assert "V4_PUBLICATION_HEAD_TARGET_INVALID" in identity
    assert "p.status <> 'ACCEPTED'" in identity
    assert "p.trade_date <> NEW.trade_date" in identity
    assert "p.model_namespace_id <> NEW.model_namespace_id" in identity
    assert "uq_publication_id_namespace" in namespace
    assert "fk_state_head_publication_identity" in namespace
    assert "model_namespace_id" in candidate and "revision_no" in candidate
    assert "INITIAL_PUBLICATION_IDENTITY_INVALID" in candidate
    assert "_validate_publication" in reader
    # Candidate/reader identity contracts are code evidence; a published Head is runtime evidence.

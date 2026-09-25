-- V4-01 R5: formal append-only lifecycle identity/history facts.
CREATE TABLE IF NOT EXISTS v4.security_lifecycle_history (
    lifecycle_fact_key text NOT NULL,
    security_id text NOT NULL,
    symbol text NOT NULL,
    security_type text NOT NULL,
    board text,
    list_date date,
    delist_date date,
    effective_from date NOT NULL,
    effective_to date,
    status text NOT NULL,
    quality text NOT NULL,
    source_contract_id text NOT NULL,
    provider_available_at timestamptz,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    source_identity text NOT NULL,
    PRIMARY KEY (lifecycle_fact_key, source_revision_id),
    CHECK (length(lifecycle_fact_key) > 0 AND length(security_id) > 0 AND length(symbol) > 0),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CHECK (delist_date IS NULL OR list_date IS NULL OR delist_date >= list_date),
    CHECK (system_available_at = GREATEST(observed_at, ingested_at)),
    CHECK (provider_available_at IS NULL OR provider_available_at <= observed_at)
);

CREATE INDEX IF NOT EXISTS ix_security_lifecycle_history_effective
    ON v4.security_lifecycle_history (security_id, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS ix_security_lifecycle_history_cutoff
    ON v4.security_lifecycle_history (lifecycle_fact_key, system_available_at DESC);
CREATE INDEX IF NOT EXISTS ix_security_lifecycle_history_symbol
    ON v4.security_lifecycle_history (symbol, effective_from, effective_to);

CREATE OR REPLACE FUNCTION v4.validate_security_lifecycle_history_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE src v4.source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO src FROM v4.source_revisions WHERE source_revision_id = NEW.source_revision_id;
    IF NOT FOUND
       OR src.logical_fact_id <> NEW.lifecycle_fact_key
       OR src.supersedes_revision_id IS DISTINCT FROM NEW.supersedes_revision_id
       OR src.provider_available_at IS DISTINCT FROM NEW.provider_available_at
       OR src.observed_at <> NEW.observed_at
       OR src.ingested_at <> NEW.ingested_at
       OR src.system_available_at <> NEW.system_available_at
       OR src.effective_from IS DISTINCT FROM NEW.effective_from
       OR src.effective_to IS DISTINCT FROM NEW.effective_to THEN
        RAISE EXCEPTION 'V4_LIFECYCLE_HISTORY_SOURCE_REVISION_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_security_lifecycle_history_revision_guard ON v4.security_lifecycle_history;
CREATE TRIGGER v4_security_lifecycle_history_revision_guard
    BEFORE INSERT ON v4.security_lifecycle_history
    FOR EACH ROW EXECUTE FUNCTION v4.validate_security_lifecycle_history_revision();

DROP TRIGGER IF EXISTS v4_security_lifecycle_history_append_only ON v4.security_lifecycle_history;
CREATE TRIGGER v4_security_lifecycle_history_append_only
    BEFORE UPDATE OR DELETE ON v4.security_lifecycle_history
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

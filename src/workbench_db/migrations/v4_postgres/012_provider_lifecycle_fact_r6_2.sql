-- V4-01 R6.2: immutable provider-reported lifecycle facts, separate from normalized membership.
CREATE TABLE IF NOT EXISTS v4.provider_lifecycle_fact_history (
    provider_fact_key text NOT NULL,
    provider text NOT NULL,
    source_security_key text NOT NULL,
    provider_ipo_date date,
    provider_out_date date,
    provider_status text,
    source_observation_date date,
    source_observation_time_quality text NOT NULL,
    source_contract_id text NOT NULL,
    raw_provider_contract_id text NOT NULL,
    raw_provider_payload jsonb NOT NULL,
    evidence jsonb NOT NULL,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    source_identity text NOT NULL,
    PRIMARY KEY (provider_fact_key, source_revision_id),
    CHECK (length(provider_fact_key) > 0 AND length(provider) > 0 AND length(source_security_key) > 0),
    CHECK (system_available_at = GREATEST(observed_at, ingested_at))
);

CREATE INDEX IF NOT EXISTS ix_provider_lifecycle_fact_key
    ON v4.provider_lifecycle_fact_history (provider, source_security_key, observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_provider_lifecycle_fact_out_date
    ON v4.provider_lifecycle_fact_history (provider_out_date, source_security_key);

CREATE OR REPLACE FUNCTION v4.validate_provider_lifecycle_fact_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE src v4.source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO src FROM v4.source_revisions WHERE source_revision_id = NEW.source_revision_id;
    IF NOT FOUND
       OR src.logical_fact_id <> NEW.provider_fact_key
       OR src.supersedes_revision_id IS DISTINCT FROM NEW.supersedes_revision_id
       OR src.provider_available_at IS NOT NULL
       OR src.observed_at <> NEW.observed_at
       OR src.ingested_at <> NEW.ingested_at
       OR src.system_available_at <> NEW.system_available_at THEN
        RAISE EXCEPTION 'V4_PROVIDER_LIFECYCLE_FACT_SOURCE_REVISION_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_provider_lifecycle_fact_revision_guard ON v4.provider_lifecycle_fact_history;
CREATE TRIGGER v4_provider_lifecycle_fact_revision_guard
    BEFORE INSERT ON v4.provider_lifecycle_fact_history
    FOR EACH ROW EXECUTE FUNCTION v4.validate_provider_lifecycle_fact_revision();

DROP TRIGGER IF EXISTS v4_provider_lifecycle_fact_append_only ON v4.provider_lifecycle_fact_history;
CREATE TRIGGER v4_provider_lifecycle_fact_append_only
    BEFORE UPDATE OR DELETE ON v4.provider_lifecycle_fact_history
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

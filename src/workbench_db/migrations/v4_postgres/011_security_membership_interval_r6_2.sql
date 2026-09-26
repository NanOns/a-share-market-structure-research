-- V4-01 R6.2: append-only, roster-normalized membership interval revisions.
CREATE TABLE IF NOT EXISTS v4.security_membership_interval_history (
    membership_fact_key text NOT NULL,
    security_id text NOT NULL,
    source_security_key text NOT NULL,
    normalized_effective_from date NOT NULL,
    normalized_effective_to date,
    from_boundary_basis text NOT NULL,
    to_boundary_basis text NOT NULL,
    provider_ipo_date date,
    provider_out_date date,
    first_observed_roster_date date,
    last_observed_roster_date date,
    boundary_quality text NOT NULL,
    source_contract_id text NOT NULL,
    evidence jsonb NOT NULL,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    source_identity text NOT NULL,
    PRIMARY KEY (membership_fact_key, source_revision_id),
    CHECK (length(membership_fact_key) > 0 AND length(security_id) > 0 AND length(source_security_key) > 0),
    CHECK (normalized_effective_to IS NULL OR normalized_effective_to >= normalized_effective_from),
    CHECK (system_available_at = GREATEST(observed_at, ingested_at))
);

CREATE INDEX IF NOT EXISTS ix_membership_interval_effective
    ON v4.security_membership_interval_history (security_id, normalized_effective_from, normalized_effective_to);
CREATE INDEX IF NOT EXISTS ix_membership_interval_cutoff
    ON v4.security_membership_interval_history (membership_fact_key, system_available_at DESC);
CREATE INDEX IF NOT EXISTS ix_membership_interval_source_key
    ON v4.security_membership_interval_history (source_security_key, normalized_effective_from, normalized_effective_to);

CREATE OR REPLACE FUNCTION v4.validate_security_membership_interval_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE src v4.source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO src FROM v4.source_revisions WHERE source_revision_id = NEW.source_revision_id;
    IF NOT FOUND
       OR src.logical_fact_id <> NEW.membership_fact_key
       OR src.supersedes_revision_id IS DISTINCT FROM NEW.supersedes_revision_id
       OR src.provider_available_at IS NOT NULL
       OR src.observed_at <> NEW.observed_at
       OR src.ingested_at <> NEW.ingested_at
       OR src.system_available_at <> NEW.system_available_at
       OR src.effective_from IS DISTINCT FROM NEW.normalized_effective_from
       OR src.effective_to IS DISTINCT FROM NEW.normalized_effective_to THEN
        RAISE EXCEPTION 'V4_MEMBERSHIP_INTERVAL_SOURCE_REVISION_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_security_membership_interval_revision_guard ON v4.security_membership_interval_history;
CREATE TRIGGER v4_security_membership_interval_revision_guard
    BEFORE INSERT ON v4.security_membership_interval_history
    FOR EACH ROW EXECUTE FUNCTION v4.validate_security_membership_interval_revision();

DROP TRIGGER IF EXISTS v4_security_membership_interval_append_only ON v4.security_membership_interval_history;
CREATE TRIGGER v4_security_membership_interval_append_only
    BEFORE UPDATE OR DELETE ON v4.security_membership_interval_history
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

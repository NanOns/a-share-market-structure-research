CREATE SCHEMA IF NOT EXISTS v4;
CREATE SCHEMA IF NOT EXISTS v4_meta;

CREATE TABLE IF NOT EXISTS v4_meta.schema_migrations (
    version text PRIMARY KEY,
    checksum_sha256 char(64) NOT NULL,
    applied_at timestamptz NOT NULL,
    contract_id text NOT NULL
);

CREATE TABLE IF NOT EXISTS v4.source_packages (
    package_id text PRIMARY KEY,
    contract_version text NOT NULL,
    package_sha256 char(64) NOT NULL,
    source_page_url text NOT NULL,
    page_observed_at timestamptz,
    declared_update_date date,
    target_trade_date date NOT NULL,
    parser_version text NOT NULL,
    manifest jsonb NOT NULL,
    accepted_scope text NOT NULL CHECK (accepted_scope IN ('ACCEPTED_SOURCE_PACKAGE','DIAGNOSTIC_ONLY','REJECTED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (package_sha256, parser_version)
);

CREATE TABLE IF NOT EXISTS v4.source_revisions (
    source_revision_id text PRIMARY KEY,
    logical_fact_id text NOT NULL,
    revision_no integer NOT NULL CHECK (revision_no > 0),
    payload jsonb NOT NULL,
    digest char(64) NOT NULL,
    effective_from date,
    effective_to date,
    provider_available_at timestamptz,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    tombstone boolean NOT NULL DEFAULT false,
    UNIQUE (logical_fact_id, revision_no),
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from),
    CHECK (system_available_at >= observed_at AND system_available_at >= ingested_at)
);

CREATE TABLE IF NOT EXISTS v4.security_lifecycle_facts (
    security_id text NOT NULL,
    security_type text NOT NULL,
    board text,
    listed_from date,
    listed_to date,
    st_state text,
    trade_status text,
    effective_from date NOT NULL,
    effective_to date,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    source_identity text NOT NULL,
    quality text NOT NULL,
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    PRIMARY KEY (security_id, effective_from, source_revision_id)
);

CREATE TABLE IF NOT EXISTS v4.universe_snapshots (
    universe_snapshot_id text PRIMARY KEY,
    contract_id text NOT NULL,
    contract_version text NOT NULL,
    trade_date date NOT NULL,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    universe_basis text NOT NULL CHECK (universe_basis IN ('PIT_OBSERVED','RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED','DIAGNOSTIC_NON_PIT')),
    logical_digest char(64) NOT NULL,
    member_count integer NOT NULL CHECK (member_count >= 0),
    UNIQUE (trade_date, contract_id, logical_digest)
);

CREATE TABLE IF NOT EXISTS v4.universe_members (
    universe_snapshot_id text NOT NULL REFERENCES v4.universe_snapshots(universe_snapshot_id),
    security_id text NOT NULL,
    security_type text NOT NULL,
    source_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    quality text NOT NULL,
    PRIMARY KEY (universe_snapshot_id, security_id)
);

CREATE TABLE IF NOT EXISTS v4.model_namespaces (
    namespace_id text PRIMARY KEY,
    model_contract_id text NOT NULL,
    execution_mode text NOT NULL CHECK (execution_mode IN ('PRODUCTION','SHADOW','REPLAY')),
    namespace text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (model_contract_id, execution_mode, namespace)
);

CREATE TABLE IF NOT EXISTS v4.publications (
    publication_id text NOT NULL,
    trade_date date NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    status text NOT NULL CHECK (status IN ('CANDIDATE','ACCEPTED','RETRACTED','REJECTED')),
    model_namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
    core_revision integer NOT NULL CHECK (core_revision > 0),
    source_manifest_sha256 char(64) NOT NULL,
    computation_identity_sha256 char(64) NOT NULL,
    prior_session_state_head text,
    same_day_revision_parent text,
    accepted_at timestamptz,
    PRIMARY KEY (publication_id, revision),
    UNIQUE (trade_date, model_namespace_id, revision),
    CHECK (status <> 'ACCEPTED' OR accepted_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS v4.publication_heads (
    trade_date date NOT NULL,
    model_namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
    publication_id text NOT NULL,
    revision integer NOT NULL,
    PRIMARY KEY (trade_date, model_namespace_id),
    FOREIGN KEY (publication_id, revision) REFERENCES v4.publications(publication_id, revision)
);

CREATE TABLE IF NOT EXISTS v4.publication_consumed_sources (
    publication_id text NOT NULL,
    revision integer NOT NULL,
    source_key text NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    digest char(64) NOT NULL,
    PRIMARY KEY (publication_id, revision, source_key),
    FOREIGN KEY (publication_id, revision) REFERENCES v4.publications(publication_id, revision)
);

CREATE TABLE IF NOT EXISTS v4.publication_revision_events (
    event_id text PRIMARY KEY,
    publication_id text NOT NULL,
    revision integer NOT NULL,
    prior_revision integer,
    event_type text NOT NULL CHECK (event_type IN ('CREATED','ACCEPTED','RETRACTED','REJECTED')),
    reason text,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (publication_id, revision) REFERENCES v4.publications(publication_id, revision)
);

CREATE TABLE IF NOT EXISTS v4.namespace_migrations (
    migration_id text PRIMARY KEY,
    source_namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
    target_namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
    frozen_source_head text NOT NULL,
    manifest_sha256 char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source_namespace_id <> target_namespace_id)
);

CREATE TABLE IF NOT EXISTS v4.event_observations (
    logical_event_id text NOT NULL,
    observation_revision integer NOT NULL CHECK (observation_revision > 0),
    publication_id text NOT NULL,
    publication_revision integer NOT NULL,
    status text NOT NULL CHECK (status IN ('ACTIVE','RETRACTED')),
    reason text,
    payload jsonb NOT NULL,
    PRIMARY KEY (logical_event_id, observation_revision),
    FOREIGN KEY (publication_id, publication_revision) REFERENCES v4.publications(publication_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_source_revisions_cutoff ON v4.source_revisions (logical_fact_id, system_available_at DESC);
CREATE INDEX IF NOT EXISTS ix_lifecycle_effective ON v4.security_lifecycle_facts (security_id, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS ix_publication_consumed_source_revision ON v4.publication_consumed_sources (source_revision_id);
CREATE INDEX IF NOT EXISTS ix_publication_revision_events_identity ON v4.publication_revision_events (publication_id, revision, recorded_at);
CREATE INDEX IF NOT EXISTS ix_event_observations_publication ON v4.event_observations (publication_id, publication_revision);

CREATE OR REPLACE FUNCTION v4.reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_APPEND_ONLY_TABLE:%', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
END $$;


DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['source_revisions','security_lifecycle_facts','universe_snapshots','universe_members','publications','publication_consumed_sources','publication_revision_events','event_observations'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS v4_append_only_guard ON v4.%I', t);
        EXECUTE format('CREATE TRIGGER v4_append_only_guard BEFORE UPDATE OR DELETE ON v4.%I FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation()', t);
    END LOOP;
END $$;

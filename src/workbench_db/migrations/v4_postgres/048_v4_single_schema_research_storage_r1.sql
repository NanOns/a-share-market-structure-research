-- V4 single-schema research storage. All release identities are row keys in v4.
CREATE TABLE IF NOT EXISTS v4.research_releases (
    release_id text PRIMARY KEY,
    storage_kind text NOT NULL CHECK (storage_kind IN ('snapshot','series','journal')),
    contract_id text NOT NULL,
    t0 date NOT NULL,
    source_schema text,
    legacy_digest text,
    original_descriptor bytea,
    original_descriptor_sha256 char(64),
    canonical_manifest jsonb NOT NULL,
    sealed boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((original_descriptor IS NULL) = (original_descriptor_sha256 IS NULL))
);

CREATE TABLE IF NOT EXISTS v4.research_objects (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    domain text NOT NULL,
    id text NOT NULL,
    name text,
    symbol text,
    state text,
    payload text,
    PRIMARY KEY (release_id,domain,id)
);

CREATE TABLE IF NOT EXISTS v4.research_aliases (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    alias text NOT NULL,
    id text NOT NULL,
    PRIMARY KEY (release_id,alias,id)
);

CREATE TABLE IF NOT EXISTS v4.research_members (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    sector text NOT NULL,
    security text NOT NULL,
    PRIMARY KEY (release_id,sector,security)
);

CREATE TABLE IF NOT EXISTS v4.research_metadata (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    key text NOT NULL,
    value text,
    PRIMARY KEY (release_id,key)
);

CREATE TABLE IF NOT EXISTS v4.research_series_versions (
    release_id text PRIMARY KEY REFERENCES v4.research_releases(release_id),
    series_contract_id text NOT NULL,
    source_digest text NOT NULL,
    bar_count bigint NOT NULL CHECK (bar_count >= 0),
    symbol_count bigint NOT NULL CHECK (symbol_count >= 0),
    price_basis text NOT NULL DEFAULT 'RAW_OR_CONTRACT_BOUND'
);

CREATE TABLE IF NOT EXISTS v4.research_series_bars (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    security text NOT NULL,
    day date NOT NULL,
    payload text NOT NULL,
    PRIMARY KEY (release_id,security,day)
);

CREATE TABLE IF NOT EXISTS v4.research_journal_versions (
    release_id text PRIMARY KEY REFERENCES v4.research_releases(release_id),
    journal_contract text NOT NULL,
    head jsonb NOT NULL,
    registry_schema text,
    registry_key text
);

CREATE TABLE IF NOT EXISTS v4.research_journal_days (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    day date NOT NULL,
    source_digest text NOT NULL,
    payload text NOT NULL,
    PRIMARY KEY (release_id,day)
);

CREATE TABLE IF NOT EXISTS v4.research_journal_inputs (
    release_id text NOT NULL REFERENCES v4.research_releases(release_id),
    day date NOT NULL,
    payload text NOT NULL,
    PRIMARY KEY (release_id,day)
);

CREATE TABLE IF NOT EXISTS v4.legacy_schema_migration_map (
    source_schema text NOT NULL,
    source_table text NOT NULL,
    legacy_identity text NOT NULL,
    canonical_relation text NOT NULL,
    canonical_version text NOT NULL REFERENCES v4.research_releases(release_id),
    original_sha256 char(64) NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (source_schema,source_table,legacy_identity)
);

CREATE INDEX IF NOT EXISTS research_objects_release_domain_symbol_idx
    ON v4.research_objects(release_id,domain,symbol,id);
CREATE INDEX IF NOT EXISTS research_journal_days_release_day_idx
    ON v4.research_journal_days(release_id,day);

-- Immutable dated history and exact source-version map in the fixed v4 schema.
CREATE TABLE IF NOT EXISTS v4.history_versions_r1 (
    version text PRIMARY KEY,
    head_token text NOT NULL,
    t0 date NOT NULL,
    source_digest text NOT NULL,
    logical_digest text NOT NULL,
    symbol_count bigint NOT NULL,
    bar_count bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS v4.history_bars_r1 (
    version text NOT NULL CONSTRAINT history_bars_r1_version_fkey
        REFERENCES v4.history_versions_r1(version) DEFERRABLE INITIALLY DEFERRED,
    security text NOT NULL,
    payload jsonb NOT NULL,
    PRIMARY KEY(version,security)
);
CREATE TABLE IF NOT EXISTS v4.history_migration_map_r1 (
    source_schema text NOT NULL,
    source_version text NOT NULL,
    canonical_version text NOT NULL REFERENCES v4.history_versions_r1(version),
    T0 date NOT NULL,
    head_token text NOT NULL,
    source_digest text NOT NULL,
    logical_digest text NOT NULL,
    symbol_count bigint NOT NULL,
    bar_count bigint NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(source_schema,source_version),
    CHECK (source_version=canonical_version)
);

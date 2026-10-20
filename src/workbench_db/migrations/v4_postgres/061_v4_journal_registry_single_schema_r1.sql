CREATE TABLE IF NOT EXISTS v4.journal_heads (
    key text PRIMARY KEY,
    contract text NOT NULL,
    descriptor jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS v4.journal_registry_migration_map_r1 (
    source_schema text NOT NULL,
    registry_key text NOT NULL,
    journal_contract text NOT NULL,
    legacy_release_id text NOT NULL,
    legacy_descriptor_sha256 char(64) NOT NULL,
    canonical_release_id text NOT NULL,
    canonical_descriptor_sha256 char(64) NOT NULL,
    canonical_descriptor jsonb NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(source_schema,registry_key),
    CHECK (verification->>'status' = 'VERIFIED')
);

CREATE INDEX IF NOT EXISTS journal_registry_migration_release_r1
    ON v4.journal_registry_migration_map_r1(canonical_release_id);

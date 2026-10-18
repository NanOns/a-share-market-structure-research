CREATE TABLE IF NOT EXISTS v4.jobs_legacy_rows_r1 (
    source_schema text NOT NULL,
    source_table text NOT NULL,
    source_pk jsonb NOT NULL,
    payload jsonb NOT NULL,
    row_sha256 char(64) NOT NULL CHECK (row_sha256 ~ '^[0-9a-f]{64}$'),
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (source_schema, source_table, source_pk)
);

CREATE TABLE IF NOT EXISTS v4.jobs_legacy_migration_map_r1 (
    source_schema text PRIMARY KEY,
    table_row_counts jsonb NOT NULL,
    table_sha256 jsonb NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (verification->>'status' = 'VERIFIED')
);

CREATE TABLE IF NOT EXISTS workbench.focus_technical_identity_migrations (
    source_object_id text PRIMARY KEY REFERENCES workbench.analysis_result_objects(result_object_id),
    legacy_hash char(64) NOT NULL,
    canonical_hash char(64) NOT NULL,
    canonical_logical_hash char(64) NOT NULL,
    row_count integer NOT NULL CHECK (row_count > 0),
    backup_sha256 char(64) NOT NULL,
    migration_reason text NOT NULL,
    migration_contract_id text NOT NULL CHECK (
        migration_contract_id = 'TECHNICAL_RESULT_CANONICAL_IDENTITY_V2'),
    accepted_at_utc timestamptz NOT NULL DEFAULT now(),
    CHECK (legacy_hash ~ '^[0-9a-f]{64}$'),
    CHECK (canonical_hash ~ '^[0-9a-f]{64}$'),
    CHECK (canonical_logical_hash ~ '^[0-9a-f]{64}$'),
    CHECK (backup_sha256 ~ '^[0-9a-f]{64}$')
);

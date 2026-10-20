CREATE TABLE IF NOT EXISTS v4.jobs_frozen_oracle_migration_receipts_r1(
    source_sha text PRIMARY KEY CHECK(source_sha ~ '^[0-9a-f]{64}$'),
    payload_sha text NOT NULL CHECK(payload_sha ~ '^[0-9a-f]{64}$'),
    counts jsonb NOT NULL CHECK(jsonb_typeof(counts)='object'),
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION v4.reject_jobs_frozen_oracle_migration_receipt_mutation_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'IMMUTABLE_JOB_MIGRATION_RECEIPT';
END
$$;

DROP TRIGGER IF EXISTS jobs_frozen_oracle_migration_receipts_immutable_r1
    ON v4.jobs_frozen_oracle_migration_receipts_r1;
CREATE TRIGGER jobs_frozen_oracle_migration_receipts_immutable_r1
    BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.jobs_frozen_oracle_migration_receipts_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_jobs_frozen_oracle_migration_receipt_mutation_r1();

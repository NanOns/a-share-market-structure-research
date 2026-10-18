-- The migration ledger is deployment metadata but remains under the sole V4
-- application schema so fresh installs and existing databases converge.
CREATE TABLE IF NOT EXISTS v4.schema_migrations (
    version text PRIMARY KEY,
    checksum_sha256 char(64) NOT NULL,
    applied_at timestamptz NOT NULL,
    contract_id text NOT NULL
);

DO $$
DECLARE old_count bigint;
DECLARE new_count bigint;
DECLARE mismatch_count bigint;
BEGIN
    IF to_regclass('v4_meta.schema_migrations') IS NOT NULL THEN
        INSERT INTO v4.schema_migrations(version,checksum_sha256,applied_at,contract_id)
        SELECT version,checksum_sha256,applied_at,contract_id
          FROM v4_meta.schema_migrations
        ON CONFLICT(version) DO NOTHING;

        SELECT count(*) INTO old_count FROM v4_meta.schema_migrations;
        SELECT count(*) INTO new_count FROM v4.schema_migrations;
        SELECT count(*) INTO mismatch_count
          FROM v4_meta.schema_migrations old
          LEFT JOIN v4.schema_migrations new USING(version)
         WHERE new.version IS NULL
            OR new.checksum_sha256 <> old.checksum_sha256
            OR new.contract_id <> old.contract_id;
        IF mismatch_count <> 0 OR new_count < old_count THEN
            RAISE EXCEPTION 'V4_SCHEMA_MIGRATION_LEDGER_PARITY_FAILED';
        END IF;

    END IF;
END $$;

CREATE TABLE IF NOT EXISTS v4.stage00_raw_owner_receipts (
    receipt_id text PRIMARY KEY,
    trade_date date NOT NULL,
    source_package_id text NOT NULL REFERENCES v4.source_packages(package_id),
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    receipt_sha256 char(64) NOT NULL,
    receipt jsonb NOT NULL,
    issuer_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (trade_date, source_package_id, source_revision_id),
    CHECK (receipt->>'contract_id' = 'V4_STAGE00_RAW_OWNER_RECEIPT_R1'),
    CHECK (receipt->>'receipt_id' = receipt_id),
    CHECK (receipt->>'receipt_sha256' = receipt_sha256),
    CHECK (receipt->>'issuer_id' = issuer_id),
    CHECK (receipt->>'owner' = 'V4-00E'),
    CHECK (receipt->>'scope' = 'RAW_BOOTSTRAP'),
    CHECK ((receipt->>'trade_date')::date = trade_date),
    CHECK (receipt->>'source_package_id' = source_package_id),
    CHECK (receipt->>'source_revision_id' = source_revision_id)
);
CREATE INDEX IF NOT EXISTS ix_stage00_raw_owner_receipts_package_t0
    ON v4.stage00_raw_owner_receipts (source_package_id, trade_date);
CREATE OR REPLACE FUNCTION v4.reject_stage00_raw_owner_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'STAGE00_RAW_OWNER_RECEIPT_IMMUTABLE';
END;
$$;
DROP TRIGGER IF EXISTS trg_stage00_raw_owner_receipts_immutable ON v4.stage00_raw_owner_receipts;
CREATE TRIGGER trg_stage00_raw_owner_receipts_immutable
    BEFORE UPDATE OR DELETE ON v4.stage00_raw_owner_receipts
    FOR EACH ROW EXECUTE FUNCTION v4.reject_stage00_raw_owner_receipt_mutation();
DROP TRIGGER IF EXISTS trg_stage00_raw_owner_receipts_no_truncate ON v4.stage00_raw_owner_receipts;
CREATE TRIGGER trg_stage00_raw_owner_receipts_no_truncate
    BEFORE TRUNCATE ON v4.stage00_raw_owner_receipts
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_stage00_raw_owner_receipt_mutation();

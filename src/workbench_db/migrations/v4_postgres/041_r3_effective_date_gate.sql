-- R13: from the approved effective T0 of 2026-10-16, a new publication cannot enter
-- PostgreSQL under the legacy R2 source-manifest contract. Existing rows are
-- untouched; the trigger constrains only future INSERT/UPDATE operations.
CREATE OR REPLACE FUNCTION v4.require_source_manifest_contract() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_manifest_contract_id NOT IN (
        'V4_PG_CONSUMED_SOURCE_MANIFEST_R2',
        'V4_PG_CONSUMED_SOURCE_MANIFEST_R3'
    ) THEN
        RAISE EXCEPTION 'V4_SOURCE_MANIFEST_R2_OR_R3_CONTRACT_REQUIRED';
    END IF;
    IF NEW.trade_date >= DATE '2026-10-16'
       AND NEW.source_manifest_contract_id IS DISTINCT FROM 'V4_PG_CONSUMED_SOURCE_MANIFEST_R3' THEN
        RAISE EXCEPTION 'V4_NEW_T0_REQUIRES_R3_SOURCE_MANIFEST';
    END IF;
    RETURN NEW;
END $$;

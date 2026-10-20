-- R3 makes the accepted package signature, PIT capability flags and exact
-- package-fact evidence part of the canonical publication source digest.
-- Existing R1/R2 publications retain their original serialization.
ALTER TABLE v4.publications
    DROP CONSTRAINT IF EXISTS ck_publication_source_manifest_contract;

ALTER TABLE v4.publications
    ADD CONSTRAINT ck_publication_source_manifest_contract
    CHECK (source_manifest_contract_id IS NULL
           OR source_manifest_contract_id IN (
               'V4_PG_CONSUMED_SOURCE_MANIFEST_R1',
               'V4_PG_CONSUMED_SOURCE_MANIFEST_R2',
               'V4_PG_CONSUMED_SOURCE_MANIFEST_R3'
           ));

CREATE OR REPLACE FUNCTION v4.require_source_manifest_contract() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_manifest_contract_id NOT IN (
        'V4_PG_CONSUMED_SOURCE_MANIFEST_R2',
        'V4_PG_CONSUMED_SOURCE_MANIFEST_R3'
    ) THEN
        RAISE EXCEPTION 'V4_SOURCE_MANIFEST_R2_OR_R3_CONTRACT_REQUIRED';
    END IF;
    RETURN NEW;
END $$;

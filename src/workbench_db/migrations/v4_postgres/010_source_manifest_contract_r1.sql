-- Version the source-set serialization before readers claim the stored SHA is
-- reproducible. Existing rows remain NULL (historical encoding unknown).
ALTER TABLE v4.publications
    ADD COLUMN source_manifest_contract_id text;

ALTER TABLE v4.publications
    ADD CONSTRAINT ck_publication_source_manifest_contract
    CHECK (source_manifest_contract_id IS NULL
           OR source_manifest_contract_id = 'V4_PG_CONSUMED_SOURCE_MANIFEST_R1');

CREATE OR REPLACE FUNCTION v4.require_source_manifest_contract() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_manifest_contract_id IS DISTINCT FROM 'V4_PG_CONSUMED_SOURCE_MANIFEST_R1' THEN
        RAISE EXCEPTION 'V4_SOURCE_MANIFEST_CONTRACT_REQUIRED';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_publication_source_manifest_contract_guard ON v4.publications;
CREATE TRIGGER v4_publication_source_manifest_contract_guard
    BEFORE INSERT ON v4.publications
    FOR EACH ROW EXECUTE FUNCTION v4.require_source_manifest_contract();

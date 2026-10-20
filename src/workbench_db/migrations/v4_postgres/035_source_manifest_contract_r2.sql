-- Preserve historical R1 rows, but require the accepted-package-bound R2
-- serialization for every publication created after this migration.
ALTER TABLE v4.publications
    DROP CONSTRAINT IF EXISTS ck_publication_source_manifest_contract;

ALTER TABLE v4.publications
    ADD CONSTRAINT ck_publication_source_manifest_contract
    CHECK (source_manifest_contract_id IS NULL
           OR source_manifest_contract_id IN (
               'V4_PG_CONSUMED_SOURCE_MANIFEST_R1',
               'V4_PG_CONSUMED_SOURCE_MANIFEST_R2'
           ));

CREATE OR REPLACE FUNCTION v4.require_source_manifest_contract() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_manifest_contract_id IS DISTINCT FROM 'V4_PG_CONSUMED_SOURCE_MANIFEST_R2' THEN
        RAISE EXCEPTION 'V4_SOURCE_MANIFEST_R2_CONTRACT_REQUIRED';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_publication_source_manifest_contract_guard ON v4.publications;
CREATE TRIGGER v4_publication_source_manifest_contract_guard
    BEFORE INSERT ON v4.publications
    FOR EACH ROW EXECUTE FUNCTION v4.require_source_manifest_contract();

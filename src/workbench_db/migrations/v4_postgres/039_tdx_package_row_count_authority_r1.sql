-- Freeze the target TDX artifact row denominator in the accepted package fact.
-- Existing facts are not rewritten; newly accepted TDX facts must carry an
-- exact positive row count also present in the package manifest.

ALTER TABLE v4.source_package_facts
    ADD CONSTRAINT ck_tdx_source_package_fact_record_count_r1
    CHECK (source_key <> 'tdx' OR (record_count IS NOT NULL AND record_count > 0))
    NOT VALID;

CREATE OR REPLACE FUNCTION v4.require_tdx_package_fact_record_count_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE package_manifest jsonb;
BEGIN
    IF NEW.source_key <> 'tdx' THEN
        RETURN NEW;
    END IF;
    IF NEW.record_count IS NULL OR NEW.record_count <= 0 THEN
        RAISE EXCEPTION 'V4_TDX_PACKAGE_RECORD_COUNT_REQUIRED';
    END IF;
    SELECT manifest INTO STRICT package_manifest
      FROM v4.source_packages
     WHERE package_id=NEW.package_id
       AND accepted_scope='ACCEPTED_SOURCE_PACKAGE';
    IF NOT EXISTS (
        SELECT 1
          FROM jsonb_array_elements(package_manifest->'source_fact_bindings') AS item
         WHERE item->>'source_key'=NEW.source_key
           AND item->>'logical_fact_id'=NEW.logical_fact_id
           AND item->>'fact_digest'=NEW.fact_digest
           AND CASE
                 WHEN item->>'record_count' ~ '^[0-9]+$'
                 THEN (item->>'record_count')::integer=NEW.record_count
                 ELSE false
               END
    ) THEN
        RAISE EXCEPTION 'V4_TDX_PACKAGE_RECORD_COUNT_MANIFEST_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER source_package_fact_tdx_record_count_guard_r1
    BEFORE INSERT ON v4.source_package_facts
    FOR EACH ROW EXECUTE FUNCTION v4.require_tdx_package_fact_record_count_r1();

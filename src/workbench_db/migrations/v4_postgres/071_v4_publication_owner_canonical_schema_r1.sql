-- New publication Owner bindings must name only the canonical business schema.
-- Historical physical locators remain in the migration map, not live bindings.
ALTER TABLE v4.publication_module_results
    DROP CONSTRAINT publication_module_results_owner_schema_check;

ALTER TABLE v4.publication_module_results
    ADD CONSTRAINT publication_module_results_owner_schema_check
    CHECK (owner_schema = 'v4');

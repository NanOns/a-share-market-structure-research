-- R5: bind every newly inserted canonical source revision to one immutable,
-- accepted source package. Existing revisions stay NULL and are not retroactively
-- promoted to accepted authority by this migration.
ALTER TABLE v4.source_revisions
    ADD COLUMN source_package_id text;

ALTER TABLE v4.source_revisions
    ADD CONSTRAINT fk_source_revision_package
    FOREIGN KEY (source_package_id) REFERENCES v4.source_packages(package_id);

CREATE INDEX ix_source_revision_package_id
    ON v4.source_revisions (source_package_id);

CREATE OR REPLACE FUNCTION v4.require_accepted_source_package_for_revision()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE package_scope text;
BEGIN
    IF NEW.source_package_id IS NULL OR btrim(NEW.source_package_id) = '' THEN
        RAISE EXCEPTION 'V4_SOURCE_PACKAGE_BINDING_REQUIRED';
    END IF;
    SELECT accepted_scope INTO package_scope
      FROM v4.source_packages
     WHERE package_id = NEW.source_package_id;
    IF package_scope IS DISTINCT FROM 'ACCEPTED_SOURCE_PACKAGE' THEN
        RAISE EXCEPTION 'V4_SOURCE_PACKAGE_NOT_ACCEPTED';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS source_revision_requires_accepted_package ON v4.source_revisions;
CREATE TRIGGER source_revision_requires_accepted_package
    BEFORE INSERT ON v4.source_revisions
    FOR EACH ROW EXECUTE FUNCTION v4.require_accepted_source_package_for_revision();

-- accepted_scope and package_sha256 are authority; they cannot be changed after
-- insertion. Diagnostic/rejected packages remain stored but cannot authorize a
-- source revision.
DROP TRIGGER IF EXISTS source_package_authority_immutable ON v4.source_packages;
CREATE TRIGGER source_package_authority_immutable
    BEFORE UPDATE OR DELETE ON v4.source_packages
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

DROP TRIGGER IF EXISTS source_package_authority_truncate_immutable ON v4.source_packages;
CREATE TRIGGER source_package_authority_truncate_immutable
    BEFORE TRUNCATE ON v4.source_packages
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_append_only_mutation();

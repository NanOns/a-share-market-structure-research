-- R6: bind each canonical source revision and consumed-source key to one
-- verifiable fact extracted from the exact immutable package. This is a
-- migration proposal only; it has not been run against any database.

CREATE TABLE v4.source_package_facts (
    package_id text NOT NULL REFERENCES v4.source_packages(package_id),
    source_key text NOT NULL,
    logical_fact_id text NOT NULL,
    fact_digest char(64) NOT NULL,
    source_fact_sha256 char(64) NOT NULL,
    record_locator jsonb NOT NULL,
    record_count integer CHECK (record_count IS NULL OR record_count >= 0),
    byte_count bigint NOT NULL CHECK (byte_count >= 0),
    acceptance_receipt_id text NOT NULL,
    PRIMARY KEY (package_id, source_key),
    UNIQUE (package_id, source_key, logical_fact_id, fact_digest),
    CHECK (fact_digest ~ '^[0-9a-f]{64}$'),
    CHECK (source_fact_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (btrim(acceptance_receipt_id) <> '')
);

CREATE OR REPLACE FUNCTION v4.reject_source_package_fact_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_SOURCE_PACKAGE_FACTS_APPEND_ONLY';
END $$;

CREATE TRIGGER source_package_facts_immutable
    BEFORE UPDATE OR DELETE ON v4.source_package_facts
    FOR EACH ROW EXECUTE FUNCTION v4.reject_source_package_fact_mutation();

CREATE TRIGGER source_package_facts_truncate_immutable
    BEFORE TRUNCATE ON v4.source_package_facts
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_source_package_fact_mutation();

ALTER TABLE v4.source_revisions
    ADD COLUMN source_package_source_key text,
    ADD COLUMN source_fact_digest char(64);

ALTER TABLE v4.source_revisions
    ADD CONSTRAINT fk_source_revision_exact_package_fact
    FOREIGN KEY (source_package_id, source_package_source_key, logical_fact_id, source_fact_digest)
    REFERENCES v4.source_package_facts (package_id, source_key, logical_fact_id, fact_digest);

CREATE OR REPLACE FUNCTION v4.require_exact_source_package_fact_for_revision()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE fact_row v4.source_package_facts%ROWTYPE;
BEGIN
    IF NEW.source_package_id IS NULL OR NEW.source_package_source_key IS NULL
       OR NEW.source_fact_digest IS NULL THEN
        RAISE EXCEPTION 'V4_SOURCE_PACKAGE_FACT_BINDING_REQUIRED';
    END IF;
    SELECT * INTO STRICT fact_row FROM v4.source_package_facts
     WHERE package_id=NEW.source_package_id
       AND source_key=NEW.source_package_source_key
       AND logical_fact_id=NEW.logical_fact_id
       AND fact_digest=NEW.source_fact_digest;
    IF NEW.digest IS DISTINCT FROM fact_row.fact_digest
       OR NEW.payload->>'source_fact_sha256' IS DISTINCT FROM fact_row.source_fact_sha256
       OR NEW.payload->>'source_key' IS DISTINCT FROM fact_row.source_key
       OR NEW.payload->>'producer_receipt_id' IS DISTINCT FROM fact_row.acceptance_receipt_id THEN
        RAISE EXCEPTION 'V4_SOURCE_REVISION_FACT_PROVENANCE_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS source_revision_requires_accepted_package ON v4.source_revisions;
CREATE TRIGGER source_revision_requires_accepted_package
    BEFORE INSERT ON v4.source_revisions
    FOR EACH ROW EXECUTE FUNCTION v4.require_exact_source_package_fact_for_revision();

CREATE OR REPLACE FUNCTION v4.require_package_fact_manifest_member()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE package_manifest jsonb;
BEGIN
    SELECT manifest INTO STRICT package_manifest FROM v4.source_packages
     WHERE package_id=NEW.package_id AND accepted_scope='ACCEPTED_SOURCE_PACKAGE';
    IF NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(package_manifest->'source_fact_bindings') AS item
        WHERE item->>'source_key'=NEW.source_key
          AND item->>'logical_fact_id'=NEW.logical_fact_id
          AND item->>'fact_digest'=NEW.fact_digest
          AND item->>'source_fact_sha256'=NEW.source_fact_sha256
          AND item->>'acceptance_receipt_id'=NEW.acceptance_receipt_id
    ) THEN
        RAISE EXCEPTION 'V4_SOURCE_PACKAGE_FACT_NOT_IN_SIGNED_MANIFEST';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER source_package_fact_manifest_guard
    BEFORE INSERT ON v4.source_package_facts
    FOR EACH ROW EXECUTE FUNCTION v4.require_package_fact_manifest_member();

CREATE OR REPLACE FUNCTION v4.require_complete_source_package_facts()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_count integer;
DECLARE actual_count integer;
BEGIN
    IF NEW.accepted_scope <> 'ACCEPTED_SOURCE_PACKAGE' THEN RETURN NEW; END IF;
    SELECT jsonb_array_length(NEW.manifest->'source_fact_bindings') INTO expected_count;
    SELECT count(*) INTO actual_count FROM v4.source_package_facts WHERE package_id=NEW.package_id;
    IF expected_count IS NULL OR expected_count=0 OR actual_count<>expected_count THEN
        RAISE EXCEPTION 'V4_ACCEPTED_SOURCE_PACKAGE_FACT_SET_INCOMPLETE';
    END IF;
    RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER accepted_package_requires_fact_set
    AFTER INSERT ON v4.source_packages DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION v4.require_complete_source_package_facts();

CREATE OR REPLACE FUNCTION v4.require_consumed_source_exact_package_key()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE revision_row v4.source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO STRICT revision_row FROM v4.source_revisions
     WHERE source_revision_id=NEW.source_revision_id;
    IF NEW.source_key IS DISTINCT FROM revision_row.source_package_source_key
       OR NEW.digest IS DISTINCT FROM revision_row.digest THEN
        RAISE EXCEPTION 'V4_CONSUMED_SOURCE_PACKAGE_KEY_OR_DIGEST_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER publication_consumed_source_exact_package_key
    BEFORE INSERT ON v4.publication_consumed_sources
    FOR EACH ROW EXECUTE FUNCTION v4.require_consumed_source_exact_package_key();

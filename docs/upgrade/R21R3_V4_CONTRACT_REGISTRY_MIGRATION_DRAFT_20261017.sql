-- DRAFT ONLY — R21-R3 contract storage proposal.
-- Do not execute until the live v4 schema, role grants and canonical publication
-- path are reviewed under a separate database authorization.
-- Reuses v4.publications as the publication identity; creates no second Head.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE v4.contract_versions (
    contract_id text NOT NULL,
    version text NOT NULL,
    raw_content bytea NOT NULL,
    raw_sha256 char(64) NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    content_format text NOT NULL CHECK (content_format IN ('JSON', 'XML', 'TEXT')),
    schema_version text NOT NULL,
    namespace text NOT NULL,
    status text NOT NULL CHECK (status IN ('DRAFT', 'APPROVED', 'EXPIRED')),
    approved_by text,
    approved_at timestamptz,
    source_revision text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (contract_id, version),
    UNIQUE (contract_id, version, raw_sha256),
    CHECK ((status = 'APPROVED') = (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
    CHECK (encode(digest(raw_content, 'sha256'), 'hex') = raw_sha256)
);

-- Raw bytes remain authoritative for the digest. JSONB is deliberately not
-- used as the byte-preserving contract source. XML is not parsed by this DDL.
CREATE FUNCTION v4.reject_contract_version_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_CONTRACT_VERSION_APPEND_ONLY';
END $$;
CREATE TRIGGER contract_versions_append_only
    BEFORE UPDATE OR DELETE ON v4.contract_versions
    FOR EACH ROW EXECUTE FUNCTION v4.reject_contract_version_mutation();

-- The accepted publication already selected by the canonical Head pins exact
-- approved contract versions and source digests in its own row.
ALTER TABLE v4.publications
    ADD COLUMN contract_bindings jsonb NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(contract_bindings) = 'object'),
    ADD CONSTRAINT ck_accepted_publication_has_contract_bindings
    CHECK (status <> 'ACCEPTED' OR contract_bindings <> '{}'::jsonb);

CREATE FUNCTION v4.validate_publication_contract_bindings() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE binding record;
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.status = 'ACCEPTED'
       AND NEW.contract_bindings IS DISTINCT FROM OLD.contract_bindings THEN
        RAISE EXCEPTION 'V4_ACCEPTED_PUBLICATION_CONTRACT_BINDINGS_IMMUTABLE';
    END IF;
    IF jsonb_typeof(NEW.contract_bindings) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDINGS_INVALID';
    END IF;
    FOR binding IN
        SELECT key AS contract_id, value->>'version' AS version,
               value->>'raw_sha256' AS raw_sha256
          FROM jsonb_each(NEW.contract_bindings)
    LOOP
        IF binding.version IS NULL OR binding.raw_sha256 IS NULL OR NOT EXISTS (
            SELECT 1 FROM v4.contract_versions c
             WHERE c.contract_id = binding.contract_id
               AND c.version = binding.version
               AND c.raw_sha256 = binding.raw_sha256
               AND c.namespace = (SELECT n.namespace FROM v4.model_namespaces n
                                   WHERE n.namespace_id = NEW.model_namespace_id)
               AND c.status = 'APPROVED'
               AND c.approved_at <= COALESCE(NEW.accepted_at, clock_timestamp())
        ) THEN
            RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDING_NOT_APPROVED';
        END IF;
    END LOOP;
    RETURN NEW;
END $$;
CREATE TRIGGER publication_contract_bindings_guard
    BEFORE INSERT OR UPDATE OF contract_bindings ON v4.publications
    FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_contract_bindings();

-- Least privilege template. Resolve the existing production Reader role before
-- use; this draft intentionally does not invent or grant to a role name.
-- GRANT SELECT ON v4.contract_versions TO <approved_v4_reader_role>;

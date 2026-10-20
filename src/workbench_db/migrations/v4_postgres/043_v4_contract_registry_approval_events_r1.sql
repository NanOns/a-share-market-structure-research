-- V4 R21-R5 immutable contract registry and append-only approval lifecycle.
-- Applied against the current empty canonical publication registry after catalog
-- inspection confirmed compatible v4.publications/model_namespaces columns and
-- No accepted publications or Heads are rewritten by this migration.


-- Contract bytes are immutable. Approval state is represented independently
-- by append-only events so DRAFT -> APPROVED -> REVOKED does not mutate bytes.
CREATE TABLE v4.contract_versions (
    contract_id text NOT NULL,
    version text NOT NULL,
    raw_content bytea NOT NULL,
    raw_sha256 char(64) NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    content_format text NOT NULL CHECK (content_format IN ('JSON', 'XML', 'TEXT')),
    schema_version text NOT NULL,
    namespace text NOT NULL,
    source_revision text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (contract_id, version),
    UNIQUE (contract_id, version, raw_sha256),
    -- PostgreSQL's built-in SHA-256 avoids requiring extension-install rights
    -- from the migration role. The canonical V4 migration chain already uses
    -- sha256(bytea) for content identity.
    CHECK (encode(sha256(raw_content), 'hex') = raw_sha256)
);

CREATE FUNCTION v4.reject_contract_version_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_CONTRACT_VERSION_APPEND_ONLY';
END $$;
CREATE TRIGGER contract_versions_append_only
    BEFORE UPDATE OR DELETE ON v4.contract_versions
    FOR EACH ROW EXECUTE FUNCTION v4.reject_contract_version_mutation();

CREATE TABLE v4.contract_approval_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contract_id text NOT NULL,
    version text NOT NULL,
    raw_sha256 char(64) NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    action text NOT NULL CHECK (action IN ('APPROVED', 'REVOKED')),
    authorized_by text NOT NULL CHECK (length(btrim(authorized_by)) > 0),
    authorization_ref text NOT NULL CHECK (length(btrim(authorization_ref)) > 0),
    occurred_at timestamptz NOT NULL,
    source_revision text NOT NULL,
    source_sha256 char(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (contract_id, version, raw_sha256)
        REFERENCES v4.contract_versions (contract_id, version, raw_sha256),
    CHECK (source_sha256 = raw_sha256)
);

CREATE FUNCTION v4.reject_contract_approval_event_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_CONTRACT_APPROVAL_EVENT_APPEND_ONLY';
END $$;
CREATE TRIGGER contract_approval_events_append_only
    BEFORE UPDATE OR DELETE ON v4.contract_approval_events
    FOR EACH ROW EXECUTE FUNCTION v4.reject_contract_approval_event_mutation();

-- Recording timestamps are assigned by the database on insert. Callers cannot
-- backdate an approval into a publication's historical acceptance interval.
CREATE FUNCTION v4.stamp_contract_registry_recorded_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.recorded_at := clock_timestamp();
    RETURN NEW;
END $$;
CREATE TRIGGER contract_versions_recorded_at
    BEFORE INSERT ON v4.contract_versions
    FOR EACH ROW EXECUTE FUNCTION v4.stamp_contract_registry_recorded_at();
CREATE TRIGGER contract_approval_events_recorded_at
    BEFORE INSERT ON v4.contract_approval_events
    FOR EACH ROW EXECUTE FUNCTION v4.stamp_contract_registry_recorded_at();

CREATE FUNCTION v4.reject_contract_registry_truncate() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_CONTRACT_REGISTRY_APPEND_ONLY';
END $$;
CREATE TRIGGER contract_versions_no_truncate
    BEFORE TRUNCATE ON v4.contract_versions
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_contract_registry_truncate();
CREATE TRIGGER contract_approval_events_no_truncate
    BEFORE TRUNCATE ON v4.contract_approval_events
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_contract_registry_truncate();

-- Historical accepted publications are intentionally left NULL until an
-- approved, evidence-backed binding is reconciled for each row. NOT VALID
-- avoids retrospectively rejecting those rows while enforcing future writes.
ALTER TABLE v4.publications
    ADD COLUMN contract_bindings jsonb;
ALTER TABLE v4.publications
    ADD CONSTRAINT ck_accepted_publication_has_contract_bindings
    CHECK (status <> 'ACCEPTED' OR contract_bindings IS NULL
           OR jsonb_typeof(contract_bindings) = 'object') NOT VALID;

CREATE FUNCTION v4.validate_publication_contract_bindings() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    binding record;
    should_validate boolean;
    approval record;
BEGIN
    -- Accepted publication identity is immutable. The only staged exception
    -- is adding an evidence-backed contract map to an older accepted row
    -- whose map is NULL; accepted_at, status, revision and every other current
    -- or future publication column must remain byte-for-byte equivalent.
    IF TG_OP = 'UPDATE' AND OLD.status = 'ACCEPTED' THEN
        IF (to_jsonb(NEW) - 'contract_bindings') IS DISTINCT FROM
           (to_jsonb(OLD) - 'contract_bindings') THEN
            RAISE EXCEPTION 'V4_ACCEPTED_PUBLICATION_IDENTITY_IMMUTABLE';
        END IF;
        IF OLD.contract_bindings IS NOT NULL
           AND NEW.contract_bindings IS DISTINCT FROM OLD.contract_bindings THEN
            RAISE EXCEPTION 'V4_ACCEPTED_PUBLICATION_CONTRACT_BINDINGS_IMMUTABLE';
        END IF;
    END IF;

    IF TG_OP = 'INSERT' THEN
        should_validate := true;
    ELSE
        should_validate := NEW.status IS DISTINCT FROM OLD.status
            OR NEW.contract_bindings IS DISTINCT FROM OLD.contract_bindings
            OR NEW.model_namespace_id IS DISTINCT FROM OLD.model_namespace_id
            OR NEW.accepted_at IS DISTINCT FROM OLD.accepted_at;
    END IF;
    IF NOT should_validate THEN
        RETURN NEW;
    END IF;

    -- Existing accepted rows may remain unbound during the staged backfill.
    -- A new acceptance or any attempted binding/namespace change must be exact.
    IF NEW.status <> 'ACCEPTED' THEN
        IF NEW.contract_bindings IS NOT NULL
           AND jsonb_typeof(NEW.contract_bindings) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDINGS_INVALID';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.status = 'ACCEPTED'
       AND NEW.contract_bindings IS NULL AND OLD.contract_bindings IS NULL
       AND NEW.model_namespace_id IS NOT DISTINCT FROM OLD.model_namespace_id THEN
        RETURN NEW;
    END IF;
    IF jsonb_typeof(NEW.contract_bindings) IS DISTINCT FROM 'object'
       OR NEW.contract_bindings = '{}'::jsonb THEN
        RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDINGS_REQUIRED';
    END IF;
    IF NEW.accepted_at IS NULL THEN
        RAISE EXCEPTION 'V4_PUBLICATION_ACCEPTED_AT_REQUIRED_FOR_CONTRACTS';
    END IF;

    FOR binding IN
        SELECT key AS contract_id, value->>'version' AS version,
               value->>'raw_sha256' AS raw_sha256
          FROM jsonb_each(NEW.contract_bindings)
    LOOP
        IF binding.version IS NULL OR binding.raw_sha256 !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDING_INVALID';
        END IF;
        SELECT e.action, e.authorized_by, e.authorization_ref, e.occurred_at,
               c.namespace
          INTO approval
          FROM v4.contract_versions c
          JOIN v4.model_namespaces n
            ON n.namespace_id = NEW.model_namespace_id
           AND n.namespace = c.namespace
          JOIN LATERAL (
              SELECT action, authorized_by, authorization_ref, occurred_at
                FROM v4.contract_approval_events e
               WHERE e.contract_id = c.contract_id
                 AND e.version = c.version
                 AND e.raw_sha256 = c.raw_sha256
                 AND e.source_revision = c.source_revision
                 AND e.occurred_at <= NEW.accepted_at
                 AND e.recorded_at <= NEW.accepted_at
               ORDER BY e.occurred_at DESC, e.recorded_at DESC, e.event_id DESC
               LIMIT 1
          ) e ON true
         WHERE c.contract_id = binding.contract_id
           AND c.version = binding.version
           AND c.raw_sha256 = binding.raw_sha256;
        IF NOT FOUND OR approval.action <> 'APPROVED'
           OR approval.authorized_by IS NULL OR approval.authorization_ref IS NULL THEN
            RAISE EXCEPTION 'V4_PUBLICATION_CONTRACT_BINDING_NOT_APPROVED';
        END IF;
    END LOOP;
    RETURN NEW;
END $$;
CREATE TRIGGER publication_contract_bindings_guard
    BEFORE INSERT OR UPDATE ON v4.publications
    FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_contract_bindings();

-- Stage 2, after per-row historical mapping has been independently approved:
-- validate ck_accepted_publication_has_contract_bindings and require non-NULL
-- bindings on the new acceptance path. Do not synthesize legacy mappings.
-- ALTER TABLE v4.publications VALIDATE CONSTRAINT ck_accepted_publication_has_contract_bindings;

-- Least privilege template. Resolve the existing Reader role before use.
-- GRANT SELECT ON v4.contract_versions, v4.contract_approval_events TO <approved_v4_reader_role>;

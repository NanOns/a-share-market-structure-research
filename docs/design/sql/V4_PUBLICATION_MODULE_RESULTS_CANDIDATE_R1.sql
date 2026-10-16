-- DRAFT ONLY. This file is not a migration and has NOT been executed.
-- Requires separate explicit approval before any PostgreSQL DDL/DML.
-- Purpose: minimally bind a canonical accepted publication revision to
-- immutable, independently stored domain Owner versions. It stores identity
-- metadata only; it does not copy module payloads or create another Head.

BEGIN;

CREATE TABLE v4.publication_module_results (
    publication_id text NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    module_key text NOT NULL CHECK (module_key ~ '^[a-z][a-z0-9_]{0,47}$'),
    database_identity jsonb NOT NULL CHECK (
        jsonb_typeof(database_identity)='object'
        AND database_identity ?& ARRAY['database','database_oid','host','port']
    ),
    owner_schema text NOT NULL CHECK (owner_schema ~ '^[a-z][a-z0-9_]{0,62}$'),
    owner_relation text NOT NULL CHECK (owner_relation ~ '^[a-z][a-z0-9_]{0,62}$'),
    owner_version_token text NOT NULL CHECK (length(owner_version_token) > 0),
    owner_trade_date date NOT NULL,
    owner_contract_id text NOT NULL CHECK (length(owner_contract_id) > 0),
    result_digest char(64) NOT NULL CHECK (result_digest ~ '^[0-9a-f]{64}$'),
    row_count bigint NOT NULL CHECK (row_count >= 0),
    quality_status text NOT NULL CHECK (length(quality_status) > 0),
    as_recorded boolean NOT NULL,
    pit_eligible boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publication_id, revision, module_key),
    FOREIGN KEY (publication_id, revision)
        REFERENCES v4.publications(publication_id, revision)
);

COMMENT ON TABLE v4.publication_module_results IS
    'Candidate R1: identity-only binding from V4 publication revision to an immutable domain Owner; not a Head or acceptance authority.';

CREATE OR REPLACE FUNCTION v4.validate_publication_module_result_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
BEGIN
    SELECT * INTO STRICT p
      FROM v4.publications
     WHERE publication_id=NEW.publication_id AND revision=NEW.revision;
    IF p.status IS DISTINCT FROM 'ACCEPTED' OR p.accepted_at IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_PUBLICATION_NOT_ACCEPTED';
    END IF;
    IF NEW.database_identity->>'database' IS DISTINCT FROM current_database() THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_DATABASE_MISMATCH';
    END IF;
    IF to_regclass(format('%I.%I', NEW.owner_schema, NEW.owner_relation)) IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_RELATION_MISSING';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER v4_publication_module_result_identity_guard
BEFORE INSERT ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_module_result_r1();

CREATE TRIGGER v4_publication_module_result_append_only_guard
BEFORE UPDATE OR DELETE ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

COMMIT;

-- Acceptance transaction outline (not executable with this draft):
-- 1. BEGIN ISOLATION LEVEL SERIALIZABLE; acquire a transaction advisory lock
--    for (trade_date, model_namespace_id); read and record the exact prior Head.
-- 2. Re-verify all V4-required source revisions, module owner token/T0/contract,
--    row count, digest, database system identifier, quality and clocks. Keep
--    AS_RECORDED/PIT flags unchanged. Reject UNKNOWN requiredness.
-- 3. INSERT one v4.publications row with status='ACCEPTED' and accepted_at set
--    only after all preconditions pass; this table is append-only, so do not
--    insert CANDIDATE then attempt to UPDATE it to ACCEPTED.
-- 4. INSERT the source rows into v4.publication_consumed_sources and exact
--    module identities into v4.publication_module_results.
-- 5. CAS v4.publication_heads against the exact prior (publication_id,revision).
--    For an initial Head, INSERT only if no Head exists; a conflict aborts.
-- 6. INSERT the matching v4.publication_revision_events ACCEPTED record; COMMIT.
--    On any mismatch, ROLLBACK and leave the previous Head unchanged.
-- 7. Read back the accepted Head and all module/source bindings in a new
--    read-only transaction before reporting success.

-- Rollback proposal (only for an unapplied/empty candidate object, after a
-- separately authorized rollback review; never remove accepted data):
-- BEGIN;
-- DROP TRIGGER IF EXISTS v4_publication_module_result_append_only_guard
--     ON v4.publication_module_results;
-- DROP TRIGGER IF EXISTS v4_publication_module_result_identity_guard
--     ON v4.publication_module_results;
-- DROP FUNCTION IF EXISTS v4.validate_publication_module_result_r1();
-- DROP TABLE IF EXISTS v4.publication_module_results;
-- COMMIT;

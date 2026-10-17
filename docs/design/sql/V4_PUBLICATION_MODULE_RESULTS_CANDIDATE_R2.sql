-- CANDIDATE ONLY. Not a migration; never execute against production without
-- a separate, explicit DDL/DML authorization and a verified backup/rollback.
-- Contract: V4_PG_PUBLICATION_MODULE_BINDING_R2.
-- Schema basis: migrations 001--009. publication_id alone is the immutable
-- publication identity; revision_no is a lineage sequence, not an FK key.
-- Same-day revision order is inherited from publications.revision_no and
-- same_day_revision_parent_id; this association intentionally stores neither.

BEGIN;

CREATE TABLE v4.publication_module_results (
    publication_id text NOT NULL REFERENCES v4.publications(publication_id),
    module_key text NOT NULL CHECK (module_key ~ '^[a-z][a-z0-9_]{0,47}$'),
    module_contract_id text NOT NULL
        CHECK (module_contract_id = 'V4_CURRENT_PUBLICATION_MODULE_CONTRACT_R2'),
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
    PRIMARY KEY (publication_id, module_key)
);

COMMENT ON TABLE v4.publication_module_results IS
    'R2 identity-only binding from one immutable publication_id to exact PG Owner versions; no payload or alternate Head.';

CREATE OR REPLACE FUNCTION v4.guard_publication_module_result_r2()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('v4-module-results:' || NEW.publication_id, 0));
    SELECT * INTO STRICT p FROM v4.publications WHERE publication_id=NEW.publication_id;
    IF p.status IS DISTINCT FROM 'ACCEPTED' OR p.accepted_at IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_PUBLICATION_NOT_ACCEPTED';
    END IF;
    IF NEW.owner_trade_date IS DISTINCT FROM p.trade_date THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_T0_MISMATCH';
    END IF;
    IF NEW.module_contract_id IS DISTINCT FROM 'V4_CURRENT_PUBLICATION_MODULE_CONTRACT_R2' THEN
        RAISE EXCEPTION 'V4_MODULE_CONTRACT_ID_MISMATCH';
    END IF;
    IF NEW.database_identity->>'database' IS DISTINCT FROM current_database()
       OR NEW.database_identity->>'database_oid' IS DISTINCT FROM
          (SELECT oid::text FROM pg_database WHERE datname=current_database()) THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_DATABASE_MISMATCH';
    END IF;
    IF to_regclass(format('%I.%I', NEW.owner_schema, NEW.owner_relation)) IS NULL THEN
        RAISE EXCEPTION 'V4_MODULE_OWNER_RELATION_MISSING';
    END IF;
    IF EXISTS (SELECT 1 FROM v4.publication_heads WHERE publication_id=NEW.publication_id) THEN
        RAISE EXCEPTION 'V4_PUBLICATION_MODULE_SET_SEALED';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION v4.seal_publication_module_results_before_head_r2()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
DECLARE actual_modules text[];
DECLARE required_modules constant text[] := ARRAY[
    'cohort','entity','health','radar','sector','settlement','summary'
];
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('v4-module-results:' || NEW.publication_id, 0));
    SELECT * INTO STRICT p FROM v4.publications WHERE publication_id=NEW.publication_id;
    IF p.status IS DISTINCT FROM 'ACCEPTED' OR p.accepted_at IS NULL
       OR p.trade_date IS DISTINCT FROM NEW.trade_date
       OR p.model_namespace_id IS DISTINCT FROM NEW.model_namespace_id THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_TARGET_INVALID';
    END IF;
    SELECT array_agg(module_key ORDER BY module_key COLLATE "C")
      INTO actual_modules
      FROM v4.publication_module_results
     WHERE publication_id=NEW.publication_id
       AND module_contract_id='V4_CURRENT_PUBLICATION_MODULE_CONTRACT_R2';
    IF actual_modules IS DISTINCT FROM required_modules THEN
        RAISE EXCEPTION 'V4_PUBLICATION_REQUIRED_MODULE_SET_INCOMPLETE';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER v4_publication_module_result_guard_r2
BEFORE INSERT ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.guard_publication_module_result_r2();

CREATE TRIGGER v4_publication_module_result_append_only_r2
BEFORE UPDATE OR DELETE ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

CREATE OR REPLACE FUNCTION v4.reject_publication_module_result_truncate_r2()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_APPEND_ONLY_TABLE:v4.publication_module_results';
END $$;

CREATE TRIGGER v4_publication_module_result_no_truncate_r2
BEFORE TRUNCATE ON v4.publication_module_results
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_publication_module_result_truncate_r2();

-- The lock trigger and completeness trigger serialize module INSERT against
-- Head publication. The existing v4.publication_heads guard in migration 009
-- continues to validate calendar, accepted publication and state Head.
CREATE TRIGGER v4_publication_module_set_seal_r2
BEFORE INSERT OR UPDATE OF publication_id ON v4.publication_heads
FOR EACH ROW EXECUTE FUNCTION v4.seal_publication_module_results_before_head_r2();

COMMIT;

-- Acceptance outline only; all statements below remain unexecuted.
-- 1. BEGIN ISOLATION LEVEL SERIALIZABLE. Read the exact current Head row
--    (publication_id, state_head_id, state_logical_digest) for date/namespace.
-- 2. Reverify all seven REQUIRED modules under this contract, each Owner T0,
--    database identity, version token, digest, row_count and quality. Insert
--    an ACCEPTED publication row with revision_no and lineage/parent identity.
-- 3. Insert its exact publication_consumed_sources rows. Each source_revision_id
--    and digest must match v4.source_revisions, effective T0, system/ingest and
--    provider availability must not be after accepted_at, and no tombstone is
--    accepted. Bind the exact prior state publication/head/logical digest.
-- 4. Insert exactly one publication_module_results row for each of the seven
--    required module keys. The shared advisory lock and Head trigger seal the
--    set: later INSERT fails after Head visibility; concurrent inserts serialize.
-- 5. CAS the date/namespace Head using publication_id plus the exact old state
--    head and logical digest. For no old Head, INSERT only if absent. The
--    existing 008/009 Head trigger validates the new state_head identity.
-- 6. Insert publication_revision_events using publication_id and
--    prior_publication_id (the final schema has no event revision column).
--    COMMIT; then read back Head, sources, module identities and payloads in a
--    fresh read-only transaction before reporting acceptance.
--
-- Rollback proposal is only for an unapplied/empty candidate relation after a
-- separate reviewed operation. Never delete accepted rows or Head history.
-- BEGIN;
-- DROP TRIGGER IF EXISTS v4_publication_module_set_seal_r2 ON v4.publication_heads;
-- DROP TRIGGER IF EXISTS v4_publication_module_result_no_truncate_r2 ON v4.publication_module_results;
-- DROP TRIGGER IF EXISTS v4_publication_module_result_append_only_r2 ON v4.publication_module_results;
-- DROP TRIGGER IF EXISTS v4_publication_module_result_guard_r2 ON v4.publication_module_results;
-- DROP FUNCTION IF EXISTS v4.reject_publication_module_result_truncate_r2();
-- DROP FUNCTION IF EXISTS v4.seal_publication_module_results_before_head_r2();
-- DROP FUNCTION IF EXISTS v4.guard_publication_module_result_r2();
-- DROP TABLE IF EXISTS v4.publication_module_results;
-- COMMIT;

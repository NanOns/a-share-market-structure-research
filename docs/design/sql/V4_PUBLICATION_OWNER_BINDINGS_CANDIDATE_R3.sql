-- CANDIDATE ONLY. Not a migration; never execute against production without
-- separate, explicit DDL/DML authorization and a verified backup/rollback.
-- Contract: V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R3.
-- Final schema basis: migrations 001--010, especially 003--009 for the
-- publication_id-only identity and 010 for the source-manifest contract.
-- Same-day lineage remains on publications.revision_no and
-- same_day_revision_parent_id; neither is copied into this binding table.
-- The rows below bind real Owner families, not API endpoints. They are
-- capability evidence and are not fabricated global daily prerequisites.

BEGIN;

CREATE TABLE v4.publication_module_results (
    publication_id text NOT NULL REFERENCES v4.publications(publication_id),
    module_key text NOT NULL CHECK (module_key IN ('research_priority','operational_risk','sector_lifecycle')),
    module_contract_id text NOT NULL
        CHECK (module_contract_id = 'V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R3'),
    database_identity jsonb NOT NULL CHECK (
        jsonb_typeof(database_identity)='object'
        AND database_identity ?& ARRAY['database','database_oid','host','port']
    ),
    owner_schema text NOT NULL CHECK (owner_schema ~ '^v4_[a-f0-9]{56}$'),
    owner_relation text NOT NULL,
    owner_version_token text NOT NULL CHECK (length(owner_version_token) > 0),
    owner_trade_date date NOT NULL,
    owner_contract_id text NOT NULL,
    result_digest char(64) NOT NULL CHECK (result_digest ~ '^[0-9a-f]{64}$'),
    row_count bigint NOT NULL CHECK (row_count >= 0),
    quality_status text NOT NULL CHECK (length(quality_status) > 0),
    as_recorded boolean NOT NULL,
    pit_eligible boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (publication_id, module_key),
    CHECK (
      (module_key='research_priority' AND owner_relation='owner_payloads' AND owner_contract_id='V4_RESEARCH_PRIORITY_PG_OWNER_R1')
      OR (module_key='operational_risk' AND owner_relation='owner_payloads' AND owner_contract_id='V4_OPERATIONAL_RISK_PG_OWNER_R1')
      OR (module_key='sector_lifecycle' AND owner_relation='owner_rows' AND owner_contract_id='V4_SECTOR_LIFECYCLE_PG_OWNER_R1')
    )
);

COMMENT ON TABLE v4.publication_module_results IS
    'R3 identity-only binding from publication_id to one of the existing immutable V4 PG Owner families; page projections may share these Owners.';

CREATE OR REPLACE FUNCTION v4.guard_publication_module_result_r3()
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
    IF NEW.module_contract_id IS DISTINCT FROM 'V4_CURRENT_PUBLICATION_OWNER_PROJECTION_CONTRACT_R3' THEN
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

CREATE OR REPLACE FUNCTION v4.serialize_publication_module_head_r3()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('v4-module-results:' || NEW.publication_id, 0));
    RETURN NEW;
END $$;

CREATE TRIGGER v4_publication_module_result_guard_r3
BEFORE INSERT ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.guard_publication_module_result_r3();

CREATE TRIGGER v4_publication_module_result_append_only_r3
BEFORE UPDATE OR DELETE ON v4.publication_module_results
FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

CREATE OR REPLACE FUNCTION v4.reject_publication_module_result_truncate_r3()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_APPEND_ONLY_TABLE:v4.publication_module_results';
END $$;

CREATE TRIGGER v4_publication_module_result_no_truncate_r3
BEFORE TRUNCATE ON v4.publication_module_results
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_publication_module_result_truncate_r3();

CREATE TRIGGER v4_publication_module_head_serialization_r3
BEFORE INSERT OR UPDATE OF publication_id ON v4.publication_heads
FOR EACH ROW EXECUTE FUNCTION v4.serialize_publication_module_head_r3();

COMMIT;

-- No exact Owner completeness is asserted here: the audit did not establish
-- which domain results are global required prerequisites for daily publication. Page projection code
-- reports absent/unsupported fields as PENDING/DEGRADED. Producer-contract
-- evidence must define global requiredness before an accepted Head is allowed.
-- This candidate SQL has not been compiled or executed against PostgreSQL.

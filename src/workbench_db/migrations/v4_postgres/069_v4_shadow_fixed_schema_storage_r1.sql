-- Shadow readback exports are versioned rows in the sole V4 business schema.
-- No per-export schema or alias is created by this migration.
SET search_path TO v4, pg_catalog;

CREATE TABLE v4.shadow_readback_identity_r1 (
    logical_digest text PRIMARY KEY CHECK (logical_digest ~ '^[0-9a-f]{64}$'),
    contract_id text NOT NULL CHECK (contract_id = 'V4_PG_SHADOW_READBACK_R3'),
    content_digest text NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    database_identity jsonb NOT NULL CHECK (jsonb_typeof(database_identity) = 'object'),
    environment text NOT NULL CHECK (environment IN ('REAL', 'ACTIVATION_SIMULATION')),
    evidence_origin text NOT NULL CHECK (evidence_origin IN ('PIT_OBSERVED', 'ACTIVATION_SIMULATION')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((environment = 'REAL' AND evidence_origin = 'PIT_OBSERVED') OR
           (environment = 'ACTIVATION_SIMULATION' AND evidence_origin = 'ACTIVATION_SIMULATION'))
);

CREATE TABLE v4.shadow_readback_facts_r1 (
    logical_digest text NOT NULL REFERENCES v4.shadow_readback_identity_r1(logical_digest),
    kind text NOT NULL CHECK (kind <> ''),
    id text NOT NULL CHECK (id <> ''),
    namespace text NOT NULL CHECK (namespace = 'SHADOW_V4'),
    execution_mode text NOT NULL CHECK (execution_mode = 'SHADOW'),
    evidence_origin text NOT NULL CHECK (evidence_origin IN ('PIT_OBSERVED', 'ACTIVATION_SIMULATION')),
    payload text NOT NULL CHECK (jsonb_typeof(payload::jsonb) = 'object'),
    digest text NOT NULL CHECK (digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (logical_digest, kind, id),
    CHECK (payload::jsonb ->> 'namespace' = namespace),
    CHECK (payload::jsonb ->> 'execution_mode' = execution_mode),
    CHECK (payload::jsonb ->> 'evidence_origin' = evidence_origin)
);

CREATE INDEX shadow_readback_facts_r1_kind_id_idx
    ON v4.shadow_readback_facts_r1 (kind, id, logical_digest);

CREATE FUNCTION v4.reject_shadow_readback_mutation_r1() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE', 'TRUNCATE') THEN
        RAISE EXCEPTION 'IMMUTABLE_SHADOW_READBACK';
    END IF;
    RETURN NULL;
END
$$;

CREATE TRIGGER immutable_shadow_readback_identity_r1
    BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.shadow_readback_identity_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_shadow_readback_mutation_r1();
CREATE TRIGGER immutable_shadow_readback_facts_r1
    BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.shadow_readback_facts_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_shadow_readback_mutation_r1();

REVOKE ALL ON v4.shadow_readback_identity_r1, v4.shadow_readback_facts_r1 FROM PUBLIC;

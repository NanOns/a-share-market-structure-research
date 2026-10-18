-- R7 Forward facts use one fixed, versioned relation in the V4 business schema.
CREATE TABLE IF NOT EXISTS v4.forward_r7_facts_r1 (
    origin_namespace text NOT NULL DEFAULT 'R7_ACTIVE' CHECK (origin_namespace = 'R7_ACTIVE'),
    owner_id text,
    run_id text,
    t0 date,
    kind text NOT NULL,
    fact_key text NOT NULL,
    payload text NOT NULL,
    payload_sha256 text NOT NULL,
    source_sha256 text,
    ordinal bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    PRIMARY KEY (kind, fact_key)
);

CREATE TABLE IF NOT EXISTS v4.forward_r7_migration_r1 (
    source_schema text PRIMARY KEY,
    source_table text NOT NULL CHECK (source_table = 'forward_facts'),
    origin_namespace text NOT NULL CHECK (origin_namespace = 'R7_ACTIVE'),
    row_count bigint NOT NULL CHECK (row_count >= 0),
    source_digest char(64) NOT NULL,
    target_digest char(64) NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (source_digest = target_digest)
);

CREATE OR REPLACE FUNCTION v4.reject_forward_r7_fact_mutation_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'FORWARD_R7_FACTS_APPEND_ONLY';
END $$;

DROP TRIGGER IF EXISTS forward_r7_immutable_r1 ON v4.forward_r7_facts_r1;
CREATE TRIGGER forward_r7_immutable_r1
BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.forward_r7_facts_r1
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_forward_r7_fact_mutation_r1();

-- Fixed V4 Forward relation. Workspace/module ownership is a row key, never a
-- physical Schema locator. Legacy source provenance is recorded separately.
CREATE TABLE IF NOT EXISTS v4.forward_facts (
    workspace_namespace text NOT NULL,
    kind text NOT NULL,
    fact_key text NOT NULL,
    payload text NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    source_sha256 text,
    ordinal bigint GENERATED ALWAYS AS IDENTITY,
    PRIMARY KEY (workspace_namespace, kind, fact_key),
    UNIQUE (ordinal)
);

CREATE TABLE IF NOT EXISTS v4.forward_migration_r1 (
    workspace_namespace text PRIMARY KEY,
    receipt jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS v4.forward_schema_migration_map_r1 (
    source_schema text NOT NULL,
    workspace_namespace text NOT NULL,
    kind text NOT NULL,
    fact_key text NOT NULL,
    payload_sha256 char(64) NOT NULL,
    source_sha256 char(64),
    target_sha256 char(64) NOT NULL,
    verification jsonb NOT NULL,
    migrated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (source_schema, kind, fact_key),
    CHECK (payload_sha256 = target_sha256),
    CHECK (verification->>'status' = 'VERIFIED')
);

CREATE OR REPLACE FUNCTION v4.reject_forward_fact_mutation_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'FORWARD_FACTS_APPEND_ONLY';
END $$;

DROP TRIGGER IF EXISTS forward_append_only_r1 ON v4.forward_facts;
CREATE TRIGGER forward_append_only_r1
BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.forward_facts
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_forward_fact_mutation_r1();

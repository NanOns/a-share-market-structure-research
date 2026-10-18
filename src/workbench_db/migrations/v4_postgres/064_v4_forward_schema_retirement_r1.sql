-- Minimal immutable evidence retained when an exact, empty Forward workspace retires.
CREATE TABLE v4.forward_legacy_schema_retirements_r1 (
    source_schema text PRIMARY KEY,
    source_owner text NOT NULL,
    source_relation_bytes jsonb NOT NULL,
    source_fact_rows bigint NOT NULL CHECK (source_fact_rows = 0),
    target_fact_rows bigint NOT NULL CHECK (target_fact_rows = 0),
    workspace_alias_history jsonb NOT NULL,
    forward_migration_receipt jsonb NOT NULL,
    verification jsonb NOT NULL CHECK (verification->>'status' = 'VERIFIED_EMPTY_SOURCE'),
    retired_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION v4.reject_forward_legacy_schema_retirement_mutation_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'V4_FORWARD_SCHEMA_RETIREMENT_IMMUTABLE';
END $$;

CREATE TRIGGER forward_legacy_schema_retirements_immutable_r1
BEFORE UPDATE OR DELETE ON v4.forward_legacy_schema_retirements_r1
FOR EACH ROW EXECUTE FUNCTION v4.reject_forward_legacy_schema_retirement_mutation_r1();
CREATE TRIGGER forward_legacy_schema_retirements_no_truncate_r1
BEFORE TRUNCATE ON v4.forward_legacy_schema_retirements_r1
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_forward_legacy_schema_retirement_mutation_r1();

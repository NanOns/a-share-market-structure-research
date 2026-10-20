-- Stable logical workspace identity to existing physical schema binding.
-- No data is moved or rehashed by this migration.
CREATE TABLE v4.workspace_namespace_aliases_r1 (
    logical_workspace_id text NOT NULL
        CHECK (logical_workspace_id ~ '^v4w_[0-9a-f]{32}$'),
    purpose text NOT NULL
        CHECK (purpose ~ '^[a-z][a-z0-9_]{0,24}$'),
    physical_schema text NOT NULL
        CHECK (physical_schema ~ '^v4_[a-z0-9_]{1,56}$'),
    source_root_identity_sha256 char(64) NOT NULL
        CHECK (source_root_identity_sha256 ~ '^[0-9a-f]{64}$'),
    contract_id text NOT NULL DEFAULT 'V4_PG_WORKSPACE_NAMESPACE_ALIAS_R1'
        CHECK (contract_id = 'V4_PG_WORKSPACE_NAMESPACE_ALIAS_R1'),
    status text NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','RETIRED')),
    registered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (logical_workspace_id, purpose),
    UNIQUE (physical_schema, purpose)
);

CREATE FUNCTION v4.reject_workspace_namespace_alias_mutation_r1() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_WORKSPACE_NAMESPACE_ALIAS_IMMUTABLE';
END $$;

CREATE TRIGGER workspace_namespace_alias_append_only_r1
    BEFORE UPDATE OR DELETE ON v4.workspace_namespace_aliases_r1
    FOR EACH ROW EXECUTE FUNCTION v4.reject_workspace_namespace_alias_mutation_r1();
CREATE TRIGGER workspace_namespace_alias_no_truncate_r1
    BEFORE TRUNCATE ON v4.workspace_namespace_aliases_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_workspace_namespace_alias_mutation_r1();

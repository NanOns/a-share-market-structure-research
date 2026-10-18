-- Preserve prior workspace alias evidence while retiring physical schema lookup.
CREATE TABLE v4.workspace_namespace_alias_history_r1 (
    logical_workspace_id text NOT NULL,
    purpose text NOT NULL,
    physical_schema text NOT NULL,
    source_root_identity_sha256 char(64) NOT NULL,
    contract_id text NOT NULL,
    status text NOT NULL,
    registered_at timestamptz NOT NULL,
    migration_state text NOT NULL CHECK (migration_state = 'MIGRATION_HISTORY_ONLY'),
    archived_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (logical_workspace_id,purpose),
    UNIQUE (physical_schema,purpose)
);

CREATE FUNCTION v4.reject_workspace_alias_history_mutation_r1() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'V4_WORKSPACE_ALIAS_HISTORY_IMMUTABLE';
END $$;

INSERT INTO v4.workspace_namespace_alias_history_r1
    (logical_workspace_id,purpose,physical_schema,source_root_identity_sha256,
     contract_id,status,registered_at,migration_state)
SELECT logical_workspace_id,purpose,physical_schema,source_root_identity_sha256,
       contract_id,status,registered_at,'MIGRATION_HISTORY_ONLY'
FROM v4.workspace_namespace_aliases_r1;

DO $$
DECLARE old_count bigint; new_count bigint; mismatch bigint;
BEGIN
    SELECT count(*) INTO old_count FROM v4.workspace_namespace_aliases_r1;
    SELECT count(*) INTO new_count FROM v4.workspace_namespace_alias_history_r1;
    SELECT count(*) INTO mismatch FROM v4.workspace_namespace_aliases_r1 old
    LEFT JOIN v4.workspace_namespace_alias_history_r1 archived
      USING (logical_workspace_id,purpose,physical_schema,source_root_identity_sha256,
             contract_id,status,registered_at)
    WHERE archived.logical_workspace_id IS NULL;
    IF old_count <> new_count OR mismatch <> 0 THEN
        RAISE EXCEPTION 'V4_WORKSPACE_ALIAS_HISTORY_PARITY_FAILED';
    END IF;
END $$;

CREATE TRIGGER workspace_alias_history_immutable_r1
BEFORE UPDATE OR DELETE ON v4.workspace_namespace_alias_history_r1
FOR EACH ROW EXECUTE FUNCTION v4.reject_workspace_alias_history_mutation_r1();
CREATE TRIGGER workspace_alias_history_no_truncate_r1
BEFORE TRUNCATE ON v4.workspace_namespace_alias_history_r1
FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_workspace_alias_history_mutation_r1();

DROP TRIGGER workspace_namespace_alias_append_only_r1 ON v4.workspace_namespace_aliases_r1;
DROP TRIGGER workspace_namespace_alias_no_truncate_r1 ON v4.workspace_namespace_aliases_r1;
DROP FUNCTION v4.reject_workspace_namespace_alias_mutation_r1() RESTRICT;
DROP TABLE v4.workspace_namespace_aliases_r1 RESTRICT;

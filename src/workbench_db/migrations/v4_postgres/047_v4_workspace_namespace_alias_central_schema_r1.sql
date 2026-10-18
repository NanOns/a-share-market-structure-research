-- The central publication namespace is a valid target for a moved main workspace.
ALTER TABLE v4.workspace_namespace_aliases_r1
    DROP CONSTRAINT workspace_namespace_aliases_r1_physical_schema_check;

ALTER TABLE v4.workspace_namespace_aliases_r1
    ADD CONSTRAINT workspace_namespace_aliases_r1_physical_schema_check
    CHECK (physical_schema ~ '^(v4|v4_[a-z0-9_]{1,56})$');

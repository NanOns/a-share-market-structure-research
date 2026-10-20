-- Allow multiple explicitly identified Forward namespaces in one fixed table.
-- Existing R7_ACTIVE rows keep their identities; no data is rewritten.
ALTER TABLE v4.forward_r7_facts_r1
    DROP CONSTRAINT IF EXISTS forward_r7_facts_r1_origin_namespace_check;
ALTER TABLE v4.forward_r7_facts_r1
    DROP CONSTRAINT IF EXISTS forward_r7_facts_r1_pkey;
ALTER TABLE v4.forward_r7_facts_r1
    ADD CONSTRAINT forward_r7_facts_r1_pkey
    PRIMARY KEY (origin_namespace, kind, fact_key);

ALTER TABLE v4.forward_r7_migration_r1
    DROP CONSTRAINT IF EXISTS forward_r7_migration_r1_origin_namespace_check;

CREATE INDEX IF NOT EXISTS forward_r7_facts_namespace_kind_ordinal_r1
    ON v4.forward_r7_facts_r1 (origin_namespace, kind, ordinal);

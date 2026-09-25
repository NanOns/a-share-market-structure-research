-- Complete the opaque publication ID migration for state heads and namespace cutovers.
ALTER TABLE v4.publications
    ADD CONSTRAINT uq_publication_id_namespace
    UNIQUE (publication_id, model_namespace_id);

ALTER TABLE v4.state_heads DROP CONSTRAINT IF EXISTS state_heads_check;
ALTER TABLE v4.state_heads DROP COLUMN IF EXISTS publication_revision;
ALTER TABLE v4.state_heads
    ADD CONSTRAINT fk_state_head_publication_identity
    FOREIGN KEY (publication_id, namespace_id)
    REFERENCES v4.publications(publication_id, model_namespace_id);

ALTER TABLE v4.namespace_migrations
    ADD CONSTRAINT fk_namespace_migration_frozen_source_head
    FOREIGN KEY (source_namespace_id, frozen_source_head)
    REFERENCES v4.state_heads(namespace_id, state_head_id);

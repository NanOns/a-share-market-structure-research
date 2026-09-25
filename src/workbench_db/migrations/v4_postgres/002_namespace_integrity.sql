CREATE TABLE IF NOT EXISTS v4.state_heads (
    namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
    state_head_id text NOT NULL,
    publication_id text,
    publication_revision integer,
    logical_digest char(64) NOT NULL,
    PRIMARY KEY (namespace_id, state_head_id),
    CHECK ((publication_id IS NULL) = (publication_revision IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_source_revision_single_successor
    ON v4.source_revisions (supersedes_revision_id)
    WHERE supersedes_revision_id IS NOT NULL;

CREATE OR REPLACE FUNCTION v4.validate_publication_prior_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.prior_session_state_head IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM v4.state_heads h
        WHERE h.namespace_id = NEW.model_namespace_id AND h.state_head_id = NEW.prior_session_state_head
    ) THEN
        RAISE EXCEPTION 'V4_PRIOR_STATE_HEAD_NAMESPACE_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION v4.validate_publication_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
BEGIN
    SELECT * INTO p FROM v4.publications WHERE publication_id=NEW.publication_id AND revision=NEW.revision;
    IF NOT FOUND OR p.status <> 'ACCEPTED' OR p.trade_date <> NEW.trade_date OR p.model_namespace_id <> NEW.model_namespace_id THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_TARGET_INVALID';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS v4_publication_prior_head_guard ON v4.publications;
CREATE TRIGGER v4_publication_prior_head_guard BEFORE INSERT ON v4.publications FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_prior_head();
DROP TRIGGER IF EXISTS v4_publication_head_guard ON v4.publication_heads;
CREATE TRIGGER v4_publication_head_guard BEFORE INSERT OR UPDATE ON v4.publication_heads FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_head();

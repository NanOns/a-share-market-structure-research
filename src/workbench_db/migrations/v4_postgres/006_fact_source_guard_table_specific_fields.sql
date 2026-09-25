-- PL/pgSQL boolean expressions are not relied on for short-circuiting NEW fields.
CREATE OR REPLACE FUNCTION v4.validate_fact_source_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE src v4.source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO src FROM v4.source_revisions WHERE source_revision_id = NEW.source_revision_id;
    IF NOT FOUND
       OR src.supersedes_revision_id IS DISTINCT FROM NEW.supersedes_revision_id
       OR src.provider_available_at IS DISTINCT FROM NEW.provider_available_at
       OR src.observed_at <> NEW.observed_at
       OR src.ingested_at <> NEW.ingested_at
       OR src.system_available_at <> NEW.system_available_at THEN
        RAISE EXCEPTION 'V4_FACT_SOURCE_REVISION_MISMATCH';
    END IF;
    IF TG_TABLE_NAME = 'security_membership_facts' THEN
        IF src.logical_fact_id <> NEW.membership_id THEN
            RAISE EXCEPTION 'V4_MEMBERSHIP_LOGICAL_FACT_ID_MISMATCH';
        END IF;
    END IF;
    RETURN NEW;
END $$;

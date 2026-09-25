-- Align empty Phase 0 schema with V4.2.2 REV2 publication and PIT contracts.
-- Existing Phase 0 runtime tables are empty; this is a forward-only migration.

-- Each physical publication revision receives its own opaque publication_id.
ALTER TABLE v4.publication_heads
    DROP CONSTRAINT IF EXISTS publication_heads_publication_id_revision_fkey;
ALTER TABLE v4.publication_heads DROP COLUMN IF EXISTS revision;

ALTER TABLE v4.publication_consumed_sources
    DROP CONSTRAINT IF EXISTS publication_consumed_sources_publication_id_revision_fkey;
ALTER TABLE v4.publication_consumed_sources
    DROP CONSTRAINT IF EXISTS publication_consumed_sources_pkey;
ALTER TABLE v4.publication_consumed_sources DROP COLUMN IF EXISTS revision;

ALTER TABLE v4.publication_revision_events
    DROP CONSTRAINT IF EXISTS publication_revision_events_publication_id_revision_fkey;
ALTER TABLE v4.publication_revision_events DROP COLUMN IF EXISTS revision;
ALTER TABLE v4.publication_revision_events DROP COLUMN IF EXISTS prior_revision;
ALTER TABLE v4.publication_revision_events ADD COLUMN IF NOT EXISTS prior_publication_id text;

ALTER TABLE v4.event_observations
    DROP CONSTRAINT IF EXISTS event_observations_publication_id_publication_revision_fkey;
ALTER TABLE v4.event_observations DROP COLUMN IF EXISTS publication_revision;

ALTER TABLE v4.publications DROP CONSTRAINT IF EXISTS publications_pkey;
ALTER TABLE v4.publications DROP CONSTRAINT IF EXISTS publications_trade_date_model_namespace_id_revision_key;
ALTER TABLE v4.publications RENAME COLUMN revision TO revision_no;
ALTER TABLE v4.publications DROP COLUMN IF EXISTS same_day_revision_parent;
ALTER TABLE v4.publications ADD COLUMN publication_lineage_id text NOT NULL;
ALTER TABLE v4.publications ADD COLUMN same_day_revision_parent_id text;
ALTER TABLE v4.publications ADD COLUMN prior_session_publication_id text;
ALTER TABLE v4.publications ADD COLUMN prior_session_revision_digest char(64);
ALTER TABLE v4.publications ADD COLUMN prior_session_gap_reason text;

ALTER TABLE v4.publications ADD CONSTRAINT publications_pkey PRIMARY KEY (publication_id);
ALTER TABLE v4.publications ADD CONSTRAINT uq_publication_namespace_trade_date_core
    UNIQUE (model_namespace_id, trade_date, core_revision);
ALTER TABLE v4.publications ADD CONSTRAINT uq_publication_namespace_date_lineage_revision
    UNIQUE (model_namespace_id, trade_date, publication_lineage_id, revision_no);
ALTER TABLE v4.publications ADD CONSTRAINT uq_publication_id_namespace_date
    UNIQUE (publication_id, model_namespace_id, trade_date);
ALTER TABLE v4.publications ADD CONSTRAINT uq_publication_parent_identity
    UNIQUE (publication_id, model_namespace_id, trade_date, publication_lineage_id);
ALTER TABLE v4.publications ADD CONSTRAINT uq_publication_lineage_revision_target
    UNIQUE (publication_id, model_namespace_id, trade_date, publication_lineage_id, revision_no);
ALTER TABLE v4.publications ADD CONSTRAINT ck_publication_lineage_nonempty
    CHECK (length(publication_lineage_id) > 0);
ALTER TABLE v4.publications ADD CONSTRAINT ck_publication_prior_identity
    CHECK (
        (prior_session_publication_id IS NOT NULL
         AND prior_session_revision_digest IS NOT NULL
         AND prior_session_gap_reason IS NULL)
        OR
        (prior_session_publication_id IS NULL
         AND prior_session_revision_digest IS NULL
         AND prior_session_gap_reason IS NOT NULL
         AND length(prior_session_gap_reason) > 0)
    );
ALTER TABLE v4.publications ADD CONSTRAINT fk_publication_same_day_parent
    FOREIGN KEY (same_day_revision_parent_id, model_namespace_id, trade_date, publication_lineage_id)
    REFERENCES v4.publications (publication_id, model_namespace_id, trade_date, publication_lineage_id);
ALTER TABLE v4.publications ADD CONSTRAINT fk_publication_prior_session
    FOREIGN KEY (prior_session_publication_id) REFERENCES v4.publications(publication_id);
ALTER TABLE v4.publications ADD CONSTRAINT fk_publication_prior_state_head
    FOREIGN KEY (model_namespace_id, prior_session_state_head)
    REFERENCES v4.state_heads(namespace_id, state_head_id);
CREATE UNIQUE INDEX uq_publication_same_day_parent_single_successor
    ON v4.publications(same_day_revision_parent_id)
    WHERE same_day_revision_parent_id IS NOT NULL;

ALTER TABLE v4.publication_heads
    ADD CONSTRAINT fk_publication_heads_revision_identity
    FOREIGN KEY (publication_id, model_namespace_id, trade_date)
    REFERENCES v4.publications(publication_id, model_namespace_id, trade_date);
ALTER TABLE v4.publication_consumed_sources
    ADD CONSTRAINT publication_consumed_sources_pkey PRIMARY KEY (publication_id, source_key),
    ADD CONSTRAINT fk_consumed_source_publication
    FOREIGN KEY (publication_id) REFERENCES v4.publications(publication_id);
ALTER TABLE v4.publication_revision_events
    ADD CONSTRAINT fk_publication_revision_event_publication
    FOREIGN KEY (publication_id) REFERENCES v4.publications(publication_id),
    ADD CONSTRAINT fk_publication_revision_event_parent
    FOREIGN KEY (prior_publication_id) REFERENCES v4.publications(publication_id);
ALTER TABLE v4.event_observations
    ADD CONSTRAINT fk_event_observation_publication
    FOREIGN KEY (publication_id) REFERENCES v4.publications(publication_id);

CREATE OR REPLACE FUNCTION v4.validate_publication_identity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_row v4.publications%ROWTYPE;
DECLARE prior_row v4.publications%ROWTYPE;
DECLARE namespace_contract text;
BEGIN
    IF NEW.same_day_revision_parent_id IS NOT NULL THEN
        SELECT * INTO parent_row FROM v4.publications WHERE publication_id = NEW.same_day_revision_parent_id;
        IF NOT FOUND
           OR parent_row.model_namespace_id <> NEW.model_namespace_id
           OR parent_row.trade_date <> NEW.trade_date
           OR parent_row.publication_lineage_id <> NEW.publication_lineage_id
           OR parent_row.revision_no >= NEW.revision_no
           OR NEW.revision_no <> parent_row.revision_no + 1 THEN
            RAISE EXCEPTION 'V4_SAME_DAY_PARENT_INVALID';
        END IF;
    ELSIF NEW.revision_no <> 1 THEN
        RAISE EXCEPTION 'V4_REVISION_ROOT_MUST_BE_ONE';
    END IF;

    IF NEW.prior_session_publication_id IS NOT NULL THEN
        SELECT * INTO prior_row FROM v4.publications WHERE publication_id = NEW.prior_session_publication_id;
        SELECT model_contract_id INTO namespace_contract FROM v4.model_namespaces
          WHERE namespace_id = NEW.model_namespace_id;
        IF prior_row.publication_id IS NULL OR namespace_contract IS NULL
           OR prior_row.model_namespace_id <> NEW.model_namespace_id
           OR prior_row.trade_date >= NEW.trade_date
           OR NOT EXISTS (
               SELECT 1 FROM v4.model_namespaces n
                WHERE n.namespace_id = prior_row.model_namespace_id
                  AND n.model_contract_id = namespace_contract
           )
           OR prior_row.computation_identity_sha256 <> NEW.prior_session_revision_digest THEN
            RAISE EXCEPTION 'V4_PRIOR_SESSION_PUBLICATION_INVALID';
        END IF;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_publication_identity_guard ON v4.publications;
CREATE TRIGGER v4_publication_identity_guard
    BEFORE INSERT ON v4.publications
    FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_identity();

CREATE OR REPLACE FUNCTION v4.validate_source_revision_chain() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_row v4.source_revisions%ROWTYPE;
BEGIN
    IF NEW.supersedes_revision_id IS NULL THEN
        IF NEW.revision_no <> 1 THEN
            RAISE EXCEPTION 'V4_SOURCE_REVISION_ROOT_MUST_BE_ONE';
        END IF;
    ELSE
        SELECT * INTO parent_row FROM v4.source_revisions
         WHERE source_revision_id = NEW.supersedes_revision_id;
        IF NOT FOUND OR parent_row.logical_fact_id <> NEW.logical_fact_id
           OR NEW.revision_no <> parent_row.revision_no + 1
           OR NEW.source_revision_id = NEW.supersedes_revision_id THEN
            RAISE EXCEPTION 'V4_SOURCE_REVISION_CHAIN_INVALID';
        END IF;
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS v4_source_revision_chain_guard ON v4.source_revisions;
CREATE TRIGGER v4_source_revision_chain_guard
    BEFORE INSERT ON v4.source_revisions
    FOR EACH ROW EXECUTE FUNCTION v4.validate_source_revision_chain();

-- Lifecycle facts mirror source revision knowledge time and correction lineage.
ALTER TABLE v4.security_lifecycle_facts
    ADD COLUMN provider_available_at timestamptz,
    ADD COLUMN supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id);
ALTER TABLE v4.security_lifecycle_facts
    ADD CONSTRAINT ck_lifecycle_system_available_max
    CHECK (system_available_at = GREATEST(observed_at, ingested_at));
ALTER TABLE v4.security_lifecycle_facts
    ADD CONSTRAINT ck_lifecycle_provider_time
    CHECK (provider_available_at IS NULL OR provider_available_at <= observed_at);

CREATE TABLE v4.security_membership_facts (
    membership_id text NOT NULL,
    security_id text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    provider_available_at timestamptz,
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    source_revision_id text NOT NULL REFERENCES v4.source_revisions(source_revision_id),
    supersedes_revision_id text REFERENCES v4.source_revisions(source_revision_id),
    source_identity text NOT NULL,
    quality text NOT NULL,
    PRIMARY KEY (membership_id, source_revision_id),
    CHECK (length(membership_id) > 0 AND length(security_id) > 0 AND length(source_identity) > 0),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    CHECK (system_available_at = GREATEST(observed_at, ingested_at)),
    CHECK (provider_available_at IS NULL OR provider_available_at <= observed_at)
);

CREATE INDEX ix_membership_effective ON v4.security_membership_facts(security_id, effective_from, effective_to);
CREATE INDEX ix_membership_revision_cutoff ON v4.security_membership_facts(membership_id, system_available_at);

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
    IF TG_TABLE_NAME = 'security_membership_facts' AND src.logical_fact_id <> NEW.membership_id THEN
        RAISE EXCEPTION 'V4_MEMBERSHIP_LOGICAL_FACT_ID_MISMATCH';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_lifecycle_source_revision_guard ON v4.security_lifecycle_facts;
CREATE TRIGGER v4_lifecycle_source_revision_guard
    BEFORE INSERT ON v4.security_lifecycle_facts
    FOR EACH ROW EXECUTE FUNCTION v4.validate_fact_source_revision();
CREATE TRIGGER v4_membership_source_revision_guard
    BEFORE INSERT ON v4.security_membership_facts
    FOR EACH ROW EXECUTE FUNCTION v4.validate_fact_source_revision();

CREATE OR REPLACE FUNCTION v4.reject_append_only_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_APPEND_ONLY_TABLE:%', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
END $$;
DROP TRIGGER IF EXISTS v4_append_only_guard ON v4.security_membership_facts;
CREATE TRIGGER v4_append_only_guard
    BEFORE UPDATE OR DELETE ON v4.security_membership_facts
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

DROP INDEX IF EXISTS v4.ix_publication_revision_events_identity;
CREATE INDEX ix_publication_revision_events_identity
    ON v4.publication_revision_events(publication_id, recorded_at);

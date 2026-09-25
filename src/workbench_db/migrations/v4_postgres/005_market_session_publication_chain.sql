-- Versioned market-session identity makes a publication predecessor verifiable.
CREATE TABLE v4.market_calendar_sessions (
    market_calendar_id text NOT NULL,
    session_no bigint NOT NULL CHECK (session_no > 0),
    trade_date date NOT NULL,
    calendar_digest char(64) NOT NULL CHECK (calendar_digest ~ '^[0-9a-fA-F]{64}$'),
    PRIMARY KEY (market_calendar_id, trade_date),
    UNIQUE (market_calendar_id, session_no)
);

ALTER TABLE v4.publications ADD COLUMN market_calendar_id text NOT NULL;
ALTER TABLE v4.publications
    ADD CONSTRAINT fk_publication_market_session
    FOREIGN KEY (market_calendar_id, trade_date)
    REFERENCES v4.market_calendar_sessions(market_calendar_id, trade_date);

CREATE OR REPLACE FUNCTION v4.validate_publication_identity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_row v4.publications%ROWTYPE;
DECLARE prior_row v4.publications%ROWTYPE;
DECLARE namespace_contract text;
DECLARE current_session_no bigint;
DECLARE prior_session_no bigint;
BEGIN
    IF NEW.same_day_revision_parent_id IS NOT NULL THEN
        SELECT * INTO parent_row FROM v4.publications WHERE publication_id = NEW.same_day_revision_parent_id;
        IF NOT FOUND
           OR parent_row.model_namespace_id <> NEW.model_namespace_id
           OR parent_row.market_calendar_id <> NEW.market_calendar_id
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
        SELECT model_contract_id INTO namespace_contract FROM v4.model_namespaces WHERE namespace_id = NEW.model_namespace_id;
        SELECT session_no INTO current_session_no FROM v4.market_calendar_sessions
         WHERE market_calendar_id = NEW.market_calendar_id AND trade_date = NEW.trade_date;
        SELECT session_no INTO prior_session_no FROM v4.market_calendar_sessions
         WHERE market_calendar_id = NEW.market_calendar_id AND trade_date = prior_row.trade_date;
        IF prior_row.publication_id IS NULL OR namespace_contract IS NULL
           OR prior_row.model_namespace_id <> NEW.model_namespace_id
           OR prior_row.market_calendar_id <> NEW.market_calendar_id
           OR prior_session_no IS NULL OR current_session_no IS NULL
           OR prior_session_no <> current_session_no - 1
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

DROP TRIGGER IF EXISTS v4_append_only_guard ON v4.market_calendar_sessions;
CREATE TRIGGER v4_append_only_guard
    BEFORE UPDATE OR DELETE ON v4.market_calendar_sessions
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

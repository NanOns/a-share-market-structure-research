-- Keep DELETE/UPDATE head validation unambiguous in PL/pgSQL and retain freeze semantics.
CREATE OR REPLACE FUNCTION v4.validate_publication_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
DECLARE session_no_value bigint;
DECLARE market_calendar_id_value text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT session_row.session_no, publication_row.market_calendar_id
          INTO session_no_value, market_calendar_id_value
          FROM v4.publications publication_row
          JOIN v4.market_calendar_sessions session_row
            ON session_row.market_calendar_id = publication_row.market_calendar_id
           AND session_row.trade_date = publication_row.trade_date
         WHERE publication_row.publication_id = OLD.publication_id;
        PERFORM pg_advisory_xact_lock(hashtextextended(
            OLD.model_namespace_id || ':' || market_calendar_id_value || ':' || session_no_value::text, 0));
        IF EXISTS (
            SELECT 1 FROM v4.publications child
            JOIN v4.publications parent_publication ON parent_publication.publication_id = OLD.publication_id
            JOIN v4.market_calendar_sessions parent_session
              ON parent_session.market_calendar_id = parent_publication.market_calendar_id
             AND parent_session.trade_date = parent_publication.trade_date
            JOIN v4.market_calendar_sessions child_session
              ON child_session.market_calendar_id = child.market_calendar_id
             AND child_session.trade_date = child.trade_date
            WHERE child.model_namespace_id = OLD.model_namespace_id
              AND child_session.market_calendar_id = parent_session.market_calendar_id
              AND child_session.session_no = parent_session.session_no + 1
              AND (child.prior_session_publication_id = OLD.publication_id OR child.prior_session_gap_reason IS NOT NULL)
        ) THEN
            RAISE EXCEPTION 'V4_PUBLICATION_HEAD_FROZEN_BY_NEXT_SESSION';
        END IF;
        RETURN OLD;
    END IF;

    SELECT * INTO p FROM v4.publications WHERE publication_id = NEW.publication_id;
    IF NOT FOUND OR p.status <> 'ACCEPTED' OR p.trade_date <> NEW.trade_date
       OR p.model_namespace_id <> NEW.model_namespace_id THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_TARGET_INVALID';
    END IF;
    SELECT session_row.session_no INTO session_no_value FROM v4.market_calendar_sessions session_row
     WHERE session_row.market_calendar_id = p.market_calendar_id AND session_row.trade_date = p.trade_date;
    PERFORM pg_advisory_xact_lock(hashtextextended(
        NEW.model_namespace_id || ':' || p.market_calendar_id || ':' || session_no_value::text, 0));

    IF NOT EXISTS (
        SELECT 1 FROM v4.state_heads state_head
         WHERE state_head.namespace_id = NEW.model_namespace_id
           AND state_head.state_head_id = NEW.state_head_id
           AND state_head.publication_id = NEW.publication_id
           AND state_head.logical_digest = NEW.state_logical_digest
    ) THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_STATE_TARGET_INVALID';
    END IF;

    IF TG_OP = 'UPDATE'
       AND (OLD.publication_id, OLD.state_head_id, OLD.state_logical_digest)
           IS DISTINCT FROM (NEW.publication_id, NEW.state_head_id, NEW.state_logical_digest)
       AND EXISTS (
            SELECT 1 FROM v4.publications child
            JOIN v4.publications old_publication ON old_publication.publication_id = OLD.publication_id
            JOIN v4.market_calendar_sessions parent_session
              ON parent_session.market_calendar_id = old_publication.market_calendar_id
             AND parent_session.trade_date = OLD.trade_date
            JOIN v4.market_calendar_sessions child_session
              ON child_session.market_calendar_id = old_publication.market_calendar_id
             AND child_session.trade_date = child.trade_date
            WHERE child.model_namespace_id = OLD.model_namespace_id
              AND child_session.session_no = parent_session.session_no + 1
              AND (child.prior_session_publication_id = OLD.publication_id OR child.prior_session_gap_reason IS NOT NULL)
       ) THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_FROZEN_BY_NEXT_SESSION';
    END IF;
    RETURN NEW;
END $$;

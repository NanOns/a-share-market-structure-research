-- Freeze the accepted previous-session publication and logical state as one identity.
ALTER TABLE v4.publications
    DROP CONSTRAINT IF EXISTS ck_publication_prior_identity;
ALTER TABLE v4.publications
    RENAME COLUMN prior_session_revision_digest TO prior_session_state_logical_digest;
ALTER TABLE v4.publications
    ADD CONSTRAINT ck_publication_prior_state_identity CHECK (
        (prior_session_publication_id IS NOT NULL
         AND prior_session_state_head IS NOT NULL
         AND prior_session_state_logical_digest IS NOT NULL
         AND prior_session_gap_reason IS NULL)
        OR
        (prior_session_publication_id IS NULL
         AND prior_session_state_head IS NULL
         AND prior_session_state_logical_digest IS NULL
         AND prior_session_gap_reason IS NOT NULL
         AND length(prior_session_gap_reason) > 0)
    );

-- A published head now names its state head and logical digest explicitly.
ALTER TABLE v4.state_heads
    ADD CONSTRAINT uq_state_head_publication_logical_identity
    UNIQUE (namespace_id, state_head_id, publication_id, logical_digest);

ALTER TABLE v4.publication_heads
    ADD COLUMN state_head_id text NOT NULL,
    ADD COLUMN state_logical_digest char(64) NOT NULL,
    ADD CONSTRAINT fk_publication_head_state_identity
    FOREIGN KEY (model_namespace_id, state_head_id, publication_id, state_logical_digest)
    REFERENCES v4.state_heads(namespace_id, state_head_id, publication_id, logical_digest);

CREATE OR REPLACE FUNCTION v4.validate_publication_identity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_row v4.publications%ROWTYPE;
DECLARE prior_row v4.publications%ROWTYPE;
DECLARE current_session_no bigint;
DECLARE prior_session_no bigint;
DECLARE prior_session_date date;
DECLARE prior_head v4.publication_heads%ROWTYPE;
DECLARE has_earlier_session boolean;
DECLARE has_prior_head boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('market-calendar:' || NEW.market_calendar_id, 0));

    IF NEW.same_day_revision_parent_id IS NOT NULL THEN
        SELECT * INTO parent_row FROM v4.publications WHERE publication_id = NEW.same_day_revision_parent_id;
        IF NOT FOUND
           OR parent_row.model_namespace_id <> NEW.model_namespace_id
           OR parent_row.market_calendar_id <> NEW.market_calendar_id
           OR parent_row.trade_date <> NEW.trade_date
           OR parent_row.publication_lineage_id <> NEW.publication_lineage_id
           OR parent_row.revision_no >= NEW.revision_no
           OR NEW.revision_no <> parent_row.revision_no + 1
           OR NEW.prior_session_publication_id IS DISTINCT FROM parent_row.prior_session_publication_id
           OR NEW.prior_session_state_head IS DISTINCT FROM parent_row.prior_session_state_head
           OR NEW.prior_session_state_logical_digest IS DISTINCT FROM parent_row.prior_session_state_logical_digest
           OR NEW.prior_session_gap_reason IS DISTINCT FROM parent_row.prior_session_gap_reason THEN
            RAISE EXCEPTION 'V4_SAME_DAY_PARENT_INVALID';
        END IF;
    ELSIF NEW.revision_no <> 1 THEN
        RAISE EXCEPTION 'V4_REVISION_ROOT_MUST_BE_ONE';
    END IF;

    SELECT session_no INTO current_session_no
      FROM v4.market_calendar_sessions
     WHERE market_calendar_id = NEW.market_calendar_id AND trade_date = NEW.trade_date;
    IF current_session_no IS NULL THEN
        RAISE EXCEPTION 'V4_CURRENT_MARKET_SESSION_MISSING';
    END IF;

    IF NEW.prior_session_publication_id IS NOT NULL THEN
        SELECT * INTO prior_row FROM v4.publications WHERE publication_id = NEW.prior_session_publication_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'V4_PRIOR_SESSION_PUBLICATION_INVALID';
        END IF;
        SELECT trade_date, session_no INTO prior_session_date, prior_session_no
          FROM v4.market_calendar_sessions
         WHERE market_calendar_id = NEW.market_calendar_id AND session_no = current_session_no - 1;
        IF prior_session_no IS NULL THEN
            RAISE EXCEPTION 'V4_PRIOR_MARKET_SESSION_MISSING';
        END IF;

        PERFORM pg_advisory_xact_lock(hashtextextended(
            NEW.model_namespace_id || ':' || NEW.market_calendar_id || ':' || prior_session_no::text, 0));
        SELECT * INTO prior_head FROM v4.publication_heads
         WHERE trade_date = prior_session_date AND model_namespace_id = NEW.model_namespace_id;

        IF prior_head.publication_id IS NULL
           OR prior_head.publication_id <> NEW.prior_session_publication_id
           OR prior_head.state_head_id <> NEW.prior_session_state_head
           OR prior_head.state_logical_digest <> NEW.prior_session_state_logical_digest
           OR prior_row.status <> 'ACCEPTED'
           OR prior_row.trade_date <> prior_session_date
           OR prior_row.model_namespace_id <> NEW.model_namespace_id
           OR prior_row.market_calendar_id <> NEW.market_calendar_id
           OR NOT EXISTS (
               SELECT 1 FROM v4.state_heads h
                WHERE h.namespace_id = NEW.model_namespace_id
                  AND h.state_head_id = NEW.prior_session_state_head
                  AND h.publication_id = NEW.prior_session_publication_id
                  AND h.logical_digest = NEW.prior_session_state_logical_digest
           ) THEN
            RAISE EXCEPTION 'V4_PRIOR_SESSION_ACCEPTED_STATE_INVALID';
        END IF;
    ELSE
        SELECT session_no INTO prior_session_no
          FROM v4.market_calendar_sessions
         WHERE market_calendar_id = NEW.market_calendar_id AND session_no = current_session_no - 1;
        IF prior_session_no IS NULL THEN
            SELECT EXISTS (
                SELECT 1 FROM v4.market_calendar_sessions
                 WHERE market_calendar_id = NEW.market_calendar_id AND session_no < current_session_no
            ) INTO has_earlier_session;
            IF has_earlier_session OR NEW.prior_session_gap_reason NOT IN ('FIRST_OBSERVED', 'INITIAL_BOUNDARY') THEN
                RAISE EXCEPTION 'V4_INITIAL_SESSION_BOUNDARY_INVALID';
            END IF;
        ELSE
            PERFORM pg_advisory_xact_lock(hashtextextended(
                NEW.model_namespace_id || ':' || NEW.market_calendar_id || ':' || prior_session_no::text, 0));
            SELECT EXISTS (SELECT 1 FROM v4.publication_heads h
             JOIN v4.market_calendar_sessions s
               ON s.market_calendar_id = NEW.market_calendar_id AND s.trade_date = h.trade_date
             WHERE h.model_namespace_id = NEW.model_namespace_id
               AND s.session_no = prior_session_no) INTO has_prior_head;
            IF has_prior_head OR NEW.prior_session_gap_reason IN ('FIRST_OBSERVED', 'INITIAL_BOUNDARY') THEN
                RAISE EXCEPTION 'V4_PRIOR_SESSION_GAP_INVALID';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION v4.validate_market_calendar_session_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('market-calendar:' || NEW.market_calendar_id, 0));
    IF EXISTS (
        SELECT 1 FROM v4.publications p
        JOIN v4.market_calendar_sessions current_session
          ON current_session.market_calendar_id = p.market_calendar_id AND current_session.trade_date = p.trade_date
        WHERE p.market_calendar_id = NEW.market_calendar_id
          AND current_session.session_no > NEW.session_no
          AND p.prior_session_gap_reason IN ('FIRST_OBSERVED', 'INITIAL_BOUNDARY')
    ) THEN
        RAISE EXCEPTION 'V4_MARKET_CALENDAR_INSERT_INVALIDATES_INITIAL_BOUNDARY';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER v4_market_calendar_session_boundary_guard
    BEFORE INSERT ON v4.market_calendar_sessions
    FOR EACH ROW EXECUTE FUNCTION v4.validate_market_calendar_session_insert();

CREATE OR REPLACE FUNCTION v4.validate_publication_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p v4.publications%ROWTYPE;
DECLARE session_no_value bigint;
DECLARE market_calendar_id_value text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT s.session_no, p.market_calendar_id INTO session_no_value, market_calendar_id_value
          FROM v4.publications p
          JOIN v4.market_calendar_sessions s
            ON s.market_calendar_id = p.market_calendar_id AND s.trade_date = p.trade_date
         WHERE p.publication_id = OLD.publication_id;
        PERFORM pg_advisory_xact_lock(hashtextextended(
            OLD.model_namespace_id || ':' || market_calendar_id_value || ':' || session_no_value::text, 0));
        IF EXISTS (
            SELECT 1 FROM v4.publications child
            JOIN v4.publications parent ON parent.publication_id = OLD.publication_id
            JOIN v4.market_calendar_sessions ps
              ON ps.market_calendar_id = parent.market_calendar_id AND ps.trade_date = parent.trade_date
            JOIN v4.market_calendar_sessions cs
              ON cs.market_calendar_id = child.market_calendar_id AND cs.trade_date = child.trade_date
            WHERE child.model_namespace_id = OLD.model_namespace_id
              AND cs.market_calendar_id = ps.market_calendar_id
              AND cs.session_no = ps.session_no + 1
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
    SELECT session_no INTO session_no_value FROM v4.market_calendar_sessions
     WHERE market_calendar_id = p.market_calendar_id AND trade_date = p.trade_date;
    PERFORM pg_advisory_xact_lock(hashtextextended(
        NEW.model_namespace_id || ':' || p.market_calendar_id || ':' || session_no_value::text, 0));

    IF NOT EXISTS (
        SELECT 1 FROM v4.state_heads h
         WHERE h.namespace_id = NEW.model_namespace_id
           AND h.state_head_id = NEW.state_head_id
           AND h.publication_id = NEW.publication_id
           AND h.logical_digest = NEW.state_logical_digest
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
              ON parent_session.market_calendar_id = old_publication.market_calendar_id AND parent_session.trade_date = OLD.trade_date
            JOIN v4.market_calendar_sessions child_session
              ON child_session.market_calendar_id = old_publication.market_calendar_id AND child_session.trade_date = child.trade_date
            WHERE child.model_namespace_id = OLD.model_namespace_id
              AND child_session.session_no = parent_session.session_no + 1
              AND (child.prior_session_publication_id = OLD.publication_id OR child.prior_session_gap_reason IS NOT NULL)
       ) THEN
        RAISE EXCEPTION 'V4_PUBLICATION_HEAD_FROZEN_BY_NEXT_SESSION';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS v4_publication_head_guard ON v4.publication_heads;
CREATE TRIGGER v4_publication_head_guard
    BEFORE INSERT OR UPDATE OR DELETE ON v4.publication_heads
    FOR EACH ROW EXECUTE FUNCTION v4.validate_publication_head();

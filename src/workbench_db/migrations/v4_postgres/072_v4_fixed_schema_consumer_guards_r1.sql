-- Fixed-schema runtime guards for versioned V4 consumers.
-- Relations are created by migrations 052, 053 and 056. Application startup
-- validates them and never creates/replaces persistent database objects.

CREATE OR REPLACE FUNCTION v4.owner_guard_risk_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'owner_versions_risk_r1' THEN
        IF TG_OP = 'INSERT' AND NOT NEW.sealed THEN RETURN NEW; END IF;
        IF TG_OP = 'UPDATE' AND NOT OLD.sealed AND NEW.sealed
           AND (OLD.token,OLD.T0,OLD.contract,OLD.digest,OLD.row_count,OLD.database_identity) =
               (NEW.token,NEW.T0,NEW.contract,NEW.digest,NEW.row_count,NEW.database_identity) THEN
            RETURN NEW;
        END IF;
    ELSE
        IF TG_OP = 'INSERT' AND NOT EXISTS (
            SELECT 1 FROM v4.owner_versions_risk_r1
            WHERE token=NEW.token AND T0=NEW.T0 AND sealed
        ) THEN RETURN NEW; END IF;
    END IF;
    RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE';
END
$$;

CREATE OR REPLACE FUNCTION v4.owner_no_truncate_risk_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE'; END
$$;

CREATE OR REPLACE FUNCTION v4.owner_guard_priority_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'owner_versions_priority_r1' THEN
        IF TG_OP = 'INSERT' AND NOT NEW.sealed THEN RETURN NEW; END IF;
        IF TG_OP = 'UPDATE' AND NOT OLD.sealed AND NEW.sealed
           AND (OLD.token,OLD.T0,OLD.contract,OLD.digest,OLD.row_count,OLD.database_identity) =
               (NEW.token,NEW.T0,NEW.contract,NEW.digest,NEW.row_count,NEW.database_identity) THEN
            RETURN NEW;
        END IF;
    ELSE
        IF TG_OP = 'INSERT' AND NOT EXISTS (
            SELECT 1 FROM v4.owner_versions_priority_r1
            WHERE token=NEW.token AND T0=NEW.T0 AND sealed
        ) THEN RETURN NEW; END IF;
    END IF;
    RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE';
END
$$;

CREATE OR REPLACE FUNCTION v4.owner_no_truncate_priority_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'OPERATIONAL_RISK_OWNER_IMMUTABLE'; END
$$;

DROP TRIGGER IF EXISTS risk_r1_immutable_guard ON v4.owner_versions_risk_r1;
DROP TRIGGER IF EXISTS risk_r1_immutable_guard ON v4.owner_payloads_risk_r1;
DROP TRIGGER IF EXISTS risk_r1_no_truncate_guard ON v4.owner_versions_risk_r1;
DROP TRIGGER IF EXISTS risk_r1_no_truncate_guard ON v4.owner_payloads_risk_r1;
CREATE TRIGGER risk_r1_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.owner_versions_risk_r1
    FOR EACH ROW EXECUTE FUNCTION v4.owner_guard_risk_r1();
CREATE TRIGGER risk_r1_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.owner_payloads_risk_r1
    FOR EACH ROW EXECUTE FUNCTION v4.owner_guard_risk_r1();
CREATE TRIGGER risk_r1_no_truncate_guard BEFORE TRUNCATE ON v4.owner_versions_risk_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_no_truncate_risk_r1();
CREATE TRIGGER risk_r1_no_truncate_guard BEFORE TRUNCATE ON v4.owner_payloads_risk_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_no_truncate_risk_r1();

DROP TRIGGER IF EXISTS priority_r1_immutable_guard ON v4.owner_versions_priority_r1;
DROP TRIGGER IF EXISTS priority_r1_immutable_guard ON v4.owner_payloads_priority_r1;
DROP TRIGGER IF EXISTS priority_r1_no_truncate_guard ON v4.owner_versions_priority_r1;
DROP TRIGGER IF EXISTS priority_r1_no_truncate_guard ON v4.owner_payloads_priority_r1;
CREATE TRIGGER priority_r1_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.owner_versions_priority_r1
    FOR EACH ROW EXECUTE FUNCTION v4.owner_guard_priority_r1();
CREATE TRIGGER priority_r1_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.owner_payloads_priority_r1
    FOR EACH ROW EXECUTE FUNCTION v4.owner_guard_priority_r1();
CREATE TRIGGER priority_r1_no_truncate_guard BEFORE TRUNCATE ON v4.owner_versions_priority_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_no_truncate_priority_r1();
CREATE TRIGGER priority_r1_no_truncate_guard BEFORE TRUNCATE ON v4.owner_payloads_priority_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_no_truncate_priority_r1();

CREATE OR REPLACE FUNCTION v4.sector_lifecycle_owner_immutable_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'sector_lifecycle_owner_versions_r1' THEN
        IF TG_OP = 'INSERT' AND NOT NEW.sealed THEN RETURN NEW; END IF;
        IF TG_OP = 'UPDATE' AND NOT OLD.sealed AND NEW.sealed
           AND (OLD.token,OLD.T0,OLD.contract,OLD.digest,OLD.producer_sha256,OLD.parameter_digest,OLD.input_digest,OLD.row_count,OLD.database_identity) =
               (NEW.token,NEW.T0,NEW.contract,NEW.digest,NEW.producer_sha256,NEW.parameter_digest,NEW.input_digest,NEW.row_count,NEW.database_identity) THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE';
    END IF;
    IF TG_OP <> 'INSERT' OR EXISTS (
        SELECT 1 FROM v4.sector_lifecycle_owner_versions_r1
        WHERE token=NEW.token AND T0=NEW.T0 AND sealed
    ) THEN RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE'; END IF;
    RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION v4.owner_sector_lifecycle_no_truncate_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'SECTOR_LIFECYCLE_OWNER_IMMUTABLE'; END
$$;

DROP TRIGGER IF EXISTS sector_lifecycle_owner_immutable_r1_guard ON v4.sector_lifecycle_owner_versions_r1;
DROP TRIGGER IF EXISTS sector_lifecycle_owner_immutable_r1_guard ON v4.sector_lifecycle_owner_rows_r1;
DROP TRIGGER IF EXISTS owner_sector_lifecycle_no_truncate_r1_guard ON v4.sector_lifecycle_owner_versions_r1;
DROP TRIGGER IF EXISTS owner_sector_lifecycle_no_truncate_r1_guard ON v4.sector_lifecycle_owner_rows_r1;
CREATE TRIGGER sector_lifecycle_owner_immutable_r1_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.sector_lifecycle_owner_versions_r1
    FOR EACH ROW EXECUTE FUNCTION v4.sector_lifecycle_owner_immutable_r1();
CREATE TRIGGER sector_lifecycle_owner_immutable_r1_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.sector_lifecycle_owner_rows_r1
    FOR EACH ROW EXECUTE FUNCTION v4.sector_lifecycle_owner_immutable_r1();
CREATE TRIGGER owner_sector_lifecycle_no_truncate_r1_guard BEFORE TRUNCATE ON v4.sector_lifecycle_owner_versions_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_sector_lifecycle_no_truncate_r1();
CREATE TRIGGER owner_sector_lifecycle_no_truncate_r1_guard BEFORE TRUNCATE ON v4.sector_lifecycle_owner_rows_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.owner_sector_lifecycle_no_truncate_r1();

CREATE OR REPLACE FUNCTION v4.read_index_r1_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='read_versions_r1' THEN
        IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed
           AND (OLD.token,OLD.day,OLD.digest,OLD.contract)=(NEW.token,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
        IF TG_OP='INSERT' THEN RETURN NEW; END IF;
        RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
    END IF;
    IF TG_OP<>'INSERT' OR EXISTS (
        SELECT 1 FROM v4.read_versions_r1 WHERE token=NEW.token AND day=NEW.day AND sealed
    ) THEN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END IF;
    RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION v4.read_index_r2_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='read_versions_r2' THEN
        IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed
           AND (OLD.context_id,OLD.day,OLD.digest,OLD.contract)=(NEW.context_id,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
        IF TG_OP='INSERT' THEN RETURN NEW; END IF;
        RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
    END IF;
    IF TG_OP<>'INSERT' OR EXISTS (
        SELECT 1 FROM v4.read_versions_r2 WHERE context_id=NEW.context_id AND day=NEW.day AND digest=NEW.digest AND sealed
    ) THEN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END IF;
    RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION v4.read_index_r1_no_truncate()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END $$;
CREATE OR REPLACE FUNCTION v4.read_index_r2_no_truncate()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END $$;

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['read_versions_r1','read_items_r1','read_responses_r1'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS read_index_r1_immutable_guard ON v4.%I',table_name);
        EXECUTE format('DROP TRIGGER IF EXISTS read_index_r1_truncate_guard ON v4.%I',table_name);
        EXECUTE format('DROP TRIGGER IF EXISTS read_index_truncate_guard ON v4.%I',table_name);
        EXECUTE format('CREATE TRIGGER read_index_r1_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.%I FOR EACH ROW EXECUTE FUNCTION v4.read_index_r1_immutable()',table_name);
        EXECUTE format('CREATE TRIGGER read_index_r1_truncate_guard BEFORE TRUNCATE ON v4.%I FOR EACH STATEMENT EXECUTE FUNCTION v4.read_index_r1_no_truncate()',table_name);
    END LOOP;
    FOREACH table_name IN ARRAY ARRAY['read_versions_r2','read_items_r2','read_responses_r2'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS read_index_r2_immutable_guard ON v4.%I',table_name);
        EXECUTE format('DROP TRIGGER IF EXISTS read_index_truncate_guard ON v4.%I',table_name);
        EXECUTE format('CREATE TRIGGER read_index_r2_immutable_guard BEFORE INSERT OR UPDATE OR DELETE ON v4.%I FOR EACH ROW EXECUTE FUNCTION v4.read_index_r2_immutable()',table_name);
        EXECUTE format('CREATE TRIGGER read_index_truncate_guard BEFORE TRUNCATE ON v4.%I FOR EACH STATEMENT EXECUTE FUNCTION v4.read_index_r2_no_truncate()',table_name);
    END LOOP;
END
$$;

CREATE OR REPLACE FUNCTION v4.reject_jobs_history_mutation_r1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'IMMUTABLE_JOB_ATTEMPT_EVENT_HISTORY'; END
$$;

DROP TRIGGER IF EXISTS append_only_jobs_history_r1 ON v4.jobs_scheduler_attempts_r1;
DROP TRIGGER IF EXISTS append_only_jobs_history_r1 ON v4.jobs_update_events_r1;
CREATE TRIGGER append_only_jobs_history_r1 BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.jobs_scheduler_attempts_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_jobs_history_mutation_r1();
CREATE TRIGGER append_only_jobs_history_r1 BEFORE UPDATE OR DELETE OR TRUNCATE ON v4.jobs_update_events_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_jobs_history_mutation_r1();

INSERT INTO v4.jobs_scheduler_policy_r1(id,enabled,revision,updated_at)
VALUES(1,1,1,clock_timestamp()) ON CONFLICT(id) DO NOTHING;

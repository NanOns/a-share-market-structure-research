-- History storage and its immutability guards are provisioned centrally in v4.
-- Runtime builders must not create or replace database structure.
CREATE OR REPLACE FUNCTION v4.reject_history_r1_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF TG_TABLE_NAME = 'history_bars_r1' AND NOT EXISTS (
            SELECT 1 FROM v4.history_versions_r1 WHERE version = NEW.version
        ) THEN
            RETURN NEW;
        ELSIF TG_TABLE_NAME = 'history_versions_r1' AND NOT EXISTS (
            SELECT 1 FROM v4.history_versions_r1 WHERE version = NEW.version
        ) THEN
            RETURN NEW;
        END IF;
    END IF;
    RAISE EXCEPTION 'IMMUTABLE_HISTORY_VERSION';
END
$$;

DROP TRIGGER IF EXISTS immutable_history_r1 ON v4.history_bars_r1;
CREATE TRIGGER immutable_history_r1
    BEFORE INSERT OR UPDATE OR DELETE ON v4.history_bars_r1
    FOR EACH ROW EXECUTE FUNCTION v4.reject_history_r1_mutation();
DROP TRIGGER IF EXISTS immutable_history_r1_truncate ON v4.history_bars_r1;
CREATE TRIGGER immutable_history_r1_truncate
    BEFORE TRUNCATE ON v4.history_bars_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_history_r1_mutation();

DROP TRIGGER IF EXISTS immutable_history_r1_version ON v4.history_versions_r1;
CREATE TRIGGER immutable_history_r1_version
    BEFORE INSERT OR UPDATE OR DELETE ON v4.history_versions_r1
    FOR EACH ROW EXECUTE FUNCTION v4.reject_history_r1_mutation();
DROP TRIGGER IF EXISTS immutable_history_r1_version_truncate ON v4.history_versions_r1;
CREATE TRIGGER immutable_history_r1_version_truncate
    BEFORE TRUNCATE ON v4.history_versions_r1
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_history_r1_mutation();

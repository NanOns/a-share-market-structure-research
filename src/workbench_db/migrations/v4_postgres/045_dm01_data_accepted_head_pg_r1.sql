-- Canonical DM01 accepted Data Head. Bootstrap must copy the exact current
-- Head bytes already admitted to SourceIngress; this migration never seeds it.
CREATE TABLE v4.dm01_data_accepted_heads (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    head_payload jsonb NOT NULL,
    head_bytes bytea NOT NULL,
    head_sha256 char(64) NOT NULL CHECK (head_sha256 ~ '^[0-9a-f]{64}$'),
    generation bigint NOT NULL CHECK (generation > 0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (head_payload->>'contract_id' = 'V4_DATA_ACCEPTED_HEAD_V2'),
    CHECK (encode(sha256(head_bytes), 'hex') = head_sha256),
    CHECK (head_payload = convert_from(head_bytes, 'UTF8')::jsonb)
);

CREATE TABLE v4.dm01_data_accepted_head_history (
    generation bigint PRIMARY KEY,
    head_payload jsonb NOT NULL,
    head_bytes bytea NOT NULL,
    head_sha256 char(64) NOT NULL CHECK (head_sha256 ~ '^[0-9a-f]{64}$'),
    replaced_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (encode(sha256(head_bytes), 'hex') = head_sha256),
    CHECK (head_payload = convert_from(head_bytes, 'UTF8')::jsonb)
);

CREATE FUNCTION v4.guard_dm01_data_accepted_head() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'V4_DM01_DATA_HEAD_DELETE_FORBIDDEN';
    END IF;
    IF NEW.singleton IS DISTINCT FROM OLD.singleton
       OR NEW.generation <> OLD.generation + 1 THEN
        RAISE EXCEPTION 'V4_DM01_DATA_HEAD_CAS_GENERATION_REQUIRED';
    END IF;
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END $$;

CREATE FUNCTION v4.archive_dm01_data_accepted_head() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO v4.dm01_data_accepted_head_history
        (generation, head_payload, head_bytes, head_sha256)
    VALUES (OLD.generation, OLD.head_payload, OLD.head_bytes, OLD.head_sha256);
    RETURN NEW;
END $$;

CREATE TRIGGER dm01_data_accepted_head_cas
    BEFORE UPDATE OR DELETE ON v4.dm01_data_accepted_heads
    FOR EACH ROW EXECUTE FUNCTION v4.guard_dm01_data_accepted_head();
CREATE TRIGGER dm01_data_accepted_head_archive
    AFTER UPDATE ON v4.dm01_data_accepted_heads
    FOR EACH ROW EXECUTE FUNCTION v4.archive_dm01_data_accepted_head();

CREATE FUNCTION v4.reject_dm01_data_head_history_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'V4_DM01_DATA_HEAD_HISTORY_APPEND_ONLY';
END $$;
CREATE TRIGGER dm01_data_head_history_append_only
    BEFORE UPDATE OR DELETE ON v4.dm01_data_accepted_head_history
    FOR EACH ROW EXECUTE FUNCTION v4.reject_dm01_data_head_history_mutation();
CREATE TRIGGER dm01_data_head_history_no_truncate
    BEFORE TRUNCATE ON v4.dm01_data_accepted_head_history
    FOR EACH STATEMENT EXECUTE FUNCTION v4.reject_dm01_data_head_history_mutation();

-- Canonical live Operational Successor Head. Workspace JSON is migration
-- evidence and cannot select the accepted candidate after this relation exists.
CREATE TABLE v4.operational_research_heads (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    head_payload jsonb NOT NULL,
    head_bytes bytea NOT NULL,
    head_sha256 char(64) NOT NULL CHECK (head_sha256 ~ '^[0-9a-f]{64}$'),
    generation bigint NOT NULL CHECK (generation > 0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (head_payload->>'contract_id' = 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1'),
    CHECK (encode(sha256(head_bytes), 'hex') = head_sha256)
);

CREATE FUNCTION v4.guard_operational_research_head() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'V4_OPERATIONAL_HEAD_DELETE_FORBIDDEN';
    END IF;
    IF NEW.singleton IS DISTINCT FROM OLD.singleton
       OR NEW.generation <> OLD.generation + 1 THEN
        RAISE EXCEPTION 'V4_OPERATIONAL_HEAD_CAS_GENERATION_REQUIRED';
    END IF;
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END $$;

CREATE TRIGGER operational_research_head_cas
    BEFORE UPDATE OR DELETE ON v4.operational_research_heads
    FOR EACH ROW EXECUTE FUNCTION v4.guard_operational_research_head();

-- The table is intentionally empty until an explicitly authorized, exact
-- legacy-Head reconciliation imports the existing Head bytes. Never synthesize
-- an accepted Head from the workspace file during migration.

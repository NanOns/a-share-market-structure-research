-- V4-08 PIT sector membership baseline: append-only, revisioned, fail-closed.
CREATE TABLE v4.sector_membership_type_policy (
    registry_digest char(64) NOT NULL CHECK (registry_digest ~ '^[0-9a-f]{64}$'),
    sector_type text NOT NULL CHECK (sector_type IN ('INDUSTRY', 'THEME', 'STYLE', 'UNKNOWN')),
    formal_radar_allowed boolean NOT NULL,
    formal_sector_qualification_allowed boolean NOT NULL,
    formal_rotation_qualification_allowed boolean NOT NULL,
    contract_id text NOT NULL CHECK (contract_id = 'V4_08_SECTOR_TYPE_REGISTRY_V1'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (sector_type NOT IN ('STYLE', 'UNKNOWN') OR
       (NOT formal_radar_allowed AND NOT formal_sector_qualification_allowed AND NOT formal_rotation_qualification_allowed)),
    PRIMARY KEY (registry_digest, sector_type)
);

INSERT INTO v4.sector_membership_type_policy
    (registry_digest, sector_type, formal_radar_allowed, formal_sector_qualification_allowed, formal_rotation_qualification_allowed, contract_id)
VALUES
    ('4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743', 'INDUSTRY', true, true, true, 'V4_08_SECTOR_TYPE_REGISTRY_V1'),
    ('4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743', 'THEME', true, true, true, 'V4_08_SECTOR_TYPE_REGISTRY_V1'),
    ('4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743', 'STYLE', false, false, false, 'V4_08_SECTOR_TYPE_REGISTRY_V1'),
    ('4a8d1c8e6574bfa9985e7980ca83337b7a14bed54bfbbace9e817d44b2076743', 'UNKNOWN', false, false, false, 'V4_08_SECTOR_TYPE_REGISTRY_V1');

CREATE TABLE v4.sector_membership_source_revisions (
    source_revision_id text PRIMARY KEY,
    source_contract_id text NOT NULL CHECK (source_contract_id = 'V4_08_SECTOR_MEMBERSHIP_SOURCE_V1'),
    source_digest char(64) NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
    source_file_digests jsonb NOT NULL CHECK (jsonb_typeof(source_file_digests) = 'object'),
    observed_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL,
    system_available_at timestamptz NOT NULL,
    provider_available_at timestamptz,
    membership_asof_date date,
    membership_basis text NOT NULL CHECK (membership_basis IN ('PIT_OBSERVED', 'CURRENT_TDX_MEMBERSHIP', 'CURRENT_MEMBERSHIP_REPLAY', 'DERIVED_PARENT_MEMBERSHIP')),
    supersedes_revision_id text REFERENCES v4.sector_membership_source_revisions(source_revision_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ingested_at >= observed_at),
    CHECK (system_available_at >= observed_at),
    CHECK (membership_basis <> 'PIT_OBSERVED' OR (provider_available_at IS NOT NULL AND membership_asof_date IS NOT NULL))
);
CREATE UNIQUE INDEX ux_v4_sector_membership_revision_no_fork
    ON v4.sector_membership_source_revisions (supersedes_revision_id)
    WHERE supersedes_revision_id IS NOT NULL;

CREATE TABLE v4.sector_membership_snapshots (
    snapshot_id char(64) PRIMARY KEY CHECK (snapshot_id ~ '^[0-9a-f]{64}$'),
    target_trade_date date NOT NULL,
    cutoff timestamptz NOT NULL,
    sector_type_registry_digest char(64) NOT NULL CHECK (sector_type_registry_digest ~ '^[0-9a-f]{64}$'),
    source_revision_id text NOT NULL REFERENCES v4.sector_membership_source_revisions(source_revision_id),
    source_digest char(64) NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
    source_file_digests jsonb NOT NULL CHECK (jsonb_typeof(source_file_digests) = 'object'),
    membership_basis text NOT NULL CHECK (membership_basis IN ('PIT_OBSERVED', 'CURRENT_TDX_MEMBERSHIP', 'CURRENT_MEMBERSHIP_REPLAY', 'DERIVED_PARENT_MEMBERSHIP')),
    membership_quality text NOT NULL,
    pit_observed boolean NOT NULL,
    historical_backtest_safe boolean NOT NULL,
    row_count integer NOT NULL CHECK (row_count >= 0),
    supersedes_snapshot_id char(64) REFERENCES v4.sector_membership_snapshots(snapshot_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (pit_observed = (membership_basis = 'PIT_OBSERVED')),
    CHECK (historical_backtest_safe = (membership_basis = 'PIT_OBSERVED'))
);
CREATE UNIQUE INDEX ux_v4_sector_membership_snapshot_no_fork
    ON v4.sector_membership_snapshots (supersedes_snapshot_id)
    WHERE supersedes_snapshot_id IS NOT NULL;

CREATE TABLE v4.sector_membership_facts (
    membership_fact_id char(64) PRIMARY KEY CHECK (membership_fact_id ~ '^[0-9a-f]{64}$'),
    snapshot_id char(64) NOT NULL REFERENCES v4.sector_membership_snapshots(snapshot_id),
    source_revision_id text NOT NULL REFERENCES v4.sector_membership_source_revisions(source_revision_id),
    sector_id text NOT NULL,
    sector_code text NOT NULL,
    sector_name text NOT NULL,
    sector_type text NOT NULL CHECK (sector_type IN ('INDUSTRY', 'THEME', 'STYLE', 'UNKNOWN')),
    source_sector_type text NOT NULL,
    source_security_key text NOT NULL,
    security_id text,
    identity_status text NOT NULL CHECK (identity_status IN ('MAPPED', 'UNKNOWN')),
    target_trade_date date NOT NULL,
    membership_asof_date date,
    cutoff timestamptz NOT NULL,
    membership_basis text NOT NULL CHECK (membership_basis IN ('PIT_OBSERVED', 'CURRENT_TDX_MEMBERSHIP', 'CURRENT_MEMBERSHIP_REPLAY', 'DERIVED_PARENT_MEMBERSHIP')),
    membership_quality text NOT NULL,
    pit_observed boolean NOT NULL,
    historical_backtest_safe boolean NOT NULL,
    supersedes_revision_id text REFERENCES v4.sector_membership_source_revisions(source_revision_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((identity_status = 'MAPPED' AND security_id IS NOT NULL) OR (identity_status = 'UNKNOWN' AND security_id IS NULL)),
    CHECK (pit_observed = (membership_basis = 'PIT_OBSERVED')),
    CHECK (historical_backtest_safe = (membership_basis = 'PIT_OBSERVED')),
    UNIQUE (snapshot_id, sector_id, source_security_key)
);
CREATE UNIQUE INDEX ux_v4_sector_membership_fact_identity
    ON v4.sector_membership_facts (snapshot_id, sector_id, security_id)
    WHERE security_id IS NOT NULL;

CREATE FUNCTION v4.check_sector_membership_fact_temporal_binding() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE snapshot_row v4.sector_membership_snapshots%ROWTYPE;
DECLARE revision_row v4.sector_membership_source_revisions%ROWTYPE;
BEGIN
    SELECT * INTO STRICT snapshot_row FROM v4.sector_membership_snapshots WHERE snapshot_id = NEW.snapshot_id;
    SELECT * INTO STRICT revision_row FROM v4.sector_membership_source_revisions WHERE source_revision_id = NEW.source_revision_id;
    IF NEW.target_trade_date <> snapshot_row.target_trade_date
       OR NEW.cutoff <> snapshot_row.cutoff
       OR NEW.membership_basis <> snapshot_row.membership_basis
       OR NEW.pit_observed <> snapshot_row.pit_observed
       OR NEW.historical_backtest_safe <> snapshot_row.historical_backtest_safe
       OR NEW.source_revision_id <> snapshot_row.source_revision_id THEN
        RAISE EXCEPTION 'sector membership fact does not match snapshot header';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM v4.sector_membership_type_policy
        WHERE registry_digest = snapshot_row.sector_type_registry_digest AND sector_type = NEW.sector_type
    ) THEN
        RAISE EXCEPTION 'sector type is absent from the snapshot type-registry revision';
    END IF;
    IF revision_row.system_available_at > snapshot_row.cutoff THEN
        RAISE EXCEPTION 'sector membership source revision unavailable at snapshot cutoff';
    END IF;
    IF NEW.membership_basis = 'PIT_OBSERVED'
       AND (revision_row.provider_available_at IS NULL OR revision_row.provider_available_at > snapshot_row.cutoff
            OR NEW.membership_asof_date IS NULL OR NEW.membership_asof_date > NEW.target_trade_date) THEN
        RAISE EXCEPTION 'PIT membership source/effective date is not available at target cutoff';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER tr_v4_sector_membership_fact_temporal_binding
    BEFORE INSERT ON v4.sector_membership_facts
    FOR EACH ROW EXECUTE FUNCTION v4.check_sector_membership_fact_temporal_binding();

CREATE TRIGGER tr_v4_sector_membership_type_policy_append_only BEFORE UPDATE OR DELETE ON v4.sector_membership_type_policy
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER tr_v4_sector_membership_source_revisions_append_only BEFORE UPDATE OR DELETE ON v4.sector_membership_source_revisions
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER tr_v4_sector_membership_snapshots_append_only BEFORE UPDATE OR DELETE ON v4.sector_membership_snapshots
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();
CREATE TRIGGER tr_v4_sector_membership_facts_append_only BEFORE UPDATE OR DELETE ON v4.sector_membership_facts
    FOR EACH ROW EXECUTE FUNCTION v4.reject_append_only_mutation();

CREATE VIEW v4.formal_sector_membership AS
SELECT f.*
FROM v4.sector_membership_facts AS f
JOIN v4.sector_membership_snapshots AS s USING (snapshot_id)
JOIN v4.sector_membership_type_policy AS p
  ON p.registry_digest = s.sector_type_registry_digest AND p.sector_type = f.sector_type
WHERE p.formal_radar_allowed
  AND p.formal_sector_qualification_allowed
  AND p.formal_rotation_qualification_allowed
  AND f.membership_basis = 'PIT_OBSERVED'
  AND f.pit_observed
  AND f.historical_backtest_safe
  AND f.identity_status = 'MAPPED';

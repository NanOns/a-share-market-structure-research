-- V4-08 R2 repairs the immutable R1 schema without rewriting migrations 016/017.
-- One snapshot remains one basis; derived-parent lineage binds its raw child snapshot.

ALTER TABLE v4.sector_membership_source_revisions
    ADD COLUMN source_bytes_digest char(64),
    ADD COLUMN temporal_evidence_digest char(64),
    ADD COLUMN temporal_evidence jsonb,
    ADD COLUMN provider_available_at_basis text,
    ADD COLUMN membership_asof_basis text,
    ADD COLUMN revision_quality text;

ALTER TABLE v4.sector_membership_snapshots
    ADD COLUMN parent_snapshot_id char(64) REFERENCES v4.sector_membership_snapshots(snapshot_id),
    ADD COLUMN snapshot_lineage_role text NOT NULL DEFAULT 'LEGACY_R1';

DO $$
DECLARE constraint_row record;
BEGIN
    FOR constraint_row IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'v4.sector_membership_snapshots'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%historical_backtest_safe%membership_basis%'
    LOOP
        EXECUTE format('ALTER TABLE v4.sector_membership_snapshots DROP CONSTRAINT %I', constraint_row.conname);
    END LOOP;
    FOR constraint_row IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'v4.sector_membership_facts'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%historical_backtest_safe%membership_basis%'
    LOOP
        EXECUTE format('ALTER TABLE v4.sector_membership_facts DROP CONSTRAINT %I', constraint_row.conname);
    END LOOP;
END;
$$;

ALTER TABLE v4.sector_membership_snapshots
    ADD CONSTRAINT ck_v4_sector_snapshot_safe_requires_accepted_pit
    CHECK (NOT historical_backtest_safe OR
           (membership_basis = 'PIT_OBSERVED' AND membership_quality = 'PIT_OBSERVED_ACCEPTED')),
    ADD CONSTRAINT ck_v4_sector_snapshot_basis_owns_lineage_role
    CHECK (
        (membership_basis = 'CURRENT_TDX_MEMBERSHIP' AND snapshot_lineage_role = 'RAW_CURRENT') OR
        (membership_basis = 'CURRENT_MEMBERSHIP_REPLAY' AND snapshot_lineage_role = 'RAW_REPLAY') OR
        (membership_basis = 'DERIVED_PARENT_MEMBERSHIP' AND snapshot_lineage_role IN ('DERIVED_PARENT', 'DERIVED_PARENT_REPLAY')) OR
        (membership_basis = 'PIT_OBSERVED' AND snapshot_lineage_role = 'FORWARD_PIT_CANDIDATE') OR
        snapshot_lineage_role = 'LEGACY_R1'
    );

ALTER TABLE v4.sector_membership_facts
    ADD CONSTRAINT ck_v4_sector_fact_safe_requires_accepted_identity
    CHECK (NOT historical_backtest_safe OR
           (membership_basis = 'PIT_OBSERVED'
            AND membership_quality = 'PIT_OBSERVED_ACCEPTED'
            AND identity_status = 'MAPPED' AND security_id IS NOT NULL));

ALTER TABLE v4.sector_membership_source_revisions
    ADD CONSTRAINT ck_v4_sector_revision_source_bytes_digest
    CHECK (source_bytes_digest IS NULL OR source_bytes_digest ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT ck_v4_sector_revision_temporal_digest
    CHECK (temporal_evidence_digest IS NULL OR temporal_evidence_digest ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT ck_v4_sector_revision_temporal_object
    CHECK (temporal_evidence IS NULL OR jsonb_typeof(temporal_evidence) = 'object'),
    ADD CONSTRAINT ck_v4_sector_revision_quality
    CHECK (revision_quality IS NULL OR revision_quality IN (
        'PIT_OBSERVED_ACCEPTED', 'SOURCE_TIME_UNVERIFIED', 'CURRENT_TDX_DIAGNOSTIC',
        'CURRENT_REPLAY_DIAGNOSTIC', 'DERIVED_PARENT_DIAGNOSTIC', 'UNKNOWN_IDENTITY',
        'UNKNOWN_SECTOR_TYPE'
    ));

CREATE FUNCTION v4.check_sector_membership_revision_metadata_r2() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_bytes_digest IS NULL OR NEW.temporal_evidence_digest IS NULL
       OR NEW.temporal_evidence IS NULL OR NEW.revision_quality IS NULL
       OR NEW.provider_available_at_basis IS NULL OR NEW.membership_asof_basis IS NULL THEN
        RAISE EXCEPTION 'R2 source revision requires immutable byte and temporal evidence metadata';
    END IF;
    IF NEW.source_bytes_digest !~ '^[0-9a-f]{64}$' OR NEW.temporal_evidence_digest !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'R2 source revision digest must be lowercase SHA-256';
    END IF;
    IF NEW.membership_basis = 'PIT_OBSERVED'
       AND (NEW.provider_available_at IS NULL OR NEW.membership_asof_date IS NULL
            OR NEW.provider_available_at_basis = 'NOT_APPLICABLE'
            OR NEW.membership_asof_basis = 'NOT_APPLICABLE') THEN
        RAISE EXCEPTION 'PIT source revision requires availability and exact membership-asof evidence';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_v4_sector_membership_revision_metadata_r2
    BEFORE INSERT ON v4.sector_membership_source_revisions
    FOR EACH ROW EXECUTE FUNCTION v4.check_sector_membership_revision_metadata_r2();

CREATE FUNCTION v4.check_sector_membership_snapshot_lineage_r2() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE parent_row v4.sector_membership_snapshots%ROWTYPE;
BEGIN
    IF NEW.membership_basis = 'DERIVED_PARENT_MEMBERSHIP' THEN
        IF NEW.parent_snapshot_id IS NULL THEN
            RAISE EXCEPTION 'derived-parent snapshot must reference its raw child snapshot';
        END IF;
        SELECT * INTO STRICT parent_row FROM v4.sector_membership_snapshots
         WHERE snapshot_id = NEW.parent_snapshot_id;
        IF parent_row.membership_basis NOT IN ('CURRENT_TDX_MEMBERSHIP', 'CURRENT_MEMBERSHIP_REPLAY')
           OR parent_row.target_trade_date <> NEW.target_trade_date
           OR parent_row.source_digest <> NEW.source_digest
           OR parent_row.source_file_digests <> NEW.source_file_digests THEN
            RAISE EXCEPTION 'derived-parent snapshot does not bind a matching raw child lineage';
        END IF;
    ELSIF NEW.parent_snapshot_id IS NOT NULL THEN
        RAISE EXCEPTION 'only derived-parent snapshots may set parent_snapshot_id';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_v4_sector_membership_snapshot_lineage_r2
    BEFORE INSERT ON v4.sector_membership_snapshots
    FOR EACH ROW EXECUTE FUNCTION v4.check_sector_membership_snapshot_lineage_r2();

CREATE OR REPLACE FUNCTION v4.check_sector_membership_fact_temporal_binding() RETURNS trigger
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
            OR NEW.membership_asof_date IS NULL OR NEW.membership_asof_date <> NEW.target_trade_date) THEN
        RAISE EXCEPTION 'PIT membership availability or exact effective date is invalid';
    END IF;
    IF NEW.historical_backtest_safe AND
       (NEW.membership_basis <> 'PIT_OBSERVED'
        OR NEW.membership_quality <> 'PIT_OBSERVED_ACCEPTED'
        OR revision_row.revision_quality <> 'PIT_OBSERVED_ACCEPTED'
        OR revision_row.temporal_evidence IS NULL
        OR NEW.identity_status <> 'MAPPED' OR NEW.security_id IS NULL
        OR coalesce((revision_row.temporal_evidence->>'revision_chain_valid')::boolean, false) IS NOT TRUE) THEN
        RAISE EXCEPTION 'historical safety requires accepted PIT, temporal evidence, identity and revision chain';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE VIEW v4.formal_sector_membership AS
SELECT f.*
FROM v4.sector_membership_facts AS f
JOIN v4.sector_membership_snapshots AS s USING (snapshot_id)
JOIN v4.sector_membership_source_revisions AS r ON r.source_revision_id = f.source_revision_id
JOIN v4.sector_membership_type_policy AS p
  ON p.registry_digest = s.sector_type_registry_digest AND p.sector_type = f.sector_type
WHERE p.formal_radar_allowed
  AND p.formal_sector_qualification_allowed
  AND p.formal_rotation_qualification_allowed
  AND f.sector_type IN ('INDUSTRY', 'THEME')
  AND f.membership_basis = 'PIT_OBSERVED'
  AND s.membership_basis = 'PIT_OBSERVED'
  AND f.membership_quality = 'PIT_OBSERVED_ACCEPTED'
  AND s.membership_quality = 'PIT_OBSERVED_ACCEPTED'
  AND r.revision_quality = 'PIT_OBSERVED_ACCEPTED'
  AND r.source_bytes_digest IS NOT NULL
  AND r.temporal_evidence_digest IS NOT NULL
  AND r.temporal_evidence IS NOT NULL
  AND r.provider_available_at_basis NOT IN ('UNVERIFIED', 'NOT_APPLICABLE')
  AND r.membership_asof_basis NOT IN ('UNVERIFIED', 'NOT_APPLICABLE')
  AND f.pit_observed AND s.pit_observed
  AND f.historical_backtest_safe AND s.historical_backtest_safe
  AND f.identity_status = 'MAPPED'
  AND f.security_id IS NOT NULL
  AND f.membership_asof_date = f.target_trade_date
  AND r.provider_available_at IS NOT NULL
  AND r.provider_available_at <= f.cutoff
  AND r.system_available_at <= f.cutoff;

CREATE OR REPLACE VIEW v4.sector_membership_fact_evidence AS
SELECT
    f.membership_fact_id,
    f.snapshot_id,
    f.source_revision_id,
    f.sector_id,
    f.sector_code,
    f.sector_name,
    f.sector_type,
    f.source_sector_type,
    f.security_id,
    f.source_security_key,
    f.target_trade_date,
    f.membership_asof_date,
    r.observed_at,
    r.ingested_at,
    r.system_available_at,
    r.provider_available_at,
    f.cutoff,
    r.source_digest,
    r.source_file_digests,
    s.sector_type_registry_digest,
    f.membership_basis,
    f.membership_quality,
    f.pit_observed,
    f.historical_backtest_safe,
    f.supersedes_revision_id,
    r.created_at AS source_revision_created_at,
    f.created_at AS fact_created_at,
    r.source_bytes_digest,
    r.temporal_evidence_digest,
    r.temporal_evidence,
    r.provider_available_at_basis,
    r.membership_asof_basis,
    r.revision_quality,
    s.parent_snapshot_id,
    s.snapshot_lineage_role
FROM v4.sector_membership_facts AS f
JOIN v4.sector_membership_snapshots AS s ON s.snapshot_id = f.snapshot_id
JOIN v4.sector_membership_source_revisions AS r ON r.source_revision_id = f.source_revision_id;


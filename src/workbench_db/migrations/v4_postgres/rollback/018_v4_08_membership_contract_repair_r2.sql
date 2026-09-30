DROP VIEW IF EXISTS v4.formal_sector_membership;
DROP VIEW IF EXISTS v4.sector_membership_fact_evidence;
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

DROP TRIGGER IF EXISTS tr_v4_sector_membership_snapshot_lineage_r2 ON v4.sector_membership_snapshots;
DROP TRIGGER IF EXISTS tr_v4_sector_membership_revision_metadata_r2 ON v4.sector_membership_source_revisions;
DROP FUNCTION IF EXISTS v4.check_sector_membership_snapshot_lineage_r2();
DROP FUNCTION IF EXISTS v4.check_sector_membership_revision_metadata_r2();

ALTER TABLE v4.sector_membership_facts
    DROP CONSTRAINT IF EXISTS ck_v4_sector_fact_safe_requires_accepted_identity;
ALTER TABLE v4.sector_membership_snapshots
    DROP CONSTRAINT IF EXISTS ck_v4_sector_snapshot_safe_requires_accepted_pit,
    DROP CONSTRAINT IF EXISTS ck_v4_sector_snapshot_basis_owns_lineage_role;
ALTER TABLE v4.sector_membership_source_revisions
    DROP CONSTRAINT IF EXISTS ck_v4_sector_revision_source_bytes_digest,
    DROP CONSTRAINT IF EXISTS ck_v4_sector_revision_temporal_digest,
    DROP CONSTRAINT IF EXISTS ck_v4_sector_revision_temporal_object,
    DROP CONSTRAINT IF EXISTS ck_v4_sector_revision_quality;

ALTER TABLE v4.sector_membership_snapshots
    DROP COLUMN IF EXISTS snapshot_lineage_role,
    DROP COLUMN IF EXISTS parent_snapshot_id;
ALTER TABLE v4.sector_membership_source_revisions
    DROP COLUMN IF EXISTS revision_quality,
    DROP COLUMN IF EXISTS membership_asof_basis,
    DROP COLUMN IF EXISTS provider_available_at_basis,
    DROP COLUMN IF EXISTS temporal_evidence,
    DROP COLUMN IF EXISTS temporal_evidence_digest,
    DROP COLUMN IF EXISTS source_bytes_digest;

CREATE VIEW v4.sector_membership_fact_evidence AS
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
    f.created_at AS fact_created_at
FROM v4.sector_membership_facts AS f
JOIN v4.sector_membership_snapshots AS s ON s.snapshot_id = f.snapshot_id
JOIN v4.sector_membership_source_revisions AS r ON r.source_revision_id = f.source_revision_id;

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
            OR NEW.membership_asof_date IS NULL OR NEW.membership_asof_date > NEW.target_trade_date) THEN
        RAISE EXCEPTION 'PIT membership source/effective date is not available at target cutoff';
    END IF;
    RETURN NEW;
END;
$$;


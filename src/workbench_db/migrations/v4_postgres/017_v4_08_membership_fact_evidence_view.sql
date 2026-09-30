-- Read model that exposes the complete contract fields on each fact through
-- its immutable source revision and snapshot bindings.
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

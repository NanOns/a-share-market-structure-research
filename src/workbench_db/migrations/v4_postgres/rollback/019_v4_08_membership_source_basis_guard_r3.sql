-- Remove only R3 objects and restore the exact R2 formal view.
DROP TRIGGER tr_v4_sector_fact_source_basis_r3 ON v4.sector_membership_facts;
DROP TRIGGER tr_v4_sector_snapshot_source_basis_r3 ON v4.sector_membership_snapshots;
DROP FUNCTION v4.check_sector_membership_fact_source_basis_r3();
DROP FUNCTION v4.check_sector_membership_snapshot_source_basis_r3();
ALTER TABLE v4.sector_membership_source_revisions DROP CONSTRAINT ck_v4_sector_revision_basis_quality_r3;
ALTER TABLE v4.sector_membership_snapshots DROP CONSTRAINT ck_v4_sector_snapshot_basis_quality_r3;
ALTER TABLE v4.sector_membership_facts DROP CONSTRAINT ck_v4_sector_fact_basis_quality_r3;
DROP FUNCTION v4.sector_membership_basis_quality_compatible_r3(text,text);
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


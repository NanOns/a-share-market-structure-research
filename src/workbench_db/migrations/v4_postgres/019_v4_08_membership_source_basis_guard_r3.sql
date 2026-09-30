-- R3 is append-only relative to migrations 016/017/018.
CREATE FUNCTION v4.sector_membership_basis_quality_compatible_r3(basis text, quality text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE quality
      WHEN 'PIT_OBSERVED_ACCEPTED' THEN basis = 'PIT_OBSERVED'
      WHEN 'CURRENT_TDX_DIAGNOSTIC' THEN basis = 'CURRENT_TDX_MEMBERSHIP'
      WHEN 'CURRENT_REPLAY_DIAGNOSTIC' THEN basis = 'CURRENT_MEMBERSHIP_REPLAY'
      WHEN 'DERIVED_PARENT_DIAGNOSTIC' THEN basis = 'DERIVED_PARENT_MEMBERSHIP'
      ELSE true END;
$$;

ALTER TABLE v4.sector_membership_source_revisions ADD CONSTRAINT ck_v4_sector_revision_basis_quality_r3
 CHECK (v4.sector_membership_basis_quality_compatible_r3(membership_basis, revision_quality));
ALTER TABLE v4.sector_membership_snapshots ADD CONSTRAINT ck_v4_sector_snapshot_basis_quality_r3
 CHECK (v4.sector_membership_basis_quality_compatible_r3(membership_basis, membership_quality));
ALTER TABLE v4.sector_membership_facts ADD CONSTRAINT ck_v4_sector_fact_basis_quality_r3
 CHECK (v4.sector_membership_basis_quality_compatible_r3(membership_basis, membership_quality));

CREATE FUNCTION v4.check_sector_membership_snapshot_source_basis_r3() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE revision_row v4.sector_membership_source_revisions%ROWTYPE;
BEGIN
 SELECT * INTO STRICT revision_row FROM v4.sector_membership_source_revisions
 WHERE source_revision_id = NEW.source_revision_id;
 IF revision_row.membership_basis <> NEW.membership_basis THEN
   RAISE EXCEPTION 'R3 source revision basis does not match snapshot basis';
 END IF;
 IF revision_row.source_digest <> NEW.source_digest OR revision_row.source_file_digests <> NEW.source_file_digests THEN
   RAISE EXCEPTION 'R3 snapshot source digests do not match source revision';
 END IF;
 IF NEW.membership_basis = 'PIT_OBSERVED' AND
    (revision_row.membership_asof_date IS DISTINCT FROM NEW.target_trade_date
     OR (revision_row.observed_at AT TIME ZONE 'Asia/Shanghai')::date <> NEW.target_trade_date) THEN
   RAISE EXCEPTION 'R3 PIT snapshot requires exact target-day source observation and asof';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER tr_v4_sector_snapshot_source_basis_r3 BEFORE INSERT ON v4.sector_membership_snapshots
 FOR EACH ROW EXECUTE FUNCTION v4.check_sector_membership_snapshot_source_basis_r3();

CREATE FUNCTION v4.check_sector_membership_fact_source_basis_r3() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM v4.sector_membership_source_revisions r
   JOIN v4.sector_membership_snapshots s ON s.source_revision_id = r.source_revision_id
   WHERE s.snapshot_id=NEW.snapshot_id AND r.source_revision_id=NEW.source_revision_id
     AND r.membership_basis=NEW.membership_basis AND s.membership_basis=NEW.membership_basis) THEN
   RAISE EXCEPTION 'R3 source revision snapshot fact basis mismatch';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER tr_v4_sector_fact_source_basis_r3 BEFORE INSERT ON v4.sector_membership_facts
 FOR EACH ROW EXECUTE FUNCTION v4.check_sector_membership_fact_source_basis_r3();

CREATE OR REPLACE VIEW v4.formal_sector_membership AS
SELECT f.* FROM v4.sector_membership_facts f
JOIN v4.sector_membership_snapshots s USING(snapshot_id)
JOIN v4.sector_membership_source_revisions r ON r.source_revision_id=f.source_revision_id
JOIN v4.sector_membership_type_policy p ON p.registry_digest=s.sector_type_registry_digest AND p.sector_type=f.sector_type
WHERE p.formal_radar_allowed AND p.formal_sector_qualification_allowed AND p.formal_rotation_qualification_allowed
 AND f.sector_type IN ('INDUSTRY','THEME')
 AND r.membership_basis='PIT_OBSERVED' AND s.membership_basis='PIT_OBSERVED' AND f.membership_basis='PIT_OBSERVED'
 AND s.source_revision_id=r.source_revision_id
 AND r.revision_quality='PIT_OBSERVED_ACCEPTED' AND s.membership_quality='PIT_OBSERVED_ACCEPTED' AND f.membership_quality='PIT_OBSERVED_ACCEPTED'
 AND r.source_bytes_digest IS NOT NULL AND r.temporal_evidence_digest IS NOT NULL AND r.temporal_evidence IS NOT NULL
 AND coalesce((r.temporal_evidence->>'revision_chain_valid')::boolean,false)
 AND r.provider_available_at_basis NOT IN ('UNVERIFIED','NOT_APPLICABLE')
 AND r.membership_asof_basis NOT IN ('UNVERIFIED','NOT_APPLICABLE')
 AND f.pit_observed AND s.pit_observed AND f.historical_backtest_safe AND s.historical_backtest_safe
 AND f.identity_status='MAPPED' AND f.security_id IS NOT NULL
 AND f.membership_asof_date=f.target_trade_date AND r.membership_asof_date=f.target_trade_date
 AND (r.observed_at AT TIME ZONE 'Asia/Shanghai')::date=f.target_trade_date
 AND r.provider_available_at IS NOT NULL AND r.provider_available_at<=f.cutoff AND r.system_available_at<=f.cutoff;

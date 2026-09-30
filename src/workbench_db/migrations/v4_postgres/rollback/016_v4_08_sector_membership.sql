-- Isolated rollback for an empty V4-08 candidate schema only.
DROP VIEW IF EXISTS v4.formal_sector_membership;
DROP TABLE IF EXISTS v4.sector_membership_facts;
DROP TABLE IF EXISTS v4.sector_membership_snapshots;
DROP TABLE IF EXISTS v4.sector_membership_source_revisions;
DROP TABLE IF EXISTS v4.sector_membership_type_policy;
DROP FUNCTION IF EXISTS v4.check_sector_membership_fact_temporal_binding();

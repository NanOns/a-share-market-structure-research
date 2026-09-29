-- Isolated rollback for an empty V4-06 candidate schema only. Production
-- historical enrichment rows must never be deleted or rewritten.
DROP TABLE IF EXISTS v4.stock_profile_enrichments;
DROP TABLE IF EXISTS v4.supplemental_enrichment_manifests;

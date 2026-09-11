-- M8C post-audit V1.1 evidence fields.
-- Existing V1.0 rows remain immutable and are explicitly marked pending review.
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS contract_id VARCHAR;
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS rule_verified BOOLEAN;
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS source_sha256 VARCHAR;
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS audit_status VARCHAR;
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS audit_reason VARCHAR;
ALTER TABLE limit_rule_versions ADD COLUMN IF NOT EXISTS audited_at TIMESTAMP;
UPDATE limit_rule_versions
   SET contract_id=COALESCE(contract_id,'LIMIT_RULES_V1_0'),
       rule_verified=COALESCE(rule_verified,FALSE),
       audit_status=COALESCE(audit_status,'PENDING_REVIEW'),
       audit_reason=COALESCE(audit_reason,'PRE_V11_RULE_ROW')
 WHERE contract_id IS NULL OR rule_verified IS NULL OR audit_status IS NULL;

ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS source_snapshot_id VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS quote_capability VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS reference_status VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS reference_basis VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS exchange VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS board VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS risk_status VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS listing_phase VARCHAR;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS ex_rights_reference_unknown BOOLEAN;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS rule_verified BOOLEAN;
ALTER TABLE market_reference_daily ADD COLUMN IF NOT EXISTS source_rule_sha256 VARCHAR;
UPDATE market_reference_daily
   SET quote_capability=COALESCE(quote_capability,CASE WHEN status_known THEN 'UNKNOWN' ELSE 'UNKNOWN' END),
       reference_status=COALESCE(reference_status,'UNKNOWN'),
       reference_basis=COALESCE(reference_basis,'RAW_PREV_CLOSE_APPROXIMATE'),
       ex_rights_reference_unknown=COALESCE(ex_rights_reference_unknown,TRUE),
       rule_verified=COALESCE(rule_verified,FALSE)
 WHERE quote_capability IS NULL OR reference_status IS NULL OR reference_basis IS NULL
    OR ex_rights_reference_unknown IS NULL OR rule_verified IS NULL;

ALTER TABLE security_metadata_versions ADD COLUMN IF NOT EXISTS risk_status VARCHAR;
ALTER TABLE security_metadata_versions ADD COLUMN IF NOT EXISTS listing_phase VARCHAR;
ALTER TABLE security_metadata_versions ADD COLUMN IF NOT EXISTS metadata_confidence VARCHAR;
ALTER TABLE security_metadata_versions ADD COLUMN IF NOT EXISTS source_snapshot_id VARCHAR;
UPDATE security_metadata_versions
   SET risk_status=COALESCE(risk_status,'UNKNOWN'),
       listing_phase=COALESCE(listing_phase,'UNKNOWN'),
       metadata_confidence=COALESCE(metadata_confidence,'UNKNOWN')
 WHERE risk_status IS NULL OR listing_phase IS NULL OR metadata_confidence IS NULL;

CREATE TABLE IF NOT EXISTS analysis_snapshot_audit_status (
    snapshot_id VARCHAR PRIMARY KEY REFERENCES analysis_snapshots(snapshot_id),
    audit_status VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);

INSERT INTO analysis_snapshot_audit_status
SELECT s.snapshot_id, 'BLOCKED', 'M8C_POST_AUDIT_PENDING_REBUILD', current_timestamp
  FROM analysis_snapshots s
 WHERE EXISTS (
       SELECT 1 FROM analysis_snapshot_entries e
        WHERE e.snapshot_id=s.snapshot_id
          AND e.domain IN ('market_cycle','limit_ladder','limit_promotion')
   )
   AND NOT EXISTS (
       SELECT 1 FROM analysis_snapshot_audit_status a WHERE a.snapshot_id=s.snapshot_id
   );

CREATE TABLE IF NOT EXISTS m8c_rule_audit_events (
    rule_id VARCHAR NOT NULL,
    content_sha256 VARCHAR NOT NULL,
    contract_id VARCHAR NOT NULL,
    audit_status VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    source_ref VARCHAR NOT NULL,
    audited_at TIMESTAMP NOT NULL,
    PRIMARY KEY (rule_id, content_sha256)
);

-- FOCUS_TARGET_DATA_AUDIT_SCHEMA_V1; reviewed terminal-state evidence.
CREATE TABLE IF NOT EXISTS workbench.focus_target_data_audits (
    audit_id text PRIMARY KEY,
    entity_type text NOT NULL CHECK (entity_type IN ('STOCK','SECTOR')),
    entity_id text NOT NULL,
    target_trade_date date NOT NULL,
    audit_kind text NOT NULL CHECK
      (audit_kind IN ('CONFIRMED_SUSPENSION','CONFIRMED_DELISTING','FINAL_DATA_GAP')),
    target_source_identity_digest char(64) NOT NULL CHECK
      (target_source_identity_digest ~ '^[0-9a-f]{64}$'),
    normalized_artifact_sha256 char(64) NOT NULL CHECK
      (normalized_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
    audited_by text NOT NULL CHECK (length(audited_by)>0),
    evidence jsonb NOT NULL CHECK (jsonb_typeof(evidence)='object'),
    audited_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (entity_type,entity_id,target_trade_date,audit_kind,
            target_source_identity_digest,normalized_artifact_sha256)
);
CREATE INDEX IF NOT EXISTS focus_target_data_audits_lookup_idx
  ON workbench.focus_target_data_audits(entity_type,entity_id,target_trade_date,audit_kind);

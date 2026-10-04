PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS storage_identity (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 environment TEXT NOT NULL CHECK(environment IN ('REAL','ACTIVATION_SIMULATION')),
 evidence_origin TEXT NOT NULL CHECK(evidence_origin IN ('PIT_OBSERVED','ACTIVATION_SIMULATION')),
 CHECK((environment='REAL' AND evidence_origin='PIT_OBSERVED') OR
       (environment='ACTIVATION_SIMULATION' AND evidence_origin='ACTIVATION_SIMULATION'))
);
CREATE TABLE IF NOT EXISTS facts (
 kind TEXT NOT NULL, id TEXT NOT NULL, namespace TEXT NOT NULL CHECK(namespace='SHADOW_V4'),
 execution_mode TEXT NOT NULL CHECK(execution_mode='SHADOW'),
 evidence_origin TEXT NOT NULL CHECK(evidence_origin IN ('PIT_OBSERVED','ACTIVATION_SIMULATION')),
 payload TEXT NOT NULL CHECK(json_valid(payload)), digest TEXT NOT NULL,
 PRIMARY KEY(kind,id),
 CHECK(json_extract(payload,'$.namespace') IS 'SHADOW_V4'),
 CHECK(json_extract(payload,'$.execution_mode') IS 'SHADOW'),
 CHECK(json_extract(payload,'$.evidence_origin') IS evidence_origin)
);
CREATE TRIGGER IF NOT EXISTS origin_guard BEFORE INSERT ON facts BEGIN
 SELECT CASE WHEN NEW.evidence_origin IS NOT (SELECT evidence_origin FROM storage_identity WHERE singleton=1)
 THEN RAISE(ABORT,'STORAGE_ORIGIN_MISMATCH') END;
END;
CREATE TRIGGER IF NOT EXISTS no_fact_update BEFORE UPDATE ON facts BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS no_fact_delete BEFORE DELETE ON facts BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
CREATE TRIGGER IF NOT EXISTS no_storage_update BEFORE UPDATE ON storage_identity BEGIN SELECT RAISE(ABORT,'IMMUTABLE_STORAGE'); END;
CREATE TRIGGER IF NOT EXISTS no_storage_delete BEFORE DELETE ON storage_identity BEGIN SELECT RAISE(ABORT,'IMMUTABLE_STORAGE'); END;
CREATE UNIQUE INDEX IF NOT EXISTS unique_original_event ON facts(json_extract(payload,'$.logical_event_id')) WHERE kind='enrollment';
CREATE UNIQUE INDEX IF NOT EXISTS unique_slot_revision ON facts(json_extract(payload,'$.slot_id'),json_extract(payload,'$.revision')) WHERE kind='slot';
CREATE UNIQUE INDEX IF NOT EXISTS unique_publication_revision ON facts(json_extract(payload,'$.slot_id'),json_extract(payload,'$.revision')) WHERE kind='publication';
CREATE UNIQUE INDEX IF NOT EXISTS unique_due ON facts(json_extract(payload,'$.enrollment_id'),json_extract(payload,'$.horizon')) WHERE kind='due';
CREATE UNIQUE INDEX IF NOT EXISTS unique_observation_revision ON facts(json_extract(payload,'$.logical_event_id'),json_extract(payload,'$.slot_id'),json_extract(payload,'$.revision')) WHERE kind='observation';
CREATE TRIGGER IF NOT EXISTS observation_lineage BEFORE INSERT ON facts WHEN NEW.kind='observation' BEGIN
 SELECT CASE WHEN json_extract(NEW.payload,'$.revision')>1 AND NOT EXISTS (
  SELECT 1 FROM facts prior WHERE prior.kind='observation'
  AND prior.id=json_extract(NEW.payload,'$.supersedes_observation')
  AND json_extract(prior.payload,'$.logical_event_id')=json_extract(NEW.payload,'$.logical_event_id')
  AND json_extract(prior.payload,'$.slot_id')=json_extract(NEW.payload,'$.slot_id')
  AND json_extract(prior.payload,'$.revision')<json_extract(NEW.payload,'$.revision')
 ) THEN RAISE(ABORT,'INVALID_OBSERVATION_PREDECESSOR') END;
 SELECT CASE WHEN json_extract(NEW.payload,'$.revision')=1 AND json_extract(NEW.payload,'$.supersedes_observation') IS NOT NULL
 THEN RAISE(ABORT,'ORIGINAL_HAS_PREDECESSOR') END;
END;
CREATE TABLE IF NOT EXISTS publication_heads (
 slot_id TEXT PRIMARY KEY, publication_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0)
);
CREATE TABLE IF NOT EXISTS activation_head (singleton INTEGER PRIMARY KEY CHECK(singleton=1), authority_id TEXT NOT NULL);

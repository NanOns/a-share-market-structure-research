-- Additive durable queue; immutable due/outcome facts remain the authority.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS settlement_queue_v2 (
 queue_key TEXT NOT NULL, evaluation_source_digest TEXT NOT NULL,
 due_kind TEXT NOT NULL DEFAULT 'due' CHECK(due_kind IN ('due','due_revision')), due_id TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('READY','CLAIMED','SETTLED','ACKED')),
 claim_owner TEXT, claim_version INTEGER NOT NULL DEFAULT 0,
 claim_at REAL, lease_until REAL, retry_count INTEGER NOT NULL DEFAULT 0,
 backlog_reason TEXT, outcome_kind TEXT NOT NULL DEFAULT 'outcome' CHECK(outcome_kind='outcome'),
 accepted_outcome_revision TEXT, ack_at REAL,
 PRIMARY KEY(queue_key,evaluation_source_digest),
 FOREIGN KEY(due_kind,due_id) REFERENCES facts(kind,id),
 FOREIGN KEY(outcome_kind,accepted_outcome_revision) REFERENCES facts(kind,id),
 CHECK(status NOT IN ('SETTLED','ACKED') OR accepted_outcome_revision IS NOT NULL),
 CHECK(status!='ACKED' OR ack_at IS NOT NULL)
);
CREATE TRIGGER IF NOT EXISTS queue_ack_guard BEFORE UPDATE ON settlement_queue_v2
WHEN NEW.status='ACKED' BEGIN
 SELECT CASE WHEN NOT EXISTS (
 SELECT 1 FROM facts o JOIN facts d ON d.kind=NEW.due_kind AND d.id=NEW.due_id
 WHERE o.kind='outcome' AND o.id=NEW.accepted_outcome_revision
 AND json_extract(o.payload,'$.evaluation_source_digest')=NEW.evaluation_source_digest
 AND json_extract(o.payload,'$.enrollment_id')=json_extract(d.payload,'$.enrollment_id')
 AND json_extract(o.payload,'$.horizon')=json_extract(d.payload,'$.horizon')
 AND json_extract(o.payload,'$.due_date')=json_extract(d.payload,'$.due_date')
 AND json_extract(o.payload,'$.frozen_t0')=json_extract(d.payload,'$.frozen_t0')
 ) THEN RAISE(ABORT,'QUEUE_RESULT_READBACK_MISMATCH') END;
END;
CREATE TRIGGER IF NOT EXISTS queue_identity_guard BEFORE UPDATE ON settlement_queue_v2 BEGIN
 SELECT CASE WHEN NEW.queue_key IS NOT OLD.queue_key OR NEW.evaluation_source_digest IS NOT OLD.evaluation_source_digest
 OR NEW.due_id IS NOT OLD.due_id OR OLD.status='ACKED'
 THEN RAISE(ABORT,'IMMUTABLE_QUEUE_IDENTITY_OR_ACK') END;
END;
CREATE TRIGGER IF NOT EXISTS queue_transition_guard BEFORE UPDATE ON settlement_queue_v2 BEGIN
 SELECT CASE WHEN NOT (
  (OLD.status IN ('READY','CLAIMED') AND NEW.status='CLAIMED' AND NEW.claim_version=OLD.claim_version+1 AND NEW.claim_owner IS NOT NULL)
  OR (OLD.status='CLAIMED' AND NEW.status IN ('READY','SETTLED') AND NEW.claim_version=OLD.claim_version)
  OR (OLD.status='SETTLED' AND NEW.status='ACKED' AND NEW.claim_version=OLD.claim_version)
  OR (OLD.status='CLAIMED' AND NEW.status='CLAIMED' AND NEW.claim_version=OLD.claim_version AND NEW.claim_owner IS OLD.claim_owner AND NEW.lease_until<OLD.lease_until)
 ) THEN RAISE(ABORT,'INVALID_QUEUE_TRANSITION') END;
END;
CREATE TRIGGER IF NOT EXISTS queue_delete_guard BEFORE DELETE ON settlement_queue_v2 BEGIN
 SELECT RAISE(ABORT,'DURABLE_QUEUE_DELETE_FORBIDDEN');
END;

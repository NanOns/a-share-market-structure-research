-- Deferred typed references support the existing atomic publication write order.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS integrity_calendar_v2(session_no INTEGER PRIMARY KEY,trade_date TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS integrity_authority_v2(authority_id TEXT PRIMARY KEY,authority_binding TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS integrity_activation_v2(id TEXT PRIMARY KEY,authority_binding TEXT NOT NULL,
 FOREIGN KEY(id,authority_binding) REFERENCES integrity_authority_v2(authority_id,authority_binding) DEFERRABLE INITIALLY DEFERRED);
CREATE UNIQUE INDEX IF NOT EXISTS authority_exact_v2 ON integrity_authority_v2(authority_id,authority_binding);
CREATE TABLE IF NOT EXISTS integrity_manifest_v2(id TEXT PRIMARY KEY,model TEXT NOT NULL,lineage TEXT NOT NULL,trade_date TEXT NOT NULL,
 UNIQUE(id,model,lineage,trade_date));
CREATE TABLE IF NOT EXISTS integrity_slot_v2(id TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),manifest TEXT NOT NULL,
 model TEXT NOT NULL,lineage TEXT NOT NULL,trade_date TEXT NOT NULL,status TEXT NOT NULL CHECK(status='ACCEPTED_ON_TIME'),
 PRIMARY KEY(id,revision),UNIQUE(id,revision,manifest,model,lineage,trade_date),UNIQUE(id,revision,manifest),
 FOREIGN KEY(manifest,model,lineage,trade_date) REFERENCES integrity_manifest_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_publication_v2(id TEXT PRIMARY KEY,slot TEXT NOT NULL,revision INTEGER NOT NULL,manifest TEXT NOT NULL,
 model TEXT NOT NULL,lineage TEXT NOT NULL,trade_date TEXT NOT NULL,UNIQUE(id,model,lineage,trade_date),
 FOREIGN KEY(slot,revision,manifest,model,lineage,trade_date) REFERENCES integrity_slot_v2(id,revision,manifest,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_event_v2(id TEXT PRIMARY KEY,model TEXT NOT NULL,lineage TEXT NOT NULL,trade_date TEXT NOT NULL,
 UNIQUE(id,model,lineage,trade_date));
CREATE TABLE IF NOT EXISTS integrity_freeze_v2(reference TEXT PRIMARY KEY,enrollment TEXT NOT NULL,t0 TEXT NOT NULL,
 UNIQUE(reference,enrollment,t0),
 FOREIGN KEY(enrollment) REFERENCES integrity_enrollment_v2(id) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_enrollment_v2(id TEXT PRIMARY KEY,event TEXT NOT NULL,model TEXT NOT NULL,lineage TEXT NOT NULL,
 t0 TEXT NOT NULL,frozen_t0 TEXT NOT NULL,slot TEXT NOT NULL,revision INTEGER NOT NULL,manifest TEXT NOT NULL,freeze_reference TEXT NOT NULL,
 UNIQUE(id,event),UNIQUE(id,frozen_t0),
 FOREIGN KEY(event,model,lineage,t0) REFERENCES integrity_event_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(slot,revision,manifest,model,lineage,t0) REFERENCES integrity_slot_v2(id,revision,manifest,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(id,event) REFERENCES integrity_admission_v2(id,event) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(freeze_reference,id,t0) REFERENCES integrity_freeze_v2(reference,enrollment,t0) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_admission_v2(id TEXT PRIMARY KEY,event TEXT NOT NULL,slot TEXT NOT NULL,revision INTEGER NOT NULL,
 manifest TEXT NOT NULL,UNIQUE(id,event),
 FOREIGN KEY(id,event) REFERENCES integrity_enrollment_v2(id,event) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(slot,revision,manifest) REFERENCES integrity_slot_v2(id,revision,manifest) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_due_v2(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,horizon INTEGER NOT NULL CHECK(horizon IN(1,3,5,10,20)),
 due_date TEXT,frozen_t0 TEXT NOT NULL,UNIQUE(enrollment,horizon,due_date,frozen_t0),
 FOREIGN KEY(enrollment,frozen_t0) REFERENCES integrity_enrollment_v2(id,frozen_t0) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE IF NOT EXISTS integrity_evaluation_source_v2(digest TEXT PRIMARY KEY,source_binding TEXT NOT NULL,
 CHECK(json_valid(source_binding) AND json_extract(source_binding,'$.sha256') IS digest));
CREATE TABLE IF NOT EXISTS integrity_outcome_v2(id TEXT PRIMARY KEY,enrollment TEXT NOT NULL,horizon INTEGER NOT NULL,due_date TEXT NOT NULL,
 frozen_t0 TEXT NOT NULL,source_digest TEXT NOT NULL,source_binding TEXT NOT NULL,
 FOREIGN KEY(enrollment,horizon,due_date,frozen_t0) REFERENCES integrity_due_v2(enrollment,horizon,due_date,frozen_t0) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(source_digest,source_binding) REFERENCES integrity_evaluation_source_v2(digest,source_binding) DEFERRABLE INITIALLY DEFERRED);
CREATE UNIQUE INDEX IF NOT EXISTS evaluation_exact_v2 ON integrity_evaluation_source_v2(digest,source_binding);
CREATE TABLE IF NOT EXISTS integrity_state_v2(id TEXT PRIMARY KEY,publication TEXT NOT NULL,model TEXT NOT NULL,lineage TEXT NOT NULL,trade_date TEXT NOT NULL,
 FOREIGN KEY(publication,model,lineage,trade_date) REFERENCES integrity_publication_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE TRIGGER IF NOT EXISTS integrity_fact_v2 AFTER INSERT ON facts BEGIN
 INSERT INTO integrity_activation_v2 SELECT NEW.id,json_extract(NEW.payload,'$.authority_binding') WHERE NEW.kind='activation';
 INSERT INTO integrity_manifest_v2 SELECT NEW.id,json_extract(NEW.payload,'$.model_contract_id'),json_extract(NEW.payload,'$.state_lineage_id'),json_extract(NEW.payload,'$.trade_date') WHERE NEW.kind='manifest';
 INSERT INTO integrity_slot_v2 SELECT json_extract(NEW.payload,'$.slot_id'),json_extract(NEW.payload,'$.revision'),json_extract(NEW.payload,'$.source_manifest_digest'),json_extract(NEW.payload,'$.model_contract_id'),json_extract(NEW.payload,'$.state_lineage_id'),json_extract(NEW.payload,'$.trade_date'),json_extract(NEW.payload,'$.slot_status') WHERE NEW.kind='slot';
 INSERT INTO integrity_publication_v2 SELECT NEW.id,json_extract(NEW.payload,'$.slot_id'),json_extract(NEW.payload,'$.revision'),json_extract(NEW.payload,'$.source_manifest_digest'),s.model,s.lineage,json_extract(NEW.payload,'$.trade_date') FROM integrity_slot_v2 s WHERE NEW.kind='publication' AND s.id=json_extract(NEW.payload,'$.slot_id') AND s.revision=json_extract(NEW.payload,'$.revision');
 SELECT CASE WHEN NEW.kind='publication' AND NOT EXISTS(SELECT 1 FROM integrity_publication_v2 WHERE id=NEW.id) THEN RAISE(ABORT,'ORPHAN_PUBLICATION') END;
 INSERT OR IGNORE INTO integrity_event_v2 SELECT json_extract(NEW.payload,'$.value.logical_event_id'),json_extract(NEW.payload,'$.value.model_contract_id'),json_extract(NEW.payload,'$.value.state_lineage_id'),json_extract(NEW.payload,'$.value.event_trade_date') WHERE NEW.kind='artifact' AND json_extract(NEW.payload,'$.kind')='logical_event';
 INSERT INTO integrity_freeze_v2 SELECT 'sqlite:'||NEW.id,json_extract(NEW.payload,'$.value.enrollment_id'),json_extract(NEW.payload,'$.value.T0') WHERE NEW.kind='artifact' AND json_extract(NEW.payload,'$.kind')='t0_freezes';
 INSERT INTO integrity_enrollment_v2 SELECT NEW.id,json_extract(NEW.payload,'$.logical_event_id'),json_extract(NEW.payload,'$.model_contract_id'),json_extract(NEW.payload,'$.state_lineage_id'),json_extract(NEW.payload,'$.T0'),json_extract(NEW.payload,'$.frozen_t0'),json_extract(NEW.payload,'$.observation_slot.slot_id'),json_extract(NEW.payload,'$.observation_slot.revision'),json_extract(NEW.payload,'$.source_manifest_digest'),json_extract(NEW.payload,'$.frozen_t0.path') WHERE NEW.kind='enrollment';
 SELECT CASE WHEN NEW.kind='enrollment' AND (json_extract(NEW.payload,'$.owner_logical_event') IS NOT json_extract(NEW.payload,'$.logical_event_id') OR json_extract(NEW.payload,'$.cohort_acceptance') IS NOT 'ACCEPTED_REALTIME_WITH_SLOT') THEN RAISE(ABORT,'INVALID_ENROLLMENT_OWNER_OR_ADMISSION') END;
 INSERT INTO integrity_admission_v2 SELECT NEW.id,json_extract(NEW.payload,'$.logical_event_id'),json_extract(NEW.payload,'$.observation_slot.slot_id'),json_extract(NEW.payload,'$.observation_slot.revision'),json_extract(NEW.payload,'$.source_manifest_digest') WHERE NEW.kind='realtime_admission';
 SELECT CASE WHEN NEW.kind='realtime_admission' AND json_extract(NEW.payload,'$.owner_event.logical_event_id') IS NOT json_extract(NEW.payload,'$.logical_event_id') THEN RAISE(ABORT,'WRONG_OWNER_LOGICAL_EVENT') END;
 INSERT INTO integrity_due_v2 SELECT NEW.id,json_extract(NEW.payload,'$.enrollment_id'),json_extract(NEW.payload,'$.horizon'),json_extract(NEW.payload,'$.due_date'),json_extract(NEW.payload,'$.frozen_t0') WHERE NEW.kind IN ('due','due_revision');
 INSERT INTO integrity_outcome_v2 SELECT NEW.id,json_extract(NEW.payload,'$.enrollment_id'),json_extract(NEW.payload,'$.horizon'),json_extract(NEW.payload,'$.due_date'),json_extract(NEW.payload,'$.frozen_t0'),json_extract(NEW.payload,'$.evaluation_source_digest'),json_extract(NEW.payload,'$.evaluation_source') WHERE NEW.kind='outcome';
 INSERT INTO integrity_state_v2 SELECT NEW.id,json_extract(NEW.payload,'$.publication_id'),json_extract(NEW.payload,'$.model_contract_id'),json_extract(NEW.payload,'$.state_lineage_id'),json_extract(NEW.payload,'$.trade_date') WHERE NEW.kind='state';
END;
CREATE TRIGGER IF NOT EXISTS integrity_due_calendar_v2 BEFORE INSERT ON integrity_due_v2 BEGIN
 SELECT CASE WHEN NEW.due_date IS NOT (SELECT future.trade_date FROM integrity_enrollment_v2 e JOIN integrity_calendar_v2 t0 ON t0.trade_date=e.t0 JOIN integrity_calendar_v2 future ON future.session_no=t0.session_no+NEW.horizon WHERE e.id=NEW.enrollment)
 AND EXISTS(SELECT 1 FROM integrity_enrollment_v2 WHERE id=NEW.enrollment)
 THEN RAISE(ABORT,'WRONG_DUE_CALENDAR_HORIZON') END;
END;
CREATE TRIGGER IF NOT EXISTS integrity_enrollment_due_calendar_v2 AFTER INSERT ON integrity_enrollment_v2 BEGIN
 SELECT CASE WHEN EXISTS(SELECT 1 FROM integrity_due_v2 d WHERE d.enrollment=NEW.id AND d.due_date IS NOT
 (SELECT future.trade_date FROM integrity_calendar_v2 t0 JOIN integrity_calendar_v2 future ON future.session_no=t0.session_no+d.horizon WHERE t0.trade_date=NEW.t0))
 THEN RAISE(ABORT,'WRONG_DUE_CALENDAR_HORIZON') END;
END;

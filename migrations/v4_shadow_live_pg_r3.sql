-- R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1. PostgreSQL DDL; no embedded engine.
CREATE TABLE shadow_live_identity(singleton integer PRIMARY KEY CHECK(singleton=1),contract_id text NOT NULL CHECK(contract_id='R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1'),schema_name text NOT NULL,root_digest text NOT NULL,migration_sha256 text NOT NULL);
CREATE TABLE storage_identity(singleton integer PRIMARY KEY CHECK(singleton=1),environment text NOT NULL,evidence_origin text NOT NULL,
 CHECK((environment='REAL' AND evidence_origin='PIT_OBSERVED') OR (environment='ACTIVATION_SIMULATION' AND evidence_origin='ACTIVATION_SIMULATION')));
CREATE TABLE facts(kind text NOT NULL,id text NOT NULL,namespace text NOT NULL CHECK(namespace='SHADOW_V4'),execution_mode text NOT NULL CHECK(execution_mode='SHADOW'),evidence_origin text NOT NULL,payload text NOT NULL,digest text NOT NULL CHECK(digest ~ '^[0-9a-f]{64}$'),ordinal bigint GENERATED ALWAYS AS IDENTITY,
 PRIMARY KEY(kind,id),CHECK(jsonb_typeof(payload::jsonb)='object'),CHECK(payload::jsonb->>'namespace' IS NOT DISTINCT FROM 'SHADOW_V4'),CHECK(payload::jsonb->>'execution_mode' IS NOT DISTINCT FROM 'SHADOW'),CHECK(payload::jsonb->>'evidence_origin' IS NOT DISTINCT FROM evidence_origin),CHECK(digest=encode(sha256(convert_to(payload,'UTF8')),'hex')));
CREATE TABLE publication_heads(slot_id text PRIMARY KEY,publication_id text NOT NULL,revision integer NOT NULL CHECK(revision>0));
CREATE TABLE activation_head(singleton integer PRIMARY KEY CHECK(singleton=1),authority_id text NOT NULL);
CREATE UNIQUE INDEX unique_original_event ON facts((payload::jsonb->>'logical_event_id')) WHERE kind='enrollment';
CREATE UNIQUE INDEX unique_slot_revision ON facts((payload::jsonb->>'slot_id'),((payload::jsonb->>'revision')::integer)) WHERE kind='slot';
CREATE UNIQUE INDEX unique_publication_revision ON facts((payload::jsonb->>'slot_id'),((payload::jsonb->>'revision')::integer)) WHERE kind='publication';
CREATE UNIQUE INDEX unique_due ON facts((payload::jsonb->>'enrollment_id'),((payload::jsonb->>'horizon')::integer)) WHERE kind='due';
CREATE UNIQUE INDEX unique_observation_revision ON facts((payload::jsonb->>'logical_event_id'),(payload::jsonb->>'slot_id'),((payload::jsonb->>'revision')::integer)) WHERE kind='observation';
CREATE FUNCTION reject_shadow_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'APPEND_ONLY_IMMUTABLE_SHADOW' USING ERRCODE='23514'; END $$;
CREATE TRIGGER immutable_facts BEFORE UPDATE OR DELETE OR TRUNCATE ON facts FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_mutation();
CREATE TRIGGER immutable_storage BEFORE UPDATE OR DELETE OR TRUNCATE ON storage_identity FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_mutation();
CREATE TRIGGER immutable_identity BEFORE UPDATE OR DELETE OR TRUNCATE ON shadow_live_identity FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_mutation();
CREATE FUNCTION shadow_fact_origin_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p jsonb:=NEW.payload::jsonb; prior jsonb;
BEGIN
 IF NEW.evidence_origin IS DISTINCT FROM (SELECT evidence_origin FROM storage_identity WHERE singleton=1) THEN RAISE EXCEPTION 'STORAGE_ORIGIN_MISMATCH' USING ERRCODE='23514'; END IF;
 IF NEW.kind='observation' THEN
  IF p->>'revision' IS NULL OR (p->>'revision')::integer<=0 THEN RAISE EXCEPTION 'INVALID_OBSERVATION_REVISION' USING ERRCODE='23514'; END IF;
  IF (p->>'revision')::integer>1 THEN
   SELECT payload::jsonb INTO prior FROM facts WHERE kind='observation' AND id=p->>'supersedes_observation';
   IF prior IS NULL OR prior->>'logical_event_id' IS DISTINCT FROM p->>'logical_event_id' OR prior->>'slot_id' IS DISTINCT FROM p->>'slot_id' OR (prior->>'revision')::integer >= (p->>'revision')::integer THEN RAISE EXCEPTION 'INVALID_OBSERVATION_PREDECESSOR' USING ERRCODE='23514'; END IF;
  ELSIF p->>'supersedes_observation' IS NOT NULL THEN RAISE EXCEPTION 'ORIGINAL_HAS_PREDECESSOR' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fact_origin BEFORE INSERT ON facts FOR EACH ROW EXECUTE FUNCTION shadow_fact_origin_guard();

CREATE TABLE integrity_calendar_v2(session_no integer PRIMARY KEY,trade_date text NOT NULL UNIQUE);
CREATE TABLE integrity_authority_v2(authority_id text PRIMARY KEY,authority_binding jsonb NOT NULL UNIQUE,UNIQUE(authority_id,authority_binding));
CREATE TABLE integrity_activation_v2(id text PRIMARY KEY,authority_binding jsonb NOT NULL,FOREIGN KEY(id,authority_binding) REFERENCES integrity_authority_v2(authority_id,authority_binding) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE integrity_manifest_v2(id text PRIMARY KEY,model text NOT NULL,lineage text NOT NULL,trade_date text NOT NULL,UNIQUE(id,model,lineage,trade_date));
CREATE TABLE integrity_slot_v2(id text NOT NULL,revision integer NOT NULL CHECK(revision>0),manifest text NOT NULL,model text NOT NULL,lineage text NOT NULL,trade_date text NOT NULL,status text NOT NULL CHECK(status='ACCEPTED_ON_TIME'),PRIMARY KEY(id,revision),UNIQUE(id,revision,manifest,model,lineage,trade_date),UNIQUE(id,revision,manifest),FOREIGN KEY(manifest,model,lineage,trade_date) REFERENCES integrity_manifest_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE integrity_publication_v2(id text PRIMARY KEY,slot text NOT NULL,revision integer NOT NULL,manifest text NOT NULL,model text NOT NULL,lineage text NOT NULL,trade_date text NOT NULL,UNIQUE(id,model,lineage,trade_date),FOREIGN KEY(slot,revision,manifest,model,lineage,trade_date) REFERENCES integrity_slot_v2(id,revision,manifest,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE integrity_event_v2(id text PRIMARY KEY,model text NOT NULL,lineage text NOT NULL,trade_date text NOT NULL,UNIQUE(id,model,lineage,trade_date));
CREATE TABLE integrity_freeze_v2(reference text PRIMARY KEY,enrollment text NOT NULL,t0 text NOT NULL,UNIQUE(reference,enrollment,t0));
CREATE TABLE integrity_enrollment_v2(id text PRIMARY KEY,event text NOT NULL,model text NOT NULL,lineage text NOT NULL,t0 text NOT NULL,frozen_t0 jsonb NOT NULL,slot text NOT NULL,revision integer NOT NULL,manifest text NOT NULL,freeze_reference text NOT NULL,UNIQUE(id,event),UNIQUE(id,frozen_t0),
 FOREIGN KEY(event,model,lineage,t0) REFERENCES integrity_event_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(slot,revision,manifest,model,lineage,t0) REFERENCES integrity_slot_v2(id,revision,manifest,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(freeze_reference,id,t0) REFERENCES integrity_freeze_v2(reference,enrollment,t0) DEFERRABLE INITIALLY DEFERRED);
ALTER TABLE integrity_freeze_v2 ADD CONSTRAINT freeze_enrollment FOREIGN KEY(enrollment) REFERENCES integrity_enrollment_v2(id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE integrity_admission_v2(id text PRIMARY KEY,event text NOT NULL,slot text NOT NULL,revision integer NOT NULL,manifest text NOT NULL,UNIQUE(id,event),FOREIGN KEY(id,event) REFERENCES integrity_enrollment_v2(id,event) DEFERRABLE INITIALLY DEFERRED,FOREIGN KEY(slot,revision,manifest) REFERENCES integrity_slot_v2(id,revision,manifest) DEFERRABLE INITIALLY DEFERRED);
ALTER TABLE integrity_enrollment_v2 ADD CONSTRAINT enrollment_admission FOREIGN KEY(id,event) REFERENCES integrity_admission_v2(id,event) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE integrity_due_v2(id text PRIMARY KEY,enrollment text NOT NULL,horizon integer NOT NULL CHECK(horizon IN(1,3,5,10,20)),due_date text,frozen_t0 jsonb NOT NULL,UNIQUE(enrollment,horizon,due_date,frozen_t0),FOREIGN KEY(enrollment,frozen_t0) REFERENCES integrity_enrollment_v2(id,frozen_t0) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE integrity_evaluation_source_v2(digest text PRIMARY KEY,source_binding jsonb NOT NULL,CHECK(jsonb_typeof(source_binding)='object' AND source_binding->>'sha256' IS NOT DISTINCT FROM digest),UNIQUE(digest,source_binding));
CREATE TABLE integrity_outcome_v2(id text PRIMARY KEY,enrollment text NOT NULL,horizon integer NOT NULL,due_date text NOT NULL,frozen_t0 jsonb NOT NULL,source_digest text NOT NULL,source_binding jsonb NOT NULL,
 FOREIGN KEY(enrollment,horizon,due_date,frozen_t0) REFERENCES integrity_due_v2(enrollment,horizon,due_date,frozen_t0) DEFERRABLE INITIALLY DEFERRED,
 FOREIGN KEY(source_digest,source_binding) REFERENCES integrity_evaluation_source_v2(digest,source_binding) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE integrity_state_v2(id text PRIMARY KEY,publication text NOT NULL,model text NOT NULL,lineage text NOT NULL,trade_date text NOT NULL,FOREIGN KEY(publication,model,lineage,trade_date) REFERENCES integrity_publication_v2(id,model,lineage,trade_date) DEFERRABLE INITIALLY DEFERRED);
CREATE FUNCTION shadow_integrity_projection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p jsonb:=NEW.payload::jsonb;
BEGIN
 CASE NEW.kind
 WHEN 'activation' THEN INSERT INTO integrity_activation_v2 VALUES(NEW.id,p->'authority_binding');
 WHEN 'manifest' THEN INSERT INTO integrity_manifest_v2 VALUES(NEW.id,p->>'model_contract_id',p->>'state_lineage_id',p->>'trade_date');
 WHEN 'slot' THEN INSERT INTO integrity_slot_v2 VALUES(p->>'slot_id',(p->>'revision')::integer,p->>'source_manifest_digest',p->>'model_contract_id',p->>'state_lineage_id',p->>'trade_date',p->>'slot_status');
 WHEN 'publication' THEN
  INSERT INTO integrity_publication_v2 SELECT NEW.id,p->>'slot_id',(p->>'revision')::integer,p->>'source_manifest_digest',s.model,s.lineage,p->>'trade_date' FROM integrity_slot_v2 s WHERE s.id=p->>'slot_id' AND s.revision=(p->>'revision')::integer;
  IF NOT FOUND THEN RAISE EXCEPTION 'ORPHAN_PUBLICATION' USING ERRCODE='23514'; END IF;
 WHEN 'artifact' THEN
  IF p->>'kind'='logical_event' THEN INSERT INTO integrity_event_v2 VALUES(p#>>'{value,logical_event_id}',p#>>'{value,model_contract_id}',p#>>'{value,state_lineage_id}',p#>>'{value,event_trade_date}') ON CONFLICT DO NOTHING;
  ELSIF p->>'kind'='t0_freezes' THEN INSERT INTO integrity_freeze_v2 VALUES('pg-shadow:'||NEW.id,p#>>'{value,enrollment_id}',p#>>'{value,T0}'); END IF;
 WHEN 'enrollment' THEN
  IF p->>'owner_logical_event' IS DISTINCT FROM p->>'logical_event_id' OR p->>'cohort_acceptance' IS DISTINCT FROM 'ACCEPTED_REALTIME_WITH_SLOT' THEN RAISE EXCEPTION 'INVALID_ENROLLMENT_OWNER_OR_ADMISSION' USING ERRCODE='23514'; END IF;
  INSERT INTO integrity_enrollment_v2 VALUES(NEW.id,p->>'logical_event_id',p->>'model_contract_id',p->>'state_lineage_id',p->>'T0',p->'frozen_t0',p#>>'{observation_slot,slot_id}',(p#>>'{observation_slot,revision}')::integer,p->>'source_manifest_digest',p#>>'{frozen_t0,path}');
 WHEN 'realtime_admission' THEN
  IF p#>>'{owner_event,logical_event_id}' IS DISTINCT FROM p->>'logical_event_id' THEN RAISE EXCEPTION 'WRONG_OWNER_LOGICAL_EVENT' USING ERRCODE='23514'; END IF;
  INSERT INTO integrity_admission_v2 VALUES(NEW.id,p->>'logical_event_id',p#>>'{observation_slot,slot_id}',(p#>>'{observation_slot,revision}')::integer,p->>'source_manifest_digest');
 WHEN 'due','due_revision' THEN INSERT INTO integrity_due_v2 VALUES(NEW.id,p->>'enrollment_id',(p->>'horizon')::integer,p->>'due_date',p->'frozen_t0');
 WHEN 'outcome' THEN INSERT INTO integrity_outcome_v2 VALUES(NEW.id,p->>'enrollment_id',(p->>'horizon')::integer,p->>'due_date',p->'frozen_t0',p->>'evaluation_source_digest',p->'evaluation_source');
 WHEN 'state' THEN INSERT INTO integrity_state_v2 VALUES(NEW.id,p->>'publication_id',p->>'model_contract_id',p->>'state_lineage_id',p->>'trade_date');
 ELSE NULL;
 END CASE;
 RETURN NEW;
END $$;
CREATE TRIGGER integrity_projection AFTER INSERT ON facts FOR EACH ROW EXECUTE FUNCTION shadow_integrity_projection();
CREATE FUNCTION shadow_due_calendar_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF EXISTS(SELECT 1 FROM integrity_due_v2 d JOIN integrity_enrollment_v2 e ON e.id=d.enrollment LEFT JOIN integrity_calendar_v2 t0 ON t0.trade_date=e.t0 LEFT JOIN integrity_calendar_v2 future ON future.session_no=t0.session_no+d.horizon WHERE d.id=NEW.id AND d.due_date IS DISTINCT FROM future.trade_date) THEN RAISE EXCEPTION 'WRONG_DUE_CALENDAR_HORIZON' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER due_calendar_guard AFTER INSERT ON integrity_due_v2 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION shadow_due_calendar_guard();
CREATE CONSTRAINT TRIGGER enrollment_calendar_guard AFTER INSERT ON integrity_enrollment_v2 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION shadow_due_calendar_guard();

CREATE TABLE settlement_queue_v2(queue_key text NOT NULL,evaluation_source_digest text NOT NULL,due_kind text NOT NULL DEFAULT 'due' CHECK(due_kind IN('due','due_revision')),due_id text NOT NULL,status text NOT NULL CHECK(status IN('READY','CLAIMED','SETTLED','ACKED')),claim_owner text,claim_version integer NOT NULL DEFAULT 0,claim_at double precision,lease_until double precision,retry_count integer NOT NULL DEFAULT 0,backlog_reason text,outcome_kind text NOT NULL DEFAULT 'outcome' CHECK(outcome_kind='outcome'),accepted_outcome_revision text,ack_at double precision,
 PRIMARY KEY(queue_key,evaluation_source_digest),FOREIGN KEY(due_kind,due_id) REFERENCES facts(kind,id),FOREIGN KEY(outcome_kind,accepted_outcome_revision) REFERENCES facts(kind,id),CHECK(status NOT IN('SETTLED','ACKED') OR accepted_outcome_revision IS NOT NULL),CHECK(status!='ACKED' OR ack_at IS NOT NULL));
CREATE FUNCTION shadow_queue_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'DURABLE_QUEUE_DELETE_FORBIDDEN' USING ERRCODE='23514'; END IF;
 IF NEW.queue_key IS DISTINCT FROM OLD.queue_key OR NEW.evaluation_source_digest IS DISTINCT FROM OLD.evaluation_source_digest OR NEW.due_id IS DISTINCT FROM OLD.due_id OR NEW.due_kind IS DISTINCT FROM OLD.due_kind OR OLD.status='ACKED' THEN RAISE EXCEPTION 'IMMUTABLE_QUEUE_IDENTITY_OR_ACK' USING ERRCODE='23514'; END IF;
 IF NOT((OLD.status IN('READY','CLAIMED') AND NEW.status='CLAIMED' AND NEW.claim_version=OLD.claim_version+1 AND NEW.claim_owner IS NOT NULL) OR (OLD.status='CLAIMED' AND NEW.status IN('READY','SETTLED') AND NEW.claim_version=OLD.claim_version) OR (OLD.status='SETTLED' AND NEW.status='ACKED' AND NEW.claim_version=OLD.claim_version) OR (OLD.status='CLAIMED' AND NEW.status='CLAIMED' AND NEW.claim_version=OLD.claim_version AND NEW.claim_owner IS NOT DISTINCT FROM OLD.claim_owner AND NEW.lease_until<OLD.lease_until)) THEN RAISE EXCEPTION 'INVALID_QUEUE_TRANSITION' USING ERRCODE='23514'; END IF;
 IF NEW.status='ACKED' AND NOT EXISTS(SELECT 1 FROM facts o JOIN facts d ON d.kind=NEW.due_kind AND d.id=NEW.due_id WHERE o.kind='outcome' AND o.id=NEW.accepted_outcome_revision AND o.payload::jsonb->>'evaluation_source_digest'=NEW.evaluation_source_digest AND o.payload::jsonb->'enrollment_id'=d.payload::jsonb->'enrollment_id' AND o.payload::jsonb->'horizon'=d.payload::jsonb->'horizon' AND o.payload::jsonb->'due_date'=d.payload::jsonb->'due_date' AND o.payload::jsonb->'frozen_t0'=d.payload::jsonb->'frozen_t0') THEN RAISE EXCEPTION 'QUEUE_RESULT_READBACK_MISMATCH' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER queue_guard BEFORE UPDATE OR DELETE ON settlement_queue_v2 FOR EACH ROW EXECUTE FUNCTION shadow_queue_guard();
CREATE TRIGGER queue_no_truncate BEFORE TRUNCATE ON settlement_queue_v2 FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_mutation();
DO $$ DECLARE name text; BEGIN
 FOR name IN SELECT tablename FROM pg_tables WHERE schemaname=current_schema() AND tablename LIKE 'integrity_%' LOOP
  EXECUTE format('CREATE TRIGGER immutable_reference BEFORE UPDATE OR DELETE OR TRUNCATE ON %I FOR EACH STATEMENT EXECUTE FUNCTION reject_shadow_mutation()',name);
 END LOOP;
END $$;

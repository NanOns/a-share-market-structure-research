-- Allocated by V4 migration allocator R2. Candidate ledger only; no accepted heads.
CREATE TABLE v4.confirmation_candidate_publications_r1 (
 publication_id text PRIMARY KEY,
 consumer_contract_id text NOT NULL CHECK (consumer_contract_id='V4_11_CANDIDATE_ENGINEERING_CONSUMER_V1'),
 producer_contract_id text NOT NULL CHECK (producer_contract_id='CONFIRMATION_DETECTOR_V1'),
 parameter_set_id text NOT NULL CHECK (parameter_set_id='V4_11_CONFIRMATION_PARAMETER_SET_V1'),
 payload jsonb NOT NULL,
 payload_digest text NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
 accepted boolean NOT NULL DEFAULT false CHECK (NOT accepted),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(publication_id,consumer_contract_id)
);
CREATE TABLE v4.confirmation_candidate_facts_r1 (
 publication_id text NOT NULL,
 security_id text NOT NULL,
 consumer_contract_id text NOT NULL,
 payload jsonb NOT NULL,
 PRIMARY KEY(publication_id,security_id),
 FOREIGN KEY(publication_id,consumer_contract_id) REFERENCES v4.confirmation_candidate_publications_r1(publication_id,consumer_contract_id),
 CHECK(payload->>'security_id'=security_id AND payload->>'publication_id'=publication_id),
 CHECK(payload->>'producer_contract_id'='CONFIRMATION_DETECTOR_V1'),
 CHECK(payload->>'parameter_set_id'='V4_11_CONFIRMATION_PARAMETER_SET_V1'),
 CHECK(payload->>'confirmation_status' IN ('TRUE','FALSE','UNKNOWN')),
 CHECK(NOT (payload ?| ARRAY['maturity','validity','tracking'])),
 CHECK(payload->>'amount_A_formal_branch'='DISABLED')
);
CREATE TABLE v4.confirmation_candidate_event_publications_r1 (
 publication_id text PRIMARY KEY,
 confirmation_publication_id text NOT NULL REFERENCES v4.confirmation_candidate_publications_r1(publication_id),
 consumer_contract_id text NOT NULL CHECK(consumer_contract_id='V4_11_CANDIDATE_ENGINEERING_CONSUMER_V1'),
 payload jsonb NOT NULL,
 payload_digest text NOT NULL CHECK(payload_digest ~ '^[0-9a-f]{64}$'),
 accepted boolean NOT NULL DEFAULT false CHECK(NOT accepted),
 UNIQUE(publication_id,consumer_contract_id)
);
CREATE TABLE v4.confirmation_candidate_events_r1 (
 publication_id text NOT NULL,
 entity_id text NOT NULL,
 consumer_contract_id text NOT NULL,
 payload jsonb NOT NULL,
 PRIMARY KEY(publication_id,entity_id),
 FOREIGN KEY(publication_id,consumer_contract_id) REFERENCES v4.confirmation_candidate_event_publications_r1(publication_id,consumer_contract_id),
 CHECK(payload->>'entity_id'=entity_id AND payload->>'contract_id'='STATE_EVENT_V1'),
 CHECK(payload->>'primary_event' IN ('FIRST_OBSERVED','CONFIRMATION_INVALIDATED','RECONFIRMED','NEW_CONFIRMED','SCENARIO_UPGRADED','CONFIRMATION_WEAKENED','PERSISTENT_CONFIRMED','SCENARIO_CHANGED','NONE'))
);
CREATE FUNCTION v4.confirmation_candidate_immutable_r1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'V4_11_CANDIDATE_APPEND_ONLY'; END $$;
CREATE TRIGGER confirmation_candidate_publications_append_only BEFORE UPDATE OR DELETE ON v4.confirmation_candidate_publications_r1 FOR EACH ROW EXECUTE FUNCTION v4.confirmation_candidate_immutable_r1();
CREATE TRIGGER confirmation_candidate_facts_append_only BEFORE UPDATE OR DELETE ON v4.confirmation_candidate_facts_r1 FOR EACH ROW EXECUTE FUNCTION v4.confirmation_candidate_immutable_r1();
CREATE TRIGGER confirmation_candidate_event_publications_append_only BEFORE UPDATE OR DELETE ON v4.confirmation_candidate_event_publications_r1 FOR EACH ROW EXECUTE FUNCTION v4.confirmation_candidate_immutable_r1();
CREATE TRIGGER confirmation_candidate_events_append_only BEFORE UPDATE OR DELETE ON v4.confirmation_candidate_events_r1 FOR EACH ROW EXECUTE FUNCTION v4.confirmation_candidate_immutable_r1();
REVOKE ALL ON v4.confirmation_candidate_publications_r1,v4.confirmation_candidate_facts_r1,v4.confirmation_candidate_event_publications_r1,v4.confirmation_candidate_events_r1 FROM PUBLIC;
CREATE FUNCTION v4.guard_confirmation_candidate_publication_r1() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.payload_digest IS DISTINCT FROM v4.state_digest_r1_1(NEW.payload) OR NEW.payload->>'accepted' IS DISTINCT FROM 'false' THEN
   RAISE EXCEPTION 'V4_11_PUBLICATION_DIGEST_OR_ACCEPTANCE_MISMATCH';
 END IF;
 IF TG_TABLE_NAME='confirmation_candidate_publications_r1' THEN
   IF NEW.publication_id IS DISTINCT FROM NEW.payload->>'publication_id' OR NEW.payload->>'contract_id' IS DISTINCT FROM 'CONFIRMATION_FACT_V1' OR
      NEW.payload->'permissions' IS DISTINCT FROM '{"production":false,"shadow":false,"focus":false}'::jsonb OR
      NEW.payload->'rows' IS NULL OR jsonb_typeof(NEW.payload->'rows') IS DISTINCT FROM 'array' THEN
     RAISE EXCEPTION 'V4_11_FACT_PUBLICATION_CONTRACT_MISMATCH';
   END IF;
 ELSE
   IF NEW.publication_id IS DISTINCT FROM 'V4_11_EVENTS:'||v4.state_digest_r1_1(NEW.payload) OR NEW.payload->>'contract_id' IS DISTINCT FROM 'STATE_EVENT_V1' THEN
     RAISE EXCEPTION 'V4_11_EVENT_PUBLICATION_CONTRACT_MISMATCH';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER confirmation_candidate_publication_identity BEFORE INSERT ON v4.confirmation_candidate_publications_r1 FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_publication_r1();
CREATE TRIGGER confirmation_candidate_event_publication_identity BEFORE INSERT ON v4.confirmation_candidate_event_publications_r1 FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_publication_r1();
CREATE FUNCTION v4.guard_confirmation_candidate_result_r1() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE publication jsonb;
BEGIN
 IF TG_TABLE_NAME='confirmation_candidate_facts_r1' THEN
   SELECT payload INTO publication FROM v4.confirmation_candidate_publications_r1 WHERE publication_id=NEW.publication_id;
 ELSE
   SELECT payload INTO publication FROM v4.confirmation_candidate_event_publications_r1 WHERE publication_id=NEW.publication_id;
 END IF;
 IF publication IS NULL OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(publication->'rows') r WHERE r=NEW.payload) THEN
   RAISE EXCEPTION 'V4_11_ROW_NOT_IN_EXACT_PUBLICATION';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER confirmation_candidate_fact_payload BEFORE INSERT ON v4.confirmation_candidate_facts_r1 FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_result_r1();
CREATE TRIGGER confirmation_candidate_event_payload BEFORE INSERT ON v4.confirmation_candidate_events_r1 FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_result_r1();
CREATE FUNCTION v4.guard_confirmation_candidate_complete_r1() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual bigint;
BEGIN
 IF TG_TABLE_NAME='confirmation_candidate_publications_r1' THEN
   SELECT count(*) INTO actual FROM v4.confirmation_candidate_facts_r1 WHERE publication_id=NEW.publication_id;
 ELSE
   SELECT count(*) INTO actual FROM v4.confirmation_candidate_events_r1 WHERE publication_id=NEW.publication_id;
 END IF;
 IF actual IS DISTINCT FROM jsonb_array_length(NEW.payload->'rows')::bigint THEN RAISE EXCEPTION 'V4_11_PUBLICATION_INCOMPLETE'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER confirmation_candidate_fact_complete AFTER INSERT ON v4.confirmation_candidate_publications_r1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_complete_r1();
CREATE CONSTRAINT TRIGGER confirmation_candidate_event_complete AFTER INSERT ON v4.confirmation_candidate_event_publications_r1 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v4.guard_confirmation_candidate_complete_r1();

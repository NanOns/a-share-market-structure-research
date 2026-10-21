-- Batch 07 D0 candidate-only source seal. All facts are append-only and never
-- create or alter a production Head. Historical replay is forced NON_PIT.
CREATE SCHEMA IF NOT EXISTS v4_r8d0seal_batch07_r1;

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='r8_publications_token_trade_date_uq') THEN
  ALTER TABLE v4_r8pub_fde08c597fc76d13.r8_publications
   ADD CONSTRAINT r8_publications_token_trade_date_uq UNIQUE(candidate_token,trade_date);
 END IF;
END $$;

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='v4_r8_d0_seal_reader_r1') THEN
  CREATE ROLE v4_r8_d0_seal_reader_r1 NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
 END IF;
END $$;
GRANT USAGE ON SCHEMA v4_r8d0seal_batch07_r1 TO v4_r8_d0_seal_reader_r1;

CREATE TABLE IF NOT EXISTS v4_r8d0seal_batch07_r1.publications (
 publication_id text PRIMARY KEY,
 revision_no integer NOT NULL DEFAULT 1 CHECK(revision_no>0),
 trade_date date NOT NULL,
 candidate_token text NOT NULL,
 owner_sha256 text NOT NULL CHECK(owner_sha256 ~ '^[0-9a-f]{64}$'),
 owner_bytes bigint NOT NULL CHECK(owner_bytes>0),
 predicate_digest text NOT NULL CHECK(predicate_digest ~ '^[0-9a-f]{64}$'),
 row_count integer NOT NULL CHECK(row_count>0),
 producer_contract_id text NOT NULL CHECK(producer_contract_id='V4_D0_SOURCE_SEAL_SUCCESSOR_R2'),
 producer_version text NOT NULL,
 parameter_sha256 text NOT NULL CHECK(parameter_sha256 ~ '^[0-9a-f]{64}$'),
 predecessor_window jsonb NOT NULL,
 knowledge_cutoff_at timestamptz NOT NULL,
 cutoff_basis text NOT NULL CHECK(cutoff_basis='EXACT_R8_SNAPSHOT_PUBLICATION_INSERTED_AT'),
 publication_status text NOT NULL,
 as_recorded boolean NOT NULL DEFAULT false,
 pit_eligible boolean NOT NULL DEFAULT false,
 production_admission boolean NOT NULL DEFAULT false CHECK(NOT production_admission),
 published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(publication_id,trade_date,candidate_token),
 UNIQUE(trade_date,candidate_token,revision_no),
 FOREIGN KEY(candidate_token,trade_date)
   REFERENCES v4_r8pub_fde08c597fc76d13.r8_publications(candidate_token,trade_date)
);
ALTER TABLE v4_r8d0seal_batch07_r1.publications ADD COLUMN IF NOT EXISTS revision_no integer NOT NULL DEFAULT 1;
ALTER TABLE v4_r8d0seal_batch07_r1.publications DROP CONSTRAINT IF EXISTS publications_publication_status_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications DROP CONSTRAINT IF EXISTS publications_as_recorded_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications DROP CONSTRAINT IF EXISTS publications_pit_eligible_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications DROP CONSTRAINT IF EXISTS d0_publication_status_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications DROP CONSTRAINT IF EXISTS d0_truthfulness_check;
ALTER TABLE v4_r8d0seal_batch07_r1.publications
 ADD CONSTRAINT d0_publication_status_check CHECK(publication_status IN ('DEV_RECONSTRUCTED_NON_PIT','DEV_SOURCE_VERIFIED')),
 ADD CONSTRAINT d0_truthfulness_check CHECK(
  (publication_status='DEV_RECONSTRUCTED_NON_PIT' AND NOT as_recorded AND NOT pit_eligible)
  OR (publication_status='DEV_SOURCE_VERIFIED' AND as_recorded AND pit_eligible));
CREATE UNIQUE INDEX IF NOT EXISTS d0_seal_publication_revision_uq
 ON v4_r8d0seal_batch07_r1.publications(trade_date,candidate_token,revision_no);

CREATE TABLE IF NOT EXISTS v4_r8d0seal_batch07_r1.consumed_sources (
 publication_id text NOT NULL,
 trade_date date NOT NULL,
 candidate_token text NOT NULL,
 source_role text NOT NULL,
 source_path text NOT NULL,
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
 source_bytes bigint NOT NULL CHECK(source_bytes>0),
 owner_contract_id text NOT NULL,
 owner_version_token text NOT NULL,
 time_role text NOT NULL,
 evidence_class text NOT NULL,
 available_at timestamptz,
 source_ingress_artifact_sha256 text,
 source_available_before_cutoff boolean NOT NULL,
 as_recorded boolean NOT NULL DEFAULT false,
 pit_eligible boolean NOT NULL DEFAULT false,
 PRIMARY KEY(publication_id,source_role),
 FOREIGN KEY(publication_id,trade_date,candidate_token)
   REFERENCES v4_r8d0seal_batch07_r1.publications(publication_id,trade_date,candidate_token)
);
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources DROP CONSTRAINT IF EXISTS consumed_sources_as_recorded_check;
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources DROP CONSTRAINT IF EXISTS consumed_sources_pit_eligible_check;
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources DROP CONSTRAINT IF EXISTS d0_consumed_truthfulness_check;
ALTER TABLE v4_r8d0seal_batch07_r1.consumed_sources ADD CONSTRAINT d0_consumed_truthfulness_check CHECK(
 (NOT as_recorded AND NOT pit_eligible) OR
 (as_recorded AND pit_eligible AND source_available_before_cutoff AND evidence_class NOT IN ('RECONSTRUCTED_NON_PIT','CAPTURED_AFTER_CLOSE_NON_PIT')));

CREATE TABLE IF NOT EXISTS v4_r8d0seal_batch07_r1.facts (
 publication_id text NOT NULL REFERENCES v4_r8d0seal_batch07_r1.publications(publication_id),
 scenario text NOT NULL CHECK(scenario IN ('LAUNCH_CONFIRM','RECOVERY_TURN')),
 security_id text NOT NULL,
 predicate_state text NOT NULL CHECK(predicate_state IN ('TRUE','FALSE','UNKNOWN')),
 check_values jsonb NOT NULL,
 field_lineage jsonb NOT NULL,
 fact_digest text NOT NULL CHECK(fact_digest ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY(publication_id,scenario,security_id)
);

CREATE OR REPLACE FUNCTION v4_r8d0seal_batch07_r1.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'D0_SEAL_BATCH07_APPEND_ONLY'; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['publications','consumed_sources','facts'] LOOP
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass('v4_r8d0seal_batch07_r1.'||t)
      AND tgname=t||'_append_only') THEN
   EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE OR TRUNCATE ON %I.%I FOR EACH STATEMENT EXECUTE FUNCTION v4_r8d0seal_batch07_r1.reject_mutation()',t||'_append_only','v4_r8d0seal_batch07_r1',t);
  END IF;
 END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA v4_r8d0seal_batch07_r1 FROM PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA v4_r8d0seal_batch07_r1 TO v4_r8_d0_seal_reader_r1;
GRANT USAGE ON SCHEMA v4_r8pub_fde08c597fc76d13,v4_r8_batch04_source_ingress TO v4_r8_d0_seal_reader_r1;
GRANT SELECT ON v4_r8pub_fde08c597fc76d13.r8_publications,
 v4_r8_batch04_source_ingress.source_receipts TO v4_r8_d0_seal_reader_r1;
GRANT v4_r8_d0_seal_reader_r1 TO postgres;

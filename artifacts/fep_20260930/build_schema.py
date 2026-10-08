from pathlib import Path
import os
p=Path('docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql')
s=r'''-- FEP_SCHEMA_DESIGN_V1 | 2026-09-30 | DESIGN ONLY: not installed or executed.
-- Requires accepted v4 publications schema (001..018 at reviewed HEAD).
-- V4-15 label authority adapter and acceptance service remain implementation gates.
-- No ALTER of existing publications/heads/cohorts; no network or TDX writes.
CREATE SCHEMA fep;
CREATE DOMAIN fep.sha256 AS text CHECK (VALUE ~ '^[0-9a-f]{64}$');

CREATE TABLE fep.contracts (
 contract_id text PRIMARY KEY, family text NOT NULL, version text NOT NULL,
 body jsonb NOT NULL CHECK(jsonb_typeof(body)='object'), digest fep.sha256 NOT NULL UNIQUE,
 created_at timestamptz NOT NULL, UNIQUE(family,version)
);
CREATE TABLE fep.scopes (
 scope_id text PRIMARY KEY, entity_type text NOT NULL CHECK(entity_type IN ('STOCK','SECTOR','MARKET')),
 observation_kind text NOT NULL CHECK(observation_kind IN ('ENTRY','DAILY_LANDMARK','MARKET_WIDE','MARKET_DAY','ROTATION_ENTRY')),
 signal_type text NOT NULL, feature_variant text NOT NULL, namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
 observation_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), digest fep.sha256 NOT NULL UNIQUE
);
CREATE TABLE fep.field_registry (
 feature_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), field_name text NOT NULL,
 producer text NOT NULL, source_field text NOT NULL, data_type text NOT NULL, unit text NOT NULL,
 nullable boolean NOT NULL, required boolean NOT NULL, availability_rule text NOT NULL,
 quality_allowlist jsonb NOT NULL, window_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 PRIMARY KEY(feature_contract_id,field_name)
);
CREATE TABLE fep.field_scope (
 feature_contract_id text NOT NULL, field_name text NOT NULL, scope_id text NOT NULL REFERENCES fep.scopes(scope_id),
 PRIMARY KEY(feature_contract_id,field_name,scope_id),
 FOREIGN KEY(feature_contract_id,field_name) REFERENCES fep.field_registry(feature_contract_id,field_name)
);
CREATE TABLE fep.targets (
 target_id text PRIMARY KEY, contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 scope_id text NOT NULL REFERENCES fep.scopes(scope_id), horizon integer NOT NULL CHECK(horizon IN (1,3,5,10,20)),
 unit text NOT NULL, value_kind text NOT NULL CHECK(value_kind IN ('NUMERIC','BINARY','CLASS')),
 formula text NOT NULL, risk_set jsonb NOT NULL, allowed_quality jsonb NOT NULL,
 enabled boolean NOT NULL DEFAULT false, UNIQUE(target_id,scope_id,horizon)
);
CREATE TABLE fep.observations (
 observation_id text PRIMARY KEY, scope_id text NOT NULL REFERENCES fep.scopes(scope_id),
 entity_id text NOT NULL, trade_date date NOT NULL, signal_key text NOT NULL,
 episode_key text, core_signal_contract_id text NOT NULL, slot_deadline timestamptz NOT NULL,
 UNIQUE(scope_id,entity_id,trade_date,signal_key), UNIQUE(observation_id,scope_id)
);
CREATE TABLE fep.observation_revisions (
 observation_id text NOT NULL REFERENCES fep.observations(observation_id), revision integer NOT NULL CHECK(revision>0),
 publication_id text NOT NULL REFERENCES v4.publications(publication_id),
 feature_cutoff timestamptz NOT NULL, dependency_manifest jsonb NOT NULL,
 dependency_digest fep.sha256 NOT NULL, enrichment_token text NOT NULL, -- NONE is explicit
 evidence_origin text NOT NULL CHECK(evidence_origin IN ('PIT_OBSERVED','RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED','DIAGNOSTIC_NON_PIT')),
 execution_mode text NOT NULL CHECK(execution_mode IN ('SHADOW','PRODUCTION','REPLAY')),
 supersedes_revision integer, created_at timestamptz NOT NULL,
 PRIMARY KEY(observation_id,revision), UNIQUE(observation_id,dependency_digest),
 FOREIGN KEY(observation_id,supersedes_revision) REFERENCES fep.observation_revisions(observation_id,revision),
 CHECK(supersedes_revision IS NULL OR supersedes_revision<revision)
);
CREATE TABLE fep.snapshots (
 snapshot_id text PRIMARY KEY, observation_id text NOT NULL, observation_revision integer NOT NULL,
 feature_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 feature_digest fep.sha256 NOT NULL, quality_digest fep.sha256 NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY(observation_id,observation_revision) REFERENCES fep.observation_revisions(observation_id,revision),
 UNIQUE(observation_id,observation_revision,feature_contract_id),
 UNIQUE(snapshot_id,observation_id), UNIQUE(snapshot_id,feature_contract_id)
);
CREATE TABLE fep.feature_values (
 snapshot_id text NOT NULL, feature_contract_id text NOT NULL, field_name text NOT NULL,
 value jsonb, quality text NOT NULL, reason text, source_digest fep.sha256 NOT NULL,
 PRIMARY KEY(snapshot_id,field_name),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES fep.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(feature_contract_id,field_name) REFERENCES fep.field_registry(feature_contract_id,field_name)
);
-- Binding is imported exclusively from V4-15 authority (or versioned State/Event authority).
-- No fake FK to a nonexistent Forward table: E1 must install a validated adapter/trigger
-- with exact upstream key+revision+digest readback before accepting any binding.
CREATE TABLE fep.label_source_bindings (
 binding_id text PRIMARY KEY, authority_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 upstream_key text NOT NULL, upstream_revision text NOT NULL, source_digest fep.sha256 NOT NULL,
 label_event_end date NOT NULL, label_due_at timestamptz NOT NULL, system_available_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL, UNIQUE(authority_contract_id,upstream_key,upstream_revision,source_digest),
 CHECK(system_available_at>=label_due_at)
);
CREATE TABLE fep.label_revisions (
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 revision integer NOT NULL CHECK(revision>0), binding_id text NOT NULL REFERENCES fep.label_source_bindings(binding_id),
 numeric_value double precision, class_value text, quality text NOT NULL, training_allowed boolean NOT NULL,
 target_digest fep.sha256 NOT NULL, supersedes_revision integer,
 PRIMARY KEY(observation_id,target_id,revision),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 FOREIGN KEY(observation_id,target_id,supersedes_revision) REFERENCES fep.label_revisions(observation_id,target_id,revision),
 CHECK(supersedes_revision IS NULL OR supersedes_revision<revision),
 CHECK(NOT(numeric_value IS NOT NULL AND class_value IS NOT NULL)),
 CHECK(numeric_value IS NULL OR (numeric_value>'-Infinity'::float8 AND numeric_value<'Infinity'::float8)),
 CHECK(NOT training_allowed OR numeric_value IS NOT NULL OR class_value IS NOT NULL)
);
CREATE TABLE fep.datasets (
 dataset_id text PRIMARY KEY, scope_id text NOT NULL REFERENCES fep.scopes(scope_id),
 feature_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 policy_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), dataset_cutoff timestamptz NOT NULL,
 manifest jsonb NOT NULL, digest fep.sha256 NOT NULL UNIQUE, created_at timestamptz NOT NULL,
 UNIQUE(dataset_id,scope_id,feature_contract_id)
);
CREATE TABLE fep.dataset_rows (
 dataset_id text NOT NULL, scope_id text NOT NULL, feature_contract_id text NOT NULL,
 observation_id text NOT NULL, snapshot_id text NOT NULL, target_id text NOT NULL,
 label_revision integer NOT NULL, weight double precision NOT NULL CHECK(weight>0 AND weight<'Infinity'::float8),
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST','EXCLUDED')),
 fold_id text NOT NULL, exclusion_reason text,
 PRIMARY KEY(dataset_id,observation_id,target_id,fold_id),
 FOREIGN KEY(dataset_id,scope_id,feature_contract_id) REFERENCES fep.datasets(dataset_id,scope_id,feature_contract_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(snapshot_id,observation_id) REFERENCES fep.snapshots(snapshot_id,observation_id),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES fep.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(observation_id,target_id,label_revision) REFERENCES fep.label_revisions(observation_id,target_id,revision)
);
CREATE TABLE fep.training_runs (
 training_run_id text PRIMARY KEY, dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id),
 experiment_lineage text NOT NULL, parameter_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 code_commit text NOT NULL, runtime_manifest jsonb NOT NULL, split_manifest jsonb NOT NULL,
 fit_started_at timestamptz NOT NULL, fit_finished_at timestamptz NOT NULL,
 calibration_finished_at timestamptz NOT NULL, artifact_path text NOT NULL, artifact_digest fep.sha256 NOT NULL,
 CHECK(fit_started_at<=fit_finished_at AND fit_finished_at<=calibration_finished_at)
);
CREATE TABLE fep.models (
 model_id text PRIMARY KEY, training_run_id text NOT NULL REFERENCES fep.training_runs(training_run_id),
 scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), family text NOT NULL,
 transform_digest fep.sha256 NOT NULL, calibration_digest fep.sha256 NOT NULL, ood_digest fep.sha256 NOT NULL,
 model_digest fep.sha256 NOT NULL UNIQUE, accepted_at timestamptz NOT NULL,
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 UNIQUE(model_id,scope_id,target_id,horizon,feature_contract_id)
);
CREATE TABLE fep.model_sets (
 model_set_id text PRIMARY KEY, policy_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 digest fep.sha256 NOT NULL UNIQUE, accepted_at timestamptz NOT NULL
);
CREATE TABLE fep.model_set_members (
 model_set_id text NOT NULL REFERENCES fep.model_sets(model_set_id), scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL, feature_contract_id text NOT NULL, model_id text NOT NULL,
 role text NOT NULL CHECK(role IN ('CHAMPION','BASELINE','CHALLENGER')),
 PRIMARY KEY(model_set_id,scope_id,target_id,horizon,role),
 FOREIGN KEY(model_id,scope_id,target_id,horizon,feature_contract_id)
 REFERENCES fep.models(model_id,scope_id,target_id,horizon,feature_contract_id),
 UNIQUE(model_set_id,model_id)
);
CREATE TABLE fep.activations (
 activation_id text PRIMARY KEY, model_set_id text NOT NULL REFERENCES fep.model_sets(model_set_id),
 capability text NOT NULL, scope_id text NOT NULL REFERENCES fep.scopes(scope_id),
 action text NOT NULL CHECK(action IN ('ALLOW_SHADOW','ALLOW_DISPLAY','ALLOW_PRIORITY','REVOKE')),
 effective_at timestamptz NOT NULL, recorded_at timestamptz NOT NULL, receipt_digest fep.sha256 NOT NULL,
 UNIQUE(capability,scope_id,effective_at), CHECK(recorded_at<=effective_at)
);
CREATE TABLE fep.prediction_slots (
 slot_id text PRIMARY KEY, observation_id text NOT NULL, scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL, model_family_scope text NOT NULL,
 selection_cutoff timestamptz NOT NULL, deadline timestamptz NOT NULL,
 model_set_id text NOT NULL REFERENCES fep.model_sets(model_set_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 UNIQUE(observation_id,target_id,horizon,model_family_scope),
 UNIQUE(slot_id,observation_id,scope_id,target_id,horizon,model_set_id), CHECK(selection_cutoff<=deadline)
);
CREATE TABLE fep.prediction_runs (
 run_id text PRIMARY KEY, publication_id text NOT NULL REFERENCES v4.publications(publication_id),
 model_set_id text NOT NULL REFERENCES fep.model_sets(model_set_id), input_digest fep.sha256 NOT NULL,
 started_at timestamptz NOT NULL, finished_at timestamptz NOT NULL,
 output_digest fep.sha256 NOT NULL, counts jsonb NOT NULL, CHECK(started_at<=finished_at),
 UNIQUE(run_id,model_set_id)
);
CREATE TABLE fep.predictions (
 prediction_id text PRIMARY KEY, slot_id text NOT NULL, revision integer NOT NULL CHECK(revision>0),
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 model_set_id text NOT NULL, model_id text NOT NULL, feature_contract_id text NOT NULL, snapshot_id text NOT NULL,
 run_id text NOT NULL, prediction_evidence text NOT NULL CHECK(prediction_evidence IN
 ('FIRST_OBSERVED','LATE_RECONSTRUCTION','CORRECTED_RECONSTRUCTION','HISTORICAL_SIMULATION')),
 quality text NOT NULL, unknown_reason text, outputs jsonb NOT NULL, support jsonb NOT NULL,
 output_digest fep.sha256 NOT NULL, accepted_at timestamptz NOT NULL, supersedes_id text,
 FOREIGN KEY(slot_id,observation_id,scope_id,target_id,horizon,model_set_id)
 REFERENCES fep.prediction_slots(slot_id,observation_id,scope_id,target_id,horizon,model_set_id),
 FOREIGN KEY(snapshot_id,observation_id) REFERENCES fep.snapshots(snapshot_id,observation_id),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES fep.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(model_id,scope_id,target_id,horizon,feature_contract_id)
 REFERENCES fep.models(model_id,scope_id,target_id,horizon,feature_contract_id),
 FOREIGN KEY(model_set_id,model_id) REFERENCES fep.model_set_members(model_set_id,model_id),
 FOREIGN KEY(run_id,model_set_id) REFERENCES fep.prediction_runs(run_id,model_set_id),
 UNIQUE(slot_id,model_id,revision), UNIQUE(prediction_id,slot_id,model_id),
 FOREIGN KEY(supersedes_id,slot_id,model_id) REFERENCES fep.predictions(prediction_id,slot_id,model_id),
 CHECK(supersedes_id IS NULL OR supersedes_id<>prediction_id)
);
CREATE UNIQUE INDEX prediction_first_observed ON fep.predictions(slot_id,model_id)
 WHERE prediction_evidence='FIRST_OBSERVED';
-- Freeze selected model-set once per slot. A later model is a new experiment scope,
-- not a replacement FIRST_OBSERVED of the original slot.
CREATE TABLE fep.slot_receipts (
 slot_id text NOT NULL REFERENCES fep.prediction_slots(slot_id), receipt_id text PRIMARY KEY,
 recorded_at timestamptz NOT NULL, status text NOT NULL CHECK(status IN ('MISSED','FAILED','PARTIAL','ACCEPTED')),
 payload jsonb NOT NULL, receipt_digest fep.sha256 NOT NULL
);
CREATE TABLE fep.acceptance_receipts (
 receipt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES fep.prediction_runs(run_id),
 accepted_at timestamptz NOT NULL, capability text NOT NULL,
 validation_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), checks jsonb NOT NULL,
 UNIQUE(run_id,capability)
);
CREATE TABLE fep.reports (
 report_id text PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('CALIBRATION','EVALUATION','DRIFT','PROMOTION','MISSINGNESS')),
 model_id text REFERENCES fep.models(model_id), dataset_id text REFERENCES fep.datasets(dataset_id),
 cutoff timestamptz NOT NULL, contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 manifest jsonb NOT NULL, results jsonb NOT NULL, digest fep.sha256 NOT NULL UNIQUE
);
CREATE TABLE fep.priority_projection (
 projection_id text PRIMARY KEY, run_id text NOT NULL REFERENCES fep.prediction_runs(run_id),
 observation_id text NOT NULL REFERENCES fep.observations(observation_id),
 priority_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 core_rank_identity fep.sha256 NOT NULL, axis_state text NOT NULL,
 axis_values jsonb NOT NULL, prediction_refs jsonb NOT NULL, permission_receipt_id text NOT NULL REFERENCES fep.acceptance_receipts(receipt_id),
 UNIQUE(run_id,observation_id,priority_contract_id)
);
CREATE INDEX label_by_binding ON fep.label_revisions(binding_id);
CREATE INDEX label_available ON fep.label_source_bindings(system_available_at,label_due_at);
CREATE INDEX observation_date_scope ON fep.observations(trade_date,scope_id);
CREATE INDEX dataset_cutoff ON fep.datasets(scope_id,dataset_cutoff);
CREATE INDEX prediction_readback ON fep.predictions(observation_id,model_set_id,target_id,revision);
CREATE INDEX activation_asof ON fep.activations(scope_id,capability,effective_at);

CREATE FUNCTION fep.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'FEP_APPEND_ONLY'; END $$;
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='fep' LOOP
  EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.%I FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation()',r.tablename);
 END LOOP;
END $$;
-- REQUIRED E1/E5 acceptance validations (not falsely claimed implemented here):
-- 1. Contracts/field JSON finite/schema/enum/units/required allowlist and exact manifest readback.
-- 2. Publication ACCEPTED, matching trade_date/entity/scope; snapshot publication == run publication.
-- 3. Label binding source exists in V4-15 authority, same observation/target/horizon/digest; revisions acyclic.
-- 4. Dataset selected revision availability <= cutoff, whole date folds and eligible risk set/quality;
--    dataset scope/feature and model scope/feature match, training cutoff <= fit start.
-- 5. Fit/calibration/model accepted/activation/slot selection/inference/deadline chain per FEP.3;
--    activation grants exact model_set/scope/capability, no revoked artifact, no post-deadline FIRST_OBSERVED.
-- 6. Output schema probability bounds/sums, quantile/coherence, and field_scope membership.
-- 7. Single transaction inserts all result+UNKNOWN rows, totals, acceptance receipt; read API
--    exposes only runs with acceptance receipt, never partial staging. FIRST_OBSERVED slots
--    not reserved by failed staging. Serialize competing acceptance of the same slot.
-- 8. Priority prediction_refs all match this observation/run and exact capability permission;
--    report manifest freezes label/prediction revisions and denominators, not latest heads.
-- Migration tests must deliberately violate every item before production permission.
-- Rollback: revoke capabilities and route UI to PRIORITY_V1; retain these tables/history.
'''
t=p.with_name('.'+p.name+'.tmp');p.parent.mkdir(exist_ok=True,parents=True)
with t.open('wb') as f:f.write(s.encode('utf8'));f.flush();os.fsync(f.fileno())
os.replace(t,p)
print('schema design',len(s.splitlines()),'lines')

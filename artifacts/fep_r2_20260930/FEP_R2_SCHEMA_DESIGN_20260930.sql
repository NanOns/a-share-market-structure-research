-- FEP_SCHEMA_DESIGN_V2 | 2026-09-30 | DESIGN ONLY: not installed or executed.
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
 label_event_end date NOT NULL, source_fact_available_at timestamptz NOT NULL,
 label_training_mature_at timestamptz NOT NULL, label_revision_available_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL, UNIQUE(authority_contract_id,upstream_key,upstream_revision,source_digest),
 CHECK(label_revision_available_at>=source_fact_available_at)
);
CREATE TABLE fep.label_revisions (
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 revision integer NOT NULL CHECK(revision>0), binding_id text NOT NULL REFERENCES fep.label_source_bindings(binding_id),
 numeric_value double precision, class_value text, quality text NOT NULL, training_allowed boolean NOT NULL,
 target_digest fep.sha256 NOT NULL, supersedes_revision integer,
 PRIMARY KEY(observation_id,target_id,revision),
 UNIQUE(observation_id,target_id,revision,target_digest),
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
-- Full expected denominator exists even when a label does not yet exist.
CREATE TABLE fep.dataset_eligibility_ledger (
 dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id),
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 status text NOT NULL CHECK(status IN ('EXPECTED','SCOPE_EXCLUDED')),
 reason text,
 PRIMARY KEY(dataset_id,observation_id,target_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 FOREIGN KEY(target_id) REFERENCES fep.targets(target_id)
);
-- Dataset global cutoff is a manifest upper bound, never a fold selection cutoff.
-- Fit/tune/calibration/outer-test phases have distinct as-of cutoffs; all are frozen.
CREATE TABLE fep.dataset_fold_cutoffs (
 dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id), fold_id text NOT NULL,
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST')),
 fold_dataset_cutoff timestamptz NOT NULL, phase_started_at timestamptz NOT NULL, selection_policy_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 split_digest fep.sha256 NOT NULL,
 PRIMARY KEY(dataset_id,fold_id,partition_name), CHECK(fold_dataset_cutoff<=phase_started_at)
);
CREATE TABLE fep.dataset_fold_label_selection (
 dataset_id text NOT NULL, fold_id text NOT NULL, partition_name text NOT NULL,
 observation_id text NOT NULL, target_id text NOT NULL,
 selected_label_revision integer, selected_label_digest fep.sha256, selection_reason text NOT NULL,
 eligibility text NOT NULL CHECK(eligibility IN ('ELIGIBLE','PENDING','MISSING_LABEL','QUALITY_EXCLUDED','SCOPE_EXCLUDED')),
 PRIMARY KEY(dataset_id,fold_id,partition_name,observation_id,target_id),
 FOREIGN KEY(dataset_id,fold_id,partition_name) REFERENCES fep.dataset_fold_cutoffs(dataset_id,fold_id,partition_name),
 FOREIGN KEY(dataset_id,observation_id,target_id) REFERENCES fep.dataset_eligibility_ledger(dataset_id,observation_id,target_id),
 FOREIGN KEY(observation_id,target_id,selected_label_revision,selected_label_digest)
 REFERENCES fep.label_revisions(observation_id,target_id,revision,target_digest),
 UNIQUE(dataset_id,fold_id,partition_name,observation_id,target_id,selected_label_revision,selected_label_digest),
 CHECK((selected_label_revision IS NULL)=(selected_label_digest IS NULL)),
 CHECK(eligibility<>'ELIGIBLE' OR selected_label_revision IS NOT NULL)
);
CREATE TABLE fep.dataset_rows (
 dataset_id text NOT NULL, scope_id text NOT NULL, feature_contract_id text NOT NULL,
 observation_id text NOT NULL, snapshot_id text NOT NULL, target_id text NOT NULL,
 label_revision integer NOT NULL, selected_label_digest fep.sha256 NOT NULL, weight double precision NOT NULL CHECK(weight>0 AND weight<'Infinity'::float8),
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST')),
 fold_id text NOT NULL, exclusion_reason text,
 PRIMARY KEY(dataset_id,observation_id,target_id,fold_id,partition_name),
 FOREIGN KEY(dataset_id,fold_id,partition_name,observation_id,target_id,label_revision,selected_label_digest)
 REFERENCES fep.dataset_fold_label_selection(dataset_id,fold_id,partition_name,observation_id,target_id,selected_label_revision,selected_label_digest),
 FOREIGN KEY(dataset_id,observation_id,target_id) REFERENCES fep.dataset_eligibility_ledger(dataset_id,observation_id,target_id),
 FOREIGN KEY(dataset_id,scope_id,feature_contract_id) REFERENCES fep.datasets(dataset_id,scope_id,feature_contract_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(snapshot_id,observation_id) REFERENCES fep.snapshots(snapshot_id,observation_id),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES fep.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(observation_id,target_id,label_revision) REFERENCES fep.label_revisions(observation_id,target_id,revision)
);
CREATE TABLE fep.training_runs (
 training_run_id text PRIMARY KEY, dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id),
 fold_id text NOT NULL, phase_manifest jsonb NOT NULL CHECK(jsonb_typeof(phase_manifest)='object'),
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
 UNIQUE(model_set_id,model_id),
 UNIQUE(model_set_id,scope_id,target_id,horizon,feature_contract_id,role)
);
-- The exact permission tuple is immutable and model-set-specific. Entity/variant
-- identity is inherited from scope; feature_contract is fixed explicitly.
CREATE TABLE fep.permission_keys (
 grant_id text PRIMARY KEY, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL, model_set_id text NOT NULL, model_role text NOT NULL DEFAULT 'CHAMPION',
 capability text NOT NULL CHECK(capability IN ('SHADOW_INFERENCE','DESCRIPTIVE_DISPLAY','MODEL_DISPLAY','PRIORITY_USE')),
 CHECK(model_role='CHAMPION'),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 FOREIGN KEY(model_set_id,scope_id,target_id,horizon,feature_contract_id,model_role)
 REFERENCES fep.model_set_members(model_set_id,scope_id,target_id,horizon,feature_contract_id,role),
 UNIQUE(scope_id,target_id,horizon,feature_contract_id,model_set_id,capability),
 UNIQUE(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability)
);
CREATE TABLE fep.activations (
 activation_id text PRIMARY KEY, grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id),
 action text NOT NULL CHECK(action IN ('ALLOW','REVOKE')),
 effective_at timestamptz NOT NULL, recorded_at timestamptz NOT NULL,
 prior_activation_id text REFERENCES fep.activations(activation_id), expected_head_version bigint NOT NULL CHECK(expected_head_version>=0),
 receipt_digest fep.sha256 NOT NULL, UNIQUE(activation_id,grant_id), CHECK(recorded_at<=effective_at)
);
-- This is a controlled mutable projection, NOT an append-only fact table.
-- Model-set is the payload, not part of the head key, so a replacement competes for the same head.
CREATE TABLE fep.deployment_heads (
 scope_id text NOT NULL, capability text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL, model_set_id text NOT NULL, grant_id text NOT NULL,
 activation_id text NOT NULL, head_version bigint NOT NULL CHECK(head_version>0), updated_at timestamptz NOT NULL,
 PRIMARY KEY(scope_id,capability,target_id,horizon,feature_contract_id),
 FOREIGN KEY(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability)
 REFERENCES fep.permission_keys(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability),
 FOREIGN KEY(activation_id,grant_id) REFERENCES fep.activations(activation_id,grant_id)
);
CREATE TABLE fep.deployment_change_receipts (
 activation_id text PRIMARY KEY REFERENCES fep.activations(activation_id),
 grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id), expected_prior_activation_id text,
 expected_head_version bigint NOT NULL, new_head_version bigint NOT NULL, request_id text NOT NULL UNIQUE,
 accepted_at timestamptz NOT NULL, checks jsonb NOT NULL,
 CHECK(new_head_version=expected_head_version+1),
 FOREIGN KEY(activation_id,grant_id) REFERENCES fep.activations(activation_id,grant_id)
);
CREATE TABLE fep.prediction_slots (
 slot_id text PRIMARY KEY, observation_id text NOT NULL, scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL, model_family_scope text NOT NULL,
 selection_cutoff timestamptz NOT NULL, deadline timestamptz NOT NULL,
 selection_status text NOT NULL CHECK(selection_status IN ('PLANNED','NO_ACTIVE_MODEL','SELECTED')),
 FOREIGN KEY(observation_id,scope_id) REFERENCES fep.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES fep.targets(target_id,scope_id,horizon),
 UNIQUE(observation_id,target_id,horizon,model_family_scope),
 UNIQUE(slot_id,observation_id,scope_id,target_id,horizon), CHECK(selection_cutoff<=deadline)
);
CREATE TABLE fep.slot_model_bindings (
 slot_id text PRIMARY KEY, observation_id text NOT NULL, scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL,
 model_set_id text NOT NULL REFERENCES fep.model_sets(model_set_id),
 selected_at timestamptz NOT NULL, selection_receipt_digest fep.sha256 NOT NULL,
 FOREIGN KEY(slot_id,observation_id,scope_id,target_id,horizon)
 REFERENCES fep.prediction_slots(slot_id,observation_id,scope_id,target_id,horizon),
 UNIQUE(slot_id,observation_id,scope_id,target_id,horizon,model_set_id)
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
 REFERENCES fep.slot_model_bindings(slot_id,observation_id,scope_id,target_id,horizon,model_set_id),
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
-- Each accepted target/capability uses the same exact grant key as activation/readback.
CREATE TABLE fep.acceptance_receipts (
 receipt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES fep.prediction_runs(run_id),
 accepted_at timestamptz NOT NULL, grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id),
 activation_id text NOT NULL,
 validation_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), checks jsonb NOT NULL,
 UNIQUE(run_id,grant_id), UNIQUE(receipt_id,run_id,grant_id),
 FOREIGN KEY(activation_id,grant_id) REFERENCES fep.activations(activation_id,grant_id)
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
 axis_values jsonb NOT NULL, prediction_refs jsonb NOT NULL,
 UNIQUE(run_id,observation_id,priority_contract_id), UNIQUE(projection_id,run_id)
);
-- Multi-target priority rows must cite every target's exact PRIORITY_USE grant;
-- a successful T5 grant cannot authorize another target or T20.
CREATE TABLE fep.priority_projection_grants (
 projection_id text NOT NULL REFERENCES fep.priority_projection(projection_id),
 grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id), run_id text NOT NULL,
 permission_receipt_id text NOT NULL,
 PRIMARY KEY(projection_id,grant_id),
 FOREIGN KEY(projection_id,run_id) REFERENCES fep.priority_projection(projection_id,run_id),
 FOREIGN KEY(permission_receipt_id,run_id,grant_id) REFERENCES fep.acceptance_receipts(receipt_id,run_id,grant_id)
);
CREATE INDEX label_by_binding ON fep.label_revisions(binding_id);
CREATE INDEX label_available ON fep.label_source_bindings(label_revision_available_at,label_training_mature_at);
CREATE INDEX observation_date_scope ON fep.observations(trade_date,scope_id);
CREATE INDEX dataset_cutoff ON fep.datasets(scope_id,dataset_cutoff);
CREATE INDEX prediction_readback ON fep.predictions(observation_id,model_set_id,target_id,revision);
CREATE INDEX activation_asof ON fep.activations(grant_id,effective_at);
CREATE INDEX fold_label_asof ON fep.dataset_fold_cutoffs(dataset_id,fold_id,partition_name,fold_dataset_cutoff);

CREATE FUNCTION fep.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'FEP_APPEND_ONLY'; END $$;
-- Explicit guards for this version; every future fact table migration must
-- create its own guard and be checked against the registry. No automatic inheritance.
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.contracts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.scopes FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.field_registry FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.field_scope FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.targets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.observations FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.observation_revisions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.snapshots FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.feature_values FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.label_source_bindings FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.label_revisions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.datasets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_eligibility_ledger FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_fold_cutoffs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_fold_label_selection FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.dataset_rows FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.training_runs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.models FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.model_sets FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.model_set_members FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.permission_keys FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.activations FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.deployment_change_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.prediction_slots FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.slot_model_bindings FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.prediction_runs FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.predictions FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.slot_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.acceptance_receipts FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.reports FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.priority_projection FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.priority_projection_grants FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
-- REQUIRED E1/E5 acceptance validations (not falsely claimed implemented here):
-- 1. Contracts/field JSON finite/schema/enum/units/required allowlist and exact manifest readback.
-- 2. Publication ACCEPTED, matching trade_date/entity/scope; snapshot publication == run publication.
-- 3. Label binding source exists in V4-15 authority, same observation/target/horizon/digest; revisions acyclic.
-- 4. Per-fold+partition selected revision availability <= fold cutoff <= dataset manifest upper cutoff;
--    source_fact_available_at, label_training_mature_at and label_revision_available_at each <= fold cutoff;
--    full denominator ledger holds no selected revision, fold selection freezes exact digest/reason;
--    dataset scope/feature and model scope/feature match, training cutoff <= fit start.
-- 5. Fit/calibration/model accepted/activation/slot selection/inference/deadline chain per FEP.3;
--    activation grants exact scope/target/horizon/feature_contract/model_set/capability, no revoked artifact, no post-deadline FIRST_OBSERVED.
-- 6. Output schema probability bounds/sums, quantile/coherence, and field_scope membership.
-- 7. Single transaction inserts all result+UNKNOWN rows, totals, acceptance receipt; read API
--    exposes only runs with acceptance receipt, never partial staging. FIRST_OBSERVED slots
--    not reserved by failed staging. Serialize competing acceptance of the same slot.
-- 8. Slots may be planned with no active model; selection_status is initial immutable
--    state, later binding/receipts are authoritative. A binding must be inserted by
--    selection_cutoff, reference then-active model set, and remain immutable.
--    NO_ACTIVE_MODEL/MISSED slots are retained without a fictitious model row.
--    Dataset expected-target ledger must include absent/unmatured labels; rows
--    must match ELIGIBLE fold+partition selection revision/digest and dataset scope exactly.
-- 9. Priority prediction_refs all match this observation/run and exact capability permission;
--    report manifest freezes label/prediction revisions and denominators, not latest heads.
-- 10. current daily Radar PRIORITY_USE requires DAILY_LANDMARK/candidate-day scope,
--     same-date snapshot and forecast plus pre-registered coverage. ENTRY rows are annotation only.
-- 11. Every new historical table must have an explicit append-only guard; only
--     deployment_heads allows controlled updates, denies DELETE and direct application DML.
--     Its trigger/function+DB role restriction and CAS rollback require actual E1 tests.
-- Migration tests must deliberately violate every item before production permission.
-- Rollback: revoke capabilities and route UI to PRIORITY_V1; retain these tables/history.

-- R2 CAS reference design. A service validates evidence/permission/state first;
-- this function serializes an already validated exact tuple transaction. Caller
-- must have no direct DML grants on deployment_heads, activations or receipts.
-- SECURITY DEFINER owner/search_path/EXECUTE privileges must be sealed by E1.
-- Future-effective activations are forbidden here: use explicit scheduled intents
-- and invoke this same CAS at the effective moment, not replace the head early.
CREATE FUNCTION fep.cas_deploy(
 p_grant_id text, p_activation_id text, p_action text, p_expected_version bigint,
 p_expected_prior text, p_request_id text, p_receipt_digest fep.sha256, p_checks jsonb
) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,fep AS $$
DECLARE k fep.permission_keys%ROWTYPE; prior fep.deployment_change_receipts%ROWTYPE; a fep.activations%ROWTYPE; n integer; ts timestamptz := clock_timestamp();
BEGIN
 IF p_grant_id IS NULL OR p_activation_id IS NULL OR p_action IS NULL OR p_expected_version IS NULL
  OR p_request_id IS NULL OR p_receipt_digest IS NULL OR p_checks IS NULL THEN
  RAISE EXCEPTION 'FEP_REQUIRED_CAS_PARAMETER_NULL';
 END IF;
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;
 SELECT * INTO prior FROM fep.deployment_change_receipts WHERE request_id=p_request_id;
 IF FOUND THEN
  SELECT * INTO STRICT a FROM fep.activations WHERE activation_id=prior.activation_id;
  IF prior.grant_id IS DISTINCT FROM p_grant_id OR prior.activation_id IS DISTINCT FROM p_activation_id OR a.action IS DISTINCT FROM p_action
   OR prior.expected_head_version IS DISTINCT FROM p_expected_version OR prior.expected_prior_activation_id IS DISTINCT FROM p_expected_prior
   OR a.receipt_digest IS DISTINCT FROM p_receipt_digest OR prior.checks IS DISTINCT FROM p_checks THEN
   RAISE EXCEPTION 'FEP_IDEMPOTENCY_CONFLICT';
  END IF;
  RETURN prior.new_head_version;
 END IF;
 IF p_expected_version<0 OR p_action NOT IN ('ALLOW','REVOKE') THEN RAISE EXCEPTION 'FEP_INVALID_CAS_INPUT'; END IF;
 INSERT INTO fep.activations(activation_id,grant_id,action,effective_at,recorded_at,prior_activation_id,expected_head_version,receipt_digest)
 VALUES(p_activation_id,p_grant_id,p_action,ts,ts,p_expected_prior,p_expected_version,p_receipt_digest);
 IF p_expected_version=0 THEN
  IF p_expected_prior IS NOT NULL OR p_action='REVOKE' THEN RAISE EXCEPTION 'FEP_INITIAL_PRIOR_INVALID'; END IF;
  INSERT INTO fep.deployment_heads(scope_id,capability,target_id,horizon,feature_contract_id,model_set_id,grant_id,activation_id,head_version,updated_at)
  VALUES(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id,k.model_set_id,k.grant_id,p_activation_id,1,ts)
  ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS n=ROW_COUNT;
 ELSE
  UPDATE fep.deployment_heads SET model_set_id=k.model_set_id,grant_id=k.grant_id,
   activation_id=p_activation_id,head_version=p_expected_version+1,updated_at=ts
  WHERE scope_id=k.scope_id AND capability=k.capability AND target_id=k.target_id
   AND horizon=k.horizon AND feature_contract_id=k.feature_contract_id
   AND head_version=p_expected_version AND activation_id IS NOT DISTINCT FROM p_expected_prior
   AND (p_action<>'REVOKE' OR grant_id=p_grant_id);
  GET DIAGNOSTICS n=ROW_COUNT;
 END IF;
 IF n<>1 THEN RAISE EXCEPTION 'FEP_CAS_CONFLICT'; END IF;
 INSERT INTO fep.deployment_change_receipts(activation_id,grant_id,expected_prior_activation_id,expected_head_version,new_head_version,request_id,accepted_at,checks)
 VALUES(p_activation_id,p_grant_id,p_expected_prior,p_expected_version,p_expected_version+1,p_request_id,ts,p_checks);
 RETURN p_expected_version+1;
END $$;
-- Conflict throws: activation, receipt and pointer changes all roll back together.
-- Exact historical activation used by the slot remains frozen. API current grant
-- requires deployment_heads target's accepted ALLOW; REVOKE denies that exact key.

REVOKE ALL ON FUNCTION fep.cas_deploy(text,text,text,bigint,text,text,fep.sha256,jsonb) FROM PUBLIC;
REVOKE ALL ON fep.deployment_heads FROM PUBLIC;
-- E1 must grant only EXECUTE to a sealed deployer role, not direct table DML;
-- SECURITY DEFINER owner is a dedicated trusted role with fixed search_path.

CREATE FUNCTION fep.validate_deployment_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a fep.activations%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'FEP_HEAD_DELETE_FORBIDDEN'; END IF;
 SELECT * INTO STRICT a FROM fep.activations WHERE activation_id=NEW.activation_id;
 IF a.grant_id<>NEW.grant_id OR a.effective_at>clock_timestamp() THEN RAISE EXCEPTION 'FEP_HEAD_ACTIVATION_INVALID'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.head_version<>1 OR a.expected_head_version<>0 OR a.prior_activation_id IS NOT NULL OR a.action<>'ALLOW' THEN
   RAISE EXCEPTION 'FEP_HEAD_INITIAL_INVALID';
  END IF;
 ELSE
  IF ROW(NEW.scope_id,NEW.capability,NEW.target_id,NEW.horizon,NEW.feature_contract_id)
   IS DISTINCT FROM ROW(OLD.scope_id,OLD.capability,OLD.target_id,OLD.horizon,OLD.feature_contract_id)
   OR NEW.head_version<>OLD.head_version+1 OR a.expected_head_version<>OLD.head_version
   OR a.prior_activation_id IS DISTINCT FROM OLD.activation_id
   OR (a.action='REVOKE' AND a.grant_id<>OLD.grant_id) THEN
   RAISE EXCEPTION 'FEP_HEAD_CAS_INVALID';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER controlled_head BEFORE INSERT OR UPDATE OR DELETE ON fep.deployment_heads
 FOR EACH ROW EXECUTE FUNCTION fep.validate_deployment_head();

CREATE FUNCTION fep.validate_fold_cutoff() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d fep.datasets%ROWTYPE;
BEGIN
 SELECT * INTO STRICT d FROM fep.datasets WHERE dataset_id=NEW.dataset_id;
 IF NEW.fold_dataset_cutoff>d.dataset_cutoff THEN RAISE EXCEPTION 'FEP_FOLD_CUTOFF_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fold_cutoff_guard BEFORE INSERT ON fep.dataset_fold_cutoffs
 FOR EACH ROW EXECUTE FUNCTION fep.validate_fold_cutoff();

CREATE FUNCTION fep.validate_fold_label_selection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c timestamptz; b fep.label_source_bindings%ROWTYPE; l fep.label_revisions%ROWTYPE;
BEGIN
 SELECT fold_dataset_cutoff INTO STRICT c FROM fep.dataset_fold_cutoffs
 WHERE dataset_id=NEW.dataset_id AND fold_id=NEW.fold_id AND partition_name=NEW.partition_name;
 IF NEW.selected_label_revision IS NOT NULL THEN
  SELECT * INTO STRICT l FROM fep.label_revisions WHERE observation_id=NEW.observation_id
   AND target_id=NEW.target_id AND revision=NEW.selected_label_revision;
  SELECT * INTO STRICT b FROM fep.label_source_bindings WHERE binding_id=l.binding_id;
  IF b.source_fact_available_at>c OR b.label_revision_available_at>c THEN
   RAISE EXCEPTION 'FEP_FOLD_REVISION_NOT_VISIBLE';
  END IF;
  IF NEW.eligibility='ELIGIBLE' AND (b.label_training_mature_at>c OR NOT l.training_allowed) THEN
   RAISE EXCEPTION 'FEP_FOLD_LABEL_NOT_TRAINABLE';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fold_label_guard BEFORE INSERT ON fep.dataset_fold_label_selection
 FOR EACH ROW EXECUTE FUNCTION fep.validate_fold_label_selection();

CREATE FUNCTION fep.validate_dataset_row() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE selected fep.dataset_fold_label_selection%ROWTYPE; o fep.observations%ROWTYPE;
BEGIN
 -- Serialize this dataset/fold assembly so concurrent rows cannot evade phase separation.
 PERFORM pg_advisory_xact_lock(hashtextextended(NEW.dataset_id||':'||NEW.fold_id,0));
 SELECT * INTO STRICT selected FROM fep.dataset_fold_label_selection
 WHERE dataset_id=NEW.dataset_id AND fold_id=NEW.fold_id AND partition_name=NEW.partition_name
  AND observation_id=NEW.observation_id AND target_id=NEW.target_id;
 IF selected.eligibility<>'ELIGIBLE' THEN RAISE EXCEPTION 'FEP_DATASET_ROW_NOT_ELIGIBLE'; END IF;
 SELECT * INTO STRICT o FROM fep.observations WHERE observation_id=NEW.observation_id;
 IF EXISTS (SELECT 1 FROM fep.dataset_rows r JOIN fep.observations x ON x.observation_id=r.observation_id
  WHERE r.dataset_id=NEW.dataset_id AND r.fold_id=NEW.fold_id AND r.partition_name<>NEW.partition_name
  AND (x.trade_date=o.trade_date OR x.observation_id=o.observation_id
   OR (o.episode_key IS NOT NULL AND x.scope_id=o.scope_id AND x.entity_id=o.entity_id AND x.episode_key=o.episode_key))) THEN
  RAISE EXCEPTION 'FEP_FOLD_PHASE_OVERLAP';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER dataset_row_guard BEFORE INSERT ON fep.dataset_rows
 FOR EACH ROW EXECUTE FUNCTION fep.validate_dataset_row();

CREATE FUNCTION fep.validate_acceptance_grant() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE k fep.permission_keys%ROWTYPE; r fep.prediction_runs%ROWTYPE;
BEGIN
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=NEW.grant_id;
 SELECT * INTO STRICT r FROM fep.prediction_runs WHERE run_id=NEW.run_id;
 IF r.model_set_id<>k.model_set_id THEN RAISE EXCEPTION 'FEP_ACCEPTANCE_MODELSET_MISMATCH'; END IF;
 -- Acceptance validator must additionally check exact activation ALLOW at inference,
 -- current revocations for live display, and matching CHAMPION result scope/target/horizon/schema.
 RETURN NEW;
END $$;
CREATE TRIGGER acceptance_grant_guard BEFORE INSERT ON fep.acceptance_receipts
 FOR EACH ROW EXECUTE FUNCTION fep.validate_acceptance_grant();
-- DESCRIPTIVE_DISPLAY/MODEL_DISPLAY/PRIORITY_USE grants cover CHAMPION only.
-- Baseline/challenger predictions in the same set stay diagnostic/Shadow; a
-- champion grant must not be reused to expose them as accepted production output.
-- SHADOW_INFERENCE may compute set members, but confers no production display.

-- Phase manifest: FIT cutoff <= this fold's fit_started; TUNE cutoff <= selection_started;
-- CALIBRATION cutoff <= calibrator_fit_started; OUTER_TEST cutoff is the frozen scoring
-- knowledge deadline and can be later than model fit. OUTER_TEST rows are evaluation-only.
-- phase_started_at is actual start of the respective consumer (evaluation start for TEST),
-- not a substituted global training start. E1/E3 validator must match these named times
-- to dataset_fold_cutoffs and run phase_manifest, and prohibit TEST rows as fit inputs.
-- Episode identity is (scope_id,entity_id,episode_key), not a reused entity-local string alone.

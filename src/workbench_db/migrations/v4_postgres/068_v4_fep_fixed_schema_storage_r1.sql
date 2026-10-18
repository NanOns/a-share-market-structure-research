-- Fixed V4 FEP storage. This migration ports the frozen 028-030, 032-033 contracts into v4;
-- it does not create a standalone FEP schema or change v4 schema ownership.
SET search_path TO v4, pg_catalog;

-- Dedicated non-login roles; the shared v4 schema itself remains owned by postgres.
DO $$ DECLARE name text; r record; BEGIN
 FOREACH name IN ARRAY ARRAY['fep_schema_owner','fep_cas_owner','fep_application','fep_deployer','fep_adapter','fep_auditor'] LOOP
  SELECT * INTO r FROM pg_roles WHERE rolname=name;
  IF FOUND THEN
   IF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolcanlogin OR r.rolinherit OR r.rolbypassrls
    OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid OR roleid=r.oid) THEN
    RAISE EXCEPTION 'FEP_ROLE_IDENTITY_CONFLICT:%',name;
   END IF;
  ELSE
   EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',name);
  END IF;
 END LOOP;
END $$;

-- Source: immutable historical 028_fep_schema_v1.sql; schema-qualified objects redirected to fixed v4.
-- FEP E1 / FEP_SCHEMA_DESIGN_V2 exact table/domain/key projection.
CREATE DOMAIN v4.sha256 AS text CHECK (VALUE ~ '^[0-9a-f]{64}$');

CREATE TABLE v4.contracts (
 contract_id text PRIMARY KEY, family text NOT NULL, version text NOT NULL,
 body jsonb NOT NULL CHECK(jsonb_typeof(body)='object'), digest v4.sha256 NOT NULL UNIQUE,
 created_at timestamptz NOT NULL, UNIQUE(family,version)
);
CREATE TABLE v4.scopes (
 scope_id text PRIMARY KEY, entity_type text NOT NULL CHECK(entity_type IN ('STOCK','SECTOR','MARKET')),
 observation_kind text NOT NULL CHECK(observation_kind IN ('ENTRY','DAILY_LANDMARK','MARKET_WIDE','MARKET_DAY','ROTATION_ENTRY')),
 signal_type text NOT NULL, feature_variant text NOT NULL, namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
 observation_contract_id text NOT NULL REFERENCES v4.contracts(contract_id), digest v4.sha256 NOT NULL UNIQUE
);
CREATE TABLE v4.field_registry (
 feature_contract_id text NOT NULL REFERENCES v4.contracts(contract_id), field_name text NOT NULL,
 producer text NOT NULL, source_field text NOT NULL, data_type text NOT NULL, unit text NOT NULL,
 nullable boolean NOT NULL, required boolean NOT NULL, availability_rule text NOT NULL,
 quality_allowlist jsonb NOT NULL, window_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 PRIMARY KEY(feature_contract_id,field_name)
);
CREATE TABLE v4.field_scope (
 feature_contract_id text NOT NULL, field_name text NOT NULL, scope_id text NOT NULL REFERENCES v4.scopes(scope_id),
 PRIMARY KEY(feature_contract_id,field_name,scope_id),
 FOREIGN KEY(feature_contract_id,field_name) REFERENCES v4.field_registry(feature_contract_id,field_name)
);
CREATE TABLE v4.targets (
 target_id text PRIMARY KEY, contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 scope_id text NOT NULL REFERENCES v4.scopes(scope_id), horizon integer NOT NULL CHECK(horizon IN (1,3,5,10,20)),
 unit text NOT NULL, value_kind text NOT NULL CHECK(value_kind IN ('NUMERIC','BINARY','CLASS')),
 formula text NOT NULL, risk_set jsonb NOT NULL, allowed_quality jsonb NOT NULL,
 enabled boolean NOT NULL DEFAULT false, UNIQUE(target_id,scope_id,horizon)
);
CREATE TABLE v4.observations (
 observation_id text PRIMARY KEY, scope_id text NOT NULL REFERENCES v4.scopes(scope_id),
 entity_id text NOT NULL, trade_date date NOT NULL, signal_key text NOT NULL,
 episode_key text, core_signal_contract_id text NOT NULL, slot_deadline timestamptz NOT NULL,
 UNIQUE(scope_id,entity_id,trade_date,signal_key), UNIQUE(observation_id,scope_id)
);
CREATE TABLE v4.observation_revisions (
 observation_id text NOT NULL REFERENCES v4.observations(observation_id), revision integer NOT NULL CHECK(revision>0),
 publication_id text NOT NULL REFERENCES v4.publications(publication_id),
 feature_cutoff timestamptz NOT NULL, dependency_manifest jsonb NOT NULL,
 dependency_digest v4.sha256 NOT NULL, enrichment_token text NOT NULL, -- NONE is explicit
 evidence_origin text NOT NULL CHECK(evidence_origin IN ('PIT_OBSERVED','RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED','DIAGNOSTIC_NON_PIT')),
 execution_mode text NOT NULL CHECK(execution_mode IN ('SHADOW','PRODUCTION','REPLAY')),
 supersedes_revision integer, created_at timestamptz NOT NULL,
 PRIMARY KEY(observation_id,revision), UNIQUE(observation_id,dependency_digest),
 FOREIGN KEY(observation_id,supersedes_revision) REFERENCES v4.observation_revisions(observation_id,revision),
 CHECK(supersedes_revision IS NULL OR supersedes_revision<revision)
);
CREATE TABLE v4.snapshots (
 snapshot_id text PRIMARY KEY, observation_id text NOT NULL, observation_revision integer NOT NULL,
 feature_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 feature_digest v4.sha256 NOT NULL, quality_digest v4.sha256 NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY(observation_id,observation_revision) REFERENCES v4.observation_revisions(observation_id,revision),
 UNIQUE(observation_id,observation_revision,feature_contract_id),
 UNIQUE(snapshot_id,observation_id), UNIQUE(snapshot_id,feature_contract_id)
);
CREATE TABLE v4.feature_values (
 snapshot_id text NOT NULL, feature_contract_id text NOT NULL, field_name text NOT NULL,
 value jsonb, quality text NOT NULL, reason text, source_digest v4.sha256 NOT NULL,
 PRIMARY KEY(snapshot_id,field_name),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES v4.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(feature_contract_id,field_name) REFERENCES v4.field_registry(feature_contract_id,field_name)
);
-- Binding is imported exclusively from V4-15 authority (or versioned State/Event authority).
-- No fake FK to a nonexistent Forward table: E1 must install a validated adapter/trigger
-- with exact upstream key+revision+digest readback before accepting any binding.
CREATE TABLE v4.label_source_bindings (
 binding_id text PRIMARY KEY, authority_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 upstream_key text NOT NULL, upstream_revision text NOT NULL, source_digest v4.sha256 NOT NULL,
 label_event_end date NOT NULL, source_fact_available_at timestamptz NOT NULL,
 label_training_mature_at timestamptz NOT NULL, label_revision_available_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL, UNIQUE(authority_contract_id,upstream_key,upstream_revision,source_digest),
 CHECK(label_revision_available_at>=source_fact_available_at)
);
CREATE TABLE v4.label_revisions (
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 revision integer NOT NULL CHECK(revision>0), binding_id text NOT NULL REFERENCES v4.label_source_bindings(binding_id),
 numeric_value double precision, class_value text, quality text NOT NULL, training_allowed boolean NOT NULL,
 target_digest v4.sha256 NOT NULL, supersedes_revision integer,
 PRIMARY KEY(observation_id,target_id,revision),
 UNIQUE(observation_id,target_id,revision,target_digest),
 FOREIGN KEY(observation_id,scope_id) REFERENCES v4.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES v4.targets(target_id,scope_id,horizon),
 FOREIGN KEY(observation_id,target_id,supersedes_revision) REFERENCES v4.label_revisions(observation_id,target_id,revision),
 CHECK(supersedes_revision IS NULL OR supersedes_revision<revision),
 CHECK(NOT(numeric_value IS NOT NULL AND class_value IS NOT NULL)),
 CHECK(numeric_value IS NULL OR (numeric_value>'-Infinity'::float8 AND numeric_value<'Infinity'::float8)),
 CHECK(NOT training_allowed OR numeric_value IS NOT NULL OR class_value IS NOT NULL)
);
CREATE TABLE v4.datasets (
 dataset_id text PRIMARY KEY, scope_id text NOT NULL REFERENCES v4.scopes(scope_id),
 feature_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 policy_contract_id text NOT NULL REFERENCES v4.contracts(contract_id), dataset_cutoff timestamptz NOT NULL,
 manifest jsonb NOT NULL, digest v4.sha256 NOT NULL UNIQUE, created_at timestamptz NOT NULL,
 UNIQUE(dataset_id,scope_id,feature_contract_id)
);
-- Full expected denominator exists even when a label does not yet exist.
CREATE TABLE v4.dataset_eligibility_ledger (
 dataset_id text NOT NULL REFERENCES v4.datasets(dataset_id),
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 status text NOT NULL CHECK(status IN ('EXPECTED','SCOPE_EXCLUDED')),
 reason text,
 PRIMARY KEY(dataset_id,observation_id,target_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES v4.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES v4.targets(target_id,scope_id,horizon),
 FOREIGN KEY(target_id) REFERENCES v4.targets(target_id)
);
-- Dataset global cutoff is a manifest upper bound, never a fold selection cutoff.
-- Fit/tune/calibration/outer-test phases have distinct as-of cutoffs; all are frozen.
CREATE TABLE v4.dataset_fold_cutoffs (
 dataset_id text NOT NULL REFERENCES v4.datasets(dataset_id), fold_id text NOT NULL,
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST')),
 fold_dataset_cutoff timestamptz NOT NULL, phase_started_at timestamptz NOT NULL, selection_policy_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 split_digest v4.sha256 NOT NULL,
 PRIMARY KEY(dataset_id,fold_id,partition_name), CHECK(fold_dataset_cutoff<=phase_started_at)
);
CREATE TABLE v4.dataset_fold_label_selection (
 dataset_id text NOT NULL, fold_id text NOT NULL, partition_name text NOT NULL,
 observation_id text NOT NULL, target_id text NOT NULL,
 selected_label_revision integer, selected_label_digest v4.sha256, selection_reason text NOT NULL,
 eligibility text NOT NULL CHECK(eligibility IN ('ELIGIBLE','PENDING','MISSING_LABEL','QUALITY_EXCLUDED','SCOPE_EXCLUDED')),
 PRIMARY KEY(dataset_id,fold_id,partition_name,observation_id,target_id),
 FOREIGN KEY(dataset_id,fold_id,partition_name) REFERENCES v4.dataset_fold_cutoffs(dataset_id,fold_id,partition_name),
 FOREIGN KEY(dataset_id,observation_id,target_id) REFERENCES v4.dataset_eligibility_ledger(dataset_id,observation_id,target_id),
 FOREIGN KEY(observation_id,target_id,selected_label_revision,selected_label_digest)
 REFERENCES v4.label_revisions(observation_id,target_id,revision,target_digest),
 UNIQUE(dataset_id,fold_id,partition_name,observation_id,target_id,selected_label_revision,selected_label_digest),
 CHECK((selected_label_revision IS NULL)=(selected_label_digest IS NULL)),
 CHECK(eligibility<>'ELIGIBLE' OR selected_label_revision IS NOT NULL)
);
CREATE TABLE v4.dataset_rows (
 dataset_id text NOT NULL, scope_id text NOT NULL, feature_contract_id text NOT NULL,
 observation_id text NOT NULL, snapshot_id text NOT NULL, target_id text NOT NULL,
 label_revision integer NOT NULL, selected_label_digest v4.sha256 NOT NULL, weight double precision NOT NULL CHECK(weight>0 AND weight<'Infinity'::float8),
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST')),
 fold_id text NOT NULL, exclusion_reason text,
 PRIMARY KEY(dataset_id,observation_id,target_id,fold_id,partition_name),
 FOREIGN KEY(dataset_id,fold_id,partition_name,observation_id,target_id,label_revision,selected_label_digest)
 REFERENCES v4.dataset_fold_label_selection(dataset_id,fold_id,partition_name,observation_id,target_id,selected_label_revision,selected_label_digest),
 FOREIGN KEY(dataset_id,observation_id,target_id) REFERENCES v4.dataset_eligibility_ledger(dataset_id,observation_id,target_id),
 FOREIGN KEY(dataset_id,scope_id,feature_contract_id) REFERENCES v4.datasets(dataset_id,scope_id,feature_contract_id),
 FOREIGN KEY(observation_id,scope_id) REFERENCES v4.observations(observation_id,scope_id),
 FOREIGN KEY(snapshot_id,observation_id) REFERENCES v4.snapshots(snapshot_id,observation_id),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES v4.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(observation_id,target_id,label_revision) REFERENCES v4.label_revisions(observation_id,target_id,revision)
);
CREATE TABLE v4.training_runs (
 training_run_id text PRIMARY KEY, dataset_id text NOT NULL REFERENCES v4.datasets(dataset_id),
 fold_id text NOT NULL, phase_manifest jsonb NOT NULL CHECK(jsonb_typeof(phase_manifest)='object'),
 experiment_lineage text NOT NULL, parameter_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 code_commit text NOT NULL, runtime_manifest jsonb NOT NULL, split_manifest jsonb NOT NULL,
 fit_started_at timestamptz NOT NULL, fit_finished_at timestamptz NOT NULL,
 calibration_finished_at timestamptz NOT NULL, artifact_path text NOT NULL, artifact_digest v4.sha256 NOT NULL,
 CHECK(fit_started_at<=fit_finished_at AND fit_finished_at<=calibration_finished_at)
);
CREATE TABLE v4.models (
 model_id text PRIMARY KEY, training_run_id text NOT NULL REFERENCES v4.training_runs(training_run_id),
 scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL REFERENCES v4.contracts(contract_id), family text NOT NULL,
 transform_digest v4.sha256 NOT NULL, calibration_digest v4.sha256 NOT NULL, ood_digest v4.sha256 NOT NULL,
 model_digest v4.sha256 NOT NULL UNIQUE, accepted_at timestamptz NOT NULL,
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES v4.targets(target_id,scope_id,horizon),
 UNIQUE(model_id,scope_id,target_id,horizon,feature_contract_id)
);
CREATE TABLE v4.model_sets (
 model_set_id text PRIMARY KEY, policy_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 digest v4.sha256 NOT NULL UNIQUE, accepted_at timestamptz NOT NULL
);
CREATE TABLE v4.model_set_members (
 model_set_id text NOT NULL REFERENCES v4.model_sets(model_set_id), scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL, feature_contract_id text NOT NULL, model_id text NOT NULL,
 role text NOT NULL CHECK(role IN ('CHAMPION','BASELINE','CHALLENGER')),
 PRIMARY KEY(model_set_id,scope_id,target_id,horizon,role),
 FOREIGN KEY(model_id,scope_id,target_id,horizon,feature_contract_id)
 REFERENCES v4.models(model_id,scope_id,target_id,horizon,feature_contract_id),
 UNIQUE(model_set_id,model_id),
 UNIQUE(model_set_id,scope_id,target_id,horizon,feature_contract_id,role)
);
-- The exact permission tuple is immutable and model-set-specific. Entity/variant
-- identity is inherited from scope; feature_contract is fixed explicitly.
CREATE TABLE v4.permission_keys (
 grant_id text PRIMARY KEY, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL, model_set_id text NOT NULL, model_role text NOT NULL DEFAULT 'CHAMPION',
 capability text NOT NULL CHECK(capability IN ('SHADOW_INFERENCE','DESCRIPTIVE_DISPLAY','MODEL_DISPLAY','PRIORITY_USE')),
 CHECK(model_role='CHAMPION'),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES v4.targets(target_id,scope_id,horizon),
 FOREIGN KEY(model_set_id,scope_id,target_id,horizon,feature_contract_id,model_role)
 REFERENCES v4.model_set_members(model_set_id,scope_id,target_id,horizon,feature_contract_id,role),
 UNIQUE(scope_id,target_id,horizon,feature_contract_id,model_set_id,capability),
 UNIQUE(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability)
);
CREATE TABLE v4.activations (
 activation_id text PRIMARY KEY, grant_id text NOT NULL REFERENCES v4.permission_keys(grant_id),
 action text NOT NULL CHECK(action IN ('ALLOW','REVOKE')),
 effective_at timestamptz NOT NULL, recorded_at timestamptz NOT NULL,
 prior_activation_id text REFERENCES v4.activations(activation_id), expected_head_version bigint NOT NULL CHECK(expected_head_version>=0),
 receipt_digest v4.sha256 NOT NULL, UNIQUE(activation_id,grant_id), CHECK(recorded_at<=effective_at)
);
-- This is a controlled mutable projection, NOT an append-only fact table.
-- Model-set is the payload, not part of the head key, so a replacement competes for the same head.
CREATE TABLE v4.deployment_heads (
 scope_id text NOT NULL, capability text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 feature_contract_id text NOT NULL, model_set_id text NOT NULL, grant_id text NOT NULL,
 activation_id text NOT NULL, head_version bigint NOT NULL CHECK(head_version>0), updated_at timestamptz NOT NULL,
 PRIMARY KEY(scope_id,capability,target_id,horizon,feature_contract_id),
 FOREIGN KEY(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability)
 REFERENCES v4.permission_keys(grant_id,scope_id,target_id,horizon,feature_contract_id,model_set_id,capability),
 FOREIGN KEY(activation_id,grant_id) REFERENCES v4.activations(activation_id,grant_id)
);
CREATE TABLE v4.deployment_change_receipts (
 activation_id text PRIMARY KEY REFERENCES v4.activations(activation_id),
 grant_id text NOT NULL REFERENCES v4.permission_keys(grant_id), expected_prior_activation_id text,
 expected_head_version bigint NOT NULL, new_head_version bigint NOT NULL, request_id text NOT NULL UNIQUE,
 accepted_at timestamptz NOT NULL, checks jsonb NOT NULL,
 CHECK(new_head_version=expected_head_version+1),
 FOREIGN KEY(activation_id,grant_id) REFERENCES v4.activations(activation_id,grant_id)
);
CREATE TABLE v4.prediction_slots (
 slot_id text PRIMARY KEY, observation_id text NOT NULL, scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL, model_family_scope text NOT NULL,
 selection_cutoff timestamptz NOT NULL, deadline timestamptz NOT NULL,
 selection_status text NOT NULL CHECK(selection_status IN ('PLANNED','NO_ACTIVE_MODEL','SELECTED')),
 FOREIGN KEY(observation_id,scope_id) REFERENCES v4.observations(observation_id,scope_id),
 FOREIGN KEY(target_id,scope_id,horizon) REFERENCES v4.targets(target_id,scope_id,horizon),
 UNIQUE(observation_id,target_id,horizon,model_family_scope),
 UNIQUE(slot_id,observation_id,scope_id,target_id,horizon), CHECK(selection_cutoff<=deadline)
);
CREATE TABLE v4.slot_model_bindings (
 slot_id text PRIMARY KEY, observation_id text NOT NULL, scope_id text NOT NULL,
 target_id text NOT NULL, horizon integer NOT NULL,
 model_set_id text NOT NULL REFERENCES v4.model_sets(model_set_id),
 selected_at timestamptz NOT NULL, selection_receipt_digest v4.sha256 NOT NULL,
 FOREIGN KEY(slot_id,observation_id,scope_id,target_id,horizon)
 REFERENCES v4.prediction_slots(slot_id,observation_id,scope_id,target_id,horizon),
 UNIQUE(slot_id,observation_id,scope_id,target_id,horizon,model_set_id)
);
CREATE TABLE v4.prediction_runs (
 run_id text PRIMARY KEY, publication_id text NOT NULL REFERENCES v4.publications(publication_id),
 model_set_id text NOT NULL REFERENCES v4.model_sets(model_set_id), input_digest v4.sha256 NOT NULL,
 started_at timestamptz NOT NULL, finished_at timestamptz NOT NULL,
 output_digest v4.sha256 NOT NULL, counts jsonb NOT NULL, CHECK(started_at<=finished_at),
 UNIQUE(run_id,model_set_id)
);
CREATE TABLE v4.predictions (
 prediction_id text PRIMARY KEY, slot_id text NOT NULL, revision integer NOT NULL CHECK(revision>0),
 observation_id text NOT NULL, scope_id text NOT NULL, target_id text NOT NULL, horizon integer NOT NULL,
 model_set_id text NOT NULL, model_id text NOT NULL, feature_contract_id text NOT NULL, snapshot_id text NOT NULL,
 run_id text NOT NULL, prediction_evidence text NOT NULL CHECK(prediction_evidence IN
 ('FIRST_OBSERVED','LATE_RECONSTRUCTION','CORRECTED_RECONSTRUCTION','HISTORICAL_SIMULATION')),
 quality text NOT NULL, unknown_reason text, outputs jsonb NOT NULL, support jsonb NOT NULL,
 output_digest v4.sha256 NOT NULL, accepted_at timestamptz NOT NULL, supersedes_id text,
 FOREIGN KEY(slot_id,observation_id,scope_id,target_id,horizon,model_set_id)
 REFERENCES v4.slot_model_bindings(slot_id,observation_id,scope_id,target_id,horizon,model_set_id),
 FOREIGN KEY(snapshot_id,observation_id) REFERENCES v4.snapshots(snapshot_id,observation_id),
 FOREIGN KEY(snapshot_id,feature_contract_id) REFERENCES v4.snapshots(snapshot_id,feature_contract_id),
 FOREIGN KEY(model_id,scope_id,target_id,horizon,feature_contract_id)
 REFERENCES v4.models(model_id,scope_id,target_id,horizon,feature_contract_id),
 FOREIGN KEY(model_set_id,model_id) REFERENCES v4.model_set_members(model_set_id,model_id),
 FOREIGN KEY(run_id,model_set_id) REFERENCES v4.prediction_runs(run_id,model_set_id),
 UNIQUE(slot_id,model_id,revision), UNIQUE(prediction_id,slot_id,model_id),
 FOREIGN KEY(supersedes_id,slot_id,model_id) REFERENCES v4.predictions(prediction_id,slot_id,model_id),
 CHECK(supersedes_id IS NULL OR supersedes_id<>prediction_id)
);
CREATE UNIQUE INDEX prediction_first_observed ON v4.predictions(slot_id,model_id)
 WHERE prediction_evidence='FIRST_OBSERVED';
-- Freeze selected model-set once per slot. A later model is a new experiment scope,
-- not a replacement FIRST_OBSERVED of the original slot.
CREATE TABLE v4.slot_receipts (
 slot_id text NOT NULL REFERENCES v4.prediction_slots(slot_id), receipt_id text PRIMARY KEY,
 recorded_at timestamptz NOT NULL, status text NOT NULL CHECK(status IN ('MISSED','FAILED','PARTIAL','ACCEPTED')),
 payload jsonb NOT NULL, receipt_digest v4.sha256 NOT NULL
);
-- Each accepted target/capability uses the same exact grant key as activation/readback.
CREATE TABLE v4.acceptance_receipts (
 receipt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES v4.prediction_runs(run_id),
 accepted_at timestamptz NOT NULL, grant_id text NOT NULL REFERENCES v4.permission_keys(grant_id),
 activation_id text NOT NULL,
 validation_contract_id text NOT NULL REFERENCES v4.contracts(contract_id), checks jsonb NOT NULL,
 UNIQUE(run_id,grant_id), UNIQUE(receipt_id,run_id,grant_id),
 FOREIGN KEY(activation_id,grant_id) REFERENCES v4.activations(activation_id,grant_id)
);
CREATE TABLE v4.reports (
 report_id text PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('CALIBRATION','EVALUATION','DRIFT','PROMOTION','MISSINGNESS')),
 model_id text REFERENCES v4.models(model_id), dataset_id text REFERENCES v4.datasets(dataset_id),
 cutoff timestamptz NOT NULL, contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 manifest jsonb NOT NULL, results jsonb NOT NULL, digest v4.sha256 NOT NULL UNIQUE
);
CREATE TABLE v4.priority_projection (
 projection_id text PRIMARY KEY, run_id text NOT NULL REFERENCES v4.prediction_runs(run_id),
 observation_id text NOT NULL REFERENCES v4.observations(observation_id),
 priority_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 core_rank_identity v4.sha256 NOT NULL, axis_state text NOT NULL,
 axis_values jsonb NOT NULL, prediction_refs jsonb NOT NULL,
 UNIQUE(run_id,observation_id,priority_contract_id), UNIQUE(projection_id,run_id)
);
-- Multi-target priority rows must cite every target's exact PRIORITY_USE grant;
-- a successful T5 grant cannot authorize another target or T20.
CREATE TABLE v4.priority_projection_grants (
 projection_id text NOT NULL REFERENCES v4.priority_projection(projection_id),
 grant_id text NOT NULL REFERENCES v4.permission_keys(grant_id), run_id text NOT NULL,
 permission_receipt_id text NOT NULL,
 PRIMARY KEY(projection_id,grant_id),
 FOREIGN KEY(projection_id,run_id) REFERENCES v4.priority_projection(projection_id,run_id),
 FOREIGN KEY(permission_receipt_id,run_id,grant_id) REFERENCES v4.acceptance_receipts(receipt_id,run_id,grant_id)
);
CREATE INDEX label_by_binding ON v4.label_revisions(binding_id);
CREATE INDEX label_available ON v4.label_source_bindings(label_revision_available_at,label_training_mature_at);
CREATE INDEX observation_date_scope ON v4.observations(trade_date,scope_id);
CREATE INDEX dataset_cutoff ON v4.datasets(scope_id,dataset_cutoff);
CREATE INDEX prediction_readback ON v4.predictions(observation_id,model_set_id,target_id,revision);
CREATE INDEX activation_asof ON v4.activations(grant_id,effective_at);
CREATE INDEX fold_label_asof ON v4.dataset_fold_cutoffs(dataset_id,fold_id,partition_name,fold_dataset_cutoff);


-- Source: immutable historical 029_fep_append_only_v1.sql; schema-qualified objects redirected to fixed v4.
CREATE FUNCTION v4.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'FEP_APPEND_ONLY'; END $$;
-- Explicit guards for this version; every future fact table migration must
-- create its own guard and be checked against the registry. No automatic inheritance.
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.contracts FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.scopes FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.field_registry FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.field_scope FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.targets FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.observations FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.observation_revisions FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.snapshots FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.feature_values FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.label_source_bindings FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.label_revisions FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.datasets FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.dataset_eligibility_ledger FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.dataset_fold_cutoffs FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.dataset_fold_label_selection FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.dataset_rows FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.training_runs FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.models FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.model_sets FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.model_set_members FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.permission_keys FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.activations FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.deployment_change_receipts FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.prediction_slots FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.slot_model_bindings FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.prediction_runs FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.predictions FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.slot_receipts FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.acceptance_receipts FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.reports FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.priority_projection FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.priority_projection_grants FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();

-- Source: immutable historical 030_fep_validation_cas_v1.sql; schema-qualified objects redirected to fixed v4.
CREATE FUNCTION v4.cas_deploy(
 p_grant_id text, p_activation_id text, p_action text, p_expected_version bigint,
 p_expected_prior text, p_request_id text, p_receipt_digest v4.sha256, p_checks jsonb
) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,v4 AS $$
DECLARE k v4.permission_keys%ROWTYPE; prior v4.deployment_change_receipts%ROWTYPE; a v4.activations%ROWTYPE; n integer; ts timestamptz := clock_timestamp();
BEGIN
 IF p_grant_id IS NULL OR p_activation_id IS NULL OR p_action IS NULL OR p_expected_version IS NULL
  OR p_request_id IS NULL OR p_receipt_digest IS NULL OR p_checks IS NULL THEN
  RAISE EXCEPTION 'FEP_REQUIRED_CAS_PARAMETER_NULL';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('v4.request:'||p_request_id,0));
 SELECT * INTO STRICT k FROM v4.permission_keys WHERE grant_id=p_grant_id;
 PERFORM pg_advisory_xact_lock(hashtextextended('v4.head:'||jsonb_build_array(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id)::text,0));
 SELECT * INTO prior FROM v4.deployment_change_receipts WHERE request_id=p_request_id;
 IF FOUND THEN
  SELECT * INTO STRICT a FROM v4.activations WHERE activation_id=prior.activation_id;
  IF prior.grant_id IS DISTINCT FROM p_grant_id OR prior.activation_id IS DISTINCT FROM p_activation_id OR a.action IS DISTINCT FROM p_action
   OR prior.expected_head_version IS DISTINCT FROM p_expected_version OR prior.expected_prior_activation_id IS DISTINCT FROM p_expected_prior
   OR a.receipt_digest IS DISTINCT FROM p_receipt_digest OR prior.checks IS DISTINCT FROM p_checks THEN
   RAISE EXCEPTION 'FEP_IDEMPOTENCY_CONFLICT';
  END IF;
  RETURN prior.new_head_version;
 END IF;
 IF p_expected_version<0 OR p_action NOT IN ('ALLOW','REVOKE') THEN RAISE EXCEPTION 'FEP_INVALID_CAS_INPUT'; END IF;
 INSERT INTO v4.activations(activation_id,grant_id,action,effective_at,recorded_at,prior_activation_id,expected_head_version,receipt_digest)
 VALUES(p_activation_id,p_grant_id,p_action,ts,ts,p_expected_prior,p_expected_version,p_receipt_digest);
 IF p_expected_version=0 THEN
  IF p_expected_prior IS NOT NULL OR p_action='REVOKE' THEN RAISE EXCEPTION 'FEP_INITIAL_PRIOR_INVALID'; END IF;
  INSERT INTO v4.deployment_heads(scope_id,capability,target_id,horizon,feature_contract_id,model_set_id,grant_id,activation_id,head_version,updated_at)
  VALUES(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id,k.model_set_id,k.grant_id,p_activation_id,1,ts)
  ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS n=ROW_COUNT;
 ELSE
  UPDATE v4.deployment_heads SET model_set_id=k.model_set_id,grant_id=k.grant_id,
   activation_id=p_activation_id,head_version=p_expected_version+1,updated_at=ts
  WHERE scope_id=k.scope_id AND capability=k.capability AND target_id=k.target_id
   AND horizon=k.horizon AND feature_contract_id=k.feature_contract_id
   AND head_version=p_expected_version AND activation_id IS NOT DISTINCT FROM p_expected_prior
   AND (p_action<>'REVOKE' OR grant_id=p_grant_id);
  GET DIAGNOSTICS n=ROW_COUNT;
 END IF;
 IF n<>1 THEN RAISE EXCEPTION 'FEP_CAS_CONFLICT'; END IF;
 INSERT INTO v4.deployment_change_receipts(activation_id,grant_id,expected_prior_activation_id,expected_head_version,new_head_version,request_id,accepted_at,checks)
 VALUES(p_activation_id,p_grant_id,p_expected_prior,p_expected_version,p_expected_version+1,p_request_id,ts,p_checks);
 RETURN p_expected_version+1;
END $$;
-- Conflict throws: activation, receipt and pointer changes all roll back together.
-- Exact historical activation used by the slot remains frozen. API current grant
-- requires deployment_heads target's accepted ALLOW; REVOKE denies that exact key.

REVOKE ALL ON FUNCTION v4.cas_deploy(text,text,text,bigint,text,text,v4.sha256,jsonb) FROM PUBLIC;
REVOKE ALL ON v4.deployment_heads FROM PUBLIC;
-- E1 must grant only EXECUTE to a sealed deployer role, not direct table DML;
-- SECURITY DEFINER owner is a dedicated trusted role with fixed search_path.

CREATE FUNCTION v4.validate_deployment_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a v4.activations%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'FEP_HEAD_DELETE_FORBIDDEN'; END IF;
 SELECT * INTO STRICT a FROM v4.activations WHERE activation_id=NEW.activation_id;
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
CREATE TRIGGER controlled_head BEFORE INSERT OR UPDATE OR DELETE ON v4.deployment_heads
 FOR EACH ROW EXECUTE FUNCTION v4.validate_deployment_head();

CREATE FUNCTION v4.validate_fold_cutoff() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d v4.datasets%ROWTYPE;
BEGIN
 SELECT * INTO STRICT d FROM v4.datasets WHERE dataset_id=NEW.dataset_id;
 IF NEW.fold_dataset_cutoff>d.dataset_cutoff THEN RAISE EXCEPTION 'FEP_FOLD_CUTOFF_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fold_cutoff_guard BEFORE INSERT ON v4.dataset_fold_cutoffs
 FOR EACH ROW EXECUTE FUNCTION v4.validate_fold_cutoff();

CREATE FUNCTION v4.validate_fold_label_selection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c timestamptz; b v4.label_source_bindings%ROWTYPE; l v4.label_revisions%ROWTYPE;
BEGIN
 SELECT fold_dataset_cutoff INTO STRICT c FROM v4.dataset_fold_cutoffs
 WHERE dataset_id=NEW.dataset_id AND fold_id=NEW.fold_id AND partition_name=NEW.partition_name;
 IF NEW.selected_label_revision IS NOT NULL THEN
  SELECT * INTO STRICT l FROM v4.label_revisions WHERE observation_id=NEW.observation_id
   AND target_id=NEW.target_id AND revision=NEW.selected_label_revision;
  SELECT * INTO STRICT b FROM v4.label_source_bindings WHERE binding_id=l.binding_id;
  IF b.source_fact_available_at>c OR b.label_revision_available_at>c THEN
   RAISE EXCEPTION 'FEP_FOLD_REVISION_NOT_VISIBLE';
  END IF;
  IF NEW.eligibility='ELIGIBLE' AND (b.label_training_mature_at>c OR NOT l.training_allowed) THEN
   RAISE EXCEPTION 'FEP_FOLD_LABEL_NOT_TRAINABLE';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fold_label_guard BEFORE INSERT ON v4.dataset_fold_label_selection
 FOR EACH ROW EXECUTE FUNCTION v4.validate_fold_label_selection();

CREATE FUNCTION v4.validate_dataset_row() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE selected v4.dataset_fold_label_selection%ROWTYPE; o v4.observations%ROWTYPE;
BEGIN
 -- Serialize this dataset/fold assembly so concurrent rows cannot evade phase separation.
 PERFORM pg_advisory_xact_lock(hashtextextended(NEW.dataset_id||':'||NEW.fold_id,0));
 SELECT * INTO STRICT selected FROM v4.dataset_fold_label_selection
 WHERE dataset_id=NEW.dataset_id AND fold_id=NEW.fold_id AND partition_name=NEW.partition_name
  AND observation_id=NEW.observation_id AND target_id=NEW.target_id;
 IF selected.eligibility<>'ELIGIBLE' THEN RAISE EXCEPTION 'FEP_DATASET_ROW_NOT_ELIGIBLE'; END IF;
 SELECT * INTO STRICT o FROM v4.observations WHERE observation_id=NEW.observation_id;
 IF EXISTS (SELECT 1 FROM v4.dataset_rows r JOIN v4.observations x ON x.observation_id=r.observation_id
  WHERE r.dataset_id=NEW.dataset_id AND r.fold_id=NEW.fold_id AND r.partition_name<>NEW.partition_name
  AND (x.trade_date=o.trade_date OR x.observation_id=o.observation_id
   OR (o.episode_key IS NOT NULL AND x.scope_id=o.scope_id AND x.entity_id=o.entity_id AND x.episode_key=o.episode_key))) THEN
  RAISE EXCEPTION 'FEP_FOLD_PHASE_OVERLAP';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER dataset_row_guard BEFORE INSERT ON v4.dataset_rows
 FOR EACH ROW EXECUTE FUNCTION v4.validate_dataset_row();

CREATE FUNCTION v4.validate_acceptance_grant() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE k v4.permission_keys%ROWTYPE; r v4.prediction_runs%ROWTYPE;
BEGIN
 SELECT * INTO STRICT k FROM v4.permission_keys WHERE grant_id=NEW.grant_id;
 SELECT * INTO STRICT r FROM v4.prediction_runs WHERE run_id=NEW.run_id;
 IF r.model_set_id<>k.model_set_id THEN RAISE EXCEPTION 'FEP_ACCEPTANCE_MODELSET_MISMATCH'; END IF;
 -- Acceptance validator must additionally check exact activation ALLOW at inference,
 -- current revocations for live display, and matching CHAMPION result scope/target/horizon/schema.
 RETURN NEW;
END $$;
CREATE TRIGGER acceptance_grant_guard BEFORE INSERT ON v4.acceptance_receipts
 FOR EACH ROW EXECUTE FUNCTION v4.validate_acceptance_grant();
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

-- E1 validators implement the frozen reference's required validation surfaces.
CREATE FUNCTION v4.validate_observation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s v4.scopes%ROWTYPE;
BEGIN
 SELECT * INTO STRICT s FROM v4.scopes WHERE scope_id=NEW.scope_id;
 PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(NEW.scope_id,NEW.entity_id,NEW.signal_key)::text,0));
 IF s.observation_kind='ENTRY' AND EXISTS(SELECT 1 FROM v4.observations
  WHERE scope_id=NEW.scope_id AND entity_id=NEW.entity_id AND signal_key=NEW.signal_key) THEN
  RAISE EXCEPTION 'FEP_DUPLICATE_LOGICAL_EVENT';
 END IF;
 IF s.observation_kind='DAILY_LANDMARK' AND EXISTS(SELECT 1 FROM v4.observations
  WHERE scope_id=NEW.scope_id AND entity_id=NEW.entity_id AND trade_date=NEW.trade_date) THEN
  RAISE EXCEPTION 'FEP_DUPLICATE_DAILY_LANDMARK';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_identity BEFORE INSERT ON v4.observations FOR EACH ROW EXECUTE FUNCTION v4.validate_observation();
CREATE FUNCTION v4.validate_observation_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o v4.observations%ROWTYPE; p v4.publications%ROWTYPE; ns text; k text;
BEGIN
 SELECT * INTO STRICT o FROM v4.observations WHERE observation_id=NEW.observation_id;
 SELECT * INTO STRICT p FROM v4.publications WHERE publication_id=NEW.publication_id;
 SELECT namespace_id INTO STRICT ns FROM v4.scopes WHERE scope_id=o.scope_id;
 IF p.status<>'ACCEPTED' OR p.trade_date<>o.trade_date OR p.model_namespace_id<>ns
  OR NEW.feature_cutoff>o.slot_deadline OR p.accepted_at>NEW.feature_cutoff THEN
  RAISE EXCEPTION 'FEP_PUBLICATION_OBSERVATION_MISMATCH';
 END IF;
 IF NEW.evidence_origin='PIT_OBSERVED' AND (NEW.execution_mode='REPLAY' OR NEW.created_at>o.slot_deadline) THEN
  RAISE EXCEPTION 'FEP_RECONSTRUCTION_NOT_PIT';
 END IF;
 FOREACH k IN ARRAY ARRAY['publication','accepted_head','algorithm_contract','parameter_contract','calendar','universe','adjustment_basis','feature_contract','membership','state_event_revision','enrichment_revision'] LOOP
  IF NOT NEW.dependency_manifest ? k THEN RAISE EXCEPTION 'FEP_MANIFEST_DEPENDENCY_MISSING:%',k; END IF;
 END LOOP;
 IF NEW.dependency_manifest->>'publication'<>NEW.publication_id THEN RAISE EXCEPTION 'FEP_MANIFEST_PUBLICATION_MISMATCH'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_revision_guard BEFORE INSERT ON v4.observation_revisions FOR EACH ROW EXECUTE FUNCTION v4.validate_observation_revision();
CREATE FUNCTION v4.validate_feature_value() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.field_registry%ROWTYPE; scope text;
BEGIN
 SELECT * INTO STRICT r FROM v4.field_registry WHERE feature_contract_id=NEW.feature_contract_id AND field_name=NEW.field_name;
 SELECT o.scope_id INTO STRICT scope FROM v4.snapshots s JOIN v4.observations o USING(observation_id) WHERE s.snapshot_id=NEW.snapshot_id;
 IF NOT EXISTS(SELECT 1 FROM v4.field_scope WHERE feature_contract_id=NEW.feature_contract_id AND field_name=NEW.field_name AND scope_id=scope)
  OR NOT r.quality_allowlist ? NEW.quality OR (r.required AND (NEW.value IS NULL OR NEW.value='null'::jsonb)) THEN
  RAISE EXCEPTION 'FEP_FEATURE_SCOPE_QUALITY_REQUIRED';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER feature_value_guard BEFORE INSERT ON v4.feature_values FOR EACH ROW EXECUTE FUNCTION v4.validate_feature_value();
-- Immutable exact authority rows are admitted by the migration/authority owner,
-- not by an application or deployer. The adapter cannot invent an authority contract.
-- No REAL authority contract is seeded in E1 while the three-time interface is absent.
CREATE FUNCTION v4.validate_label_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body jsonb; source jsonb;
BEGIN
 SELECT c.body INTO STRICT body FROM v4.contracts c WHERE c.contract_id=NEW.authority_contract_id;
 SELECT value INTO source FROM jsonb_array_elements(body->'exact_upstream_rows')
 WHERE value->>'upstream_key'=NEW.upstream_key AND value->>'upstream_revision'=NEW.upstream_revision
  AND value->>'source_digest'=NEW.source_digest;
 IF source IS NULL OR source->>'label_event_end'<>NEW.label_event_end::text
  OR (source->>'source_fact_available_at')::timestamptz IS DISTINCT FROM NEW.source_fact_available_at
  OR (source->>'label_training_mature_at')::timestamptz IS DISTINCT FROM NEW.label_training_mature_at
  OR (source->>'label_revision_available_at')::timestamptz IS DISTINCT FROM NEW.label_revision_available_at THEN
  RAISE EXCEPTION 'FEP_UPSTREAM_EXACT_AUTHORITY_REQUIRED';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER label_binding_guard BEFORE INSERT ON v4.label_source_bindings FOR EACH ROW EXECUTE FUNCTION v4.validate_label_binding();
CREATE FUNCTION v4.validate_label_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body jsonb; b v4.label_source_bindings%ROWTYPE; source jsonb;
BEGIN
 SELECT * INTO STRICT b FROM v4.label_source_bindings WHERE binding_id=NEW.binding_id;
 SELECT c.body INTO STRICT body FROM v4.contracts c WHERE c.contract_id=b.authority_contract_id;
 SELECT value INTO STRICT source FROM jsonb_array_elements(body->'exact_upstream_rows')
 WHERE value->>'upstream_key'=b.upstream_key AND value->>'upstream_revision'=b.upstream_revision AND value->>'source_digest'=b.source_digest;
 IF source->>'observation_id' IS DISTINCT FROM NEW.observation_id OR source->>'target_id' IS DISTINCT FROM NEW.target_id
  OR source->>'target_digest' IS DISTINCT FROM NEW.target_digest
  OR (source->>'numeric_value')::float8 IS DISTINCT FROM NEW.numeric_value
  OR source->>'class_value' IS DISTINCT FROM NEW.class_value
  OR source->>'quality' IS DISTINCT FROM NEW.quality
  OR (source->>'training_allowed')::boolean IS DISTINCT FROM NEW.training_allowed THEN
  RAISE EXCEPTION 'FEP_LABEL_EXACT_SOURCE_MISMATCH';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER label_revision_guard BEFORE INSERT ON v4.label_revisions FOR EACH ROW EXECUTE FUNCTION v4.validate_label_revision();
CREATE FUNCTION v4.validate_denominator_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE id text; m jsonb;
BEGIN
 id:=NEW.dataset_id;
 SELECT manifest INTO STRICT m FROM v4.datasets WHERE dataset_id=id;
 IF NOT m ? 'expected_targets' THEN RAISE EXCEPTION 'FEP_DENOMINATOR_MANIFEST_REQUIRED'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(m->'expected_targets') e
  WHERE NOT EXISTS(SELECT 1 FROM v4.dataset_eligibility_ledger l WHERE l.dataset_id=id AND l.observation_id=e->>'observation_id' AND l.target_id=e->>'target_id'))
  OR EXISTS(SELECT 1 FROM v4.dataset_eligibility_ledger l WHERE l.dataset_id=id
  AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(m->'expected_targets') e WHERE l.observation_id=e->>'observation_id' AND l.target_id=e->>'target_id')) THEN
  RAISE EXCEPTION 'FEP_DENOMINATOR_INCOMPLETE';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER denominator_complete AFTER INSERT ON v4.datasets DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION v4.validate_denominator_complete();
CREATE CONSTRAINT TRIGGER denominator_ledger_complete AFTER INSERT ON v4.dataset_eligibility_ledger DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION v4.validate_denominator_complete();

CREATE FUNCTION v4.validate_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.observation_revisions%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM v4.observation_revisions WHERE observation_id=NEW.observation_id AND revision=NEW.observation_revision;
 IF r.dependency_manifest->>'feature_contract' IS DISTINCT FROM NEW.feature_contract_id THEN
  RAISE EXCEPTION 'FEP_SNAPSHOT_FEATURE_CONTRACT_MISMATCH';
 END IF;
 IF NEW.created_at<r.feature_cutoff THEN RAISE EXCEPTION 'FEP_SNAPSHOT_TIME_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER snapshot_guard BEFORE INSERT ON v4.snapshots FOR EACH ROW EXECUTE FUNCTION v4.validate_snapshot();

-- Source: immutable historical 032_fep_reconstruction_authority_shadow_v1.sql; schema-qualified objects redirected to fixed v4.
-- Allocated by runtime scan after R1R1B semantic freeze. Historical files unchanged.
CREATE TABLE v4.reconstruction_authorities (
 authority_id text PRIMARY KEY, authority_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 scope_id text NOT NULL REFERENCES v4.scopes(scope_id), namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
 trade_date date NOT NULL, evidence_origin text NOT NULL CHECK(evidence_origin IN ('RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED')),
 execution_mode text NOT NULL CHECK(execution_mode='REPLAY'), source_manifest jsonb NOT NULL,
 source_manifest_digest v4.sha256 NOT NULL, feature_contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 accepted_head_identity jsonb NOT NULL, reconstructed_at timestamptz NOT NULL,
 historical_availability_claim text NOT NULL CHECK(historical_availability_claim='NOT_HISTORICALLY_OBSERVED'),
 as_recorded boolean NOT NULL CHECK(NOT as_recorded), first_observed boolean NOT NULL CHECK(NOT first_observed),
 real_oos boolean NOT NULL CHECK(NOT real_oos)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON v4.reconstruction_authorities FOR EACH ROW EXECUTE FUNCTION v4.reject_mutation();
CREATE FUNCTION v4.validate_reconstruction_authority() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b jsonb; e jsonb; ns text; registered timestamptz;
BEGIN
 SELECT body,created_at INTO STRICT b,registered FROM v4.contracts WHERE contract_id=NEW.authority_contract_id;
 SELECT value INTO e FROM jsonb_array_elements(b->'exact_authorities') WHERE value->>'authority_id'=NEW.authority_id;
 SELECT namespace_id INTO STRICT ns FROM v4.scopes WHERE scope_id=NEW.scope_id;
 IF e IS NULL OR NEW.namespace_id<>ns OR e->>'namespace_id'<>NEW.namespace_id OR e->>'scope_id'<>NEW.scope_id
  OR e->>'trade_date'<>NEW.trade_date::text OR e->>'evidence_origin'<>NEW.evidence_origin
  OR e->>'feature_contract_id'<>NEW.feature_contract_id OR e->'source_manifest' IS DISTINCT FROM NEW.source_manifest
  OR e->>'source_manifest_digest'<>NEW.source_manifest_digest OR e->'accepted_head_identity' IS DISTINCT FROM NEW.accepted_head_identity
  OR NEW.reconstructed_at<registered OR NEW.reconstructed_at>clock_timestamp()
  OR NEW.source_manifest->>'feature_contract' IS DISTINCT FROM NEW.feature_contract_id
  OR NEW.source_manifest->>'max_feature_source_trade_date' IS NULL
  OR (NEW.source_manifest->>'max_feature_source_trade_date')::date>NEW.trade_date THEN
  RAISE EXCEPTION 'FEP_RECONSTRUCTION_EXACT_FROZEN_AUTHORITY_REQUIRED';
 END IF;
 -- Dependency placeholders are forbidden. UNKNOWN feature quality is an
 -- explicit accepted fact and must not be mistaken for an authority token.
 IF NEW.source_manifest ? 'publication' OR EXISTS(
  SELECT 1 FROM jsonb_each(NEW.source_manifest) d WHERE d.key IN
   ('source_dataset_contract','historical_population','frozen_source_bindings','algorithm_contract','parameter_contract','calendar','universe','adjustment_basis','membership','state_event_revision','enrichment_revision','accepted_head','feature_contract')
   AND d.value::text ~ '"(CURRENT|LATEST|TODAY|UNKNOWN)"')
  OR NOT (NEW.source_manifest ?& ARRAY['source_dataset_contract','historical_population','frozen_source_bindings','algorithm_contract','parameter_contract','calendar','universe','adjustment_basis','membership','state_event_revision','enrichment_revision','accepted_head','feature_contract']) THEN
  RAISE EXCEPTION 'FEP_RECONSTRUCTION_MANIFEST_REQUIRED';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_authority_guard BEFORE INSERT ON v4.reconstruction_authorities FOR EACH ROW EXECUTE FUNCTION v4.validate_reconstruction_authority();

ALTER TABLE v4.observation_revisions ALTER COLUMN publication_id DROP NOT NULL;
ALTER TABLE v4.observation_revisions ADD COLUMN authority_kind text NOT NULL DEFAULT 'CANONICAL_PUBLICATION';
ALTER TABLE v4.observation_revisions ADD COLUMN reconstruction_authority_id text REFERENCES v4.reconstruction_authorities(authority_id);
-- Legacy reconstructed-publication rows cannot be silently relabelled. Installation
-- on such a population fails explicitly; accepted PIT rows remain byte-logically unchanged.
ALTER TABLE v4.observation_revisions ADD CONSTRAINT observation_authority_union CHECK(
 (authority_kind='CANONICAL_PUBLICATION' AND publication_id IS NOT NULL AND reconstruction_authority_id IS NULL AND evidence_origin='PIT_OBSERVED') OR
 (authority_kind='HISTORICAL_RECONSTRUCTION' AND publication_id IS NULL AND reconstruction_authority_id IS NOT NULL
  AND evidence_origin IN ('RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED') AND execution_mode='REPLAY'));
-- Keep the original publication validator function exactly, filtering only its
-- authority branch. Reconstruction has its own strictly checked trigger.
DROP TRIGGER observation_revision_guard ON v4.observation_revisions;
CREATE TRIGGER observation_revision_guard BEFORE INSERT ON v4.observation_revisions FOR EACH ROW
 WHEN (NEW.authority_kind='CANONICAL_PUBLICATION') EXECUTE FUNCTION v4.validate_observation_revision();
CREATE FUNCTION v4.validate_observation_authority_union() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a v4.reconstruction_authorities%ROWTYPE; o v4.observations%ROWTYPE;
BEGIN
 IF NEW.authority_kind='CANONICAL_PUBLICATION' THEN
  IF NEW.dependency_manifest ? 'reconstruction_authority' THEN RAISE EXCEPTION 'FEP_MIXED_AUTHORITY_KEYS'; END IF;
 ELSE
  SELECT * INTO STRICT a FROM v4.reconstruction_authorities WHERE authority_id=NEW.reconstruction_authority_id;
  SELECT * INTO STRICT o FROM v4.observations WHERE observation_id=NEW.observation_id;
  IF a.scope_id<>o.scope_id OR a.trade_date<>o.trade_date OR a.evidence_origin<>NEW.evidence_origin
   OR a.source_manifest->>'source_observation_id'<>NEW.observation_id
   OR a.source_manifest->>'entity_id'<>o.entity_id OR NEW.feature_cutoff>o.slot_deadline
   OR NEW.created_at<a.reconstructed_at OR NEW.dependency_manifest ? 'publication'
   OR NEW.dependency_manifest IS DISTINCT FROM a.source_manifest || jsonb_build_object('reconstruction_authority',a.authority_id)
   OR NEW.dependency_manifest->>'feature_contract'<>a.feature_contract_id THEN
   RAISE EXCEPTION 'FEP_RECONSTRUCTION_OBSERVATION_MISMATCH';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_authority_union_guard BEFORE INSERT ON v4.observation_revisions FOR EACH ROW EXECUTE FUNCTION v4.validate_observation_authority_union();

ALTER TABLE v4.prediction_runs ALTER COLUMN publication_id DROP NOT NULL;
ALTER TABLE v4.prediction_runs ADD COLUMN authority_kind text NOT NULL DEFAULT 'CANONICAL_PUBLICATION';
ALTER TABLE v4.prediction_runs ADD COLUMN reconstruction_authority_id text REFERENCES v4.reconstruction_authorities(authority_id);
ALTER TABLE v4.prediction_runs ADD CONSTRAINT prediction_run_authority_union CHECK(
 (authority_kind='CANONICAL_PUBLICATION' AND publication_id IS NOT NULL AND reconstruction_authority_id IS NULL) OR
 (authority_kind='HISTORICAL_RECONSTRUCTION' AND publication_id IS NULL AND reconstruction_authority_id IS NOT NULL));

-- Accepted artifact import is provenance, not a fabricated model fitting run.
ALTER TABLE v4.models ALTER COLUMN training_run_id DROP NOT NULL;
ALTER TABLE v4.models ADD COLUMN artifact_origin text NOT NULL DEFAULT 'TRAINED';
ALTER TABLE v4.models ADD COLUMN import_contract_id text REFERENCES v4.contracts(contract_id);
ALTER TABLE v4.models ADD COLUMN import_manifest jsonb;
ALTER TABLE v4.models ADD CONSTRAINT model_artifact_origin_union CHECK(
 (artifact_origin='TRAINED' AND training_run_id IS NOT NULL AND import_contract_id IS NULL AND import_manifest IS NULL) OR
 (artifact_origin='ACCEPTED_ARTIFACT_IMPORT' AND training_run_id IS NULL AND import_contract_id IS NOT NULL AND import_manifest IS NOT NULL));
CREATE FUNCTION v4.validate_model_import() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b jsonb;
BEGIN
 IF NEW.artifact_origin='ACCEPTED_ARTIFACT_IMPORT' THEN
  SELECT body INTO STRICT b FROM v4.contracts WHERE contract_id=NEW.import_contract_id;
  IF b->'exact_import_manifest' IS DISTINCT FROM NEW.import_manifest OR b->>'model_id'<>NEW.model_id
   OR b->>'model_digest'<>NEW.model_digest OR b->>'model_family'<>NEW.family
   OR b->>'feature_contract_id'<>NEW.feature_contract_id OR b->>'scope_id'<>NEW.scope_id
   OR b->>'target_id'<>NEW.target_id OR (b->>'horizon')::integer<>NEW.horizon THEN
   RAISE EXCEPTION 'FEP_ACCEPTED_MODEL_IMPORT_BINDING_REQUIRED';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER model_import_guard BEFORE INSERT ON v4.models FOR EACH ROW EXECUTE FUNCTION v4.validate_model_import();
CREATE FUNCTION v4.validate_import_member_role() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m v4.models%ROWTYPE;
BEGIN
 SELECT * INTO STRICT m FROM v4.models WHERE model_id=NEW.model_id;
 IF m.artifact_origin='ACCEPTED_ARTIFACT_IMPORT' AND
  (NEW.role='CHAMPION' OR NEW.role IS DISTINCT FROM (m.import_manifest->>'canonical_role')) THEN
  RAISE EXCEPTION 'FEP_IMPORTED_DIAGNOSTIC_CHAMPION_FORBIDDEN'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER import_member_guard BEFORE INSERT ON v4.model_set_members FOR EACH ROW EXECUTE FUNCTION v4.validate_import_member_role();
CREATE FUNCTION v4.validate_reconstruction_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.observation_revisions%ROWTYPE; a v4.reconstruction_authorities%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM v4.observation_revisions WHERE observation_id=NEW.observation_id AND revision=NEW.observation_revision;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM v4.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
  IF a.source_manifest->>'snapshot_id'<>NEW.snapshot_id OR a.source_manifest->>'feature_digest'<>NEW.feature_digest
   OR a.source_manifest->>'quality_digest'<>NEW.quality_digest THEN RAISE EXCEPTION 'FEP_RECONSTRUCTION_SNAPSHOT_EXACT_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_snapshot_guard BEFORE INSERT ON v4.snapshots FOR EACH ROW EXECUTE FUNCTION v4.validate_reconstruction_snapshot();
CREATE FUNCTION v4.validate_reconstruction_feature() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.observation_revisions%ROWTYPE; a v4.reconstruction_authorities%ROWTYPE; e jsonb;
BEGIN
 SELECT r0.* INTO STRICT r FROM v4.snapshots s JOIN v4.observation_revisions r0
  ON r0.observation_id=s.observation_id AND r0.revision=s.observation_revision WHERE s.snapshot_id=NEW.snapshot_id;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM v4.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
  e:=a.source_manifest->'feature_entries'->NEW.field_name;
  IF e IS NULL OR e->'value' IS DISTINCT FROM coalesce(NEW.value,'null'::jsonb)
   OR e->>'quality'<>NEW.quality OR e->>'source_digest'<>NEW.source_digest THEN
   RAISE EXCEPTION 'FEP_RECONSTRUCTION_FEATURE_EXACT_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_feature_guard BEFORE INSERT ON v4.feature_values FOR EACH ROW EXECUTE FUNCTION v4.validate_reconstruction_feature();
CREATE FUNCTION v4.reject_reconstruction_publication() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM v4.reconstruction_authorities WHERE authority_id=NEW.publication_id OR namespace_id=NEW.model_namespace_id)
  OR EXISTS(SELECT 1 FROM v4.contracts WHERE family='FEP_RECONSTRUCTION_AUTHORITY_V1' AND body->>'namespace_id'=NEW.model_namespace_id) THEN
  RAISE EXCEPTION 'FEP_RECONSTRUCTION_IS_NOT_PUBLICATION'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fep_reconstruction_not_publication BEFORE INSERT ON v4.publications FOR EACH ROW EXECUTE FUNCTION v4.reject_reconstruction_publication();

DO $$ DECLARE n text; BEGIN
 SELECT conname INTO STRICT n FROM pg_constraint WHERE conrelid='v4.permission_keys'::regclass AND contype='c'
  AND pg_get_constraintdef(oid) LIKE '%model_role%CHAMPION%';
 EXECUTE format('ALTER TABLE v4.permission_keys DROP CONSTRAINT %I',n);
END $$;
ALTER TABLE v4.permission_keys ADD CONSTRAINT permission_role_capability CHECK(
 (capability='SHADOW_INFERENCE' AND model_role IN ('BASELINE','CHALLENGER','CHAMPION')) OR
 (capability IN ('DESCRIPTIVE_DISPLAY','MODEL_DISPLAY','PRIORITY_USE') AND model_role='CHAMPION'));
-- Exact member FK, CAS implementation and all append-only guards remain in place.
CREATE FUNCTION v4.validate_canonical_prediction_authority() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.prediction_runs%ROWTYPE; s v4.snapshots%ROWTYPE; o v4.observation_revisions%ROWTYPE;
 sl v4.prediction_slots%ROWTYPE; m v4.models%ROWTYPE; a v4.reconstruction_authorities%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM v4.prediction_runs WHERE run_id=NEW.run_id;
 SELECT * INTO STRICT s FROM v4.snapshots WHERE snapshot_id=NEW.snapshot_id;
 SELECT * INTO STRICT o FROM v4.observation_revisions WHERE observation_id=s.observation_id AND revision=s.observation_revision;
 SELECT * INTO STRICT sl FROM v4.prediction_slots WHERE slot_id=NEW.slot_id;
 SELECT * INTO STRICT m FROM v4.models WHERE model_id=NEW.model_id;
 IF r.authority_kind<>o.authority_kind OR r.publication_id IS DISTINCT FROM o.publication_id
  OR r.reconstruction_authority_id IS DISTINCT FROM o.reconstruction_authority_id
  OR r.started_at<sl.selection_cutoff OR r.finished_at>NEW.accepted_at OR NEW.accepted_at>sl.deadline
  OR m.accepted_at>sl.selection_cutoff OR m.family<>sl.model_family_scope THEN RAISE EXCEPTION 'FEP_PREDICTION_EXACT_AUTHORITY_CLOCK_REQUIRED'; END IF;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM v4.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
  IF NEW.prediction_evidence NOT IN ('HISTORICAL_SIMULATION','LATE_RECONSTRUCTION','CORRECTED_RECONSTRUCTION')
   OR a.feature_contract_id<>NEW.feature_contract_id OR a.scope_id<>NEW.scope_id
   OR coalesce((NEW.outputs->>'REAL_OOS')::boolean,false) OR coalesce((NEW.outputs->>'FIRST_OBSERVED')::boolean,false)
   OR coalesce((NEW.outputs->>'AS_RECORDED')::boolean,false) OR coalesce((NEW.outputs->>'PROMOTION_EVIDENCE')::boolean,false)
   OR coalesce((NEW.outputs->>'production')::boolean,false) OR coalesce((NEW.outputs->>'model_display')::boolean,false)
   OR coalesce((NEW.outputs->>'priority_use')::boolean,false) THEN RAISE EXCEPTION 'FEP_RECONSTRUCTION_EVIDENCE_UPGRADE_FORBIDDEN'; END IF;
 ELSE
  IF NEW.prediction_evidence='HISTORICAL_SIMULATION' THEN RAISE EXCEPTION 'FEP_HISTORICAL_SIMULATION_RECONSTRUCTION_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER prediction_authority_guard BEFORE INSERT ON v4.predictions FOR EACH ROW EXECUTE FUNCTION v4.validate_canonical_prediction_authority();
CREATE FUNCTION v4.validate_reconstruction_acceptance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r v4.prediction_runs%ROWTYPE; k v4.permission_keys%ROWTYPE; a v4.activations%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM v4.prediction_runs WHERE run_id=NEW.run_id;
 SELECT * INTO STRICT k FROM v4.permission_keys WHERE grant_id=NEW.grant_id;
 -- Same lock/key as the original CAS, so revocation cannot race admission.
 PERFORM pg_advisory_xact_lock(hashtextextended('v4.head:'||jsonb_build_array(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id)::text,0));
 SELECT * INTO STRICT a FROM v4.activations WHERE activation_id=NEW.activation_id;
 IF a.action<>'ALLOW' OR a.effective_at>r.started_at OR a.grant_id<>NEW.grant_id
  OR NOT EXISTS(SELECT 1 FROM v4.deployment_heads h WHERE h.scope_id=k.scope_id AND h.capability=k.capability
   AND h.target_id=k.target_id AND h.horizon=k.horizon AND h.feature_contract_id=k.feature_contract_id
   AND h.grant_id=k.grant_id AND h.model_set_id=k.model_set_id AND h.activation_id=NEW.activation_id)
  OR (r.authority_kind='HISTORICAL_RECONSTRUCTION' AND k.capability<>'SHADOW_INFERENCE')
  OR NOT EXISTS(SELECT 1 FROM v4.predictions p JOIN v4.prediction_slots sl ON sl.slot_id=p.slot_id WHERE p.run_id=NEW.run_id AND p.scope_id=k.scope_id
   AND p.target_id=k.target_id AND p.horizon=k.horizon AND p.feature_contract_id=k.feature_contract_id
   AND p.model_set_id=k.model_set_id AND a.effective_at<=sl.selection_cutoff) THEN RAISE EXCEPTION 'FEP_EXACT_SHADOW_ACCEPTANCE_REQUIRED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_acceptance_guard BEFORE INSERT ON v4.acceptance_receipts FOR EACH ROW EXECUTE FUNCTION v4.validate_reconstruction_acceptance();
CREATE FUNCTION v4.validate_reconstruction_run() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a v4.reconstruction_authorities%ROWTYPE;
BEGIN
 IF NEW.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM v4.reconstruction_authorities WHERE authority_id=NEW.reconstruction_authority_id;
  IF NEW.started_at<a.reconstructed_at
   OR NEW.input_digest IS DISTINCT FROM (a.source_manifest->>'prediction_input_digest')
   OR (SELECT count(*) FROM v4.feature_values WHERE snapshot_id=a.source_manifest->>'snapshot_id')
     <>(SELECT count(*) FROM jsonb_object_keys(a.source_manifest->'feature_entries'))
   OR NOT EXISTS(SELECT 1 FROM v4.model_set_members m
   WHERE m.model_set_id=NEW.model_set_id AND m.scope_id=a.scope_id AND m.feature_contract_id=a.feature_contract_id) THEN
   RAISE EXCEPTION 'FEP_RECONSTRUCTION_RUN_BINDING_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_run_guard BEFORE INSERT ON v4.prediction_runs FOR EACH ROW EXECUTE FUNCTION v4.validate_reconstruction_run();

-- Source: immutable historical 033_fep_signal_contract_integrity_v1.sql; schema-qualified objects redirected to fixed v4.
-- Allocated by V4_MIGRATION_ALLOCATION_REGISTRY_R4. 028--032 remain immutable.
ALTER TABLE v4.observations ADD CONSTRAINT observation_signal_contract_fk
 FOREIGN KEY(core_signal_contract_id) REFERENCES v4.contracts(contract_id);
CREATE TABLE v4.signal_contract_registry (
 contract_id text NOT NULL REFERENCES v4.contracts(contract_id),
 scope_id text NOT NULL REFERENCES v4.scopes(scope_id), signal_family text NOT NULL,
 contract_family text NOT NULL, contract_digest v4.sha256 NOT NULL, predicate_digest v4.sha256 NOT NULL,
 PRIMARY KEY(contract_id,scope_id,signal_family)
);
CREATE FUNCTION v4.signal_registry_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c v4.contracts;
BEGIN
 SELECT * INTO STRICT c FROM v4.contracts WHERE contract_id=NEW.contract_id;
 IF c.family IS DISTINCT FROM NEW.contract_family OR c.digest IS DISTINCT FROM NEW.contract_digest
 OR c.body->'accepted_contract'->>'observation_scope' IS DISTINCT FROM NEW.scope_id
 OR c.body->'accepted_contract'->>'contract_id' IS DISTINCT FROM NEW.contract_id
 OR NOT COALESCE((c.body->'accepted_contract'->'formal_signals') ? NEW.signal_family,false)
 OR c.body->>'predicate_digest' IS DISTINCT FROM NEW.predicate_digest
 THEN RAISE EXCEPTION 'FEP_SIGNAL_REGISTRY_SEMANTIC_MISMATCH'; END IF;
 IF NEW.signal_family='FIRST_PREWATCH' AND
 (NEW.contract_id<>'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR NEW.contract_family<>'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR NEW.scope_id<>'FEP_STOCK_ENTRY_CORE'
 OR NEW.contract_digest<>'6df0c6ad8f0109b6a02b56b4f905341cd12b53b3607c18791b3aada285b6d569'
 OR NEW.predicate_digest<>'efe81c599fc24dae00bd7f3e073e389eee2efda242294186010bceb643601b4b'
 OR c.body->'source_binding'->>'sha256' IS DISTINCT FROM '9884d9df4530ceea9ee3268c30e5dfb65ef149939710eb87e66d73466408025a'
 OR c.body->'accepted_contract'->>'contract_id' IS DISTINCT FROM 'FEP_E2_ENTRY_EVENT_STRATA_V1_1'
 OR c.body->'accepted_contract'->>'first_prewatch' IS DISTINCT FROM 'Accepted Radar ENROLLED + maturity PREWATCH + no parent episode; initial SEED upgrade is not an ENROLLED event')
 THEN RAISE EXCEPTION 'FEP_FIRST_PREWATCH_EXACT_AUTHORITY_REQUIRED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER signal_registry_guard BEFORE INSERT ON v4.signal_contract_registry
 FOR EACH ROW EXECUTE FUNCTION v4.signal_registry_guard();
INSERT INTO v4.signal_contract_registry
 SELECT contract_id,'FEP_STOCK_ENTRY_CORE',s,family,digest,body->>'predicate_digest'
 FROM v4.contracts CROSS JOIN LATERAL jsonb_array_elements_text(body->'accepted_contract'->'formal_signals') s
 WHERE contract_id='FEP_E2_ENTRY_EVENT_STRATA_V1_1';
CREATE FUNCTION v4.observation_signal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM v4.signal_contract_registry r JOIN v4.contracts c USING(contract_id)
 WHERE r.contract_id=NEW.core_signal_contract_id AND r.scope_id=NEW.scope_id
 AND r.signal_family=split_part(NEW.signal_key,':',1) AND c.family=r.contract_family AND c.digest=r.contract_digest)
 THEN RAISE EXCEPTION 'FEP_OBSERVATION_SIGNAL_AUTHORITY_MISMATCH'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_signal_guard BEFORE INSERT OR UPDATE ON v4.observations
 FOR EACH ROW EXECUTE FUNCTION v4.observation_signal_guard();
CREATE FUNCTION v4.signal_registry_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'IMMUTABLE_SIGNAL_REGISTRY'; END $$;
CREATE TRIGGER signal_registry_no_update BEFORE UPDATE OR DELETE ON v4.signal_contract_registry
 FOR EACH ROW EXECUTE FUNCTION v4.signal_registry_immutable();


-- Keep v4 schema ownership/ACL intact; grants below are object-scoped to FEP relations.
GRANT USAGE ON SCHEMA v4 TO fep_application,fep_deployer,fep_adapter,fep_auditor,fep_cas_owner,fep_schema_owner;
ALTER DOMAIN v4.sha256 OWNER TO fep_schema_owner;
DO $$ DECLARE n text; sig regprocedure; BEGIN
 FOREACH n IN ARRAY ARRAY['acceptance_receipts',
'activations',
'contracts',
'dataset_eligibility_ledger',
'dataset_fold_cutoffs',
'dataset_fold_label_selection',
'dataset_rows',
'datasets',
'deployment_change_receipts',
'deployment_heads',
'feature_values',
'field_registry',
'field_scope',
'label_revisions',
'label_source_bindings',
'model_set_members',
'model_sets',
'models',
'observation_revisions',
'observations',
'permission_keys',
'prediction_runs',
'prediction_slots',
'predictions',
'priority_projection',
'priority_projection_grants',
'reconstruction_authorities',
'reports',
'scopes',
'signal_contract_registry',
'slot_model_bindings',
'slot_receipts',
'snapshots',
'targets',
'training_runs'] LOOP
  EXECUTE format('REVOKE ALL ON TABLE v4.%I FROM PUBLIC',n);
  EXECUTE format('ALTER TABLE v4.%I OWNER TO fep_schema_owner',n);
 END LOOP;
 FOR sig IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='v4' AND p.proname=ANY(ARRAY['cas_deploy',
'observation_signal_guard',
'reject_mutation',
'reject_reconstruction_publication',
'signal_registry_guard',
'signal_registry_immutable',
'validate_acceptance_grant',
'validate_canonical_prediction_authority',
'validate_dataset_row',
'validate_denominator_complete',
'validate_deployment_head',
'validate_feature_value',
'validate_fold_cutoff',
'validate_fold_label_selection',
'validate_import_member_role',
'validate_label_binding',
'validate_label_revision',
'validate_model_import',
'validate_observation',
'validate_observation_authority_union',
'validate_observation_revision',
'validate_reconstruction_acceptance',
'validate_reconstruction_authority',
'validate_reconstruction_feature',
'validate_reconstruction_run',
'validate_reconstruction_snapshot',
'validate_snapshot']) LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',sig);
  EXECUTE format('ALTER FUNCTION %s SET search_path=pg_catalog,v4',sig);
  IF split_part(sig::text,'(',1)='v4.cas_deploy' THEN
   EXECUTE format('ALTER FUNCTION %s OWNER TO fep_cas_owner',sig);
  ELSE
   EXECUTE format('ALTER FUNCTION %s OWNER TO fep_schema_owner',sig);
  END IF;
 END LOOP;
END $$;
GRANT SELECT ON v4.acceptance_receipts,
v4.activations,
v4.contracts,
v4.dataset_eligibility_ledger,
v4.dataset_fold_cutoffs,
v4.dataset_fold_label_selection,
v4.dataset_rows,
v4.datasets,
v4.deployment_change_receipts,
v4.deployment_heads,
v4.feature_values,
v4.field_registry,
v4.field_scope,
v4.label_revisions,
v4.label_source_bindings,
v4.model_set_members,
v4.model_sets,
v4.models,
v4.observation_revisions,
v4.observations,
v4.permission_keys,
v4.prediction_runs,
v4.prediction_slots,
v4.predictions,
v4.priority_projection,
v4.priority_projection_grants,
v4.reconstruction_authorities,
v4.reports,
v4.scopes,
v4.signal_contract_registry,
v4.slot_model_bindings,
v4.slot_receipts,
v4.snapshots,
v4.targets,
v4.training_runs TO fep_application,fep_auditor,fep_adapter;
GRANT SELECT ON v4.publications,v4.model_namespaces TO fep_application,fep_adapter;
GRANT INSERT ON v4.observations,v4.observation_revisions,v4.snapshots,v4.feature_values,
 v4.datasets,v4.dataset_eligibility_ledger,v4.dataset_fold_cutoffs,
 v4.dataset_fold_label_selection,v4.dataset_rows,v4.prediction_slots,v4.slot_receipts
 TO fep_application;
GRANT INSERT ON v4.label_source_bindings,v4.label_revisions TO fep_adapter;
GRANT SELECT ON v4.permission_keys,v4.activations,v4.deployment_heads,v4.deployment_change_receipts TO fep_cas_owner;
GRANT INSERT ON v4.activations,v4.deployment_heads,v4.deployment_change_receipts TO fep_cas_owner;
GRANT UPDATE ON v4.deployment_heads TO fep_cas_owner;
GRANT EXECUTE ON FUNCTION v4.cas_deploy(text,text,text,bigint,text,text,v4.sha256,jsonb) TO fep_deployer;

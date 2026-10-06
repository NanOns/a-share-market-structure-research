-- Allocated by runtime scan after R1R1B semantic freeze. Historical files unchanged.
CREATE TABLE fep.reconstruction_authorities (
 authority_id text PRIMARY KEY, authority_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 scope_id text NOT NULL REFERENCES fep.scopes(scope_id), namespace_id text NOT NULL REFERENCES v4.model_namespaces(namespace_id),
 trade_date date NOT NULL, evidence_origin text NOT NULL CHECK(evidence_origin IN ('RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED')),
 execution_mode text NOT NULL CHECK(execution_mode='REPLAY'), source_manifest jsonb NOT NULL,
 source_manifest_digest fep.sha256 NOT NULL, feature_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 accepted_head_identity jsonb NOT NULL, reconstructed_at timestamptz NOT NULL,
 historical_availability_claim text NOT NULL CHECK(historical_availability_claim='NOT_HISTORICALLY_OBSERVED'),
 as_recorded boolean NOT NULL CHECK(NOT as_recorded), first_observed boolean NOT NULL CHECK(NOT first_observed),
 real_oos boolean NOT NULL CHECK(NOT real_oos)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.reconstruction_authorities FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();
CREATE FUNCTION fep.validate_reconstruction_authority() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b jsonb; e jsonb; ns text; registered timestamptz;
BEGIN
 SELECT body,created_at INTO STRICT b,registered FROM fep.contracts WHERE contract_id=NEW.authority_contract_id;
 SELECT value INTO e FROM jsonb_array_elements(b->'exact_authorities') WHERE value->>'authority_id'=NEW.authority_id;
 SELECT namespace_id INTO STRICT ns FROM fep.scopes WHERE scope_id=NEW.scope_id;
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
CREATE TRIGGER reconstruction_authority_guard BEFORE INSERT ON fep.reconstruction_authorities FOR EACH ROW EXECUTE FUNCTION fep.validate_reconstruction_authority();

ALTER TABLE fep.observation_revisions ALTER COLUMN publication_id DROP NOT NULL;
ALTER TABLE fep.observation_revisions ADD COLUMN authority_kind text NOT NULL DEFAULT 'CANONICAL_PUBLICATION';
ALTER TABLE fep.observation_revisions ADD COLUMN reconstruction_authority_id text REFERENCES fep.reconstruction_authorities(authority_id);
-- Legacy reconstructed-publication rows cannot be silently relabelled. Installation
-- on such a population fails explicitly; accepted PIT rows remain byte-logically unchanged.
ALTER TABLE fep.observation_revisions ADD CONSTRAINT observation_authority_union CHECK(
 (authority_kind='CANONICAL_PUBLICATION' AND publication_id IS NOT NULL AND reconstruction_authority_id IS NULL AND evidence_origin='PIT_OBSERVED') OR
 (authority_kind='HISTORICAL_RECONSTRUCTION' AND publication_id IS NULL AND reconstruction_authority_id IS NOT NULL
  AND evidence_origin IN ('RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED') AND execution_mode='REPLAY'));
-- Keep the original publication validator function exactly, filtering only its
-- authority branch. Reconstruction has its own strictly checked trigger.
DROP TRIGGER observation_revision_guard ON fep.observation_revisions;
CREATE TRIGGER observation_revision_guard BEFORE INSERT ON fep.observation_revisions FOR EACH ROW
 WHEN (NEW.authority_kind='CANONICAL_PUBLICATION') EXECUTE FUNCTION fep.validate_observation_revision();
CREATE FUNCTION fep.validate_observation_authority_union() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a fep.reconstruction_authorities%ROWTYPE; o fep.observations%ROWTYPE;
BEGIN
 IF NEW.authority_kind='CANONICAL_PUBLICATION' THEN
  IF NEW.dependency_manifest ? 'reconstruction_authority' THEN RAISE EXCEPTION 'FEP_MIXED_AUTHORITY_KEYS'; END IF;
 ELSE
  SELECT * INTO STRICT a FROM fep.reconstruction_authorities WHERE authority_id=NEW.reconstruction_authority_id;
  SELECT * INTO STRICT o FROM fep.observations WHERE observation_id=NEW.observation_id;
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
CREATE TRIGGER observation_authority_union_guard BEFORE INSERT ON fep.observation_revisions FOR EACH ROW EXECUTE FUNCTION fep.validate_observation_authority_union();

ALTER TABLE fep.prediction_runs ALTER COLUMN publication_id DROP NOT NULL;
ALTER TABLE fep.prediction_runs ADD COLUMN authority_kind text NOT NULL DEFAULT 'CANONICAL_PUBLICATION';
ALTER TABLE fep.prediction_runs ADD COLUMN reconstruction_authority_id text REFERENCES fep.reconstruction_authorities(authority_id);
ALTER TABLE fep.prediction_runs ADD CONSTRAINT prediction_run_authority_union CHECK(
 (authority_kind='CANONICAL_PUBLICATION' AND publication_id IS NOT NULL AND reconstruction_authority_id IS NULL) OR
 (authority_kind='HISTORICAL_RECONSTRUCTION' AND publication_id IS NULL AND reconstruction_authority_id IS NOT NULL));

-- Accepted artifact import is provenance, not a fabricated model fitting run.
ALTER TABLE fep.models ALTER COLUMN training_run_id DROP NOT NULL;
ALTER TABLE fep.models ADD COLUMN artifact_origin text NOT NULL DEFAULT 'TRAINED';
ALTER TABLE fep.models ADD COLUMN import_contract_id text REFERENCES fep.contracts(contract_id);
ALTER TABLE fep.models ADD COLUMN import_manifest jsonb;
ALTER TABLE fep.models ADD CONSTRAINT model_artifact_origin_union CHECK(
 (artifact_origin='TRAINED' AND training_run_id IS NOT NULL AND import_contract_id IS NULL AND import_manifest IS NULL) OR
 (artifact_origin='ACCEPTED_ARTIFACT_IMPORT' AND training_run_id IS NULL AND import_contract_id IS NOT NULL AND import_manifest IS NOT NULL));
CREATE FUNCTION fep.validate_model_import() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b jsonb;
BEGIN
 IF NEW.artifact_origin='ACCEPTED_ARTIFACT_IMPORT' THEN
  SELECT body INTO STRICT b FROM fep.contracts WHERE contract_id=NEW.import_contract_id;
  IF b->'exact_import_manifest' IS DISTINCT FROM NEW.import_manifest OR b->>'model_id'<>NEW.model_id
   OR b->>'model_digest'<>NEW.model_digest OR b->>'model_family'<>NEW.family
   OR b->>'feature_contract_id'<>NEW.feature_contract_id OR b->>'scope_id'<>NEW.scope_id
   OR b->>'target_id'<>NEW.target_id OR (b->>'horizon')::integer<>NEW.horizon THEN
   RAISE EXCEPTION 'FEP_ACCEPTED_MODEL_IMPORT_BINDING_REQUIRED';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER model_import_guard BEFORE INSERT ON fep.models FOR EACH ROW EXECUTE FUNCTION fep.validate_model_import();
CREATE FUNCTION fep.validate_import_member_role() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m fep.models%ROWTYPE;
BEGIN
 SELECT * INTO STRICT m FROM fep.models WHERE model_id=NEW.model_id;
 IF m.artifact_origin='ACCEPTED_ARTIFACT_IMPORT' AND
  (NEW.role='CHAMPION' OR NEW.role IS DISTINCT FROM (m.import_manifest->>'canonical_role')) THEN
  RAISE EXCEPTION 'FEP_IMPORTED_DIAGNOSTIC_CHAMPION_FORBIDDEN'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER import_member_guard BEFORE INSERT ON fep.model_set_members FOR EACH ROW EXECUTE FUNCTION fep.validate_import_member_role();
CREATE FUNCTION fep.validate_reconstruction_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.observation_revisions%ROWTYPE; a fep.reconstruction_authorities%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM fep.observation_revisions WHERE observation_id=NEW.observation_id AND revision=NEW.observation_revision;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM fep.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
  IF a.source_manifest->>'snapshot_id'<>NEW.snapshot_id OR a.source_manifest->>'feature_digest'<>NEW.feature_digest
   OR a.source_manifest->>'quality_digest'<>NEW.quality_digest THEN RAISE EXCEPTION 'FEP_RECONSTRUCTION_SNAPSHOT_EXACT_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_snapshot_guard BEFORE INSERT ON fep.snapshots FOR EACH ROW EXECUTE FUNCTION fep.validate_reconstruction_snapshot();
CREATE FUNCTION fep.validate_reconstruction_feature() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.observation_revisions%ROWTYPE; a fep.reconstruction_authorities%ROWTYPE; e jsonb;
BEGIN
 SELECT r0.* INTO STRICT r FROM fep.snapshots s JOIN fep.observation_revisions r0
  ON r0.observation_id=s.observation_id AND r0.revision=s.observation_revision WHERE s.snapshot_id=NEW.snapshot_id;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM fep.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
  e:=a.source_manifest->'feature_entries'->NEW.field_name;
  IF e IS NULL OR e->'value' IS DISTINCT FROM coalesce(NEW.value,'null'::jsonb)
   OR e->>'quality'<>NEW.quality OR e->>'source_digest'<>NEW.source_digest THEN
   RAISE EXCEPTION 'FEP_RECONSTRUCTION_FEATURE_EXACT_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_feature_guard BEFORE INSERT ON fep.feature_values FOR EACH ROW EXECUTE FUNCTION fep.validate_reconstruction_feature();
CREATE FUNCTION fep.reject_reconstruction_publication() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM fep.reconstruction_authorities WHERE authority_id=NEW.publication_id OR namespace_id=NEW.model_namespace_id)
  OR EXISTS(SELECT 1 FROM fep.contracts WHERE family='FEP_RECONSTRUCTION_AUTHORITY_V1' AND body->>'namespace_id'=NEW.model_namespace_id) THEN
  RAISE EXCEPTION 'FEP_RECONSTRUCTION_IS_NOT_PUBLICATION'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fep_reconstruction_not_publication BEFORE INSERT ON v4.publications FOR EACH ROW EXECUTE FUNCTION fep.reject_reconstruction_publication();

DO $$ DECLARE n text; BEGIN
 SELECT conname INTO STRICT n FROM pg_constraint WHERE conrelid='fep.permission_keys'::regclass AND contype='c'
  AND pg_get_constraintdef(oid) LIKE '%model_role%CHAMPION%';
 EXECUTE format('ALTER TABLE fep.permission_keys DROP CONSTRAINT %I',n);
END $$;
ALTER TABLE fep.permission_keys ADD CONSTRAINT permission_role_capability CHECK(
 (capability='SHADOW_INFERENCE' AND model_role IN ('BASELINE','CHALLENGER','CHAMPION')) OR
 (capability IN ('DESCRIPTIVE_DISPLAY','MODEL_DISPLAY','PRIORITY_USE') AND model_role='CHAMPION'));
-- Exact member FK, CAS implementation and all append-only guards remain in place.
CREATE FUNCTION fep.validate_canonical_prediction_authority() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.prediction_runs%ROWTYPE; s fep.snapshots%ROWTYPE; o fep.observation_revisions%ROWTYPE;
 sl fep.prediction_slots%ROWTYPE; m fep.models%ROWTYPE; a fep.reconstruction_authorities%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM fep.prediction_runs WHERE run_id=NEW.run_id;
 SELECT * INTO STRICT s FROM fep.snapshots WHERE snapshot_id=NEW.snapshot_id;
 SELECT * INTO STRICT o FROM fep.observation_revisions WHERE observation_id=s.observation_id AND revision=s.observation_revision;
 SELECT * INTO STRICT sl FROM fep.prediction_slots WHERE slot_id=NEW.slot_id;
 SELECT * INTO STRICT m FROM fep.models WHERE model_id=NEW.model_id;
 IF r.authority_kind<>o.authority_kind OR r.publication_id IS DISTINCT FROM o.publication_id
  OR r.reconstruction_authority_id IS DISTINCT FROM o.reconstruction_authority_id
  OR r.started_at<sl.selection_cutoff OR r.finished_at>NEW.accepted_at OR NEW.accepted_at>sl.deadline
  OR m.accepted_at>sl.selection_cutoff OR m.family<>sl.model_family_scope THEN RAISE EXCEPTION 'FEP_PREDICTION_EXACT_AUTHORITY_CLOCK_REQUIRED'; END IF;
 IF r.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM fep.reconstruction_authorities WHERE authority_id=r.reconstruction_authority_id;
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
CREATE TRIGGER prediction_authority_guard BEFORE INSERT ON fep.predictions FOR EACH ROW EXECUTE FUNCTION fep.validate_canonical_prediction_authority();
CREATE FUNCTION fep.validate_reconstruction_acceptance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.prediction_runs%ROWTYPE; k fep.permission_keys%ROWTYPE; a fep.activations%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM fep.prediction_runs WHERE run_id=NEW.run_id;
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=NEW.grant_id;
 -- Same lock/key as the original CAS, so revocation cannot race admission.
 PERFORM pg_advisory_xact_lock(hashtextextended('fep.head:'||jsonb_build_array(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id)::text,0));
 SELECT * INTO STRICT a FROM fep.activations WHERE activation_id=NEW.activation_id;
 IF a.action<>'ALLOW' OR a.effective_at>r.started_at OR a.grant_id<>NEW.grant_id
  OR NOT EXISTS(SELECT 1 FROM fep.deployment_heads h WHERE h.scope_id=k.scope_id AND h.capability=k.capability
   AND h.target_id=k.target_id AND h.horizon=k.horizon AND h.feature_contract_id=k.feature_contract_id
   AND h.grant_id=k.grant_id AND h.model_set_id=k.model_set_id AND h.activation_id=NEW.activation_id)
  OR (r.authority_kind='HISTORICAL_RECONSTRUCTION' AND k.capability<>'SHADOW_INFERENCE')
  OR NOT EXISTS(SELECT 1 FROM fep.predictions p JOIN fep.prediction_slots sl ON sl.slot_id=p.slot_id WHERE p.run_id=NEW.run_id AND p.scope_id=k.scope_id
   AND p.target_id=k.target_id AND p.horizon=k.horizon AND p.feature_contract_id=k.feature_contract_id
   AND p.model_set_id=k.model_set_id AND a.effective_at<=sl.selection_cutoff) THEN RAISE EXCEPTION 'FEP_EXACT_SHADOW_ACCEPTANCE_REQUIRED'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_acceptance_guard BEFORE INSERT ON fep.acceptance_receipts FOR EACH ROW EXECUTE FUNCTION fep.validate_reconstruction_acceptance();
CREATE FUNCTION fep.validate_reconstruction_run() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a fep.reconstruction_authorities%ROWTYPE;
BEGIN
 IF NEW.authority_kind='HISTORICAL_RECONSTRUCTION' THEN
  SELECT * INTO STRICT a FROM fep.reconstruction_authorities WHERE authority_id=NEW.reconstruction_authority_id;
  IF NEW.started_at<a.reconstructed_at
   OR NEW.input_digest IS DISTINCT FROM (a.source_manifest->>'prediction_input_digest')
   OR (SELECT count(*) FROM fep.feature_values WHERE snapshot_id=a.source_manifest->>'snapshot_id')
     <>(SELECT count(*) FROM jsonb_object_keys(a.source_manifest->'feature_entries'))
   OR NOT EXISTS(SELECT 1 FROM fep.model_set_members m
   WHERE m.model_set_id=NEW.model_set_id AND m.scope_id=a.scope_id AND m.feature_contract_id=a.feature_contract_id) THEN
   RAISE EXCEPTION 'FEP_RECONSTRUCTION_RUN_BINDING_REQUIRED'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reconstruction_run_guard BEFORE INSERT ON fep.prediction_runs FOR EACH ROW EXECUTE FUNCTION fep.validate_reconstruction_run();
ALTER TABLE fep.reconstruction_authorities OWNER TO fep_schema_owner;
GRANT SELECT ON fep.reconstruction_authorities TO fep_application,fep_auditor;
-- No new application INSERT/UPDATE/DELETE, no direct deployment head privilege.
DO $$ DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['validate_reconstruction_authority','validate_observation_authority_union','validate_model_import','validate_import_member_role','validate_reconstruction_snapshot','validate_reconstruction_feature','reject_reconstruction_publication','validate_canonical_prediction_authority','validate_reconstruction_acceptance','validate_reconstruction_run'] LOOP
  EXECUTE format('ALTER FUNCTION fep.%I() OWNER TO fep_schema_owner',n);
  EXECUTE format('ALTER FUNCTION fep.%I() SET search_path=pg_catalog,fep',n);
  EXECUTE format('REVOKE ALL ON FUNCTION fep.%I() FROM PUBLIC',n);
 END LOOP;
END $$;

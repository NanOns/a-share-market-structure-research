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
 PERFORM pg_advisory_xact_lock(hashtextextended('fep.request:'||p_request_id,0));
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;
 PERFORM pg_advisory_xact_lock(hashtextextended('fep.head:'||jsonb_build_array(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id)::text,0));
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

-- E1 validators implement the frozen reference's required validation surfaces.
CREATE FUNCTION fep.validate_observation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s fep.scopes%ROWTYPE;
BEGIN
 SELECT * INTO STRICT s FROM fep.scopes WHERE scope_id=NEW.scope_id;
 PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(NEW.scope_id,NEW.entity_id,NEW.signal_key)::text,0));
 IF s.observation_kind='ENTRY' AND EXISTS(SELECT 1 FROM fep.observations
  WHERE scope_id=NEW.scope_id AND entity_id=NEW.entity_id AND signal_key=NEW.signal_key) THEN
  RAISE EXCEPTION 'FEP_DUPLICATE_LOGICAL_EVENT';
 END IF;
 IF s.observation_kind='DAILY_LANDMARK' AND EXISTS(SELECT 1 FROM fep.observations
  WHERE scope_id=NEW.scope_id AND entity_id=NEW.entity_id AND trade_date=NEW.trade_date) THEN
  RAISE EXCEPTION 'FEP_DUPLICATE_DAILY_LANDMARK';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER observation_identity BEFORE INSERT ON fep.observations FOR EACH ROW EXECUTE FUNCTION fep.validate_observation();
CREATE FUNCTION fep.validate_observation_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o fep.observations%ROWTYPE; p v4.publications%ROWTYPE; ns text; k text;
BEGIN
 SELECT * INTO STRICT o FROM fep.observations WHERE observation_id=NEW.observation_id;
 SELECT * INTO STRICT p FROM v4.publications WHERE publication_id=NEW.publication_id;
 SELECT namespace_id INTO STRICT ns FROM fep.scopes WHERE scope_id=o.scope_id;
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
CREATE TRIGGER observation_revision_guard BEFORE INSERT ON fep.observation_revisions FOR EACH ROW EXECUTE FUNCTION fep.validate_observation_revision();
CREATE FUNCTION fep.validate_feature_value() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.field_registry%ROWTYPE; scope text;
BEGIN
 SELECT * INTO STRICT r FROM fep.field_registry WHERE feature_contract_id=NEW.feature_contract_id AND field_name=NEW.field_name;
 SELECT o.scope_id INTO STRICT scope FROM fep.snapshots s JOIN fep.observations o USING(observation_id) WHERE s.snapshot_id=NEW.snapshot_id;
 IF NOT EXISTS(SELECT 1 FROM fep.field_scope WHERE feature_contract_id=NEW.feature_contract_id AND field_name=NEW.field_name AND scope_id=scope)
  OR NOT r.quality_allowlist ? NEW.quality OR (r.required AND (NEW.value IS NULL OR NEW.value='null'::jsonb)) THEN
  RAISE EXCEPTION 'FEP_FEATURE_SCOPE_QUALITY_REQUIRED';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER feature_value_guard BEFORE INSERT ON fep.feature_values FOR EACH ROW EXECUTE FUNCTION fep.validate_feature_value();
-- Immutable exact authority rows are admitted by the migration/authority owner,
-- not by an application or deployer. The adapter cannot invent an authority contract.
-- No REAL authority contract is seeded in E1 while the three-time interface is absent.
CREATE FUNCTION fep.validate_label_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body jsonb; source jsonb;
BEGIN
 SELECT c.body INTO STRICT body FROM fep.contracts c WHERE c.contract_id=NEW.authority_contract_id;
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
CREATE TRIGGER label_binding_guard BEFORE INSERT ON fep.label_source_bindings FOR EACH ROW EXECUTE FUNCTION fep.validate_label_binding();
CREATE FUNCTION fep.validate_label_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body jsonb; b fep.label_source_bindings%ROWTYPE; source jsonb;
BEGIN
 SELECT * INTO STRICT b FROM fep.label_source_bindings WHERE binding_id=NEW.binding_id;
 SELECT c.body INTO STRICT body FROM fep.contracts c WHERE c.contract_id=b.authority_contract_id;
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
CREATE TRIGGER label_revision_guard BEFORE INSERT ON fep.label_revisions FOR EACH ROW EXECUTE FUNCTION fep.validate_label_revision();
CREATE FUNCTION fep.validate_denominator_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE id text; m jsonb;
BEGIN
 id:=NEW.dataset_id;
 SELECT manifest INTO STRICT m FROM fep.datasets WHERE dataset_id=id;
 IF NOT m ? 'expected_targets' THEN RAISE EXCEPTION 'FEP_DENOMINATOR_MANIFEST_REQUIRED'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(m->'expected_targets') e
  WHERE NOT EXISTS(SELECT 1 FROM fep.dataset_eligibility_ledger l WHERE l.dataset_id=id AND l.observation_id=e->>'observation_id' AND l.target_id=e->>'target_id'))
  OR EXISTS(SELECT 1 FROM fep.dataset_eligibility_ledger l WHERE l.dataset_id=id
  AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(m->'expected_targets') e WHERE l.observation_id=e->>'observation_id' AND l.target_id=e->>'target_id')) THEN
  RAISE EXCEPTION 'FEP_DENOMINATOR_INCOMPLETE';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER denominator_complete AFTER INSERT ON fep.datasets DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION fep.validate_denominator_complete();
CREATE CONSTRAINT TRIGGER denominator_ledger_complete AFTER INSERT ON fep.dataset_eligibility_ledger DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION fep.validate_denominator_complete();

CREATE FUNCTION fep.validate_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r fep.observation_revisions%ROWTYPE;
BEGIN
 SELECT * INTO STRICT r FROM fep.observation_revisions WHERE observation_id=NEW.observation_id AND revision=NEW.observation_revision;
 IF r.dependency_manifest->>'feature_contract' IS DISTINCT FROM NEW.feature_contract_id THEN
  RAISE EXCEPTION 'FEP_SNAPSHOT_FEATURE_CONTRACT_MISMATCH';
 END IF;
 IF NEW.created_at<r.feature_cutoff THEN RAISE EXCEPTION 'FEP_SNAPSHOT_TIME_INVALID'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER snapshot_guard BEFORE INSERT ON fep.snapshots FOR EACH ROW EXECUTE FUNCTION fep.validate_snapshot();

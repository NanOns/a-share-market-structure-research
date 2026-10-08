from pathlib import Path
import os
B=Path(__file__).parent
def atomic(p,s):
 t=p.with_name('.'+p.name+'.tmp')
 with t.open('wb') as f:f.write(s.encode('utf8'));f.flush();os.fsync(f.fileno())
 os.replace(t,p)
p=B/'FEP_R2_SCHEMA_DESIGN_20260930.sql';s=p.read_text(encoding='utf8')
s=s.replace('UNIQUE(run_id,observation_id,priority_contract_id)\n);','UNIQUE(run_id,observation_id,priority_contract_id), UNIQUE(projection_id,run_id)\n);')
s=s.replace('PRIMARY KEY(projection_id,grant_id),','PRIMARY KEY(projection_id,grant_id),\n FOREIGN KEY(projection_id,run_id) REFERENCES fep.priority_projection(projection_id,run_id),')
s=s.replace(') RETURNS bigint LANGUAGE plpgsql AS $$',') RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,fep AS $$')
s=s.replace('DECLARE k fep.permission_keys%ROWTYPE; n integer; ts timestamptz := clock_timestamp();','DECLARE k fep.permission_keys%ROWTYPE; prior fep.deployment_change_receipts%ROWTYPE; a fep.activations%ROWTYPE; n integer; ts timestamptz := clock_timestamp();')
s=s.replace('SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;','''SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;
 SELECT * INTO prior FROM fep.deployment_change_receipts WHERE request_id=p_request_id;
 IF FOUND THEN
  SELECT * INTO STRICT a FROM fep.activations WHERE activation_id=prior.activation_id;
  IF prior.grant_id<>p_grant_id OR prior.activation_id<>p_activation_id OR a.action<>p_action
   OR prior.expected_head_version<>p_expected_version OR prior.expected_prior_activation_id IS DISTINCT FROM p_expected_prior
   OR a.receipt_digest<>p_receipt_digest OR prior.checks IS DISTINCT FROM p_checks THEN
   RAISE EXCEPTION 'FEP_IDEMPOTENCY_CONFLICT';
  END IF;
  RETURN prior.new_head_version;
 END IF;''')
s=s.replace("IF p_expected_prior IS NOT NULL THEN RAISE EXCEPTION 'FEP_INITIAL_PRIOR_INVALID'; END IF;","IF p_expected_prior IS NOT NULL OR p_action='REVOKE' THEN RAISE EXCEPTION 'FEP_INITIAL_PRIOR_INVALID'; END IF;")
s=s.replace('AND head_version=p_expected_version AND activation_id IS NOT DISTINCT FROM p_expected_prior;','AND head_version=p_expected_version AND activation_id IS NOT DISTINCT FROM p_expected_prior\n   AND (p_action<>\'REVOKE\' OR grant_id=p_grant_id);')
s+='''
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
   OR (o.episode_key IS NOT NULL AND x.scope_id=o.scope_id AND x.episode_key=o.episode_key))) THEN
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
'''
atomic(p,s)
mfile=B/'FEP_R2_MODULE_DRAFT.md';m=mfile.read_text(encoding='utf8')
m=m.replace('permission_keys、activation、prediction acceptance receipt、priority引用和API readback使用同一key，','permission_keys限定CHAMPION；DESCRIPTIVE_DISPLAY/MODEL_DISPLAY/PRIORITY_USE只授权该目标CHAMPION输出，同集合BASELINE/CHALLENGER仍是诊断/Shadow，不继承展示/排序权限。SHADOW_INFERENCE可计算集合成员但不给生产展示权。permission_keys、activation、prediction acceptance receipt、priority引用和API readback使用同一key，')
m=m.replace('一个实验的FIT/TUNE/CALIBRATION/OUTER_TEST各自截止和label可见门不能共享较晚截止。','同fold的FIT/TUNE/CALIBRATION/OUTER_TEST不得复用同observation、同市场日期组或跨边界同episode，完整purge清单仍须接受服务验收；不同fold可在未来窗口中合法复用已可见历史。一个实验的FIT/TUNE/CALIBRATION/OUTER_TEST各自截止和label可见门不能共享较晚截止。设计DDL已有fold cutoff、selection可见性/成熟度及row ELIGIBLE与phase分离触发器参考，实际PostgreSQL执行/并发反例仍待E1。')
m=m.replace('API只读对应accepted ALLOW head，','CAS请求重投按request_id及全参数一致性回读原receipt；请求内容改变则IDEMPOTENCY_CONFLICT。已有head的REVOKE仅允许其当前grant_id，不能伪造撤销另一个model_set。API只读对应accepted ALLOW head，')
atomic(mfile,m)
f=B/'FINAL_REV4_FEP_R2_DRAFT.md';sfinal=f.read_text(encoding='utf8').split('# 90. FEP R2｜')[0]
sfinal=sfinal.replace('当前生效版本为REV3-FEP','当前修订版本为REV4-FEP-R2，待外部R2复审')
atomic(f,sfinal.rstrip()+'\n\n'+m.replace('# FEP R2｜','# 90. FEP R2｜',1)+'\n**文档结束**\n')
print('R2 hardened',len(s.splitlines()),'schema lines')

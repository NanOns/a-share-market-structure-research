from pathlib import Path
import os,re,hashlib
B=Path(__file__).parent;ROOT=Path.cwd()
def atomic(p,text):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name('.'+p.name+'.tmp')
 with t.open('wb') as f:f.write(text.encode('utf8'));f.flush();os.fsync(f.fileno())
 os.replace(t,p)
s=(ROOT/'docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql').read_text(encoding='utf8')
s=s.replace('FEP_SCHEMA_DESIGN_V1','FEP_SCHEMA_DESIGN_V2')
s=s.replace(' label_event_end date NOT NULL, label_due_at timestamptz NOT NULL, system_available_at timestamptz NOT NULL,',' label_event_end date NOT NULL, source_fact_available_at timestamptz NOT NULL,\n label_training_mature_at timestamptz NOT NULL, label_revision_available_at timestamptz NOT NULL,')
s=s.replace('CHECK(system_available_at>=label_due_at)','CHECK(label_revision_available_at>=source_fact_available_at)')
s=s.replace(' selected_label_revision integer, reason text,',' reason text,')
s=s.replace(' FOREIGN KEY(observation_id,target_id,selected_label_revision) REFERENCES fep.label_revisions(observation_id,target_id,revision),\n CHECK(status<>\'ELIGIBLE\' OR selected_label_revision IS NOT NULL)',' FOREIGN KEY(target_id) REFERENCES fep.targets(target_id)')
s=s.replace("status IN ('ELIGIBLE','PENDING','MISSING_LABEL','QUALITY_EXCLUDED','SCOPE_EXCLUDED')","status IN ('EXPECTED','SCOPE_EXCLUDED')")
pos=s.index('CREATE TABLE fep.dataset_rows')
s=s[:pos]+'''-- Dataset global cutoff is a manifest upper bound, never a fold selection cutoff.
-- Fit/tune/calibration/outer-test phases have distinct as-of cutoffs; all are frozen.
CREATE TABLE fep.dataset_fold_cutoffs (
 dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id), fold_id text NOT NULL,
 partition_name text NOT NULL CHECK(partition_name IN ('FIT','TUNE','CALIBRATION','OUTER_TEST')),
 fold_dataset_cutoff timestamptz NOT NULL, selection_policy_contract_id text NOT NULL REFERENCES fep.contracts(contract_id),
 split_digest fep.sha256 NOT NULL,
 PRIMARY KEY(dataset_id,fold_id,partition_name)
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
'''+s[pos:]
s=s.replace(' PRIMARY KEY(observation_id,target_id,revision),',' PRIMARY KEY(observation_id,target_id,revision),\n UNIQUE(observation_id,target_id,revision,target_digest),')
s=s.replace(' label_revision integer NOT NULL, weight double precision',' label_revision integer NOT NULL, selected_label_digest fep.sha256 NOT NULL, weight double precision')
s=s.replace('PRIMARY KEY(dataset_id,observation_id,target_id,fold_id),','PRIMARY KEY(dataset_id,observation_id,target_id,fold_id,partition_name),\n FOREIGN KEY(dataset_id,fold_id,partition_name,observation_id,target_id,label_revision,selected_label_digest)\n REFERENCES fep.dataset_fold_label_selection(dataset_id,fold_id,partition_name,observation_id,target_id,selected_label_revision,selected_label_digest),')
start=s.index('CREATE TABLE fep.activations (');end=s.index('CREATE TABLE fep.prediction_slots',start)
s=s[:start]+'''-- The exact permission tuple is immutable and model-set-specific. Entity/variant
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
'''+s[end:]
s=s.replace('UNIQUE(model_set_id,model_id)\n);','UNIQUE(model_set_id,model_id),\n UNIQUE(model_set_id,scope_id,target_id,horizon,feature_contract_id,role)\n);')
start=s.index('CREATE TABLE fep.acceptance_receipts (');end=s.index('CREATE TABLE fep.reports',start)
s=s[:start]+'''-- Each accepted target/capability uses the same exact grant key as activation/readback.
CREATE TABLE fep.acceptance_receipts (
 receipt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES fep.prediction_runs(run_id),
 accepted_at timestamptz NOT NULL, grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id),
 activation_id text NOT NULL,
 validation_contract_id text NOT NULL REFERENCES fep.contracts(contract_id), checks jsonb NOT NULL,
 UNIQUE(run_id,grant_id), UNIQUE(receipt_id,run_id,grant_id),
 FOREIGN KEY(activation_id,grant_id) REFERENCES fep.activations(activation_id,grant_id)
);
'''+s[end:]
s=s.replace('axis_values jsonb NOT NULL, prediction_refs jsonb NOT NULL, permission_receipt_id text NOT NULL REFERENCES fep.acceptance_receipts(receipt_id),','axis_values jsonb NOT NULL, prediction_refs jsonb NOT NULL,')
pos=s.index('CREATE INDEX label_by_binding')
s=s[:pos]+'''-- Multi-target priority rows must cite every target's exact PRIORITY_USE grant;
-- a successful T5 grant cannot authorize another target or T20.
CREATE TABLE fep.priority_projection_grants (
 projection_id text NOT NULL REFERENCES fep.priority_projection(projection_id),
 grant_id text NOT NULL REFERENCES fep.permission_keys(grant_id), run_id text NOT NULL,
 permission_receipt_id text NOT NULL,
 PRIMARY KEY(projection_id,grant_id),
 FOREIGN KEY(permission_receipt_id,run_id,grant_id) REFERENCES fep.acceptance_receipts(receipt_id,run_id,grant_id)
);
'''+s[pos:]
s=s.replace('fep.label_source_bindings(system_available_at,label_due_at)','fep.label_source_bindings(label_revision_available_at,label_training_mature_at)')
s=s.replace('CREATE INDEX activation_asof ON fep.activations(scope_id,capability,effective_at);','CREATE INDEX activation_asof ON fep.activations(grant_id,effective_at);\nCREATE INDEX fold_label_asof ON fep.dataset_fold_cutoffs(dataset_id,fold_id,partition_name,fold_dataset_cutoff);')
start=s.index('DO $$ DECLARE r record;');end=s.index('-- REQUIRED E1/E5',start)
tables=re.findall(r'CREATE TABLE fep\.(\w+)',s)
guards='-- Explicit guards for this version; every future fact table migration must\n-- create its own guard and be checked against the registry. No automatic inheritance.\n'
for table in tables:
 if table!='deployment_heads':guards+=f'CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON fep.{table} FOR EACH ROW EXECUTE FUNCTION fep.reject_mutation();\n'
s=s[:start]+guards+s[end:]
s=s.replace('Dataset selected revision availability <= cutoff, whole date folds and eligible risk set/quality;','Per-fold+partition selected revision availability <= fold cutoff <= dataset manifest upper cutoff;\n--    source_fact_available_at, label_training_mature_at and label_revision_available_at each <= fold cutoff;\n--    full denominator ledger holds no selected revision, fold selection freezes exact digest/reason;')
s=s.replace('activation grants exact model_set/scope/capability','activation grants exact scope/target/horizon/feature_contract/model_set/capability')
s=s.replace('must match ELIGIBLE selected revision and dataset scope exactly.','must match ELIGIBLE fold+partition selection revision/digest and dataset scope exactly.')
s=s.replace('report manifest freezes label/prediction revisions and denominators, not latest heads.','report manifest freezes label/prediction revisions and denominators, not latest heads.\n-- 10. current daily Radar PRIORITY_USE requires DAILY_LANDMARK/candidate-day scope,\n--     same-date snapshot and forecast plus pre-registered coverage. ENTRY rows are annotation only.\n-- 11. Every new historical table must have an explicit append-only guard; only\n--     deployment_heads allows controlled updates, denies DELETE and direct application DML.\n--     Its trigger/function+DB role restriction and CAS rollback require actual E1 tests.')
# A concrete design function carrying CAS semantics; unexecuted pending external review.
s+='''
-- R2 CAS reference design. A service validates evidence/permission/state first;
-- this function serializes an already validated exact tuple transaction. Caller
-- must have no direct DML grants on deployment_heads, activations or receipts.
-- SECURITY DEFINER owner/search_path/EXECUTE privileges must be sealed by E1.
-- Future-effective activations are forbidden here: use explicit scheduled intents
-- and invoke this same CAS at the effective moment, not replace the head early.
CREATE FUNCTION fep.cas_deploy(
 p_grant_id text, p_activation_id text, p_action text, p_expected_version bigint,
 p_expected_prior text, p_request_id text, p_receipt_digest fep.sha256, p_checks jsonb
) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE k fep.permission_keys%ROWTYPE; n integer; ts timestamptz := clock_timestamp();
BEGIN
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;
 IF p_expected_version<0 OR p_action NOT IN ('ALLOW','REVOKE') THEN RAISE EXCEPTION 'FEP_INVALID_CAS_INPUT'; END IF;
 INSERT INTO fep.activations(activation_id,grant_id,action,effective_at,recorded_at,prior_activation_id,expected_head_version,receipt_digest)
 VALUES(p_activation_id,p_grant_id,p_action,ts,ts,p_expected_prior,p_expected_version,p_receipt_digest);
 IF p_expected_version=0 THEN
  IF p_expected_prior IS NOT NULL THEN RAISE EXCEPTION 'FEP_INITIAL_PRIOR_INVALID'; END IF;
  INSERT INTO fep.deployment_heads(scope_id,capability,target_id,horizon,feature_contract_id,model_set_id,grant_id,activation_id,head_version,updated_at)
  VALUES(k.scope_id,k.capability,k.target_id,k.horizon,k.feature_contract_id,k.model_set_id,k.grant_id,p_activation_id,1,ts)
  ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS n=ROW_COUNT;
 ELSE
  UPDATE fep.deployment_heads SET model_set_id=k.model_set_id,grant_id=k.grant_id,
   activation_id=p_activation_id,head_version=p_expected_version+1,updated_at=ts
  WHERE scope_id=k.scope_id AND capability=k.capability AND target_id=k.target_id
   AND horizon=k.horizon AND feature_contract_id=k.feature_contract_id
   AND head_version=p_expected_version AND activation_id IS NOT DISTINCT FROM p_expected_prior;
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
'''
atomic(B/'FEP_R2_SCHEMA_DESIGN_20260930.sql',s)
m=(ROOT/'docs/design/FEP_R1_MODULE_DESIGN_20260930.md').read_text(encoding='utf8')
m=m.replace('FEP R1','FEP R2').replace('DA-MSR-V4.2.2-FEP-R1','DA-MSR-V4.2.2-FEP-R2').replace('FEP_R1_SCHEMA_DESIGN','FEP_R2_SCHEMA_DESIGN')
m=m.replace('状态：DESIGN_REVISED / PARAMETER_AND_IMPLEMENTATION_GATES_PENDING。','状态：R2_PATCHED / EXTERNAL_REAUDIT_PENDING / IMPLEMENTATION_NOT_VERIFIED。\n外部R1审计结论EXTERNAL_DESIGN_ACCEPTANCE_BLOCKED_PENDING_R2作为既有回执保留；本次提出修复，不自行宣称EXTERNAL_DESIGN_ACCEPTANCE_PASS。FEP最终冻结、migration及E1正式任务卡等待外部R2复审；原主线不受此门阻断。')
m=m.replace('这是R0的完整替代模块设计','这是R1外部审计后定点更新的模块设计')
m=m.replace('label_due_at、label_system_available_at','source_fact_available_at、label_training_mature_at、label_revision_available_at')
m=m.replace('所选label revision及其全部派生依赖available_at<=dataset_cutoff<=fit_started；label_due_at<=dataset_cutoff，label_event_end不晚于允许边界。','所选label的source_fact_available_at、label_training_mature_at及label_revision_available_at分别<=该fold/partition的fold_dataset_cutoff；其余依赖同样需可见，fold cutoff不超过dataset manifest上界或所对应拟合/选择截止。label_event_end不晚于允许边界。')
m=m.replace('每边界按真实label_event_end及label_system_available_at purge：','每边界按真实label_event_end、source_fact_available_at及label_revision_available_at purge：')
m=m.replace('dataset为long form：','完整N-window target三时间定义：source_fact_available_at为所绑定原事实及依赖实际系统可见时间；label_training_mature_at为冻结日历的N-window训练成熟时刻；label_revision_available_at为本次投影revision实际可用时间，至少不早于它消费的事实。事件可T+2已知且记录，而T+5 target统一等T+5成熟才训练；不要求source或revision可见时间>=成熟时刻，不倒填可见时间。早记录的revision尚不能证明其余N-window完整质量时保留PENDING，成熟后需权威状态/版本确认，不能仅等到日历日期就自动解锁缺失标签。\n\ndataset为long form：')
m=m.replace('## FEP.8 条件统计的确定算法','R2 dataset完整分母ledger只记录expected scope/排除原因，不保存全局selected_label_revision。dataset_fold_cutoffs冻结(dataset,fold,partition)的as-of cutoff；dataset_fold_label_selection按同键加observation/target保存revision、digest、eligibility和选择原因。dataset_rows复合FK必须指向该fold/partition选择，不能从较晚全局dataset cutoff替早fold取latest。早fold可用r1、晚fold可用r2，dataset整体digest冻结全部cutoff/选择/分母。一个实验的FIT/TUNE/CALIBRATION/OUTER_TEST各自截止和label可见门不能共享较晚截止。\n\n## FEP.8 条件统计的确定算法')
m=m.replace('production权限拆成DESCRIPTIVE_DISPLAY、MODEL_DISPLAY、PRIORITY_USE，并按实体/scope/target/horizon/variant/model_set授权；','权限的grant_key=(scope_id,target_id,horizon,feature_contract_id,model_set_id,capability)，scope明确实体类型和variant；capability包括SHADOW_INFERENCE以及DESCRIPTIVE_DISPLAY、MODEL_DISPLAY、PRIORITY_USE。permission_keys、activation、prediction acceptance receipt、priority引用和API readback使用同一key，不用scope+model_set宽授权覆盖全部target/horizon；')
m=m.replace('FEP accepted model-set deployment head以scope+capability CAS更新，activation receipt与指针同事务；并发切换失败重读不覆盖，既有slot不随head漂移。','FEP deployment_heads受控可变指针按(scope,capability,target,horizon,feature_contract)唯一；model_set是替换payload而非head key。activation历史保留grant_key、prior_activation_id及expected_head_version；cas_deploy设计函数验证expected version+prior指针，初始0→1或更新v→v+1，并将activation、deployment_change_receipt和head同事务提交，CAS失败全部回滚。API只读对应accepted ALLOW head，REVOKE拒绝该精确key，既有slot不随head漂移。V1只允许实际切换时生效，不提前用未来activation占head；定时意图等生效时再CAS。应用角色不得直接UPDATE/DELETE head或事实表，触发器/函数权限及故障演练为E1实际验收门。')
m=m.replace('评估须同日同候选集合、','ENTRY-only FEP只用于事件日ENTRY scope研究注释。今日Radar全候选PRIORITY_USE必须有DAILY_LANDMARK或明确注册的等价candidate-day scope、当日feature和当日预测，并满足预注册同候选覆盖门；不能把入选日预测长期挂靠为“今日预测”。持久候选尚无daily样本/模型时保留PRIORITY_V1，ENTRY历史预测只在历史面板注明as-of，不影响今日全池排序。E2→E5早期ENTRY展示可先行，但不授予daily Priority。\n评估须同日同候选集合、')
m=m.replace('所有事实表append-only；current指针为可重建投影；','所有事实/历史表append-only，当前deployment_heads是唯一受控UPDATE的指针表，禁止DELETE；每个当前及未来新增事实表migration必须显式建guard并通过表清单测试，不能假设一次pg_tables循环永久覆盖未来表。')
m=m.replace('dataset expected-target eligibility ledger和合格membership、','dataset expected-target eligibility ledger、逐fold/partition cutoff和label选择及合格membership、')
m=m.replace('model registry/sets/activations、','model registry/sets、细粒度permission keys/activations、deployment heads和CAS receipts、')
m=m.replace('13. 新champion只影响future activation slot；历史prediction/readback/原始cohort、Focus手工选择不变。','''13. 新champion只影响future activation slot；历史prediction/readback/原始cohort、Focus手工选择不变。
14. 同dataset中早fold在r2可见前选r1，晚fold在r2可见后选r2；早fold行指向r2或错误partition选择必须拒绝。
15. 多target model_set中仅T5 MARKET_EXCESS允许MODEL_DISPLAY，T20 INVALIDATION仍Shadow；错target/horizon/feature grant的receipt/API/priority引用必须拒绝。
16. 两并发切换都携expected version=7/prior=A：只能一个提交version8，另一个CAS_CONFLICT且其activation/receipt不能残留；相同request_id重投必须readback原receipt而非重做切换。初始head创建、REVOKE/rollback也须验收。
17. T+2事件可见、T+5训练成熟：T+3训练拒绝，成熟但revision迟到仍拒绝；事实可见时间不晚于成熟的合法记录不被CHECK拒绝。
18. 持续PREWATCH无今日ENTRY：旧ENTRY forecast仅历史注释；无DAILY scope模型不能进入今日全Radar Priority。
19. 新增事实表无append-only guard的migration应拒绝；head CAS允许受控更新但直接修改/删除应拒绝。''')
atomic(B/'FEP_R2_MODULE_DRAFT.md',m)
oldmain=(ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV3_FEP_20260930.md').read_text(encoding='utf8')
prefix=oldmain.split('# 90. FEP R1｜')[0]
prefix=prefix.replace('DA-MSR-V4.2.2-CODEX-REV3-FEP','DA-MSR-V4.2.2-CODEX-REV4-FEP-R2')
prefix=prefix.replace('> 代码基线：','> ORIGINAL DESIGN BASELINE：')
prefix=prefix.replace('> 本轮：FEP R1多方设计审计后并入；当前代码核对HEAD=0581731c1284e82380fa115156f1dc0a16a38bd4。原代码基线仅保留沿革，不代表当前实现。','> CURRENT AUDITED IMPLEMENTATION HEAD：codex/v4-system-reform @ 0581731c1284e82380fa115156f1dc0a16a38bd4（本次仅设计核对）。\n> 本轮：FEP R2定点修订；EXTERNAL_REAUDIT_PENDING。历史R1设计回执不代表最终外部冻结通过。')
prefix=prefix.replace('追加§90 FEP R1','追加§90 FEP R2').replace('STATUS = DOCUMENT_REVISED / FEP_DESIGN_INTEGRATED / IMPLEMENTATION_NOT_VERIFIED','STATUS = DOCUMENT_REVISED / FEP_R2_PATCHED_EXTERNAL_REAUDIT_PENDING / IMPLEMENTATION_NOT_VERIFIED')
prefix=prefix.replace('FEP仅获得设计并入状态，未取得训练、模型展示或Priority生产权限。','FEP作为修订设计保留在正文；最终设计冻结、migration及E1正式任务卡等待外部R2复审，不自行授予EXTERNAL_DESIGN_ACCEPTANCE_PASS；原主线继续推进。')
# main cross-links replace only FEP-specific paragraphs
prefix=prefix.replace('FEP默认Shadow独立轴，只有§90的PRIORITY_USE门通过后','FEP默认Shadow独立轴，ENTRY仅事件日注释；今日全Radar必须DAILY_LANDMARK/candidate-day scope和同日覆盖门，只有§90的PRIORITY_USE门通过后')
prefix=prefix.replace('FEP新增registry由§90 FEP.7/12及配套设计DDL定义：','FEP新增registry由§90 FEP.7/12及R2配套设计DDL定义：')
prefix=prefix.replace('dataset eligibility ledger、dataset rows、model/set/activation','dataset完整分母ledger、fold/partition选择、dataset rows、model/set/细粒度grant/activation/deployment head/CAS receipt')
prefix=prefix.replace('参数、每日outbox','参数、每日outbox')
final=prefix.rstrip()+'\n\n'+m.replace('# FEP R2｜','# 90. FEP R2｜',1)+'\n**文档结束**\n'
atomic(B/'FINAL_REV4_FEP_R2_DRAFT.md',final)
print('R2 candidates',len(final.splitlines()),len(s.splitlines()))

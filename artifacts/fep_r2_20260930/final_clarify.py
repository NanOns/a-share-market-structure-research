from pathlib import Path
import os
b=Path(__file__).parent
def atomic(p,s):
 t=p.with_name('.'+p.name+'.tmp')
 with t.open('wb') as f:f.write(s.encode('utf8'));f.flush();os.fsync(f.fileno())
 os.replace(t,p)
p=b/'FEP_R2_SCHEMA_DESIGN_20260930.sql';s=p.read_text(encoding='utf8')
s=s.replace('fold_dataset_cutoff timestamptz NOT NULL, selection_policy_contract_id','fold_dataset_cutoff timestamptz NOT NULL, phase_started_at timestamptz NOT NULL, selection_policy_contract_id')
s=s.replace('PRIMARY KEY(dataset_id,fold_id,partition_name)\n);','PRIMARY KEY(dataset_id,fold_id,partition_name), CHECK(fold_dataset_cutoff<=phase_started_at)\n);')
s=s.replace('training_run_id text PRIMARY KEY, dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id),','training_run_id text PRIMARY KEY, dataset_id text NOT NULL REFERENCES fep.datasets(dataset_id),\n fold_id text NOT NULL, phase_manifest jsonb NOT NULL CHECK(jsonb_typeof(phase_manifest)=\'object\'),')
s=s.replace('prior.grant_id<>p_grant_id OR prior.activation_id<>p_activation_id OR a.action<>p_action','prior.grant_id IS DISTINCT FROM p_grant_id OR prior.activation_id IS DISTINCT FROM p_activation_id OR a.action IS DISTINCT FROM p_action')
s=s.replace('prior.expected_head_version<>p_expected_version','prior.expected_head_version IS DISTINCT FROM p_expected_version')
s=s.replace('a.receipt_digest<>p_receipt_digest','a.receipt_digest IS DISTINCT FROM p_receipt_digest')
s=s.replace('BEGIN\n SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;','''BEGIN
 IF p_grant_id IS NULL OR p_activation_id IS NULL OR p_action IS NULL OR p_expected_version IS NULL
  OR p_request_id IS NULL OR p_receipt_digest IS NULL OR p_checks IS NULL THEN
  RAISE EXCEPTION 'FEP_REQUIRED_CAS_PARAMETER_NULL';
 END IF;
 SELECT * INTO STRICT k FROM fep.permission_keys WHERE grant_id=p_grant_id;''')
s=s.replace('x.scope_id=o.scope_id AND x.episode_key=o.episode_key','x.scope_id=o.scope_id AND x.entity_id=o.entity_id AND x.episode_key=o.episode_key')
s+='''
-- Phase manifest: FIT cutoff <= this fold's fit_started; TUNE cutoff <= selection_started;
-- CALIBRATION cutoff <= calibrator_fit_started; OUTER_TEST cutoff is the frozen scoring
-- knowledge deadline and can be later than model fit. OUTER_TEST rows are evaluation-only.
-- phase_started_at is actual start of the respective consumer (evaluation start for TEST),
-- not a substituted global training start. E1/E3 validator must match these named times
-- to dataset_fold_cutoffs and run phase_manifest, and prohibit TEST rows as fit inputs.
-- Episode identity is (scope_id,entity_id,episode_key), not a reused entity-local string alone.
'''
atomic(p,s)
p=b/'FEP_R2_MODULE_DRAFT.md';m=p.read_text(encoding='utf8')
a='一个实验的FIT/TUNE/CALIBRATION/OUTER_TEST各自截止和label可见门不能共享较晚截止。'
z='各phase时间显式进入fold cutoff表phase_started_at与training_run.phase_manifest：FIT cutoff<=本fold fit_started；TUNE cutoff<=预注册selection_started；CALIBRATION cutoff<=calibrator_fit_started；OUTER_TEST cutoff为冻结评分知识截止，可晚于原model fit，TEST labels仅用于evaluation且不得进该模型拟合/选参/校准。phase_started_at为实际消费者开始时间（TEST为评分开始），其cutoff不晚于该时刻，不能借全局fit_started代替。episode唯一身份为(scope_id,entity_id,episode_key)，不同股票复用局部episode号不能误判同episode。一个实验的FIT/TUNE/CALIBRATION/OUTER_TEST各自截止和label可见门不能共享较晚截止。'
assert a in m;m=m.replace(a,z)
atomic(p,m)
f=b/'FINAL_REV4_FEP_R2_DRAFT.md';prefix=f.read_text(encoding='utf8').split('# 90. FEP R2｜')[0]
atomic(f,prefix.rstrip()+'\n\n'+m.replace('# FEP R2｜','# 90. FEP R2｜',1)+'\n**文档结束**\n')
print('CAS NULL and phase cutoffs repaired')

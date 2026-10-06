# V4-15E5 R1R1A｜Remote Publication & Evidence Closure Task R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 R1R1A  
> 任务性质：执行结果远端发布 / 证据闭环 / 审计入口修复  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 当前远端基线：`2bdca9dd87d210f778f4ec90aa4fbaa5f1708866`  
> 上游正式任务：`V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR_TASK_R1_20261006.md`  
> 上游审计：`V4_15E5_R1R1_REMOTE_EXECUTION_VISIBILITY_INDEPENDENT_AUDIT_R1_20261006.md`  
> 目标最高状态：`R1R1_REMOTE_CANDIDATE_VISIBLE_READY_FOR_EXTERNAL_AUDIT`

---

## 0. 唯一目标

本任务不新增 FEP 功能，不重新设计模型，不新增 Priority 算法。

唯一目标是：

> 把“已经执行完成的 R1R1 本地实现”正式、完整、可复核地发布到 GitHub 远端，并使独立审计能够读取全部代码、migration、tests、evidence 与 candidate seal。

如果本地实际没有完成 R1R1：

```text
不得伪造完成
不得只补 completion report
不得只提交文档
必须回到原 R1R1 正式任务卡继续实现
```

---

## 1. 运行前检查

必须首先输出：

```text
LOCAL_HEAD
LOCAL_BRANCH
REMOTE_HEAD
LOCAL_STATUS
LOCAL_UNPUSHED_COMMITS
LOCAL_CHANGED_FILES
```

并验证：

```text
branch = codex/v4-system-reform
```

当前已知远端：

```text
2bdca9dd87d210f778f4ec90aa4fbaa5f1708866
```

### 允许情况 A

```text
LOCAL_HEAD > REMOTE_HEAD
```

且本地存在完整 R1R1 实现。

→ 继续本任务。

### 允许情况 B

本地有未提交 R1R1 改动。

→ 先按本任务要求补齐 evidence/tests/seal，再 commit。

### 阻断情况

本地没有任何 R1R1 实现。

必须输出：

```text
R1R1_LOCAL_IMPLEMENTATION =
NOT_FOUND

NEXT =
RETURN_TO_ORIGINAL_R1R1_IMPLEMENTATION_TASK
```

不得制作假 evidence。

---

## 2. 必须确认的实现范围

本任务不重新实现，但必须确认本地候选至少覆盖原 R1R1 的三个 blocker：

```text
E5-B01
CANONICAL_FEP_LEDGER_INTEGRATION

E5-B02
CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING

E5-B03
CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION
```

任何一个缺失：

```text
不得宣称 R1R1 complete
```

---

## 3. 强制代码/Schema检查

在 push 前必须核对：

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

必须保持历史不可变。

若 R1R1 需要 schema repair：

```text
必须是新的 additive migration
```

不得：

```text
直接改 028~031
删除 FK
弱化 append-only
把所有 model_role 放开
伪造 CHAMPION
```

---

## 4. canonical authority 硬门

push 前必须确认正式执行链落在：

```text
fep.*
```

而不是：

```text
fep_e5_engineering.*
```

旧 `fep_e5_engineering.*` 允许保留：

```text
NON_AUTHORITY_ONLY
```

不得继续作为正式 R1R1 ledger。

---

## 5. publication / snapshot identity 硬门

正式历史链必须可追溯：

```text
historical source event
→ fep.observations
→ fep.observation_revisions
→ fep.snapshots
→ fep.targets
→ fep.models / model_sets
→ fep.prediction_slots
→ fep.predictions
```

publication 必须是真实：

```text
v4.publications.publication_id
```

禁止：

```text
row digest 冒充 publication_id
artifact digest 冒充 publication_id
current publication 回填历史 T0
为通过 FK 临时制造 fake accepted publication
```

如果无法合法映射：

```text
CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING
```

并阻断。

---

## 6. permission / deployment 硬门

必须验证正式：

```text
fep.permission_keys
fep.activations
fep.deployment_heads
fep.deployment_change_receipts
fep.cas_deploy(...)
```

允许的工程权限最高为：

```text
SHADOW_INFERENCE
```

且非 Champion shadow 必须是精确、窄范围、显式 model_set_member role 绑定。

仍然禁止：

```text
MODEL_DISPLAY
PRIORITY_USE
DESCRIPTIVE_DISPLAY
FEP_PRODUCTION
CHAMPION fabrication
REAL_OOS fabrication
FIRST_OBSERVED fabrication
```

---

## 7. 必需 evidence 目录

必须存在：

```text
reports/fep_e5_r1r1/
```

至少包含：

```text
BASELINE_AUTHORITY_BINDINGS.json
CONTRACT_CONFLICT_DISPOSITION.json
MIGRATION_ALLOCATION_READBACK.json
CANONICAL_SCHEMA_REPAIR_READBACK.json
CANONICAL_IDENTITY_MAPPING.json
CANONICAL_PUBLICATION_BINDING_READBACK.json
CANONICAL_LEDGER_READBACK.json
CANONICAL_PREDICTION_BINDING_READBACK.json
CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION.json
CANONICAL_PERMISSION_MATRIX.json
CANONICAL_CAS_CONCURRENCY.json
CANONICAL_CAS_IDEMPOTENCY.json
CANONICAL_ROLLBACK_DRILL.json
CANONICAL_PRIORITY_FIXTURE_READBACK.json
ISOLATED_NAMESPACE_NONAUTHORITY_READBACK.json
FRESH_DB_READBACK.json
UPGRADE_DB_READBACK.json
API_READBACK.json
NEGATIVE_MATRIX.json
PROTECTED_STATE_READBACK.json
GITHUB_CI_READBACK.json
CHANGED_FILE_LIST.json
FEP_E5_R1R1_CANDIDATE_SEAL.json
COMPLETION_REPORT.md
targeted.log
targeted.xml
targeted_SUMMARY.json
scoped.log
scoped.xml
scoped_SUMMARY.json
```

N/A 项：

```text
文件仍必须存在
status = NOT_APPLICABLE
reason = ...
```

---

## 8. 测试要求

不能继承旧 E5：

```text
306 passed / 1 skipped
2665 passed / 4 skipped / 52 known failures
```

作为 R1R1 新测试证明。

必须重新运行：

```text
R1R1 targeted
R1R1 scoped regression
```

要求：

```text
introduced active failures = 0
```

历史 known debt：

```text
继续显式列出
不得隐藏
```

---

## 9. Fresh / Upgrade DB

必须分别证明：

```text
FRESH_DB = PASS
UPGRADE_DB = PASS
```

两条路径都必须真正经过：

```text
canonical fep.*
```

不能 fresh 用 canonical、upgrade 仍走 isolated。

---

## 10. CAS / Rollback

必须至少证明：

```text
ALLOW
REVOKE
idempotency
wrong expected version
wrong prior
cross-target
cross-horizon
cross-model-set
atomic rollback
concurrent initial CAS
```

并确认：

```text
failure does not mutate Priority V1
failure does not mutate accepted Core
failure does not mutate historical prediction rows
```

---

## 11. Protected State

必须 readback：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16_ACCEPTED_HEAD
R25 state
PRIORITY_V1
Core/Profile/State/Radar/Cohort
TDX source trees
```

TDX：

```text
READ_ONLY
NO_MUTATION
```

---

## 12. Commit / Push 规则

所有 R1R1 代码、migration、tests、evidence 必须：

```text
git add exact files
git commit
git push origin codex/v4-system-reform
```

禁止：

```text
只 push 文档
只 push completion report
只 push evidence 不 push implementation
只 push implementation 不 push evidence
```

必须输出：

```text
IMPLEMENTATION_HEAD
PARENT_SHA
REMOTE_BRANCH_HEAD_AFTER_PUSH
```

并要求：

```text
REMOTE_BRANCH_HEAD_AFTER_PUSH == IMPLEMENTATION_HEAD
```

---

## 13. GitHub 远端 readback

push 后必须从远端重新读取：

```text
commit SHA
parent SHA
changed file list
candidate seal
completion report
canonical ledger readback
permission readback
protected state readback
```

如果远端 readback 仍看不到：

```text
REMOTE_PUBLICATION = FAIL
```

本任务不得结束为 PASS。

---

## 14. Candidate Seal

`FEP_E5_R1R1_CANDIDATE_SEAL.json` 至少绑定：

```text
task_card_sha256
baseline_sha
implementation_head
parent_sha
changed_file_digest
migration_digest
code_digest
test_digest
evidence_digest
protected_state_digest
canonical_schema_identity
external_acceptance = false
```

---

## 15. 成功退出状态

唯一允许：

```text
V4_15E5_R1R1_REMOTE_PUBLICATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

REMOTE_IMPLEMENTATION_VISIBLE = true
REMOTE_EVIDENCE_VISIBLE = true
E5_B01 = CANDIDATE_PENDING_EXTERNAL_AUDIT
E5_B02 = CANDIDATE_PENDING_EXTERNAL_AUDIT
E5_B03 = CANDIDATE_PENDING_EXTERNAL_AUDIT

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1
```

---

## 16. 禁止越级

本任务结束后不得自动执行：

```text
V4-16
E6
Production Priority
Model Promotion
Default UI Cutover
Focus Cutover
REAL_DAILY activation
```

必须先做：

```text
R1R1 Independent External Audit
```

由外部审计决定是否关闭：

```text
E5-B01
E5-B02
E5-B03
```

---

## 17. 最终一句

本轮不是重做 R1R1，而是把“已经执行的 R1R1”变成：

```text
远端可见
证据完整
可独立复核
可正式验收
```

只有做到这一步，项目才能继续向后推进。

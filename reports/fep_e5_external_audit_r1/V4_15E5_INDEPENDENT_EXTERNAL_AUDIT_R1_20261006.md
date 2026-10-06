# V4-15E5｜FEP Projection / Priority Shadow Engineering 独立外部审计 R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb`  
> 审计 HEAD：`51a1aab3fc9fe5bb390ec768dfd9514a1db6af54`  
> Parent：`adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb`

---

# 0. 唯一总裁决

```text
V4_15E5_FINAL_EXTERNAL_AUDIT =
BLOCKED_R1_CANONICAL_FEP_INTEGRATION

E5_PROTOCOL_FREEZE = PASS
E5_MODEL_EVIDENCE_CLASS = PASS
E5_HISTORICAL_ENTRY_PROJECTION_PROTOTYPE = PASS_ENGINEERING
E5_ENTRY_DAILY_SEPARATION = PASS
E5_PRIORITY_V2_SHADOW_ENGINE = PASS_ENGINEERING_FIXTURE
E5_PERMISSION_FAIL_CLOSED = PASS_IN_ISOLATED_ENGINEERING_LEDGER
E5_ROLLBACK_ATOMICITY = PASS_IN_ISOLATED_ENGINEERING_LEDGER
E5_NEGATIVE_MATRIX = PASS
E5_REGRESSION = PASS_CAPABILITY_SCOPED_WITH_KNOWN_DEBT

E5_CANONICAL_FEP_LEDGER_INTEGRATION = FAIL
E5_CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING = FAIL
E5_CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION = FAIL

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
PRIORITY_USE = UNGRANTED
MODEL_DISPLAY = UNGRANTED
CHAMPION = false
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

本轮不能接受为 `FEP_E5_ENGINEERING_ACCEPTED`。

准确定位是：

> E5 已经完成了一套质量较高、权限边界严格的独立工程原型；但它没有把这些能力接入 E1 已建立并冻结的 canonical `fep.*` 数据库合同，而是新建了 `fep_e5_engineering.*` 平行 ledger。因此目前证明的是“旁路原型可以工作”，尚未证明“正式 FEP 数据链可以工作”。

---

# 1. Drive / Git 基线｜PASS

本轮先同步 Drive 正式文件：

```text
V4_15E5_FEP_PROJECTION_PRIORITY_SHADOW_ENGINEERING_TASK_R1_20261006.md
V4_FEP_EXECUTION_MASTER_V4_15E5_R1_20261006.md
```

二者基线均为：

```text
adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb
```

GitHub 当前 E5 HEAD：

```text
51a1aab3fc9fe5bb390ec768dfd9514a1db6af54
```

唯一父提交正是任务基线，因此：

```text
BASELINE_IDENTITY = PASS
CLEAN_STAGE_DELTA = PASS
```

---

# 2. Protocol Freeze｜PASS

`PROTOCOL_FREEZE.json`：

```text
status = PASS_FROZEN_BEFORE_PROJECTION
projection_runs_before_freeze = 0
effectiveness_evaluation_open = false
```

运行前冻结了：

```text
effectiveness_disposition_rule
primary_metric
tie_break
promotion_boundary
priority_projection_boundary
shadow_only_boundary
model_evidence_class
```

其中：

```text
E5_EFFECTIVENESS_EVALUATION = CLOSED_ENGINEERING_ONLY
primary_metric = ENGINEERING_CONTRACT_EXACTNESS
promotion_boundary = CLOSED_NO_DAILY_SCOPE_NO_REAL_OOS
```

上一轮 `AUDIT_NOTE_E4_01` 在 E5 工程协议层已得到正确处理。

---

# 3. Model Evidence Class｜PASS

E2：

```text
CONDITIONAL_STATISTICS_BASELINE
ACCEPTED_BASELINE_ENGINEERING
PRIMARY_E5_ENGINEERING_SOURCE
production_role = NONE
```

E3：

```text
INTERPRETABLE_MODEL
ACCEPTED_MODEL_ENGINEERING_NO_INCREMENT
DIAGNOSTIC_SHADOW_ONLY
```

E4：

```text
TREE_CHALLENGER
ACCEPTED_CHALLENGER_ENGINEERING_MIXED_NO_INCREMENT_VS_E2
DIAGNOSTIC_SHADOW_ONLY
```

并保持：

```text
CHAMPION = NONE
```

没有复杂模型自动晋级。

---

# 4. 上游 Artifact 与历史 Projection｜PASS_ENGINEERING

本轮：

```text
new_model_training = 0
new_hyperparameter_search = 0
new_label_resolution = 0
new_E4_trial = 0
```

E2 使用 accepted L1 statistics，不重建、不拟合。

E3 serialized artifact 回读：

```text
point max abs delta = 2.42861286636753e-17
quantile max abs delta = 6.938893903907228e-18
```

E4 serialized artifact 回读：

```text
point delta = 0
quantile delta = 0
```

Historical ENTRY batch：

```text
205 observations
× 3 model families
= 615 projections

prediction_slots = 616
slot_model_bindings = 615
```

每 family：

```text
READY = 46
REJECTED_QUALITY = 159
```

并明确：

```text
historical_full_population_claim = false
prediction_evidence = HISTORICAL_SIMULATION
FIRST_OBSERVED = false
REAL_OOS = false
thresholds = NOT_FROZEN
```

因此历史投影工程本身通过，但只是历史工程原型。

---

# 5. ENTRY / DAILY 与 Priority Shadow｜PASS

代码强制：

```text
FIRST_PREWATCH != DAILY_LANDMARK
```

真实 Daily 未建立时：

```text
FEP_STOCK_DAILY_CORE = NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE
REAL_PRIORITY_SHADOW = NOT_GRANTED
v2_active = false
coverage = 0
```

Synthetic Priority fixture：

```text
7 rows
6 eligible
3 covered
1 OOD reject
1 missing prediction
1 missing model
```

完整 denominator、V1 rank、eligibility、risk events 均保留。

只允许在 synthetic fixture 中、同一 V1 layer 内测试 FEP tie-break，默认关闭，真实关闭。

因此：

```text
ENTRY_DAILY_SEPARATION = PASS
PRIORITY_V2_SHADOW_ENGINE = PASS_ENGINEERING_FIXTURE
PRIORITY_V1_MUTATION = NOT_FOUND
```

---

# 6. 权限 / API / Rollback 原型｜PASS_IN_ISOLATED_NAMESPACE

隔离工程 ledger 中只允许：

```text
SHADOW_INFERENCE
```

并保持：

```text
DESCRIPTIVE_DISPLAY = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
FEP_PRODUCTION = UNGRANTED
```

默认 API 不返回 model axes；仅 diagnostic + exact shadow permission 才返回诊断轴。

Rollback 后：

```text
prediction history digest unchanged
PRIORITY_V1 digest unchanged
Core unaffected
permission revoked
```

所以独立工程原型本身通过。

---

# 7. Blocker E5-B01｜Canonical FEP Ledger 未接入

E1 已正式建立：

```text
fep.prediction_slots
fep.slot_model_bindings
fep.prediction_runs
fep.predictions
fep.slot_receipts
fep.acceptance_receipts
fep.permission_keys
fep.activations
fep.deployment_heads
fep.deployment_change_receipts
fep.priority_projection
```

对应正式 migration：

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

但 E5 没有使用这些正式表，而是新建：

```text
fep_e5_engineering.*
```

`src/workbench_analysis/fep_e5/schema.sql` 第一行直接声明：

```text
Explicit isolated engineering namespace, not production migration.
```

`ledger.py` 又固定：

```text
SCHEMA = 'fep_e5_engineering'
```

`FINAL_EXIT_READBACK.json` 证明正式 E1 `fep.*` 33 张表在 fresh / upgrade database 中仍全部为 0 行，而全部 E5 ledger 数据都在 `fep_e5_engineering.*`。

任务卡明确要求：

```text
必须创建/使用正式 projection ledger
```

因此：

```text
E5-B01 CANONICAL_FEP_LEDGER_INTEGRATION = FAIL
```

工程隔离允许使用 disposable PostgreSQL，但不能另定义一套平行关系合同来替代已经验收的 E1 schema。

---

# 8. Blocker E5-B02｜Canonical Observation / Snapshot / Publication Chain 缺失

正式 E1 链：

```text
prediction
→ slot
→ observation
→ snapshot
→ observation_revision
→ v4.publications
```

E5 实际从：

```text
reports/fep_e3_r1/EXACT_MODEL_ROWS.jsonl.gz
```

重新生成：

```text
FEP_E5_EMBEDDED_SNAPSHOT:<digest>
```

Readback 明确承认这是：

```text
independent engineering ledger identity
not a fabricated Core snapshot primary key
```

同时 E5 `publication_id` 实际使用：

```text
original E2 observation-row digest
```

并明确：

```text
not a v4.publications primary key
```

这虽然保持了历史 artifact byte lineage，但没有证明正式：

```text
fep.observations
fep.observation_revisions
fep.snapshots
v4.publications
```

之间的 canonical FK / trigger 链。

任务卡要求旧 projection exact-bind：

```text
existing immutable snapshot
existing accepted observation
existing model/dataset artifact
```

当前实际是“从 accepted artifact 派生新的 E5 engineering snapshot identity”。

所以：

```text
E5-B02 CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING = FAIL
```

---

# 9. Blocker E5-B03｜Formal Permission / Deployment Contract 未验证

正式 E1 permission/deployment 链：

```text
fep.permission_keys
fep.activations
fep.deployment_heads
fep.deployment_change_receipts
fep.cas_deploy(...)
```

E5 没有走这条链，而是在：

```text
fep_e5_engineering.permission_keys
fep_e5_engineering.activations
fep_e5_engineering.deployment_heads
```

做了一套 code-level exact key + isolated CAS。

其 Python 校验本身较严格，但：

```text
Python isolated contract
!=
E1 canonical DB contract
```

更重要的是，正式 E1 `fep.permission_keys` 当前还有：

```text
model_role = CHAMPION
```

约束，而 E5 当前正确状态是：

```text
CHAMPION = NONE
```

因此正式 schema 与“非 Champion diagnostic SHADOW inference”的接口是否可直接表示，本身就是需要显式解决的 contract integration 问题。

正确处理应是：

```text
若 formal schema 无法表达
→ CONTRACT_CONFLICT
→ narrow contract/schema repair
```

而不是另起一套 parallel schema 绕开它。

所以：

```text
E5-B03 CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION = FAIL
```

---

# 10. 三个 Blocker 的共同根因

三项不是三个大改，根因只有一个：

```text
E5 没有真正接入 E1 canonical fep.* contract
```

因此下一轮必须是：

```text
V4-15E5 R1R1
Canonical FEP Integration Repair
```

而不是重做 E2/E3/E4、Priority 算法或历史 inference。

---

# 11. Negative / Regression｜PASS

Negative matrix：

```text
50 / 50 PASS
```

覆盖任务卡要求的 E5-01～E5-30，包括：

```text
ENTRY→DAILY
T1→T5
target/feature错绑
current-head rebuild
seen Outer promotion
E2/E4 Champion
MODEL_DISPLAY
PRIORITY_USE
old ENTRY as today
V1 rank/eligibility mutation
risk hiding
denominator drop
missing model slot deletion
result-driven rebind
post-result tuple/disposition
Core feedback
cross-target permission
synthetic REAL_OOS
reconstructed FIRST_OBSERVED
history deletion
partial activation
JOINT_OOD UNSET→PASS
real Daily active
V1 digest mutation
new training
label recomputation
```

Targeted：

```text
306 passed
1 skipped
0 failed
```

Scoped：

```text
2665 passed
4 skipped
52 failed
0 introduced active failures
```

52 个 failure 与上游 known debt 一致。

仓库仍不是全绿：

```text
repository_all_green = false
```

---

# 12. GitHub CI｜NO RUN / NO STATUS

仓库自己的 `GITHUB_CI_READBACK.json` 检查的是 base commit `adcfa364...`，不是 E5 implementation commit，这是一个非阻断治理缺口。

本次独立审计已直接检查：

```text
51a1aab3fc9fe5bb390ec768dfd9514a1db6af54
```

实际：

```text
workflow_runs = []
combined statuses = []
```

因此：

```text
GITHUB_CI = NO_RUN / NO_STATUS
```

审计备注：

```text
AUDIT_NOTE_E5_01 =
NONBLOCKING_CI_READBACK_TARGETED_BASE_INSTEAD_OF_IMPLEMENTATION_HEAD
```

---

# 13. Protected State｜PASS

没有修改：

```text
PRIORITY_V1 owner files
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16_ACCEPTED_HEAD
Core/Profile/State/Radar/Cohort
```

当前：

```text
Stage = V4_00_TO_V4_15_ACCEPTED
Data = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
TDX = UNTOUCHED
```

因此：

```text
PROTECTED_STATE = PASS
```

---

# 14. 下一轮只修三项

## R1R1-A Canonical FEP Ledger

将 prediction slot / model binding / run / prediction / receipt / priority projection 接入正式 `fep.*`。

若正式 schema 无法表达 E5 engineering-only semantics：

```text
必须显式登记 CONTRACT_CONFLICT
```

不得再建立第三套 parallel schema。

## R1R1-B Canonical Identity Adapter

建立合法的：

```text
historical observation
→ formal observation/revision
→ formal snapshot
→ formal target/model
→ formal prediction slot
```

可以保持：

```text
RECONSTRUCTED_CORRECTED
HISTORICAL_SIMULATION
FIRST_OBSERVED = false
```

但最终 identity 必须落到 canonical FEP contract。

## R1R1-C Canonical Permission / Deployment

验证正式：

```text
fep.permission_keys
fep.activations
fep.deployment_heads
fep.deployment_change_receipts
fep.cas_deploy
```

如果 `CHAMPION-only` 与 diagnostic SHADOW 发生合同冲突，先修合同，不得伪造 Champion，不得放开 MODEL_DISPLAY / PRIORITY_USE。

---

# 15. 可直接继承，不得重做

下一轮直接保留：

```text
Protocol Freeze
Model Evidence Class
Serialized Inference Adapter
ENTRY/DAILY Isolation
Priority V2 Same-layer Shadow Logic
Denominator/Abstention Handling
Risk-event Preservation
API No-overdisplay Rules
Rollback Semantics
50-case Negative Matrix
Targeted Regression
Scoped Regression Baseline
```

---

# 16. 修复后仍不得升级的权限

即使 R1R1 修完，仍然必须保持：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
PRIORITY_USE = UNGRANTED
MODEL_DISPLAY = UNGRANTED
CHAMPION = false
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

R1R1 只解决 canonical engineering integration，不解决模型有效性、真实 Daily OOS 或生产排序授权。

---

# 17. 最终验收矩阵

| Gate | Result |
|---|---|
| Drive authority sync | PASS |
| Git baseline / parent | PASS |
| Pre-run protocol freeze | PASS |
| E2/E3/E4 evidence class | PASS |
| No retraining / no relabel | PASS |
| Historical serialized inference | PASS |
| ENTRY / DAILY separation | PASS |
| Real Daily fail-closed | PASS |
| Priority V2 fixture | PASS |
| PRIORITY_V1 protection | PASS |
| Risk preservation | PASS |
| OOD UNSET preservation | PASS |
| Negative matrix | PASS 50/50 |
| Targeted | PASS 306/1 |
| Scoped introduced failures | 0 |
| Known debt | 52 |
| GitHub CI | NO RUN / NO STATUS |
| Protected state | PASS |
| Canonical `fep.*` projection ledger | **FAIL** |
| Canonical observation/snapshot/publication chain | **FAIL** |
| Canonical permission/deployment/CAS chain | **FAIL** |
| Real Daily Priority | NOT_GRANTED |
| Production | UNGRANTED |

---

# 18. 唯一最终状态

```text
V4_15E5_FINAL_EXTERNAL_AUDIT =
BLOCKED_R1_CANONICAL_FEP_INTEGRATION

ACCEPTED_SUBCAPABILITIES =
PROTOCOL_FREEZE
MODEL_EVIDENCE_CLASS
HISTORICAL_INFERENCE_ADAPTER
ENTRY_DAILY_ISOLATION
PRIORITY_V2_SHADOW_ENGINE
NEGATIVE_MATRIX
REGRESSION_NO_NEW_FAILURE
PROTECTED_STATE

BLOCKERS =
E5-B01 CANONICAL_FEP_LEDGER_INTEGRATION
E5-B02 CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING
E5-B03 CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION

NEXT =
ISSUE_V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR
```

E5 当前不能正式收尾，但下一轮只需要定点 integration repair，不应推翻已通过部分重做。

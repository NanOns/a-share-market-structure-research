# V4-15E5｜FEP Projection / Expectancy-aware Priority Shadow Engineering Task R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5  
> 任务性质：正式工程实施任务卡 / FEP Level 4  
> 执行分支：`codex/v4-system-reform`  
> 执行基线：`adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb`  
> 当前上游：E4 `FORMALLY_CLOSED`  
> 目标最高状态：`FEP_E5_ENGINEERING_PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT`  
> Production / Priority / Model Display 权限：全部保持 `UNGRANTED`

---

# 0. 唯一任务

本轮只执行：

```text
V4-15E5
FEP Projection / Expectancy-aware Priority Shadow Engineering
```

目标不是把模型“接进正式排序”，而是把已经完成的：

```text
E1 Dataset / PostgreSQL Foundation
→ E2 Conditional Statistics Baseline
→ E3 Interpretable Model
→ E4 Optional Tree Challenger
```

推进到：

```text
immutable prediction slot
+
model/evidence binding
+
projection ledger
+
API/readback
+
Priority Shadow projection engine
+
rollback / permission / no-feedback governance
+
future OOS promotion protocol boundary
```

本轮必须完成工程能力，但不得把工程完成包装成模型有效、Priority 有效或 Production 通过。

---

# 1. 当前正式上游状态

当前正式执行基线：

```text
adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb
```

该 HEAD 已完成并归档：

```text
E4 reconciliation final audit
E4 = FORMALLY_CLOSED
E5_ENTRY = AUTHORIZED
```

当前必须继承：

```text
CHALLENGER_EFFECTIVENESS = MIXED
PRIMARY_EFFECTIVENESS_VS_E2 = NO_INCREMENT
DIAGNOSTIC_EFFECTIVENESS_VS_E3 = IMPROVED

E3_MODEL_EFFECTIVENESS = NO_INCREMENT

SEEN_OUTER_DIAGNOSTIC_ONLY = true
NEW_INDEPENDENT_OOS_EVIDENCE = false
CHAMPION = false
PROMOTION_EVIDENCE = false

REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED
```

当前 E4 已封存，禁止回写 E4 protocol、trial、model selection、Outer evaluation 或 disposition。

---

# 2. 正式设计权威

本轮必须绑定：

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
```

正式主合同 SHA256：

```text
203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205
```

FEP R2：

```text
DA-MSR-V4.2.2-FEP-R2
```

设计 SHA256：

```text
f01ac9c550a71b8edb73436969e39172f6809404df9e19ffbfff2306c9456014
```

R2 外部设计验收：

```text
EXTERNAL_DESIGN_ACCEPTANCE_PASS
```

E5 适用核心条款：

```text
§60 PRIORITY_V1
§90 FEP.2
§90 FEP.3
§90 FEP.9
§90 FEP.10
§90 FEP.11
§90 FEP.12
§90 FEP.13
§90 FEP.14
§90 FEP.16
```

如早期 R0/R1 与 R2 冲突：

```text
R2 优先
```

---

# 3. E5 的能力拆分

本轮必须明确拆成两个 capability lane。

## Lane A｜真实 ENTRY Projection Engineering

当前已具备的正式 FEP 能力人口：

```text
scope_id = FEP_STOCK_ENTRY_CORE
observation_scope = FIRST_PREWATCH
target = ABS_RETURN_N
horizon = T1
feature_variant = CORE
evidence_origin = RECONSTRUCTED_CORRECTED
```

E5 允许在这条 exact scope 上实现：

```text
planned prediction slot
model/evidence binding
prediction run
prediction result
quality state
projection ledger
API/readback
historical/as-of annotation
diagnostic comparison
```

但：

```text
RECONSTRUCTED_CORRECTED
!=
PIT_OBSERVED

ENTRY
!=
DAILY_LANDMARK

historical projection
!=
today full-Radar prediction
```

因此 Lane A 不能直接获得：

```text
FIRST_OBSERVED
REAL_OOS
MODEL_DISPLAY
PRIORITY_USE
FEP_PRODUCTION
```

## Lane B｜Daily Priority Shadow Engine

必须实现：

```text
PRIORITY_V1 complete candidate set
+
eligible DAILY_LANDMARK / candidate-day FEP evidence
→ separate PRIORITY_V2 shadow projection
```

但当前真实 Daily FEP scope 尚未建立。

所以本轮 Lane B：

```text
ENGINEERING_IMPLEMENTED
+
SYNTHETIC / FIXTURE VERIFIED
+
REAL DAILY ACTIVATION = NOT_ENABLED
```

必须明确：

```text
NO DAILY_LANDMARK MODEL
→ NO TODAY PRIORITY SHADOW ON REAL CANDIDATES

NO REAL DAILY OOS
→ NO PRIORITY_USE
```

不得拿 ENTRY 预测长期挂在 persistent candidate 上冒充“今日预测”。

---

# 4. E2 / E3 / E4 模型证据等级

本轮必须创建机器可读 evidence class registry。

至少包含：

## E2

```text
model_family = CONDITIONAL_STATISTICS_BASELINE
evidence_class = ACCEPTED_BASELINE_ENGINEERING
priority_role = PRIMARY_E5_ENGINEERING_SOURCE
production_role = NONE
```

E2 是当前最简单且主指标优于 E3/E4 的 baseline。

## E3

```text
model_family = INTERPRETABLE_MODEL
evidence_class = ACCEPTED_MODEL_ENGINEERING_NO_INCREMENT
priority_role = DIAGNOSTIC_SHADOW_ONLY
production_role = NONE
```

## E4

```text
model_family = TREE_CHALLENGER
evidence_class = ACCEPTED_CHALLENGER_ENGINEERING_MIXED_NO_INCREMENT_VS_E2
priority_role = DIAGNOSTIC_SHADOW_ONLY
production_role = NONE
```

严禁：

```text
模型越复杂
→ 自动优先

E4 比 E3 好
→ 自动成为 champion

tree challenger
→ 自动覆盖 baseline
```

当前：

```text
CHAMPION = NONE
```

除非未来新的独立 OOS promotion protocol 正式授予。

---

# 5. E4 审计备注的强制升级

上一轮：

```text
AUDIT_NOTE_E4_01
=
OPEN_FOR_NEXT_EFFECTIVENESS_PROTOCOL
```

本轮开始前必须建立：

```text
config/fep_e5_projection_priority_protocol_v1.json
```

并在任何 projection effectiveness / priority effectiveness evaluation 打开前冻结。

必须含：

```text
effectiveness_disposition_rule
primary_metric
tie_break
promotion_boundary
priority_projection_boundary
shadow_only_boundary
model_evidence_class
```

本轮不得留成自由文本。

---

# 6. 本轮预注册 disposition

由于当前：

```text
no DAILY_LANDMARK real scope
no new independent OOS
no FIRST_OBSERVED
```

本轮不得打开生产效果 promotion evaluation。

正式冻结：

```text
E5_EFFECTIVENESS_EVALUATION =
CLOSED_ENGINEERING_ONLY
```

正式 disposition rule：

```text
if engineering contract violation:
    BLOCKED

elif protected state / PRIORITY_V1 mutation:
    BLOCKED

elif ENTRY projection identity/ledger/API/rollback incomplete:
    BLOCKED

elif Daily Priority engine cannot fail-closed without DAILY scope:
    BLOCKED

else:
    PASS_ENGINEERING_ONLY_NO_PROMOTION
```

不得存在：

```text
PASS_INCREMENT
CHAMPION
PRIORITY_USE
```

的本轮自动路径。

---

# 7. Primary Metric / Tie-break / Promotion Boundary Freeze

为了关闭 E4 governance note，本轮必须显式冻结：

```text
primary_metric =
ENGINEERING_CONTRACT_EXACTNESS
```

工程 primary gate 由以下全部成立组成：

```text
exact prediction-slot identity
exact model/evidence binding
exact same-scope target/horizon/feature identity
deterministic logical digest
no current-head rebuild
no future label read
no ENTRY→DAILY semantic reuse
no PRIORITY_V1 mutation
rollback exactness
permission fail-closed
API/readback exactness
```

tie-break：

```text
NOT_APPLICABLE_ENGINEERING_GATE
```

production promotion boundary：

```text
CLOSED_NO_DAILY_SCOPE_NO_REAL_OOS
```

future effectiveness protocol：

```text
REQUIRES_SEPARATE_PRE_REGISTERED_OOS_PROTOCOL
```

这不是把真实效果 metric 永久定义为工程一致性；
而是明确：

> 本轮根本不打开效果晋级。

---

# 8. Future Priority Effectiveness Protocol Stub

E5 必须同时生成一个：

```text
FUTURE_PRIORITY_OOS_PROTOCOL_STUB.json
```

状态：

```text
NOT_ACTIVE
NOT_EVALUATED
```

至少登记未来必须冻结的维度：

```text
scope_id
candidate-day observation scope
target
horizon
feature_contract
model_set
K
coverage floor
primary return metric
risk metric
rejection / abstention metric
missingness metric
block length
minimum OOS signal dates
minimum OOS episodes/entities
promotion margin
risk non-inferiority boundary
```

本轮这些数值可以：

```text
UNSET
```

但必须：

```text
UNSET => cannot activate evaluation
```

不得为了“跑出结论”临时填值。

---

# 9. Prediction Slot 合同

必须实现或补全：

```text
prediction_slots
slot_model_bindings
prediction_runs
predictions
slot_receipts
acceptance_receipts
```

每个 prediction slot identity 至少包含：

```text
namespace
scope_id
entity_id
observation_scope
signal_key
trade_date
target_id
horizon
feature_contract_id
model_family_scope
model_selection_cutoff
prediction_deadline
```

必须保证：

```text
slot exists
even if no model is available
```

无模型：

```text
NO_ACTIVE_MODEL
```

必须留下 receipt，不能把 slot 删除。

---

# 10. Model Selection 必须冻结在 Prediction 之前

必须满足：

```text
activation_effective_at
<= model_selection_cutoff
<= prediction_started_at
```

并且：

```text
prediction result
不能反向决定 model_set
```

必须测试：

```text
two available model sets
one later performs better
→ cannot replace frozen binding
```

---

# 11. E2 Baseline Binding

Lane A 实际工程运行必须首先绑定 E2 baseline。

必须 exact-bind：

```text
E2 accepted artifact
E2 contract
E2 dataset identity
E2 support/backoff policy
E2 feature contract
E2 target/horizon
E2 evidence class
```

禁止：

```text
重新计算 E2 historical population
重做 labels
重新选 backoff policy
用 current head 重建过去 T0
```

如果 E2 artifact 当前无法直接 portable inference：

```text
不得静默重新训练
```

必须：

```text
BLOCK affected lane
or
新增 exact serialization/readback repair
```

并记录独立证据。

---

# 12. E3 / E4 Diagnostic Binding

E3/E4 允许作为：

```text
DIAGNOSTIC_SHADOW_ONLY
```

必须 separate namespace。

禁止：

```text
E3/E4 output
→ user model display
→ priority tuple
→ production API default response
```

API 如暴露诊断：

```text
diagnostic = true
permission = SHADOW_INFERENCE_ONLY
evidence_class = ...
```

必须显式。

---

# 13. Projection Ledger

必须创建/使用正式 projection ledger。

每条 projection 至少保存：

```text
prediction_slot_id
observation_id
feature_snapshot_id
model_set_id
model_id/model_family
evidence_class
target_id
horizon
feature_contract_id
input_digest
prediction_digest
quality_state
support_state
OOD_state
coherence_state
created_at
accepted_at
execution_mode
prediction_evidence
```

对于 E2 conditional statistics：

```text
model_id 可为 baseline artifact identity
```

不能因为“不是 ML 模型”而跳过 registry / identity。

---

# 14. Projection State

本轮必须统一 fail-closed 状态。

至少：

```text
READY
UNKNOWN
NOT_ENABLED
NOT_APPLICABLE
REJECTED_OOD
REJECTED_QUALITY
REJECTED_SUPPORT
CONFLICTING
MISSING_MODEL
MISSED_SLOT
```

不得：

```text
None
→ 当作 0
→ 当作 NEUTRAL
```

---

# 15. FEP State 规则

按照 R2：

```text
required quality/support/calibration/OOD/coherence not satisfied
→ UNKNOWN

positive expectancy + excessive risk
→ CONFLICTING

pre-registered positive statistic above positive gate
and risk acceptable
→ POSITIVE

below negative gate
→ NEGATIVE

otherwise
→ NEUTRAL
```

但当前真实 ENTRY E2 scope 如果对应 threshold 未正式冻结：

```text
state = NOT_FROZEN
```

允许展示原始轴值和支持信息，
不允许事后看结果再选：

```text
mean
median
p50
lower bound
```

---

# 16. Priority Projection Engine

必须实现独立：

```text
PRIORITY_V2_SHADOW
```

输入必须是：

```text
PRIORITY_V1 complete eligible candidate ledger
+
same-day eligible FEP evidence
```

输出是：

```text
shadow projection
```

禁止修改：

```text
eligibility
priority_rank V1
display_rank V1
PREWATCH status
CONFIRMED status
State
Radar candidate set
Validation Cohort
Focus
```

---

# 17. PRIORITY_V2 排序边界

R2 明确：

```text
PRIORITY_V1 bucket 保留
emergence / structure / risk 的关键次序保留
FEP 只允许在预注册同层 tie-break 进入
```

因此本轮 engine 必须支持但默认关闭：

```text
V1 same-layer tie-break + FEP tuple
```

不得建立：

```text
opaque total score
```

禁止：

```text
trend + RPS + FEP + risk
→ 统一神秘分数
```

FEP 保留独立轴：

```text
return_expectancy
relative_expectancy
risk_expectancy
structure_expectancy
confidence/support
OOD
```

---

# 18. Risk / Invalidation 不得被隐藏

任何 Priority shadow 都不得：

```text
因为 expectancy positive
→ 隐藏 invalidation
→ 隐藏 risk change
→ 隐藏 high extension
```

必须验证：

```text
high-risk invalidated candidate
即使 expectancy axis positive
仍保留风险事件和原 V1 风险排序语义
```

---

# 19. ENTRY 与 DAILY 的硬隔离

这是本轮 P0。

必须有机器 guard：

```text
ENTRY observation scope
cannot satisfy
DAILY_LANDMARK requirement
```

测试：

```text
FIRST_PREWATCH on T0
candidate persists T+1/T+2/T+3
```

旧 ENTRY projection：

```text
只允许 historical/as-of annotation
```

不得：

```text
挂在 T+1/T+2/T+3 今日 Radar
```

要进入今日 Priority shadow，必须存在：

```text
same-day DAILY_LANDMARK
same-day feature snapshot
same-day prediction slot
same-day accepted prediction
```

---

# 20. 当前真实 Daily Priority 状态

本轮完成后必须真实写：

```text
FEP_STOCK_DAILY_CORE =
NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE

REAL_PRIORITY_SHADOW =
NOT_GRANTED

PRIORITY_USE =
UNGRANTED
```

不得用 synthetic fixture 改成：

```text
READY
```

---

# 21. Synthetic Daily Fixture

为了不让真实样本等待阻塞工程开发，
允许构造 synthetic fixture 验证：

```text
same-day candidate set
DAILY_LANDMARK
same-day FEP axis
same K
same coverage
PRIORITY_V1
PRIORITY_V2 shadow
risk event preservation
rollback
```

但 fixture 必须：

```text
ENGINEERING_FIXTURE
synthetic_only = true
```

严禁成为：

```text
REAL_OOS
FIRST_OBSERVED
PRIORITY_EFFECTIVENESS
```

---

# 22. Permission Key

继续使用 R2 grant identity：

```text
(scope_id,
 target_id,
 horizon,
 feature_contract_id,
 model_set_id,
 capability)
```

capability 至少：

```text
SHADOW_INFERENCE
DESCRIPTIVE_DISPLAY
MODEL_DISPLAY
PRIORITY_USE
```

本轮真实可授予的最高工程权限：

```text
SHADOW_INFERENCE
```

但仅表示：

```text
engine may calculate/store diagnostic result
```

不等于：

```text
production display
priority use
```

---

# 23. CHAMPION 限制

当前没有 Champion。

本轮必须 fail-closed：

```text
MODEL_DISPLAY requires CHAMPION + exact permission
PRIORITY_USE requires CHAMPION + exact permission
```

E2 虽然是当前最佳 baseline：

```text
PRIMARY_E5_ENGINEERING_SOURCE
```

但仍不是：

```text
CHAMPION
```

E3/E4 更不是。

---

# 24. API

至少提供或补全：

```text
FEP projection readback API
FEP diagnostic projection API
Priority shadow readback API
permission/evidence state
```

建议 response 至少包含：

```text
scope_id
observation_scope
trade_date
entity_id
target
horizon
feature_variant

projection_state
axes
support_state
quality_state
OOD_state
coherence_state

model/evidence identity
prediction slot identity
prediction evidence
execution mode

permission:
  shadow_inference
  descriptive_display
  model_display
  priority_use

priority:
  v1_rank
  v2_shadow_rank
  v2_active = false
```

---

# 25. API 禁止过度展示

当前真实响应不得写：

```text
“预测上涨概率”
“模型推荐”
“Priority V2 已启用”
```

若返回 diagnostic raw values：

```text
必须带 evidence_class / permission / reconstructed status
```

---

# 26. Prediction Revision / Append-only

历史 prediction 必须 append-only。

新 source/model revision：

```text
不得 UPDATE 原 prediction
```

允许：

```text
new revision
supersedes
corrected view
```

但 original slot 首个合规 accepted prediction 保留。

---

# 27. FIRST_OBSERVED Boundary

当前历史 reconstruction 必须：

```text
prediction_evidence =
HISTORICAL_SIMULATION / RECONSTRUCTED_*
```

不得：

```text
FIRST_OBSERVED = true
```

只有未来实时 slot：

```text
在 deadline 前
由当时 active model
使用当时可见 feature
首次 accepted
```

才有资格创建 FIRST_OBSERVED。

---

# 28. No Current-Head Rebuild

E5 必须禁止：

```text
读取 latest/current profile
去重算旧 observation feature
```

旧 projection 必须 exact-bind：

```text
existing immutable snapshot
existing model/dataset artifact
existing accepted observation
```

缺失：

```text
MISSING_DEPENDENCY
```

不能 current-head backfill 冒充旧事实。

---

# 29. OOD / Support / Calibration

必须继承各上游 artifact 的状态。

E2：

```text
support/backoff
```

E3/E4：

```text
OOD/calibration/coherence
```

不能 E5 自己重新解释：

```text
E4 JOINT_OOD = UNSET
```

必须继续显示 UNSET。

不能 E5 因要展示：

```text
→ 自动把 UNSET 当 PASS
```

---

# 30. Same-Scope Identity

必须严格校验：

```text
scope
observation_scope
target
horizon
feature_contract
model namespace
```

故意串：

```text
T1 model → T5 slot
ENTRY model → DAILY slot
CORE model → SUPPLEMENTAL slot
ABS_RETURN model → MARKET_EXCESS slot
```

全部拒绝。

---

# 31. Priority Shadow Coverage

未来真实 Daily Priority evaluation 必须：

```text
same day
same candidate set
same K
same coverage policy
same observable labels
```

本轮 engine 必须能记录：

```text
eligible_candidates
covered_candidates
rejected_OOD
missing_prediction
missing_model
missing_daily_observation
coverage_ratio
```

不得：

```text
只比较被模型覆盖的漂亮子集
```

---

# 32. Rejection / Abstention

OOD / quality / support 不足：

```text
必须保留 row
```

不得 complete-case 删除。

Priority shadow 应记录：

```text
ABSTAIN / REJECTED
```

并继续保留原：

```text
PRIORITY_V1
```

---

# 33. Rollback

必须支持独立 FEP rollback。

rollback 只影响：

```text
FEP activation
FEP priority projection activation
FEP API active pointer
```

不能影响：

```text
Core
PREWATCH
State
Radar
Validation
Focus
PRIORITY_V1
```

rollback 后：

```text
历史 prediction / receipts / failed experiments 保留
```

---

# 34. Failure Atomicity

构造故障：

```text
prediction persisted
priority projection fails
```

或：

```text
activation receipt created
head update fails
```

必须证明：

```text
no half-activated Priority V2
no partial permission grant
```

---

# 35. Protected State

本轮禁止修改：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16_ACCEPTED_HEAD
PRIORITY_V1 algorithm/parameter contract
Core publication
Validation Cohort
Focus
```

如需增加 FEP 独立 head：

```text
必须新 namespace
```

不能覆盖全局 accepted head。

---

# 36. TDX / BaoStock

E5 不应需要重新采集。

要求：

```text
TDX = READ_ONLY / preferably UNTOUCHED
BaoStock = NOT_REQUIRED
```

禁止为了 Priority projection：

```text
重新下载历史行情
重新构建 V4 Core
重新结算 labels
```

---

# 37. 资源预算

E5 是投影层，不允许无界训练。

正式要求：

```text
new model training = 0
new hyperparameter tuning = 0
new E4 trial = 0
```

若发现现有 artifact 无法消费：

```text
先 BLOCK
```

不得借 E5 重训。

允许：

```text
bounded projection inference
bounded fixture
bounded API/readback
```

---

# 38. 可恢复性

每个执行阶段必须有 checkpoint：

```text
protocol freeze
input binding
slot creation
model binding
prediction run
projection ledger
priority shadow fixture
permission test
rollback test
regression
seal
```

重复执行：

```text
same semantic input
→ same logical digest
```

---

# 39. 必须产生的配置/证据

至少：

```text
config/fep_e5_projection_priority_protocol_v1.json
config/fep_e5_model_evidence_class_v1.json

reports/fep_e5_r1/ENTRY_BASELINE.json
reports/fep_e5_r1/UPSTREAM_BINDINGS.json
reports/fep_e5_r1/PROTOCOL_FREEZE.json
reports/fep_e5_r1/MODEL_EVIDENCE_CLASS.json
reports/fep_e5_r1/PREDICTION_SLOT_LEDGER.json
reports/fep_e5_r1/PREDICTION_BINDING_READBACK.json
reports/fep_e5_r1/ENTRY_PROJECTION_READBACK.json
reports/fep_e5_r1/DAILY_PRIORITY_CAPABILITY_READBACK.json
reports/fep_e5_r1/PRIORITY_V1_PROTECTED_READBACK.json
reports/fep_e5_r1/PERMISSION_MATRIX.json
reports/fep_e5_r1/ROLLBACK_DRILL.json
reports/fep_e5_r1/NEGATIVE_MATRIX.json
reports/fep_e5_r1/TARGETED_SUMMARY.json
reports/fep_e5_r1/SCOPED_REGRESSION_SUMMARY.json
reports/fep_e5_r1/INDEPENDENT_AUDIT_ITEMS.json
reports/fep_e5_r1/FINAL_EXIT_READBACK.json
reports/fep_e5_r1/FEP_E5_R1_CANDIDATE_SEAL.json
reports/fep_e5_r1/COMPLETION_REPORT.md
```

文件名可按仓库规范调整，但语义证据不能缺。

---

# 40. Future OOS Protocol 必须单独保存

必须有：

```text
reports/fep_e5_r1/FUTURE_PRIORITY_OOS_PROTOCOL_STUB.json
```

内容明确：

```text
status = NOT_ACTIVE
evaluation_open = false
```

任何未冻结项：

```text
UNSET
```

必须 fail-closed。

---

# 41. Negative Matrix｜最低要求

至少执行以下反例：

## E5-01
```text
ENTRY model bound to DAILY slot
→ REJECT
```

## E5-02
```text
T1 model bound to T5 slot
→ REJECT
```

## E5-03
```text
ABS_RETURN model bound to MARKET_EXCESS slot
→ REJECT
```

## E5-04
```text
CORE model bound to SUPPLEMENTAL feature contract
→ REJECT
```

## E5-05
```text
current-head feature rebuild for old observation
→ REJECT
```

## E5-06
```text
seen Outer result used as promotion evidence
→ REJECT
```

## E5-07
```text
E4 marked CHAMPION
→ REJECT
```

## E5-08
```text
E2 baseline marked CHAMPION without new OOS
→ REJECT
```

## E5-09
```text
MODEL_DISPLAY grant without champion/exact permission
→ REJECT
```

## E5-10
```text
PRIORITY_USE grant without DAILY scope
→ REJECT
```

## E5-11
```text
old ENTRY forecast shown as today's persistent-candidate forecast
→ REJECT
```

## E5-12
```text
Priority V2 mutates PRIORITY_V1 rank
→ REJECT
```

## E5-13
```text
Priority V2 changes PREWATCH eligibility
→ REJECT
```

## E5-14
```text
positive expectancy hides invalidation/risk event
→ REJECT
```

## E5-15
```text
OOD rejected rows dropped from denominator
→ REJECT
```

## E5-16
```text
missing model slot silently omitted
→ REJECT
```

## E5-17
```text
prediction result used to choose model binding
→ REJECT
```

## E5-18
```text
post-result change to priority tuple
→ REJECT
```

## E5-19
```text
post-result change to effectiveness disposition
→ REJECT
```

## E5-20
```text
priority projection writes Core/Profile/State/Cohort
→ REJECT
```

## E5-21
```text
permission for one target/horizon reused by another
→ REJECT
```

## E5-22
```text
synthetic fixture marked REAL_OOS
→ REJECT
```

## E5-23
```text
RECONSTRUCTED_CORRECTED marked FIRST_OBSERVED
→ REJECT
```

## E5-24
```text
rollback deletes historical failed prediction
→ REJECT
```

## E5-25
```text
partial activation after transaction failure
→ REJECT
```

## E5-26
```text
E4 JOINT_OOD UNSET treated as PASS
→ REJECT
```

## E5-27
```text
no DAILY model but Priority API says active
→ REJECT
```

## E5-28
```text
PRIORITY_V1 source/parameter digest changes
→ REJECT
```

## E5-29
```text
new model training detected
→ BLOCK
```

## E5-30
```text
new label resolution / settlement recomputation detected
→ BLOCK
```

---

# 42. Targeted Tests

至少覆盖：

```text
prediction slot identity
model binding
projection persistence
append-only
permission matrix
ENTRY/DAILY separation
priority shadow fixture
risk-event preservation
API permission readback
rollback
logical digest determinism
```

必须：

```text
0 introduced active failures
```

---

# 43. Scoped Regression

使用当前 E4 closure baseline 的 scoped regression identity。

如果仍存在上游已知 debt：

```text
必须逐 node 比较
```

不能写：

```text
52 failures are historical
```

却不核对 exact identities。

要求：

```text
introduced_active_failures = 0
```

仓库若非全绿：

```text
repository_all_green = false
```

必须保留。

---

# 44. GitHub CI

如果没有：

```text
workflow run
commit status
```

必须写：

```text
NO_RUN / NO_STATUS
```

不得自己把仓库内 pytest receipt 等同 GitHub CI。

---

# 45. 本轮不允许的“成功捷径”

禁止：

```text
E4比E3好
→ 接E4

E2当前最好
→ 宣布E2是Champion

ENTRY预测可跑
→ 当作Daily预测

历史重建可跑
→ 当作FIRST_OBSERVED

seen Outer有指标
→ 当作新OOS

synthetic priority效果好
→ 当作Priority有效

API能返回
→ 当作MODEL_DISPLAY获权

Priority Shadow能排序
→ 当作PRIORITY_USE获权
```

---

# 46. E5 Exit Gate

本轮最高允许状态：

```text
V4_15E5_ENGINEERING =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

必须同时：

```text
ENTRY_PROJECTION_ENGINEERING = PASS
PREDICTION_LEDGER = PASS
MODEL_EVIDENCE_BINDING = PASS
API_READBACK = PASS
PRIORITY_SHADOW_ENGINE = PASS_ENGINEERING
ENTRY_DAILY_SEPARATION = PASS
PERMISSION_GOVERNANCE = PASS
ROLLBACK = PASS
PRIORITY_V1_PROTECTED = PASS
TARGETED_REGRESSION = PASS
SCOPED_INTRODUCED_FAILURES = 0
```

但必须保持：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
PRIORITY_USE = UNGRANTED
MODEL_DISPLAY = UNGRANTED
CHAMPION = false
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

---

# 47. 允许的阻断状态

如果 projection 工程本身失败：

```text
BLOCKED_ENGINEERING
```

如果 ENTRY 可完成但 Daily engine fixture 暂时有实现缺口：

```text
PARTIAL_BLOCKED_DAILY_PRIORITY_ENGINE
```

如果 Daily 只是缺真实样本/真实模型：

```text
NOT_BLOCKED
```

因为本轮设计就是：

```text
real Daily activation NOT_ENABLED
```

真实数据不足不能拿来阻塞独立工程实现。

---

# 48. 最终交付格式

Codex 完成后必须：

1. 提交代码、配置、测试和 evidence；
2. 给出 exact implementation commit；
3. 给出 parent/base；
4. 给出 changed file list；
5. 给出 targeted + scoped regression；
6. 给出所有 negative matrix；
7. 给出 protected state readback；
8. 给出 candidate seal；
9. 停止，不自行宣布外部通过。

最终只允许报告：

```text
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

或：

```text
BLOCKED / PARTIAL_BLOCKED
```

禁止自行报告：

```text
EXTERNAL_ACCEPTANCE_PASS
PRODUCTION_PASS
PRIORITY_USE_GRANTED
MODEL_DISPLAY_GRANTED
```

---

# 49. 最终执行命令

```text
Execute V4-15E5 exactly against baseline:

adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb

Implement:
- ENTRY projection ledger/API from accepted E2 baseline
- E3/E4 diagnostic-only binding
- immutable prediction slots and receipts
- Daily Priority V2 shadow engine as engineering capability only
- strict ENTRY vs DAILY separation
- permission / rollback / no-feedback governance
- pre-run protocol freeze
- full negative matrix and regression

Do not:
- retrain models
- recompute labels
- mutate PRIORITY_V1
- use seen Outer as promotion
- grant CHAMPION / MODEL_DISPLAY / PRIORITY_USE / production
- mark reconstructed history FIRST_OBSERVED
- use ENTRY forecasts as current DAILY predictions

Stop at:
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 50. 当前项目状态迁移

E5 开始前：

```text
E4 = FORMALLY_CLOSED
E5_ENTRY = AUTHORIZED
E5_STARTED = false
```

本任务卡正式发布后：

```text
E5_FORMAL_TASK_CARD = ISSUED
E5_EXECUTION = AUTHORIZED
```

但只有 Codex 实际提交并经独立审计后，才能决定：

```text
E5_ENGINEERING_ACCEPTED
```

**文档结束**

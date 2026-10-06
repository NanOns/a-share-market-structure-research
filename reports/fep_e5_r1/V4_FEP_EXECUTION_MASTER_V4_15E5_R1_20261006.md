# V4 FEP Execution Master｜V4-15E5 R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 当前阶段：V4-15E5  
> 执行基线：`adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb`  
> 主任务卡：`V4_15E5_FEP_PROJECTION_PRIORITY_SHADOW_ENGINEERING_TASK_R1_20261006.md`  
> 调度性质：最高执行调度卡 / 本轮 Codex 唯一执行入口

---

# 0. 唯一目标

执行：

```text
V4-15E5
FEP Projection / Priority Shadow Engineering
```

本轮不是模型训练轮，不是模型晋级轮，不是 Production Priority 切换轮。

唯一目标：

```text
把 E2/E3/E4 已有 artifact
接入 immutable prediction / projection / permission / API / Priority Shadow 工程链，
并证明不会破坏 PRIORITY_V1 或 Core。
```

---

# 1. 基线

必须从 exact HEAD：

```text
adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb
```

开始。

该 HEAD 已完成：

```text
E4 = FORMALLY_CLOSED
E5_ENTRY = AUTHORIZED
```

任何其他 HEAD：

```text
先停止
输出 BASELINE_MISMATCH
```

不得自动 rebase 后继续假装同一任务。

---

# 2. 执行优先级

P0：

```text
A. protocol freeze
B. upstream exact binding
C. ENTRY/DAILY semantic isolation
D. prediction slot / ledger
E. PRIORITY_V1 protection
F. permission / rollback
```

P1：

```text
G. E2 baseline projection
H. E3/E4 diagnostic-only binding
I. API/readback
J. Daily Priority shadow synthetic fixture
```

P2：

```text
K. negative matrix
L. regression
M. seal / completion
```

---

# 3. 强制上游解释

模型证据等级：

```text
E2 = PRIMARY_E5_ENGINEERING_SOURCE
E3 = DIAGNOSTIC_SHADOW_ONLY / NO_INCREMENT
E4 = DIAGNOSTIC_SHADOW_ONLY / MIXED / NO_INCREMENT_VS_E2
```

当前：

```text
CHAMPION = NONE
```

不得自行选择新 champion。

---

# 4. 实际可运行 scope

真实工程 projection：

```text
FEP_STOCK_ENTRY_CORE
FIRST_PREWATCH
ABS_RETURN_N:T1
CORE
RECONSTRUCTED_CORRECTED
```

真实 Daily Priority：

```text
NOT_ENABLED
```

因为没有：

```text
accepted DAILY_LANDMARK model
+
same-day prediction
+
new independent OOS
```

---

# 5. Daily Priority 开发策略

不得等真实 Daily 样本才写工程。

允许：

```text
synthetic / engineering fixture
```

完成：

```text
PRIORITY_V1 complete pool
→ DAILY FEP axis
→ PRIORITY_V2 shadow
→ rollback
```

但必须保留：

```text
synthetic_only = true
REAL_PRIORITY_SHADOW = NOT_GRANTED
```

---

# 6. 运行前冻结

任何 evaluation 前必须写入并 seal：

```text
effectiveness disposition rule
primary metric
tie-break
promotion boundary
priority projection boundary
shadow-only boundary
model evidence class
```

本轮：

```text
E5_EFFECTIVENESS_EVALUATION =
CLOSED_ENGINEERING_ONLY

promotion_boundary =
CLOSED_NO_DAILY_SCOPE_NO_REAL_OOS
```

---

# 7. 严禁事项

```text
new model fit
new hyperparameter search
new label settlement
current-head rebuild of old T0
ENTRY → DAILY reuse
seen Outer → promotion
E2/E3/E4 → CHAMPION
MODEL_DISPLAY grant
PRIORITY_USE grant
production activation
PRIORITY_V1 mutation
PREWATCH eligibility mutation
State/Radar/Cohort feedback
```

---

# 8. 必做工作包

## WP1｜Protocol & Authority Freeze

输出：

```text
fep_e5_projection_priority_protocol_v1
model_evidence_class_v1
upstream bindings
```

## WP2｜Prediction Slot / Ledger

输出：

```text
planned slots
model bindings
runs
predictions
receipts
append-only readback
```

## WP3｜ENTRY Projection

以 E2 baseline 为主。

E3/E4 仅诊断。

## WP4｜Priority Shadow Engine

真实 Daily：

```text
NOT_ENABLED
```

synthetic fixture：

```text
PASS required
```

## WP5｜Permission / API

必须逐 scope/target/horizon/feature/model/capability 授权。

## WP6｜Rollback / Atomicity

FEP failure 不影响 Core/Priority V1。

## WP7｜Negative / Regression

按主任务卡执行完整矩阵。

## WP8｜Seal

候选 seal 后停止。

---

# 9. 退出状态

成功时只能：

```text
FEP_E5 =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

同时：

```text
PRIORITY_USE = UNGRANTED
MODEL_DISPLAY = UNGRANTED
FEP_PRODUCTION = UNGRANTED
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
CHAMPION = false
```

如果 Codex 输出任何更高权限：

```text
视为越权
```

---

# 10. 与主线关系

E5 仍是：

```text
V4-15 optional branch
```

不是：

```text
V4-16~22 总前置门
```

真实 Daily FEP OOS 样本积累不能阻塞其他独立开发。

---

# 11. 外部验收入口

Codex 完成后提交：

```text
implementation commit SHA
parent SHA
candidate seal
completion report
negative matrix
targeted/scoped regression
protected state readback
```

之后停止，交给独立外部审计。

**文档结束**

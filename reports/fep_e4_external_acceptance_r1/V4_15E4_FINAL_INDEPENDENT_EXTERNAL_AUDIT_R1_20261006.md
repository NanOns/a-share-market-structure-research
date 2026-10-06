# V4-15E4｜FEP Tree Challenger Engineering Final Independent External Audit R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E4  
> 审计性质：独立外部验收 / capability-scoped engineering audit  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`77c7c2c85a5ff0bbd27bb664900673de7a3bff5a`  
> 审计 HEAD：`848db27bfd2ede74ef1eac508f5454044d2211ce`

---

# 0. 唯一总裁决

```text
V4_15E4_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

FEP_TREE_CHALLENGER_ENGINEERING =
PASS_EXTERNAL_FIRST_PREWATCH_T1

CHALLENGER_EFFECTIVENESS =
MIXED

PRIMARY_EFFECTIVENESS_VS_E2 =
NO_INCREMENT

DIAGNOSTIC_EFFECTIVENESS_VS_E3 =
IMPROVED

E3_MODEL_EFFECTIVENESS =
NO_INCREMENT

SEEN_OUTER_DIAGNOSTIC_ONLY =
true

NEW_INDEPENDENT_OOS_EVIDENCE =
false

REAL_OOS =
NOT_GRANTED

FIRST_OBSERVED =
NOT_GRANTED

CHAMPION =
false

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

E5_ENTRY =
AUTHORIZED_NOT_BLOCKED_BY_E4
```

E4 可以正式通过本轮独立外部工程验收，但通过范围必须严格限定为：

> 在 E3 已冻结的数据、时间切分、特征、预处理和 OOD 边界内，成功实现了一个受限 HistGradientBoosting challenger 工程能力，并完成了已见 Outer 上的同人口诊断比较。

本轮**不能**解释为：

```text
树模型已证明优于现有基线
树模型已获得新独立 OOS 证据
模型已可展示给用户
模型已可影响 PRIORITY
模型已成为 CHAMPION
FEP 已获生产权限
```

---

# 1. 审计输入同步

本轮审计首先同步 Google Drive 当前正式执行基准，确认最新有效文件为：

```text
V4_FEP_EXECUTION_MASTER_V4_15E4_R1_20261005.md
V4_15E4_TREE_CHALLENGER_ENGINEERING_TASK_R1_20261005.md
V4_15E3_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md
```

E4 Execution Master 明确要求：

```text
exact E3 folds/features/OOD
→ freeze bounded tree challenger budget
→ TRAIN fit
→ INTERNAL_TUNE selection
→ CALIBRATION diagnostics
→ exact E3 predictable population
→ seen-Outer diagnostic only
→ E2 vs E3 vs E4 comparison
→ immutable challenger registry
→ STOP external audit
```

并明确：

```text
E3 Outer Test is already seen
E4 may use it only as SEEN_OUTER_DIAGNOSTIC_ONLY

not NEW_UNSEEN_TEST
not REAL_OOS
not PROMOTION_EVIDENCE
```

GitHub 当前分支 HEAD：

```text
848db27bfd2ede74ef1eac508f5454044d2211ce
```

其唯一父提交：

```text
77c7c2c85a5ff0bbd27bb664900673de7a3bff5a
```

与 E4 任务卡执行基线完全一致。

因此本轮不存在夹杂其它提交后再倒推出 E4 结果的问题。

---

# 2. Exact E3 Input Reuse｜PASS

E4 的 `E3_INPUT_BINDING.json` 对 E3 当前正式产物逐文件绑定 byte size + SHA256，并声明：

```text
status = PASS_EXACT_ACCEPTED_BYTES
live_rebuild = false
new_label_resolution = false
```

核对通过的关键输入包括：

```text
E3 active protocol v1.1
FOLD_MANIFEST
PURGE_ROW_LEDGER
FEATURE_MANIFEST
preprocessing
OOD reference
exact model rows
E3 model artifacts
E3 Outer population
E3 candidate seal
E2 baseline dependencies
accepted heads
priority authority
```

没有发现：

```text
重新从 current head 构造 E2/E3 membership
解析更新 label revision
扩大 ENTRY event scope
引入 REENTRY / NEW_CONFIRMED
更换 target / horizon
```

结论：

```text
E3_INPUT_REUSE = PASS
```

---

# 3. Split / Feature / OOD Reuse｜PASS

## 3.1 Fold

`FOLD_REUSE_GATE.json`：

```text
TRAIN = 3893
INTERNAL_TUNE = 147
CALIBRATION = 213
OUTER_TEST predictable rows = 46
new_split = false
```

使用 E3 原 fold artifact，不重新随机切分。

## 3.2 Feature

`FEATURE_REUSE_GATE.json`：

```text
20 feature terms
exact E3 feature manifest
exact E3 preprocessing
fit = false
imputer = false
```

没有新增：

```text
feature
imputation
feature selection
outcome-driven transform
```

## 3.3 OOD

`OOD_REUSE_GATE.json`：

```text
PASS_EXACT_E3_MARGINAL_JOINT_UNSET
relaxation = false
JOINT_OOD = UNSET
global_OOD_OK = false
```

没有为了让树模型获得更多可预测样本而放宽 OOD。

结论：

```text
FOLD_REUSE = PASS
FEATURE_REUSE = PASS
OOD_REUSE = PASS
```

---

# 4. Hyperparameter Protocol Freeze｜PASS

这是本轮最重要的防后见偏差门之一。

`CHALLENGER_PROTOCOL_DISCOVERY.json` 显示，在任何 fit 前：

```text
selection_outcome_performance_consumed = false
trial_fits = 0
```

网格依据是工程资源约束：

```text
small depth / leaf grid
fixed 100 iterations
min_samples_leaf = 40
threads = 2
no automatic early stopping
no random validation split
```

实际预算：

```text
point trials = 4
quantile trials = 6
total fits = 10
```

均低于任务卡上限：

```text
point <= 8
quantile <= 12
total <= 20
```

`CHALLENGER_PROTOCOL_FREEZE.json`：

```text
PASS_FROZEN_BEFORE_FIT
fits_before_freeze = 0
```

冻结时间早于所有 10 个 training trial。

因此：

```text
HYPERPARAMETER_BUDGET_PRE_FREEZE = PASS
NO_RESULT_DRIVEN_GRID_EXPANSION = PASS
```

---

# 5. TRAIN-only Fit / INTERNAL_TUNE-only Selection｜PASS

本轮共留下 10 个 immutable trial，全部 SUCCESS。

## 5.1 Point challenger

4 个 `HGB_ABSOLUTE_ERROR` trial 的 INTERNAL_TUNE 指标：

```text
trial 0 = 0.0202896316269  ← selected
trial 1 = 0.0203946917882
trial 2 = 0.0207645065437
trial 3 = 0.0214413039392
```

selected trial 0 确实为最小值。

## 5.2 q25

```text
trial 4 = 0.0073921340024
trial 5 = 0.0068953383378  ← selected
```

## 5.3 q50

```text
trial 6 = 0.0101448158135  ← selected
trial 7 = 0.0107206519696
```

## 5.4 q75

```text
trial 8 = 0.0092270148824
trial 9 = 0.0091961384767  ← selected
```

所有 trial：

```text
selection_partition = INTERNAL_TUNE
model_state = CHALLENGER_ENGINEERING_ONLY
REAL_OOS = false
PROMOTION_EVIDENCE = false
CHAMPION = false
```

训练 dependency 中绑定同一：

```text
TRAIN IDs digest
E3 preprocessing
E3 OOD reference
protocol digest
runtime versions
```

未发现 CALIBRATION 或 Outer 指标进入模型选择。

结论：

```text
TRAIN_ONLY_FIT = PASS
INTERNAL_TUNE_ONLY_SELECTION = PASS
OUTER_DRIVEN_TUNING = NOT_FOUND
```

---

# 6. Calibration｜PASS_WITH_LIMITATION

Calibration 只作为 diagnostics 使用：

```text
rows = 213
selection = false
probability_calibration = NOT_APPLICABLE_REGRESSION
```

E4：

```text
raw crossing rows = 3
weighted raw crossing frequency ≈ 1.0896%
coherent crossing rows = 0
mean middle interval width ≈ 0.035877
middle interval empirical coverage ≈ 0.346328
```

单分位 empirical coverage：

```text
q25 ≈ 0.1000
q50 ≈ 0.19066
q75 ≈ 0.44633
```

这些数值本身显示：

> 当前 quantile 预测仍然不具备可被包装成“可信概率区间”的资格。

但任务卡本来就禁止 probability calibration claim，且 E4 没有越权宣称。

结论：

```text
CALIBRATION_ROLE = PASS
QUANTILE_CALIBRATION_QUALITY = WEAK
PROBABILITY_CLAIM = NOT_GRANTED
```

---

# 7. Seen Outer Gate｜PASS

`SELECTED_DEPENDENCIES.json` 的模型选择在：

```text
2026-10-05T15:06:25.558151Z
```

冻结。

`SEEN_OUTER_DIAGNOSTIC_OPEN.json` 直到：

```text
2026-10-05T15:07:54.460055Z
```

才打开已见 Outer。

因此顺序满足：

```text
protocol freeze
→ train
→ INTERNAL_TUNE selection
→ selected dependencies freeze
→ calibration
→ seen Outer open
```

Outer population：

```text
exact comparable rows = 46
original outer population = 205
coverage = 22.4390%
dates = 35
blocks = 24
entities = 46
episodes = 46
same_ID_order = true
same_weights = true
```

并持续写明：

```text
SEEN_OUTER_DIAGNOSTIC_ONLY = true
TEST_PREVIOUSLY_SEEN = true
REAL_OOS = false
PROMOTION_EVIDENCE = false
```

结论：

```text
SEEN_OUTER_BOUNDARY = PASS
NEW_OOS_CLAIM = NOT_FOUND
```

---

# 8. E2 vs E3 vs E4｜MIXED / NO_INCREMENT VS E2

同一 46 个 observation IDs 上：

| Model | DATE_BALANCED_MAE | DATE_BALANCED_HUBER_LOSS | DATE_BALANCED_RMSE | weighted sign hit |
|---|---:|---:|---:|---:|
| E2 baseline | 0.0253833272 | 0.0002082618 | 0.0316968749 | 0.542857 |
| E3 Huber | 0.0264982642 | 0.0002202852 | 0.0339868534 | 0.500000 |
| E4 HGB | 0.0256040815 | 0.0002093785 | 0.0316344061 | 0.500000 |

因此：

```text
E4 vs E3 MAE:
better by ≈ 0.0008941827

E4 vs E2 MAE:
worse by ≈ 0.0002207543
```

也就是说：

> E4 修复了 E3 的一部分性能退化，但没有击败最简单的 E2 baseline。

所以：

```text
CHALLENGER_EFFECTIVENESS = MIXED
PRIMARY_EFFECTIVENESS_VS_E2 = NO_INCREMENT
```

这里不能因为“E4 比 E3 好”就得出：

```text
TREE_MODEL_VALIDATED
```

真正强基线仍然是 E2。

---

# 9. Quantile Comparison｜MIXED / NOT PROMOTABLE

Seen Outer 上：

E3：

```text
mean interval width ≈ 0.029636
middle coverage ≈ 0.364286
q25 coverage ≈ 0.22857
q50 coverage ≈ 0.51429
q75 coverage ≈ 0.59286
```

E4：

```text
mean interval width ≈ 0.031683
middle coverage ≈ 0.395238
q25 coverage ≈ 0.23333
q50 coverage = 0.50000
q75 coverage ≈ 0.62857
```

Pinball 指标同样是有好有坏，而不是一致提升。

因此 quantile challenger 只能保留为：

```text
ENGINEERING_DIAGNOSTIC
```

不能升级为：

```text
CALIBRATED_PROBABILITY
PREDICTIVE_INTERVAL_PASS
PROMOTION_EVIDENCE
```

---

# 10. Immutable Registry / Serialization｜PASS

`MODEL_REGISTRY_GATE.json`：

```text
PASS_IMMUTABLE_CHALLENGER_LEDGER
failed_trials_retained = true
logical_ID_excludes_created_at = true
models_portable_JSON = true
```

registry 留存：

```text
10 attempt receipts
10 trial artifacts
selected point model
selected q25/q50/q75 models
calibration artifact
feature importance artifact
seen Outer predictions
seen Outer evaluation
```

Tree JSON 与 sklearn 实际预测有 parity test，误差门限 `<= 1e-12`。

因此：

```text
IMMUTABLE_TRIAL_LEDGER = PASS
PORTABLE_MODEL_SERIALIZATION = PASS
```

---

# 11. Negative Matrix｜PASS

任务卡要求的 E4-01～E4-20 均有实际负向测试覆盖，包括：

```text
new random split rejected
fold mutation rejected
pooled ENTRY rejected
REENTRY / NEW_CONFIRMED rejected
new feature rejected
OOD relaxation rejected
seen Outer tuning rejected
unseen claim rejected
REAL_OOS claim rejected
promotion rejected
budget overflow rejected
failed trial deletion rejected
CALIBRATION selection rejected
post-result coherence change rejected
E3 mutation rejected
PRIORITY mutation rejected
MODEL_DISPLAY rejected
PRIORITY_USE rejected
production/shadow/focus rejected
failure leaves upstream unchanged
```

实际 negative matrix：

```text
31 cases
31 PASS
synthetic_only = true
```

其中还额外覆盖：

```text
tree serialization parity
failed-trial selection behavior
Outer feature-importance rejection
non-TRAIN fit rejection
logical ID timestamp exclusion
```

结论：

```text
NEGATIVE_MATRIX = PASS
```

---

# 12. Regression｜PASS_CAPABILITY_SCOPED_WITH_KNOWN_DEBT

Targeted：

```text
256 passed
1 skipped
0 failed
0 introduced active failures
```

Scoped regression：

```text
2615 passed
4 skipped
52 failed
0 introduced active failures
```

52 个失败节点与 E3 上游已登记 existing debt 节点逐项一致，并不是 E4 新引入失败。

两项原有 deselection 也与上游一致。

因此：

```text
E4_INTRODUCED_REGRESSION = 0
```

但必须明确：

> 整个仓库当前不是“全绿测试”。

本轮只能声明：

```text
PASS_CAPABILITY_SCOPED_WITH_EXACT_KNOWN_DEBT
```

不能把 52 个历史 debt failure 从项目状态中抹掉。

另外，当前 commit 没有 GitHub Actions workflow run / commit status 可作为额外 CI 证据，因此本次结论依赖仓库内封存的 pytest XML/log/readback 与独立代码审计，而不是 GitHub CI 绿灯。

---

# 13. Protected State｜PASS

E4 后：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

R25 = WAIT_ACCEPTED_DAILY_INPUT
PRIORITY_V1 = UNCHANGED
E3_MODEL_EFFECTIVENESS = NO_INCREMENT

FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = false
PROMOTION_EVIDENCE = false
CHAMPION = false

MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED

production = false
shadow = false
focus = false
```

33 张正式 FEP 表在本次 isolated engineering run 后仍为 0 行。

TDX：

```text
UNTOUCHED
```

R25 protected path historical diff：

```text
[]
```

结论：

```text
PROTECTED_STATE = PASS
```

---

# 14. 非阻断审计备注｜Disposition Rule Freeze

本轮发现一个治理层面的轻微不足：

任务卡预先冻结了：

```text
primary criterion = DATE_BALANCED_MAE
allowed dispositions =
PASS_INCREMENT_DIAGNOSTIC
PASS_NO_INCREMENT
PASS_MIXED
BLOCKED
```

但是具体映射：

```text
INCREMENT if beats both E2 and E3
NO_INCREMENT if beats neither
otherwise MIXED
```

没有作为字段写入 fit 前冻结的 `fep_e4_challenger_protocol_v1.json`，而是在 `seen_outer()` 评价代码中定义。

这不构成本轮阻断，原因是：

1. 它没有参与 hyperparameter selection；
2. 没有触发 refit；
3. 不改变 observation population；
4. 不提供 promotion 权限；
5. 即使结果标签改变，也不能让 E4 获得 CHAMPION / PRIORITY / production 权限。

但后续 E5 或任何新的 effectiveness audit 应要求：

```text
effectiveness disposition rule
必须与 primary metric / tie-break / promotion boundary
一起 pre-register / freeze before evaluation open
```

审计状态：

```text
AUDIT_NOTE_E4_01 =
PASS_NONBLOCKING_GOVERNANCE_HARDENING_REQUIRED
```

---

# 15. 仍然存在的模型限制

这些不是 E4 实施错误，但必须继续保留：

## L1. Outer 可预测覆盖低

```text
46 / 205 = 22.4390%
```

意味着当前 effectiveness 只代表非常窄的一部分历史 population。

## L2. Outer 已见

这轮不是新独立 OOS。

## L3. JOINT_OOD 仍为 UNSET

当前只有 marginal OOD，不能宣称完整多变量分布外保护。

## L4. E4 未击败 E2

树模型复杂度上升并没有带来相对最简单 baseline 的主指标增益。

## L5. Quantile calibration 仍弱

不能把 q25/q50/q75 直接解释为稳定概率意义上的 25%/50%/75% 分位。

---

# 16. 最终验收矩阵

| Gate | Result |
|---|---|
| Drive latest authority sync | PASS |
| Git baseline / parent identity | PASS |
| Exact E3 bytes reuse | PASS |
| Exact folds reuse | PASS |
| Exact features/preprocessing reuse | PASS |
| Exact OOD reuse / no relaxation | PASS |
| Pre-fit challenger budget freeze | PASS |
| TRAIN-only fitting | PASS |
| INTERNAL_TUNE-only selection | PASS |
| CALIBRATION diagnostic only | PASS |
| Seen Outer opened after selection | PASS |
| Exact E3 predictable population | PASS |
| Outer-driven tuning | NOT FOUND |
| New independent OOS claim | NOT FOUND |
| E2/E3/E4 same-population comparison | PASS |
| Tree serialization parity | PASS |
| Immutable registry | PASS |
| Negative matrix | PASS |
| Targeted regression | PASS |
| Scoped regression introduced failures | 0 |
| Protected heads / R25 / PRIORITY | PASS |
| TDX mutation | NOT FOUND |
| Production / Shadow / Focus grant | NOT FOUND |
| GitHub CI status | NO RUN / NO STATUS |
| Disposition-rule pre-freeze | NONBLOCKING NOTE |

---

# 17. 下一步权限

本轮外部验收后：

```text
E4_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED
```

E4 到此正式收尾。

根据既有 FEP 设计顺序：

```text
Level 0 Outcome / PIT Infrastructure
→ Level 1 Conditional Statistics
→ Level 2 Interpretable Baseline Model
→ Level 3 Tree Challenger
→ Level 4 Expectancy-aware Priority Projection
```

因此：

```text
E5_ENTRY = AUTHORIZED
```

但 E5 必须继续遵守：

```text
no promotion from seen Outer
no MODEL_DISPLAY from E4
no PRIORITY_USE from E4
no production grant from E4
no retroactive rewrite of PRIORITY_V1
```

E5 的正式实施必须另发独立任务卡，并把：

```text
effectiveness disposition rule
promotion boundary
priority projection boundary
shadow-only boundary
model evidence class
```

在运行前冻结。

---

# 18. 唯一最终状态

```text
V4_15E4_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

FEP_TREE_CHALLENGER_ENGINEERING =
PASS_EXTERNAL_FIRST_PREWATCH_T1

CHALLENGER_EFFECTIVENESS =
MIXED

PRIMARY_EFFECTIVENESS_VS_E2 =
NO_INCREMENT

NEW_INDEPENDENT_OOS_EVIDENCE =
false

CHAMPION =
false

MODEL_DISPLAY =
UNGRANTED

PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

E5_ENTRY =
AUTHORIZED

NEXT =
ISSUE_V4_15E5_EXPECTANCY_AWARE_PRIORITY_PROJECTION_TASK
```

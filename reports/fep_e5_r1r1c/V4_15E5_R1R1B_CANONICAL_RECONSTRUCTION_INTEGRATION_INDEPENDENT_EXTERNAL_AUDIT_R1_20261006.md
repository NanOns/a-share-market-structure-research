# V4-15E5 R1R1B｜Canonical Reconstruction Integration Independent External Audit R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 阶段：V4-15E5 R1R1B  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`9a6ecd205c690b62063cc80810272dda8001cfe9`  
> Implementation Candidate：`58372af31c246fd86f18e70654c8f615ce0d983c`  
> Remote Receipt HEAD：`68b3d97d1f5d98a4ed6be87bca3ce8c81696e587`

## 0. 唯一总裁决

```text
V4_15E5_R1R1B_FINAL_EXTERNAL_AUDIT =
BLOCKED_R1_CANONICAL_METADATA_BINDING

PASS_KEEP =
RECONSTRUCTION_AUTHORITY
MIGRATION_032
PIT_PATH
205_OBSERVATIONS
205_SNAPSHOTS
4100_FEATURE_VALUES
615_PROJECTIONS
616_SLOTS
OUTPUT_PARITY
ARTIFACT_IMPORT
SHADOW_PERMISSION
CANONICAL_CAS
ROLLBACK
API
PRIORITY_BOUNDARY
V4_18_SUCCESSOR
REGRESSION
PROTECTED_STATE

BLOCKERS =
R1R1B-M01 TARGET_CONTRACT_EXACT_BINDING
R1R1B-M02 CORE_SIGNAL_CONTRACT_EXACT_BINDING

NEXT =
ISSUE_V4_15E5_R1R1C_CANONICAL_METADATA_BINDING_REPAIR
```

R1R1B 主体工程基本成功，但还不能正式关闭 E5。剩余问题不是 reconstruction authority、projection 或 CAS，而是两处 canonical metadata 语义错绑。

## 1. Git / 基线身份｜PASS

Implementation commit `58372af3...` 的 parent 正是正式任务基线 `9a6ecd20...`。随后 `68b3d97...` 仅封存 remote candidate/readback，没有改变 implementation 语义。

```text
BASELINE_IDENTITY = PASS
REMOTE_CANDIDATE_VISIBLE = PASS
```

## 2. Additive Migration 032｜PASS

新增：

```text
032_fep_reconstruction_authority_shadow_v1.sql
```

028–031 保持不变。032 正确增加了：

- `fep.reconstruction_authorities`
- observation authority union
- prediction-run authority union
- accepted-artifact model import origin
- reconstruction snapshot/feature guards
- reconstruction evidence guards
- non-Champion `SHADOW_INFERENCE` role repair
- canonical acceptance/run guards

原 PIT publication validator 保留。

## 3. Historical Reconstruction Authority｜PASS

205 条历史 observation 均为：

```text
authority_kind = HISTORICAL_RECONSTRUCTION
publication_id = null
evidence_origin = RECONSTRUCTED_CORRECTED
execution_mode = REPLAY
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
```

`reconstructed_at` 使用当前真实记录时间，没有伪造历史 accepted_at。Fresh `v4.publications=0`；upgrade 仅有 1 条当前 synthetic PIT regression publication，不属于历史回填。

```text
FAKE_HISTORICAL_PUBLICATION = NOT_FOUND
HISTORICAL_AVAILABILITY_FABRICATION = NOT_FOUND
```

## 4. Observation / Snapshot / Feature｜PASS

```text
historical observations = 205
reconstruction authorities = 205
canonical snapshots = 205
canonical feature values = 4100
UNKNOWN feature values = 477
dropped observations = 0
```

Snapshot 绑定 observation/revision/feature contract/feature digest/quality digest/exact feature entries/source digests，不再用整包 artifact digest 冒充 snapshot identity。

## 5. Canonical Prediction Ledger｜PASS

Fresh / upgrade 均保持：

```text
prediction_slots = 616
slot_model_bindings = 615
prediction_runs = 615
predictions = 615
acceptance_receipts = 615
slot_receipts = 616
```

E2/E3/E4 每族：

```text
READY = 46
REJECTED_QUALITY = 159
```

与 E5 R1 exact reconciliation：

```text
exact_output_equality = true
numeric_outputs_changed = 0
new_fit = 0
new_search = 0
new_label_resolution = 0
```

## 6. Historical Slot Clock｜PASS

R1R1B 使用当前工程执行时钟作为 prediction selection cutoff/deadline，这与 E5 R1 冻结语义一致：

```text
model_selection_cutoff = actual engineering UTC
prediction_deadline = selection cutoff + 60 minutes
historical_trade_dates_not_real_prediction_dates = true
prediction_evidence = HISTORICAL_SIMULATION
```

因此不构成 FIRST_OBSERVED 越权。

## 7. Accepted Artifact Import｜PASS

Candidate 没有伪造 training run，而是通过 `ACCEPTED_ARTIFACT_IMPORT` 导入 E2/E3/E4 accepted artifacts：

```text
models = 3
training_runs = 0
new training = 0
CHAMPION = NONE
```

Imported BASELINE/CHALLENGER 受 DB guard 限制，不能伪造为 CHAMPION。

## 8. Permission / CAS｜PASS

032 正确把权限语义改为：

```text
SHADOW_INFERENCE
→ BASELINE / CHALLENGER / CHAMPION exact member

DESCRIPTIVE_DISPLAY / MODEL_DISPLAY / PRIORITY_USE
→ CHAMPION only
```

实际只有 3 个 SHADOW key：E2 BASELINE、E3/E4 CHALLENGER。最终 heads 全部 REVOKE。

CAS 并发验证：

```text
exactly one winner
other = FEP_CAS_CONFLICT
no orphan activation
no orphan receipt
idempotent replay = PASS
rollback = PASS
```

## 9. API / Priority Boundary｜PASS

默认 API 不返回模型轴：

```text
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
FIRST_OBSERVED = false
REAL_OOS = false
```

Priority 仍是 synthetic linkage only，`priority_projection_grants=0`，未修改 PRIORITY_V1。

## 10. Regression｜PASS_CAPABILITY_SCOPED

```text
Targeted = 527 passed / 1 skipped / 0 failed
Scoped = 2886 passed / 4 skipped / 52 exact known debt / 0 introduced
```

既有 2 个 governed deselection 保留。仓库仍不可声称 all-green。

## 11. V4-18 Successor｜PASS_NONBLOCKING

新增 `config/v4_18_migration_replay_contract_v1_2.json` 与 successor test，仅用于让当前 SQL inventory 包含新增 FEP table。

没有：

```text
V4-18 migration replay grant
production cutover
V4_18 accepted head
```

符合 E1 已采用的 successor governance 模式，不构成本轮 blocker。

## 12. Blocker M01｜Target Contract Identity 错绑

正式 Target Registry：

```text
config/fep_target_registry_v1.json

contract_id = FEP_E1_TARGETS_V1

ABS_RETURN_N:T1:
family = ABS_RETURN_N
horizon = 1
scope_id = FEP_STOCK_ENTRY_CORE
definition_reference = FEP.5/ABS_RETURN_N
status = REGISTERED_NOT_ENABLED
training_allowed = false
engineering_adapter = true
```

但 candidate `canonical_ledger.py::seed_identity()` 创建：

```text
contract(FEP_E5_OBSERVATION_V1, ...)
```

随后写入：

```text
target_id = ABS_RETURN_N:T1
contract_id = FEP_E5_OBSERVATION_V1
formula = "accepted V4-15 ABS_RETURN_N:T1"
enabled = true
```

问题：

1. Observation contract 被错误用作 Target contract。
2. `"accepted V4-15 ABS_RETURN_N:T1"` 不是 accepted target formula；正式设计定义是 `R_N`。
3. `enabled=true` 与 registry 的 `REGISTERED_NOT_ENABLED` 不一致。`engineering_adapter=true` 不等于 target 全局启用。

因此：

```text
R1R1B_M01_TARGET_CONTRACT_EXACT_BINDING = FAIL
```

这违反了原 R1R1 的“不得新 Target 定义”边界。

## 13. Blocker M02｜Core Signal Contract Identity 错绑

Candidate 对全部 205 条 observation 写入：

```text
core_signal_contract_id =
FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1
```

但 reconstruction authority 描述的是：

```text
历史数据/时间/dependency authority
```

它不是 FIRST_PREWATCH 的事件定义。

已有 accepted event-strata authority：

```text
reports/fep_e2_r1r2/ENTRY_EVENT_STRATA_CONTRACT.json
contract_id = FEP_E2_ENTRY_EVENT_STRATA_V1_1
```

并明确：

```text
formal_signals = FIRST_PREWATCH / NEW_CONFIRMED / REENTRY
FIRST_PREWATCH =
Accepted Radar ENROLLED
+ maturity PREWATCH
+ no parent episode
```

所以当前 candidate 把 availability authority 错塞进 signal contract 字段。

```text
R1R1B_M02_CORE_SIGNAL_CONTRACT_EXACT_BINDING = FAIL
```

## 14. 为什么必须阻断

Canonical 的要求不是“同名字段能对上”，而是：

```text
数据 identity
时间 authority
Target contract
Signal contract
```

都必须 exact-bind。

当前数据、时间、projection、permission 已经基本正确，但 Target 与 Signal metadata 还不是 accepted authority。如果直接 PASS，会留下“同 target_id / signal 名，但 contract semantic 不同”的长期债务。

## 15. 下一轮只修两项

### R1R1C-A
`ABS_RETURN_N:T1` exact-bind `FEP_E1_TARGETS_V1` 与 FEP.5 accepted definition；保持 `REGISTERED_NOT_ENABLED`，不得因 engineering adapter 将 target 全局 enable。

### R1R1C-B
205 条 FIRST_PREWATCH observation 的 `core_signal_contract_id` exact-bind accepted FIRST_PREWATCH event/signal authority，当前首选 `FEP_E2_ENTRY_EVENT_STRATA_V1_1`（若存在更严格已接受上游合同，可使用，但必须证明）。

## 16. 最终状态

```text
V4_15E5_R1R1B_FINAL_EXTERNAL_AUDIT =
BLOCKED_R1_CANONICAL_METADATA_BINDING

E5_B01 =
CANDIDATE_TECHNICALLY_IMPLEMENTED_BUT_NOT_FINAL_ACCEPTED

E5_B02 =
BLOCKED_METADATA_IDENTITY

E5_B03 =
PASS_CANDIDATE

NEXT =
V4_15E5_R1R1C_CANONICAL_METADATA_BINDING_REPAIR
```

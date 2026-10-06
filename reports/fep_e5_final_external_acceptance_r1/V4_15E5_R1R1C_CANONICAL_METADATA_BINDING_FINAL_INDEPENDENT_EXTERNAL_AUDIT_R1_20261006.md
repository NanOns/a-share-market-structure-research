# V4-15E5 R1R1C｜Canonical Metadata Binding Final Independent External Audit R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 R1R1C  
> 审计性质：独立外部验收 / E5 canonical integration 最终工程验收  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> R1R1C 执行基线：`68b3d97d1f5d98a4ed6be87bca3ce8c81696e587`  
> 首次实现提交：`28de34e0765e5cacb810366e973cf9772249f366`  
> Remote Candidate：`6d06288c56bc632539262b246b0829ceee317690`  
> Remote Closure Receipt HEAD：`cf74b179fe847cb7260fb4b47c6e3be2c3a82206`

## 0. 唯一总裁决

```text
V4_15E5_R1R1C_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

R1R1B_M01_TARGET_CONTRACT_EXACT_BINDING = PASS_FINAL
R1R1B_M02_CORE_SIGNAL_CONTRACT_EXACT_BINDING = PASS_FINAL

E5_B01_CANONICAL_FEP_LEDGER = CLOSED_PASS
E5_B02_CANONICAL_IDENTITY_BINDING = CLOSED_PASS
E5_B03_CANONICAL_PERMISSION_DEPLOYMENT = CLOSED_PASS

V4_15E5_EXTERNAL_ACCEPTANCE =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

E5_FORMAL_ARCHIVE_CLOSURE =
PENDING_RECONCILIATION_ONLY
```

权限仍全部关闭：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

下一步：

```text
V4_15E5_EXTERNAL_ACCEPTANCE_RECONCILIATION_AND_BRANCH_CLOSURE
```

---

## 1. Drive / Task Authority｜PASS

正式 Drive 最新任务链已核对，R1R1C task 已存在并与仓库归档版本一致，不存在 stale task / wrong stage / local-only task。

---

## 2. Git / Remote Publication｜PASS

执行链：

```text
68b3d97...  R1R1C baseline
28de34e...  main metadata implementation
6d06288...  remote publication verification + candidate seal repair
cf74b179...  remote evidence closure
```

`6d06288...` 相对 `28de34e...` 仅修改 remote tree traversal、candidate seal self-binding exclusion 和 evidence binding；未触及 metadata admission、prediction、CAS、API、Priority 主逻辑。

因此：

```text
IMPLEMENTATION_CANDIDATE = 6d06288...
REMOTE_EVIDENCE_CLOSURE = cf74b179...
REMOTE_VISIBILITY = PASS
```

---

## 3. M01｜Canonical Target Contract Exact Binding｜PASS_FINAL

正式 Target authority：

```text
config/fep_target_registry_v1.json
contract_id = FEP_E1_TARGETS_V1
SHA256 = 1ac08f5c30e2c6748346fcc5bdbc48c1a148f67cd656fad3357710925a48eeec
```

R1R1C canonical row：

```text
target_id = ABS_RETURN_N:T1
contract_id = FEP_E1_TARGETS_V1
scope_id = FEP_STOCK_ENTRY_CORE
horizon = 1
unit = ratio
value_kind = NUMERIC
formula = R_N
allowed_quality = [OBSERVED]
enabled = false
```

与正式 Registry：

```text
status = REGISTERED_NOT_ENABLED
training_allowed = false
engineering_adapter = true
definition_reference = FEP.5/ABS_RETURN_N
```

及设计 authority：

```text
FEP_R2_MODULE_DESIGN_20260930.md
ABS_RETURN_N = R_N
endpoint quality = OBSERVED
```

一致。

关键修复：

```text
engineering_adapter = true
!=
enabled = true
```

结论：

```text
M01 = PASS_FINAL
NEW_TARGET_DEFINITION = false
TARGET_GLOBAL_ENABLE = false
```

---

## 4. M02｜FIRST_PREWATCH Signal Contract Exact Binding｜PASS_FINAL

205 条 historical observations 全部：

```text
core_signal_contract_id =
FEP_E2_ENTRY_EVENT_STRATA_V1_1
```

Authority：

```text
reports/fep_e2_r1r2/ENTRY_EVENT_STRATA_CONTRACT.json
SHA256 = 9884d9df4530ceea9ee3268c30e5dfb65ef149939710eb87e66d73466408025a
```

定义：

```text
observation_scope = FEP_STOCK_ENTRY_CORE

formal_signals =
FIRST_PREWATCH
NEW_CONFIRMED
REENTRY

FIRST_PREWATCH =
Accepted Radar ENROLLED
+ maturity PREWATCH
+ no parent episode
```

同时 reconstruction authority 仍只负责 dependency / availability：

```text
reconstruction_authority_id
→ historical dependency authority

core_signal_contract_id
→ event semantic authority
```

Readback：

```text
205 / 205 exact contract
fallback = 0
reconstruction-authority substitution = 0
```

结论：

```text
M02 = PASS_FINAL
NEW_SIGNAL_DEFINITION = false
```

---

## 5. Reconstruction Authority｜PASS_KEEP

032 migration 未改。205 条 historical rows 继续保持：

```text
authority_kind = HISTORICAL_RECONSTRUCTION
publication_id = null
evidence_origin = RECONSTRUCTED_CORRECTED
execution_mode = REPLAY
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
```

没有 fake publication、fake accepted_at 或 current-head historical backfill。

---

## 6. Migration Governance｜PASS_KEEP

028–032 全部 exact bytes unchanged。R1R1C 没有新增 migration，并把 `NO_NEW_MIGRATION` 标记为：

```text
NOT_APPLICABLE
not_a_pass = true
```

没有用 N/A 冒充 PASS。

---

## 7. 205 / 615 / 616 Parity｜PASS

Fresh：

```text
observations = 205
reconstruction_authorities = 205
snapshots = 205
feature_values = 4100
predictions = 615
prediction_runs = 615
prediction_slots = 616
slot_model_bindings = 615
training_runs = 0
```

与 R1R1B parity：

```text
feature values identical
feature source digests identical
predictions identical
models identical
model_set_members identical
permission_keys identical
numeric_outputs_changed = 0
authority_ID_changes = 0
snapshot_ID_changes = 0
```

仅 execution-clock columns 在新的 disposable reconstruction 中重新生成，符合事实。

---

## 8. Metadata Negative Matrix｜PASS

R1R1C 新增并实际运行：

```text
TM01 ~ TM08
SM01 ~ SM07
accepted metadata positive
fresh DB readback
upgrade DB readback
```

共：

```text
18 / 18 PASS
```

覆盖 wrong target contract、enabled overclaim、wrong horizon/scope/family/formula，以及 reconstruction authority/observation contract/unknown signal/wrong event predicate 等错误绑定。

---

## 9. Targeted / Scoped Regression｜PASS_CAPABILITY_SCOPED

Targeted：

```text
545 passed
1 skipped
0 failed
```

Scoped：

```text
2904 passed
4 skipped
52 exact existing debt failures
0 introduced active failures
```

所以：

```text
INTRODUCED_ACTIVE_FAILURES = 0
REPOSITORY_ALL_GREEN = false
```

52 个历史债务继续保留，未被隐藏。

---

## 10. Permission / CAS｜PASS_KEEP

仍只有：

```text
E2 BASELINE SHADOW
E3 CHALLENGER SHADOW
E4 CHALLENGER SHADOW
```

并保持：

```text
CHAMPION = NONE
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
```

Canonical CAS 继续通过并发 one-winner、幂等、冲突和 rollback，最终 head 为 REVOKE。

所以：

```text
E5_B03 = CLOSED_PASS
```

---

## 11. API / Priority｜PASS_KEEP

Default API 不暴露模型轴；historical projection 仍是 `HISTORICAL_SIMULATION`，不是 FIRST_OBSERVED / REAL_OOS。

Priority 仍：

```text
synthetic linkage only
priority_projection_grants = 0
PRIORITY_V1 unchanged
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
```

---

## 12. Protected State｜PASS

未修改：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
config/v4_16_runtime_activation_authority_v3.json
PRIORITY_V1
Core/Profile/State/Radar/Cohort
TDX
```

仍然：

```text
V4_16_ACCEPTED_HEAD = NOT_CREATED
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
R25 = WAIT_ACCEPTED_DAILY_INPUT
```

---

## 13. Remote CI｜PASS_TRANSPARENT

GitHub 当前没有可用 workflow/check-run 成功证据。Codex 正确记录：

```text
CI_pass_claim = false
```

未把“没有 CI”包装成“CI PASS”。

---

## 14. 非阻断残余｜Signal DB-Level Hardening

`fep.observations.core_signal_contract_id` 当前 schema 是：

```text
text NOT NULL
```

没有 dedicated FK/semantic trigger。

当前 exact binding 由：

```text
metadata_binding.authority()
metadata_binding.verify_signal()
canonical fixture readback
TM/SM negative matrix
```

保证。

为什么本轮不阻断：

1. R1R1C 正式合同要求的是 canonical verifier。
2. 本轮默认 NO NEW MIGRATION。
3. 所有 production / real shadow / display / priority 权限仍关闭。
4. 205 条当前正式 engineering fixture 已 exact readback。

因此登记为：

```text
FEP_SIGNAL_DB_LEVEL_HARDENING =
OPEN_NONBLOCKING_PRODUCTION_GOVERNANCE_DEBT
```

在任何以下权限打开前必须关闭或正式豁免：

```text
FEP_PRODUCTION
REAL_DAILY_PRIORITY_SHADOW
MODEL_DISPLAY
PRIORITY_USE
```

---

## 15. Candidate Publication Test Timing｜PASS_WITH_NOTE

主要 runtime/metadata 代码在 `28de34e...` 后已完成测试。`6d06288...` 只修改 publication transport / seal evidence tooling，没有重跑 full test。

本轮接受为：

```text
NO_RETEST_AFTER_TRANSPORT_ONLY_CHANGE =
ACCEPTED_NONBLOCKING
```

但这不能泛化为“测试后任意代码变化都无需重测”。

---

## 16. E5 原始 Blocker 最终处置

```text
E5-B01 Canonical FEP Ledger
= CLOSED_PASS

E5-B02 Canonical Identity Binding
= CLOSED_PASS

E5-B03 Canonical Permission / Deployment
= CLOSED_PASS
```

---

## 17. E5 工程能力最终定位

当前正式完成：

```text
Historical ENTRY canonical projection engineering
E2 primary engineering source
E3/E4 diagnostic challenger binding
canonical prediction ledger
canonical permission/CAS
diagnostic API
synthetic Priority V2 linkage
rollback
protected-state isolation
```

未完成/未授权：

```text
real Daily model
new independent OOS
effectiveness promotion
Champion
MODEL_DISPLAY
PRIORITY_USE
real Daily Priority Shadow
FEP Production
```

所以只能叫：

```text
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED
```

---

## 18. 唯一最终状态

```text
V4_15E5_R1R1C_FINAL_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

V4_15E5_EXTERNAL_ACCEPTANCE =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED

R1R1B_M01 = CLOSED_PASS
R1R1B_M02 = CLOSED_PASS

E5_B01 = CLOSED_PASS
E5_B02 = CLOSED_PASS
E5_B03 = CLOSED_PASS

FEP_SIGNAL_DB_LEVEL_HARDENING =
OPEN_NONBLOCKING_PRODUCTION_GOVERNANCE_DEBT

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

NEXT =
V4_15E5_EXTERNAL_ACCEPTANCE_RECONCILIATION_AND_BRANCH_CLOSURE
```

外部工程验收完成。下一步只需归档本审计并完成 E5 branch closure，不需要再做 canonical integration 修复。

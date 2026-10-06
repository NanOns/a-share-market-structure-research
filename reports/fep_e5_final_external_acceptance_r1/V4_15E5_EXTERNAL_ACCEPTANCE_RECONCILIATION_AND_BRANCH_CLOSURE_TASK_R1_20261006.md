# V4-15E5｜External Acceptance Reconciliation & FEP Engineering Branch Closure Task R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 Final Closure  
> 任务性质：外部验收归档 / branch closure / 不含新功能开发  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`cf74b179fe847cb7260fb4b47c6e3be2c3a82206`  
> 外部验收：`V4_15E5_R1R1C_CANONICAL_METADATA_BINDING_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md`

## 0. 唯一目标

把已经独立通过的：

```text
V4_15E5 =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED
```

正式归档成 repository 内不可歧义的 closure state。

本轮不是修复轮，不是开发轮。

禁止修改：

```text
模型
prediction
migration
schema
target/signal semantics
CAS
API
Priority
production permission
```

---

## 1. 正式归档目录

创建：

```text
reports/fep_e5_final_external_acceptance_r1/
```

至少包含：

```text
V4_15E5_R1R1C_CANONICAL_METADATA_BINDING_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md
FINAL_EXTERNAL_ACCEPTANCE_READBACK.json
E5_BLOCKER_FINAL_DISPOSITION.json
FEP_ENGINEERING_BRANCH_CLOSURE.json
OPEN_PRODUCTION_GOVERNANCE_DEBT.json
PROTECTED_STATE_READBACK.json
COMPLETION_REPORT.md
FEP_E5_FINAL_CLOSURE_SEAL.json
```

---

## 2. External Acceptance Readback

`FINAL_EXTERNAL_ACCEPTANCE_READBACK.json` 必须 exact-bind：

```text
R1R1C baseline =
68b3d97d1f5d98a4ed6be87bca3ce8c81696e587

R1R1C implementation =
28de34e0765e5cacb810366e973cf9772249f366

R1R1C remote candidate =
6d06288c56bc632539262b246b0829ceee317690

remote evidence closure =
cf74b179fe847cb7260fb4b47c6e3be2c3a82206

external audit =
exact bytes + SHA256
```

必须明确：

```text
external_acceptance =
PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED
```

---

## 3. E5 Blocker Final Disposition

`E5_BLOCKER_FINAL_DISPOSITION.json`：

```text
E5_B01_CANONICAL_FEP_LEDGER =
CLOSED_PASS

E5_B02_CANONICAL_IDENTITY_BINDING =
CLOSED_PASS

E5_B03_CANONICAL_PERMISSION_DEPLOYMENT =
CLOSED_PASS

R1R1B_M01_TARGET_CONTRACT_EXACT_BINDING =
CLOSED_PASS

R1R1B_M02_CORE_SIGNAL_CONTRACT_EXACT_BINDING =
CLOSED_PASS
```

不得保留为：

```text
PASS_CANDIDATE
OPEN_BLOCKER
PENDING_EXTERNAL_AUDIT
```

---

## 4. FEP Engineering Branch Closure

`FEP_ENGINEERING_BRANCH_CLOSURE.json`：

```text
V4_15E1 = CLOSED
V4_15E2 = CLOSED_ENGINEERING_CAPABILITY_SCOPED
V4_15E3 = CLOSED_ENGINEERING_CAPABILITY_SCOPED
V4_15E4 = CLOSED_ENGINEERING_CAPABILITY_SCOPED
V4_15E5 = CLOSED_ENGINEERING_CAPABILITY_SCOPED

FEP_ENGINEERING_BRANCH =
COMPLETE_FOR_CURRENT_SCOPE
```

注意：

```text
COMPLETE_FOR_CURRENT_SCOPE
!=
FEP_PRODUCTION_READY
```

---

## 5. 权限必须保持关闭

Closure 后继续：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
DESCRIPTIVE_DISPLAY = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

不得因为 E5 final pass 自动升级任何 permission。

---

## 6. 开放生产治理债务

创建：

```text
OPEN_PRODUCTION_GOVERNANCE_DEBT.json
```

至少登记：

```text
debt_id =
FEP_SIGNAL_DB_LEVEL_HARDENING

status =
OPEN_NONBLOCKING_UNTIL_PRODUCTION_PERMISSION

current_state =
core_signal_contract_id exact-bound by canonical adapter/verifier,
but no dedicated FK/semantic DB trigger

must_close_before =
FEP_PRODUCTION
REAL_DAILY_PRIORITY_SHADOW
MODEL_DISPLAY
PRIORITY_USE

allowed_current_scope =
historical engineering fixture / diagnostic readback only
```

同时保留以下现实限制：

```text
52 existing repository debt nodes
real Daily model absent
new independent OOS absent
joint OOD limitations
calibration limitations
E4 no increment vs E2
```

不得因 E5 closure 删除。

---

## 7. Protected State

再次 readback：

```text
V4_STAGE_ACCEPTED_HEAD unchanged
V4_DATA_ACCEPTED_HEAD unchanged
V4_15_ACCEPTED_HEAD unchanged
V4_16_ACCEPTED_HEAD = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
PRIORITY_V1 unchanged
TDX untouched
```

本轮不能创建：

```text
FEP_PRODUCTION_HEAD
V4_16_ACCEPTED_HEAD
REAL_DAILY_HEAD
```

---

## 8. 不要求重跑 full regression

本轮只允许：

```text
archive external audit
write closure JSON/MD/seal
```

因此无需重新跑 545 targeted / 2904 scoped。

Closure seal 必须 exact-bind R1R1C 已接受：

```text
TARGETED_SUMMARY.json
SCOPED_REGRESSION_SUMMARY.json
METADATA_NEGATIVE_MATRIX.json
R1R1C_CANONICAL_VS_R1R1B_PARITY.json
PROTECTED_STATE_READBACK.json
```

如果任何 runtime/config/migration/test 被修改：

```text
STOP
OUT_OF_SCOPE
重新进入独立审计
```

---

## 9. Final Closure Seal

`FEP_E5_FINAL_CLOSURE_SEAL.json` 必须绑定：

```text
external audit bytes/digest
R1R1C candidate seal
remote candidate
remote closure receipt
E5 blocker disposition
branch closure
open production governance debt
protected state
```

并设置：

```text
external_acceptance = true
engineering_scope_closed = true
production_ready = false
```

---

## 10. 成功退出状态

唯一成功状态：

```text
V4_15E5_FINAL_CLOSURE =
PASS_EXTERNAL_ACCEPTANCE_ARCHIVED

FEP_ENGINEERING_BRANCH =
COMPLETE_FOR_CURRENT_SCOPE

E5_B01 = CLOSED_PASS
E5_B02 = CLOSED_PASS
E5_B03 = CLOSED_PASS

FEP_SIGNAL_DB_LEVEL_HARDENING =
OPEN_NONBLOCKING_PRODUCTION_GOVERNANCE_DEBT

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

production_ready = false

NEXT =
RETURN_TO_LATEST_PROJECT_MASTER_FOR_NEXT_AUTHORIZED_WORK
```

---

## 11. 禁止事项

禁止：

```text
创建新 migration
修改 028~032
修改 canonical_ledger
修改 metadata_binding
修改模型 artifact
修改 prediction
修改 permission
修改 CAS
修改 Priority
创建 Champion
打开 display/priority
打开 real Daily
打开 production
把 closure 解释成 effectiveness promotion
```

---

## 12. 最终原则

本轮只做：

```text
external acceptance
→ repository reconciliation
→ formal branch closure
```

不是：

```text
external acceptance
→ 自动生产上线
```

E5 关闭后，必须回到整个 V4 项目的最新 master / progress authority，再决定下一开发任务；不得从 FEP closure 自行推导 V4-16、FWP 或其他生产任务。

# Source Authority PASS 项正式化 + Registry R3 任务卡｜2026-10-01

**基线：** `1655f84d1a47faca43c281d66e7704f2fa56b1b8`  
**性质：** 只正式化本轮已获得独立外部结论的项目；不得借此关闭 A10/A12/DM01。

---

# 1. 本卡允许正式化的外部结论

## A08

独立外部结论：

```text
A08_EXTERNAL_ACCEPTANCE = PASS
```

Registry：

```text
AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
→ ACCEPTED
```

只关闭 hardening audit。

不得：

```text
开放 production
重写 V4-09 algorithm acceptance
把 current runtime 自动标 accepted
```

历史 accepted publication replay 与 current runtime acceptance 必须继续分离。

---

## A09

独立外部结论：

```text
A09_EXTERNAL_ACCEPTANCE = PASS
```

Registry：

```text
AUD-V4-09-DB-CONSUMER-IDENTITY-N02
→ ACCEPTED
```

Migration 025 可记录为：

```text
accepted future schema hardening
```

但不等于：

```text
production DB 已部署
```

真实 deployment 仍走独立 deployment gate。

---

## A11

独立外部结论：

```text
A11_EXTERNAL_ACCEPTANCE =
PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE
```

这不是：

```text
historical authority resolved
```

正式记录应为：

```text
historical stable IDs / current business values preserved

historical pre-capture:
security type / lifecycle / listing-anchor source authority
= RECONSTRUCTED_CORRECTED / PROVIDER_RECONSTRUCTED_FACT
unless independently official-confirmed

HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED

go-forward official observed identity model
= preserved accepted
```

SH.600018：

```text
retain current stable identity anchor
no mass rekey
```

A11 audit 本身可以关闭；
“历史 legal lifecycle/type 已成为 local-TDX formal truth”不得建立。

---

# 2. A10 / A12 / A01 必须继续 OPEN

Registry R3：

```text
A10:
status = OPEN
implementation_status = BLOCKED_R2_OWNER_ACCEPTANCE_GATE
external_acceptance = BLOCKED

A12:
status = OPEN
implementation_status = BLOCKED_R2_REAL_DATED_OWNER_SEMANTICS
external_acceptance = BLOCKED

A01:
status = OPEN
implementation_status =
PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED

depends_on =
A10-R2 + A12-R2 external acceptance
```

不得因 A08/A09/A11 formalize 而关闭它们。

---

# 3. Registry R3

新增：

```text
reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json
```

不得覆盖：

```text
R1
R2
```

R3 必须绑定：

```text
本轮独立外部审计文档
审计文档 sha256
审计 HEAD
```

每个 status transition 记录：

```text
previous_status
new_status
acceptance_scope
capability_limitations
external_authority
evidence bindings
remaining dependencies
```

---

# 4. A11 正式 Contract Amendment

新增 versioned amendment，例如：

```text
V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1
```

至少包含：

```text
business identity bytes unchanged = true
security_id unchanged = true
go-forward official identity authority unchanged = true

historical provenance amendment:
  provider facts = RECONSTRUCTED_CORRECTED
  provider observation time != historical fact date
  not AS_RECORDED
  not local-TDX legal lifecycle authority

capability:
  HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED
```

---

# 5. A11 下游处理

因为已证明：

```text
canonical old sha == candidate sha
identity_rows_changed = 0
security_ids_renumbered = 0
V4-02/03/04/05/07/08/09 business diff = 0
```

所以：

```text
不重跑业务 stage
```

只追加：

```text
provenance / capability amendment
```

---

# 6. A08 正式化

必须绑定当前 external audit 结论，并保留：

```text
historical validation scope =
ACCEPTED_PUBLICATION_HISTORY_ONLY

current runtime =
NOT AUTO ACCEPTED
```

不得改：

```text
V4_09_STOCK_PREWATCH accepted artifact
logical digest
historical implementation binding
```

允许新增：

```text
V4_09_N01_HARDENING_ACCEPTED_RECORD_R1
```

---

# 7. A09 正式化

允许新增：

```text
V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1
```

必须绑定：

```text
migration 025 sha256
rollback 025 sha256
disposable PostgreSQL oracle
legacy exact readback
rollback exact evidence
```

不得修改：

```text
migration 021
022
023
024
```

---

# 8. Accepted Heads

A08/A09/A11 本轮正式化原则：

```text
不需要改变业务 Accepted Head
```

可以增加：

```text
accepted hardening sidecar record
audit acceptance record
contract amendment
registry binding
```

但必须保证以下业务 head bytes 不变：

```text
V4_01_ACCEPTED_HEAD
V4_09_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
```

如需要在 global governance 中记录 hardening acceptance，
必须用独立 metadata namespace，
不得改变历史 business artifact identity。

---

# 9. A10/A12 候选不得被错误纳入 accepted owner registry

本卡执行时：

```text
A10-R1 generic governance candidate
A12-R1 status/ST owner candidate
```

均不得登记成：

```text
EXTERNALLY_ACCEPTED OWNER
```

A12 owner registry 必须等 A10-R2/A12-R2 独立验收通过后的新任务。

---

# 10. Permission

全程：

```text
production = false
shadow = false
focus_cutover = false
```

不得修改。

---

# 11. Clean Regression

执行后至少检查：

```text
A08 accepted historical replay
A09 DB migration/rollback tests
A11 identity old/new equivalence
Registry R3 exact status
A10/A12/A01 remain open
accepted business heads byte-identical
```

---

# 12. 验收门

```text
R3-G01 A08 accepted scope exact
R3-G02 A09 accepted scope exact
R3-G03 A11 Result C limitation exact
R3-G04 A11 business bytes unchanged
R3-G05 no A10 closure
R3-G06 no A12 closure
R3-G07 no A01 final closure
R3-G08 historical accepted business heads unchanged
R3-G09 Registry R1/R2 preserved
R3-G10 new R3 exact readback
R3-G11 A12 candidate absent from accepted owner registry
R3-G12 permissions false
R3-G13 clean regression
```

Codex 允许的最终状态：

```text
SOURCE_AUTHORITY_REGISTRY_R3_FORMALIZATION_CANDIDATE_READY_FOR_EXTERNAL_CONFIRMATION
```

不得自行修改本轮外部判定。

# A10-R2 外部接受正式化 + A12-R2 入场任务卡｜2026-10-01

**前置外部结论：**

```text
REGISTRY_R3_EXTERNAL_CONFIRMATION = PASS

A10_R2_EXTERNAL_ACCEPTANCE =
PASS_INFRASTRUCTURE_SCOPE
```

**审计 HEAD：**

```text
699d3503d2d8ddbd37997441eec59308aec1990f
```

---

# 1. 本轮唯一顺序

必须：

```text
Step 1  正式记录 Registry R3 external confirmation
Step 2  正式记录 A10-R2 infrastructure-scope external acceptance
Step 3  更新 remediation registry（新版本，禁止覆盖 R3）
Step 4  明确 A10 global owner population 仍未完成
Step 5  授权 A12-R2 implementation entry
Step 6  STOP
```

禁止在本卡里执行：

```text
A12-R2 全历史修复
A12 owner promotion
DM01 all-nine
Data Head promotion
```

A12-R2 主任务仍使用既有：

```text
V4_A12_R2_REAL_DATED_STATUS_ST_AUTHORITY_REPAIR_TASK_20261001.md
```

---

# 2. Registry 新版本

新增：

```text
reports/audits/
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R4.json
```

不得覆盖：

```text
R1
R2
R3
```

---

# 3. A10 状态转换

A10 从：

```text
OPEN
BLOCKED_R2_OWNER_ACCEPTANCE_GATE
```

变为：

```text
ACCEPTED_INFRASTRUCTURE_SCOPE
```

必须记录：

```text
external_acceptance =
PASS_INFRASTRUCTURE_SCOPE

formal_consumer_authorization =
false
```

这里 `formal_consumer_authorization=false` 是正确的，因为 A10 是治理机制，不是业务字段 owner。

---

# 4. A10 接受范围

Registry R4 必须明确：

```text
accepted:
- owner registry schema
- governance trust root
- exact owner hash verification
- external acceptance verification
- formal consumer authorization verification
- consumer scope verification
- historical mode verification
- effective target scope verification
- supplemental promotion guard
- pending owner rejection
```

---

# 5. A10 不接受范围

同时写：

```text
not_accepted:
- no real source owner was authorized by A10-R2
- existing formal owners have not been globally migrated
- A12 owner is not accepted
- DM01 all-nine is not accepted
- production/shadow/focus remain false
```

---

# 6. Accepted owner registry 当前保持空

当前：

```text
data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json

owners = []
```

本卡不得为了让数字“好看”直接塞入 owner。

继续：

```text
owners = []
```

是允许的。

新增状态说明：

```text
OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS =
DEFERRED_BEFORE_GLOBAL_MANDATORY_ADOPTION
```

---

# 7. 为什么暂时不 bootstrap 旧 owner

以下字段不能用一个批量脚本粗暴接受：

```text
OHLC / Amount / Volume
QFQ
Security Identity
Special Phase
Sector Membership
```

因为它们各自有不同：

```text
accepted scope
degraded scope
go-forward vs historical scope
PIT semantics
capability limitations
```

所以本卡只记录 deferred gate。

禁止：

```text
bulk mark all historical owners accepted
```

---

# 8. A12-R2 Entry

Registry R4 将 A12 更新为：

```text
A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED
```

但：

```text
status = OPEN
external_acceptance = BLOCKED / PENDING
formal_consumer_authorization = false
```

---

# 9. A12-R2 必须使用 A10-R2 gate

A12 candidate owner 必须兼容：

```text
SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V1
SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V1
```

但开发阶段：

```text
owner candidate
不得写入 owners[]
```

只能形成：

```text
owner acceptance candidate
role binding candidate
external audit evidence
```

---

# 10. A12-R2 最终候选允许状态

A12 执行完成后只允许：

```text
A12_R2_REAL_DATED_OWNER_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止：

```text
A12_OWNER_ACCEPTED
A12_OWNER_REGISTERED
```

---

# 11. DM01 状态继续保持

```text
DM01_A01 =
PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED
```

依赖：

```text
A12-R2 external acceptance
+
A12 owner registration
```

A10-R2 PASS 只满足其中一个前置条件。

---

# 12. Accepted Head 保护

不得修改：

```text
V4_01_ACCEPTED_HEAD
V4_02_ACCEPTED_HEAD
V4_04_ACCEPTED_HEAD
V4_05_ACCEPTED_HEAD
V4_09_ACCEPTED_HEAD
V4_10_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
```

---

# 13. External Acceptance Record

新增：

```text
reports/audits/
A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1.json
```

必须绑定：

```text
independent audit document
audit document sha256
audited HEAD = 699d3503d2d8ddbd37997441eec59308aec1990f
A10 R2 candidate evidence
A10 clean checkout
A10 targeted tests
A10 no-symbol
```

并明确：

```text
scope = INFRASTRUCTURE_ONLY
```

---

# 14. Registry R3 Confirmation Record

新增：

```text
reports/audits/
SOURCE_AUTHORITY_REGISTRY_R3_EXTERNAL_CONFIRMATION_R1.json
```

绑定：

```text
Registry R3 exact SHA
A08 accepted record
A09 accepted record
A11 amendment
independent audit
```

---

# 15. Permissions

继续：

```text
production = false
shadow = false
focus_cutover = false
```

---

# 16. Clean Regression

本卡正式化后至少复查：

```text
Registry R4 exact status
R1/R2/R3 preserved
A08/A09/A11 status preserved
A10 accepted only infrastructure scope
owners[] still empty
A12 still not accepted
DM01 still blocked
business Accepted Heads unchanged
permissions false
```

---

# 17. Codex 最终允许状态

```text
A10_R2_EXTERNAL_ACCEPTANCE_FORMALIZED
A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED
```

禁止：

```text
A12_ACCEPTED
DM01_ACCEPTED
DATA_HEAD_PROMOTED
PRODUCTION_READY
```

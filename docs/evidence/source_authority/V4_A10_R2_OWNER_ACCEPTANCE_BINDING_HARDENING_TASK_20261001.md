# A10-R2｜Global Field Authority Owner Acceptance Binding Hardening｜2026-10-01

**Work Package：** `WP-A10-R2-OWNER-ACCEPTANCE-BINDING`  
**基线：** `1655f84d1a47faca43c281d66e7704f2fa56b1b8`  
**优先级：** P0 Governance  
**性质：** 补 A10 通用治理门缺失的 owner acceptance binding；不得修改任何业务算法。

---

# 1. Blocker

当前 `evaluate_consumer_gate()` 可以把：

```text
role = FIELD_AUTHORITY
enabled = true
consumer declared
availability = AVAILABLE
```

直接当 authority。

但它不验证：

```text
owner_contract_id
是否：
- externally accepted
- formal consumer authorized
- hash-bound
- registered in accepted authority registry/global head
```

当前 A10 config 已声明：

```text
LOCAL_DATED_TRADING_STATUS_V2
LOCAL_DATED_ST_IDENTITY_V2
```

为 FIELD_AUTHORITY / enabled=true，
而 A12 仍未 external accepted。

DM01 私有 `require_external_a12_owner_for_final_candidate()` 已正确补门，
但通用 A10 runtime 仍缺。

---

# 2. 修复目标

建立一个统一、版本化、机器可验证的：

```text
SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V1
```

每个 owner 至少包含：

```text
owner_contract_id
field_id
artifact path
artifact sha256
external_acceptance
formal_consumer_authorization
allowed_consumers
effective_scope
historical_mode
accepted_at
supersedes
```

---

# 3. evaluate_consumer_gate 新要求

当：

```text
role in [CORE_AUTHORITY, FIELD_AUTHORITY]
```

且 consumer 要正式使用时，必须验证：

```text
owner binding exists
hash exact
owner contract id exact
external_acceptance == EXTERNALLY_ACCEPTED
formal_consumer_authorization == true
consumer 在 owner allowed_consumers
owner scope 覆盖 target / mode
```

否则统一 fail-closed：

```text
AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED
```

不得返回 formal authority PASS。

---

# 4. Pending owner 状态

A12 尚未 external accepted 时：

```text
TRADING_STATUS
ISST
```

A10 rule 必须处于：

```text
authority_status = PENDING_EXTERNAL_ACCEPTANCE
```

或：

```text
enabled_for_formal_consumer = false
```

不能仅凭 config 的 `enabled=true` 被 generic gate 消费。

可以继续：

```text
diagnostic
candidate replay
external audit
```

---

# 5. Supplemental promotion

必须 machine-enforce：

```text
SUPPLEMENTAL_CROSSCHECK
不能通过修改单个 consumer 参数就变成 required field authority
```

Promotion 必须同时存在：

```text
new versioned owner contract
external acceptance
accepted owner registry entry
new role binding
```

---

# 6. Owner Registry 与 Global Head 的关系

建议不要把业务 Stage Head 与 Source Authority owner 混在同一个隐式字段里。

允许：

```text
独立 owner registry
+
global head exact binding
```

例如：

```text
data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json
```

Global head 只保存：

```text
registry path
registry sha256
registry version
```

不得把候选 owner 自己声明为 accepted。

---

# 7. 必须新增 negative tests

至少：

```text
self_declared_field_authority_without_owner_registry -> reject

hash_valid_but_external_acceptance_null -> reject

external_acceptance_true_but_formal_consumer_authorization_false -> reject

owner_registered_for_other_field -> reject

owner_registered_for_other_consumer -> reject

owner_binding_hash_mismatch -> reject

owner_scope_not_cover_target -> reject

supplemental_self_promotion -> reject

registry_binding_not_in_global_authority_head -> reject
```

Positive：

```text
externally accepted
+ exact registered owner
+ matching field
+ matching consumer
+ matching scope
→ PASS
```

---

# 8. 与 A12 的关系

A10-R2 不决定：

```text
谁是 ST / Trading Status owner
```

它只决定：

> 任何 owner 在外部接受前都不能进入 formal consumer path。

A12-R2 完成后再向 owner registry 写正式 entry。

当前 A12-R1：

```text
external_acceptance = null
formal_consumer_authorization = false
```

必须继续被通用 A10-R2 gate 拒绝。

---

# 9. 与 DM01 的关系

DM01 当前已有私有 gate：

```text
require_external_a12_owner_for_final_candidate()
```

A10-R2 完成后：

```text
DM01 私有 gate
+
全局 owner registry gate
```

应逻辑一致。

可以保留 DM01 二次防线，
但不得出现：

```text
全局 gate PASS
DM01 gate FAIL
```

或反向不一致。

---

# 10. Scanner 更新

A10 scanner 必须增加新规则：

```text
FIELD_AUTHORITY_WITHOUT_ACCEPTED_OWNER_BINDING
FORMAL_CONSUMER_USING_PENDING_OWNER
SUPPLEMENTAL_ROLE_PROMOTED_WITHOUT_ACCEPTED_OWNER
```

至少把当前：

```text
TRADING_STATUS
ISST
```

识别成：

```text
PENDING_OWNER
```

而不是正式 accepted authority。

---

# 11. Accepted Head

禁止修改：

```text
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
任意 V4-xx Accepted Head
```

A10-R2 是治理 hardening，不是业务结果 promotion。

---

# 12. Clean Regression

必须复跑：

```text
A10 tests
A12 source-boundary tests
DM01 R2 gate tests
A08/A09 不相关 accepted replay smoke
global regression
```

不得只跑新增 unit tests。

---

# 13. 验收

```text
A10R2-G01 accepted owner registry schema
A10R2-G02 owner hash binding
A10R2-G03 external acceptance gate
A10R2-G04 formal consumer authorization gate
A10R2-G05 scope gate
A10R2-G06 supplemental self-promotion rejected
A10R2-G07 A12 pending owner rejected
A10R2-G08 synthetic externally accepted owner positive
A10R2-G09 DM01 private/global gates consistent
A10R2-G10 existing historical-mode tests preserved
A10R2-G11 repo scan updated
A10R2-G12 accepted heads unchanged
A10R2-G13 clean detached regression
A10R2-G14 independent external reaudit
```

Codex 最终只能声称：

```text
A10_R2_OWNER_ACCEPTANCE_BINDING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不得自行写：

```text
A10_ACCEPTED
A12_OWNER_ACCEPTED
PRODUCTION_READY
```

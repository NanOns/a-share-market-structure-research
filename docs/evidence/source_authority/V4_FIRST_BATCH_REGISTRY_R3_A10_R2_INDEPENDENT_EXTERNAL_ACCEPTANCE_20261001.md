# 第一批独立外部验收｜Registry R3 + A10-R2｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `699d3503d2d8ddbd37997441eec59308aec1990f`  
**前一审计基线：** `1655f84d1a47faca43c281d66e7704f2fa56b1b8`  
**本批新增提交：** 5

## 1. 唯一总状态

```text
FIRST_BATCH_EXTERNAL_ACCEPTANCE = PASS_WITH_SCOPE_LIMITS

REGISTRY_R3_FORMALIZATION = PASS

A10_R2_OWNER_ACCEPTANCE_GATE =
PASS_INFRASTRUCTURE_SCOPE

A10_R2_GLOBAL_OWNER_POPULATION =
NOT_YET_MIGRATED / DEFERRED

A12_R2_ENTRY =
AUTHORIZED

DM01_A01_R3 =
STILL_BLOCKED
```

Registry R3 可以正式确认。A10-R2 成功修复了“配置自称 FIELD_AUTHORITY 即可进入 formal consumer”的漏洞。

A10-R2 本轮验收的是 **owner acceptance enforcement infrastructure**，不是“现有所有历史 owner 已经迁入新 registry”。

当前 `accepted owner registry` 中真实 `owners=[]` 是本任务范围内的有意 fail-closed 状态，不是 A10-R2 代码失效。

但在 A10 成为全系统 mandatory gate 或进入 Production/Shadow 之前，既有合法 owner 仍需要逐字段、逐 scope 正式注册。

A12-R2 可以进入，因为它下一步要做的正是生成 Status/ST owner candidate，并验证与 A10-R2 gate 的兼容性。

## 2. Git 变更范围

从 `1655f84d...` 到 `699d3503...` 共 5 个提交：

```text
5f10f4b  Formalize externally audited A08 A09 A11 scopes in Registry R3
f268332  Bind unchanged workspace and Git historical head byte representations separately
ddeaee2  Seal Registry R3 formalization with clean regression evidence
fa07b6f  Require exact external owner acceptance for formal source authority consumers
699d350  Seal A10 R2 owner acceptance candidate with clean regression and pending reaudit gate
```

本批没有修改任何业务 Accepted Head 文件。

## 3. Registry R3｜PASS

A08 正式化为：

```text
status = ACCEPTED
external_acceptance = PASS
scope = REPAIR_FREEZE_AUTHORITY_HARDENING_AUDIT_ONLY
limitation = CURRENT_RUNTIME_NOT_AUTO_ACCEPTED
```

A09 正式化为：

```text
status = ACCEPTED
external_acceptance = PASS
scope = ACCEPTED_FUTURE_SCHEMA_HARDENING
limitation = PRODUCTION_DEPLOYMENT_NOT_AUTHORIZED
```

A11 正式化为：

```text
status = ACCEPTED
external_acceptance =
PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE
```

并保留：

```text
HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED
```

正式 amendment `V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1` 记录：

```text
business_identity_bytes_unchanged = true
security_id_unchanged = true
go_forward official authority unchanged = true
historical provenance =
PROVIDER_RECONSTRUCTED_FACT / RECONSTRUCTED_CORRECTED
AS_RECORDED = false
```

SH.600018 继续：

```text
RETAIN_CURRENT_STABLE_IDENTITY_ANCHOR
```

A10/A12/DM01 没有被误关：

```text
A10 = OPEN / BLOCKED_R2_OWNER_ACCEPTANCE_GATE
A12 = OPEN / BLOCKED_R2_REAL_DATED_OWNER_SEMANTICS
A01 = OPEN / PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED
```

Registry R3 裁决：

```text
PASS
```

## 4. Accepted Head 保护｜PASS

本批 compare 中没有业务 Accepted Head 被修改。

关键 Head 保持：

```text
V4_01_ACCEPTED_HEAD
b8ea5b8091629d116c860f9bf6a1a398301d75be16af7b08ff526fba9329bf6b

V4_02_ACCEPTED_HEAD
da318a1f82a03f13930af7858ca1640fadbdaedbee85e27d47f9c869c2d6b595

V4_04_ACCEPTED_HEAD
1d8a0611dc80e3c3bea86175f75096eeac53f04af126137892cbc8a14dc0bd7a

V4_05_ACCEPTED_HEAD
fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb

V4_09_ACCEPTED_HEAD
641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d

V4_10_ACCEPTED_HEAD
ad9fc4643652feb3684223817f2e9c300167d128e2e8a07179e86f65094fd1e1

V4_DATA_ACCEPTED_HEAD
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0
```

Data Head 仍为 `2026-09-24`。

## 5. CRLF / Git byte representation｜PASS

两个文件存在此前已经存在的 Git LF / workspace CRLF 表示差异：

```text
V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json
V4_03_ACCEPTED_HEAD.json
```

Codex 没有把这种 representation difference 误判为本批业务修改，而是同时保存 workspace sha、git baseline sha，并标记：

```text
representation_difference = PRE_EXISTING_CRLF_LF_ONLY
```

compare 未显示这些业务 head 被修改。

裁决：

```text
PASS
```

## 6. Registry R3 Clean Regression

```text
1336 passed
2 skipped
0 failed
0 errors
1 existing authorized deselect
```

使用 disposable PostgreSQL，没有使用 production/configured DB。

No-symbol：

```text
PASS
```

## 7. A10-R2｜核心漏洞已修复

新增：

```text
SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_V1
SOURCE_AUTHORITY_GLOBAL_GOVERNANCE_HEAD_V1
```

formal authority proof 现在固定经过：

```text
global governance head
→ accepted owner registry
→ exact owner entry
→ exact owner artifact
→ exact role binding
```

consumer 不能把临时 registry、candidate head 或 business stage head 当 trust root。

## 8. A10-R2 exact owner gate｜PASS

Formal authority 必须同时验证：

```text
owner_contract_id exact
field_id exact
artifact hash exact
external_acceptance == EXTERNALLY_ACCEPTED
formal_consumer_authorization == true
consumer in scope
historical mode exact
target date in effective scope
source role exact
role_binding_id exact
owner artifact declarations == registry declarations
```

任何一项失败统一：

```text
AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED
```

并保持旧 Core value，不授权 formal authority。

## 9. Supplemental self-promotion｜PASS

BaoStock supplemental 不能只通过改 consumer rule 自我升级成 FIELD_AUTHORITY。

Promotion 必须有：

```text
new versioned owner contract
new accepted registry entry
exact role binding
external acceptance
```

negative vectors 已覆盖。

## 10. A12 pending owner 被真实拒绝｜PASS

当前 A12 的：

```text
TRADING_STATUS
ISST
```

在 R2 config 中：

```text
authority_status = PENDING_EXTERNAL_ACCEPTANCE
enabled_for_formal_consumer = false
```

当前 registry：

```text
owners = []
```

Generic A10 gate 对这两个字段真实返回：

```text
AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED
formal_authority_authorized = false
```

DM01 private gate 同样返回：

```text
A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED
```

两套 gate 一致。

## 11. Synthetic positive 仅用于机制证明｜PASS

A10-R2 正例使用 synthetic externally-accepted owner fixture。

Evidence 明确：

```text
positive_authorization_scope =
SYNTHETIC_FIXTURE_ONLY_NO_REAL_OWNER_ACCEPTANCE
```

没有把 synthetic fixture 当真实 owner。

## 12. 当前 owners=[] 是否构成失败？

结论：

```text
NO
```

本任务卡没有授权真实 owner registration。

它的职责是建立：

> 只有外部接受 owner 才能进入 formal consumer 的信任门。

当前：

```text
owners=[]
pending_owners=[...]
```

属于保守且正确的 infrastructure candidate。

新的 governance head 属于：

```text
INDEPENDENT_SOURCE_AUTHORITY_METADATA_NAMESPACE
business_head_promotion = false
```

因此没有追溯性推翻旧 Accepted Head。

## 13. 但存在一个明确后续边界

A10-R2 PASS 不等于：

```text
GLOBAL_AUTHORITY_REGISTRY_FULLY_POPULATED
```

当前这些既有 authority 尚未迁入新 registry：

```text
TDX OHLC / Volume / Amount
GBBQ QFQ
Security Identity
Special Phase
Sector Membership
```

而且它们各自有不同的 accepted scope / degraded scope / PIT 限制。

因此：

```text
A10_R2_GATE_INFRASTRUCTURE = ACCEPTED
```

但：

```text
A10_GLOBAL_MANDATORY_ADOPTION = NOT_AUTHORIZED_YET
```

在 Production / Shadow 或所有旧 consumer 强制迁入 A10 gate 前，需要逐字段 owner bootstrap。

这不是 A10-R2 当前验收 blocker，但属于后续正式集成 gate。

## 14. A10-R2 Clean Regression

最终：

```text
1375 passed
2 skipped
0 failed
0 errors
1 existing authorized deselect
```

Targeted owner-gate：

```text
107 tests
0 failures
0 errors
0 skipped
```

保护：

```text
accepted business heads unchanged = true
production = false
shadow = false
focus_cutover = false
```

## 15. A10-R2 独立外部裁决

```text
A10_R2_EXTERNAL_ACCEPTANCE =
PASS_INFRASTRUCTURE_SCOPE
```

接受：

```text
owner registry schema
global governance head trust root
exact owner hash binding
external acceptance gate
formal consumer authorization gate
consumer scope gate
historical mode gate
target-date effective scope gate
supplemental self-promotion rejection
A12 pending owner rejection
DM01/global gate consistency
```

不接受：

```text
任何真实 source owner 自动获准
现有全部 authority 已迁入 registry
A12 owner 已接受
DM01 all-nine 已接受
production/shadow/cutover
```

## 16. 第一批最终状态

```text
REGISTRY_R3_EXTERNAL_CONFIRMATION = PASS

A08 = KEEP_ACCEPTED
A09 = KEEP_ACCEPTED
A11 = KEEP_ACCEPTED_RESULT_C

A10_R2 =
EXTERNALLY_ACCEPTED_INFRASTRUCTURE_SCOPE

A12_R2_ENTRY =
AUTHORIZED

A12_OWNER =
NOT_ACCEPTED

DM01_A01_R3 =
NOT_AUTHORIZED_YET

V4_DATA_ACCEPTED_HEAD =
KEEP_2026_09_24

PRODUCTION = FALSE
SHADOW = FALSE
FOCUS_CUTOVER = FALSE
```

## 17. 下一步

先把 A10-R2 的独立外部接受正式写入 Registry / governance metadata，然后执行 A12-R2。

A12-R2 可以开始真实 Status/ST 样本矩阵、Path A/Path B source semantics 决策、全历史 rebuild、V4-04 真回放及 V4-03/05/07/08/09 cascade。

但 A12 不能自行把自己写入 `owners[]`。

必须等下一轮独立外部验收通过后，再执行 owner registration。

DM01 A01-R3 继续等待。

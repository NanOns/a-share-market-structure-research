# DM01 A01-R3 外部接受正式化 + V4 Data Head Promotion 任务卡｜2026-10-01

**Work Package：** `WP-DM01-A01-R3-EXTERNAL-ACCEPTANCE-AND-DATA-HEAD-PROMOTION`  
**基线 HEAD：** `ac811e210c66b7ee9446086659dee169ee0f81a8`  
**优先级：** P0 Governance / Data Head  
**外部验收依据：** `V4_DM01_A01_R3_AND_A13_FORMALIZATION_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`

## 1. 前置外部结论

已通过：

```text
A10/A12-R3 source authority formalization
A13 external acceptance formalization
DM01 A01-R3 real continuous all-nine chain

2026-09-24 Accepted
→ 2026-09-28
→ 2026-09-29
→ 2026-09-30
```

正式授权：

```text
V4_DATA_ACCEPTED_HEAD → 2026-09-30
```

不授权：

```text
V4_STAGE_ACCEPTED_HEAD movement
production
shadow
focus cutover
```

## 2. 将真正外部验收文件加入仓库

新增：

```text
docs/evidence/source_authority/
V4_DM01_A01_R3_AND_A13_FORMALIZATION_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md
```

记录 exact：

```text
bytes
sha256
audited_head =
ac811e210c66b7ee9446086659dee169ee0f81a8
```

禁止以本任务卡代替 external authority。

## 3. DM01 External Acceptance Record

新增：

```text
reports/audits/
DM01_A01_R3_EXTERNAL_ACCEPTANCE_RECORD_R1.json
```

至少绑定：

```text
external audit exact document/hash
audited HEAD
A10/A12 Registry R3
Governance Head R3
9/28 Candidate R3
9/29 Candidate R3
9/30 Candidate R3
Continuous Chain Postcheck R3
Determinism R3
Atomic Failure Probes R3
Final Version Business Parity
Metadata Durability R2
Source Dependency Durability
Clean Checkout
No-Symbol Scan
Final Handoff R3
```

状态：

```text
external_acceptance =
EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN

accepted_through =
2026-09-30
```

## 4. 创建 Accepted Chain Manifest

新增不可变 artifact，例如：

```text
data/v4/
DM01_A01_R3_ACCEPTED_CHAIN_20260924_20260930_R1.json
```

Anchor：

```text
2026-09-24
V4_DATA_ACCEPTED_HEAD
sha256 =
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0
```

Node 1：

```text
trade_date = 2026-09-28
parent = old 9/24 Data Head
candidate =
b338caaea8f9e41228a62add7e987d946f4dc9a5a5297dbe02e9ee73df525313
```

Node 2：

```text
trade_date = 2026-09-29
parent =
b338caaea8f9e41228a62add7e987d946f4dc9a5a5297dbe02e9ee73df525313
candidate =
0a67e7211572a7057c50ab27e397c3e093f88c24732e8c7be7bdda92952ca1bf
```

Node 3：

```text
trade_date = 2026-09-30
parent =
0a67e7211572a7057c50ab27e397c3e093f88c24732e8c7be7bdda92952ca1bf
candidate =
e4ba1fb6d4690b869f98ffc45a8d576a641ef2e9a852a9db97aedd19e043bc81
```

每个 node 同时绑定九组件 logical digest / artifact digest / source instances。

## 5. Promotion 前 Registry R10 清理

R9 不覆盖。新增：

```text
reports/audits/
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json
```

A12 current 必须统一为：

```text
status = ACCEPTED_SOURCE_AUTHORITY_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
historical_path_b = EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY
daily_producer_authority = EXTERNALLY_ACCEPTED
observed_daily_producer_acceptance =
EXTERNALLY_ACCEPTED_PRODUCER_SOURCE_INSTANCE_MODEL
capability_limitations = []
```

以下旧值不得继续作为 current：

```text
NO_FUNCTIONAL_CLOSURE
EXTERNAL_REPAIR_ACCEPTANCE_REQUIRED
PENDING
READY_FOR_EXTERNAL_REAUDIT
OPEN/PENDING transition
```

它们只能放在 `prior_transition/history`。

## 6. Registry R10｜DM01

DM01 更新：

```text
status = ACCEPTED

implementation_status =
EXTERNAL_ACCEPTANCE_PASS_REAL_CONTINUOUS_CHAIN

external_acceptance =
PASS_REAL_INCREMENTAL_CHAIN_20260928_20260930

formal_consumer_authorization =
true for accepted DM01 chain scope

dm01_all_nine_accepted = true
accepted_through = 2026-09-30
remaining_external_gate = null
```

保留：

```text
production_gate = true
```

DM01 acceptance 不等于 Production。

## 7. Registry R10｜A13

A13：

```text
status = ACCEPTED
external_acceptance =
PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT
formalization_external_reaudit = PASS
V4_08_HEAD_ACTION = KEEP
```

旧 `external_acceptance=PENDING` 仅保存在历史 evidence。

## 8. Promotion 前 Preflight

独立重读：

```text
old V4_DATA_ACCEPTED_HEAD
Accepted Chain Manifest
3 final R3 candidates
Source Authority Governance Head R3
Registry R3
DM01 external acceptance record
Registry R10
```

确认：

```text
all hashes exact
all parent pointers exact
all 9 components each day complete
no session skipped
external audit exact
old Stage Head exact unchanged
```

任一失败：

```text
STOP
禁止 Data Head promotion
```

## 9. Archive 旧 Data Head

覆盖 movable pointer 前，将旧：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

exact bytes 归档成不可变 parent archive。

至少记录：

```text
bytes
sha256 =
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0
accepted_trade_date = 2026-09-24
```

禁止只记录解析后 JSON。

## 10. 原子推进 Data Head

最终：

```text
accepted_trade_date = 2026-09-30
```

Data Head 必须绑定：

```text
accepted chain manifest
final 9/30 candidate
DM01 external acceptance record
source authority governance R3
calendar
identity
parent archive
```

如现有 `V4_DATA_ACCEPTED_HEAD_V1` schema 不能表达 accepted chain，则创建 versioned V2 contract，不要塞未治理字段。

## 11. Component Permission 必须来自 9/30 final candidate

保持：

```text
RAW_DAILY       FULL_PASS
IDENTITY        FULL_PASS
TRADING_STATUS  FULL_PASS
ISST            FULL_PASS
ADJUSTED_DAILY  DEGRADED_PASS
PERIOD_RAW      FULL_PASS
PERIOD_ADJUSTED DEGRADED_PASS
PRICE_LIMIT     DEGRADED_PASS
SPECIAL_PHASE   FULL_PASS
```

具体 reason/capability 从 final R3 receipt 读取，不允许手工猜，也不允许因为 row quality READY 就升级 FULL_PASS。

## 12. 不移动 Stage Head

`V4_STAGE_ACCEPTED_HEAD` 必须 byte-identical。

当前：

```text
V4_00_TO_V4_10_ACCEPTED
```

保持。

Data Head promotion != Stage acceptance。

## 13. V4-08 / V4-09 不自动重建

本任务只移动 Data Head。

禁止自动：

```text
re-accept V4-08
re-accept V4-09
```

后续各 stage 是否消费新 Data Head，按各自合同独立执行。

## 14. Owner Registry Bootstrap 仍 OPEN

保持：

```text
OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS = OPEN
```

Scope：

```text
OHLC / Amount / Volume
QFQ
Security Identity
Special Phase
Sector Membership
```

它是 global mandatory adoption / production/shadow 前置，不阻塞当前 Data Head promotion。

## 15. Promotion Receipt

新增：

```text
reports/v4_joint/
DM01_A01_R3_DATA_HEAD_PROMOTION_RECEIPT_R1.json
```

至少记录：

```text
old data head exact archive
new data head
accepted chain
external acceptance
promotion timestamp
stage head before/after exact
production/shadow/focus before/after false
```

## 16. Promotion Independent Readback

从新 checkout 读取：

```text
V4_DATA_ACCEPTED_HEAD
```

确认：

```text
accepted_trade_date = 2026-09-30
chain manifest hash exact
final candidate hash exact
old parent archive exact
Stage Head unchanged
```

并对最终 9/30 九组件做 source-binding readback。

## 17. Clean Regression

至少覆盖：

```text
A10/A12
DM01
V4-01
V4-02
V4-04
V4-07
V4-08
V4-09
A13
no-symbol
```

使用 disposable PostgreSQL。

## 18. Permission

始终：

```text
production = false
shadow = false
focus = false
```

本任务不得开放。

## 19. 完成状态

Codex 完成后允许：

```text
DM01_A01_R3_EXTERNAL_ACCEPTANCE_FORMALIZED = PASS
V4_DATA_ACCEPTED_HEAD = PROMOTED_TO_2026_09_30
V4_STAGE_ACCEPTED_HEAD = UNCHANGED
A13_FORMALIZATION = EXTERNALLY_CONFIRMED
REGISTRY_R10 = PASS
```

禁止：

```text
PRODUCTION_READY
SHADOW_READY
ALL_OPEN_AUDITS_CLOSED
```

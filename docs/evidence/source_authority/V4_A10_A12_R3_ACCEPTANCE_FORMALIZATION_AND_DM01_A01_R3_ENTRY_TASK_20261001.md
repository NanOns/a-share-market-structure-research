# V4 A10/A12-R3 正式化 + DM01 A01-R3 连续候选执行任务卡｜2026-10-01

**Work Package：** `WP-A10-A12-R3-FORMALIZE-AND-DM01-A01-R3`  
**基线 HEAD：** `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`  
**优先级：** P0  
**外部验收依据：** `V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`

## 1. 目标

同一工作包分两阶段：

```text
Phase A
修复 formal authority provenance + 正式登记 daily producer

Phase B
仅在 Phase A validation PASS 后，
继续执行 DM01 A01-R3 真实连续 candidate chain
```

不要再次停在 governance-only entry。

## 2. Phase A｜加入真实外部验收文件

把：

```text
V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md
```

加入：

```text
docs/evidence/source_authority/
```

记录精确 path、bytes、sha256、`audited_head=d85f815097a09ca2dceda00d0e29d6ff4fe331d4`。

禁止继续把：

```text
V4_A10_A12_R3_PRODUCER_SOURCE_INSTANCE_SCOPE_REPAIR_TASK_20261001.md
```

当成 external acceptance authority。

## 3. 历史记录不可覆盖

保留：

```text
source_authority_governance_r3.json
V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json
V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json
A10_A12_R3_EXTERNAL_DISPOSITION_R1.json
```

新增：

```text
config/source_authority_governance_r4.json
data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json
data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R3.json
reports/audits/A10_A12_R3_EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json
```

R3 Head supersedes R2。

## 4. Registry R3 必须包含 4 个 authority

Historical：

```text
BAOSTOCK_DATED_TRADING_STATUS_RECONSTRUCTED_V3
BAOSTOCK_DATED_ST_STATUS_RECONSTRUCTED_V3
```

Scope：

```text
registration_scope = HISTORICAL_PATH_B_ONLY
2023-07-04 ~ 2026-09-24
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
```

Daily producer：

```text
BAOSTOCK_DATED_TRADING_STATUS_PROVIDER_AUTHORITY_V4
BAOSTOCK_DATED_ISST_PROVIDER_AUTHORITY_V4
registration_scope = PRODUCER_SEMANTIC_AUTHORITY
```

四项 `external_authority` 全部绑定本轮独立验收 MD。

## 5. Producer V4 权限

允许：

```text
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
machine-verified daily source instance
routine daily revision without human acceptance
```

禁止：

```text
AS_RECORDED
FIRST_AVAILABLE_AT_TARGET
OHLC authority
QFQ/adjustment authority
consumer outside scope
missing source instance
```

## 6. 正式 Global Gate Validator

必须基于 repo 真实 R4/R3 Head，不允许只使用 fixture：

```text
2026-09-28:
TRADING_STATUS PASS
ISST PASS

2026-09-29:
TRADING_STATUS FAIL SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE
ISST FAIL SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE

2026-09-30:
TRADING_STATUS PASS
ISST PASS
```

并验证：

```text
task card cannot satisfy external_acceptance
wrong external audit sha fails
Registry R2 not active trust root
Head R3 exact binds Registry R3
```

## 7. Historical validator

至少覆盖：

```text
2023-07-04
2024 ST boundary
2025 code-change boundary
2026-09-24
```

确认：

```text
source_revisions_by_target_date exact hit
AS_RECORDED false
first availability not minted
full-row oracle exact
```

## 8. Cross-stage Registry

新增下一 version。

A12：

```text
status = ACCEPTED_SOURCE_AUTHORITY_SCOPE
historical_path_b = EXTERNALLY_ACCEPTED_RECONSTRUCTED_ONLY
daily_producer_authority = EXTERNALLY_ACCEPTED
```

但：

```text
DM01 all-nine != accepted
```

## 9. Phase A STOP/GO

以下全部 PASS 才进入 Phase B：

```text
external audit exact binding
Registry R3 validation
Governance Head R3 validation
9/28 PASS
9/29 FAIL
9/30 PASS
historical owner validation
old business heads unchanged
```

任一失败：

```text
STOP
不得执行 DM01 final all-nine
```

## 10. Phase B｜连续 session

当前：

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-24
```

必须由 accepted calendar resolver 解析下一 completed sessions，不得硬编码。

预期：

```text
2026-09-28
2026-09-29
2026-09-30
```

不能跳过中间 session。

## 11. 2026-09-28 candidate

使用已有：

```text
A10_A12_R3_INSTANCE_2026-09-28_TRADING_STATUS_R1
A10_A12_R3_INSTANCE_2026-09-28_ISST_R1
```

执行完整九组件：

```text
RAW_DAILY
IDENTITY_UNIVERSE
TRADING_STATUS
ISST
ADJUSTED_DAILY
PERIOD_RAW
PERIOD_ADJUSTED
PRICE_LIMIT
SPECIAL_PHASE
```

要求 all-nine success、cross-component postcheck、atomic candidate only。

Data Head 不动。

## 12. 2026-09-29 必须真实补抓

当前 9/29 source instance 缺失。

真实查询：

```text
BaoStock target_trade_date = 2026-09-29
```

冻结：

```text
raw response
request/response receipt
provider_date
observed_at
received_at
schema
source revision
identity/calendar binding
```

因捕获晚于 target，必须：

```text
origin = DELAYED_HISTORICAL_RETRIEVAL
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

禁止用 9/28、9/30、插值或 forward fill 替代。

## 13. 9/29 不重新做人为 producer acceptance

必须证明：

```text
same accepted producer V4
+
new valid 9/29 source instance
=
PASS
```

并证明 producer/registry contract digest 不变，仅 source instance/revision 新增。

## 14. 连续 candidate chain

依次执行：

```text
9/24 accepted
→ 9/28 candidate
→ 9/29 candidate
→ 9/30 candidate
```

9/29 的 parent 必须是 9/28 candidate；9/30 的 parent 必须是 9/29 candidate。

不能直接从 9/24 跳 9/30。

## 15. 每日九组件 + atomicity

每个 session 都必须全九组件成功。

任何一天任一 component 失败：

```text
该日 candidate 不可视为 complete
后续日期停止
Data Head 不动
```

禁止 `8/9 success` 后继续下一日。

## 16. Candidate Chain Identity

逐日记录：

```text
target_trade_date
parent accepted/candidate digest
nine component digests
source instance digests
calendar binding
identity binding
candidate revision
created_at
```

## 17. Determinism / revision

验证：

```text
same source + same parent → same logical digest
source revision changes → new candidate revision
old candidate immutable
```

## 18. Data Head 纪律

本任务严禁：

```text
V4_DATA_ACCEPTED_HEAD promotion
V4_STAGE_ACCEPTED_HEAD movement
production/shadow/focus enablement
```

即使三日 candidate 全成功。

## 19. A13 不阻塞 DM01

A13 是独立 evidence-governance P1。

DM01 的 Trading Status / ISST 依赖 dated structured provider source instances，不消费 misnamed notices。

因此 A13 formalization 不阻塞 Phase B。

## 20. Required Evidence

至少生成：

```text
A10_A12_R3_EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json
A10_A12_R3_REGISTRY_R3_VALIDATION_R1.json
A10_A12_R3_REAL_DATE_GLOBAL_GATE_R2.json

DM01_A01_R3_SESSION_RESOLUTION_R1.json
DM01_A01_R3_20260928_CANDIDATE_R1.json
DM01_A01_R3_20260929_SOURCE_CAPTURE_R1.json
DM01_A01_R3_20260929_CANDIDATE_R1.json
DM01_A01_R3_20260930_CANDIDATE_R1.json
DM01_A01_R3_CONTINUOUS_CHAIN_POSTCHECK_R1.json
DM01_A01_R3_ATOMIC_FAILURE_PROBES_R1.json
DM01_A01_R3_DETERMINISM_R1.json
DM01_A01_R3_EXTERNAL_REAUDIT_HANDOFF_R1.json
DM01_A01_R3_CLOSURE_R1.md
```

## 21. Clean Regression

至少：

```text
A10
A10-R2
A10/A12-R3
A12
A12-R2
DM01
DM01-R2
DM01-R3
V4-01
V4-02
V4-04
V4-08
V4-09
global no-symbol
```

并证明旧 Accepted Heads unchanged。

## 22. Codex 最大允许结论

```text
A10_A12_R3_ACCEPTANCE_FORMALIZATION = PASS

DM01_A01_R3_CONTINUOUS_CANDIDATE_CHAIN =
READY_FOR_EXTERNAL_REAUDIT
```

禁止：

```text
DM01_EXTERNAL_ACCEPTANCE_PASS
V4_DATA_ACCEPTED_HEAD_PROMOTED
PRODUCTION_READY
SHADOW_READY
FOCUS_READY
```

# DM01 A01-R3 + A13 Formalization 独立外部验收审计｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `ac811e210c66b7ee9446086659dee169ee0f81a8`  
**前一审计基线：** `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`

## 1. 唯一总状态

```text
A10_A12_R3_ACCEPTANCE_FORMALIZATION = EXTERNAL_ACCEPTANCE_PASS
A13_EXTERNAL_ACCEPTANCE_FORMALIZATION = EXTERNAL_ACCEPTANCE_PASS
DM01_A01_R3_REAL_CONTINUOUS_CHAIN = EXTERNAL_ACCEPTANCE_PASS_SCOPED

DM01_ACCEPTED_CHAIN_SCOPE:
2026-09-24 ACCEPTED
→ 2026-09-28 CANDIDATE
→ 2026-09-29 CANDIDATE
→ 2026-09-30 CANDIDATE

V4_DATA_ACCEPTED_HEAD_PROMOTION =
AUTHORIZED_TO_2026_09_30_AFTER_FORMALIZATION

V4_STAGE_ACCEPTED_HEAD = KEEP

PRODUCTION = FALSE
SHADOW = FALSE
FOCUS = FALSE
```

本轮不是“工程 PASS”。DM01 真实连续增量链已经满足外部验收要求，可以进入正式 acceptance + Data Head promotion。

## 2. Source Authority 正式重绑｜PASS

上一轮发现的错误是 repair task card 被当成 external_authority。本轮已经修正。

正式 external authority：

```text
docs/evidence/source_authority/
V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md
```

精确绑定：

```text
bytes = 10868
sha256 = a23789d9de4eb48831125cbb9165964a8dacacb33e9dd30dba0f3bfced681d3a
audited_head = d85f815097a09ca2dceda00d0e29d6ff4fe331d4
```

新增并通过：

```text
source_authority_governance_r4.json
V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json
V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R3.json
A10_A12_R3_EXTERNAL_ACCEPTANCE_FORMALIZATION_R1.json
```

Registry R2 不再是 active trust root。Task card 与错误 audit SHA 均有显式 negative probe：`INVALID_EXTERNAL_AUTHORITY_BINDING`。

## 3. Registry R3 四个正式 authority｜PASS

Historical：

```text
BAOSTOCK_DATED_TRADING_STATUS_RECONSTRUCTED_V3
BAOSTOCK_DATED_ST_STATUS_RECONSTRUCTED_V3
```

Scope：

```text
2023-07-04 ~ 2026-09-24
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
```

Daily Producer：

```text
BAOSTOCK_DATED_TRADING_STATUS_PROVIDER_AUTHORITY_V4
BAOSTOCK_DATED_ISST_PROVIDER_AUTHORITY_V4
```

Daily producer 允许 machine-verified target-date source instance 和 routine daily revision without new human acceptance；禁止 AS_RECORDED、FIRST_AVAILABLE_AT_TARGET、OHLC/QFQ authority、missing target source、consumer outside scope。

## 4. 正式 Global Gate｜PASS

基于真实 R4/R3 trust root：

```text
2026-09-28: TRADING_STATUS PASS / ISST PASS
2026-09-29: both FAIL SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE
2026-09-30: TRADING_STATUS PASS / ISST PASS
```

历史 sample 重新验证多个边界日期，全部 `PASS_EXACT_HISTORICAL_SOURCE_INSTANCE`，且 `AS_RECORDED=false`、`first_available_at_target_proven=false`。

## 5. Session Resolution｜PASS

当前 Data Head：`2026-09-24`。

Resolver：

```text
MIN_ACCEPTED_COMPLETED_SESSION_STRICTLY_AFTER_PARENT
```

真实解析：

```text
2026-09-28
2026-09-29
2026-09-30
```

`hardcoded_pipeline_sessions=false`，没有跳交易日。

## 6. 2026-09-29 真实补抓｜PASS

真实请求：

```text
request_count = 3
row_count = 5223
```

Raw response：

```text
bytes = 2,586,263
sha256 = 2302544479b5db8408dd40461685602d4a72f6b3cb32e1ebcba09bed854bcbb0
```

Lineage：

```text
origin = DELAYED_HISTORICAL_RETRIEVAL
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

Producer Registry SHA 前后完全一致，`human_producer_reacceptance_required=false`。这正式验证了 producer/source-instance 分层的核心目标。

## 7. 最终连续链｜PASS

最终采用 `durable_r3` chain。

### 2026-09-28

Parent：

```text
V4_DATA_ACCEPTED_HEAD
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0
```

Candidate：

```text
b338caaea8f9e41228a62add7e987d946f4dc9a5a5297dbe02e9ee73df525313
```

### 2026-09-29

Parent：

```text
b338caaea8f9e41228a62add7e987d946f4dc9a5a5297dbe02e9ee73df525313
```

Candidate：

```text
0a67e7211572a7057c50ab27e397c3e093f88c24732e8c7be7bdda92952ca1bf
```

### 2026-09-30

Parent：

```text
0a67e7211572a7057c50ab27e397c3e093f88c24732e8c7be7bdda92952ca1bf
```

Candidate：

```text
e4ba1fb6d4690b869f98ffc45a8d576a641ef2e9a852a9db97aedd19e043bc81
```

因此 `9/24 Accepted → 9/28 → 9/29 → 9/30` 父子链完全连续。

## 8. 三日 All-Nine｜PASS

每天完整执行九组件：

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

`CONTINUOUS_CHAIN_POSTCHECK_R3`：

```text
all_nine_each_day = true
all_independent_postchecks = PASS
no_intermediate_session_skipped = true
```

行数：

```text
9/28: IDENTITY 5222, RAW 5210, STATUS 5210 ACTUAL + 12 SUSPENDED
9/29: IDENTITY 5223, RAW 5211, STATUS 5211 ACTUAL + 12 SUSPENDED
9/30: IDENTITY 5224, RAW 5213, STATUS 5213 ACTUAL + 11 SUSPENDED
```

ISST / Price / Special Phase 与对应 universe 同步完整。

## 9. DEGRADED_PASS 边界

ADJUSTED_DAILY、PERIOD_ADJUSTED，以及 9/30 PRICE_LIMIT 保持既有 `DEGRADED_PASS`。当前 row quality 均为 READY，这些是继承既有 accepted capability/contract 的降级状态，不是本轮新增 source 缺失。

不得因为 row quality READY 就擅自改成 FULL_PASS。

## 10. Determinism｜PASS

最终：

```text
fresh_namespace_exact_component_logical_digests = true
original logical digest == fresh rerun logical digest
old_candidates_immutable = true
same source + same parent → NOOP_IDENTICAL_CANDIDATE
```

还做了真实 SDK recapture：provider row values 未变化，但 source binding revision 改变后 candidate revision 改变；Producer Registry SHA 前后不变。

## 11. R1/R2/R3 Business Parity｜PASS

检查 27 components：

```text
business values identical
accepted_heads_changed = false
source_bytes_changed = false
```

少数 Identity / Period / Special Phase full-row digest 差异只来自显式 parent publication provenance 字段，且已经逐版本验证实际 parent binding。业务字段 digest 一致。

## 12. Durability / Clean Checkout｜PASS

中途发现 accepted metadata byte representation、LFS source dependency、checkout durability 问题。最终修复未弱化 hash gate，也没有重构原 source：

```text
hash_gate_weakened = false
original_sources_unchanged = true
accepted_head_bytes_unchanged = true
```

旧 candidate 不覆盖，最终重新构建 durable_r3 chain 并做 determinism/parity/clean regression。

## 13. Atomicity｜PASS

Final R3 atomic failure probes 通过。任何一天任一组件失败，则当日 complete candidate 不成立、后续日期停止、Accepted namespace 不可见、Data Head 不动。不存在 `8/9 success` 后继续下一日。

## 14. DM01 Clean Regression｜PASS

最终：

```text
1496 passed
2 skipped
1 authorized deselected
0 failures
0 errors
```

`config/.env` 未读取，production DB 未使用，disposable PostgreSQL 使用正常，no-symbol PASS。

## 15. Head Discipline｜PASS

截至审计 HEAD：

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-24
data_head_moved = false

V4_STAGE_ACCEPTED_HEAD
stage_head_moved = false
```

所有业务 Accepted Heads 保持不变。Production/Shadow/Focus 全 false。

## 16. DM01 外部裁决

正式结论：

```text
DM01_A01_R3_REAL_INCREMENTAL_BUILDERS =
EXTERNAL_ACCEPTANCE_PASS_SCOPED
```

接受 2026-09-28 / 09-29 / 09-30 三日真实连续 All-Nine chain。

这足以解除 `DM01_INDEPENDENT_EXTERNAL_REAUDIT`，并授权下一步：

```text
V4_DATA_ACCEPTED_HEAD
2026-09-24 → 2026-09-30
```

但必须用 accepted-chain manifest / promotion receipt 保留中间连续性。

## 17. A13 Formalization｜PASS

`OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1` 已建立：

```text
external_acceptance = EXTERNALLY_ACCEPTED
acceptance_scope = EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT
V4_08_HEAD_ACTION = KEEP
```

Accepted sidecar SHA：

```text
89916c039a72f39624769974a0e915c26ab7412ea933be1e88ef4b0f4cac43fe
```

Runtime readback：

```text
semantic_entry_count = 134
fixture_market_facts_consumed = false
positive_eligible_real_entry_count = 0
```

所有 IPO postpone / UNKNOWN 均拒绝进入 trading-event truth，没有用 fixture 制造正式 positive market fact。

## 18. A13 Counterfactual｜PASS

移除 SH.603302 / SH.688688 / SZ.300728 误命名 notice 后：

```text
V4-08 admission unchanged
PIT 50,162 facts unchanged
V4-07/V4-08/V4-09 business digest unchanged
```

因此 V4_08_ACCEPTED_HEAD = KEEP，BUSINESS_REBUILD_REQUIRED=false。

## 19. A13 Clean Regression｜PASS

```text
1496 passed
2 skipped
1 authorized deselected
0 failures
```

Accepted business heads unchanged。

## 20. Registry R9 状态一致性缺口

技术 acceptance 不受影响，但 R9 的 A12 entry 同时存在新旧矛盾字段。

正确 current：

```text
status = ACCEPTED_SOURCE_AUTHORITY_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
daily_producer_authority = EXTERNALLY_ACCEPTED
```

但仍残留：

```text
acceptance_scope = NO_FUNCTIONAL_CLOSURE
capability_limitations = EXTERNAL_REPAIR_ACCEPTANCE_REQUIRED
observed_daily_producer_acceptance = PENDING
implementation_status = ...READY_FOR_EXTERNAL_REAUDIT
transition.status = OPEN
```

Canonical Registry R3 + Governance Head R3 正确，DM01 实际消费正确 trust root，所以不推翻技术 acceptance。

Data Head promotion 前必须新增 Registry R10 清理 current state；旧字段只保留在 history/prior_transition。

## 21. 仍 OPEN 的非本轮 blocker

`OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS` 仍 OPEN，范围为 OHLC/Amount/Volume、QFQ、Security Identity、Special Phase、Sector Membership。

这是 global mandatory adoption / production / shadow 前置，不阻断当前 DM01 Data Head promotion。

## 22. 当前正式状态

```text
A10/A12-R3 = EXTERNALLY_ACCEPTED
A13 = EXTERNALLY_ACCEPTED_FORMALIZATION_CONFIRMED
DM01_A01-R3 = EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
DM01_ACCEPTED_THROUGH = 2026-09-30

V4_DATA_ACCEPTED_HEAD =
CURRENTLY 2026-09-24
PROMOTION_TO_2026-09-30 AUTHORIZED

V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10
V4_08_ACCEPTED_HEAD = KEEP

PRODUCTION = FALSE
SHADOW = FALSE
FOCUS = FALSE
```

## 23. 下一步

只需一个正式收口任务：

```text
1. 将本独立外部验收写入仓库
2. Registry R10 统一 A12 / DM01 / A13 当前状态
3. 创建 DM01 accepted-chain manifest
4. 创建 external acceptance record
5. archive 旧 V4_DATA_ACCEPTED_HEAD exact bytes
6. 原子推进 V4_DATA_ACCEPTED_HEAD → 2026-09-30
7. 独立 readback / clean regression
8. V4_STAGE_ACCEPTED_HEAD 不动
```

不需要再次修改 DM01 算法。

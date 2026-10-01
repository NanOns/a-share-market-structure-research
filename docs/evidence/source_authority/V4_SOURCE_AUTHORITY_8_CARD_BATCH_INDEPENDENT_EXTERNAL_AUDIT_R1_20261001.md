# V4 Source Authority 八卡批次｜独立外部验收审计 R1｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `1655f84d1a47faca43c281d66e7704f2fa56b1b8`  
**前次审计基线：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**新增提交：** 14  
**性质：** 对 Source Authority 八卡批次执行结果做独立外部验收，不接受 Codex 自报 PASS 作为最终结论。

---

# 1. 唯一总状态

```text
BATCH_EXTERNAL_ACCEPTANCE = PARTIAL_PASS_WITH_BLOCKERS

PASS:
  A08 V4-09 N01
  A09 V4-09 N02

PASS_RESULT_C:
  A11 V4-01 Identity Authority Reconciliation
  说明：接受“历史 authority 未解决”的审计结论，不等于历史 authority 已解决。

BLOCKED_REPAIR_REQUIRED:
  A10 Source Authority Governance
  A12 V4-02 Trading Status / ST Authority

PARTIAL_ENGINEERING_PASS_FINAL_BLOCKED:
  A01 DM01 R2

ADMIN_GOVERNANCE:
  Master Amendment / Registry 执行记录与状态账本基本合格，
  但不能替代上述功能性验收。
```

**不得移动：**

```text
V4_DATA_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_01/V4_02/V4_04/V4_05/V4_07/V4_08/V4_09 accepted heads
```

当前保留原 Accepted Heads 是正确的。

---

# 2. Git / 变更范围

从：

```text
4e5284f74c5275e28d75985d1c3e60eaf96e4103
```

到：

```text
1655f84d1a47faca43c281d66e7704f2fa56b1b8
```

共 14 commits。

主要实现线：

```text
A10 Source Authority Governance
A11 V4-01 Identity Authority
A12 V4-02 Status / ST Authority + Cascade
A08 V4-09 N01 Hardening
A09 V4-09 N02 Consumer Identity
A01 DM01 R2 Catch-up / Supplemental Gate
```

另有 Master/Registry/Closure 类提交。

---

# 3. Accepted Head 保护

本轮最重要的治理动作之一是：

```text
没有因为工程 candidate PASS 自动移动历史 Accepted Head
```

核对到：

```text
V4_01_ACCEPTED_HEAD
= b8ea5b8091629d116c860f9bf6a1a398301d75be16af7b08ff526fba9329bf6b

V4_02_ACCEPTED_HEAD
= da318a1f82a03f13930af7858ca1640fadbdaedbee85e27d47f9c869c2d6b595

V4_04_ACCEPTED_HEAD
= 1d8a0611dc80e3c3bea86175f75096eeac53f04af126137892cbc8a14dc0bd7a

V4_05_ACCEPTED_HEAD
= fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb

V4_09_ACCEPTED_HEAD
= 641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d

V4_DATA_ACCEPTED_HEAD
仍为 2026-09-24
```

该部分：

```text
PASS
```

---

# 4. A10｜Source Authority Governance

## 4.1 已完成且正确

A10 建立了统一：

```text
Source Role:
CORE_AUTHORITY
FIELD_AUTHORITY
SUPPLEMENTAL_CROSSCHECK
DIAGNOSTIC_ONLY
RESEARCH_ONLY
```

Availability：

```text
AVAILABLE
LOCAL_CAPTURE_MISSING
LOCAL_ACCEPTED_ARTIFACT_MISSING
PROVIDER_NOT_QUERIED
PROVIDER_QUERY_ATTEMPTED_FAILED
PROVIDER_TARGET_DATE_EMPTY_CONFIRMED
PROVIDER_SCHEMA_MISMATCH
PROVIDER_RUNTIME_UNACCEPTED
SOURCE_NOT_YET_PUBLISHED
PIT_FIRST_AVAILABILITY_UNPROVEN
PIT_HISTORICAL_STATE_NOT_RECONSTRUCTABLE
CAPABILITY_DISABLED_BY_CONTRACT
```

Historical mode：

```text
TARGET_DATE_QUERYABLE_FACT
AS_RECORDED_PIT_FACT
MUTABLE_CURRENT_SNAPSHOT
```

并正确防止：

```text
NOT_QUERIED → PROVIDER_EMPTY
延迟历史补抓 → AS_RECORDED
mutable current snapshot → 历史 PIT 倒填
supplemental missing → 自动阻断 Core
```

Repo scan 完成 1,143 个文件，保留了 49 个已识别 findings，没有用“scanner PASS”偷换“问题全部解决”。

以上：

```text
PASS_ENGINEERING
```

## 4.2 新发现 blocker｜Owner Acceptance Binding 未进入通用运行时门

当前：

```python
evaluate_consumer_gate(...)
```

验证：

```text
role
allowed_consumers
availability
required
may_block_core
```

但**没有验证：**

```text
owner_contract_id 对应的 owner contract
是否：
- externally accepted
- formal consumer authorized
- hash-bound
- registered in accepted authority registry/global head
```

与此同时 A10 config 已将：

```text
LOCAL_DATED_TRADING_STATUS_V2
LOCAL_DATED_ST_IDENTITY_V2
```

写为：

```text
FIELD_AUTHORITY
enabled=true
```

但 A12 当前：

```text
external_acceptance = null
formal_consumer_authorization = false
```

这意味着：

> Generic A10 gate 本身仍可能把一个“仅在配置里声明为 FIELD_AUTHORITY、但尚未外部接受的 owner”当成 authority。

DM01 没被这个缺口污染，是因为 DM01 另外实现了：

```python
require_external_a12_owner_for_final_candidate()
```

明确检查：

```text
external_acceptance == EXTERNALLY_ACCEPTED
formal_consumer_authorization == true
global_head.accepted_source_authority_owners binding exact
```

但这是 DM01 私有补丁，不是 A10 全局治理门。

### A10 外部裁决

```text
A10_FRAMEWORK = PASS
A10_GLOBAL_OWNER_AUTHORIZATION_GATE = FAIL

A10_EXTERNAL_ACCEPTANCE = BLOCKED_R2
```

这是 P0 Governance blocker。

---

# 5. A11｜V4-01 Identity Source Authority Reconciliation

## 5.1 审计结果不是“修好了”，而是 Result C

A11 输出：

```text
RESULT_C_WIDESPREAD_AUTHORITY_UNRESOLVED
```

并正式提出：

```text
formal_authority = UNRESOLVED_MASTER_AUTHORITY

proposed_historical_label =
PROVIDER_RECONSTRUCTED_FACT / RECONSTRUCTED_CORRECTED

proposed_capability_downgrade =
HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED

stable_security_id_policy =
DO_NOT_RENUMBER
```

这是正确的。

它没有为了“过任务”硬说：

```text
所有历史 security type / lifecycle 已被 TDX 独立确认
```

## 5.2 SH.600018 单案处理合格

旧差异：

```text
accepted anchor = 2006-10-26
exchange code first listing = 2000-07-19
```

A11 补充官方证据后判断：

```text
CORPORATE_REORGANIZATION_ENTITY_ANCHOR_SEMANTICS_SUPPORTED
```

即：

```text
code continuity first-listing
≠
post-reorganization issuer identity anchor
```

因此：

```text
不改 stable security_id
不 mass rekey
不把 code first-listing 自动当 issuer anchor
```

合理。

同时新抓证据标记：

```text
RECONSTRUCTED_CORRECTED_OBSERVED_2026_10_01
first_available_at_target_proven = false
```

没有倒填 PIT。

## 5.3 下游业务结果

A11 明确：

```text
identity_rows_changed = 0
security_ids_renumbered = 0
canonical candidate sha == old sha
```

V4-02 / 03 / 04 / 05 / 07 / 08 / 09：

```text
business_output_changed = false
input_identity_changed = false
logical_digest_changed = false
rebuild_required = false
```

因此无需为 A11 无差别重跑下游。

### A11 外部裁决

接受的是：

```text
A11_AUDIT_RESULT_C = PASS
```

不是：

```text
V4_01_HISTORICAL_AUTHORITY_RESOLVED = PASS
```

正式状态应为：

```text
A11_EXTERNAL_ACCEPTANCE =
PASS_RESULT_C_WITH_CAPABILITY_DOWNGRADE

HISTORICAL_IDENTITY_BUSINESS_VALUES =
KEEP_CURRENT_ACCEPTED_VALUES

HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_LOCAL_TDX_AUTHORITY =
NOT_PROVEN

GO_FORWARD_OFFICIAL_IDENTITY =
KEEP_ACCEPTED
```

需要后续 formal amendment 将这个限制写入正式治理状态。

---

# 6. A12｜V4-02 Trading Status / ST Authority

这是本批次最大的未闭环项。

## 6.1 Source Boundary 修正本身是对的

A12 正确停止：

```text
BaoStock tradestatus → formal SUSPENDED
BaoStock isST → formal ST
```

当前候选规则：

```text
local actual bar
→ ACTUAL_TRADED

local/official accepted dated evidence
→ SUSPENDED / SHOULD_TRADE / ST

BaoStock
→ SUPPLEMENTAL_CROSSCHECK only
```

这一层：

```text
PASS_ENGINEERING
```

## 6.2 但实际 accepted dated owner = 0

Inventory：

```text
accepted_dated_authority_fact_count = 0
accepted_dated_authority_files = []
```

所以 full-history candidate 变成：

```text
4,035,729 rows

ACTUAL_TRADED = 4,026,611
UNKNOWN trading status = 9,118

is_st = UNKNOWN / None
= 4,035,729 rows
```

旧 ST：

```text
ST=0 → UNKNOWN : 3,913,800
ST=1 → UNKNOWN :   121,929
```

即所有历史 ST formal facts 全部被撤成 UNKNOWN。

## 6.3 Price Limit 被几乎完全击穿

由于 `is_st` 不再有 formal owner：

```text
LIMIT_UP     → UNKNOWN : 59,550
LIMIT_DOWN   → UNKNOWN : 24,377
NOT_LIMIT    → UNKNOWN : 3,940,937
NO_LIMIT     → UNKNOWN : 1,670
SUSPENDED    → UNKNOWN : 9,118
```

当前 A12 candidate 的 Price Limit 业务能力几乎整体变成 UNKNOWN。

这说明 fail-closed 是正确的，但：

```text
“没有错误使用 BaoStock”
≠
“业务修复已完成”
```

## 6.4 V4-04 真回放证明退化是实际业务影响

A12 用未修改算法重跑 V4-04：

```text
rows = 5,222
PARTIAL_UNKNOWN = 5,222
COMPLETE = 0
```

旧 V4-04：

```text
COMPLETE = 4,981
PARTIAL_UNKNOWN = 241
```

因此：

```text
这是大规模业务能力退化
```

不能直接把当前 A12 candidate promotion 成正式 repaired accepted state。

## 6.5 下游真实传播

A12 级联重放显示：

### V4-03
大量 technical / relative / RPS 字段发生变化。

### V4-07 Base Seed
有：

```text
36 security rows changed
4 rows base_seed_state:
FALSE → UNKNOWN
```

### V4-08
B0 / B2 / ROTATION / SECTOR_NATIVE：

```text
business digest 完全一致
security_rows_changed = 0
```

因此 V4-08 business 层暂时可以停止级联。

### V4-09
仍受 V4-07/Base Seed 传播：

```text
33 security rows changed
4 rows raw_qualification / base_seed / priority_bucket
发生 FALSE/NOT_ELIGIBLE → UNKNOWN
```

所以不能说：

```text
“V4-08没变，所以 V4-09不用重跑”
```

Codex 这点实际做了真 replay，处理正确。

## 6.6 A12 任务卡要求的真实样本矩阵没有完成

原任务要求 Trading Status 真实样本至少：

```text
正常交易
真实停牌
复牌
真实数据缺口
provider/local conflict
代码变更边界
新上市
退市/长期停牌边界
```

ST 至少：

```text
NORMAL → ST
ST → *ST / risk-warning
ST removal
ST期间停牌
代码变更期间 ST
新上市
官方 vs BaoStock conflict
```

当前 A12 closure 明确承认：

```text
dated owner transition vectors =
synthetic contract fixtures

not real official acceptance
```

虽然仓库已有很多 suspension / delisting / exchange evidence，
但没有把它们正式整理成 A12 可接受的 dated source semantics matrix。

### A12 外部裁决

```text
A12_FAIL_CLOSED_MECHANICS = PASS
A12_UNCHANGED_ALGORITHM_REPLAY = PASS
A12_CASCADE_DIFF = PASS

A12_REAL_DATED_OWNER_SEMANTICS = FAIL
A12_REQUIRED_REAL_SAMPLE_MATRIX = FAIL
A12_BUSINESS_RESTORATION = FAIL

A12_EXTERNAL_ACCEPTANCE = BLOCKED_R2
```

当前 all-UNKNOWN candidate 只能保留为：

```text
DIAGNOSTIC_FAIL_CLOSED_CANDIDATE
```

不能 promotion。

---

# 7. A08｜V4-09 N01 Repair Freeze Authority Hardening

A08 处理得比较完整。

验证：

```text
accepted V4-09 rows = 5222
accepted artifact bytes exact
logical digest exact
algorithm AST unchanged
```

历史 accepted runtime 使用 Git-anchored archive 只用于：

```text
ACCEPTED_PUBLICATION_HISTORY_ONLY
```

同时明确：

```text
current_runtime_matches_accepted_implementation = false
current_runtime_external_acceptance = PENDING
```

没有用历史 archive 给当前 runtime 洗白。

Negative vectors 包括：

```text
wrong_status
wrong_identity
wrong_authority
missing_binding
extra_binding
wrong_file_hash
wrong_consumer
wrong_original_parent
wrong_amended_parent
changed_unaccepted_receipt
```

新 promotion 仍保持 strict current-runtime gate。

### A08 外部裁决

```text
A08_EXTERNAL_ACCEPTANCE = PASS
```

可关闭：

```text
AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
```

只关闭 hardening audit，不开放 production/shadow/Focus。

---

# 8. A09｜V4-09 N02 DB Consumer Identity

新增：

```text
025_v4_09_consumer_identity_hardening.sql
```

未修改历史 021～024。

独立 disposable PostgreSQL 验证了：

```text
legacy rows exact readable
legacy payload digest unchanged
retry idempotent
same publication other consumer rejected
mixed consumer rejected
payload consumer mismatch rejected
cross-consumer FK rejected
consumer UPDATE rejected
distinct consumer with distinct publication works
rollback refuses destructive nonlegacy loss
rollback 后 schema / payload / publication / migration ledger exact
```

### A09 外部裁决

```text
A09_EXTERNAL_ACCEPTANCE = PASS
```

可关闭：

```text
AUD-V4-09-DB-CONSUMER-IDENTITY-N02
```

仍不代表 production cutover。

---

# 9. DM01 A01 R2

## 9.1 本轮成功解决了最初的问题

真实 BaoStock bounded requests：

```text
request_count = 6
```

Smoke：

```text
2026-09-30
```

历史 target：

```text
2026-09-28
```

实际返回：

```text
query_daily_history_k_AStock rows = 5,222
query_daily_adjust_factor rows = 16
```

observed_at / received_at：

```text
2026-10-01
```

并明确：

```text
origin = DELAYED_HISTORICAL_RETRIEVAL
lineage = RECONSTRUCTED_CORRECTED
first_availability_at_target_proven = false
```

证明：

```text
本地 9/28 没冻结
≠
BaoStock 9/28 没数据
```

这一点正式解决。

## 9.2 BaoStock 不再阻断 Core

独立 preflight：

```text
with provider    → core_source_gate PASS
without provider → core_source_gate PASS
```

Canonical QFQ：

```text
GBBQ_ONLY
```

BaoStock adjustment factor：

```text
audit/supplemental
不能覆盖 canonical QFQ
```

正确。

## 9.3 SDK schema 修复合理

初次 runtime smoke 对 adjustment factor 遇到：

```text
adjustFacto
```

而不是：

```text
adjustFactor
```

后续不是随便容错，而是：

```text
baostock==0.9.3
installed Python sources hash pinned
actual SDK parser source captured
raw bytes preserved
exact alias:
adjustFacto → adjustFactor
其他 schema drift fail closed
```

同时发现 smoke/target normalized path collision 后：

```text
保留原 raw capture
不重新发网络请求
建立 purpose-scoped V2_1 immutable path
```

这一修复可接受。

## 9.4 TDX / BaoStock crosscheck

2026-09-28：

```text
target members = 5,222
TDX actual bars = 5,210
local bar missing = 12
provider crosscheck rows = 5,210
close exact match = 5,210
```

支持历史 capture 真实性。

## 9.5 最终 all-nine 没执行

Codex 如实记录：

```text
all_nine_final_execution_performed = false
stage_completed = false
data_head_promoted = false
```

阻塞：

```text
A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED
```

这是正确的。

### DM01 外部裁决

```text
DM01_A01_R2_RUNTIME_CAPTURE = PASS
DM01_A01_R2_SUPPLEMENTAL_GATE = PASS
DM01_A01_R2_SOURCE_PREFLIGHT = PASS

DM01_A01_FINAL_ALL_NINE = BLOCKED
DM01_A01_FINAL_EXTERNAL_ACCEPTANCE = BLOCKED
```

Data Head 继续停在：

```text
2026-09-24
```

正确。

---

# 10. DM01 是否存在 9/24 → 9/28 跳日问题

核对 accepted calendar extension：

```text
candidate_sessions:
2026-09-28
2026-09-29
2026-09-30
```

并且 next-session resolver：

```text
selection = MIN_ACCEPTED_SESSION_STRICTLY_AFTER_PARENT
next_completed_required_session = 2026-09-28
later_sessions_cannot_leap_over_missing_target = true
```

因此当前没有：

```text
9/24 → 跳过正式交易日 → 9/28
```

的证据。

此项：

```text
PASS
```

---

# 11. 八卡批次状态表

| 项目 | 工程实现 | 独立外部结论 | 是否可关闭 |
|---|---|---|---|
| Master / Registry R2 | PASS | PASS_ADMIN | 是，作为治理入口 |
| A10 Governance | 大部分 PASS | **BLOCKED_R2** | 否 |
| A11 Identity Authority | PASS Result C | **PASS_RESULT_C** | 可关闭 audit，但需正式 capability amendment |
| A12 Status/ST Authority | fail-closed/cascade PASS | **BLOCKED_R2** | 否 |
| A08 N01 | PASS | **PASS** | 是 |
| A09 N02 | PASS | **PASS** | 是 |
| DM01 A01 R2 | Partial PASS | **FINAL_BLOCKED** | 否 |
| 批次 closure/status card | 状态记录基本如实 | PASS_ADMIN | 不等于功能闭环 |

---

# 12. 新增阻塞关系

正式依赖应改成：

```text
A10-R2 owner-acceptance gate
        │
        ├──────────────┐
        │              │
        ▼              ▼
A12-R2 real source semantics / authority
        │
        ▼
A12 external acceptance + owner promotion
        │
        ▼
DM01 A01-R3 final all-nine integration
        │
        ▼
DM01 external acceptance
        │
        ▼
V4_DATA_ACCEPTED_HEAD promotion
```

A08 / A09 可独立关闭。

A11 Result C 可独立正式化，不阻塞 A12 工程探索。

---

# 13. 下一轮必须修什么

## P0-1｜A10-R2

补：

```text
generic owner acceptance binding
```

FIELD_AUTHORITY 不能只靠配置自声明。

## P0-2｜A12-R2

不能继续停在：

```text
accepted dated owner = 0
→ 全市场 UNKNOWN
```

必须完成真实 source semantics adjudication。

允许两条路径：

```text
Path A
建立 local / official dated owner dataset

Path B
经过真实官方样本校验后，
正式提出 historical reconstructed field authority amendment，
使 BaoStock tradestatus/isST
只在明确范围内成为 RECONSTRUCTED_CORRECTED field authority
```

Path B 也不得声称：

```text
AS_RECORDED
first_available_at = target
```

## P0-3｜DM01-A01-R3

必须等 A10/A12 owner acceptance 完成后才执行 final all-nine。

---

# 14. 不需要重做什么

不需要重做：

```text
A08
A09
A11 全量 identity audit
DM01 9/28 BaoStock 网络抓取
DM01 SDK 0.9.3 schema proof
DM01 TDX/BaoStock 5210 exact-close crosscheck
A12 unchanged-algorithm replay machinery
A12 downstream cascade diff machinery
```

这些已经形成有效证据。

下一轮只补缺口，不返工已经通过的部分。

---

# 15. 当前正式状态

```text
V4_SOURCE_AUTHORITY_BATCH_R2 =
PARTIAL_PASS_WITH_BLOCKERS

A08 = EXTERNALLY_ACCEPTED
A09 = EXTERNALLY_ACCEPTED

A11 =
EXTERNALLY_ACCEPTED_RESULT_C
CAPABILITY_DOWNGRADE_TO_BE_FORMALIZED

A10 =
EXTERNAL_ACCEPTANCE_BLOCKED_R2

A12 =
EXTERNAL_ACCEPTANCE_BLOCKED_R2

DM01_A01 =
PARTIAL_ENGINEERING_PASS
FINAL_ALL_NINE_BLOCKED

V4_DATA_ACCEPTED_HEAD =
KEEP_2026_09_24

PRODUCTION =
NOT_AUTHORIZED

SHADOW =
NOT_AUTHORIZED

FOCUS_CUTOVER =
NOT_AUTHORIZED
```

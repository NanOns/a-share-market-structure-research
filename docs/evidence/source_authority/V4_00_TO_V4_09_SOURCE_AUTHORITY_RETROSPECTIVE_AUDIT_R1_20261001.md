# V4-00～V4-09 Source Authority / Availability 同类问题专项回溯审计 R1｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**审计性质：** 针对 DM-01 本轮暴露出的“本地缺失被误判为服务不可用 / Supplemental 越权成为 Core Gate / 历史补抓与 PIT 混淆”做 V4-00～V4-09 回溯审计。

---

# 1. 审计问题定义

本轮只查四类同源错误：

```text
C1 LOCAL_MISSING_AS_PROVIDER_UNAVAILABLE
   本地/仓库没冻结，不等于 provider 没数据。

C2 SUPPLEMENTAL_ESCALATED_TO_CORE_AUTHORITY
   supplemental/cross-check 被实现成正式 Core authority 或 hard gate。

C3 HISTORICAL_CATCHUP_BLOCKED_BY_SAME_DAY_ONLY_CONTRACT
   provider 本可查询历史指定日期，但本地合同只允许目标日当天抓。

C4 HISTORICAL_FACT_RETRIEVAL_CONFUSED_WITH_AS_RECORDED_PIT
   后补到历史事实，不等于证明历史 T 当时已知。
```

---

# 2. 唯一总裁决

```text
V4_00_TO_V4_09_RETROSPECTIVE_SOURCE_AUTHORITY_AUDIT = ACTION_REQUIRED

DM01 = REPAIR_REQUIRED
V4_02 = SOURCE_AUTHORITY_REPAIR_REQUIRED
V4_01 = SOURCE_AUTHORITY_RECONCILIATION_REQUIRED

V4_00 = KEEP_ACCEPTED
V4_03 = KEEP_ACCEPTED_PENDING_CASCADE_DIFF_CHECK
V4_04 = ACCEPTED_RESULT_REVALIDATION_REQUIRED
V4_05 = ACCEPTED_RESULT_REVALIDATION_REQUIRED
V4_06 = KEEP_ACCEPTED
V4_07 = CONDITIONAL_CASCADE_REVALIDATION
V4_08 = CONDITIONAL_CASCADE_REVALIDATION
V4_09 = CONDITIONAL_CASCADE_REVALIDATION + EXISTING_N01_N02_OPEN
```

注意：

**这不是宣布 V4-01/V4-02/V4-04/V4-05 全部推倒重来。**

处理原则是：

```text
冻结旧 Accepted Head
→ 修正 authority contract / producer
→ 重建受影响 artifact
→ 做 business diff
→ 只对真实变化的下游做级联复验
→ 外部验收后用 Amendment / Superseding Head 追加
```

不得静默覆盖历史接受记录。

---

# 3. 权威基准

V4.2.2 REV2（阶段实施时已经生效）和当前 REV4 的 Source Authority Matrix 均明确：

```text
OHLC / Volume / Amount
正式 Authority = TDX
BaoStock = fingerprint / supplemental

Turnover
BaoStock 可作为正式 supplemental dataset
但缺失不能阻断价格 Core 主链

Trade Status
正式 Authority = accepted local security master + TDX/calendar facts
BaoStock = independent cross-check

ST
正式 Authority = accepted local security master 日期有效身份
BaoStock = cross-check only
未知必须传播 UNKNOWN

股票代码 / 证券类型
正式 Authority = 本地 TDX metadata
BaoStock basic = supplemental
```

另有统一原则：

```text
BaoStock supplemental failure
does_not_block_or_invalidate_accepted_core_publication = true

core_flow_waits_for_supplement = false
```

---

# 4. V4-00 / V4-00F

## 结论

```text
KEEP_ACCEPTED
NO_STAGE_REOPEN
GLOBAL_TAXONOMY_HARDENING_REQUIRED
```

早期审计曾把本地没有 BaoStock 包、未做 live request 写成：

```text
current_capability = UNAVAILABLE
```

这个词容易被误读为“provider unavailable”。

但后续已经通过 0.9.3 public anonymous route 的真实 probe，且 Phase0 一直保持：

```text
NON_BLOCKING_SUPPLEMENTAL
NO CORE DEPENDENCY
```

所以 V4-00 不需要重开。

需要由新的全局治理任务统一修正术语：

```text
LOCAL_ARTIFACT_MISSING
PROVIDER_NOT_QUERIED
PROVIDER_QUERY_FAILED
PROVIDER_TARGET_EMPTY
```

禁止继续用一个 `UNAVAILABLE` 混写。

---

# 5. V4-01

## 5.1 历史补抓机制｜PASS

V4-01 是本项目正确实现历史 catch-up 的正例。

已有：

```text
v4_01_dated_roster_r5.py
v4_01_requery_missing_roster_days_r6_1.py
```

能够对历史指定交易日重新请求 provider 数据，并保存：

```text
provider date
实际 observed_at
query result
digest
error code
```

因此 V4-01 没有犯 DM-01 的 same-day-only 错误。

## 5.2 但发现 Source Authority Contract 不完全一致｜RECONCILIATION REQUIRED

`SECURITY_ENTITY_IDENTITY_V1` 当前正式 source contracts：

```text
BAOSTOCK_LIFECYCLE_FACTS_R5_V1
BSE_SECURITY_LIFECYCLE_SOURCE_V1
```

SH/SZ 历史 stable identity 初始构造中：

```text
BaoStock query_stock_basic
→ security_type_provider
→ ipo/listed_from
→ stable security_id anchor
```

而 REV2/REV4 总合同写的是：

```text
股票代码 / 证券类型
正式 Authority = 本地 TDX metadata
BaoStock basic = supplemental
```

后续 V4-01 已经做了大量 TDX-first boundary scan、官方代码变更证据与 go-forward 官方交易所 identity 增量，这显著降低了风险；但没有证据证明历史 5,351 个 canonical identities 的**每一个正式字段**已经从“BaoStock owner”转换成“TDX/official owner”。

另有现存证据：

```text
V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_01
status = OPEN_SEPARATE_LIFECYCLE_ANCHOR_AUDIT
```

其中 SH.600018 的 accepted canonical listing anchor 与交易所目录 first listing date 存在差异。

### 裁决

```text
V4_01_HISTORY_CATCHUP = PASS
V4_01_IDENTITY_RESULT = KEEP_ACCEPTED_FOR_NOW
V4_01_SOURCE_AUTHORITY = RECONCILIATION_REQUIRED
```

不允许直接 mass-renumber security_id。

必须先逐字段区分：

```text
symbol
security_type
board
listing anchor
alias relation
lifecycle interval
```

各自 authority，再决定是否需要 Amendment。

---

# 6. V4-02｜发现本轮最重要的历史同类问题

## 6.1 Trading Status 实际把 BaoStock 从 cross-check 提升成 formal producer

当前：

```text
config/v4_02_dated_trading_status_v1.json
```

规定：

```text
local bar present
→ ACTUAL_TRADED

local bar missing + BaoStock tradestatus=0
→ SUSPENDED

local bar missing + BaoStock tradestatus=1
→ DATA_GAP

provider missing
→ UNKNOWN
```

正式执行结果：

```text
membership rows = 4,036,121
ACTUAL_TRADED   = 4,027,002
SUSPENDED       = 9,119
missing bar rows = 9,119
```

也就是说这 9,119 个 `SUSPENDED` 全部依赖 provider `tradestatus` 来完成 formal classification。

这不是“cross-check only”。

## 6.2 isST 更直接

V4-02 的 dated ST producer：

```text
V4_02_DATED_ST_STATUS_V1
```

直接查询：

```text
BaoStock query_daily_history_k_AStock(date)
isST
```

并把 `is_st` 作为正式 artifact。

随后：

```text
build_v4_02_price_limits.py
```

直接：

```text
is_st = isst_row.get("is_st")

is_st == 1 → RISK_WARNING
is_st == 0 → NORMAL
unknown    → PRICE LIMIT UNKNOWN
```

Receipt 甚至写明：

```text
LOCAL_TDX_PRICES + BAOSTOCK_DATED_ISST_SUPPLEMENT
```

但它实际上不是“仅 supplemental”，而是决定正式涨跌停规则状态。

## 6.3 这是合同实现冲突，不是 provider 数据真假问题

可能出现两种最终修复：

### Option A｜严格执行当前总合同

建立：

```text
LOCAL_DATED_TRADING_STATUS_V2
LOCAL_DATED_ST_IDENTITY_V2
```

由 local TDX / accepted security master / official dated evidence 产生正式事实。

BaoStock 仅：

```text
cross-check
conflict alert
supplement quality
```

无法证明的历史状态：

```text
UNKNOWN
```

### Option B｜经过独立证据后正式修改 Authority Matrix

如果证明：

```text
本地/官方无法形成可持续的 dated ST / suspension authority
而 BaoStock 字段语义、日期、修订机制足以承担该字段正式 authority
```

则必须先产生：

```text
独立 source semantics acceptance
Master Contract Amendment
新 producer contract
```

再允许 BaoStock 成为该**特定字段**的 authority。

禁止继续现在这种：

```text
合同写 cross-check
实现却当 formal truth
```

---

# 7. V4-03

## 结论

```text
NO_DIRECT_SAME_CLASS_DEFECT_FOUND
KEEP_ACCEPTED_PENDING_INPUT_DIFF_CHECK
```

V4-03 没有直接读取 BaoStock tradestatus/isST 作为算法输入。

Core factor registry / AST 中未发现：

```text
is_st
risk_status
limit_status
```

作为直接核心公式条件。

但其 accepted daily/factor lineage来自 V4-02，所以 V4-02 修复后仍必须做 exact input/output digest diff。

若 business fields 不变，不重跑算法验收。

---

# 8. V4-04｜存在真实下游传播

V4-04 明确绑定：

```text
V4_02_DATED_TRADING_STATUS_R7
```

并在：

```text
profile_primitives.technical_window_status()
```

要求窗口：

```text
actual bar dates
==
status == ACTUAL_TRADED dates

其余 calendar dates
必须全部是 SUSPENDED
```

只允许：

```text
ACTUAL_TRADED
SUSPENDED
```

任何：

```text
UNKNOWN
DATA_GAP
```

都会使窗口 invalid。

因此 V4-02 那 9,119 个由 BaoStock 证明的 `SUSPENDED`，会影响：

```text
MA10 window
POS250 window
PRIOR20 minimum liquidity
suspended_count
window_identity
input_digest
primitive quality
profile quality
```

当前 V4-04：

```text
row_count = 5222
COMPLETE = 4981
PARTIAL_UNKNOWN = 241
```

修正 authority 后这些数字可能变化。

### 裁决

```text
V4_04_ALGORITHM = KEEP
V4_04_ACCEPTED_RESULT = REVALIDATION_REQUIRED
```

禁止提前假设重算后一定相同。

---

# 9. V4-05

V4-05 Replay Gate A 直接回放 V4-04 Core Profile / factors。

因此：

```text
V4_05_ALGORITHM = KEEP
V4_05_ACCEPTED_RESULT = CONDITIONAL_REVALIDATION_REQUIRED
```

如果 V4-04 corrected logical digest 变化：

```text
必须重跑 V4-05 unchanged algorithm
```

如果 V4-04 business output 完全不变：

```text
只需 lineage amendment / digest rebinding
```

Historical AS_RECORDED 继续保持：

```text
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

**不能因为“历史可以补抓”而解锁。**

后补历史事实只证明：

```text
provider_date = T
```

不证明：

```text
knowledge_available_at = T
```

---

# 10. V4-06

## 结论

```text
KEEP_ACCEPTED
NO_SAME_CLASS_DEFECT
```

V4-06 是正确反例。

它在 2026-09-29 实际查询 2026-09-28 provider rows：

```text
target_rows_observed = 4
strict_bound_row_count = 0
```

并正确归因：

```text
binding / amount semantics / tolerance 未接受
```

没有写成：

```text
BaoStock 服务无 9/28 数据
```

说明历史指定日期查询本身在系统内已经被证明可行。

---

# 11. V4-07

Prior-RPS 当前 UNKNOWN 是：

```text
accepted publication warm-up / lineage bootstrap
```

不是 provider availability 问题。

因此既有：

```text
WP-A02-PRIOR-RPS
```

保持。

但如果 V4-05 corrected output 改变：

```text
V4-07 必须用不变算法重新计算
```

所以新增：

```text
CONDITIONAL_CASCADE_REVALIDATION
```

不重开参数。

---

# 12. V4-08

PIT membership 当前处理是正确的。

这里不能套用 BaoStock “历史指定日期补抓”的逻辑。

V4-08 的 sector membership source 是 mutable current snapshot。

若 T 当天没有冻结：

```text
今天看到的 current membership
不能证明历史 T 当时 membership
```

所以：

```text
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES
no backdating
CURRENT_MEMBERSHIP_REPLAY diagnostic only
```

是正确设计。

### 裁决

```text
V4_08_PIT_SEMANTICS = PASS
```

但若 V4-07/Base Seed 或 V4-05 输入发生变化：

```text
V4-08 real result 做 conditional cascade replay
```

---

# 13. V4-09

本轮未发现新的 provider/source-role 直接错误。

原裁决保持：

```text
V4_09_STAGE_ENGINEERING = PASS
REAL_SIGNAL = DEGRADED
PRODUCTION = FALSE
```

已有两个 hardening：

```text
WP-A08-V4-09-N01
WP-A09-V4-09-N02
```

继续执行，不需要重复创建新任务卡。

若上游 V4-07/V4-08 accepted input digest 变化：

```text
V4-09 unchanged algorithm 做 conditional replay
```

---

# 14. 分类总结

| Stage | 历史补抓 | Source Role | PIT/AS_RECORDED | 结论 |
|---|---|---|---|---|
| V4-00 | N/A | 基本正确 | N/A | KEEP |
| V4-01 | 正确 | **需 reconciliation** | 正确区分 reconstructed | TASK |
| V4-02 | 可历史查 | **正式越权** | historical diagnostic 有标注 | **REPAIR** |
| V4-03 | N/A | 未见直接问题 | N/A | KEEP + diff |
| V4-04 | N/A | **受 V4-02 status 传播** | N/A | REVALIDATE |
| V4-05 | N/A | 继承 V4-04 | AS_RECORDED 阻断正确 | REVALIDATE |
| V4-06 | 正确历史查 | 正确 supplemental | N/A | KEEP |
| V4-07 | N/A | 无同类问题 | warm-up 正确 | CONDITIONAL |
| V4-08 | 不允许伪补 PIT | 正确 | PIT 正确 | KEEP + CONDITIONAL |
| V4-09 | N/A | 无新同类问题 | N/A | KEEP + existing hardening |

---

# 15. 新增任务

本轮新增三条正式 remediation line：

```text
A10 SOURCE_AUTHORITY_AVAILABILITY_SEMANTICS_GOVERNANCE
A11 V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION
A12 V4_02_STATUS_ST_AUTHORITY_AND_DOWNSTREAM_CASCADE
```

其中：

```text
A10 = 防止再次犯同类错误
A11 = 核对历史 identity 正式 owner
A12 = 真正修复已发现的 V4-02 contract/runtime divergence
```

现有：

```text
A01 DM01
A08 V4-09 N01
A09 V4-09 N02
```

不重复创建。

---

# 16. 执行顺序修订

用户当前要求三张既有文档暂不执行。

因此推荐下一次统一执行按：

```text
Batch 0
A10 全局 Source Authority / Availability 语义门
A11 V4-01 authority reconciliation（audit-first）
A12 V4-02 status/ST authority repair + cascade baseline

Batch 1
DM01 A01 R2
必须消费 A12 已冻结的 status/ST producer contract
不能自己再定义一套 authority

Batch 2
A08 + A09 V4-09 hardening
可并行

Batch 3
A02/A03/A04/A05/A06/A07 按既有 Master Card 继续
```

主工程 V4-11/V4-12 不需要等待 Batch 0/1 全部完成才能继续编码，但：

```text
V4-14 Replay Gate B
Production/Shadow
```

必须重新读取这些 remediation 状态。

---

# 17. 最终一句话

本次 DM-01 不是孤例。

真正同类的历史问题主要集中在：

```text
V4-02：BaoStock cross-check 被实现成 formal Trade Status / ST authority
```

并已经传播到 V4-04 的技术窗口完整性，再由 V4-05 向后传递。

V4-01 还有一项 identity source-authority 合同需 reconciliation，但目前没有证据要求推翻 canonical identity。

其余阶段没有发现“本地没抓 = provider 没数据”的系统性普遍错误；V4-05/V4-08 对 AS_RECORDED/PIT 的严格阻断反而应该保留。

# A10｜Source Authority / Availability Semantics Governance 修复任务卡 R1｜2026-10-01

**Work Package：** `WP-A10-SOURCE-AUTHORITY-GOVERNANCE`  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**基线 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**优先级：** P0 Governance  
**性质：** 防止“本地缺失=provider不可用、supplemental越权、历史事实=PIT事实”再次发生。

---

# 1. 目标

建立一个全仓统一、机器可执行的：

```text
Source Role Contract
Availability State Contract
Historical Retrieval / PIT Semantics Contract
Failure Taxonomy
Consumer Gate
```

之后任何 stage / DM-01 / supplemental source 都不得自由解释 `UNAVAILABLE`。

---

# 2. Source Role 必须显式枚举

建议冻结：

```text
CORE_AUTHORITY
FIELD_AUTHORITY
SUPPLEMENTAL_CROSSCHECK
DIAGNOSTIC_ONLY
RESEARCH_ONLY
```

每个 source-family / field 必须记录：

```text
field_id
source_family
role
owner_contract_id
allowed_consumers
may_block_core
may_change_core_value
may_change_core_quality
historical_retrieval_mode
pit_requirement
```

---

# 3. Availability State 必须拆开

禁止一个 `UNAVAILABLE` 表达所有情况。

至少：

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

硬规则：

```text
PROVIDER_TARGET_DATE_EMPTY_CONFIRMED
```

只有存在真实 bounded request receipt，且 provider 对目标日期返回空/明确无数据时才能使用。

没有 request：

```text
只能写 PROVIDER_NOT_QUERIED / LOCAL_*_MISSING
```

---

# 4. Historical Retrieval Mode

至少冻结三类：

## A. TARGET_DATE_QUERYABLE_FACT

例：

```text
BaoStock query_all_stock(day=T)
BaoStock DailyUpdates(date=T)
```

允许 T+n 后补抓。

但必须保留：

```text
provider_date = T
observed_at = T+n
received_at = T+n
origin = DELAYED_HISTORICAL_RETRIEVAL
```

不能反向证明 `first_available_at=T`。

## B. AS_RECORDED_PIT_FACT

需要：

```text
first_available_at
source_revision
knowledge_time
```

没有证据：

```text
历史 AS_RECORDED 必须 UNKNOWN / BLOCKED
```

## C. MUTABLE_CURRENT_SNAPSHOT

例：

```text
sector membership current file
```

未在 T 冻结时：

```text
不得用今天的 snapshot 假装 T 当时 snapshot
```

只能：

```text
CURRENT_MEMBERSHIP_REPLAY / DIAGNOSTIC
```

---

# 5. Supplemental Gate

机器门必须 enforce：

```text
SUPPLEMENTAL_CROSSCHECK
```

默认：

```text
may_block_core = false
may_change_core_value = false
```

如果某 consumer 要让 supplemental 成为 required input：

必须同时满足：

```text
explicit field-level owner contract
external source-semantics acceptance
consumer contract explicitly declares required
```

否则：

```text
SUPPLEMENTAL_MAY_NOT_BLOCK_CORE
```

---

# 6. Runtime Capability 与 Target Data 分离

所有外部 provider contract 都要区分：

```text
Runtime Capability Acceptance
Target-Date Data Capture
```

Runtime acceptance 验证：

```text
SDK
auth
endpoint
method
schema
quota/budget
```

不应该天然绑定某个 target date。

Target capture 验证：

```text
target/provider date
row set
revision
digest
observed_at
```

---

# 7. Error Taxonomy

统一错误命名，至少：

```text
LOCAL_ACCEPTED_FREEZE_MISSING
LOCAL_SOURCE_BYTES_MISSING
PROVIDER_NOT_QUERIED
PROVIDER_QUERY_FAILED
PROVIDER_TARGET_EMPTY
SOURCE_PUBLICATION_PENDING
RUNTIME_CAPABILITY_UNACCEPTED
SUPPLEMENTAL_UNAVAILABLE
CORE_REQUIRED_SOURCE_UNAVAILABLE
PIT_FIRST_AVAILABILITY_UNPROVEN
PIT_SOURCE_NOT_FROZEN_AT_TARGET
```

禁止模糊错误：

```text
DATA_MISSING
SOURCE_UNAVAILABLE
BAOSTOCK_MISSING
```

除非附带 scope-qualified reason。

---

# 8. Machine Governance Tests

至少新增：

```text
supplemental missing cannot block unrelated Core
supplemental conflict cannot overwrite Core authority
not-queried cannot become provider-unavailable
target-date historical query observed later retains late observed_at
historical catch-up cannot mint first_available_at
mutable current snapshot cannot backdate PIT
core authority missing does block declared capability
field authority may block only its own declared consumers
```

---

# 9. Positive Controls

用现有真实项目案例作为 golden governance vectors：

```text
V4-01 historical roster re-query
= TARGET_DATE_QUERYABLE_FACT positive control

V4-06 2026-09-29 query 2026-09-28 BaoStock
= historical target query positive control

V4-05 Historical AS_RECORDED blocked
= PIT first-availability negative control

V4-08 sector membership no backdating
= mutable snapshot PIT negative control

DM01 old same-day-only BaoStock runtime gate
= regression negative control
```

---

# 10. Repository Scan

实现一个静态/结构化扫描：

检查：

```text
config
src
scripts
accepted head
stage candidate manifest
```

发现：

```text
role=SUPPLEMENTAL but consumer hard requires it
role=cross-check but output becomes formal value
provider NOT_QUERIED yet reason says unavailable
same-day-only guard on historical-queryable API
today-observed data written with target-day observed_at
```

输出：

```text
reports/audits/V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R1.json
```

---

# 11. 不允许的操作

本 WP 不得：

```text
重写任何 Accepted Head
自动修业务数据
直接改变 V4-01/V4-02 formal outputs
修改历史 migration
把 existing open audit 自动关闭
```

它先建立治理门和扫描结果。

业务修复由 A11/A12/DM01 分别执行。

---

# 12. Acceptance Gates

至少：

```text
A10-G01 source role schema frozen
A10-G02 availability schema frozen
A10-G03 historical mode schema frozen
A10-G04 error taxonomy frozen
A10-G05 supplemental gate executable
A10-G06 not-queried/provider-unavailable negative test PASS
A10-G07 delayed historical retrieval lineage test PASS
A10-G08 PIT no-backdating tests PASS
A10-G09 repo scan generated
A10-G10 existing accepted algorithms unchanged
A10-G11 clean detached regression PASS
A10-G12 independent external audit
```

---

# 13. Codex 最终允许状态

```text
A10_SOURCE_AUTHORITY_GOVERNANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不得自行：

```text
A10_ACCEPTED
PRODUCTION_READY
```

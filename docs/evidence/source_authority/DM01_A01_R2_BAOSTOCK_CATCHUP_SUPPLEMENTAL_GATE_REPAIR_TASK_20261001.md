# DM-01 A01 R2｜BaoStock 历史补抓与 Supplemental Gate 修复任务卡｜2026-10-01

**前置裁决：**

```text
DM01_A01_ENGINEERING_ADAPTERS = KEEP_PASS_ENGINEERING_SCOPE
DM01_A01_REAL_SOURCE_ACCEPTANCE = BLOCKED_R2
```

本任务禁止重写 9 个已经通过 engineering checks 的 adapters。只修 source-authority、historical catch-up 和 supplemental gating。

---

# P0-1 Runtime Capability 与 Target-Date Capture 解耦

新增版本化合同，不静默改写历史 acceptance。

建议：

```text
BAOSTOCK_DM01_RUNTIME_CAPABILITY_V2
BAOSTOCK_DM01_TARGET_DATE_CAPTURE_V2
```

Runtime capability 验证：

```text
SDK version/hash
auth mode
connected endpoint
query_daily_history_k_AStock callable
query_daily_adjust_factor callable
required fields/schema
bounded request budget
```

不得再要求：

```text
live_smoke.target_date == target_trade_date
local_today == target_trade_date
```

Smoke 可以选最近一个已完成且 provider 可查询日期，只证明 runtime 能力。

---

# P0-2 支持 delayed historical catch-up

正式允许：

```text
current observation date = 2026-10-01
target/provider date = 2026-09-28
```

查询：

```text
query_daily_history_k_AStock(date="2026-09-28")
query_daily_adjust_factor(date="2026-09-28")
```

冻结字段至少：

```text
target_trade_date
provider_date
observed_at
received_at
source_revision_id
response_sha256
runtime_capability_id
origin = DELAYED_HISTORICAL_RETRIEVAL
```

禁止写：

```text
observed_at = 2026-09-28
first_available_at = 2026-09-28
AS_RECORDED_AT_CLOSE = true
```

如果 provider 返回 9/28 rows：

```text
说明此前只是 local freeze 缺失
```

如果 provider 真返回空/错误：

```text
才允许记录 PROVIDER_TARGET_DATE_UNAVAILABLE
```

并必须附实际 request receipt。

---

# P0-3 BaoStock 从 Core required gate 降回 supplemental

按 master contract：

```text
TDX = canonical Core authority
BaoStock = supplemental / cross-check
```

必须区分：

```text
required_source_families
supplemental_source_families
```

`source_freeze_complete_v2` / DM01 `_context()` 不能因为 BaoStock missing 直接让所有 9 components fail。

BaoStock unavailable 时：

```text
BaoStock crosscheck = UNKNOWN/UNAVAILABLE
```

不得影响有本地 accepted authority 的：

```text
RAW_DAILY
ADJUSTED_DAILY
PERIOD_RAW
PERIOD_ADJUSTED
PRICE_LIMIT
SPECIAL_PHASE
```

---

# P0-4 Identity / Trading Status / ISST authority 修正

重新核对 owner contract。

正式原则：

```text
identity / security type / lifecycle
→ accepted local dated identity

trading status
→ local TDX/calendar facts authoritative
BaoStock tradestatus = cross-check only

ST
→ accepted local dated ST identity authoritative
BaoStock isST = cross-check only
```

因此：

```text
build_identity_universe()
build_trading_status()
build_isst()
```

不得把 BaoStock presence 当唯一正式事实来源。

若本地 ST authority 当前不完整：

```text
ISST only = DEGRADED/UNKNOWN
```

而不是：

```text
全局 DM01 BLOCKED
```

---

# P0-5 Adjustment factor role

BaoStock `query_daily_adjust_factor`：

```text
AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY
```

继续保持。

Canonical adjusted daily：

```text
GBBQ / accepted adjustment contract
```

BaoStock factor snapshot missing：

```text
不能阻断 ADJUSTED_DAILY
```

除非未来另有正式 accepted consumer contract。

---

# P0-6 真实 9/28 补抓必须实际执行

修复后必须实际发起 bounded query。

Evidence 必须显示：

```text
request_count > 0
target_trade_date = 2026-09-28
provider_date = 2026-09-28
observed_at = actual current timestamp
```

不得再次仅凭：

```text
local manifest missing
```

宣称 provider unavailable。

---

# P0-7 Real all-nine candidate

利用已存在：

```text
TDX 2026-09-28 accepted frozen package
GBBQ target-eligible accepted snapshot
accepted calendar
accepted parent Data Head
```

加修复后的 authority/catch-up，真正运行 all-nine target candidate。

若 supplemental unavailable：

```text
按 capability scope 降级
```

而不是全局阻断。

---

# P0-8 Independent postcheck

独立检查：

```text
TDX package exact
target rows exact date
identity authority exact
local trading status authority
local ST authority / explicit UNKNOWN
BaoStock delayed-capture lineage
BaoStock no Core overwrite
GBBQ exact
period arithmetic
price-limit
special phase
all component parent/source/calendar consistency
```

独立 oracle 不得复用 adapter 自己的 helper 得出同一结论。

---

# P1-1 修订 failure taxonomy

新增至少：

```text
LOCAL_ACCEPTED_FREEZE_MISSING
HISTORICAL_CATCHUP_NOT_AUTHORIZED
HISTORICAL_CATCHUP_QUERY_FAILED
PROVIDER_TARGET_DATE_EMPTY
SUPPLEMENTAL_SOURCE_UNAVAILABLE
CORE_REQUIRED_SOURCE_UNAVAILABLE
```

禁止把这些统称：

```text
BAOSTOCK_DATA_MISSING
```

---

# P1-2 历史证据治理

此次 10/1 补抓的 9/28 BaoStock：

```text
可以支持 exact target facts/cross-check
```

但不得用于证明：

```text
9/28 当天我们已经知道
9/28 first-availability
历史 AS_RECORDED lineage
```

`HISTORICAL_AS_RECORDED_ADJUSTED_PRICE` 等独立 audit 不得因此自动关闭。

---

# 必须保留

不得修改：

```text
V4_09_ACCEPTED_HEAD
V4_10_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD（外部接受前）
V4_DEV_BASELINE_HEAD
```

9 个 engineering adapter 当前通过的算法/contract，只做必要 source boundary 修订。

---

# Required Tests

至少：

```text
runtime capability accepted on date A
capture target date B where B < today
provider exact-date rows pass
provider empty rows classified correctly
observed_at later than provider_date retained
no backdating
BaoStock absent does not block TDX Core components
BaoStock conflicts do not overwrite local facts
local trading status survives BaoStock missing
local ST survives BaoStock missing
ST local unknown degrades only ISST
BaoStock factor missing does not block GBBQ adjusted daily
all-nine real target run
same target retry idempotent
delayed provider revision creates new source revision
Data Head remains unchanged before external acceptance
```

---

# Codex 完成后唯一允许状态

```text
DM01_A01_R2_REAL_TARGET_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行声明：

```text
A01_CLOSED
DATA_HEAD_PROMOTED
PRODUCTION_READY
```

外部复审通过后再单独执行 Data Head promotion。

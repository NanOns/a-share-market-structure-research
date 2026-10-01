# WP-A01 DM-01 Real Incremental Builders 实现任务卡 R1｜2026-10-01

**Audit ID：** `DM01_REAL_INCREMENTAL_BUILDERS`  
**Work Package：** `WP-A01-DM01`  
**优先级：** P0  
**当前 Data Accepted Head：** `2026-09-24`  
**当前 registry：** `BLOCKED_TARGET_DATE_ADAPTER_APIS_MISSING`  
**任务性质：** 真正实现代码，不是再做治理登记

---

# 1. 目标

真正实现 DM-01 的 9 个 accepted target-date incremental adapters：

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

目标不是重写 V4-01/V4-02 算法，而是把已接受 domain runtime 封装成：

```text
target session
+
parent accepted data head
+
accepted source/calendar/identity
→
staging component candidate
→
independent postcheck
→
atomic Data Head promotion candidate
```

---

# 2. 硬禁止

禁止：

```text
test_builder
fake_builder
fallback_builder
dynamic function discovery
复制旧算法另写一套公式
直接调用 frozen historical CLI 当 incremental adapter
绕开 accepted runtime
部分 component 成功就移动 Data Head
修改 V4_STAGE_ACCEPTED_HEAD
把 staging 结果直接冒充 accepted
```

---

# 3. 统一 Builder Contract

每个 builder 必须提供正式 callable：

```python
build_<capability>(
    target_trade_date,
    parent_data_head,
    source_freeze,
    calendar_binding,
    identity_binding,
    staging_root
) -> ComponentCandidate
```

返回至少：

```text
component_id
contract_id
target_trade_date
parent_data_head_digest
source_revision
calendar_publication_id
identity_publication_id
runtime_bindings[]
input_publication_ids[]
artifact_path
artifact_sha256
logical_digest
row_count
quality_counts
unknown_reason_counts
postcheck_digest
```

每个 adapter 都必须明确：

```text
accepted owner stage
accepted algorithm contract
accepted runtime path + SHA
target-date input contract
output contract
UNKNOWN/degraded policy
```

---

# 4. RAW_DAILY

必须消费：

```text
TDX_PACKAGE_DELTA_V1.target_bars
CURRENT_LIFECYCLE_SNAPSHOT_V1
```

复用 accepted：

```text
date_identity
check_raw_quality
```

必须满足：

```text
target date only
no duplicated security/date
official package identity retained
quality explicit
source digest explicit
```

不得用全历史 rebuild 代替 target-date adapter。

---

# 5. IDENTITY_UNIVERSE

复用：

```text
discover_identity_events
build_current_lifecycle_snapshot
```

输入：

```text
parent accepted universe
BaoStock roster
official session bridge
dated identity records
```

必须：

```text
absence != delisting
code change continuity explicit
security type explicit
knowledge time explicit
parent universe identity explicit
```

---

# 6. TRADING_STATUS

必须把 accepted historical domain logic 抽出为 target-date callable。

保留：

```text
local TDX bar precedence
BaoStock only cross-check
missing != suspension
conflict explicit
```

历史 frozen CLI 只能作为参考/回归，不得作为正式 incremental entrypoint。

---

# 7. ISST

必须提供 target-date callable。

规则：

```text
dated ST identity
knowledge time
UNKNOWN explicit
```

禁止：

```text
current ST status → retroactive historical fill
```

---

# 8. ADJUSTED_DAILY

复用：

```text
read_gbbq
build_affine_factors
adjust_ohlc
```

输入：

```text
RAW_DAILY_INCREMENT
accepted GBBQ snapshot
per-security adjustment disposition
target cutoff
```

unsupported corporate action：

```text
继续 per-security fail-closed
```

DM-01 不得为了推进 Data Head 放宽 V4-02 的 adjustment capability boundary。

---

# 9. PERIOD_RAW / PERIOD_ADJUSTED

必须实现：

```text
parent period state
+
target daily session
```

不能每次整历史重建冒充 incremental。

输出要求：

```text
weekly/monthly
as_of only
closed period preserved
current partial period revisioned
parent period publication bound
```

必须覆盖：

```text
week boundary
month boundary
holiday
suspension
new listing
same-day source revision
```

---

# 10. PRICE_LIMIT

调用 accepted：

```text
run_builder
apply_row_runtime
```

DM-01 只负责：

```text
target-date input selection
staging artifact
receipt
lineage
```

禁止重写涨跌停公式或 special phase policy。

---

# 11. SPECIAL_PHASE

绑定：

```text
CURRENT_LIFECYCLE_SNAPSHOT
SPECIAL_PHASE_SOURCE_MANIFEST
accepted event store
accepted policy
```

必须允许合法：

```text
NO_EVENT
```

manifest。

没有事件：

```text
≠ source failure
```

---

# 12. Atomic Orchestrator

DM-01 orchestrator 必须成为：

```text
resolve next target session
→ freeze parent/source/calendar/identity
→ stage 9 components
→ component postchecks
→ cross-component postchecks
→ candidate manifest
→ promotion candidate
```

任何一个 component FAIL：

```text
V4_DATA_ACCEPTED_HEAD 不移动
staging evidence 保留
accepted namespace 不可见
```

不得部分发布。

---

# 13. Cross-component Checks

至少：

```text
RAW_DAILY covers required active identities
TRADING_STATUS identity/date aligned
ISST identity/date aligned
ADJUSTED_DAILY raw binding exact
PERIOD_RAW source daily digest exact
PERIOD_ADJUSTED adjusted daily digest exact
PRICE_LIMIT canonical daily source exact
SPECIAL_PHASE identity/date exact
all components share same target calendar session
all components share same parent Data Head
all component source revisions declared
```

---

# 14. Target Session Resolution

当前 parent：

```text
2026-09-24
```

实现不得硬编码目标为：

```text
2026-09-28
2026-09-30
```

正式逻辑：

```text
parent accepted session
→ exchange calendar
→ nearest next completed market session
→ source readiness
```

如果中间一个 required session 缺 source：

```text
BLOCKED_MISSING_INTERMEDIATE_SESSION
```

不得跨洞跳到后一天。

同一 target 重跑：

```text
必须 deterministic / idempotent
```

source revision 改变：

```text
必须产生新 revision
不能覆盖旧 candidate
```

---

# 15. Data Head Promotion Discipline

本 WP 只做到：

```text
Data Head promotion candidate
```

Codex 不得自行写正式：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

只有独立外部验收通过后，另发 promotion。

必须保持：

```text
V4_STAGE_ACCEPTED_HEAD 不变
V4_DEV_BASELINE_HEAD 不变
```

---

# 16. Required Negative Tests

至少覆盖：

```text
wrong parent head
wrong target date
skipped intermediate market session
duplicate raw row
identity/date mismatch
trading_status conflict
missing != suspension
ST unavailable
unsupported corporate action
adjusted/raw source mismatch
weekly boundary
monthly boundary
period parent mismatch
price-limit source mismatch
special-phase valid no-event
special-phase malformed event
component failure atomic rollback
candidate digest mismatch
same target rerun idempotent
source revision creates new candidate revision
partial component output invisible
```

---

# 17. Independent Arithmetic / Identity Postcheck

Postcheck 不得调用被测 adapter 自己作为 oracle。

至少独立重算/核对：

```text
target trade date
row identity uniqueness
raw OHLCV/amount samples
trading status samples
ST samples
adjusted OHLC samples
weekly/monthly aggregation samples
price-limit samples
special-phase samples
source/artifact digests
parent/target continuity
```

---

# 18. Clean Regression

至少覆盖：

```text
tests/v4_01
tests/v4_02
DM-01 tests
V4-03...V4-10 required smoke
tests/v4_joint
no-symbol governance
```

不得新增未经授权 deselect。

---

# 19. Evidence

至少生成：

```text
reports/dm01/DM01_A01_CONTRACT_FREEZE_R1.json
reports/dm01/DM01_A01_BUILDER_EXPORTS_R1.json
reports/dm01/DM01_A01_TARGET_SESSION_RESOLUTION_R1.json
reports/dm01/DM01_A01_COMPONENT_POSTCHECK_R1.json
reports/dm01/DM01_A01_CROSS_COMPONENT_POSTCHECK_R1.json
reports/dm01/DM01_A01_ATOMIC_FAILURE_PROBES_R1.json
reports/dm01/DM01_A01_DETERMINISM_R1.json
reports/dm01/DM01_A01_REAL_NEXT_SESSION_CANDIDATE_R1.json
reports/dm01/DM01_A01_CLEAN_CHECKOUT_R1.json
reports/dm01/DM01_A01_EXTERNAL_REAUDIT_HANDOFF_R1.json
reports/dm01/DM01_A01_CLOSURE_R1.md
```

Closure 必须列出 9 个 capability 各自：

```text
PASS
DEGRADED_PASS
BLOCKED
```

及具体原因。

---

# 20. 本 WP 完成状态

Codex 完成后最多声明：

```text
DM01_A01_INCREMENTAL_BUILDERS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止：

```text
DM01_ACCEPTED
V4_DATA_ACCEPTED_HEAD_ADVANCED
A01_CLOSED
```

独立外部审计通过后才允许 promotion。

---

# 21. 与主工程线关系

WP-A01 与 V4-11 并行。

禁止：

```text
因为 DM-01 尚未 external accepted
而停止 V4-11 / V4-12 独立工程开发
```

但任何需要“最新 accepted daily data”的正式 consumer 必须继续受：

```text
V4_DATA_ACCEPTED_HEAD
```

capability gate 约束。

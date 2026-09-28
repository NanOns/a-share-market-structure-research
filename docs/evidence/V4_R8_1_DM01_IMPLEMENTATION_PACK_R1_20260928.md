# 大A市场结构研究系统 V4｜R8.1 Identity Event Discovery + Continuous Data Maintenance V1 实施包

> 文档编号：DA-MSR-V4-R8.1-DM01-IMPLEMENTATION-PACK-R1-20260928  
> 日期：2026-09-28  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 输入 HEAD：`8941119dba4fb8c75d98699f8fa92c3406de9811`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> 任务类型：Pre-V4-03 基础设施收尾 + 持续增量数据轨  
> **禁止开始 V4-03。**

# 0. 总原则

本任务允许合并实施，但验收必须严格拆成两个 Gate：

```text
Gate A
= V4-01 R8.1 Identity Event Discovery / Joint 00-01-02 Reseal

Gate B
= V4-DM-01 Continuous Data Maintenance / Daily Incremental Lane
```

必须分别拥有：

```text
contract
tests
receipt
independent postcheck
external-review package
```

禁止 Gate B 跑通就推断 Gate A PASS，也禁止 Gate A PASS 就推断 Gate B PASS。

---

# 1. Gate A｜SECURITY_IDENTITY_EVENT_DISCOVERY_V1

目标：

```text
把“代码变更 / 身份连续性发现”
从一次性历史修补
升级为历史 + 未来共用的通用事件发现组件。
```

运行模式：

```text
HISTORICAL_BACKSCAN
DAILY_INCREMENTAL
```

# 2. Candidate Signal Union

至少支持：

```text
OFFICIAL_CODE_CHANGE_EVENT
DATED_ALIAS_FACT
ROSTER_EXIT_ENTRY_ADJACENCY
LIFECYCLE_BOUNDARY_ADJACENCY
PERSISTENT_RETROSPECTIVE_BAR_ALIAS
SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE
```

任何单一弱信号都只能生成 candidate，不得直接 merge identity。

# 3. 非重叠代码变化必须可发现

必须覆盖：

```text
OLD_CODE active through T-1
NEW_CODE active from T
```

即使：

```text
shared_bar_sessions = 0
```

也必须进入 candidate set。

Candidate 可来源于：

```text
dated roster transition
lifecycle effective boundary
official notice index
provider listing/outDate relation
name/company continuity（仅弱信号）
```

# 4. Official / Versioned Evidence Gate

确认：

```text
CONFIRMED_SAME_ENTITY_CODE_CHANGE
```

必须绑定：

```text
official exchange notice
或 versioned independently accepted identity evidence
```

并保存：

```text
source_ref
source_capture_path
source_capture_sha256
effective_date
observed_at
system_available_at
```

# 5. Code Reuse

同一代码后来由另一实体使用时：

```text
CONFIRMED_DISTINCT_ENTITY
```

不得错误 merge。

Stable identity 必须考虑：

```text
lifecycle interval
listing anchor
effective date
official identity evidence
```

# 6. Unresolved

无法确认：

```text
UNRESOLVED
```

对 affected formal capability：

```text
identity = UNKNOWN
```

Required Scope historical seal：

```text
unresolved candidate > 0
→ BLOCKED
```

# 7. Gate A Required Tests

至少：

```text
test_non_overlapping_code_transition_is_discovered
test_roster_exit_entry_boundary_becomes_candidate
test_lifecycle_boundary_without_shared_bar_is_candidate
test_overlapping_retrospective_alias_is_candidate
test_existing_alias_fact_is_candidate
test_true_code_reuse_resolves_distinct
test_weak_name_match_does_not_merge
test_unresolved_candidate_fails_closed
test_candidate_union_deduplicates_same_event
test_no_specific_security_literals_in_discovery_logic
test_300114_302132_remains_fixture_only
test_required_scope_unresolved_zero_required_for_joint_pass
```

# 8. Gate A Output

至少：

```text
config/security_identity_event_discovery_v1.json

reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json

reports/v4_01/V4_01_ALIAS_COMPLETENESS_R8_1.json

reports/v4_01/v4_01_final_stage_receipt_R8_1_*.json

reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R2_*.json
```

如果没有发现新 historical counterexample：

```text
R7 canonical artifact hashes 保持不变
```

只 reseal completeness proof。

如果发现新 counterexample：

```text
仅 affected identity/date scope 定点修复并向下游重建
```

禁止默认全量重跑 V4-02。

---

# 9. Gate B｜V4-DM-01 Continuous Data Maintenance V1

这是长期运行的数据维护轨，不属于 V4-03。

目标：

```text
系统升级持续数周/月期间，
每个新增交易日的数据持续冻结、追加、校验、发布，
避免开发完成时出现数据断层。
```

# 10. 三个 Head 必须严格分离

## 10.1 Stage Accepted Head

```text
V4_00/01/02_STAGE_ACCEPTED_HEAD
```

表示阶段验收基线。Daily Maintenance 禁止改变其历史语义。

## 10.2 Data Accepted Head

新增：

```text
V4_DATA_ACCEPTED_HEAD
```

每天移动，绑定：

```text
accepted trade_date
source revision
canonical data revision
component permissions
```

## 10.3 Development Baseline Head

新增：

```text
V4_DEV_BASELINE_HEAD
```

以后开发 V4-03/04... 时显式冻结。

Daily Head 更新：

```text
不得自动移动 DEV_BASELINE_HEAD
```

# 11. Initial Bootstrap

Daily Data Head 初始 bootstrap：

```text
base_cutoff = 2026-09-24
```

引用现有 accepted：

```text
V4-01 canonical identity/universe
V4-02 R6 canonical artifacts
```

不得复制整套历史大文件。

只生成：

```text
bootstrap manifest
parent hashes
component cutoffs
```

# 12. Catch-Up Mode

新增：

```text
CATCH_UP
```

自动发现：

```text
last accepted trade_date
之后到 target cutoff 之间
所有正式交易 session
```

按日期严格顺序：

```text
T1 -> T2 -> T3 ...
```

如果中间某日 required head：

```text
BLOCKED
```

则不得跳过该日直接 promote 更晚 Data Head。

可以继续 staging，但不能跨 gap 发布。

# 13. 交易日不能靠“有没有bar”猜

必须扩展正式 exchange calendar。

要求：

```text
official/versioned session truth
```

周末/节假日：

```text
NO_SESSION
```

不得因为所有股票都没 bar 才推断休市。

# 14. Daily Source Freeze

每个目标 session T，在任何 canonical 计算前冻结：

```text
SOURCE_FREEZE_MANIFEST(T)
```

至少包含：

```text
TDX source snapshot identity
exchange calendar revision
BaoStock daily supplement source identity
GBBQ / gbbq.map snapshot
identity / lifecycle event input manifest
special price phase event input manifest
observed_at
ingested_at
system_available_at
sha256 / bytes / source revision
```

# 15. TDX Increment

正式优先级继续遵守：

```text
accepted local TDX chain
>
validated downloaded TDX package overlap
```

对于新日期：

```text
local fresh
→ 使用 local

local missing + accepted package available
→ package 可填 local-missing

local/package conflict
→ local wins
→ conflict receipt
```

禁止下载包覆盖用户本地 TDX 根目录。

# 16. TDX 增量 source identity

不要求每天重 hash 全部历史文件。

可以：

```text
previous source manifest
+
changed-file manifest
+
consumed source file hashes
```

形成增量 source identity。

但每个新 row 必须可追溯到：

```text
source file
source revision
parser
trade_date
```

# 17. Identity / Lifecycle Daily Delta

每个 T 运行：

```text
SECURITY_IDENTITY_EVENT_DISCOVERY_V1
mode = DAILY_INCREMENTAL
```

至少检查：

```text
new listing
delisting
code change
code reuse
roster disappearance / appearance
board change
lifecycle boundary
```

具体股票是数据，不能进入算法分支。

# 18. Raw Canonical Daily

只追加新 trade_date。

Raw facts：

```text
immutable
```

如果源出现 correction：

```text
append new source revision
```

不得覆盖旧 raw observation。

# 19. Trading Status

继续遵守：

```text
actual local TDX bar
→ ACTUAL_TRADED

no bar
!= SUSPENDED
```

必须结合：

```text
calendar
identity/lifecycle
BaoStock dated status
accepted status rules
```

无法确认：

```text
UNKNOWN
```

# 20. BaoStock Daily

复用已接受 public route。

优先：

```text
full-market daily query per date
```

而不是：

```text
security × date
```

正式保存：

```text
tradestatus
isST
provider date
binding quality
query receipt
```

Turnover 仍不实现，继续归 V4-06。

# 21. GBBQ Daily Snapshot

从现在开始每天冻结：

```text
gbbq
gbbq.map
```

保存：

```text
sha256
bytes
observed_at
ingested_at
system_available_at
snapshot_id
```

作为未来真正 PIT_OBSERVED adjustment lineage 的基础。

# 22. Evidence Origin 按 source family 保存

允许：

```text
PIT_OBSERVED
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
DIAGNOSTIC_NON_PIT
```

禁止用一个全局标签掩盖不同 source family。

# 23. 2026-09-24 后的 Bridge

当前 V4-02 formal historical cutoff：

```text
2026-09-24
```

此前已冻结：

```text
第一批 go-forward GBBQ PIT eligible trade date
= 2026-09-28
```

所以 catch-up 时，对任何：

```text
2026-09-24 < T < 2026-09-28
```

如果当时没有正式 frozen source-consumption set：

```text
不得标 PIT_OBSERVED
```

必须按实际证据：

```text
RECONSTRUCTED_ASOF
或
DIAGNOSTIC_NON_PIT
```

具体日期是否交易日由正式 calendar discovery 决定，不得硬编码。

# 24. Adjusted Daily Increment｜关键要求

普通无公司行为日：

```text
只追加 T adjusted row
```

但如果新的 GBBQ/company-action revision 导致：

```text
QFQ historical coordinate changed
```

不能只算当天。

必须生成：

```text
ADJUSTMENT_IMPACT_SET
```

只对 affected security：

```text
recompute affected historical adjusted series
```

形成新 revision。

禁止每天全市场全历史重算，也禁止新公司行为发生后历史 QFQ 保持旧坐标。

# 25. Adjustment Revisions

必须保存：

```text
security_id
affected_from
affected_to
source_snapshot_id
old_adjustment_revision
new_adjustment_revision
row_count_changed
old_digest
new_digest
reason
```

旧 adjusted revision 不删除。

# 26. Weekly / Monthly Increment

Raw period：

```text
当前周/月 AS_OF_PARTIAL 更新
```

到 period_last_session：

```text
CLOSED_ONLY
```

历史 CLOSED raw period 不动。

如果 affected security 的 adjusted history因公司行为 revision 改变：

```text
只重建该 security 的 affected adjusted weekly/monthly revision
```

# 27. Price Limit Increment

每日只计算目标 T：

```text
identity
board
listing phase
isST
previous official close state
special price phase
corporate action reference
```

继续使用已接受 generic Price Limit runtime，不得建立第二套实现。

# 28. Special Price Phase Daily Events

复用：

```text
SPECIAL_PRICE_PHASE_EVENT_V1
```

增量 event：

```text
IPO
DELISTING_FIRST_DAY
DELISTING_PERIOD
RELISTING_FIRST_DAY
SPECIAL_REFERENCE_RESET
```

事件证据不足：

```text
UNKNOWN_SPECIAL_PHASE
```

fail closed。

# 29. Daily QA / Cross-Component Invariants

每个 session 至少：

```text
one canonical identity per security/date
no duplicate stable-id/date
Universe key set compatible with status/isST/price-limit
actual traded -> bar exists
suspended -> no fabricated zero return
Adjusted readiness never falls back to raw silently
period max_source_trade_date <= head cutoff
no post-cutoff source row
special phase policy version bound
source hashes match
TDX root write count = 0
```

# 30. Data Head Capability Status

每个 capability 单独：

```text
FULL_PASS
DEGRADED_PASS
BLOCKED
NOT_APPLICABLE
```

至少区分：

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

# 31. Promotion Rule

只有：

```text
required component 没有 BLOCKED
atomic postcheck PASS
source freeze complete
```

才可 promote：

```text
V4_DATA_ACCEPTED_HEAD
```

真实、合同允许的 per-security fail-closed 可以 `DEGRADED_PASS`，但必须显式列：

```text
affected security/date/component/reason
```

工程未实现不得包装成 degraded。

# 32. Atomic Publication

完整顺序：

```text
STAGING
→ SOURCE_FREEZE_COMPLETE
→ COMPONENT_BUILD
→ INDEPENDENT_POSTCHECK
→ CANDIDATE_MANIFEST
→ ATOMIC HEAD SWAP
```

失败时 previous `V4_DATA_ACCEPTED_HEAD` 保持不变。

# 33. Idempotency

同一个：

```text
trade_date
+
source manifest digest
+
contract digest
```

重复运行：

```text
NOOP_ALREADY_ACCEPTED
```

如果 source revision 改变：

```text
创建新 revision
supersedes previous
```

# 34. Development Isolation

Daily Data Head 更新不能自动改变开发阶段验收数据集。

以后 V4-03 等阶段正式 acceptance 仍使用：

```text
explicit DEV_BASELINE_HEAD
```

可额外运行：

```text
LATEST_DATA_SMOKE
```

但 smoke 不能替代 frozen acceptance。

# 35. DM-01 禁止提前实现上层

DM-01 禁止计算：

```text
V4-03 factors
V4-04 profile
V4-08 sector
V4-10 state
V4-15 radar
```

只负责 00/01/02 已验收数据底座的持续维护。

# 36. 建议文件

至少：

```text
config/v4_continuous_data_maintenance_v1.json
config/v4_data_accepted_head_v1.json

src/workbench_analysis/continuous_data_maintenance.py
src/workbench_analysis/daily_source_freeze.py
src/workbench_analysis/daily_data_head.py

scripts/run_v4_continuous_data_maintenance.py
scripts/independent_v4_dm01_postcheck.py

tests/v4_dm01/
```

命名可调整，但职责不可混淆。

# 37. Daily Head

建议：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

只保存小型 pointer/manifest。

每次 immutable receipt：

```text
reports/v4_dm01/YYYYMMDD/
```

大型新增数据继续放 artifact_store，遵守 artifact governance。

# 38. DM-01 Required Tests

至少覆盖：

```text
test_no_new_session_is_noop
test_one_session_increment
test_multi_session_catchup_is_strictly_sequential
test_weekend_holiday_not_inferred_from_missing_bars
test_stale_tdx_blocks_required_raw_increment
test_local_tdx_wins_overlap_conflict
test_same_source_digest_is_idempotent
test_source_revision_creates_new_revision
test_crash_before_head_swap_keeps_old_head
test_new_listing_identity_delta
test_delisting_identity_delta
test_nonoverlap_code_change_daily_candidate
test_code_reuse_not_merged
test_suspension_does_not_mean_data_gap
test_resume_carries_previous_official_close
test_isst_change
test_gbbq_snapshot_frozen_before_adjustment_build
test_corporate_action_recomputes_only_affected_adjusted_history
test_unsupported_adjustment_fails_closed
test_weekly_asof_partial
test_weekly_closed_on_formal_period_last_session
test_monthly_asof_partial
test_monthly_closed_on_formal_period_last_session
test_holiday_shortened_week
test_special_price_phase_increment
test_bridge_date_not_claimed_pit_observed_without_snapshot
test_pit_eligible_date_uses_frozen_source_set
test_data_head_move_does_not_move_dev_baseline
test_data_head_move_does_not_modify_stage_accepted_head
test_cross_component_key_consistency
test_atomic_publication_and_rollback
```

# 39. DM-01 Initial E2E

代码完成后：

```text
BOOTSTRAP_FROM_2026_09_24_ACCEPTED_HEAD
```

然后自动发现所有已完成 exchange session，按顺序 catch-up 到：

```text
运行时最新可完整获取的已完成 session
```

不得硬编码目标日期。

# 40. Initial E2E 输出

至少：

```text
bootstrap receipt
discovered session list
per-session source freeze receipt
per-session build receipt
adjustment impact receipt
period impact receipt
independent postcheck
final data head promotion receipt
```

# 41. Source Not Ready

例如：

```text
TDX 尚未更新到目标日
```

必须：

```text
SOURCE_NOT_READY
```

不得用 BaoStock OHLC 顶替 TDX。

# 42. 性能记录

DM-01 必须记录：

```text
wall time
CPU time
peak memory
rows read
rows written
securities affected
```

在正式性能 owner stage 之前：

```text
只记录
不后验拍阈值
```

明显全量重跑属于架构失败，需要修复。

# 43. Gate B Final Receipt

至少生成：

```text
V4_DM01_FINAL_RECEIPT_R1
```

明确：

```text
stage_00_01_02_modified = false
v4_03_implementation_started = false

bootstrap_cutoff
latest_data_cutoff
processed_sessions
blocked_sessions

source lineage states
component statuses

data_head_sha
dev_baseline_sha
stage_head_sha

test receipt
independent postcheck
```

# 44. 提交规则

本实施包可以一次开发多个相邻功能，但最终必须分别封存：

```text
Gate A Receipt
Gate A Tests
Gate A Postcheck

Gate B Receipt
Gate B Tests
Gate B Postcheck
```

禁止一个 TOTAL PASS 代替两个验收。

# 45. 最终内部状态

理想提交状态：

```text
Gate A:
JOINT 00/01/02
= READY_FOR_EXTERNAL_REVIEW

Gate B:
V4-DM-01
= READY_FOR_EXTERNAL_REVIEW

V4-03
= BLOCKED
```

然后停止，不得开始 03。

**任务卡结束**

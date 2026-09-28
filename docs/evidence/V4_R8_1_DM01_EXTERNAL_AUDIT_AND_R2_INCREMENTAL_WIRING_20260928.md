# 大A市场结构研究系统 V4｜R8.1 + DM-01 外部验收与增量主链接线任务

> 文档编号：DA-MSR-V4-R8.1-DM01-EXTERNAL-AUDIT-R2-20260928
> 日期：2026-09-28
> 仓库：`NanOns/a-share-market-structure-research`
> 分支：`codex/v4-system-reform`
> 当前 HEAD：`f04e4a7c7e30aef58df0fe15ed31783ab079fa8c`
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`
> V4-03：禁止启动

## 1. 验收结论

```text
V4-00 = FULL_PASS
V4-01 R8.1 = INTERNAL_PASS / EXTERNAL_BLOCKED_PENDING_R8_2
V4-02 = PASS / EXTERNALLY_ACCEPTED

JOINT 00/01/02
= NOT YET EXTERNALLY_FULL_PASS

V4-DM-01
= BOOTSTRAP / NOOP FRAMEWORK PASS
= REAL INCREMENTAL BUILD NOT YET IMPLEMENTED

V4-03
= BLOCKED
```

## 2. 增量数据更新是否应该现在做

结论：

```text
现在做最合适。
```

不建议等待 V4-03、V4-04 或更后面的任务。

原因不是开发便利，而是数据证据具有时间不可逆性。从现在开始可以每天冻结：

```text
TDX source identity
BaoStock daily facts
GBBQ / gbbq.map
exchange calendar
identity/lifecycle events
special-price events
```

并保存：

```text
observed_at
ingested_at
system_available_at
sha256
```

这些以后可以成为真正的 `PIT_OBSERVED`。如果等后面阶段才开始，中间数据只能 reconstructed，无法真实恢复“当日系统实际看见什么”。

## 3. 当前 DM-01 已完成的部分

当前已经建立：

```text
V4_CONTINUOUS_DATA_MAINTENANCE_V1 contract
three-head separation
bootstrap from 2026-09-24
official calendar bridge
NOOP / idempotency
source readiness gate
TDX local-wins rule
atomic head swap / rollback skeleton
source freeze schema
adjustment impact helper
period impact helper
cross-component postcheck helper
incremental identity delta helper
```

三种 Head 分离正确：

```text
V4_STAGE_ACCEPTED_HEAD
= 00/01/02 阶段验收基线

V4_DATA_ACCEPTED_HEAD
= 每日向前移动

V4_DEV_BASELINE_HEAD
= 后续 03/04... 正式验收时冻结
```

Daily Data Head 更新不得自动移动 Stage Head 或 Dev Baseline。

## 4. 当前 DM-01 尚未完成真实增量

机器回执明确：

```text
incremental_component_builders
= NOT_WIRED_FAIL_CLOSED
```

当前：

```text
processed_sessions = []
source_freeze_receipts = []
per_session_component_build_receipts = []
```

因此 DM-01 目前只能定义：

```text
BOOTSTRAP / NOOP FRAMEWORK PASS
```

不能定义：

```text
PRODUCTION_INCREMENTAL_PASS
```

## 5. 当前没有处理新 session 是正常的

本轮运行发生在 2026-09-28 15:00 Asia/Shanghai 之前。

正式 calendar bridge 判断：

```text
accepted cutoff = 2026-09-24

2026-09-25 ~ 2026-09-27
= official closure

2026-09-28
= official session
但运行时尚未收盘
```

因此：

```text
latest_completed_session = 2026-09-24
```

这个结果正确。

## 6. Gate A：R8.1 Discovery 已修复上一轮的大部分问题

R8.1 已经真正实现：

```text
OFFICIAL_CODE_CHANGE_EVENT
DATED_ALIAS_FACT
ROSTER_EXIT_ENTRY_ADJACENCY
LIFECYCLE_BOUNDARY_ADJACENCY
PERSISTENT_RETROSPECTIVE_BAR_ALIAS
SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE
```

因此非重叠：

```text
OLD_CODE -> NEW_CODE
```

现在能够进入 candidate set。

## 7. Gate A 仍有一个 P0：弱证据被直接确认成 DISTINCT

当前 runtime 存在：

```text
两个 candidate 的 list_date 不同
+ 都有 source revision
→ CONFIRMED_DISTINCT_ENTITY
```

reason：

```text
DIFFERENT_VERSIONED_LISTING_ANCHORS
```

这个证据强度不足。

真实 code-change 完全可能出现：

```text
旧代码 listing anchor = 原上市日期
新代码 provider anchor = 新代码生效日期
```

因此 `different listing anchors` 不能独立证明 `different entity`。

同理：

```text
ROSTER_EXIT_ENTRY_ADJACENCY
LIFECYCLE_BOUNDARY_ADJACENCY
DIFFERENT_LISTING_ANCHOR
SAME_NAME
BAR_CONTINUITY
SOURCE_REVISION_PRESENT
```

都只能生成 candidate，不能单独确认 SAME 或 DISTINCT。

## 8. R8.2 最小修复

不重构 discovery，只强化：

```text
resolution evidence policy
```

建议新增：

```text
IDENTITY_RELATION_EVIDENCE_POLICY_V1
```

正式要求：

```text
CONFIRMED_SAME_ENTITY_CODE_CHANGE
→ official exchange code-change notice
或 versioned independently accepted identity evidence

CONFIRMED_DISTINCT_ENTITY
→ official distinct listing / issuer identity evidence
或足够独立的 accepted lifecycle identity evidence

否则
→ UNRESOLVED
```

Required Scope：

```text
unresolved > 0
→ Gate A BLOCKED
```

## 9. R8.2 必须新增测试

至少：

```text
test_different_listing_dates_do_not_confirm_distinct_without_identity_evidence
test_versioned_listing_anchor_alone_is_weak_evidence
test_official_distinct_entity_evidence_confirms_distinct
test_official_same_entity_code_change_confirms_same
test_nonoverlap_transition_without_identity_evidence_remains_unresolved
test_required_scope_unresolved_blocks_gate
test_candidate_discovery_remains_generic
test_300114_302132_is_fixture_not_algorithm_branch
```

## 10. 增量功能下一步应该现在完成

Gate A resolution policy 修正后，不进入 V4-03。

立即完成：

```text
DM-01 Real Incremental Component Builders
```

因为 identity event discovery 本身就是 Daily Incremental 的直接依赖。

正式主链：

```text
Official Session Discovery
↓
Source Freeze
↓
Identity / Lifecycle Delta
↓
Raw Daily Increment
↓
Trading Status
↓
isST
↓
Adjustment Impact
↓
Adjusted Daily
↓
Weekly / Monthly
↓
Special Price Phase
↓
Price Limit
↓
Independent Cross-Component Postcheck
↓
Candidate Data Head
↓
Atomic Head Swap
```

## 11. 必须复用 00/01/02 已验收生产代码

DM-01 不能另写一套：

```text
Raw parser
Adjustment algorithm
Period aggregator
Price Limit engine
Special Price Phase engine
```

DM-01 的职责是：

```text
orchestration
incremental scope selection
source freeze
revision management
publication
```

业务算法继续调用已经 accepted 的 V4-01/V4-02 runtime。

## 12. Raw / Identity / BaoStock / GBBQ 增量

### Raw Daily
只读取 last accepted cutoff 之后的目标 session TDX 增量。历史 Raw immutable。

### Identity / Universe
调用：

```text
SECURITY_IDENTITY_EVENT_DISCOVERY_V1
mode = DAILY_INCREMENTAL
```

处理：

```text
new listing
delisting
code change
code reuse
board/lifecycle boundary
```

无足够身份关系证据：

```text
UNRESOLVED
→ affected capability BLOCKED
```

### BaoStock
每个 trade_date 优先一次 full-market daily query，获取：

```text
tradestatus
isST
```

Turnover 继续保留在 V4-06。

### GBBQ
必须在 Adjusted build 前冻结：

```text
gbbq
gbbq.map
snapshot_id
sha256
system_available_at
```

## 13. Adjusted Increment

普通日：

```text
append T
```

如果新的 GBBQ/company-action revision 改变历史 QFQ coordinate：

```text
ADJUSTMENT_IMPACT_SET
↓
只重算 affected security 的 affected history
```

禁止每天全市场历史重跑。

## 14. Weekly / Monthly Increment

只更新：

```text
当前 open week/month
```

以及：

```text
受 adjustment revision 影响的 security/period
```

历史 CLOSED raw period 不重算。

## 15. Price Limit Increment

必须调用现有：

```text
generic Price Limit production runtime
```

每日计算 T，不得复制旧结果或写第二套算法。

## 16. DM-01 正式验收必须有真实完成交易日 E2E

不能只靠单元测试和 NOOP bootstrap。

正式 FULL_PASS 至少需要：

```text
1 个真实完成的新交易 session
```

完整验证：

```text
真实 Source Freeze
真实 TDX increment
真实 BaoStock date query
真实 GBBQ freeze
真实 Raw/Adjusted/Status/isST/Period/PriceLimit build
真实 independent postcheck
真实 Data Head promotion
```

否则最高只能：

```text
FRAMEWORK_PASS
```

## 17. 第一真实 E2E

当前最自然的第一个真实 session：

```text
2026-09-28
```

前提：

```text
2026-09-28 15:00 Asia/Shanghai 后
且 local TDX / accepted sources 已完整可用
```

若 source 未就绪：

```text
SOURCE_NOT_READY
```

并保持：

```text
V4_DATA_ACCEPTED_HEAD = 2026-09-24
```

这是正确结果。

## 18. Head 隔离验收

真实 E2E 后：

```text
V4_DATA_ACCEPTED_HEAD
→ 可推进到新 session

V4_STAGE_ACCEPTED_HEAD
→ 必须不变

V4_DEV_BASELINE_HEAD
→ 必须不变
```

## 19. 为什么不等 V4-03 以后

如果等 03/04/05 以后才补 DM，会增加：

```text
PIT snapshot 缺失
identity event history gap
special event gap
GBBQ source-observation gap
后续 Forward 样本减少
catch-up 范围持续扩大
```

这些不是普通历史 backfill 能完整恢复的。

## 20. 为什么现在也不能做 03+ 增量

当前只维护：

```text
00/01/02 accepted data capabilities
```

不能提前混入：

```text
03 factors
04 profile
08 sector
10 state
15 radar
```

等对应阶段分别验收通过后，再把它们接到 Daily Lane。

## 21. 正确推进顺序

```text
STEP 1
修 R8.2 identity resolution evidence gate

STEP 2
Gate A 外部验收
→ 00/01/02 Joint FULL_PASS

STEP 3
接通 DM-01 real incremental builders

STEP 4
第一个真实完成交易日 E2E

STEP 5
DM-01 独立外部验收

STEP 6
冻结/确认 DEV_BASELINE

STEP 7
才开始 V4-03
```

## 22. 当前正式状态

```text
Gate A
= BLOCKED_PENDING_R8_2_EVIDENCE_POLICY

Gate B
= FRAMEWORK_PASS
= REAL_INCREMENTAL_NOT_IMPLEMENTED

V4-03
= BLOCKED
```

## 23. 一句话结论

```text
增量数据维护不是后面再补的功能。

现在做最合适。

代码以后可以补，
但今天没有冻结的 PIT source snapshot，
未来无法真实还原。

当前 DM-01 骨架已经搭好，
下一步先修 R8.2 身份关系证据门，
然后立即把 00/01/02 的真实增量生产链接通，
并用第一个完成交易日做正式 E2E。

DM-01 独立验收通过后，
再进入 V4-03。
```

**文档结束**

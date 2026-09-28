# 大A市场结构研究系统 V4｜R8.2 外部审计 + R8.3 Candidate Linkage Precision + DM-01 Real Incremental Wiring

> 文档编号：DA-MSR-V4-R8.2-DM01-EXTERNAL-AUDIT-R3-20260928  
> 日期：2026-09-28  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 当前 HEAD：`d08efb1837097532bf2d32cb49cc2697f1dd1398`  
> 上一基线：`f04e4a7c7e30aef58df0fe15ed31783ab079fa8c`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> V4-03：继续禁止启动。

## 1. 当前状态

```text
V4-00 = FULL_PASS
V4-01 R8.2 Evidence Policy = POLICY_CORRECT / OWNER_GATE_BLOCKED
V4-02 = PASS / EXTERNALLY_ACCEPTED
JOINT 00/01/02 = BLOCKED_PENDING_R8_3
V4-DM-01 = FRAMEWORK_PASS_ONLY
V4-03 = BLOCKED
```

## 2. R8.2 修对了什么

上一轮错误：

```text
different listing anchors + source revision
→ CONFIRMED_DISTINCT_ENTITY
```

已经删除。

新 `IDENTITY_RELATION_EVIDENCE_POLICY_V1` 正确规定：

```text
ROSTER_EXIT_ENTRY_ADJACENCY
LIFECYCLE_BOUNDARY_ADJACENCY
DIFFERENT_LISTING_DATES
SOURCE_REVISION_PRESENT
SAME_NAME
BAR_CONTINUITY
```

全部只能生成 candidate，不能单独确认 SAME/DISTINCT。

当前 backscan：

```text
candidate_count = 38
CONFIRMED_SAME_ENTITY_CODE_CHANGE = 1
CONFIRMED_DISTINCT_ENTITY = 0
UNRESOLVED = 37
```

Required Scope unresolved=37，因此 owner gate BLOCKED 是正确行为。

## 3. 当前真正问题：candidate linkage 太宽

现在 roster discovery 对：

```text
previous session exited codes
×
current session entered codes
```

在同一 exchange 中做笛卡尔组合。

Lifecycle boundary 也有类似：

```text
all end(T-1)
×
all start(T)
```

这会把普通退市和普通 IPO 只因为日期相邻而形成 old/new relation candidate。

所以当前 37 个 unresolved 里，大量并不是“37 个真实身份问题”，而是 candidate pairing 过宽。

## 4. 禁止人工逐个处理 37 对

不得：

```text
逐个查37对
→ 全部标 DISTINCT
→ unresolved=0
```

这会用人工证据掩盖候选算法缺陷。

下一步必须修 generic linkage。

## 5. R8.3：Atomic Boundary + Linkage

新增：

```text
SECURITY_IDENTITY_EVENT_LINKAGE_V1
```

Roster / lifecycle 首先生成原子边界事件：

```text
SECURITY_EXIT
SECURITY_ENTRY
LISTING_START
LISTING_END
SYMBOL_REASSIGNMENT
```

原子事件本身不自动形成 old/new pair。

只有存在真正 linkage signal 时才形成 relation candidate。

允许 linkage signal：

```text
OFFICIAL_CODE_CHANGE_EVENT
DATED_ALIAS_FACT
ACCEPTED_PROVIDER_PREDECESSOR_SUCCESSOR_LINK
VERSIONED_SAME_ISSUER_ID
VERSIONED_SAME_COMPANY_ENTITY_ID
PERSISTENT_RETROSPECTIVE_BAR_ALIAS
EXACT_NORMALIZED_NAME_CONTINUITY + adjacent effective dates
```

其中弱 signal 仍然只能生成 candidate，最终 SAME/DISTINCT 继续受 R8.2 evidence policy 约束。

## 6. Official Code-Change Event Index

为了不因为收紧 candidate pairing 而降低召回率，必须建立：

```text
OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1
```

覆盖：

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
2023-07-04 ～ 2026-09-24
```

至少保存：

```text
exchange
old_source_security_key
new_source_security_key
effective_date
issuer/entity identifier（如有）
source_ref
source_capture_path
source_capture_sha256
published_at
observed_at
system_available_at
```

并生成 coverage receipt：

```text
required exchanges covered
history window covered
query/index method
source revision
event count
failed query count
unresolved source windows
```

Coverage 不完整就不能声称 identity completeness PASS。

## 7. R8.3 Gate

Required Scope 必须同时满足：

```text
official code-change event index coverage = PASS
linked relation candidates unresolved = 0
unlinked boundary anomaly requiring review = 0
known 300114/302132 = confirmed same
code reuse conflicts = 0 or resolved
specific-security branches in generic runtime = 0
```

普通 IPO / 普通 delisting 原子事件不是 code-change unresolved candidate。

## 8. R8.3 Tests

至少：

```text
test_single_exit_three_unrelated_ipos_does_not_create_three_pairs
test_multiple_exit_entry_same_day_no_cartesian_product
test_roster_boundary_without_link_signal_remains_atomic_event
test_lifecycle_boundary_without_link_signal_remains_atomic_event
test_official_code_change_links_nonoverlap_symbols
test_same_issuer_id_creates_candidate_but_does_not_confirm_same
test_same_normalized_name_creates_candidate_but_does_not_confirm_same
test_different_listing_dates_never_confirm_distinct_alone
test_official_distinct_issuer_evidence_confirms_distinct
test_symbol_reuse_disjoint_lifecycle_candidate
test_official_event_index_coverage_required
test_missing_exchange_event_index_blocks_completeness
test_known_300114_302132_fixture_passes
test_no_specific_security_literals_in_generic_linkage_logic
```

## 9. R8.3 输出

至少：

```text
config/security_identity_event_linkage_v1.json

data/v4/source_evidence/official_code_change_event_index/

reports/v4_01/V4_01_OFFICIAL_CODE_CHANGE_EVENT_INDEX_R8_3.json
reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json
reports/v4_01/V4_01_IDENTITY_RELATION_LINKAGE_R8_3.json
reports/v4_01/V4_01_R8_3_INDEPENDENT_POSTCHECK.json
reports/v4_01/v4_01_final_stage_receipt_R8_3_*.json
reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R3_*.json
```

如果没有新的 SAME_ENTITY counterexample，R7 identity/universe hash 保持不变，V4-02 不重建。

如果发现真实新反例，只允许 affected identity/date scope 定点重建。

## 10. DM-01 当前仍未完成真实增量

最新回执仍明确：

```text
incremental_component_builders = NOT_WIRED_FAIL_CLOSED
processed_sessions = []
source_freeze_receipts = []
per_session_build_receipts = []
```

所以：

```text
DM-01 = FRAMEWORK_PASS_ONLY
```

## 11. 当前 local TDX readiness

最新探测：

```text
eligible daily files = 11,881
latest_tail_date = 2026-09-23
files after accepted cutoff 2026-09-24 = 0
tail date means complete market session = false
```

因此当前 local TDX 还不能支持新 Data Head promotion。

这是 source readiness 状态，不是算法失败。

## 12. DM-01 真实 builder 仍应现在实现

无需等待 V4-03。

但 Gate A 未通过时，只允许：

```text
build / stage / test
```

不得正式 promote 新 Data Head。

完整生产链：

```text
Session Discovery
→ Source Readiness
→ Source Freeze
→ Identity Event Discovery / Linkage
→ Universe Delta
→ Raw Daily Increment
→ Trading Status Increment
→ isST Increment
→ GBBQ Freeze
→ Adjustment Impact
→ Adjusted Daily Increment
→ Weekly / Monthly Increment
→ Special Phase
→ Price Limit Increment
→ Cross-Component Postcheck
→ Candidate Head
→ Atomic Promote
```

## 13. 必须复用已验收 runtime

DM-01 只负责：

```text
orchestration
incremental scope selection
source freeze
revision management
publication
```

不得另写第二套：

```text
TDX parser
identity resolver
adjustment algorithm
period aggregator
special-phase engine
Price Limit engine
```

必须调用已 accepted V4-01/V4-02 runtime。

## 14. DM-01 FULL_PASS 最低条件

必须至少处理：

```text
1 个真实完成并 source-ready 的交易日
```

产生：

```text
source freeze receipt
raw increment receipt
identity/universe increment receipt
tradestatus/isST receipt
GBBQ snapshot receipt
adjustment impact receipt
adjusted increment receipt
period impact receipt
special phase receipt
price limit receipt
independent postcheck
data head promotion receipt
```

单元测试/fixture 不能代替真实 E2E。

## 15. Head 隔离

真实 E2E 后必须：

```text
V4_DATA_ACCEPTED_HEAD → 可移动
V4_STAGE_ACCEPTED_HEAD → hash 不变
V4_DEV_BASELINE_HEAD → hash 不变
```

## 16. 两个 Gate 仍严格独立

允许同一 implementation batch 开发：

```text
R8.3
+
DM-01 real builder wiring
```

但必须分别：

```text
Gate A Receipt / Tests / Postcheck
Gate B Receipt / Tests / Real E2E / Postcheck
```

禁止 TOTAL PASS 代替两个 Gate。

## 17. 执行顺序

```text
STEP 1  R8.3 atomic boundary + linkage refactor
STEP 2  official code-change event index + coverage receipt
STEP 3  R8.3 historical backscan
STEP 4  Gate A tests/postcheck
STEP 5  Gate A PASS 后 reseal Joint 00/01/02
STEP 6  完成 DM-01 real incremental builders
STEP 7  若真实 session source-ready，执行 real E2E
        否则 SOURCE_NOT_READY，不 promote
STEP 8  分别封存 Gate A / Gate B
STEP 9  停止，等待外部验收

V4-03 继续禁止启动。
```

## 18. 当前正式判断

```text
R8.2 Evidence Policy = PASS
R8.2 Candidate Linkage Precision = FAIL / OVERBROAD
V4-01 owner gate = BLOCKED
V4-02 = PASS
DM-01 Framework = PASS
DM-01 Production Incremental = NOT YET IMPLEMENTED
V4-03 = BLOCKED
```

## 19. 一句话结论

```text
R8.2 把错误的“弱证据直接判 DISTINCT”修成了正确 fail-closed。

但 37 个 unresolved 主要暴露的是：
同日 exit × entry candidate pairing 太宽。

下一步不应该人工调查37对股票，
而应该把 roster/lifecycle 拆成 atomic boundary event，
只有真正存在 linkage signal 时才形成 old/new relation candidate，
并用全窗口 official code-change event index 保证召回率。

DM-01 可以同时继续接真实增量 builder，
但 Gate A 未通过或 TDX source 尚未 ready 时，
不得 promote 新 Data Head。

两个 Gate 分别验收；
V4-03 继续不启动。
```

**文档结束**

# 大A市场结构研究系统 V4｜Pre-V4-03 联合最终封口任务卡

> 文档编号：DA-MSR-V4-PRE03-JOINT-SEAL-R1-20260927  
> 日期：2026-09-27  
> 任务性质：V4-00 / V4-01 / V4-02 联合最终封口  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 输入 HEAD：`1a70c8c733096936da4fa250a3f4def501ccfd1d`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> REV2 SHA-256：`744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`  
> 上游联合审计：`DA-MSR-V4-00-01-02-JOINT-FINAL-AUDIT-20260927`  
> Required Scope：`SH_MAIN / SZ_MAIN / CHINEXT / STAR`  
> Optional Scope：`BSE`，允许独立 `DEGRADED_BSE`，不得阻断 Required Scope。  
> V4-03：**禁止实现，直到本任务联合封口 + 外部复验通过。**

---

# 0. 用户治理决策｜本任务最高优先级

以下三条已经由用户正式确认，不得再次讨论、改写或逆转：

## 决策 1｜Phase0 FULL_PASS 采用 Stage-Obligation FULL_PASS

```text
V4-00 FULL_PASS
=
V4-00 自身负责的 contract / schema / policy /
fail-closed / ownership / gate / rollback governance
全部正确完成。
```

明确属于未来 owner stage 的 capability：

```text
Turnover enrichment
Factor performance
Sector / Rotation forward thresholds
Marked-relative benchmark permission
Radar / Focus performance
Future production cutover
```

即使当前仍：

```text
NOT_IMPLEMENTED
PENDING_OWNER_STAGE
SHADOW_ONLY
DISABLED_FAIL_CLOSED
```

**不得继续降低 V4-00 本阶段状态。**

---

## 决策 2｜00F 的 Turnover BOUND_STRICT 保留在 V4-06

```text
V4-00F FULL_PASS
```

只要求：

```text
BaoStock Supplemental Source Contract
public runtime route
field / unit contract
bounded request contract
failure isolation
provenance
source capability boundary
```

完整。

正式：

```text
TURNOVER_CONTEXT_V1
BOUND_STRICT
```

继续由：

```text
V4-06 Supplemental Enrichment
```

实现和验收。

本任务禁止把 V4-06 Turnover 工作提前。

---

## 决策 3｜00H future consumer 可以 fail-closed

以下状态允许继续存在：

```text
MARKED_RELATIVE_BENCHMARK_CONSUMER = DISABLED

benchmark coverage threshold = UNSET
quote-age threshold = UNSET

future performance = PENDING_OWNER_STAGE

sector / rotation forward thresholds
= PENDING_REPRESENTATIVE_EVIDENCE
```

只要：

```text
policy
ownership
permission gate
failure semantics
rollback behavior
```

均已正确冻结，

则：

```text
V4-00H = FULL_PASS
```

不得因为未来 consumer 尚未放行继续标记 Phase0 DEGRADED。

---

# 1. 本任务目标

本任务只解决联合验收剩余的两个问题：

```text
A. V4-01 canonical final receipt 落后于 R7 identity/universe 事实；
B. V4-01 historical code-change alias completeness 尚未形成通用闭环。
```

并基于用户已确认的治理语义：

```text
重新 seal V4-00
重新 seal V4-01
复核 V4-02
生成 00/01/02 Joint Final Receipt
```

最终只有在所有 Required Scope 验收为 PASS 后：

```text
V4-03_ENTRY = AUTHORIZED
```

---

# 2. 当前已接受、不得重做的事实

除非本任务发现新的、可复核的反证，否则不得重新打开：

```text
V4-00A Clean Baseline
V4-00C Publication Identity
V4-00D TDX Source Selection / Overlap
BaoStock Public 0.9.3 runtime route
V4-01 Raw archive
V4-01 Canonical Source Selection
V4-01 lifecycle boundary normalization
V4-01 all-day roster coverage
V4-02 Raw Canonical Daily
V4-02 Adjusted Canonical Daily
V4-02 Market Calendar
V4-02 Trading Status
V4-02 Dated isST
V4-02 Weekly / Monthly
V4-02 CLOSED_ONLY / AS_OF
V4-02 Temporal Leakage
V4-02 Price Limit
V4-02 Special Price Phase
V4-02 Generic Production Wiring R6
V4-02 R6 Independent Postcheck
```

---

# 3. 明确禁止的工作

本任务禁止：

```text
重新下载 TDX
重新跑 00D overlap
重建全部 Raw Canonical Daily
重抓全部 BaoStock 786 日 isST
重新研究 adjustment 算法
重新研究 calendar
重新做 Weekly / Monthly 全阶段
重新做 Price Limit 规则研究
重新抓 R4 官方 source evidence
重新做 V4-02 R6 generic runtime
开始 V4-03 factor/runtime implementation
开始 V4-04+
```

除非 Generic Alias Completeness Gate 找到新的真实 identity counterexample，
才允许对 **affected identity/date scope** 做最小定点重建。

禁止无关全量重跑。

---

# 4. V4-01 R8｜第一项：Generic Historical Code-Change Alias Completeness

必须新增一个通用 gate，例如：

```text
HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_V1
```

名称可按现有命名体系调整，但语义不得改变。

---

# 5. 为什么这是 P0 封口项

当前基础 stable identity 生成逻辑对 SH/SZ 普通证券基本依赖：

```text
exchange
+ source symbol
+ listing date
```

这对 symbol 不变化的证券成立。

但真实反例：

```text
SZ.300114
→
SZ.302132
```

已经证明：

```text
同一上市主体发生代码变化
```

时，如果没有额外 alias 事实：

```text
旧代码
新代码
```

可能被生成两个 stable security_id。

因此：

```text
unresolved_identity = 0
```

不能单独证明：

```text
historical identity completeness = PASS
```

---

# 6. Generic Candidate Discovery 要求

必须针对 Required Scope 全量扫描潜在 code-change continuity candidate。

不得只扫描：

```text
已经共享同一个 security_id 的多个 source key
```

因为那会漏掉：

```text
OLD_CODE -> SEC-A
NEW_CODE -> SEC-B
```

这种恰恰最需要发现的情况。

---

# 7. Candidate Discovery 可以使用的证据维度

可组合使用，但不得把弱启发式直接当事实：

```text
provider listing / delisting boundary
provider code roster disappearance / appearance
security name continuity
official exchange code-change notices
same issuer / company continuity
effective-date adjacency
board continuity / official board change
source revision identity
historical bar continuity
dated roster continuity
existing alias facts
```

这些只能用于：

```text
candidate generation
```

最终 identity 合并必须依赖：

```text
official
or
versioned independently acceptable evidence
```

---

# 8. Candidate 分类

每个 candidate 至少输出：

```text
candidate_id
old_source_security_key
new_source_security_key
old_security_id
new_security_id
candidate_reason
effective_date_candidate
exchange
old_board
new_board
evidence_refs
evidence_digests
resolution_status
resolved_security_id
reason_code
```

resolution_status 至少：

```text
CONFIRMED_SAME_ENTITY_CODE_CHANGE
CONFIRMED_DISTINCT_ENTITY
UNRESOLVED
NOT_APPLICABLE
```

---

# 9. Fail-Closed

如果 candidate 无法确认：

```text
UNRESOLVED
```

不得自动：

```text
认为两个 code 就是两个独立实体
```

对于受影响 historical formal capability：

```text
identity = UNKNOWN
```

并记录 affected：

```text
dates
rows
boards
downstream artifacts
```

---

# 10. Required Scope Final Gate

Required Scope：

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
```

必须满足：

```text
unresolved_code_change_candidate_count = 0
```

否则：

```text
V4-01 R8 = BLOCKED
V4-03 = BLOCKED
```

BSE：

```text
独立 optional degraded
```

不得混入 Required Scope gate。

---

# 11. Facts 与 Logic 分离

允许：

```text
SZ.300114
SZ.302132
```

出现在：

```text
dated_security_alias facts
evidence manifests
official source receipts
regression fixtures
```

禁止：

```python
if code == "300114":
    ...
```

出现在正式 generic production identity logic。

必须继续使用 / 扩展：

```text
DATED_SECURITY_ALIAS_V1
```

这一类通用 resolver。

---

# 12. R7 已有事实必须正式迁入 V4-01 canonical chain

当前 R7：

```text
security_entity_map_R7_20260927.json

v4_01_historical_universe_required_R7_20260927.jsonl.gz
```

必须成为 V4-01 R8 的正式输入。

当前历史：

```text
input membership rows = 4,036,121
output membership rows = 4,035,729
duplicate rows removed = 392
```

必须在新 Final Receipt 中解释并绑定。

---

# 13. V4-01 R8｜Identity / Alias Integrity Postcheck

必须至少检查：

```text
duplicate stable security_id + trade_date = 0

source alias date overlap conflicts = 0

one alias resolving to multiple active stable IDs = 0

dated alias gaps for confirmed code change = 0

wrong-board rows for dated alias = 0

wrong-source-symbol outside effective interval = 0

unresolved Required-Scope code-change candidates = 0
```

---

# 14. Board 映射不能仅依赖 code prefix

300114 / 302132 已证明：

```text
代码前缀
```

不能作为全部历史 board truth。

R8 必须检查：

```text
dated board fact
```

跟随：

```text
stable entity + effective interval
```

而不是简单：

```text
prefix -> board
```

---

# 15. V4-01 R8｜Historical Universe Postcheck

基于最终 alias/identity facts 重验：

```text
session_count = 786

required_scope_rows
= 当前 accepted R7/R8 真实行数

identity_unresolved = 0

duplicate stable-id/date = 0

normalized membership mismatch = 0

required roster coverage missing = 0

source bar structural invalid = 0
```

---

# 16. All-Day Coverage 必须继续覆盖全部 session

不得回退到：

```text
只检查 suspicion-trigger dates
```

仍必须：

```text
for every accepted session:
    expected active Required identities
    ⊆
    dated accepted roster
```

最终：

```text
days_with_missing_required_identity = 0
total_missing_required_identity_rows = 0

SH_MAIN = 0
SZ_MAIN = 0
CHINEXT = 0
STAR = 0
```

---

# 17. V4-01 R8｜正式 Final Receipt

生成：

```text
reports/v4_01/v4_01_final_stage_receipt_R8_20260927.json
```

或同等规范命名。

必须显式 supersede：

```text
v4_01_final_stage_receipt_R6_2_20260926.json
```

但保留历史文件。

---

# 18. V4-01 R8 Final Receipt 必含

至少：

```text
stage
version
technical_contract
technical_contract_sha256

required_boards
optional_bse_status

canonical_identity_artifact
canonical_identity_sha256

canonical_alias_fact_artifact
canonical_alias_fact_sha256

canonical_historical_universe_artifact
canonical_historical_universe_sha256

required_scope_membership_rows
session_count

identity_unresolved
code_change_candidate_count
code_change_confirmed_same_entity
code_change_confirmed_distinct_entity
code_change_unresolved

duplicate_identity_date_rows
alias_interval_conflicts
board_interval_conflicts

all_day_coverage_missing
source_exception_unresolved

test_receipt
execution_commit

status
blockers
stage_completion_authorized
```

---

# 19. V4-01 R8 Tests

至少新增回归：

```text
test_same_entity_code_change_not_split_into_two_entities

test_distinct_entity_code_reuse_not_merged

test_unresolved_code_change_candidate_fails_closed

test_alias_effective_interval_non_overlapping

test_dated_board_follows_alias_fact_not_prefix_only

test_duplicate_stable_id_trade_date_rejected

test_generic_candidate_discovery_catches_split_ids

test_known_300114_302132_case_passes_as_fact_fixture_not_hardcoded_logic

test_all_day_required_coverage_still_zero

test_final_receipt_requires_alias_completeness_gate
```

---

# 20. V4-01 R8 External Acceptance Reseal

生成新的外部 reseal evidence：

```text
V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_20260927.md/json
```

但注意：

Codex 内部只能准备：

```text
EXTERNAL_REVIEW_REQUIRED
```

状态。

不得自行冒充用户/外部模型最终签署：

```text
EXTERNALLY_ACCEPTED
```

最终 external acceptance 要等本任务提交后由外部审计确认。

---

# 21. V4-00 Downstream Closure Reconciliation

在 V4-01 R8 通过后，

重新计算 Phase0 00A–00H。

采用本任务第 0 节已冻结的：

```text
Stage-Obligation FULL_PASS
```

语义。

---

# 22. V4-00A

保持：

```text
FULL_PASS
```

不得重做数据库 reset。

---

# 23. V4-00B

原 degraded：

```text
HISTORICAL_PIT_MEMBERSHIP_DATA_NOT_YET_BOOTSTRAPPED
```

现在使用：

```text
V4-01 R8 Historical Lifecycle
V4-01 R8 Historical Universe
V4-01 R8 all-day coverage
V4-01 R8 alias completeness
```

作为 downstream closure evidence。

如果 R8 PASS：

```text
00B = FULL_PASS
```

---

# 24. V4-00C

保持：

```text
FULL_PASS
```

---

# 25. V4-00D

保持：

```text
FULL_PASS
```

不得重新下载、重新 overlap。

---

# 26. V4-00E

原 degraded：

```text
UNSUPPORTED_ADJUSTED_EVENT_CATEGORIES
```

使用 V4-02 已接受事实：

```text
Adjusted Canonical
empirical samples
per-security fail-closed
no silent RAW fallback
historical non-PIT boundary
go-forward source snapshot
```

作为 downstream closure evidence。

如果 V4-02 R6 继续 PASS：

```text
00E = FULL_PASS
```

历史 pre-project PIT 不存在：

```text
NOT_AVAILABLE
NOT_CLAIMED
```

不得作为 00E degraded 理由。

---

# 27. V4-00F

按照用户决策：

```text
00F FULL_PASS
```

验收：

```text
Supplemental Source Contract
BaoStock public 0.9.3 runtime
field/unit mapping
request bounds
failure isolation
source provenance
status/isST usable source facts
```

当前：

```text
TURNOVER_CONTEXT_V1 BOUND_STRICT
```

明确写：

```text
OWNER_STAGE = V4-06
CURRENT_STATUS = PENDING_OWNER_STAGE
DOES_NOT_DEGRADE_V4_00F = true
```

---

# 28. 00F 不得造假 Turnover capability

Phase0 reseal 不能写：

```text
BaoStock Turnover BOUND_STRICT = PASS
```

当前事实仍应保留：

```text
dataset enabled = false
strict tolerance = not yet accepted
formal Turnover producer = V4-06
```

这属于正确阶段 ownership，不是 degraded。

---

# 29. V4-00G

当前 framework 已经有：

```text
AST validator
schema validator
parameter registry validation
UNKNOWN propagation
window semantics
negative vectors
```

按照 Stage-Obligation：

```text
00G = FULL_PASS
```

未来 owner-stage parameter：

```text
PENDING_OWNER_STAGE
```

不得继续作为 00G DEGRADED。

---

# 30. V4-00H

按照用户决策：

```text
00H = FULL_PASS
```

验收的是：

```text
capability scopes
failure receipts
cutover permissions
rollback semantics
performance ownership
fail-closed future consumers
```

以下继续允许：

```text
Marked Relative disabled
future benchmark threshold unset
future performance pending
future forward threshold pending
```

它们必须正确标 owner stage，

但：

```text
DOES_NOT_DEGRADE_V4_00H = true
```

---

# 31. Phase0 新 Final Receipt

生成新 canonical receipt，例如：

```text
reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260927.json
```

或者更新 canonical pointer 指向新版本。

不得覆盖历史 R3/R4。

---

# 32. Phase0 Final Receipt 必须明确

```text
phase0_status = FULL_PASS

00A FULL_PASS
00B FULL_PASS
00C FULL_PASS
00D FULL_PASS
00E FULL_PASS
00F FULL_PASS
00G FULL_PASS
00H FULL_PASS
```

Required Phase0 blockers：

```text
[]
```

---

# 33. Future Capability 不得伪装成已完成

新 receipt 同时必须保留：

```text
future_owner_stage_capabilities
```

例如：

```text
TURNOVER_CONTEXT_V1
owner = V4-06
status = PENDING_OWNER_STAGE

MARKED_RELATIVE_BENCHMARK
owner = V4-15 / Forward
status = DISABLED_FAIL_CLOSED

factor_performance
owner = V4-03 / V4-05

sector/rotation thresholds
owner = V4-08 / V4-17G
```

这样做到：

```text
Phase0 Stage FULL_PASS
!=
全系统所有 future capability 已生产
```

---

# 34. V4-02 Cross-Stage Rebind Check

V4-02 不重做。

只做独立 postcheck：

```text
V4-02 accepted manifest
```

必须引用/绑定：

```text
与 V4-01 R8 相同的 canonical stable identity / alias / universe
```

如果 R8 仅 reseal 现有 R7：

```text
4,035,729 rows
R7 universe hash unchanged
```

则：

```text
V4-02 business artifacts
无需重建。
```

---

# 35. 如果 R8 找到新的 identity counterexample

只有这时才：

```text
BLOCK
```

并列出：

```text
affected security
affected dates
affected V4-01 rows
affected V4-02 rows
affected components
```

然后做：

```text
最小 affected-scope rebuild
```

禁止默认重跑全部 V4-02。

---

# 36. V4-02 Cross-Stage Postcheck 至少检查

```text
V4-01 canonical universe hash
== V4-02 bound historical universe hash

identity key set compatible

security_id + trade_date uniqueness

dated alias resolution consistent

dated board consistent

trading status key set consistent

dated isST key set consistent

Adjusted Daily key set consistent

Weekly / Monthly identity set consistent

Price Limit key set consistent
```

---

# 37. V4-02 当前接受状态保持

如果 cross-stage postcheck 无差异：

```text
V4-02 = PASS_WITH_BSE_SCOPE_DEGRADED
V4-02 = EXTERNALLY_ACCEPTED
```

不得重新降级。

---

# 38. Joint Final Receipt

最终生成：

```text
reports/v4_joint/
V4_00_01_02_JOINT_FINAL_RECEIPT_R1_20260927.json
```

或同等规范路径。

---

# 39. Joint Receipt 必须绑定

```text
REV2 SHA

current execution commit

Phase0 final receipt + SHA

V4-01 R8 final receipt + SHA

V4-01 alias completeness receipt + SHA

V4-01 universe + SHA

V4-02 accepted head + SHA

V4-02 final external acceptance receipt + SHA

cross-stage postcheck + SHA

test receipts + SHA
```

---

# 40. Joint Receipt Final Gate

仅当：

```text
V4-00 = FULL_PASS

V4-01 Required Scope = PASS
BSE = DEGRADED_BSE accepted

V4-01 generic alias completeness = PASS

V4-01 canonical receipt = CURRENT

V4-02 = PASS_WITH_BSE_SCOPE_DEGRADED

cross-stage hash / identity / row-key consistency = PASS

Required Scope blockers = []
```

才允许：

```text
joint_status = FULL_PASS

v4_03_entry = READY_FOR_EXTERNAL_ACCEPTANCE
```

注意：

Codex 自己不能把：

```text
READY_FOR_EXTERNAL_ACCEPTANCE
```

直接改成：

```text
EXTERNALLY_ACCEPTED
```

---

# 41. Test Gate

必须运行所有受影响测试。

至少：

```text
tests/v4_phase0
V4-01 R8 identity / alias / universe tests
V4-02 cross-stage consistency tests
joint receipt tests
```

不得只运行新增 test file。

---

# 42. Test Receipt

机器回执至少包含：

```text
command
input commit
execution commit
test-tree digest
passed
failed
skipped
duration
python version
affected source digests
```

要求：

```text
failed = 0
```

---

# 43. Code/Receipt Binding

最终 receipt 必须绑定：

```text
business code head
```

如果后续 commit 只添加：

```text
docs
receipts
evidence metadata
```

允许 evidence seal HEAD 晚于 test head，

但必须明确：

```text
no business code changed after tested head
```

并给 compare / changed-file receipt。

---

# 44. Artifact Governance

本任务不要再次把大型 generated artifact 无原则 force-track。

遵循：

```text
正式 artifact 可保留在本地 artifact store

Git 主要提交：
hash
row count
byte count
bounded sample
manifest
receipt
```

如果现有正式 R7 artifact 已在仓库 tracking：

```text
本任务不要求 rewrite history
```

但不得继续扩张无必要大文件 tracking。

---

# 45. 最终执行顺序

必须严格：

```text
STEP 1
Generic Historical Code-Change Candidate Discovery

STEP 2
Alias completeness resolution

STEP 3
R8 identity / universe rebuild or reseal

STEP 4
V4-01 R8 postcheck

STEP 5
V4-01 R8 final receipt

STEP 6
Phase0 downstream closure reconciliation

STEP 7
Phase0 FULL_PASS reseal

STEP 8
V4-02 cross-stage consistency postcheck

STEP 9
Joint 00/01/02 final receipt

STEP 10
提交仓库

STEP 11
停止
等待外部验收
```

---

# 46. 不得执行 STEP 12

本任务没有：

```text
STEP 12 = 开始 V4-03
```

即使 Codex 自己判断：

```text
joint_status = FULL_PASS
```

也必须停止。

由外部模型重新读取最新仓库，完成最终验收后才授权 03。

---

# 47. 提交后用户需要提供的最小信息

只需：

```text
仓库已更新，继续最终验收
```

不需要重新解释过程。

外部验收会直接从最新 HEAD 开始。

---

# 48. 最终目标状态

本任务理想输出：

```text
V4-00
= FULL_PASS

V4-01
= PASS_WITH_BSE_SCOPE_DEGRADED
= CANONICAL_R8_CURRENT
= ALIAS_COMPLETENESS_PASS

V4-02
= PASS_WITH_BSE_SCOPE_DEGRADED
= EXTERNALLY_ACCEPTED
= CROSS_STAGE_RECHECK_PASS

JOINT 00/01/02
= FULL_PASS

V4-03
= READY_FOR_EXTERNAL_ACCEPTANCE
```

然后停止。

---

# 49. 一句话执行要求

```text
不要重做已经通过的阶段。

把 V4-01 的 identity/code-change 完整性做成通用闭环，
把 R7 事实正式 reseal 回 V4-01，
按用户确认的 Stage-Obligation 语义重新封口 V4-00，
再验证 V4-02 与新 canonical identity/universe 完全一致。

只有 00/01/02 联合机器回执无 blocker 后，
才能提交给外部模型决定是否进入 V4-03。
```

**任务卡结束**

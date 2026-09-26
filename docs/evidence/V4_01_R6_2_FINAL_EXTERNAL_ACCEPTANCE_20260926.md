# 大A市场结构研究系统 V4｜V4-01 R6.2 最终外部验收结论

> 文档编号：DA-MSR-V4-01-R6.2-FINAL-EXTERNAL-ACCEPTANCE  
> 日期：2026-09-26  
> 审计仓库：`NanOns/a-share-market-structure-research`  
> 审计分支：`codex/v4-system-reform`  
> 当前 HEAD：`0c94fdc38f4edf8a68482e81e7043ef0a9dd7d9a`  
> R6.2 主要实现提交：`c980675735cfae05e3beb69b240078ef615abe7e`  
> 测试/审计封存实现 HEAD：`05d0510b237865ac5439099a6619d57329395137`  
> 最终 evidence commit：`0c94fdc38f4edf8a68482e81e7043ef0a9dd7d9a`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> 用户 Scope：沪深主板、创业板、科创板必须完整闭环；北交所允许独立降级。

---

# 1. 最终外部验收结论

```text
V4-01 REQUIRED SCOPE = PASS

V4-01 BSE OPTIONAL SCOPE
= DEGRADED_BSE
= ACCEPTED BY USER SCOPE POLICY

V4-01 FINAL
= PASS_WITH_BSE_SCOPE_DEGRADED

V4-02 ENTRY
= AUTHORIZED

V4-03
= BLOCKED
```

这是外部验收结论，不再只是 Codex 内部 `stage_completion_authorized=true`。

# 2. 为什么本轮可以正式接受 V4-01

此前核心 P0 已全部关闭：

```text
Raw archive / extraction lineage
Canonical Source Selection
local TDX > package overlap priority
Stable Security Identity
Historical Lifecycle
Historical Evaluable Universe
BaoStock public route
Dated roster silent partial
Required board scope isolation
786-day all-day lifecycle coverage
Provider outDate / normalized membership boundary conflict
```

R6.2 最关键修复：

```text
provider outDate
!=
normalized membership effective_to
```

已经真正从数据模型和数据库模型中拆开。

# 3. Provider Raw Fact 与 Normalized Membership 已正式分离

新增：

```text
PROVIDER_LIFECYCLE_FACT_V1
```

保留原始：

```text
provider_ipo_date
provider_out_date
provider_status
```

并明确 raw provider fact 不得被 normalized membership 改写。

同时新增：

```text
SECURITY_MEMBERSHIP_INTERVAL_V1
```

独立保存：

```text
normalized_effective_from
normalized_effective_to
from_boundary_basis
to_boundary_basis
boundary_quality
```

这一建模修复符合此前外部审计要求。

# 4. Provider Raw Facts 没有被篡改

R6.2 materialization 实测：

```text
provider fact rows = 8,981 current facts
raw_provider_value_mismatch_count = 0
source_revision_binding_violation_count = 0
append_only_trigger_present = true
```

因此 BaoStock `outDate` 仍作为 source fact 原样保留。

# 5. 129 个窗口内 outDate 已逐证券归一化

Required Scope：

```text
required_security_count = 5,557
provider_outdate_in_window_count = 129
```

真实分布：

```text
outDate 当日仍在 roster = 90
outDate 当日已不在 roster = 39
```

归一化：

```text
resolved_by_same_day_presence = 90
resolved_by_prior_membership = 39
unresolved_boundary_count = 0
```

分板块 unresolved：

```text
SH_MAIN = 0
SZ_MAIN = 0
CHINEXT = 0
STAR = 0
```

# 6. 39 个 R6.1 反例已经正确处理

对于之前发现的 39 个：

```text
outDate 当日 roster absent
```

R6.2 没有补数据、统一改 right-open 或忽略异常，而是采用：

```text
LAST_DATED_ROSTER_MEMBERSHIP_BEFORE_PROVIDER_OUTDATE
```

作为 `normalized_effective_to`，同时保持 `provider_out_date` 不变。

# 7. 90 个 opposite cases 也被保留

对于：

```text
outDate 当日仍存在于 roster
```

的 90 个证券：

```text
normalized_effective_to = provider_out_date
to_boundary_basis = DATED_ROSTER_PRESENT_ON_PROVIDER_OUTDATE
```

因此 R6.2 不再假定所有 outDate 都 inclusive 或都 exclusive。

# 8. Post-outDate Reappearance 已 Fail Closed

如果：

```text
outDate 当日不在 roster
```

但之后再次出现，则：

```text
UNRESOLVED_POST_OUTDATE_REAPPEARANCE
```

不能自动归一化。

回归测试已覆盖：

```text
test_outdate_absence_with_later_roster_reappearance_is_unresolved
```

# 9. 旧错误 regression 已替换

此前：

```text
test_lifecycle_effective_to_is_inclusive_in_r6_scope
```

已改成围绕 normalized interval 的测试：

```text
test_normalized_membership_effective_to_is_inclusive
test_provider_outdate_not_assumed_inclusive
test_outdate_present_in_roster_resolves_inclusive
test_outdate_absent_in_roster_resolves_to_prior_membership_day
test_mixed_outdate_semantics_supported_per_security
test_outdate_absence_with_later_roster_reappearance_is_unresolved
```

# 10. `active_on()` 已改为 fail-closed

如果存在原始结束日期，但没有：

```text
normalized_effective_to
```

则 `active_on()` fail closed，不再重新使用 raw outDate。

只有正式 normalized interval 才进入 membership 计算。

# 11. 786 日 Coverage 已归零

使用 normalized membership interval 重跑：

```text
786 sessions
days_with_missing_required_identity = 0
total_missing_required_identity_rows = 0
```

四板块：

```text
SH_MAIN = 0
SZ_MAIN = 0
CHINEXT = 0
STAR = 0
```

上一轮唯一 blocker 已关闭。

# 12. Normalized Interval 本身没有未决

R6.2：

```text
normalized interval distinct securities = 5,351
interval row_count = 5,351
unresolved boundary = 0
```

另有：

```text
206
```

个 provider outDate 在研究窗口之前的历史证券，被正确排除出研究窗口 active membership。

数量关系：

```text
5,557 required identities
-
206 pre-window excluded
=
5,351 active/window-relevant identities
```

成立。

# 13. Append-only Materialization：通过

新增正式表：

```text
v4.security_membership_interval_history
v4.provider_lifecycle_fact_history
```

均具备：

```text
source revision binding
append-only trigger
UPDATE / DELETE reject
effective interval validation
system_available_at invariant
```

当前：

```text
source_revision_binding_violation_count = 0
supersession_binding_violation_count = 0
```

# 14. Historical Lifecycle Revision 没有覆盖旧判断

对窗口内 129 个边界证券，R6.2 采用：

```text
append new lifecycle revision
supersedes prior revision
```

没有 UPDATE 旧 lifecycle。

# 15. Historical Universe 已重新构建

R6.2：

```text
session_count = 786
required membership rows = 4,036,121
identity_unresolved = 0
source_bar_validation_error_count = 0
normalized_interval_membership_mismatch_count = 0
```

分板块：

```text
SH_MAIN = 1,331,624
SZ_MAIN = 1,174,019
CHINEXT = 1,071,896
STAR = 458,582
```

全部 PASS。

# 16. Universe 行数与 R6 相同不是异常

R6.2 Required Universe 仍为：

```text
4,036,121
```

原因是 R6 Universe 本身已经按 dated roster membership 生成。

R6.1 暴露的是：

```text
formal lifecycle interval
vs
roster
```

不一致，而不是最终 roster-derived universe 多了 39 行。

R6.2 是把正式 lifecycle interval 修正到与已接受 roster/universe 一致，所以行数和 digest 保持一致是合理结果。

# 17. 9,119 条 Bar Missing 继续不阻塞 V4-01

当前：

```text
bar_missing_total = 9,119
```

仍不自动解释成：

```text
SUSPENDED
DATA_GAP
```

正式 trading status / suspension / resumption 属于 V4-02。

# 18. Required Scope 已完整闭环

最终四板块均满足：

```text
identity unresolved = 0
lifecycle unresolved = 0
membership boundary unresolved = 0
all-day coverage missing = 0
unexplained source exception = 0
historical universe identity unresolved = 0
```

因此 Required Scope 正式通过。

# 19. BSE 继续允许降级

当前：

```text
BSE = DEGRADED_BSE
```

并与 Required digest 隔离。

按照用户明确授权，不阻塞 V4-01。

# 20. 测试状态

R6.2：

```text
132 passed
2 skipped
0 failed
py_compile = PASS
```

测试绑定实现 HEAD：

```text
05d0510b237865ac5439099a6619d57329395137
```

之后 `0c94fdc...` 主要为 evidence sealing，无业务代码变化，因此测试绑定可接受。

# 21. Final Receipt：功能性接受

当前 Final Receipt：

```text
blockers = []
required_scope_status = PASS
stage_completion_authorized = true
status = PASS_WITH_BSE_SCOPE_DEGRADED
```

本次外部复审未发现需要重新打开 Required Scope 的 P0。

正式接受：

```text
V4-01 = PASS_WITH_BSE_SCOPE_DEGRADED
```

# 22. 唯一剩余问题｜Git Artifact Governance 回归

这不是模型/数据正确性 P0，但违反此前冻结的仓库治理原则。

`.gitignore` 明确写：

```text
Commit only hashes, counts, bounded samples,
validation reports, and receipts.
```

但 R6.2 又 force-track 了多份 generated artifact。

当前至少：

```text
baostock_dated_rosters ≈ 11.1 MB
security_entity_map ≈ 5.5 MB
baostock_lifecycle_facts ≈ 3.17 MB
BSE optional universe ≈ 4.84 MB
membership interval artifacts ≈ 0.78 MB
```

合计约 25 MB+。

# 23. 该问题如何处理

不要求 rewrite Git history，也不推翻 V4-01 PASS。

但 V4-02 的第一个 housekeeping commit 必须：

```text
git rm --cached
```

移除这些 generated artifacts 的持续 tracking。

保留：

```text
SHA256
row count
byte count
bounded sample
receipt
local artifact path
```

不要删除本地正式 artifact，只停止 Git tracking。

# 24. 一个轻微 Receipt 命名问题

Final Receipt evidence 中：

```text
R6_1_tests
```

实际引用的是：

```text
v4_01_test_receipt_R6_2_20260926.json
```

只是 label naming inconsistency，不影响 SHA / evidence 真实性。

建议下次改成：

```text
R6_2_tests
```

# 25. 外部验收后的阶段状态

从本文件起：

```text
Phase0 = CLOSED
V4-01 = PASS_WITH_BSE_SCOPE_DEGRADED
V4-01 = EXTERNALLY_ACCEPTED
BaoStock Public = OPERATIONAL
V4-02 = AUTHORIZED_TO_START
V4-03 = BLOCKED
```

# 26. V4-02 正式范围

按照 REV2 §78：

```text
RAW Canonical Daily
Adjusted Canonical Daily
formal market calendar
trading status
suspension / resumption
Formal Weekly
Formal Monthly
CLOSED_ONLY
AS_OF
§3C.4 temporal leakage
PRICE_LIMIT_RULE_V1
atomic publication
independent postcheck
```

# 27. V4-02 继续执行当前规则

```text
可以完成
→ 必须完成

工程没实现
≠
允许 DEGRADED_PASS
```

北交所继续 optional degraded scope。

主板、创业板、科创板对应 V4-02 能力必须完整关闭。

# 28. 不需要再重做

V4-02 不得重新打开：

```text
Phase0
00D
BaoStock public route
Raw archive
Extraction lineage
Canonical Source Selection
Historical Security Identity
Lifecycle boundary normalization
Historical Evaluable Universe
```

除非出现新的可复核反证。

# 29. 最终一句话

```text
V4-01 这次可以正式收尾。

R6.2 没有通过“改数据”消除39条反例，
而是把 provider outDate 与 normalized membership interval
彻底拆开，再逐证券按 dated roster 事实归一化。

最终四个 Required Board：
identity 0 unresolved，
boundary 0 unresolved，
786日 coverage 0 missing，
Historical Universe 0 identity error。

因此 V4-01 正式接受：
PASS_WITH_BSE_SCOPE_DEGRADED。

下一步可以进入 V4-02。

但进入 V4-02 的第一个 commit，
先把本轮为了审计而重新 force-track 的 generated artifacts
从 Git tracking 中移除，恢复既定 artifact governance。
```

**文档结束**

# 大A市场结构研究系统 V4｜Pre-V4-03 Joint Seal R1 外部复验

> 文档编号：DA-MSR-V4-PRE03-JOINT-R1-EXTERNAL-REAUDIT-20260928  
> 日期：2026-09-28  
> 仓库：`NanOns/a-share-market-structure-research`  
> 分支：`codex/v4-system-reform`  
> 当前 HEAD：`8941119dba4fb8c75d98699f8fa92c3406de9811`  
> 输入基线：`1a70c8c733096936da4fa250a3f4def501ccfd1d`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> Required Scope：`SH_MAIN / SZ_MAIN / CHINEXT / STAR`  
> Optional Scope：`BSE = DEGRADED_BSE`

# 1. 外部结论

当前 Joint Receipt 虽然内部写 `FULL_PASS`，但本次外部复验暂不接受 Joint FULL_PASS。

```text
V4-00 = FULL_PASS / 外部无新增异议
V4-01 R8 = INTERNAL_PASS / EXTERNAL_BLOCKED_PENDING_R8_1
V4-02 = PASS / EXTERNALLY_ACCEPTED / 无新增P0

JOINT 00/01/02
= EXTERNAL_BLOCKED_PENDING_R8_1_ALIAS_DISCOVERY_COMPLETENESS

V4-03
= BLOCKED
```

# 2. 已通过部分

## 2.1 Phase0 Stage-Obligation Reseal

用户确认的治理语义已正确进入机器回执：

```text
00A FULL_PASS
00B FULL_PASS
00C FULL_PASS
00D FULL_PASS
00E FULL_PASS
00F FULL_PASS
00G FULL_PASS
00H FULL_PASS
```

未来 owner-stage 能力被明确区分：

```text
TURNOVER_CONTEXT_V1 -> V4-06 / PENDING_OWNER_STAGE
MARKED_RELATIVE -> DISABLED_FAIL_CLOSED
factor performance -> V4-03/V4-05
sector/rotation thresholds -> future owner stage
```

没有伪装成已经生产。本项接受。

## 2.2 V4-01 R7 Canonical Reseal

R8 final receipt 已正确 supersede R6.2，并绑定：

```text
security_entity_map_R7
historical_universe_R7
dated_security_alias_r7
membership rows = 4,035,729
duplicate stable-id/date = 0
identity unresolved = 0
all-day coverage missing = 0
```

本项接受。

## 2.3 V4-02 Cross-Stage Rebind

R8 cross-stage postcheck 对：

```text
Adjusted Daily
Trading Status
dated isST
Weekly
Monthly
Price Limit
```

均与 R7 identity/universe key set 对齐，无需重建 V4-02。本项接受。

## 2.4 Joint Tests

```text
190 passed
2 skipped
0 failed
```

两个 skipped 均为 runner symlink capability，不是业务逻辑失败。

测试后到最终 seal：

```text
business_code_changed_after_tested_head = false
```

本项接受。

# 3. 唯一外部 blocker：Alias Completeness Candidate Discovery 仍不完整

R8 新增 `HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_V1`，方向正确，但实际自动 candidate discovery 比合同文字更窄。

当前核心 SQL 只自动发现：

```text
不同 source_security_key
+
不同 stable security_id
+
同一个 trade_date
+
OHLCV + Amount 完全一致
+
至少 20 个共享 session
```

即：

```text
PERSISTENT_IDENTICAL_RAW_OHLCV_AMOUNT_ACROSS_SPLIT_STABLE_IDS
```

另外会把已经存在于 `DATED_SECURITY_ALIAS_V1` 的 alias facts 加入 candidate set。

# 4. 为什么这不足以证明全量代码变更完整性

真实代码变更可以是：

```text
OLD_CODE 最后交易日 = T-1
NEW_CODE 第一个交易日 = T
```

两者可能从来没有同日 bar。

此时：

```text
shared_identical_raw_bar_sessions = 0
```

当前 exact-bar self join 无法发现。

如果该 code change 事先也不在 alias facts：

```text
candidate 根本不会出现
```

最终却仍可能得到：

```text
unresolved_candidate_count = 0
```

形成 false negative。

# 5. 配置与实现不一致

配置声明 candidate signals 包括：

```text
persistent identical raw series
versioned dated alias fact
effective lifecycle and roster boundary continuity, when independently supported
```

但当前生产脚本实际 candidate construction 只有：

```text
exact overlapping raw-bar pair
+
existing alias fact pair
```

没有真正实现：

```text
lifecycle boundary adjacency candidate generation
dated roster exit/entry candidate generation
non-overlap symbol transition candidate generation
```

所以当前的“扫描了全量行”不能证明“candidate detection rule 覆盖全部合理代码变更形态”。

# 6. 测试也缺关键反例

现有 `test_generic_candidate_discovery_catches_split_ids` 仍构造 20 个同日完全相同 bar。

现有 `test_distinct_entity_code_reuse_not_merged` 只验证 resolver 不误合并，并没有验证非重叠旧代码→新代码会进入 candidate set。

至少缺：

```text
test_non_overlapping_code_transition_is_discovered
test_roster_exit_entry_boundary_becomes_candidate
test_lifecycle_boundary_candidate_without_shared_bar
test_true_code_reuse_candidate_resolves_distinct
test_candidate_signal_union_has_no_single_heuristic_blind_spot
```

# 7. R8.1 修复原则

不能继续围绕 300114/302132 写逻辑。

必须建立同时服务历史与未来增量的：

```text
SECURITY_IDENTITY_EVENT_DISCOVERY_V1
```

同一组件支持：

```text
HISTORICAL_BACKSCAN
DAILY_INCREMENTAL
```

candidate generation 至少联合：

```text
OFFICIAL_CODE_CHANGE_EVENT
DATED_ALIAS_FACT
ROSTER_EXIT_ENTRY_ADJACENCY
LIFECYCLE_BOUNDARY_ADJACENCY
PERSISTENT_RETROSPECTIVE_BAR_ALIAS
SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE
```

弱信号只生成 candidate，不允许直接 merge。

最终 same-entity 合并仍要求 official / versioned independently acceptable evidence。

无法确认：

```text
UNRESOLVED
→ fail closed
```

# 8. 本轮不要求重做

禁止重新：

```text
Phase0
TDX历史下载
Raw Canonical
Calendar
BaoStock 786日 isST
Adjustment
Weekly/Monthly
Price Limit
V4-02 R6
```

除非 R8.1 真正发现新的 historical identity counterexample。

# 9. 下一步

不启动 V4-03。

下一实施包：

```text
Gate A:
R8.1 Generic Identity Event Discovery + Joint Reseal

Gate B:
V4-DM-01 Continuous Data Maintenance / Daily Incremental Lane
```

两者可以同一实施包开发，但必须独立合同、独立测试、独立 receipt、独立 postcheck、独立外部验收。

**文档结束**

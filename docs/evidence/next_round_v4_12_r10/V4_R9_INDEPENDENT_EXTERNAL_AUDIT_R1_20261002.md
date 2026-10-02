# V4 R9 独立外部验收审计 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R9 基线 HEAD：** `5267c9e482268dfaaf06d1c752e1bb3d09e33b6f`  
**tested source：** `11d8015d608670572bd57fc50fb6327e2b693a73`  
**当前远端 HEAD：** `d99c242ff90180372df1055d5fff266a48f38102`

# 1. 唯一总裁决

```text
V4_R9_EXTERNAL_AUDIT =
PASS_V4_12_CONTRACT_FREEZE

R6R1_GOVERNANCE_REPLAY_CLEANUP = PASS_KEEP
V4_12_R2_SOURCE_AUTHORITY_REPAIR = PASS_KEEP
V4_12_R2_1_TIME_COUNTER_SEMANTICS = PASS
V4_12_CONTRACT_FREEZE = EXTERNAL_PASS

V4_12_RUNTIME_IMPLEMENTATION =
AUTHORIZED_NEXT_SCOPED_ENGINEERING_STAGE

V4_12_STAGE_ACCEPTED_HEAD =
NOT_YET_AUTHORIZED

V4_STAGE_ACCEPTED_HEAD =
KEEP_V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
KEEP_2026_09_30

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

本轮没有再发现新的 P0。V4-12 合同冻结层可以正式收口，下一步允许进入 **scoped engineering runtime implementation**。

# 2. 当前远端与测试边界

当前远端：

```text
d99c242ff90180372df1055d5fff266a48f38102
```

相对 R9 基线：

```text
ahead_by = 2
behind_by = 0
```

tested source：

```text
11d8015d608670572bd57fc50fb6327e2b693a73
```

最终 HEAD 只比 tested source 多 evidence-only seal：

```text
R9_CLEAN_CHECKOUT_REPLAY.json
R9_TEST_RESULTS.xml
R9_TIME_COUNTER_HANDOFF.json
```

没有业务代码/合同在测试后继续变化。

测试回执：

```text
156 tests
0 failures
0 errors
0 skipped
0 deselected
```

当前 GitHub 没有额外 status/workflow，因此不声称 CI 背书。

# 3. R2.1 P0 已真正修复

旧字段：

```text
post_creation_sessions
```

已经从 Field Registry 和 Machine AST 移除。

现在明确拆成：

```text
post_creation_market_sessions
post_creation_evaluable_sessions
```

## 3.1 market-session age

```text
post_creation_market_sessions
unit = market_sessions_after_available_date
semantic_dimension = market_session_age
producer = V4_12_SESSION_COUNTER_V2
```

只服务：

```text
old_anchor
earliest test
same-day self-confirmation prevention
```

## 3.2 evaluable-session count

```text
post_creation_evaluable_sessions
unit = evaluable_sessions
semantic_dimension = evaluable_session_count
producer = V4_12_SESSION_COUNTER_V2
```

只服务：

```text
acceptance.PENDING
```

没有再把 market-age 与 evaluable-count 混用。

# 4. Acceptance AST 对齐最高合同

当前 Acceptance 规则顺序：

```text
1 BROKEN
2 UNKNOWN when current observation not evaluable
3 ACCEPTED:
    post_creation_market_sessions >= earliest_anchor_test_sessions
    AND
    held_count >= acceptance_consecutive_sessions
4 PENDING:
    post_creation_evaluable_sessions < acceptance_consecutive_sessions
5 otherwise NOT_ACCEPTED
```

符合 §41D：

```text
UNKNOWN = required observation missing
PENDING = 尚无2个可评估会话
ACCEPTED = 后2个连续可评估会话守住
NOT_ACCEPTED = 其余已充分可评估路径
```

`held_count` 独立保持：

```text
consecutive_evaluable_count
```

缺失会话会打断连续链，但不会虚增 cumulative evaluable count。

# 5. B03_missing 已订正

旧错误：

```text
B03_missing = NOT_ACCEPTED
```

已经改成：

```text
T0 created
T+1 missing
T+2 first evaluable hold

market_age = 2
evaluable_count = 1
held_count = 1
expected = PENDING
```

外审认可。

其余 68 个旧向量 expected 保持不变。

因此当前：

```text
AMENDED_69_VECTOR_ORACLE =
69 / 69 PASS
```

已经不再只是上一轮的 mechanical pass。

# 6. sequence oracle 通过

新增三类缺失来源：

```text
SUSPENDED
MISSING_BAR
REQUIRED_COORDINATE_UNAVAILABLE
```

均覆盖：

```text
creation
→ missing/unknown
→ first evaluable resume
→ second adjacent evaluable hold
→ breach
→ same-day revisions
```

并额外覆盖：

```text
hold
→ missing
→ resume
```

证明：

```text
cumulative evaluable count 保留
consecutive held/breach chain 断开
```

以及：

```text
missing calendar
→ market age UNKNOWN
→ support/acceptance UNKNOWN
```

共：

```text
33 sequence steps PASS
```

# 7. same-day revision 语义通过

R2.1 合同已经明确：

```text
same market date revision
不会增加 market-session age

不会重复累计 evaluable membership

不会重复增加 held_count
不会重复增加 breach_count

quality correction 只替换同日 membership/observation
```

sequence 中 r1/r2/r3 均验证 count 不重复累加。

# 8. Time Domain Compatibility Audit 通过

新增：

```text
V4_12_R2_1_TIME_DOMAIN_COMPATIBILITY_AUDIT
```

不是简单比较 unit string，而是识别：

```text
market_session_age
evaluable_session_count
consecutive_evaluable_count
actual_session_separation_count
actual_evaluable_window_count
dimensionless_ATR_multiple
price
percentage_points
...
```

结果：

```text
incompatible_edges = 0
```

并且我核查了负向 gate：

```text
market-age 替换 PENDING counter
→ audit FAIL

evaluable-count 替换 old_anchor counter
→ audit FAIL

仅伪造 unit 字符串
→ 无法掩盖 semantic_dimension 错误
```

因此该 gate 有真实拒绝能力，不是只报告 PASS。

# 9. unit metadata 已消歧

已规范：

```text
held_count / breach_count / recovery_held_count
→ consecutive_evaluable_sessions

pivot left/right
→ actual_evaluable_sessions

support separation
→ actual_session_separation_count

body_atr / range_atr threshold
→ dimensionless_ATR_multiple

range_anchor_range_atr_max
→ dimensionless_ATR_multiple
```

所有 24 个参数 **数值不变**。

这是 metadata/semantic repair，不是调参。

# 10. R2 Source Authority 保持完整

R9 没有回退 R2。

保持 byte-identical / parity PASS：

```text
delta3 -> RPS_DELTA_V1
prior_delta3 prior-session mapping
near_high20 -> POSITION_STATE_V1
V4-03 target-date blocked policy
coordinate authority
alpha/beta blocked
prior_range20_atr blocked
pivot source blocked
RANGE_UPPER REMOVE_EXTRA_TRIGGER
dynamic MA blocked
generic CORE_FACTOR fallback = 0
false accepted owner claim = 0
```

R2 authority vectors：

```text
12 / 12 PASS_KEEP
```

# 11. Protected governance 保持

以下继续 byte-identical：

```text
AGENTS.md
V4_11_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_12 Stage Entry
R6R1 evidence
R8 authority evidence
Anchor Coordinate Contract
Anchor Schema
```

没有：

```text
src/v4 runtime implementation
schema migration
D2 integration
V4-13
Stage Head advance
Data Head advance
Production/Shadow/Focus cutover
```

# 12. Contract Freeze 外审结论

当前已经满足 V4-12 Entry Surface 在 implementation 前要求的核心冻结项：

```text
versioned registries
machine AST
parameter set
source capability policy
producer ownership
time roles
input/output schema
independent vectors
coordinate rules
UNKNOWN semantics
DAG boundaries
session/evaluable counter semantics
```

因此：

```text
V4_12_CONTRACT_FREEZE =
EXTERNAL_PASS
```

注意：

> Contract Freeze PASS 不等于 V4-12 Stage 完成。

它只意味着：

> 现在允许实现 Runtime，而且 Runtime 必须严格消费这些冻结合同。

# 13. 下一阶段权限

下一阶段允许：

```text
V4_12 scoped engineering runtime implementation
```

允许：

```text
D1 pure runtime engine
AST runtime evaluator
Anchor/Event candidate construction
Support/Acceptance state evaluation
time counters
append-only candidate artifacts
synthetic + frozen replay
fail-closed UNKNOWN propagation
```

仍禁止：

```text
D2 integration
Final State writeback
Radar
Focus
Production
Shadow production
Global mandatory adoption
V4-13
Stage Head -> V4-12
Data Head advance
```

# 14. Source capability 边界

当前有些正式 input capability 仍然 blocked，例如：

```text
target-date V4-03 ATR/CLV/MA20/etc
V4-04 near_high20 target publication
alpha/beta cross-basis transform
prior_range20_atr
pivot accepted history
dynamic MA source event allowlist
previous-session accepted D1 publication
```

这些 **不阻止 Runtime 工程实现**。

Runtime 必须：

```text
blocked input
→ UNKNOWN / explicit reason
```

而不是：

```text
raw K fallback
candidate output 偷升级
自行重算获取 authority
```

因此下一轮要区分：

```text
ENGINE IMPLEMENTATION
!=
REAL CAPABILITY CLOSURE
```

# 15. 下一轮建议调度

```text
R10A:
正式记录 Contract Freeze External PASS
+ Runtime Engineering Entry Authorization

R10B:
实现 V4-12 D1 Runtime Engine R1
```

R10A 通过本地 exact/readback gate 后，R10B 可以在同一 Codex 批次顺序执行。

R10B 完成后：

```text
commit + push
STOP
```

再由独立外审决定 Runtime Engine 是否通过，以及是否进入 real capability / storage integration。

# 16. Heads

保持：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

不得创建正式：

```text
V4_12_ACCEPTED_HEAD
```

直到 V4-12 runtime、存储/读回、真实 capability scoped evidence 通过后再决定。

# 17. 最终状态

```text
V4_R9_EXTERNAL_AUDIT =
PASS_V4_12_CONTRACT_FREEZE

NEXT =
V4_12_R10A_RUNTIME_ENTRY
THEN
V4_12_R10B_D1_RUNTIME_ENGINE_R1
```

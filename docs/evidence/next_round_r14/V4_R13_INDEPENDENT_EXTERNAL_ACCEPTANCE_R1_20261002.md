# V4 R13 独立外部验收 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R13 基线：** `a74c42671774a6df389e78c014f9218844f74539`  
**R13 tested source：** `180606d6fe06f47b3639acf25e1549de1c19429f`  
**当前远端 HEAD：** `33b1949a1c05b0fe6c9068e6db9f219a9f11378b`

# 1. 唯一总裁决

```text
V4_R13_EXTERNAL_AUDIT = PASS_SCOPED_ENGINEERING

R13A_BREAKOUT_EPISODE_CONTRACT = PASS
R13B_BREAKOUT_LIFECYCLE_RUNTIME = PASS

BREAKOUT_T_MINUS_1_CONTINUITY = PASS
BREAKOUT_DUPLICATE_CREATION_GUARD = PASS
BREAKOUT_OWNER_ANCHOR_IMMUTABILITY = PASS
BREAKOUT_SAME_DAY_REVISION_PREDECESSOR = PASS
BREAKOUT_SECURITY_PROJECTION = PASS
BREAKOUT_TRANSITION_IDENTITY = PASS

R11_REGRESSION = PASS_KEEP
R12_MULTI_ANCHOR_REGRESSION = PASS_KEEP

REAL_ACCEPTED_SOURCE_RUNTIME = DEGRADED_FAIL_CLOSED_UNKNOWN
V4_12_RUNTIME_ENGINEERING = READY_FOR_ACCEPTED_HEAD_PROMOTION

PRODUCTION = NOT_AUTHORIZED
SHADOW = NOT_AUTHORIZED
V4_13_RUNTIME = NOT_AUTHORIZED_YET
```

R13 已关闭 R12 外审留下的最后一个核心 P0：Basic Breakout State 已从单日 detector 补齐为真正的跨日 Breakout Episode lifecycle。

# 2. 远端提交链

R13 共 3 个提交：

```text
c6e69e810c7fc680aa995694974bc006699ed8a4
Close Basic Breakout episode continuity with frozen owner lifecycle and persisted oracle

180606d6fe06f47b3639acf25e1549de1c19429f
Bind preexisting owner head checkout normalization separately from protected working bytes

33b1949a1c05b0fe6c9068e6db9f219a9f11378b
Seal R13 clean checkout verification and candidate handoff
```

最终 HEAD 相对 tested source 只增加/修改：

```text
reports/v4_12_runtime_r13/R13_CLEAN_CHECKOUT_GATE.json
reports/v4_12_runtime_r13/R13_RUNTIME_HANDOFF.json
reports/v4_12_runtime_r13/R13_TEST_RESULTS.xml
```

不存在测试后 Runtime 代码漂移。GitHub 当前没有 commit status / Actions run，因此本报告不声称 CI 背书。

# 3. Contract 与真实 Runtime

新增：

```text
config/v4_12_breakout_episode_contract_v1.json
config/v4_12_breakout_episode_vectors_v1.json
src/workbench_analysis/v4_12_breakout_episode.py
src/workbench_analysis/v4_12_breakout_snapshot.py
```

并修改：

```text
src/workbench_analysis/v4_12_structure_engine.py
```

核心合同：

```text
contract_id = V4_12_BREAKOUT_EPISODE_CONTINUITY_V1
owning_anchor_type = PRIOR_HIGH
creation_allowed = KNOWN_NO_ACTIVE_EPISODE
existing_source = EXACT_T_MINUS_1_FROZEN_EPISODE_OWNER_OVERLAY
duplicate_guard = ACTIVE_OR_UNKNOWN_DISALLOWS_BREAKOUT_ANCHOR_CREATION
same_day_revision = ALL_REVISIONS_USE_EXACT_PREVIOUS_MARKET_SESSION
terminal_states = FAILED_BREAKOUT
```

# 4. t-1 Breakout Episode 连续性

已有 active breakout episode 时：

```text
读取 t-1 frozen episode
→ 找 owning PRIOR_HIGH Anchor
→ 构建 owner overlay
→ prior_breakout_exists = KNOWN TRUE
→ 运行原 frozen breakout AST
```

因此 `TESTING / BREAKOUT_ACCEPTED / FAILED_BREAKOUT / BREAKOUT_TENTATIVE` 已真正进入跨日 Existing Episode 分支。

# 5. Duplicate Creation Guard

已有 active breakout episode 时，即使 `breakout_trigger=TRUE`，也不会再次生成 PRIOR_HIGH/BREAKOUT_LEVEL。实物证据：

```text
reports/v4_12_runtime_r13/synthetic/duplicate/2026-09-24/r1/anchors.jsonl
```

为空。

# 6. Owner Anchor 与 active_anchor 分离

Basic Breakout Episode owner 固定为 `PRIOR_HIGH`。`display_switch` 路径证明 security active_anchor 可以切换到 `BULLISH_IMPULSE_BODY`，但 breakout owner 不变，符合 §41A.3。

# 7. 跨日状态链

独立 persisted oracle 为：

```text
HAND_WRITTEN_NO_RUNTIME_IMPORTS
```

已证明：

```text
T0 BREAKOUT_TENTATIVE
T+1 touch → TESTING
第二个连续可评估 hold → BREAKOUT_ACCEPTED
owner Anchor BROKEN/INVALIDATED → FAILED_BREAKOUT
```

Breakout transition 携带：

```text
breakout_episode_id
event_id
owning_anchor_id
prior_session_state_ref
from_state
to_state
```

# 8. Failed → New Episode

`terminal` 路径：

```text
2026-09-23 BREAKOUT_TENTATIVE
2026-09-24 BREAKOUT_TENTATIVE
2026-09-28 FAILED_BREAKOUT
2026-09-29 new BREAKOUT_TENTATIVE
```

9/29 `episodes=2`：旧失败 episode 保留，新 trigger 产生新 episode identity。

# 9. Same-day Revision

2026-09-24：

```text
r1 = TESTING
r2 = UNKNOWN
r3 = BREAKOUT_TENTATIVE
```

三者都读取同一个 2026-09-23 r1 `prior_episode_ref`，没有把 r1→r2→r3 当成 prior-session 链。

# 10. UNKNOWN / Fail-Closed

真实 accepted-source replay：

```text
2026-09-29: 5224 securities, 0 episodes, state=UNKNOWN
2026-09-30: 5224 securities, 0 episodes, state=UNKNOWN
```

并保持：

```text
raw_fallback_count = 0
provider_replacement_count = 0
V4_11_candidate_substitution_count = 0
```

这是 capability-scoped fail-closed，不是生产能力证明。

# 11. Tests / Regression

```text
336 tests
0 failures
0 errors
0 skipped
```

并保留：

```text
69 business vectors
33 sequence steps
12 authority vectors
10 time-domain vectors
11 active selector vectors
12 multi-anchor cases
12 breakout cases
```

R11、R12 均 `PASS_KEEP`。

# 12. Heads / 权限

当前仍：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

还没有 `V4_12_ACCEPTED_HEAD`。

权限继续：

```text
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 13. V4-12 可正式 Promotion 的范围

建议 capability map 至少包含：

```text
MULTI_ANCHOR_SNAPSHOT_V2 = ENGINEERING_ACCEPTED
PER_ANCHOR_SUPPORT_ACCEPTANCE = ENGINEERING_ACCEPTED
PER_ANCHOR_PULLBACK_RECOVERY_RETENTION = ENGINEERING_ACCEPTED
ACTIVE_ANCHOR_SELECTOR = ENGINEERING_ACCEPTED
BREAKOUT_EPISODE_CONTINUITY = ENGINEERING_ACCEPTED
BREAKOUT_DUPLICATE_CREATION_GUARD = ENGINEERING_ACCEPTED
BREAKOUT_OWNER_ANCHOR_IMMUTABILITY = ENGINEERING_ACCEPTED
BREAKOUT_SAME_DAY_REVISION_PREDECESSOR = ENGINEERING_ACCEPTED
BREAKOUT_SECURITY_PROJECTION = ENGINEERING_ACCEPTED
BREAKOUT_TRANSITION_IDENTITY = ENGINEERING_ACCEPTED
ANCHOR_COORDINATE_REBASE = ENGINEERING_ACCEPTED_CAPABILITY_SCOPED
SOURCE_AUTHORITY_FAIL_CLOSED = ENGINEERING_ACCEPTED
TIME_COUNTER_SEMANTICS = ENGINEERING_ACCEPTED
REAL_TARGET_DATE_STRUCTURE_SIGNAL = DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY
HISTORICAL_AS_RECORDED_D1 = NOT_PROVEN
FULL_D0_D1_D2_REPLAY = NOT_YET_ACCEPTED_V4_14
V4_13_PROFILE_ADVANCED_PROJECTION = NOT_IMPLEMENTED
```

# 14. 下一步

严格：

```text
R14A
V4-12 Accepted Head Promotion
→ exact promotion validation
→ Stage Head = V4_00_TO_V4_12_ACCEPTED

R14B
V4-13 Stage Entry + Contract Freeze
→ commit + push
→ STOP
```

R14 不实现 V4-13 Runtime。V4-13 Runtime 只有在 R14B contract completeness PASS 后才单独开下一轮。

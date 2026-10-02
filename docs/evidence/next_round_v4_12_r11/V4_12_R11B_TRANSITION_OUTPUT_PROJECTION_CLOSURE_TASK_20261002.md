# V4-12 R11B｜Transition + Output Projection Closure Task｜2026-10-02

**前置：** R11A local PASS  
**任务性质：** Runtime Semantic Output Closure  
**Heads：** KEEP

# 1. 目标

在 persisted t-1 chain 已成立后修复：

```text
Observation / Transition 混用
retest_count 未投影
invalidation_facts 未投影
last_known_support_state 未更新
```

不修改业务阈值与 rule order。

# 2. Observation 与 Transition 拆开

新增明确：

```text
V4_12_STATE_OBSERVATION_CANDIDATE
```

保存所有机器的当日 observation，包括 UNKNOWN、same-state、retention metric。

# 3. Transition 只保存真实 state change

只针对：

```text
breakout
pullback
recovery
support
acceptance
```

`retention` 不进入 state transition。

每条 transition 至少：

```text
logical_transition_id
security_id
machine
trade_date
revision
from_state
to_state
prior_session_state_ref
current_observation_ref
transition_kind
quality
reason
anchor_ref
event_ref
contract_digest
input_digest
```

# 4. Transition 条件

只有：

```text
prior market-session state KNOWN
AND current state KNOWN
AND current != prior
```

才生成正常 transition。

UNKNOWN 与 same-state 只保留 observation，不伪造 change transition。

# 5. Same-day revision

同日 r1/r2/r3：

```text
from_state 永远来自同一 t-1 frozen snapshot
```

不允许 r1→r2→r3 作为 prior-session transition 链。

# 6. retest_count

不能固定 null。

```text
next_test_count KNOWN
→ retest_count = integer(next_test_count)

UNKNOWN
→ null + exact reason attribution
```

并与 snapshot `counter_state.test_count` 一致。

# 7. invalidation_facts

若 hard/episode invalidation TRUE：

```text
输出实际触发事实列表
```

至少可核验：

```text
episode_owns_anchor
deep_breach
breach_count
threshold/result
prior_hard_invalidated
owning anchor/event refs
```

known FALSE：

```text
[]
```

UNKNOWN：

```text
null + exact reason
```

# 8. last_known_support_state

修复：

```text
current support KNOWN
→ current support

current support UNKNOWN
→ preserve t-1 last known support
```

覆盖：

```text
TESTING -> RECLAIMED
RECLAIMED -> HELD_TENTATIVE
known -> missing
missing -> resume
```

# 9. Output/snapshot parity

必须：

```text
envelope.retest_count
==
snapshot.counter_state.test_count

envelope.last_known_support_state
==
snapshot last-known support

transition.from_state
==
t-1 snapshot state

transition.to_state
==
current observation state
```

# 10. Real 9/29 -> 9/30

当前真实链可以继续全 UNKNOWN。

但：

```text
observation rows = full scope
transition rows = only actual known changes
UNKNOWN 不产生虚假 transition
```

在当前 capability 下，real transition count 可能为 0，这是允许的。

# 11. Candidate Schema Manifest

明确三类：

```text
structure_observations
stock_structure_event_transitions
frozen_D1_snapshots
```

禁止 metric observation 冒充 transition。

# 12. 禁止

```text
V4_12_ACCEPTED_HEAD
Stage/Data Head advance
D2
Radar
Focus
Production
Shadow
V4-13
DB production migration
```

# 13. 完成状态

只允许：

```text
V4_12_R11B_TRANSITION_OUTPUT_PROJECTION_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

统一 commit + push 后 STOP。

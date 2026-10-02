# V4-12 R12B｜Multi-Anchor Runtime + Active Selector Closure｜2026-10-02

**前置：** R12A Contract V2 local PASS  
**任务性质：** Scoped Engineering Runtime Closure  
**Stage/Data Heads：** KEEP

# 1. 目标

把：

```text
one security -> one bound_anchor
```

重构为：

```text
one security -> many persisted anchor_states
```

同时实现 frozen active_anchor_sort。

# 2. Common F0 只绑定一次

每 security/date：

```text
InputBinder -> common F0 facts
```

不得为每 Anchor 获得不同 source authority。

# 3. Per-anchor overlay

对每个 prior anchor_state：

```text
common F0
+
that immutable Anchor
+
owning Event
+
that counter_state
+
that t-1 states
```

构建 one-anchor AST overlay。

复用同一 frozen AST 计算：

```text
pullback
recovery
support
acceptance
retest / invalidation
```

# 4. Binder 不再挑一个 Anchor

当前 `prior['anchor']` 单 Anchor 正式路径必须退出。

Binder 负责 common facts 与 prior snapshot authority validation。

StructureEngine / AnchorState evaluator 负责 iterate `anchor_states[]`。

# 5. Same-day creation

所有 qualified Anchor type 都 append：

```text
create immutable Anchor
create owning Event
append new anchor_state
```

BODY + LOW 同时满足时，两者都持久化。

禁止 `result['anchors'][0]`。

# 6. Existing + new merge

必测：

```text
t-1 old impulse anchors
+ t new breakout anchor
→ t set grows
→ t+1 fresh process retains all
```

# 7. Per-anchor counters

每 Anchor 独立：

```text
market age
evaluable count
held
breach
recovery held
test count
separated sessions
last-known support
```

A 的 missing/breach 不得改 B。

# 8. Per-anchor transitions

Transition mandatory：

```text
anchor_id
event_id
```

仍只对 known→known actual change 生成。

retention metric 不冒充 state transition。

# 9. Active selector

实现：

```text
eligible = non-terminal anchors

0 -> null / NO_ACTIVE_ANCHOR

1 -> select it

>1, ranking known:
distance_to_C / ATR ASC
anchor_trade_date DESC
anchor_id ASC

>1, ranking not fully comparable:
null / ACTIVE_ANCHOR_SELECTION_UNKNOWN
```

不得 first()/oldest/newest shortcut。

# 10. Active output projection

Top-level：

```text
active_anchor_id
anchor_view_asof_t
support_state
acceptance_state
retest_count
last_known_support_state
invalidation_facts
```

来自 active Anchor。

完整 per-anchor states 另存，不被覆盖。

# 11. Episode invalidation

Event A 的 invalid_if 始终读取 owning Anchor A，即使 active selector 切到 B。

# 12. Synthetic hard cases

至少：

```text
M01 BODY + LOW same-day -> 2 persisted -> next day still 2
M02 two anchors independent states
M03 old + new anchor merge
M04 one invalidated, another valid
M05 active distance sort
M06 active date tie-break
M07 active id tie-break
M08 active selector UNKNOWN fail-closed
M09 active switch does not mutate owning episode
M10 new anchor no self-confirm
M11 same-day r1/r2/r3 share same t-1 set
M12 append-only / immutable rerun
```

# 13. Real replay

继续 2026-09-29→09-30 reconstructed candidate。

允许当前真实仍：

```text
0 anchors
0 transitions
大量 UNKNOWN
```

但必须保持：

```text
raw_fallback = 0
provider replacement = 0
V4_11 candidate substitution = 0
AS_RECORDED = false
formal_accepted = false
```

# 14. Regression

全部 KEEP：

```text
69 business vectors
33 sequence steps
12 authority vectors
10 time-domain vectors
R11 fresh-process chain
R11 transition predicate
R11 projection oracle
R11 same-day correction
```

# 15. Independent multi-anchor oracle

不得调用 runtime selector 生成 expected。

手写核验：

```text
anchor count
anchor ids
per-anchor counters/states
active selector winner/UNKNOWN
transition identities
owning episode refs
```

# 16. Snapshot V2 only

R12 candidate 使用：

```text
V4_12_FROZEN_D1_CANDIDATE_SNAPSHOT_V2
```

V1 evidence 保留，不作为 R12 formal candidate source。

# 17. 禁止

```text
V4_12_ACCEPTED_HEAD
Stage/Data Head advance
V4-13
D2
Radar
Focus
Production
Shadow
formal DB migration
```

# 18. 完成状态

只允许：

```text
V4_12_R12B_MULTI_ANCHOR_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

统一 commit + push 后 STOP。

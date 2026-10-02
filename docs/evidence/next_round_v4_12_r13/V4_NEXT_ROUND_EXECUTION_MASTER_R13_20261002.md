# V4 下一轮执行总调度卡 R13｜2026-10-02

**基线 HEAD：** `a74c42671774a6df389e78c014f9218844f74539`

# 1. 当前状态

```text
R12 Multi-Anchor Snapshot V2 = PASS KEEP
R12 Per-Anchor State = PASS KEEP
R12 Active Selector = PASS KEEP
R12 Owning Episode = PASS KEEP

Global Basic Breakout lifecycle = FAIL P0
Duplicate breakout creation guard = FAIL P0

V4-12 Runtime External Acceptance =
BLOCKED R13
```

# 2. 执行顺序

严格：

```text
R13A
→ contract local gate PASS
→ R13B
→ unified commit + push
→ STOP
```

# 3. R13A

执行：

```text
V4_12_R13A_BREAKOUT_EPISODE_CONTINUITY_CONTRACT_TASK_20261002.md
```

冻结：

```text
Creation Detector
Existing Episode Lifecycle
Breakout owner Anchor
Episode identity
duplicate creation guard
same-day revision predecessor
security basic_breakout projection
transition identity
```

# 4. R13B

R13A PASS 后执行：

```text
V4_12_R13B_BREAKOUT_LIFECYCLE_RUNTIME_CLOSURE_TASK_20261002.md
```

核心：

```text
t-1 persisted breakout episode
→ owning Anchor overlay
→ frozen breakout AST existing-event path
→ TESTING / ACCEPTED / FAILED / retained tentative
```

# 5. KEEP

不得返工：

```text
Snapshot V2 anchor_states[]
MultiAnchor cardinality
per-anchor counters
per-anchor Support/Acceptance/Pullback/Recovery/Retention
active selector
owning episode
R11 fresh-process chain
R8/R9 authority/time semantics

69 business vectors
33 sequence steps
12 authority vectors
10 time-domain vectors
11 selector vectors
R12 M01-M12
```

# 6. 当前错误不得保留

禁止：

```text
global breakout always evaluated from binder.bind(..., None)
existing breakout treated as no-prior
active breakout + breakout_trigger creates duplicate episode
basic_breakout_state absent from security projection
breakout transition with episode state but null owner identity
```

# 7. Heads

全轮：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

# 8. 禁止

```text
V4_12_ACCEPTED_HEAD
V4-13 Runtime
D2
Final State
Radar
Focus
Validation Cohort
Production
Shadow
formal DB migration
```

# 9. 完成条件

```text
no-event detector correct
first trigger creates one Basic Breakout episode
creation day no self-accept
t+1 reads exact t-1 episode
tentative retention PASS
touch -> TESTING PASS
2 holds -> BREAKOUT_ACCEPTED PASS
broken/invalidated -> FAILED_BREAKOUT PASS
active event blocks duplicate creation
failed event permits later new episode
owner unaffected by general active_anchor
same-day revisions share same t-1 episode
basic_breakout_state security projection exact
breakout transition owner identity exact
real replay authority unchanged
all R8-R12 regression KEEP
```

最终：

```text
V4_12_R13B_BREAKOUT_LIFECYCLE_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

commit + push 后 STOP。

# 10. R13 外审通过后

直接进入：

```text
V4-12 scoped engineering Accepted Head Promotion
Stage Head -> V4_00_TO_V4_12_ACCEPTED
V4-13 Stage Entry
```

不等待长期真实样本阻塞后续开发。

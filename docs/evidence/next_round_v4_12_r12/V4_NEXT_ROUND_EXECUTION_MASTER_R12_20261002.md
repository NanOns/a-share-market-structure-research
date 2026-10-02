# V4 下一轮执行总调度卡 R12｜2026-10-02

**基线 HEAD：** `5bc34c907bd5d39f322c315db34c7788d61f0bbc`

# 1. 当前状态

```text
R11 persisted fresh-process chain =
PASS_SINGLE_ANCHOR_SCOPE

R11 Transition / Output Projection =
PASS_SINGLE_ANCHOR_SCOPE

Multi-Anchor persistence =
FAIL P0

Active Anchor selector =
NOT_IMPLEMENTED P0

V4-12 Runtime External Acceptance =
BLOCKED R12
```

# 2. 执行顺序

严格：

```text
R12A
→ contract local gate PASS
→ R12B
→ unified commit + push
→ STOP
```

# 3. R12A

执行：

```text
V4_12_R12A_MULTI_ANCHOR_STATE_CONTRACT_V2_TASK_20261002.md
```

冻结：

```text
Snapshot V2
anchor_states[]
per-anchor counters/states
owning episode binding
active selector
security-level active projection
transition anchor dimension
```

V1 不得原地修改。

# 4. R12B

R12A PASS 后执行：

```text
V4_12_R12B_MULTI_ANCHOR_RUNTIME_ACTIVE_SELECTOR_TASK_20261002.md
```

核心：

```text
common F0 once
→ every prior Anchor independently evaluated
→ all new Anchors appended
→ all Anchor states persisted
→ active_anchor deterministic projection
```

# 5. KEEP

不得返工：

```text
R8 Source Authority
R9 Time Counter
R10A Runtime Entry
R11 fresh-process mechanism
R11 Observation/Transition predicate
R11 retest/invalidation/last-known projection
69 / 33 / 12 / 10 vectors
```

# 6. 当前错误不得保留

禁止继续：

```text
result['anchors'][0]
prior['anchor'] singular state model
bound_anchor == active_anchor
new anchor dropped when old anchor exists
snapshot scalar-only anchor/event
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
V4-13 runtime
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
same-day 2+ Anchor persisted
t+1 fresh readback retains all
old + new Anchor merge
per-anchor counters independent
per-anchor invalidation independent
per-anchor transitions keyed by anchor
active selector exact
selector UNKNOWN fail-closed
active switch does not change owning episode
new Anchor no self-confirm
same-day revisions share same t-1 set
real replay authority unchanged
all prior vectors KEEP
```

最终：

```text
V4_12_R12B_MULTI_ANCHOR_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

commit + push 后 STOP。

# 10. R12 外审通过后

下一轮直接：

```text
V4-12 scoped engineering Accepted Head Promotion
Stage Head -> V4_00_TO_V4_12_ACCEPTED
V4-13 Stage Entry
```

不等待长期真实 Anchor 样本阻塞后续开发。

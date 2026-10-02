# V4 下一轮执行总调度卡 R9｜2026-10-02

**基线 HEAD：** `5267c9e482268dfaaf06d1c752e1bb3d09e33b6f`

# 1. 当前外审状态

```text
R6R1 = PASS KEEP
V4-12 R2 Source Authority = PASS KEEP
V4-12 Contract Freeze = BLOCKED R2.1
V4-12 Runtime = NOT AUTHORIZED
```

# 2. 本轮只有一张执行卡

```text
V4_12_R2_1_SESSION_COUNTER_SEMANTICS_REPAIR_TASK_20261002.md
```

# 3. 唯一 P0

当前 `post_creation_sessions` 同时被用于：

```text
market-session age
```

与：

```text
post-event evaluable-session count
```

必须拆分：

```text
post_creation_market_sessions
→ old_anchor / earliest test

post_creation_evaluable_sessions
→ Acceptance PENDING
```

# 4. 必修 vector

当前：

```text
B03_missing = NOT_ACCEPTED
```

与最高合同 §41D 冲突。

必须补真实时序：

```text
creation
→ next-day suspension/missing
→ first evaluable resume
→ second adjacent evaluable
```

并证明：

```text
UNKNOWN
→ PENDING
→ ACCEPTED
```

按事实演化正确发生。

# 5. KEEP

不得重做：

```text
R2 owner reconciliation
RPS delta authority
V4-04 near_high authority
coordinate authority
range/pivot blocks
RANGE_UPPER reconciliation
dynamic MA block
slope20 unit
```

# 6. 禁止

```text
V4-12 runtime
src/v4 D1 engine
migration
D2
V4-13
Stage/Data Head advance
Production/Shadow/Focus
```

# 7. 完成条件

```text
two time-domain counters split
old_anchor uses market age only
PENDING uses evaluable count only
missing/suspension sequence PASS
same-day revision PASS
B03_missing corrected
C01-C07 PASS
time-domain compatibility incompatible_edges = 0
R2 authority parity remains PASS
```

最终：

```text
V4_12_R2_1_TIME_COUNTER_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

commit + push 后 STOP。

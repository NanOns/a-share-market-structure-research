# V4 下一轮执行总调度卡 R15R1｜2026-10-02

**执行基线**：`c7b2cb92c5fb12127a941d5af102742fe0d5e965`

# 当前状态

```text
C01-C04 = PASS_KEEP

R15_EXTERNAL_AUDIT =
PARTIAL_PASS_VERSION_LINEAGE_CLEANUP_REQUIRED

V4_13_RUNTIME =
NOT_AUTHORIZED
```

# 本轮只执行一张卡

```text
V4_13_R15R1_VERSION_LINEAGE_CLEANUP_TASK_20261002.md
```

顺序：

```text
remove two false supersedes
→ add correct introduced/derived lineage
→ strengthen supersedes validator
→ negative lineage tests
→ clean detached validation
→ commit + push
→ STOP
```

# KEEP

```text
V4_12_ACCEPTED_HEAD exact
V4_STAGE_ACCEPTED_HEAD exact
V4_DATA_ACCEPTED_HEAD exact
AGENTS.md exact
```

不重开 C01-C04，不重开 R8-R14A。

# 禁止

```text
V4-13 Runtime
DB migration
V4_13_ACCEPTED_HEAD
V4-14
Production
Shadow
Focus
Radar/Cohort
Data Head advance
```

R15R1 外审通过后，再进入 V4-13 Runtime implementation。

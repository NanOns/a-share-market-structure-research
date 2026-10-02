# V4 下一轮执行总调度卡 R7｜2026-10-02

**当前远端 HEAD：** `2e3e811eb08d7e350e27c4c1e2767ba91160ef98`  
**当前 Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**当前 Data Head：** KEEP `2026-09-30`

# 1. 当前外审状态

```text
V4_11 Promotion = PASS KEEP
V4_12 Stage Entry = PASS SCOPED KEEP

R6 full batch =
PARTIAL_PASS_GOVERNANCE_CLEANUP_REQUIRED
```

不回滚 promotion。

# 2. 本轮两张任务卡

```text
1. R6R1_PROMOTION_GOVERNANCE_REPLAY_CLEANUP_TASK_20261002.md
2. V4_12_R1_STRUCTURE_ANCHOR_SUPPORT_CONTRACT_FREEZE_TASK_20261002.md
```

# 3. 执行顺序

```text
R6R1 cleanup
→ exact heads/readback PASS
→ V4-12A Contract Freeze
→ unified commit/push
→ STOP
→ independent external audit
```

两张卡可以同一轮 Codex 完成，但 V4-12A 不得借机实现 runtime。

# 4. R6R1 必须关闭

```text
G01:
restore AGENTS.md exact baseline

G02:
remove hardcoded personal Desktop bundle path
repo-first + explicit --bundle-dir bootstrap + fail-closed
```

# 5. V4-12A 目标

完成：

```text
field registry
producer/time-role registry
input/output schema
Anchor schema
coordinate/rebase contract
Breakout/Pullback/Recovery AST
Support/Acceptance AST
Retention contract
parameter instance
UNKNOWN/source capability
machine vectors
independent oracle
contract completeness matrix
```

# 6. 禁止

```text
V4-12 runtime implementation
src/v4 D1 detector
schema migration
D2 integration
V4-13
Stage Head advance
Data Head advance
production/shadow/focus
```

# 7. Heads

全轮：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

# 8. 完成后状态

```text
R6R1_GOVERNANCE_REPLAY_CLEANUP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT

V4_12_R1_CONTRACT_FREEZE_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

commit + push 后 STOP，等待独立外审。

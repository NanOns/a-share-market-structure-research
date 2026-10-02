# V4 下一轮执行总调度卡 R8｜2026-10-02

**基线 HEAD：** `b475002697bb3c5d91fab1ba44852b31d0d1da29`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

# 1. 当前外审状态

```text
R6R1 Governance Cleanup =
EXTERNAL PASS

V4-12 R1 AST / parameters / vectors =
KEEP

V4-12 R1 Source Authority / Producer Registry =
BLOCKED_R2

V4-12 runtime =
NOT AUTHORIZED
```

# 2. 本轮只有一张主任务卡

```text
V4_12_R2_SOURCE_AUTHORITY_PRODUCER_REGISTRY_REPAIR_TASK_20261002.md
```

不再重做 R6R1。

# 3. 本轮核心

只修：

```text
wrong CORE_FACTOR ownership
exact source-field alias
delta3/RPS authority
near_high20/V4-04 authority
coordinate/adjustment authority
D1 local-derived classification
prior/pivot/range capability blocking
units
branch requiredness
Completeness Matrix
```

# 4. KEEP

不得无故重写：

```text
Breakout AST
Pullback AST
Recovery AST
Support AST
Retention formula
DAG boundary
24 parameter values
69 R1 independent vectors
Anchor immutability
basis identity
```

# 5. 禁止

```text
V4-12 runtime implementation
src/v4 D1 engine
schema migration
D2 integration
V4-13
Stage Head advance
Data Head advance
production/shadow/focus
```

# 6. Heads

全轮：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

# 7. 完成条件

```text
Producer Authority Parity = PASS
Coordinate Authority Audit = PASS
Unit Parity = PASS
branch requiredness explicit
false accepted owner claims = 0
generic CORE_FACTOR fallback = 0
R1 vectors remain PASS
new authority vectors PASS
no runtime changes
```

最终只输出：

```text
V4_12_R2_CONTRACT_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

统一 commit + push 后 STOP，等待独立外审。

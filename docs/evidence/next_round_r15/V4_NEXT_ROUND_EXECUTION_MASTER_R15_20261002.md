# V4 下一轮执行总调度卡 R15｜2026-10-02

**执行基线**：`226270c3178736e9b52e0e3574339039ed191350`

# 1. 当前状态

```text
R14_EXTERNAL_AUDIT =
PARTIAL_PASS_V4_13_CONTRACT_REPAIR_REQUIRED

R14A_V4_12_ACCEPTED_HEAD_PROMOTION =
PASS_KEEP

V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_12_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30

V4_13_STAGE_ENTRY =
AUTHORIZED_CONTRACT_DESIGN_ONLY

V4_13_RUNTIME =
NOT_AUTHORIZED
```

# 2. 本轮只执行一张卡

```text
R15A
V4_13_R1_1_CONTRACT_SEMANTIC_AUTHORITY_REPAIR_TASK_20261002.md
```

执行顺序：

```text
fix C01-C04
→ local independent contract gate
→ clean detached validation
→ unified commit + push
→ STOP
```

# 3. 只修 4 个问题

```text
C01 TIME_ROLE_OVERCOUPLING

C02 SECTOR_CONTEXT_STATE_SEMANTICS_NOT_FROZEN

C03 MEMBERSHIP_DAG_SOURCE_AUTHORITY_MISBIND

C04 ROTATION_STRUCTURE_ENRICHMENT_MULTI_SOURCE_BINDING_INCOMPLETE
```

不得扩大范围。

# 4. KEEP

必须保持：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

其中：

```text
Stage = V4_00_TO_V4_12_ACCEPTED
Data = 2026-09-30
```

不重开 R8-R14A。

# 5. 核心修复目标

## Time Role

```text
primary_industry
supporting_concepts
```

只能依赖 current exact membership，不得依赖 t-1 LOO history。

## Sector Context State

必须冻结成 deterministic/lossless schema，不能让 Runtime 自己发明语义。

## Membership Authority

membership 必须显式绑定 V4-08 PIT Membership Accepted Head；core primitives / seed 分开绑定正式 owners。

## Rotation Structure Enrichment

必须显式双来源：

```text
V4-08 Rotation
+
V4-12 read-only Structure
```

并做 component-wise quality propagation。

# 6. 仍然禁止

```text
V4-13 Runtime
V4-13 Accepted Head
V4-14
Production
Shadow
Focus
Radar/Cohort
DB migration
Data Head advance
```

# 7. STOP

完成：

```text
V4_13_R1_1_CONTRACT_SEMANTIC_AUTHORITY_REPAIR = PASS
```

后：

```text
commit
push
STOP
```

等待独立外审。

只有 R15 外审通过后，才发布 V4-13 Runtime implementation task cards。

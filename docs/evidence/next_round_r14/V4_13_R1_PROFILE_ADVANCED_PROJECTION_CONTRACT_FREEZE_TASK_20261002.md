# R14B｜V4-13 Profile Advanced Projection Stage Entry + Contract Freeze｜2026-10-02

**前置：** R14A Promotion exact PASS  
**阶段：** V4-13  
**§78 唯一名称：** Profile Advanced Projection  
**本卡性质：** Stage Entry + Contract Freeze ONLY  
**禁止：** Runtime implementation

# 1. 最高目标

冻结 V4-13：

```text
Context / LOO / Structure Projection
+
完整 DAG Integration Interface
```

的正式实现合同。本轮不写 V4-13 Runtime。

# 2. §87A 必须覆盖的 V4-13 字段

至少：

```text
primary_industry
supporting_concepts
algorithmic_support_sector
relative_sector_state
sector_context_state
sector_context_quality
rotation_structure_enrichment
```

同时明确 V4-12 Structure 字段如何只读投影进入 Advanced Profile：

```text
active_anchor_id
anchor_view_asof_t
basic_breakout_state
basic_pullback_state
basic_recovery_state
support_state
acceptance_state
retest_count
structure_events
structure_health
```

不得复制第二套 Structure 状态机。

# 3. 核心合同

冻结：

```text
LOO_CONTEXT_V1
```

及必要的：

```text
PROFILE_ADVANCED_PROJECTION_V1
V4_13_DAG_INTEGRATION_INTERFACE_V1
```

若已有正式 contract_id，必须复用。

# 4. LOO 原则

目标股票 `s` 的 sector context 必须排除 `s` 自身。

禁止：

```text
股票自身强
→ 抬高所属板块
→ 板块强
→ 再反过来证明股票强
```

# 5. Sector Membership Authority

所有：

```text
primary_industry
supporting_concepts
algorithmic_support_sector
```

必须绑定日期有效 membership / accepted source identity。

历史 PIT 不足时：

```text
CURRENT_MEMBERSHIP_REPLAY
或明确 degraded evidence origin
```

不得把当前成员倒灌过去并称 PIT。

# 6. primary_industry

冻结：

```text
唯一选择规则
source identity
trade-date validity
quality
UNKNOWN / NOT_APPLICABLE
tie-break
```

禁止 UI 顺序或数组第一项。

# 7. supporting_concepts

冻结：

```text
候选 concept 完整集合
membership quality
保留条件
排序条件
stable tie-break
显示 cap 与底层集合分离
```

# 8. algorithmic_support_sector

必须明确：

```text
context projection
!=
stock qualification gate
```

选择规则至少登记：

```text
sector type
LOO quality
sector state
rotation state
relative evidence
stable tie-break
```

# 9. relative_sector_state

沿用 §10E 拓扑，但将 market relative 替换为 LOO sector relative。

不得复制/修改 RELATIVE_STATE_V1 优先级和阈值。

冻结：

```text
input fields
LOO denominator
minimum member/coverage
UNKNOWN
NOT_APPLICABLE
```

# 10. sector_context_state / quality

必须分开保存：

```text
value
quality
reason
source identity
membership basis
LOO basis
```

并映射到现有统一 quality 体系。

# 11. Context 不进入第一版 Stock PREWATCH Hard Gate

必须证明：

```text
perturb sector/context
```

不会改：

```text
A Base Seed
C Stock PREWATCH raw qualification
```

V4-13 只提供 Advanced Profile / Context enrichment / DAG integration。

# 12. rotation_structure_enrichment

V4-08 `rotation_core_state` 仍是 Core owner。

V4-13 只允许：

```text
Structure -> D3/context enrichment
```

禁止：

```text
Structure[t] -> B0/B1/B2[t]
```

# 13. DAG Integration Interface

逐边登记：

```text
producer
consumer
field
contract/version
t / t-1
required / optional
namespace
quality propagation
```

覆盖 A / B0 / B1 / B2 / C / D0 / D1 / D2 / V4-13 Context。

显式禁止：

```text
D2[t] -> D1[t]
D1[t] -> B0/B1/B2[t]
Context[t] -> A/C raw qualification[t]
Focus/UI -> qualification
Supplemental -> Core
future outcome -> same-day state
```

# 14. V4-14 边界

V4-13 可以后续实现完整 DAG integration，但不得在 V4-13 声称：

```text
ALGORITHM_STATE_REPLAY_PASS
```

完整 D0/D1/D2 时序 + revision replay acceptance 属于 V4-14。

# 15. Structure Projection

Advanced Profile 只能读取 V4-12 Accepted Head。

禁止重新计算：

```text
Anchor
breakout
support
acceptance
```

必须保留 V4-12 producer identity 与 UNKNOWN/NOT_APPLICABLE/DEGRADED。

# 16. Contract Registry

至少新增/更新 versioned：

```text
V4-13 field registry
producer registry
time-role registry
input schema
output schema
LOO contract
projection contract
DAG edge registry
quality/degradation map
machine vectors
```

# 17. 独立向量

至少：

```text
L01 dominant target removed by LOO
L02 small sector after removal insufficient
L03 industry + multiple concepts deterministic
L04 concept membership unknown
L05 no eligible sector -> NOT_APPLICABLE
L06 current-membership historical replay -> degraded, not PIT
L07 LOO relative branch exact
L08 perturb sector context -> raw PREWATCH unchanged
L09 perturb Structure -> B0/B1/B2 unchanged
L10 active_anchor changes -> no V4-12 recomputation
L11 same-day revision -> same t-1 predecessor
L12 membership correction -> new revision, old observation immutable
```

# 18. Negative Gate

必须拒绝：

```text
self-including sector aggregate
UI-first sector as primary
current membership claimed PIT
context modifying raw PREWATCH
structure feeding same-day B stage
D2 feeding D1
missing membership treated FALSE
UNKNOWN treated as weak sector
display cap altering algorithmic set
recomputed V4-12 structure semantics
```

# 19. Stage Entry

R14B 可创建 V4_13_STAGE_ENTRY，但状态只能是：

```text
AUTHORIZED_CONTRACT_DESIGN_ONLY
```

不得 `runtime_implemented=true`。

# 20. Heads / Permissions

保持：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

R14B 不接受 V4-13。

# 21. 完成状态

唯一：

```text
V4_13_R1_PROFILE_ADVANCED_PROJECTION_CONTRACT_FREEZE = PASS
V4_13_RUNTIME = NOT_IMPLEMENTED
NEXT = V4_13_RUNTIME_IMPLEMENTATION_TASKS
```

commit + push 后 STOP。

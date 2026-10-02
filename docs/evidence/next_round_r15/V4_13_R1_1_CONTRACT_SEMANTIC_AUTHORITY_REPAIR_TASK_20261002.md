# R15A｜V4-13 R1.1 Contract Semantic / Authority Repair｜2026-10-02

**执行基线**：`226270c3178736e9b52e0e3574339039ed191350`  
**前置外审**：`R14_EXTERNAL_AUDIT = PARTIAL_PASS_V4_13_CONTRACT_REPAIR_REQUIRED`  
**性质**：Contract Repair ONLY  
**禁止**：V4-13 Runtime / migration / Accepted Head

# 1. 唯一目标

只修复 R14B V4-13 Contract Freeze 的 4 个合同级闭环：

```text
C01 TIME_ROLE_OVERCOUPLING
C02 SECTOR_CONTEXT_STATE_SEMANTICS_NOT_FROZEN
C03 MEMBERSHIP_DAG_SOURCE_AUTHORITY_MISBIND
C04 ROTATION_STRUCTURE_ENRICHMENT_MULTI_SOURCE_BINDING_INCOMPLETE
```

修复完成前：

```text
V4_13_RUNTIME = NOT_AUTHORIZED
```

# 2. 强制 KEEP

必须 byte-identical 保持：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

其中：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-30
```

权限继续：

```text
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

不得创建：

```text
data/v4/V4_13_ACCEPTED_HEAD.json
```

# 3. 版本治理

R14 的 V4-13 R1 已进入审计链，禁止静默覆盖历史语义。

优先新增 versioned R1.1 / v1.1 合同，或使用项目现有 supersedes 机制。例如：

```text
config/v4_13_field_registry_v1_1.json
config/v4_13_time_role_registry_v1_1.json
config/v4_13_dag_edge_registry_v1_1.json
config/v4_13_loo_context_v1_1.json
config/v4_13_output_schema_v1_1.json
config/v4_13_producer_registry_v1_1.json
config/v4_13_quality_map_v1_1.json
config/v4_13_machine_vectors_v1_1.json
```

如既有 naming convention 要求不同名称，允许调整，但必须记录：

```text
supersedes = exact R1 ref
reason = R14_EXTERNAL_AUDIT_C01_C04_REPAIR
```

旧 R1 文件必须保留。

# 4. C01｜拆分 time role

当前错误：

```text
primary_industry
supporting_concepts
```

被统一绑定：

```text
T_WITH_EXACT_T_MINUS_1_LOO_HISTORY
```

修复为：

```text
primary_industry:
T_EXACT_MEMBERSHIP_AT_CUTOFF

supporting_concepts:
T_EXACT_MEMBERSHIP_AT_CUTOFF
```

只依赖：

```text
trade-date-valid membership
source revision
available_at <= cutoff
membership quality
```

不得因为：

```text
loo_history missing
```

而自动 UNKNOWN。

其余字段按真实依赖逐字段登记，禁止“一套 time role 套所有 Context 字段”。

# 5. C01 必测向量

至少新增：

```text
T01
current membership = KNOWN
loo_history = MISSING
```

预期：

```text
primary_industry = KNOWN
supporting_concepts = KNOWN
```

而只有真正依赖 history 的 context 字段允许 UNKNOWN。

再新增：

```text
T02
current membership = UNKNOWN
```

预期：

```text
primary_industry = UNKNOWN
supporting_concepts = UNKNOWN
```

禁止将 UNKNOWN membership 转成空集合。

# 6. C02｜冻结 sector_context_state

禁止保留：

```text
source_field = loo_raw_context_state
```

但没有正式 schema / enum / mapping。

不要发明新的综合评分、成熟度或第二套 Rotation 状态机。

优先冻结：

```text
SECTOR_CONTEXT_STATE_V1
```

为**无损、确定性的 selected LOO sector context snapshot**。

至少包含：

```text
selected_sector_id
sector_type

loo_b0_raw
loo_confirmed_raw
loo_warm_raw

emergence
adjusted_seed_width

rotation_core_state
relative_sector_state

membership_basis
context_quality
reasons[]
source_refs[]
```

如果 accepted owner 使用不同准确字段名，复用正式字段，不创建同义字段。

# 7. C02 语义边界

`sector_context_state`：

```text
不是 eligibility
不是 score
不是 maturity
不是第二套 Rotation
不是第二套 B0/B2
```

必须是：

```text
lossless / deterministic projection
```

source capability：

```text
NOT_IMPLEMENTED
UNKNOWN
NOT_APPLICABLE
DEGRADED
KNOWN
```

必须原样保留。

# 8. C02 独立向量

至少：

```text
S01
LOO B0 known
B2 legacy NOT_IMPLEMENTED
rotation known
relative known
```

输出中必须明确保留：

```text
B2 = NOT_IMPLEMENTED
```

不得把整个 context 误变成 false。

```text
S02
relative UNKNOWN
其余 known
```

输出 object 仍存在，relative component 独立 UNKNOWN，整体 quality 按冻结规则计算。

# 9. C03｜拆分 membership 与 primitives authority

废止这种复合 authority：

```text
producer = F0
field = accepted_membership_and_non_target_primitives
source_owner_binding = V4_04_ACCEPTED_HEAD
```

至少拆为以下边。

## 9.1 Membership Edge

必须显式绑定：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

或通过：

```text
V4_08_ACCEPTED_HEAD_AMENDED_R1
→ exact membership_binding
→ V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
```

可复核解析。

必须保存：

```text
membership_snapshot_id
source_revision
trade_date
available_at / cutoff
membership_basis
membership_quality
```

## 9.2 Core Primitive Edge

非目标成员的 price/core facts：

```text
→ 对应 V4_04 / V4_05 accepted owner
```

如果 LOO 重算需要：

```text
base_seed_raw
```

必须单独绑定：

```text
V4_07_ACCEPTED_HEAD
```

不得让 V4_04 代替 V4_07 Seed authority。

# 10. C03 Consumer Scope Gate

增加独立 validator：

```text
V4_13 engineering consumer
→ V4_08 Accepted Head
→ exact membership binding
→ V4_08 PIT Membership Accepted Head
```

同时验证：

```text
production_permission = false
```

如果 accepted routing 无法证明：

```text
BLOCKED_MEMBERSHIP_CONSUMER_SCOPE
```

禁止：

```text
provider direct read
raw source bypass
current-membership silent fallback
```

# 11. C04｜rotation_structure_enrichment 双来源

字段必须显式登记两个 source：

```text
rotation_source =
V4_08 Accepted Head / rotation_core_state

structure_source =
V4_12 Accepted Head / read-only D1 Structure
```

可使用：

```text
source_bindings = [...]
```

或项目等价正式结构。

不能继续只写：

```text
source_binding = V4_08
source_field = rotation_core_state_PLUS_READ_ONLY_D1
```

# 12. C04 Object Schema

冻结：

```text
ROTATION_STRUCTURE_ENRICHMENT_V1
```

至少明确：

```text
rotation_core_state
rotation_quality
rotation_source_ref

structure_component
structure_quality
structure_source_ref

combined_quality
reasons[]
```

`structure_component` 只能读取 V4-12 accepted projection，不允许重算 Structure。

# 13. C04 Quality Propagation

必须满足：

```text
V4_08 rotation KNOWN
+
V4_12 D1 unavailable
```

不能改写：

```text
rotation_core_state
```

只能：

```text
structure component = UNKNOWN / NOT_IMPLEMENTED
rotation component = preserved
combined enrichment quality = degraded/partial per frozen rule
```

反向同理。

# 14. DAG 再验收

修复后仍必须证明：

```text
D2[t] !-> D1[t]

D1[t] !-> B0[t]
D1[t] !-> B1[t]
D1[t] !-> B2[t]

CONTEXT[t] !-> A[t]
CONTEXT[t] !-> C[t]

Focus/UI !-> QUALIFICATION

Supplemental !-> Core

Future Outcome !-> Same-day State
```

# 15. 新独立 vectors

至少新增：

```text
R15-01
membership current known + no LOO history
=> primary/supporting KNOWN

R15-02
membership unknown
=> primary/supporting UNKNOWN, not empty

R15-03
LOO history missing
=> only dependent context fields degrade

R15-04
sector_context_state exact structured object

R15-05
membership authority exact V4-08 PIT head

R15-06
core member facts exact V4-04/V4-05 owner

R15-07
seed input exact V4-07 owner

R15-08
rotation_structure_enrichment exact dual bindings

R15-09
D1 unavailable does not mutate rotation_core_state

R15-10
D1 perturbation does not mutate B1

R15-11
Context perturbation does not mutate A/C

R15-12
same-day revisions retain exact t-1 predecessor
```

Expected outputs 必须手写，不得调用 Runtime implementation helper 生成 oracle。

# 16. Negative Gate

必须拒绝：

```text
primary_industry requires t-1 LOO history
supporting_concepts requires t-1 LOO history

membership authority bound only to V4_04
membership provider/raw bypass

base_seed_raw owned by V4_04

rotation_structure_enrichment single-source only

undefined sector_context_state shape

context writes raw A/C qualification

D1 -> B0/B1/B2 same-day

D2 -> D1 same-day

UNKNOWN membership treated as empty

CURRENT_MEMBERSHIP_REPLAY claimed PIT
```

# 17. Completeness Matrix

新的 completeness gate 不允许只验证：

```text
file exists
field exists
vector count
```

必须逐字段核：

```text
semantic definition
data type / object schema
producer
source binding(s)
time role
quality propagation
UNKNOWN / NOT_APPLICABLE
runtime capability
consumer scope
```

每项只能：

```text
FROZEN
BLOCKED_WITH_EXPLICIT_REASON
```

不得 silent TODO / TBD。

# 18. 禁止范围

R15 禁止：

```text
V4-13 Runtime code
DB migration
V4_13_ACCEPTED_HEAD

V4-14 Replay Gate B
Radar/Cohort/Settlement
Production
Shadow
Focus
Data Head advance
V4-12 re-promotion
```

# 19. Clean Detached Gate

必须验证：

```text
R14A V4-12 Accepted Head exact unchanged
Stage Head exact unchanged
Data Head exact unchanged

R8-R13 evidence unchanged

no V4-13 runtime
no migration

C01-C04 all repaired
new vectors all PASS
negative gates all reject
git clean before/after
```

# 20. 完成状态

唯一允许：

```text
V4_13_R1_1_CONTRACT_SEMANTIC_AUTHORITY_REPAIR =
PASS

V4_13_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_13_RUNTIME =
NOT_IMPLEMENTED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

commit + push 后立即 STOP。

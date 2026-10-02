# R16A｜V4-13 Accepted Input Binder + LOO Context Core Runtime｜2026-10-02

**执行基线**：`dcbfe610b5cb0a8d94dc743963a1fa80f7f71f32`  
**前置状态**：

```text
V4_13_CONTRACT_COMPLETENESS = PASS
V4_13_RUNTIME = AUTHORIZED_NEXT_SCOPED_ENGINEERING
```

**任务性质**：Runtime Implementation / Part A  
**禁止**：Accepted Head / V4-14 / Production

# 1. 唯一目标

实现 V4-13 的 accepted-source input binding 与 LOO Context 核心生产链：

```text
accepted source authority
→ exact input binder
→ current membership relation projection
→ target-excluded LOO recomputation
→ relative sector state
→ algorithmic support sector
```

不得实现第二套 Core / Rotation / Structure。

# 2. Runtime Contract Authority

唯一业务权威：

```text
config/v4_13_*_v1_1.json
```

尤其：

```text
v4_13_input_schema_v1_1.json
v4_13_field_registry_v1_1.json
v4_13_time_role_registry_v1_1.json
v4_13_membership_consumer_route_v1_1.json
v4_13_loo_context_v1_1.json
v4_13_dag_edge_registry_v1_1.json
v4_13_quality_map_v1_1.json
v4_13_machine_vectors_v1_1.json
```

禁止重新解释 R15/R15R1 已冻结语义。

# 3. Accepted Input Binder

建议新增正式 Runtime 模块，例如：

```text
src/workbench_analysis/v4_13_input_binder.py
```

或项目现有命名规范下等价模块。

Binder 只允许消费 exact accepted owners：

```text
Membership:
V4_08 Accepted Head
→ exact membership_binding
→ V4_08 PIT Membership Accepted Head

Core facts:
V4_04 Accepted Head

Native facts:
V4_05 Accepted Head

Base Seed:
V4_07 Accepted Head

Sector/Rotation:
V4_08 Accepted Head

Structure:
V4_12 Accepted Head
```

# 4. 禁止 Source Fallback

明确：

```text
raw_fallback = false
provider_direct_read = false
current_membership_silent_fallback = false
raw_reconstruction = false
```

缺 accepted capability：

```text
UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
```

不得使用 BaoStock/TDX/provider 原始数据临时补洞。

这不是 Data Producer 任务。

# 5. Current Membership Projection

实现：

```text
MEMBERSHIP_RELATION_PROJECTION_V1
```

输出：

```text
primary_industry
supporting_concepts
```

必须只依赖：

```text
T current exact membership
source_revision
available_at <= cutoff
membership_quality
```

不得读取：

```text
LOO history
t-1 Context
rotation history
```

## primary_industry

按冻结排序：

```text
official classification priority ASC
taxonomy depth DESC
sector_id ASC
```

缺 conflict metadata：

```text
UNKNOWN
```

已知完整且无行业关系：

```text
NOT_APPLICABLE
```

## supporting_concepts

输出：

```text
全部 date-valid theme relations
```

不是显示 cap 后集合。

排序 deterministic。

membership UNKNOWN：

```text
value = null
quality = UNKNOWN
```

禁止：

```text
[]
```

# 6. LOO Target Exclusion

对每个 target stock `s`：

```text
对每个相关 sector
先 REMOVE s
再进行任何 aggregate / rank / state 计算
```

禁止：

```text
先算 self-including sector
再减 member_count
```

必须真正重算：

```text
native return medians
breadth
MA width
amount/concentration

Base Seed aggregates
K/N/UNKNOWN
Wilson ordering

full qualified sector universe
ranks / medians

B0 raw
B2 raw

required history endpoints
common-member cohort
rotation history lineage
```

# 7. LOO Core Owner Reuse

所有公式必须调用或严格复用 accepted owner contract/AST：

```text
V4_08 sector native
V4_08 B0
V4_08 B2
V4_08 rotation
V4_07 Base Seed
V4_04/V4_05 primitive semantics
```

禁止复制后修改阈值。

如复用 owner helper：

```text
需要证明输入 lineage 已 target-excluded
```

如无法复用 helper：

```text
实现必须有 independent owner-parity vectors
```

# 8. Minimum Members / Coverage

严格继承：

```text
V4_08_SECTOR_MIN_MEMBERS
V4_08_SECTOR_MIN_QUOTE_COVERAGE
```

规则：

```text
below minimum
→ UNKNOWN_INSUFFICIENT_LOO_MEMBERS

incomplete coverage
→ UNKNOWN_NO_ZERO_IMPUTATION

0 non-target members:
    membership complete/known
    → NOT_APPLICABLE
    otherwise
    → UNKNOWN
```

禁止 zero imputation。

# 9. Historical Capability

`algorithmic_support_sector` 需要：

```text
ACCEPTED_OWNER_REGISTERED_B0_B2_COMPARE_ENDPOINTS_AND_LOO_LINEAGE
```

如果 accepted historical LOO lineage 不足：

```text
algorithmic_support_sector = UNKNOWN
```

但这不得污染：

```text
primary_industry
supporting_concepts
relative_sector_state
```

中不依赖历史的部分。

# 10. Relative Sector State

实现：

```text
RELATIVE_STATE_V1
```

但只替换：

```text
rel_market_1 -> rel_sector_1
rel_market_5 -> rel_sector_5
```

其余：

```text
rps5
rps20
rps20_delta3
compression_state
ma_structure_state
```

必须来自 accepted stock owner。

不得复制第二套 Relative State priority / threshold。

# 11. Algorithmic Support Sector

只在所有 required LOO authority READY 时参与正式选择。

排序严格：

```text
LOO_confirmed_raw DESC
LOO_warm_raw DESC
emergence HIGH > MEDIUM > LOW
adjusted_seed_width DESC
sector_id ASC
```

`rotation_core_state / relative_sector_state`：

```text
explanatory only
not new sort rules
```

显示 cap：

```text
view only
never changes algorithmic candidate set
```

# 12. Membership Basis

正式 2026-09-30 membership：

```text
PIT_OBSERVED
```

历史日期若没有 accepted PIT membership：

```text
禁止用 2026-09-30 current membership 倒灌后声称 PIT
```

如需要 diagnostic current-membership replay：

```text
membership_basis =
HISTORICAL_REPLAY_CURRENT_MEMBERSHIP

quality =
DEGRADED

formal_context_eligible =
false
```

本卡正式 Runtime 不应依赖 diagnostic replay 才能 PASS。

# 13. Runtime Output / Internal Evidence

R16A 至少生成：

```text
accepted_input_bindings
membership_relation_rows
loo_sector_context_rows
relative_sector_state_rows
algorithmic_support_sector_rows
authority/quality diagnostics
```

每行必须携带：

```text
security_id
trade_date
revision
cutoff

source refs
membership_snapshot_id
membership source revision
membership_basis
LOO identity/digest
quality
reason
```

# 14. Synthetic Hard Cases

至少：

```text
A01 dominant target stock
→ remove target
→ sector state changes

A02 2-member sector
→ remove target leaves 1
→ minimum-members UNKNOWN/NA per owner rule

A03 membership KNOWN + no LOO history
→ primary/supporting remain KNOWN
→ algorithmic support sector may UNKNOWN

A04 membership UNKNOWN
→ primary/supporting null/UNKNOWN

A05 exact current industry + multiple concepts
→ deterministic relation projection

A06 no relation, complete known membership
→ NOT_APPLICABLE

A07 incomplete quote coverage
→ UNKNOWN, no zero fill

A08 target excluded from rank/median and historical cohort

A09 relative-sector substitution exact owner parity

A10 display cap perturbation
→ algorithmic set unchanged

A11 current membership replay diagnostic
→ DEGRADED and non-formal

A12 provider/raw fallback attempt
→ rejected/fail closed
```

# 15. Independent Oracle

Expected values不能由 V4-13 Runtime helper 生成。

至少：

```text
hand-written LOO member set
hand-written medians / coverage
hand-written membership relation result
hand-written selector ordering
literal owner AST parity cases
```

# 16. Local Gate

R16A 完成后只允许：

```text
V4_13_R16A_LOO_CONTEXT_RUNTIME =
PASS_SCOPED_ENGINEERING_LOCAL

V4_13_RUNTIME =
PARTIAL_IMPLEMENTED_R16A

NEXT =
R16B
```

不得 commit/push 后 STOP；继续 R16B。

# 17. 禁止

```text
V4_13_ACCEPTED_HEAD
Stage Head advance
Data Head advance

V4-14 acceptance
Production
Shadow
Focus
Radar/Cohort/Settlement
formal DB migration
raw provider fallback
```

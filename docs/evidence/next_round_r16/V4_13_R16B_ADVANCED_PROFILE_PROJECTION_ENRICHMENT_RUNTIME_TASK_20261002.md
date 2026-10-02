# R16B｜V4-13 Advanced Profile Projection + Enrichment Runtime｜2026-10-02

**前置**：

```text
R16A local gate = PASS
```

**任务性质**：Runtime Implementation / Part B

# 1. 唯一目标

实现 V4-13 Advanced Profile 的剩余运行时输出：

```text
sector_context_state
sector_context_quality

rotation_structure_enrichment

V4-12 Structure read-only projection

完整 Profile Advanced output envelope
```

不得改变任何 Raw Qualification。

# 2. SECTOR_CONTEXT_STATE_V1

严格按照：

```text
config/v4_13_sector_context_state_schema_v1_1.json
```

生成 lossless selected LOO context snapshot。

字段：

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
reasons
source_refs
```

# 3. Component Envelope

每个 component 保留：

```text
value
quality
reasons
source_refs
```

source refs 至少：

```text
path
sha256
bytes
producer_contract_id
trade_date
available_at
source_revision
```

不得丢掉 source identity。

# 4. Component Quality

只允许：

```text
KNOWN
UNKNOWN
NOT_IMPLEMENTED
NOT_APPLICABLE
DEGRADED
```

严格用：

```text
V4_13_QUALITY_DEGRADATION_V1
component_pair_table
```

折叠 metadata quality。

禁止：

```text
UNKNOWN -> false
NOT_IMPLEMENTED -> false
```

缺一个 component：

```text
只降级该 component
object 仍存在
```

# 5. No Selected Sector

只有：

```text
known complete candidate set
+
no eligible sector
```

才能：

```text
selected_sector_id = null
quality = NOT_APPLICABLE
```

如果 selection 不确定：

```text
UNKNOWN
```

不能偷用 NOT_APPLICABLE。

# 6. V4-12 Structure Projection

严格实现：

```text
PROFILE_ADVANCED_PROJECTION_V1
```

只允许读取由：

```text
V4_12_ACCEPTED_HEAD
```

授权的 publication manifest。

复制：

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

模式：

```text
COPY_VALUE_QUALITY_REASON_PRODUCER_IDENTITY_SOURCE_REF_NO_RECOMPUTATION
```

禁止：

```text
重新选择 Anchor
重新算 Breakout
重新算 Support
重新算 Acceptance
```

# 7. Structure Capability Degradation

如果 target-date V4-12 authorized publication 不存在：

```text
Structure fields =
UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
```

不得：

```text
读取 R13 candidate 目录冒充 Accepted publication
直接运行 V4-12 Runtime 临时重算
raw bars reconstruct Structure
```

# 8. Rotation / Structure Enrichment

严格实现：

```text
ROTATION_STRUCTURE_ENRICHMENT_V1
```

两个 source：

```text
rotation_source =
V4_08 Accepted Head

structure_source =
V4_12 Accepted Head authorized publication
```

输出：

```text
rotation_core_state
rotation_quality
rotation_source_ref

structure_component
structure_quality
structure_source_ref

combined_quality
reasons
```

# 9. Component Independence

必须：

```text
rotation KNOWN
+
structure unavailable
→ rotation unchanged
→ structure UNKNOWN/NOT_IMPLEMENTED
→ combined quality degraded
```

反向同理。

禁止：

```text
D1 unavailable
→ overwrite rotation_core_state

rotation unavailable
→ erase valid Structure
```

# 10. No Writeback

硬门：

```text
rotation_structure_enrichment
!-> B1
```

同时：

```text
Context[t] !-> A[t]
Context[t] !-> C[t]
D1[t] !-> B0/B1/B2[t]
```

必须有 perturbation test。

# 11. Advanced Profile Output

按：

```text
V4_13_OUTPUT_SCHEMA_V1
```

至少输出完整字段：

```text
primary_industry
supporting_concepts
algorithmic_support_sector
relative_sector_state
sector_context_state
sector_context_quality
rotation_structure_enrichment

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

每个 field envelope：

```text
value
quality
reason
source_identity
membership_basis
loo_basis
```

# 12. Publication Identity

至少：

```text
security_id
trade_date
revision
contract_digest
membership_digest
loo_history_digest
structure_source_digest
prior_session_ref
```

同样输入必须 deterministic。

# 13. Raw Qualification Freeze

必须读取并证明：

```text
A_BASE_SEED_RAW before == after
C_STOCK_PREWATCH_RAW before == after
B0/B1/B2 before == after
```

Context / Structure perturbation 不能影响其 bytes/digest。

# 14. Synthetic Hard Cases

至少：

```text
B01 component UNKNOWN only degrades itself
B02 B2 NOT_IMPLEMENTED preserved in context object
B03 no eligible known set -> NOT_APPLICABLE
B04 uncertain selection -> UNKNOWN
B05 V4-12 publication unavailable -> Structure only UNKNOWN
B06 valid Structure exact copy
B07 active_anchor changes -> projection changes only, no recomputation
B08 rotation known + Structure unavailable
B09 rotation unavailable + Structure known
B10 combined quality exact literal table
B11 Context perturbation -> A/C unchanged
B12 D1 perturbation -> B0/B1/B2 unchanged
```

# 15. Local Gate

完成后：

```text
V4_13_R16B_ADVANCED_PROFILE_RUNTIME =
PASS_SCOPED_ENGINEERING_LOCAL

V4_13_RUNTIME =
PARTIAL_IMPLEMENTED_R16A_R16B

NEXT =
R16C
```

继续 R16C，不创建 Accepted Head。

# 16. 禁止

```text
V4_13_ACCEPTED_HEAD
Stage/Data Head advance
V4-14 acceptance
Production / Shadow / Focus
Radar/Cohort
formal DB migration
```

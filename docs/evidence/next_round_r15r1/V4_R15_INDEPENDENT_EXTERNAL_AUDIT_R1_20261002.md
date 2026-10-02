# V4 R15 独立外部验收 R1｜2026-10-02

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**R15 基线**：`226270c3178736e9b52e0e3574339039ed191350`  
**当前远端 HEAD**：`c7b2cb92c5fb12127a941d5af102742fe0d5e965`  
**Clean detached tested source**：`202a48170fd765da0fd247683baf3e688091b3f8`

# 1. 唯一总裁决

```text
R15_EXTERNAL_AUDIT =
PARTIAL_PASS_VERSION_LINEAGE_CLEANUP_REQUIRED

C01_TIME_ROLE_OVERCOUPLING =
PASS_KEEP

C02_SECTOR_CONTEXT_STATE_SEMANTICS =
PASS_KEEP

C03_MEMBERSHIP_SOURCE_AUTHORITY =
PASS_KEEP

C04_ROTATION_STRUCTURE_MULTI_SOURCE =
PASS_KEEP

R15_SCOPE_NO_RUNTIME =
PASS

R15_PROTECTED_HEADS =
PASS_EXACT_UNCHANGED

V4_13_CONTRACT_BUSINESS_SEMANTICS =
PASS_KEEP

V4_13_CONTRACT_VERSION_LINEAGE =
BLOCKED_BY_G01_G02

V4_13_RUNTIME =
NOT_AUTHORIZED_YET
```

本轮不是业务合同返工。C01-C04 已经修复成功。  
唯一剩余问题是两个新建 schema 的 `supersedes` lineage 写错，以及 validator 没有识别这种错误。

# 2. 提交链

相对 R15 基线共 3 个提交：

```text
0c2eb40ce53e1dacfaf2ceeaebdc2d0afa27d870
Repair V4-13 contract semantics and exact source authority for R15

202a48170fd765da0fd247683baf3e688091b3f8
Record exact Git baseline comparison for clean R15 validation

c7b2cb92c5fb12127a941d5af102742fe0d5e965
Seal R15 clean detached validation and contract audit evidence
```

最终封存提交只更新 clean validation / handoff evidence，没有继续改 contract/runtime 语义。

# 3. Scope Gate｜PASS

R15 相对基线只新增/修改：

```text
config/v4_13_*_v1_1.json
docs/evidence/next_round_r15/*
reports/v4_13_r1_1/*
scripts/repair/validate/vector tooling
tests/test_v4_13_r15_contract.py
```

没有新增：

```text
src/ V4-13 runtime
migrations/
data/v4/V4_13_ACCEPTED_HEAD.json
```

Clean detached evidence：

```text
status = PASS
clean_before = true
clean_after = true
runtime_added = false
migration_added = false
read_only = true
head_changes = false
```

因此：

```text
R15_SCOPE_NO_RUNTIME = PASS
```

# 4. Protected Heads｜PASS

独立读取并逐字节比较 R15 baseline 与当前 HEAD：

```text
data/v4/V4_12_ACCEPTED_HEAD.json = EXACT_SAME
data/v4/V4_STAGE_ACCEPTED_HEAD.json = EXACT_SAME
data/v4/V4_DATA_ACCEPTED_HEAD.json = EXACT_SAME
AGENTS.md = EXACT_SAME
```

当前继续：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-30
```

没有 re-promotion、没有 Data Head 偷推进。

# 5. C01｜PASS_KEEP

`primary_industry` 与 `supporting_concepts` 已从错误的：

```text
T_WITH_EXACT_T_MINUS_1_LOO_HISTORY
```

拆成：

```text
T_EXACT_MEMBERSHIP_AT_CUTOFF
```

并明确：

```text
history_dependencies = []
prior = NOT_REQUIRED_FOR_THIS_FIELD
loo_history_required = false
```

current dependencies 只保留：

```text
trade_date_valid_membership
source_revision
available_at_le_cutoff
membership_quality
```

同时：

```text
UNKNOWN membership
!=
empty relation
```

`supporting_concepts` 缺失语义为：

```text
UNKNOWN_VALUE_NULL_NOT_EMPTY_ARRAY
```

符合上一轮外审要求。

# 6. C02｜PASS_KEEP

已新增正式 schema：

```text
SECTOR_CONTEXT_STATE_V1
```

语义冻结为：

```text
LOSSLESS_SELECTED_LOO_CONTEXT_SNAPSHOT_NO_NEW_SCORE_OR_STATE_MACHINE
```

明确包含：

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

每个 component 都保留：

```text
value
quality
reasons
source_refs
```

质量允许：

```text
KNOWN
UNKNOWN
NOT_IMPLEMENTED
NOT_APPLICABLE
DEGRADED
```

并明确：

```text
OBJECT_REMAINS_AND_ONLY_COMPONENT_IS_UNKNOWN_OR_NOT_IMPLEMENTED
```

因此没有再发明第二套 eligibility、score、maturity 或 Rotation state。

# 7. C03｜PASS_KEEP

旧的复合 authority：

```text
accepted_membership_and_non_target_primitives -> V4_04
```

已移除。

当前 DAG 已拆分：

```text
date_valid_membership
→ V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1

non_target_core_facts
→ V4_04_ACCEPTED_HEAD

non_target_native_facts
→ V4_05_ACCEPTED_HEAD

non_target_base_seed_raw
→ V4_07_ACCEPTED_HEAD
```

Membership engineering consumer route 已显式证明：

```text
V4_13_SCOPED_ENGINEERING_ONLY
→ V4_08_ACCEPTED_HEAD_AMENDED_R1
→ membership_binding
→ V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
```

并保持：

```text
formal_consumers_flag_override = false
provider_direct_read = false
raw_fallback = false
current_membership_silent_fallback = false
production_permission = false
```

validator 实际读回 PIT snapshot / facts / source_revision，并核：

```text
membership_basis = PIT_OBSERVED
target_trade_date = 2026-09-30
```

因此：

```text
ENGINEERING_CONSUMER_SCOPE_PROVEN
```

可接受。

# 8. C04｜PASS_KEEP

`rotation_structure_enrichment` 已从单一 V4-08 source 改为显式双来源：

```text
rotation_source
= V4_08_ACCEPTED_HEAD_AMENDED_R1

structure_source
= V4_12_ACCEPTED_HEAD
```

正式 schema：

```text
ROTATION_STRUCTURE_ENRICHMENT_V1
```

明确：

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

并冻结：

```text
missing_structure
→ STRUCTURE_ONLY_UNKNOWN_OR_NOT_IMPLEMENTED
→ ROTATION_UNCHANGED

missing_rotation
→ ROTATION_ONLY_UNKNOWN_OR_NOT_IMPLEMENTED
→ STRUCTURE_UNCHANGED
```

同时：

```text
writeback_to_B1 = false
```

符合 D1 只允许进入 D3 enrichment、不得回写 B1 的要求。

# 9. DAG Negative Gates｜PASS

继续禁止：

```text
D2[t] -> D1[t]

D1[t] -> B0[t]
D1[t] -> B1[t]
D1[t] -> B2[t]

CONTEXT[t] -> A[t]
CONTEXT[t] -> C[t]

Focus/UI -> QUALIFICATION
Supplemental -> Core
Future Outcome -> Same-day State
```

15 个 negative gates 均为：

```text
REJECTED
```

包括：

```text
wrong_membership_owner
provider_bypass
seed_owned_by_core
single_source_enrichment
undefined_context_object
context_changes_qualification
D1_to_B0/B1/B2
D2_to_D1
unknown_to_empty
current_membership_claimed_pit_or_formal_override
current_replay_claimed_pit
```

# 10. Independent Vectors / Tests

R15 v1.1 当前有：

```text
14 contract vectors
25 literal component-quality pair cases
15 negative gates
```

Clean test：

```text
45 tests
45 passed
0 failed
0 errors
0 skipped
```

Expected vector outputs由独立 literal witness 提供，没有导入 V4-13 Runtime 实现，因为 Runtime 尚不存在。

# 11. G01｜FALSE_SUPERSEDES_LINEAGE

这是当前唯一实质 blocker。

新建合同：

```text
config/v4_13_sector_context_state_schema_v1_1.json
contract_id = SECTOR_CONTEXT_STATE_V1
version = 1.0.0
```

却写：

```text
supersedes =
config/v4_13_output_schema_v1.json

predecessor contract_id =
V4_13_OUTPUT_SCHEMA_V1
```

这不成立。

`SECTOR_CONTEXT_STATE_V1` 是 R15 新引入的独立 schema，没有同 contract family 的旧版本。  
它可以说：

```text
introduced_in = R15
derived_from / replaces_definition_from = old output/field contract
```

但不能说：

```text
SECTOR_CONTEXT_STATE_V1 supersedes V4_13_OUTPUT_SCHEMA_V1
```

第二处同类错误：

```text
config/v4_13_rotation_structure_enrichment_schema_v1_1.json

contract_id =
ROTATION_STRUCTURE_ENRICHMENT_V1

supersedes =
config/v4_13_field_registry_v1.json

predecessor contract_id =
V4_13_FIELD_REGISTRY_V1
```

同样属于错误 lineage。

这两个 schema 是“从旧 registry 中抽出并正式冻结的新合同”，不是旧 registry 本身的 successor。

# 12. G02｜VALIDATOR_DOES_NOT_VALIDATE_SUPERSEDES_IDENTITY

当前：

```python
if 'supersedes' in obj:
    exact(obj['supersedes'])
```

只证明：

```text
被引用文件存在
bytes/hash 正确
```

没有证明：

```text
predecessor contract_id 与 current contract_id 属于同一 contract family
```

因此当前 validator 会把：

```text
SECTOR_CONTEXT_STATE_V1
supersedes
V4_13_OUTPUT_SCHEMA_V1
```

这种逻辑错误判成 PASS。

这是 validator coverage 缺口。

# 13. 为什么 G01/G02 阻断 FULL PASS

这不影响 C01-C04 的业务语义正确性，也不要求回滚 R15。

但 V4-13 目前正处于：

```text
Contract Freeze
```

合同的版本 lineage 本身就是治理事实。

如果现在带着错误 `supersedes` 进入 Runtime / Accepted Head：

```text
后续无法准确回答：
这个合同是旧合同升级，
还是新合同首次引入？
```

而项目要求版本修改必须保留：

```text
版本号
原因
迁移/继承关系
```

因此必须先把这两处 lineage 清理掉。

# 14. 正确修复方式

对于已有同族 R1 predecessor 的 v1.1：

```text
field_registry
time_role_registry
dag_edge_registry
input/output schema
loo_context
producer_registry
quality_map
projection
parameter_set
machine_vectors
```

当前 `supersedes` 保持不动。

只修两个新合同：

```text
SECTOR_CONTEXT_STATE_V1
ROTATION_STRUCTURE_ENRICHMENT_V1
```

它们应：

```text
remove supersedes
```

并改为非 successor 语义，例如：

```text
introduced_in = V4_13_R1_1_CONTRACT_REPAIR
derived_from = [...]
definition_replaces = [...]
```

其中 `derived_from / definition_replaces` 可以继续保存原 field/output registry 的 exact path/hash，用于说明来源，但不能叫 `supersedes`。

validator 必须新增：

```text
若存在 supersedes：
load predecessor
assert predecessor.contract_id == current.contract_id
```

若未来确实支持 contract_id rename，则必须有显式：

```text
contract_family_id
rename/migration contract
```

不能靠路径近似。

对于首次引入 contract：

```text
supersedes MUST NOT EXIST
```

# 15. 下一步

只需要一张很小的治理清理卡：

```text
R15R1
V4-13 Version Lineage Cleanup
```

顺序：

```text
fix G01
→ strengthen validator G02
→ rerun 45+ tests
→ clean detached validation
→ commit + push
→ STOP
→ external audit
```

仍然禁止 V4-13 Runtime。

R15R1 外审通过后，V4-13 Contract Freeze 即可正式 FULL PASS，下一轮进入 V4-13 Runtime implementation。

# R15R1｜V4-13 Version Lineage Cleanup｜2026-10-02

**执行基线**：`c7b2cb92c5fb12127a941d5af102742fe0d5e965`  
**前置结论**：

```text
R15_EXTERNAL_AUDIT =
PARTIAL_PASS_VERSION_LINEAGE_CLEANUP_REQUIRED
```

**性质**：Governance / Contract Lineage Cleanup ONLY

# 1. 唯一目标

只修：

```text
G01 FALSE_SUPERSEDES_LINEAGE
G02 VALIDATOR_DOES_NOT_VALIDATE_SUPERSEDES_IDENTITY
```

C01-C04 已通过，不得重做业务合同。

# 2. 强制 KEEP

必须 byte-identical 保持：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
AGENTS.md
```

并保持：

```text
Stage = V4_00_TO_V4_12_ACCEPTED
Data = 2026-09-30
```

不得创建：

```text
V4_13_ACCEPTED_HEAD
```

# 3. G01｜修复错误 supersedes

当前错误 1：

```text
config/v4_13_sector_context_state_schema_v1_1.json

contract_id =
SECTOR_CONTEXT_STATE_V1

supersedes =
config/v4_13_output_schema_v1.json

predecessor contract_id =
V4_13_OUTPUT_SCHEMA_V1
```

当前错误 2：

```text
config/v4_13_rotation_structure_enrichment_schema_v1_1.json

contract_id =
ROTATION_STRUCTURE_ENRICHMENT_V1

supersedes =
config/v4_13_field_registry_v1.json

predecessor contract_id =
V4_13_FIELD_REGISTRY_V1
```

这两个都是 R15 首次引入的独立 contract family。

必须：

```text
remove supersedes
```

不得伪造同族 predecessor。

允许新增：

```text
introduced_in = V4_13_R1_1_CONTRACT_REPAIR
```

并使用：

```text
derived_from[]
definition_replaces[]
```

或项目等价命名记录其来源定义。

建议：

```text
SECTOR_CONTEXT_STATE_V1
derived_from:
- config/v4_13_output_schema_v1.json
- config/v4_13_field_registry_v1.json

ROTATION_STRUCTURE_ENRICHMENT_V1
derived_from:
- config/v4_13_field_registry_v1.json
- config/v4_13_dag_edge_registry_v1.json
```

所有 ref 必须 path/hash/bytes 精确绑定。

`derived_from` 只表示定义来源，不表示版本继承。

# 4. 已正确的 supersedes 禁止改坏

以下同族 v1.1 predecessor 当前是正确的，应保留：

```text
V4_13_DAG_INTEGRATION_INTERFACE_V1
V4_13_FIELD_REGISTRY_V1
V4_13_INPUT_SCHEMA_V1
LOO_CONTEXT_V1
V4_13_INDEPENDENT_MACHINE_VECTORS_V1
V4_13_OUTPUT_SCHEMA_V1
V4_13_PARAMETER_SET_V1
V4_13_PRODUCER_REGISTRY_V1
PROFILE_ADVANCED_PROJECTION_V1
V4_13_QUALITY_DEGRADATION_V1
V4_13_TIME_ROLE_REGISTRY_V1
```

这些 v1.1 的 `supersedes` 应继续指向同 contract_id 的 v1 predecessor。

# 5. G02｜升级 validator

修改：

```text
scripts/validate_v4_13_r1_1.py
```

不得再只有：

```python
exact(obj['supersedes'])
```

必须：

```text
if supersedes exists:
    exact predecessor ref
    load predecessor
    assert predecessor.contract_id == current.contract_id
```

并建议同时检查：

```text
current.version > predecessor.version
```

至少按 semantic version 进行可比较的 major/minor/patch 检查。

如未来允许 contract_id rename：

```text
必须显式 contract_family_id
+
rename/migration contract
```

本轮不需要实现 rename。

# 6. 新增 Negative Gates

至少新增：

```text
L01
SECTOR_CONTEXT_STATE_V1 supersedes V4_13_OUTPUT_SCHEMA_V1
=> REJECTED

L02
ROTATION_STRUCTURE_ENRICHMENT_V1 supersedes V4_13_FIELD_REGISTRY_V1
=> REJECTED

L03
same contract_id + exact old v1 predecessor
=> ACCEPTED

L04
new contract without supersedes + valid introduced_in/derived_from
=> ACCEPTED

L05
supersedes path/hash exact but contract_id mismatch
=> REJECTED
```

# 7. Repair Script

同时修改：

```text
scripts/repair_v4_13_r1_1.py
```

保证从 baseline 重跑时不会重新生成两个错误 `supersedes`。

要求 deterministic。

# 8. Amendment / Handoff

更新：

```text
V4_13_CONTRACT_AMENDMENT_R1_1
R15/R15R1 contract gate evidence
final handoff
```

不得把：

```text
CONTRACT_REPAIR_CANDIDATE
```

误升格为 V4-13 Accepted Head。

外审前仍保持：

```text
runtime_implemented = false
production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 9. Clean Detached Gate

必须证明：

```text
C01-C04 all still PASS
G01 fixed
G02 validator rejects false supersedes

protected Heads exact unchanged

no src runtime
no migration
no V4_13_ACCEPTED_HEAD

git clean before/after
```

# 10. 完成状态

唯一允许：

```text
R15R1_VERSION_LINEAGE_CLEANUP = PASS

V4_13_CONTRACT_COMPLETENESS =
PASS_READY_FOR_EXTERNAL_AUDIT

V4_13_RUNTIME =
NOT_IMPLEMENTED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

commit + push 后立即 STOP。

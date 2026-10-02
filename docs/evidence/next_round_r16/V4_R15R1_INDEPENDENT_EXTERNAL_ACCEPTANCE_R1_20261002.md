# V4 R15R1 独立外部验收 R1｜2026-10-02

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**R15R1 基线**：`c7b2cb92c5fb12127a941d5af102742fe0d5e965`  
**Clean detached tested source**：`57ba77694e2a1ceb692dab4e0eea745d4d889e07`  
**当前远端 HEAD**：`dcbfe610b5cb0a8d94dc743963a1fa80f7f71f32`

# 1. 唯一总裁决

```text
R15R1_EXTERNAL_AUDIT =
PASS_FULL_CONTRACT_FREEZE

G01_FALSE_SUPERSEDES_LINEAGE =
PASS

G02_SUPERSEDES_IDENTITY_VALIDATOR =
PASS

C01_TIME_ROLE_OVERCOUPLING =
PASS_KEEP

C02_SECTOR_CONTEXT_STATE_SEMANTICS =
PASS_KEEP

C03_MEMBERSHIP_SOURCE_AUTHORITY =
PASS_KEEP

C04_ROTATION_STRUCTURE_MULTI_SOURCE =
PASS_KEEP

V4_13_CONTRACT_COMPLETENESS =
PASS

V4_13_RUNTIME =
AUTHORIZED_NEXT_SCOPED_ENGINEERING

V4_13_ACCEPTED_HEAD =
NOT_AUTHORIZED_YET

V4_14_REPLAY_GATE_B =
NOT_AUTHORIZED_YET
```

R15R1 已关闭 V4-13 Contract Freeze 的最后一个治理缺口。  
从本轮开始，不再增加合同修复轮；下一阶段正式进入 V4-13 Runtime implementation。

# 2. 提交链

R15R1 共 2 个提交：

```text
57ba77694e2a1ceb692dab4e0eea745d4d889e07
Correct V4-13 first-introduction lineage and enforce predecessor identity

dcbfe610b5cb0a8d94dc743963a1fa80f7f71f32
Seal R15R1 lineage cleanup clean detached evidence
```

最终 HEAD 相对 clean tested source 只新增/更新：

```text
reports/v4_13_r15r1/CLEAN_DETACHED_GATE.json
reports/v4_13_r15r1/CLEAN_TEST_RESULTS.xml
reports/v4_13_r15r1/FINAL_HANDOFF.json
reports/v4_13_r1_1/R15_FINAL_HANDOFF.json
```

没有测试后业务合同漂移。

GitHub 当前：

```text
commit statuses = []
workflow runs = []
```

因此本报告不声称 CI 背书。

# 3. G01｜PASS

两个 R15 首次引入合同已删除错误 `supersedes`：

```text
SECTOR_CONTEXT_STATE_V1
ROTATION_STRUCTURE_ENRICHMENT_V1
```

现在使用：

```text
introduced_in = V4_13_R1_1_CONTRACT_REPAIR
derived_from = exact source refs
```

## SECTOR_CONTEXT_STATE_V1

来源定义：

```text
config/v4_13_output_schema_v1.json
config/v4_13_field_registry_v1.json
```

## ROTATION_STRUCTURE_ENRICHMENT_V1

来源定义：

```text
config/v4_13_field_registry_v1.json
config/v4_13_dag_edge_registry_v1.json
```

这两个 contract family 现在被正确表示为：

```text
first introduction
```

而不是伪造为旧 registry/schema 的后续版本。

# 4. 同族 supersedes 保持正确

已有同 contract family 的 v1 -> v1.1 lineage 没有被误删：

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

仍然精确绑定同 contract_id 的旧 v1 predecessor。

# 5. G02｜PASS

`validate_lineage()` 已从“只验证文件/hash存在”升级为：

```text
first-introduced contract:
    supersedes MUST NOT EXIST
    introduced_in MUST EXIST
    derived_from MUST EXIST
    every derived_from ref exact

existing contract with supersedes:
    predecessor exact
    predecessor.contract_id == current.contract_id
    current.version > predecessor.version
```

因此不再允许：

```text
path/hash 正确
但 contract family 错误
```

的假 lineage。

# 6. 新 Lineage Negative Tests

新增测试实际覆盖：

```text
L01
SECTOR_CONTEXT_STATE_V1
supersedes V4_13_OUTPUT_SCHEMA_V1
→ REJECTED

L02
ROTATION_STRUCTURE_ENRICHMENT_V1
supersedes V4_13_FIELD_REGISTRY_V1
→ REJECTED

L03
same-family v1 -> v1.1
→ ACCEPTED

L04
first-introduced + introduced_in + derived_from
→ ACCEPTED

L05
exact predecessor ref but wrong contract_id
→ REJECTED

NON_INCREASING_VERSION
→ REJECTED

CORRUPT_HASH
→ REJECTED

MISSING_INTRODUCTION
→ REJECTED
```

# 7. Repair Script Determinism

`repair_v4_13_r1_1.py` 已加入：

```text
introduced_lineage()
```

baseline 重跑会稳定产生：

```text
no false supersedes
exact introduced_in
exact derived_from
```

测试包含重复生成相等性，不会再次重生 R15 的 lineage 错误。

# 8. Business Semantics｜EXACT KEEP

R15R1 validator 对所有 `v4_13_*_v1_1.json` 做 normalized comparison：

仅忽略：

```text
introduced_in
derived_from
definition_replaces
supersedes
以及由于被引用文件变化产生的 ref hash/bytes
```

其余业务语义必须与 R15 baseline 完全一致。

结果：

```text
C01_C04 = PASS_KEEP
```

因此本轮没有重新修改：

```text
Time Role
LOO selection
Membership Authority
Sector Context semantics
Rotation/Structure quality
DAG business edges
```

# 9. Protected Heads｜PASS

独立比较 R15R1 baseline 与当前 HEAD：

```text
data/v4/V4_12_ACCEPTED_HEAD.json = EXACT_SAME
data/v4/V4_STAGE_ACCEPTED_HEAD.json = EXACT_SAME
data/v4/V4_DATA_ACCEPTED_HEAD.json = EXACT_SAME
AGENTS.md = EXACT_SAME
```

继续：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_12_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

# 10. Scope / Tests

Clean detached gate：

```text
clean_before = true
clean_after = true

runtime_added = false
migration_added = false

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

Clean tests：

```text
54 total
54 PASS
0 FAIL
0 ERROR
0 SKIP
```

# 11. V4-13 Runtime 实现现已授权

R15R1 通过后，V4-13 Runtime 必须严格实现已经冻结的 R1.1 合同。

下一阶段允许：

```text
V4-13 scoped engineering runtime
accepted-source binders
LOO context calculation
Profile Advanced Projection
Context publication
synthetic + real capability-scoped replay
same-day revision handling
append-only candidate artifacts
```

但仍不允许：

```text
V4_13_ACCEPTED_HEAD
Stage Head -> V4_13
V4-14 Replay Gate B acceptance
Production
Shadow
Focus
Radar / Cohort / Settlement
formal DB migration
```

# 12. 下一步

进入：

```text
R16A
Accepted Input Binder + LOO Context Core Runtime

R16B
Advanced Profile Projection + Enrichment Runtime

R16C
Persisted Publication + E2E / Revision / Real Capability Replay
```

严格：

```text
R16A local gate
→ R16B local gate
→ R16C clean detached E2E
→ unified commit + push
→ STOP
→ independent external audit
```

R16 外审通过后，再进入：

```text
V4-13 Accepted Head Promotion
+
V4-14 Replay Gate B Stage Entry
```

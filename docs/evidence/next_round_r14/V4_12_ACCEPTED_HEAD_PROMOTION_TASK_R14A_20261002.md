# R14A｜V4-12 Scoped Engineering Accepted Head Promotion｜2026-10-02

**基线 HEAD：** `33b1949a1c05b0fe6c9068e6db9f219a9f11378b`  
**前置外审：** `V4_R13_EXTERNAL_AUDIT = PASS_SCOPED_ENGINEERING`

# 1. 唯一目标

将已经完成独立外部验收的 V4-12 `Structure / Anchor / Support` 以 `SCOPED ENGINEERING ACCEPTANCE` 正式写入 Accepted Head。

不得扩大为 Production / Shadow / Focus permission。

# 2. 创建

新增：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
```

建议：

```text
contract_id = V4_12_ACCEPTED_HEAD_V1
```

必须绑定 R8/R9/R10/R11/R12/R13 最终 contract/runtime/evidence/外审，不能只绑定 R13。

# 3. Capability Map

至少精确记录：

```text
MULTI_ANCHOR_SNAPSHOT_V2 = ENGINEERING_ACCEPTED
PER_ANCHOR_SUPPORT_ACCEPTANCE = ENGINEERING_ACCEPTED
PER_ANCHOR_PULLBACK_RECOVERY_RETENTION = ENGINEERING_ACCEPTED
ACTIVE_ANCHOR_SELECTOR = ENGINEERING_ACCEPTED
BREAKOUT_EPISODE_CONTINUITY = ENGINEERING_ACCEPTED
BREAKOUT_DUPLICATE_CREATION_GUARD = ENGINEERING_ACCEPTED
BREAKOUT_OWNER_ANCHOR_IMMUTABILITY = ENGINEERING_ACCEPTED
BREAKOUT_SAME_DAY_REVISION_PREDECESSOR = ENGINEERING_ACCEPTED
BREAKOUT_SECURITY_PROJECTION = ENGINEERING_ACCEPTED
BREAKOUT_TRANSITION_IDENTITY = ENGINEERING_ACCEPTED
ANCHOR_COORDINATE_REBASE = ENGINEERING_ACCEPTED_CAPABILITY_SCOPED
SOURCE_AUTHORITY_FAIL_CLOSED = ENGINEERING_ACCEPTED
TIME_COUNTER_SEMANTICS = ENGINEERING_ACCEPTED
REAL_TARGET_DATE_STRUCTURE_SIGNAL = DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY
HISTORICAL_AS_RECORDED_D1 = NOT_PROVEN
FULL_D0_D1_D2_REPLAY = NOT_YET_ACCEPTED_V4_14
V4_13_PROFILE_ADVANCED_PROJECTION = NOT_IMPLEMENTED
```

如 evidence 支持更精确命名可细化，但禁止扩大权限。

# 4. Knowledge / Evidence Scope

必须：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
```

不得声称 PIT_OBSERVED 或 historical AS_RECORDED proven。

# 5. Permissions

全部：

```text
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
global_mandatory_adoption = false
```

# 6. Stage Head Promotion

只有 V4_12_ACCEPTED_HEAD validator 全 PASS 后，才更新：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

从：

```text
V4_00_TO_V4_11_ACCEPTED
```

到：

```text
V4_00_TO_V4_12_ACCEPTED
```

只新增 V4-12 binding/status/capabilities/external acceptance，不改写 V4-00～V4-11 历史 accepted metadata。

# 7. Data Head

必须 byte-identical：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

仍：

```text
accepted_trade_date = 2026-09-30
```

# 8. Promotion Validator

至少验证：

```text
parent Stage Head exact
V4-11 Accepted Head exact
Data Head exact
R13 final remote/tested ancestry
R13 independent external acceptance exact
R11/R12/R13 retained evidence exact
capability map exact
permissions all false
AS_RECORDED false
real runtime degraded wording exact
no Production/Shadow/Focus
no V4-13 runtime
idempotent
clean detached replay
```

# 9. Idempotence

重复执行 promotion：

```text
0 mutations
```

# 10. 禁止

```text
修改 V4-12 Runtime
修改参数/AST
修改 R8-R13 evidence
推进 Data Head
实现 V4-13 Runtime
实现 V4-14
D2 replay acceptance
Production
Shadow
Focus
DB migration
```

# 11. 完成状态

只有：

```text
V4_12_ACCEPTED_HEAD_PROMOTION = PASS_SCOPED_ENGINEERING
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
```

然后进入 R14B。

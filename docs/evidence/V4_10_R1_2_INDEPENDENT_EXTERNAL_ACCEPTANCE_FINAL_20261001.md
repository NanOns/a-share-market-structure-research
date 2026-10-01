# V4-10 R1.2 独立外部最终验收｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 sealed HEAD：** `f0c6eb57f7c0c8fc2d0d6875d73295e349e7d315`  
**被测实现提交：** `6a339e71d38ced6e97c077fddef8dc7a8dfbd104`  
**上一外部阻塞基线：** `db6319856468c6788c9dd656da3992e569a64572`

## 唯一总状态

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE
```

并维持：

```text
V4_09 = KEEP_ACCEPTED
V4_10_PRODUCTION_PERMISSION = FALSE
V4_10_SHADOW_PRODUCTION_PERMISSION = FALSE
V4_10_FOCUS_CUTOVER_PERMISSION = FALSE
```

本验收只接受 V4-10 `RESEARCH_STATE_V1` 的 **State Reducer engineering interface + authority/lineage/persistence contract**。

不代表完整 D0/D1/D2 DAG、V4-11/V4-12、V4-14 Replay Gate B 或任何 Production/Shadow/Focus 权限已经通过。

## 1. R1.1 两个 P0 已真实闭合

### Real Model Boundary

R1.2 新增：

```text
v4.research_state_boundary_prior_publications
V4_10_BOUNDARY_PRIOR_LEDGER_R1_2
```

并实现 old-source immutable authority、source payload/content digest、source model/parameter/interface identity、boundary manifest 精确绑定、`from != to` no-op 拒绝、旧 episode follow-up 保留和 MODEL_BOUNDARY 非 REENTERED。

工程正例：

```text
OLD_RESEARCH_STATE_V0 / OLD_PARAMETER_SET_V0
→
RESEARCH_STATE_V1 / V4_10_STATE_REDUCER_PARAMETER_SET_V1
```

该 old source 是 frozen engineering golden，不是市场数据或真实历史模型接受声明；但足以证明 V4-10 engineering boundary interface。

### Implemented-field Status Authority

Accepted mode 下，policy `implemented=true` 的 owner 不再允许 caller 自行声明 `NOT_IMPLEMENTED`。

即使不可计算：

```text
status = IMPLEMENTED
value = UNKNOWN
quality = UNKNOWN
```

仍必须绑定正式 producer publication。

已覆盖：

```text
SEED
PREWATCH
core_price_damage
suspended
risk
delta3
dq5
```

并验证 trusted TRUE 不能被 relabel 成 NOT_IMPLEMENTED/UNKNOWN 或 IMPLEMENTED/UNKNOWN 来隐藏正式事实。

## 2. Controlled Publisher

migration 024 新增：

```text
v4_10_reducer_publisher_r1_2
v4_10_state_reader_r1_2
```

普通 reader/result writer 无法直接 INSERT：

```text
research_state_engineering_publications
research_state_engineering_results
```

正式 state publication 通过：

```text
publish_state()
→ reduce_state()
→ validate_output()
→ content-address
→ persist
```

DB 继续承担 payload/state identity、field provenance、calendar/prior/boundary lineage、append-only 和 revision guard。

## 3. Migration 024

确认：

```text
022 byte-identical
023 byte-identical
```

R1.2 使用：

```text
024_v4_10_research_state_authority_hardening.sql
```

验证旧 022/023 rows 可读、append-only/revision 保留、rollback before/after new rows 精确恢复 023 schema/roles/grants、old payload bytes 保留，且 publisher 不能自行注册 old-source authority 或 input manifests。

## 4. Independent Vectors

```text
vector_count = 180
mismatch_count = 0
```

保留原 98 个 semantic vectors 与 R1.1 的 149-vector 语义基础。

新增硬覆盖：

```text
real_model_boundary_transition
noop_model_boundary_rejected
implemented_field_status_authority
trusted_fact_cannot_be_suppressed
controlled_state_publisher_authority
semantic_forge_direct_sql_blocked_by_permission
```

全部 PASS。

## 5. Clean Detached Regression

被测提交：

```text
6a339e71d38ced6e97c077fddef8dc7a8dfbd104
```

结果：

```text
1116 passed
2 skipped
0 failed
0 errors
1 existing authorized historical deselect
```

无新增 deselect。`config/.env` absent/not read，使用 disposable PostgreSQL，未使用 production/configured DB。

## 6. Head Discipline

截至 sealed HEAD：

```text
data/v4/V4_10_ACCEPTED_HEAD.json = ABSENT
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_09_ACCEPTED
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-24
```

V4-09 Accepted Head SHA 继续为：

```text
641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d
```

没有提前 promotion。

## 7. G01–G22 独立裁决

| Gate | 外部裁决 |
|---|---|
| G01 V4-09 unchanged | PASS |
| G02 Prior content identity | PASS |
| G03 Calendar lineage | PASS |
| G04 Input manifest shape | PASS |
| G05 Real OLD→CURRENT boundary | PASS |
| G06 No-op boundary rejected | PASS |
| G07 Implemented field status authority | PASS |
| G08 Implemented UNKNOWN binds publication | PASS |
| G09 Trusted TRUE cannot be suppressed | PASS |
| G10 NOT_IMPLEMENTED limited to missing owner | PASS |
| G11 NOT_APPLICABLE scope limited | PASS |
| G12 Ordinary direct insert denied | PASS |
| G13 Controlled publisher positive path | PASS |
| G14 DB identity / lineage | PASS |
| G15 022 / 023 unchanged | PASS |
| G16 024 exact rollback | PASS |
| G17 Original 149 expectations retained | PASS |
| G18 New negative vectors | PASS |
| G19 Clean detached regression | PASS |
| G20 No new deselect | PASS |
| G21 Production/shadow/Focus false | PASS |
| G22 V4-10 Accepted Head absent before external acceptance | PASS |
| NO_SYMBOL | PASS |

## 8. 跨阶段 remediation 本轮状态

`e368f8705049d74c5b66777e3270786decb895bc` 完成的是 Master Governance Entry，不是 capability repair。

确认：

```text
A01-A09 全部进入正式 registry
A01/A08/A09 = IMPLEMENTATION_ENTRY_AUTHORIZED
其余 = QUEUED_FORMAL_WORK_PACKAGE
all_capabilities_remain_unaccepted = true
```

因此：

```text
CROSS_STAGE_REMEDIATION_MASTER_ENTRY = PASS
A01-A09_CAPABILITY_REPAIR = NOT_YET_ACCEPTED
```

下一步应实际进入 `WP-A01-DM01`。

## 9. 最终状态

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE
V4_10_ACCEPTED_HEAD_PROMOTION = AUTHORIZED
V4_11_ENTRY = AUTHORIZED_ONLY_AFTER_V4_10_PROMOTION_VALIDATION_PASS

CROSS_STAGE_REMEDIATION_MASTER_ENTRY = PASS
WP_A01_DM01_IMPLEMENTATION = AUTHORIZED_TO_START

PRODUCTION_PERMISSION = FALSE
SHADOW_PRODUCTION_PERMISSION = FALSE
FOCUS_CUTOVER_PERMISSION = FALSE
```

完整算法链仍必须经过 V4-11、V4-12、V4-13、V4-14 后才能声称完整 D0/D1/D2 算法链通过。

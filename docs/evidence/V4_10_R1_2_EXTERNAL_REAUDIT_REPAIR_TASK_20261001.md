# V4-10 R1.2 独立外部复审修复任务卡｜2026-10-01

**文档编号：** DA-MSR-V4-10-R1.2-EXTERNAL-REAUDIT-REPAIR-20261001  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**本轮审计远端 HEAD：** `db6319856468c6788c9dd656da3992e569a64572`  
**R1.1 被测实现提交：** `6049973cd78e51cdeb2ba33461f20ce96b13c8d6`  
**上一轮基线：** `14db3ef521d34b366bf5a22bad2a3564838ce8bf`  
**V4-09 Accepted Head：** 继续 KEEP_ACCEPTED / NO_REOPEN  
**V4-10 当前裁决：** `V4_10_EXTERNAL_ACCEPTANCE_BLOCKED_R1_2`  
**V4-11 入场：** `BLOCKED`

---

# 0. 本轮总评

R1.1 不是无效修复。

上一轮 B01–B06 中的大部分问题已经得到真实处理：

- prior 已改为完整 output schema + content-address identity；
- accepted prior 已要求从 PostgreSQL engineering publication 读取；
- input_publication_ids 已有严格 array / unique / exact membership；
- model_boundary 已从裸 boolean 改为 manifest；
- state-changing fields 已增加统一 provenance envelope；
- migration 023 没有覆盖 migration 022；
- DB 已增加 payload digest / state publication id / calendar / field lineage / direct SQL guard；
- 149 个静态向量覆盖原 98 个业务语义向量；
- clean detached regression 为 `1090 passed / 2 skipped / 0 failed`；
- production / shadow / Focus permission 仍为 false；
- V4-10 Accepted Head 仍不存在；
- V4-09 Accepted Head 未被污染。

因此不回滚 R1.1。

但本轮独立复审发现两个新的**实质阻塞问题**和一个**可信 prior publication 加固问题**。它们都集中在“interface authority 是否真的成立”，不是业务算法本身。

---

# 1. 当前裁决

```text
V4_09_ACCEPTED_HEAD                            = KEEP_ACCEPTED
V4_10_R1_1_REDUCER_CORE_SEMANTICS             = PASS_WITH_REPAIR
V4_10_R1_1_PRIOR_CONTENT_ADDRESS              = PASS
V4_10_R1_1_CALENDAR_LINEAGE                   = PASS
V4_10_R1_1_INPUT_MANIFEST_SHAPE               = PASS
V4_10_R1_1_DB_IDENTITY_GUARD                  = PASS_WITH_HARDENING
V4_10_R1_1_MODEL_BOUNDARY_REAL_MIGRATION      = FAIL
V4_10_R1_1_IMPLEMENTED_FIELD_STATUS_AUTHORITY = FAIL
V4_10_R1_1_PRIOR_PUBLICATION_SEMANTIC_AUTHORITY = INSUFFICIENT
V4_10_EXTERNAL_ACCEPTANCE                     = BLOCKED_R1_2
V4_11_ENTRY                                   = BLOCKED
```

---

# 2. 已确认通过项｜不要返工

## 2.1 Prior payload 完整性

`src/v4/state_provenance.py::validate_output()` 已要求：

- full output required fields；
- axis domain；
- calendar binding；
- input manifest digest；
- content-address state publication id；
- interface/canonicalization identity；
- stale eligibility constraints。

这一方向正确。

## 2.2 Accepted prior ledger readback

`PostgresEngineeringLedger.prior()` 已经不是信任 caller 自报 dict，而是从：

```text
v4.research_state_engineering_results
+
v4.research_state_engineering_publications
```

进行 publication / payload / digest / model / parameter readback。

保留。

## 2.3 Input publication manifest shape

目前已经拒绝：

- string 代替 list；
- empty；
- empty id；
- duplicate；
- nested；
- non-string；
- substring membership。

保留。

## 2.4 Migration 023

023 正确采用新 migration，而没有修改历史 022。

保留这一版本治理原则。

## 2.5 DB content identity

目前已实现：

```text
payload_digest == canonical(payload)
state_publication_id == V4_10:<canonical payload without publication_id>
```

并且有 direct SQL negative probes。

保留。

---

# 3. B01｜P0｜Model Boundary 正例实际上是“同模型 → 同模型”的 no-op boundary

这是本轮最明确的阻塞项。

## 3.1 问题事实

migration 022 中：

```sql
v4.research_state_engineering_publications.model_contract_id
CHECK (model_contract_id='RESEARCH_STATE_V1')

v4.research_state_engineering_publications.parameter_set_id
CHECK (parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1')
```

同时 022 trigger 强制：

```text
result.model_contract_id
==
publication.model_contract_id

result.parameter_set_id
==
publication.parameter_set_id
```

因此：

> 当前 `PostgresEngineeringLedger.prior()` 能读取到的合法 prior，事实上只能是当前 `RESEARCH_STATE_V1 + current parameter set`。

但是 R1.1 的 positive boundary fixture：

```text
accepted_prior_fixture()
```

同样使用当前：

```text
RESEARCH_STATE_V1
V4_10_STATE_REDUCER_PARAMETER_SET_V1
```

于是：

```text
from_model == to_model
from_parameter == to_parameter
```

仍被作为：

```text
AUTHORIZED MODEL_BOUNDARY
```

通过。

这不是一个真正的模型边界迁移。

## 3.2 为什么这是实质问题

当前代码表面上存在：

```text
from_model_contract_id
from_parameter_set_id
to_model_contract_id
to_parameter_set_id
migration_manifest
effective_trade_date
```

但真正的旧模型 / 旧参数 prior 根本无法进入当前 prior ledger。

也就是说：

```text
G05_model_boundary_authorized_manifest = PASS
```

目前只能证明：

> 可以给“当前模型到当前模型”的 no-op boundary 发一张授权 manifest。

不能证明：

> 可以从真实旧模型 / 旧参数状态迁移到当前模型。

这不满足 Model Boundary 的实际语义。

---

# 4. B01 修复要求｜建立真正的 boundary prior authority

禁止修改历史 migration 022。

必须通过新的版本化机制允许：

```text
OLD MODEL / OLD PARAMETER PRIOR
        ↓
AUTHORIZED MODEL BOUNDARY
        ↓
RESEARCH_STATE_V1 current model
```

推荐二选一。

## 方案 A｜独立 Boundary Prior Ledger

新增例如：

```text
v4.research_state_boundary_prior_publications
```

至少保存：

```text
source_publication_id
source_payload
source_payload_digest
source_model_contract_id
source_parameter_set_id
source_interface_contract_id
source_trade_date
source_session_index
source_entity_id
source_entity_type
source_episode_id
source_authority
source_authority_digest
```

并由 boundary manifest 精确绑定。

## 方案 B｜通用 immutable prior adapter

如果未来 V4-18 会统一迁移，可实现一个通用只读 adapter：

```text
OLD_STATE_SOURCE
→ canonical boundary-prior envelope
→ boundary manifest
→ V4-10 reducer
```

但是：

```text
adapter 不得把 old model 伪装成 current model
```

必须保留真实：

```text
from_model
from_parameter
source publication
source digest
```

---

# 5. B01 新强制规则

## 5.1 禁止 no-op model boundary

以下必须拒绝：

```text
from_model_contract_id == to_model_contract_id
AND
from_parameter_set_id == to_parameter_set_id
```

除非总合同未来明确新增另一种非模型迁移 boundary 类型。

当前 `MODEL_BOUNDARY` 不允许把“无变化”当边界。

建议错误码：

```text
MODEL_BOUNDARY_NOOP_FORBIDDEN
```

## 5.2 Positive case 必须是真迁移

至少新增一条真正正例：

```text
OLD_RESEARCH_STATE_V0
OLD_PARAMETER_SET_V0
→
RESEARCH_STATE_V1
V4_10_STATE_REDUCER_PARAMETER_SET_V1
```

名称只是 fixture 示例，不要求真实历史模型叫这个名字。

重点是：

```text
from != to
```

且 prior 必须来自独立 immutable authority，不得由 test caller 临时改字段后自签 digest。

---

# 6. B01 必测向量

新增至少：

```text
test_noop_model_boundary_rejected
test_real_old_model_prior_can_enter_only_with_authorized_boundary
test_old_model_prior_without_boundary_rejected
test_boundary_from_model_must_equal_real_old_prior
test_boundary_from_parameter_must_equal_real_old_prior
test_boundary_to_model_must_equal_current_reducer
test_boundary_source_publication_missing_rejected
test_boundary_source_payload_digest_mismatch_rejected
test_boundary_effective_date_mismatch_rejected
test_real_boundary_preserves_old_episode_followup
test_real_boundary_does_not_emit_REENTERED
test_real_boundary_new_episode_identity_not_collide_with_old_episode
```

---

# 7. B02｜P0｜`implemented=true` 字段仍可被 caller 自行降级成 `NOT_IMPLEMENTED`

这是第二个阻塞项。

## 7.1 当前代码行为

在：

```text
src/v4/state_provenance.py
```

当：

```text
status in ('NOT_IMPLEMENTED','NOT_APPLICABLE')
```

时，代码主要检查：

```text
value == UNKNOWN
quality == UNKNOWN
publication_id == null
source_output_digest == null
producer ids 与 policy 一致
```

并存在：

```python
if definition['implemented'] and status=='NOT_IMPLEMENTED':
    pass
```

也就是说，policy 中明确：

```text
implemented = true
```

的字段，accepted caller 仍能传：

```text
status = NOT_IMPLEMENTED
value = UNKNOWN
```

并通过 Python gate。

migration 023 的 DB trigger 也存在同样语义：

```text
NOT_IMPLEMENTED
```

分支不会要求：

```text
policy.implemented == false
```

## 7.2 为什么这会破坏 provenance authority

以下字段当前 policy 已经明确是 implemented：

```text
SEED
PREWATCH
core_price_damage
risk
delta3
dq5
suspended
```

但 caller 可以将它们改成：

```text
NOT_IMPLEMENTED / UNKNOWN
```

从而绕开已有 trusted fact publication。

例如：

```text
trusted publication:
core_price_damage = TRUE
```

caller 仍可构造：

```text
core_price_damage.status = NOT_IMPLEMENTED
core_price_damage.value  = UNKNOWN
publication_id = null
```

当前 gate 不会去检查 trusted manifest 中其实已经存在：

```text
core_price_damage = TRUE
```

Reducer 就会从：

```text
HARD INVALIDATION
```

退化为：

```text
REQUIRED FACT UNKNOWN
STALE
```

这不是 UNKNOWN→FALSE，但仍允许调用方**隐藏一个已经存在的正式事实**。

这与“字段 producer authority 不由 caller 决定”的目标冲突。

---

# 8. B02 修复规则

Accepted mode 下：

## 8.1 Policy implemented=true

只能接受：

```text
status = IMPLEMENTED
```

如果 producer 正常运行但结果无法计算：

```text
status 仍然 = IMPLEMENTED
value = UNKNOWN
quality = UNKNOWN
publication_id = 正式 producer publication
source_output_digest = 正式 UNKNOWN 输出 digest
```

也就是说：

> “算法能力已经实现，但今天算不出”不是 `NOT_IMPLEMENTED`。

例如 prior-RPS bootstrap 不足：

```text
delta3.status = IMPLEMENTED
delta3.value  = UNKNOWN
```

而不是：

```text
delta3.status = NOT_IMPLEMENTED
```

## 8.2 Policy implemented=false

才允许：

```text
NOT_IMPLEMENTED
```

例如当前：

```text
CONFIRMED
frozen_invalidation
episode_invalidation_contract_id
scenario
followup_complete
```

直到其 owner stage 正式交付。

## 8.3 NOT_APPLICABLE

继续只允许合同明确定义的对象：

- Stock WARM；
- Stock/sector 非本实体 metric；
- 无 episode 时的 episode invalidation fields；
- 未来合同明确登记的其他 N/A。

不得作为“缺数据”的通用逃生口。

---

# 9. B02 Python + DB 两层都必须修

同时修：

```text
src/v4/state_provenance.py
```

和新 migration，例如：

```text
024_v4_10_research_state_authority_hardening.sql
```

不得修改 023 历史文件。

DB 必须独立拒绝：

```text
policy.implemented = true
AND
status = NOT_IMPLEMENTED
```

建议错误码：

```text
STATE_IMPLEMENTED_FIELD_CANNOT_BE_NOT_IMPLEMENTED
```

---

# 10. B02 必测反例

每个 implemented owner 至少抽样覆盖：

```text
test_prewatch_cannot_be_downgraded_to_not_implemented
test_seed_cannot_be_downgraded_to_not_implemented
test_core_price_damage_cannot_be_downgraded_to_not_implemented
test_suspended_cannot_be_downgraded_to_not_implemented
test_risk_cannot_be_downgraded_to_not_implemented
test_delta3_implemented_unknown_with_publication_pass
test_dq5_implemented_unknown_with_publication_pass
```

重点必须包含：

```text
trusted publication 中为 TRUE
caller envelope 改成 NOT_IMPLEMENTED/UNKNOWN
```

→ 必须拒绝。

还需要 direct SQL 对应反例。

---

# 11. B03｜P1｜Prior “在 ledger 中存在”仍不等于“确实由 reducer 产生”

R1.1 已经解决：

```text
caller 自己伪造 prior dict
```

这一层问题。

但是又出现下一层 authority 边界：

schema receipt 明确创建了：

```text
ordinary result writer
```

并授予：

```text
INSERT ON
research_state_engineering_publications
research_state_engineering_results
```

只禁止它注册：

```text
research_state_input_manifests
```

当前 DB trigger 会检查：

- content digest；
- state id；
- field provenance；
- calendar；
- boundary；
- prior binding。

但是不会在数据库里完整重新执行 Python State Reducer 状态机。

因此一个拥有 result-writer 权限的进程，只要使用已有合法 input manifests，理论上仍可直接构造一个：

```text
digest 正确
provenance 正确
但 maturity / validity / tracking / transition_reasons 等 reducer 语义错误
```

的 state row。

该 row 一旦进入 engineering publication：

```text
PostgresEngineeringLedger.prior()
```

以后会把它当成 trusted prior。

---

# 12. B03 修复方向

不要求在 PostgreSQL 中重写完整 Python reducer。

建议采用**受控 publication writer**。

至少做到：

```text
普通应用 / result writer
不能直接 INSERT R1.1 state publication/results
```

允许写入的只能是：

```text
受控 reducer publisher role
或
SECURITY DEFINER publication function
```

该 writer 必须在写入前完成：

```text
reduce_state()
validate_output()
content address
input authority
```

然后数据库负责第二层 identity / lineage defense。

即：

```text
Reducer semantics = controlled producer responsibility
DB               = immutable identity + lineage guard
```

不能让“trusted prior”建立在任何 ordinary result writer 都能直接写 state table 的前提上。

---

# 13. B03 最低验收

新增数据库角色测试：

```text
ordinary_result_writer:
    SELECT = allowed
    direct INSERT research_state_engineering_publications = rejected
    direct INSERT research_state_engineering_results      = rejected

authorized_reducer_publisher:
    publish via controlled path = pass
```

如果选择 SECURITY DEFINER function：

```text
ordinary writer 只能 EXECUTE function
不能直接 INSERT base tables
```

并测试：

```text
semantically forged state via direct SQL rejected by permission
```

而不是只测试 payload digest 错误。

---

# 14. 本轮不要扩大范围

不修：

```text
V4-07 prior RPS bootstrap
Amount A
DM01
Legacy valid member
Forward PIT history
BaoStock strict binding
V4-11 detector
V4-12 anchor/support
```

这些仍按原 audit register 独立推进。

---

# 15. Migration 版本治理

已有：

```text
022
023
```

均保留 byte-identical。

新 DB 修复使用：

```text
024_v4_10_research_state_authority_hardening.sql
rollback/024_v4_10_research_state_authority_hardening.sql
```

如果 024 已被其他工作占用，则顺延。

---

# 16. 新增 hard-required coverage tags

在 independent verifier 中新增硬编码：

```text
real_model_boundary_transition
noop_model_boundary_rejected
implemented_field_status_authority
trusted_fact_cannot_be_suppressed
controlled_state_publisher_authority
semantic_forge_direct_sql_blocked_by_permission
```

不得只在 vector 自己写 tag。

---

# 17. R1.2 Acceptance Gate

下一轮至少全部满足：

```text
G01 V4-09 Accepted Head unchanged                         PASS
G02 Existing R1.1 prior content-address checks           PASS
G03 Existing calendar lineage checks                     PASS
G04 Existing input manifest shape checks                 PASS
G05 Real OLD→CURRENT model boundary                      PASS
G06 No-op model boundary rejected                        PASS
G07 Implemented field cannot claim NOT_IMPLEMENTED       PASS
G08 Implemented UNKNOWN must retain owner publication    PASS
G09 Trusted TRUE fact cannot be suppressed to UNKNOWN    PASS
G10 NOT_IMPLEMENTED only for policy implemented=false    PASS
G11 NOT_APPLICABLE remains scope-limited                 PASS
G12 Ordinary result writer direct state INSERT rejected  PASS
G13 Authorized reducer publisher positive path           PASS
G14 DB content-address / lineage guards still PASS       PASS
G15 022 / 023 remain byte-identical                      PASS
G16 New migration rollback exact                         PASS
G17 Original 149 vectors remain PASS                     PASS
G18 New negative vectors PASS                            PASS
G19 Clean detached regression                            PASS
G20 No new deselect                                      PASS
G21 production/shadow/Focus permissions remain false     PASS
G22 V4-10 Accepted Head remains absent                   PASS
```

---

# 18. 修复后只允许声明

```text
V4_10_R1_2_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行：

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS
V4_10_ACCEPTED_HEAD
V4_11_AUTHORIZED
```

---

# 19. 本轮结论

R1.1 已经把上一轮多数“自洽伪造”问题真正修掉，所以不回滚。

但目前仍不能给 V4-10 外部通过，原因不是测试数量不足，而是两个 authority 语义仍不成立：

1. `MODEL_BOUNDARY` 只能做 current→current 的 no-op，真实 old→current prior 无法进入当前 ledger；
2. policy 已标记 `implemented=true` 的正式字段仍可由 caller 自行降级成 `NOT_IMPLEMENTED/UNKNOWN`，从而隐藏 trusted publication 中已经存在的事实。

另外，既然 future prior 要被称为 trusted engineering publication，就应收紧 state result table 的写权限，避免普通 result writer 绕过 reducer 语义直接构造“合法 digest、错误状态”的 prior。

最终裁决：

```text
V4_09 = KEEP_ACCEPTED
V4_10_R1_1 = REPAIR_NOT_ACCEPTED
V4_10_EXTERNAL_ACCEPTANCE = BLOCKED_R1_2
V4_11_ENTRY = BLOCKED
```

# V4-10 R1 独立外部审计修复任务卡｜2026-10-01

**文档编号：** DA-MSR-V4-10-R1-EXTERNAL-AUDIT-REPAIR-TASK-20261001  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计远端 HEAD：** `14db3ef521d34b366bf5a22bad2a3564838ce8bf`  
**V4-10 被测实现提交：** `e3b29a434c57a94cc5fe68edc3de647862da4ec4`  
**V4-09 Accepted Head 封存提交：** `ba6e15ce9ddbc260cbc2131bcdda30da9a9fb381`  
**最高设计权威：** `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`  
**适用章节：** §13A、§30、§31、§32、§33、§34A.2A、§78、§80、§87A  
**当前外部审计结论：** `V4_10_EXTERNAL_ACCEPTANCE_BLOCKED_R1`  
**V4-09 结论：** `KEEP_ACCEPTED / NO_REOPEN`  
**V4-11 入场：** `BLOCKED_UNTIL_V4_10_R1_REPAIR_EXTERNAL_REAUDIT_PASS`

---

# 0. 任务目的

本任务不是重新实现 State Reducer，也不是修改 V4-09 PREWATCH / PRIORITY 算法。

本轮目标只有一个：

> 修复 V4-10 `RESEARCH_STATE_V1` engineering interface 中的 lineage、producer provenance、model-boundary authorization、输入结构与持久化防伪缺口，使 V4-10 真正达到“可被 V4-11 / V4-12 后续 detector 安全接入”的工程接口标准。

当前 reducer 的主体状态机语义、优先级、hysteresis、expiry、reentry、UNKNOWN 基本骨架可保留。

禁止为了修复 lineage 问题修改以下正式业务阈值：

- `downgrade_sessions = 2`
- `expiry_sessions = 10`
- `expiry_improvement_pp = 3`
- `health_deadband_pp = 3`

禁止重新设计 V4-07、V4-08、V4-09 算法。

---

# 1. 审计基线与已确认通过项

## 1.1 V4-09 Accepted Head 未被后续污染

从：

```text
ba6e15ce9ddbc260cbc2131bcdda30da9a9fb381
```

到当前：

```text
14db3ef521d34b366bf5a22bad2a3564838ce8bf
```

仅新增 V4-10 相关实现、配置、测试、migration、report/evidence。

没有修改：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
src/v4/stock_prewatch.py
V4-09 machine AST
V4-09 parameter set
V4-09 accepted artifacts
```

因此：

```text
V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

继续有效，不允许借本任务重开 V4-09。

---

## 1.2 V4-10 当前已有正面结果

以下结果本轮保留：

### A. Stage Scope 正确

当前没有越权声称：

```text
V4_10_FULL_STATE_REDUCER_ACCEPTED
```

仓库明确保持：

```text
External acceptance = PENDING_INDEPENDENT_EXTERNAL_REAUDIT
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
```

### B. 主状态机骨架方向正确

已实现并有静态向量覆盖：

- Hard invalidation 优先
- Required UNKNOWN 保留 last-known state
- `PREWATCH > SEED`
- `CONFIRMED > PREWATCH`
- 升级立即生效
- 下降需要连续两个可评估 market sessions
- UNKNOWN / suspension 打断 downgrade 连续计数
- EXTREME → EXHAUSTED
- ±3pp health deadband
- expiry 10 sessions
- improvement baseline 3pp
- same-session revision 不推进计数
- reentry 次一市场会话以后才允许
- old follow-up episode 保留
- MODEL_BOUNDARY 不标记为 REENTERED
- Stock WARM = NOT_APPLICABLE

### C. 当前测试证据存在

被测 implementation commit：

```text
e3b29a434c57a94cc5fe68edc3de647862da4ec4
```

clean detached regression：

```text
1021 passed
2 skipped
1 authorized historical test deselected
0 failed
0 errors
```

### D. 当前 98 个 machine vectors 的 expected values 为静态声明

不是直接调用 reducer 生成 expected output。

### E. Migration 022 使用独立 engineering sidecar

没有移动 production head，也没有修改旧 migration 021。

### F. No-symbol-specific runtime gate PASS

这些项目不需要返工，只需在修复后重新回归。

---

# 2. 外部审计总裁决

当前不能接受：

```text
V4_10_REDUCER_INTERFACE_ENGINEERING_ACCEPTED
```

正式状态：

```text
V4_09_ACCEPTED_HEAD                     = KEEP PASS
V4_10_STATE_MACHINE_CORE_SEMANTICS      = PASS_WITH_REPAIR
V4_10_PRIOR_STATE_LINEAGE               = FAIL
V4_10_MODEL_BOUNDARY_AUTHORIZATION      = FAIL
V4_10_STATE_CHANGING_FACT_PROVENANCE    = FAIL
V4_10_INPUT_PUBLICATION_MANIFEST_SHAPE  = FAIL
V4_10_DB_PAYLOAD_IDENTITY_HARDENING     = INSUFFICIENT
V4_10_NEGATIVE_VECTOR_COVERAGE          = INSUFFICIENT
V4_10_EXTERNAL_ACCEPTANCE               = BLOCKED_R1
V4_11_ENTRY                             = BLOCKED
```

---

# 3. B01｜P0｜Prior State 真实性与完整 lineage 未闭环

## 3.1 当前问题

当前：

```python
prior = x['prior_state']
```

只要调用方自己构造一个 dict，并同时构造：

```text
prior_state_binding.publication_id
prior_state_binding.payload_digest
```

使其与该 dict 自洽，就可以进入 reducer。

当前校验只覆盖部分字段：

- `publication_id`
- payload digest
- entity_id
- entity_type
- session_index
- model_contract_id
- parameter_set_id
- 少量 axis

但**没有证明 prior 本身是一个合法、完整的 `RESEARCH_STATE_V1` output publication**。

现有 synthetic helper `prior()` 就能说明这一点：

它使用：

```text
publication_id = FIXTURE_PRIOR
```

并且 prior payload 缺少正式 output schema 中多项字段，例如：

- `trade_date`
- `calendar_publication_id`
- `mode`
- `input_publication_ids`
- `input_digest`
- `raw_qualification`
- `detector_statuses`
- `matched_predicates`
- `unknown_predicates`
- `transition_reasons`
- `boundary_event`
- 等

仍可被 reducer 接受。

这意味着：

> 当前的 `payload_digest` 只证明“这个伪造 dict 没在传输中变化”，不能证明“它是合法 reducer 产生并发布过的 previous state”。

---

## 3.2 修复要求

必须新增严格 prior-state authenticity gate。

`ACCEPTED_FACT_INTERFACE` 下的 prior 至少必须满足：

### A. Full Output Schema Validation

prior 必须包含当前正式 prior schema 要求的全部字段。

不得再接受“只含 reducer 恰好读取字段”的 partial prior。

### B. Content-Addressed State Identity

如果当前 state publication identity 规则为：

```text
V4_10:<sha256(payload_without_publication_id)>
```

则 accepted-mode prior 必须独立重新计算并验证：

```text
prior.publication_id
==
V4_10:<recomputed digest>
```

Synthetic fixture 可以有明确 synthetic namespace，但必须与 accepted mode 严格隔离。

### C. Publication Existence / Manifest Binding

Accepted-mode prior 不得只靠调用者自报。

至少需要绑定：

```text
prior engineering publication id
publication manifest / accepted engineering ledger identity
row payload digest
consumer/model/parameter identity
```

当前阶段可以只绑定 V4-10 engineering publication，不要求 production head。

### D. Calendar Binding

prior 必须保存并验证：

```text
calendar_publication_id
trade_date
session_index
```

必须证明：

```text
same-session revision:
    prior.trade_date == current.trade_date
    prior.session_index == current.session_index

prior-session transition:
    prior.session_index < current.session_index
    且两者属于兼容/同一冻结 market-calendar lineage
```

不能只检查：

```python
prior.session_index <= current.session_index
```

### E. Entity / Episode / Contract Identity

继续保留并强化：

```text
entity_id
entity_type
episode_id
model_contract_id
parameter_set_id
```

---

## 3.3 必测反例

至少新增：

```text
test_partial_prior_payload_rejected_in_accepted_mode
test_self_consistent_fake_prior_digest_rejected
test_prior_content_address_publication_id_mismatch_rejected
test_prior_missing_calendar_publication_rejected
test_prior_calendar_identity_mismatch_rejected
test_prior_trade_date_session_index_inconsistent_rejected
test_same_day_revision_exact_session_binding_pass
test_prior_session_transition_bound_calendar_pass
test_synthetic_prior_cannot_enter_accepted_mode
```

---

# 4. B02｜P0｜MODEL_BOUNDARY 当前是裸 boolean，可被任意调用方触发

## 4.1 当前问题

当前接口：

```text
model_boundary: bool
```

代码逻辑：

```python
if boundary:
    prior = None
```

也就是说，只要调用方传：

```text
model_boundary = true
```

就可以：

- 丢弃旧 prior 作为当前 reducer 输入；
- 生成 boundary_event；
- 后续重新 ENROLLED 新 episode。

但当前没有要求任何：

```text
migration manifest
boundary contract id
from_model
to_model
effective_trade_date
boundary publication id
manifest digest
authorization
```

这与总合同要求的：

```text
D2 使用“合规迁移 manifest”
```

不一致。

`MODEL_BOUNDARY` 是会改变 episode lineage 的强控制输入，不能是无 provenance 的裸 boolean。

---

## 4.2 修复要求

将 model boundary 改成结构化、可验证输入。

推荐最少结构：

```json
{
  "status": "NONE | AUTHORIZED",
  "boundary_contract_id": "...",
  "migration_manifest_id": "...",
  "migration_manifest_sha256": "...",
  "from_model_contract_id": "...",
  "from_parameter_set_id": "...",
  "to_model_contract_id": "RESEARCH_STATE_V1",
  "to_parameter_set_id": "V4_10_STATE_REDUCER_PARAMETER_SET_V1",
  "effective_trade_date": "...",
  "publication_id": "..."
}
```

具体字段名可以调整，但语义不得减少。

Accepted mode：

```text
AUTHORIZED
```

必须绑定实际存在且 hash 校验通过的 migration/boundary manifest。

否则：

```text
MODEL_BOUNDARY_UNAUTHORIZED
```

fail closed。

Synthetic vector 可使用明确：

```text
SYNTHETIC_MODEL_BOUNDARY_FIXTURE
```

不得进入 accepted mode。

---

## 4.3 必测反例

```text
test_bare_true_model_boundary_rejected
test_boundary_missing_manifest_rejected
test_boundary_wrong_from_model_rejected
test_boundary_wrong_to_model_rejected
test_boundary_wrong_effective_date_rejected
test_boundary_manifest_digest_mismatch_rejected
test_authorized_boundary_pass
test_authorized_boundary_not_marked_reentered
test_boundary_preserves_old_followup_episode_reference
```

---

# 5. B03｜P0｜只有 SEED/PREWATCH detector 做了 producer gate，其余状态改变输入缺 provenance

这是本轮最重要的横向问题之一。

## 5.1 当前已正确做 lineage 的字段

目前：

```text
SEED
PREWATCH
```

有：

```text
contract_id
parameter_set_id
publication_id
input_publication_ids binding
```

这一方向正确。

---

## 5.2 当前仍为裸值或弱结构的状态改变输入

以下输入都会改变 reducer 结果，但当前没有等价 producer/time/provenance 校验：

```text
core_price_damage
frozen_invalidation
episode_invalidation_contract_id
risk
delta3
dq5
scenario
suspended
followup_complete
model_boundary（B02单独修）
calendar/session mapping
```

其中尤其严重的是：

### A. core_price_damage

可直接触发：

```text
maturity = NONE
health = DAMAGED
validity = INVALIDATED
final_eligibility = FALSE
tracking = FOLLOWUP
```

但当前只是：

```text
TRUE/FALSE/UNKNOWN
```

无 source publication producer gate。

### B. frozen_invalidation

当前只有：

```text
value
episode_id
contract_id
```

虽然会核对 episode/contract，但没有：

```text
producer publication
parameter identity
source digest
detector status
time role
```

调用方可以伪造一个“contract_id 恰好相同”的 TRUE。

而总合同明确：

```text
frozen episode invalidation
= NOT_IMPLEMENTED_V4_12
```

因此 V4-10 accepted interface 不能提前允许一个无正式 producer 的 TRUE 进入 Hard Invalidation。

### C. followup_complete

当前是裸 bool。

但：

```text
所有冻结 outcome / follow-up 到期工作完成
```

属于后续 settlement/due planner 能力。

在正式 owner producer 没有交付前，不允许 caller 自报：

```text
followup_complete = true
```

然后关闭 tracking。

### D. risk / delta3 / dq5

这些输入影响：

- health
- expiry
- improvement baseline

必须绑定其正式 upstream producer / publication。

### E. scenario

KNOWN scenario 目前可以由 caller 自由输入合法 enum。

虽然 enum 合法，但没有 producer provenance。

这不足以成为正式 Research State axis。

### F. suspended

它直接暂停状态迁移与计数，必须绑定正式 Trading Status producer，而不是裸 bool。

---

## 5.3 修复原则

必须新增统一的：

```text
V4_10_STATE_INPUT_PROVENANCE_V1
```

或等价字段级 manifest。

每一个会影响 State Reducer 的字段至少登记：

```text
field
value
quality/status
producer_contract_id
producer_parameter_set_id（如适用）
publication_id
source/output digest
time_role = T | T-1 | MODEL_BOUNDARY
required/optional
```

禁止每个字段临时写一套不同的 provenance 规则。

---

## 5.4 NOT_IMPLEMENTED 行为

当前未交付 producer 必须显式：

```text
NOT_IMPLEMENTED
```

对应值不得伪装成 FALSE。

例如 V4-12 前：

```text
frozen_invalidation.status = NOT_IMPLEMENTED
value = UNKNOWN
```

在正式 D1 producer 接入前不能变 TRUE/FALSE。

`followup_complete` 在正式 owner stage 交付前同理。

---

## 5.5 必测反例

至少：

```text
test_unbound_core_price_damage_true_rejected_or_unknown
test_wrong_core_price_damage_producer_rejected
test_frozen_invalidation_true_without_v4_12_producer_rejected
test_frozen_invalidation_wrong_publication_rejected
test_invalidation_contract_matches_but_publication_unbound_rejected
test_unbound_risk_cannot_set_exhausted
test_unbound_delta3_cannot_move_health_or_expiry
test_unbound_dq5_cannot_move_sector_health_or_expiry
test_unbound_suspension_cannot_pause_state
test_unbound_scenario_cannot_be_known
test_followup_complete_true_before_owner_producer_rejected
test_not_implemented_fact_never_coerced_false
```

---

# 6. B04｜P0｜`input_publication_ids` 缺结构类型校验

## 6.1 当前问题

当前只检查：

```python
if not x['input_publication_ids']:
    ...
```

没有严格验证：

```text
必须是 list
元素必须是 non-empty string
不得重复
不得嵌套
不得为空字符串
不得把单个 string 当 collection
```

而 producer gate 使用：

```python
publication_id not in x['input_publication_ids']
```

如果 `input_publication_ids` 错误地传入 string，会退化成字符串包含判断，而不是 publication exact membership。

这是典型接口边界漏洞。

---

## 6.2 修复要求

Accepted 和 Synthetic 两种模式都必须校验 canonical shape：

```text
type = array
minItems >= 1
uniqueItems = true
item = non-empty stable publication id
```

进入 reducer 后转换成不可歧义 canonical representation。

推荐同时增加：

```text
input_publication_manifest_digest
```

对 field->publication 绑定做整体 hash。

---

## 6.3 必测反例

```text
test_input_publication_ids_string_rejected
test_input_publication_ids_empty_rejected
test_input_publication_ids_contains_empty_id_rejected
test_input_publication_ids_duplicate_rejected
test_input_publication_ids_nested_rejected
test_exact_publication_membership_no_substring_match
```

---

# 7. B05｜P1｜Migration 022 的 DB 防伪仍主要依赖 Python persistence helper

## 7.1 当前正面部分

Migration 022 已经做到：

- publication append-only
- result append-only
- UPDATE/DELETE trigger reject
- publication model/parameter identity gate
- 部分 payload column equality guard
- persistence helper exact readback
- revision_of FK

这些继续保留。

---

## 7.2 当前缺口

DB trigger 当前没有证明：

```text
payload_digest == sha256(payload canonical bytes)
```

也没有证明：

```text
state_publication_id
==
V4_10:<content digest>
```

因此绕过：

```text
src/v4/research_state_persistence.py
```

直接 SQL INSERT 时，仍可能构造：

```text
payload
payload_digest
state_publication_id
```

三者彼此不真实对应，但通过当前部分列一致性检查。

另外部分重要 lineage 字段只存在 payload 中，没有数据库侧独立约束。

---

## 7.3 修复方式

二选一，必须明确选择并形成正式边界：

### 方案 A｜DB 强校验

使用 PostgreSQL 可接受的 digest/trigger 方案，校验：

```text
payload canonical identity
state_publication_id
payload_digest
```

并补重要 lineage column/payload equality。

### 方案 B｜写权限收口

如果不希望 DB 内复制 Python canonical JSON 算法，则必须：

- 明确工程表 direct INSERT 权限边界；
- revoke 普通 writer direct INSERT；
- 只允许唯一受控 writer/function 写入；
- 用数据库角色/函数证明无法绕过 persistence identity validation；
- 形成独立 SQL negative test。

不能维持“理论上任何同权限 SQL writer 都能绕过，但文档默认没人这么做”的模糊状态。

---

## 7.4 Migration 规则

**禁止修改历史 migration 022 文件内容。**

022 已有执行回执。

新增修复必须使用下一 migration，例如：

```text
023_v4_10_research_state_lineage_hardening.sql
rollback/023_v4_10_research_state_lineage_hardening.sql
```

具体序号如仓库已有占用则顺延。

---

# 8. B06｜P0/P1｜98 个 vectors 没覆盖本轮真正危险的 lineage 反例

当前 98 个 vectors 对 reducer 业务状态逻辑覆盖不错，但 lineage 负例不足。

当前已有：

```text
prior_digest_reject
unmarked_boundary_reject
producer_wrong_contract_id
producer_wrong_parameter_set_id
producer_wrong_publication_id
```

但没有覆盖：

```text
partial prior
self-consistent forged prior
prior content-address mismatch
calendar mismatch
bare model boundary authorization
unbound core_price_damage
unbound frozen invalidation publication
unbound risk/delta/dq5
unbound scenario
unbound suspension
unbound followup_complete
malformed input_publication_ids
DB forged payload digest
```

因此当前：

```text
missing_required_tags = []
```

只能证明“当前 required tag 集合全部覆盖”，不能证明 required tag 集合本身完整。

---

## 8.1 修复要求

新增本轮 hard-required coverage tags，例如：

```text
prior_full_schema_authenticity
prior_content_address_identity
calendar_lineage_binding
model_boundary_authorization
hard_invalidation_provenance
state_input_field_provenance
input_publication_manifest_shape
followup_owner_gate
db_payload_identity_guard
```

这些 required tags 必须由 verifier 中**硬编码要求**，不能只来自 vector 自己声明。

修复后重新生成：

```text
V4_10_INDEPENDENT_POSTCHECK_R1_1
V4_10_MACHINE_VECTOR_COVERAGE_R1_1
```

---

# 9. V4-09 N01 / N02 不得被本任务误关闭

当前已有两个独立 hardening audit：

```text
AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
AUD-V4-09-DB-CONSUMER-IDENTITY-N02
```

本任务：

```text
不修改 V4-09 accepted runtime
不回滚 migration 021
不自动关闭 N01/N02
```

如果本轮顺手补充了通用基础设施，也必须：

```text
单独给出 N01/N02 acceptance evidence
```

否则继续保持 OPEN。

---

# 10. 其余历史 OPEN capability audits 继续保持独立

以下项目本轮不得伪装成已关闭：

```text
V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
AUD-AMOUNT-A-06
DM01_REAL_INCREMENTAL_BUILDERS
LEGACY_VALID_MEMBER_EXACT_PRODUCER
FORWARD_PIT_HISTORY_ACCUMULATION
V4-06-BAOSTOCK-BINDING-TOLERANCE-01
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
```

本任务不因为这些 OPEN 而阻断 reducer lineage 修复，但也不得修改其 capability 状态。

---

# 11. 允许修改范围

允许：

```text
src/v4/research_state.py
src/v4/research_state_persistence.py

config/v4_10_*.json
  - 只能版本化修订，不得覆盖掉旧候选审计轨迹

scripts/freeze_v4_10_contract.py
scripts/verify_v4_10_state_reducer.py
scripts/run_v4_10_isolated_verification.py

tests/v4_10/*

新增 migration 023（或下一未占用编号）
新增 reports/v4_10 R1.1 evidence
新增 docs/evidence V4-10 repair disposition / handoff
```

如需要新增通用 provenance helper：

```text
src/v4/*
```

可以，但必须保持职责单一并有独立测试。

---

# 12. 禁止修改范围

禁止：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json   # 不得推进到 V4-10 accepted
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_DEV_BASELINE_HEAD.json

src/v4/stock_prewatch.py
V4-09 algorithm / Priority parameters
V4-07 BASE_SEED thresholds
V4-08 Sector/Rotation algorithms
```

禁止：

```text
生产 permission
shadow production permission
Focus cutover permission
V4-11 implementation
```

在本轮 repair external acceptance 前开启。

---

# 13. 版本治理要求

当前 V4-10 candidate 已经形成正式审计证据。

因此不得静默覆盖旧候选。

必须保留：

```text
原 e3b29a implementation
原 98-vector candidate
原 migration 022
原 reports/v4_10/*
```

修复产生：

```text
R1.1 / V2 / repair revision
```

并明确：

```text
supersedes candidate identity
does not supersede master RESEARCH_STATE_V1 business contract
```

业务合同仍为：

```text
RESEARCH_STATE_V1
```

修的是 engineering interface / lineage contract。

---

# 14. 新测试最低要求

除现有 tests 外，本轮最低新增以下测试族。

## 14.1 Prior Authenticity

见 B01 全部负例。

## 14.2 Model Boundary

见 B02 全部负例。

## 14.3 Provenance

见 B03 全部负例。

## 14.4 Input Manifest Shape

见 B04 全部负例。

## 14.5 DB Integrity

至少：

```text
direct SQL forged payload_digest rejected
direct SQL forged state_publication_id rejected
direct SQL producer lineage mismatch rejected
old valid R1 engineering rows still readable
append-only preserved
revision chain preserved
rollback 023 restores exact 022 state
```

---

# 15. 回归门

必须从 clean detached checkout 执行。

至少覆盖：

```text
tests/v4_phase0
tests/v4_01
tests/v4_02
tests/v4_03
tests/v4_04
tests/v4_05
tests/v4_06
tests/v4_07
tests/v4_08
tests/v4_09
tests/v4_10
tests/v4_joint
governance no-symbol suite
fixed QFQ samples
Phase gates
```

不得为了修复新失败而新增未授权 deselect。

现有唯一历史 deselect：

```text
tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled
```

可以继续保留当前已记录的 supersession 逻辑，但不得扩大 deselect 列表。

---

# 16. 必须输出的修复证据

至少生成：

```text
reports/v4_10/V4_10_R1_1_CONTRACT_FREEZE.json
reports/v4_10/V4_10_R1_1_PRIOR_LINEAGE_ACCEPTANCE.json
reports/v4_10/V4_10_R1_1_MODEL_BOUNDARY_ACCEPTANCE.json
reports/v4_10/V4_10_R1_1_INPUT_PROVENANCE_ACCEPTANCE.json
reports/v4_10/V4_10_R1_1_INPUT_MANIFEST_SHAPE_ACCEPTANCE.json
reports/v4_10/V4_10_R1_1_MACHINE_VECTOR_COVERAGE.json
reports/v4_10/V4_10_R1_1_INDEPENDENT_POSTCHECK.json
reports/v4_10/V4_10_R1_1_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_10/V4_10_R1_1_ISOLATED_REGRESSION.json
reports/v4_10/V4_10_R1_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
reports/v4_10/V4_10_R1_1_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_10/V4_10_R1_1_STAGE_CANDIDATE_MANIFEST.json
reports/v4_10/V4_10_R1_1_EXTERNAL_REAUDIT_HANDOFF.json
reports/v4_10/V4_10_R1_1_CLOSURE.md
```

文件名可在不降低语义的情况下微调。

---

# 17. Independent Postcheck 要求

独立 postcheck 不允许只做：

```text
implementation output == vector expected
```

还必须独立验证：

### Prior

```text
prior schema
content-address identity
calendar lineage
publication existence/binding
```

### Boundary

```text
boundary manifest authorization
from/to model identity
effective date
digest
```

### Facts

```text
field -> producer
field -> parameter
field -> publication
field -> time-role
```

### DB

```text
payload identity
append-only
revision
direct-write negative cases
```

---

# 18. Acceptance Gate

本轮只有满足以下全部条件才允许请求下一次外部验收。

```text
G01 V4-09 accepted head unchanged                         PASS
G02 Prior full-schema authenticity                       PASS
G03 Prior content-address identity                       PASS
G04 Prior calendar lineage                              PASS
G05 Model-boundary authorized manifest                   PASS
G06 State-changing field provenance                      PASS
G07 Frozen invalidation fail-closed before V4-12         PASS
G08 Follow-up completion owner gate                      PASS
G09 input_publication manifest canonical shape           PASS
G10 DB payload/publication identity hardening            PASS
G11 New independent negative vectors                     PASS
G12 Existing reducer semantic vectors                    PASS
G13 Append-only/revision/rollback                        PASS
G14 No-symbol                                            PASS
G15 Clean detached full required regression              PASS
G16 Production/shadow/Focus permissions remain false     PASS
G17 V4-10 Accepted Head still absent                     PASS
```

---

# 19. 本轮结束状态

修复提交完成后，只允许声明：

```text
V4_10_R1_1_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行声明：

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS
V4_10_ACCEPTED
V4_11_AUTHORIZED
```

必须停止并等待独立外部复审。

---

# 20. 通过后的下一步

只有外部复审给出：

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

并完成正式 V4-10 Accepted Head / Global Stage promotion（若阶段合同要求）后，才允许发布：

```text
V4-11 Confirmation / Events Entry
```

V4-11 仍只负责自身范围：

- Legacy confirmation exact AST extraction
- independent golden examples
- D0 facts
- D2 后 event diff
- Amount A 隔离

不得在 V4-11 顺带绕过 V4-12 Structure / Anchor / Support。

---

# 21. 一句话任务摘要

```text
V4-09 保持已接受，不回滚。

当前 V4-10 reducer 的状态机主体方向基本正确，
但其 engineering interface 仍允许“自洽但未被正式发布的 prior”、
无授权 MODEL_BOUNDARY，以及多个无 producer provenance 的状态改变输入进入 reducer。

本轮不要重写算法。
只把 prior / calendar / model-boundary / field-provenance / input-manifest / DB identity 六条线彻底封死，
补独立负例和 clean regression，
然后停止等待外部复审。
```

---

**外部审计裁决：**

```text
V4_09 = KEEP_ACCEPTED
V4_10 = EXTERNAL_ACCEPTANCE_BLOCKED_R1
REPAIR_REQUIRED = YES
V4_11_ENTRY = BLOCKED
```

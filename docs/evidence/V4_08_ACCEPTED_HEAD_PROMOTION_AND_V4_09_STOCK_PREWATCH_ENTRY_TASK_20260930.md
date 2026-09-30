# V4-08 Accepted Head Promotion + V4-09 Stock PREWATCH Entry Task｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**输入 HEAD**：`8200a775d9c4115f479ee60b4c11a16579e86723`  
**外部验收决定**：`V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE`

任务分两部分：

```text
A. V4-08 Accepted Head Promotion
B. V4-09 Stock PREWATCH Engineering Entry
```

禁止再次回到 R5/R5.1/R5.2 重做已经通过的算法。

# A. V4-08 Accepted Head Promotion

## A1. 新建正式 Accepted Head

创建：

```text
data/v4/V4_08_ACCEPTED_HEAD.json
```

至少包含：

```text
contract_id
stage = V4-08
accepted_at
external_acceptance
external_acceptance_decision

input_head / accepted input lineage
membership_binding
r5_2_candidate_manifest
parameter_set
field_registry
accepted_context_contract

native_contract / producer
b0_contract / producer
rotation_contract / producer
b2_contract / producer

clean_checkout
isolated_regression
schema_readback
no_symbol_scan
external_acceptance_document

capabilities
open_audits
production_permission
next_stage
```

## A2. capability 必须精确分层

写入：

```text
SECTOR_NATIVE_CORE = ENGINEERING_ACCEPTED
B0_SECTOR_PREWATCH_RAW = ENGINEERING_ACCEPTED
B1_ROTATION_CORE = ENGINEERING_ACCEPTED
ACCEPTED_CONTEXT_ROUTING = ENGINEERING_ACCEPTED
```

明确：

```text
B2_LEGACY_CONFIRMED_WARM
= NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE

B2_AMOUNT_A
= DIAGNOSTIC_AUDIT_OPEN
```

真实信号：

```text
REAL_SIGNAL_CAPABILITY
= DEGRADED_BY_TARGET_CORE_DATA_HEAD_PRIOR_RPS_AND_FORWARD_PIT_HISTORY
```

权限：

```text
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
```

不得写：

```text
FULL_PRODUCTION_PASS
REAL_SIGNAL_PASS
B2_PASS
```

## A3. 保留 OPEN audits

至少：

```text
V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
AUD-AMOUNT-A-06
DM01_REAL_INCREMENTAL_BUILDERS
LEGACY_VALID_MEMBER_EXACT_PRODUCER
FORWARD_PIT_HISTORY_ACCUMULATION
```

这些是 capability/deferred work，不回滚 engineering acceptance。

## A4. Promotion 必须绑定外部验收文件

绑定：

```text
docs/evidence/V4_08_R5_2_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20260930.md
```

必须记录：

```text
path
SHA256
decision string
audited HEAD
implementation commit
```

不得自行更改外部决定文本。

## A5. Global Stage Head Promotion

更新：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

从：

```text
V4_00_TO_V4_07_ACCEPTED
```

推进到：

```text
V4_00_TO_V4_08_ACCEPTED
```

新增至少：

```text
v4_08_binding
v4_08_external_acceptance
v4_08_status
v4_08_real_signal_capability
v4_08_b2_capability
v4_08_production_permission
v4_09_entry
```

建议：

```text
v4_08_status
= ENGINEERING_PASS_CAPABILITY_SCOPED

v4_08_external_acceptance
= V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE

v4_08_b2_capability
= NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE

v4_08_production_permission
= false

v4_09_entry
= AUTHORIZED_AFTER_V4_08_PROMOTION_VALIDATION
```

## A6. Promotion 不得移动 Daily / Dev Head

必须 byte-compare：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_DEV_BASELINE_HEAD.json
```

promotion 前后必须相同。

不得因为 Stage promotion：

```text
把 Data Head 从 9/24 推到 9/30
把 Dev Baseline 改成当前 HEAD
```

## A7. PIT Membership Head 不重写

保持：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

不覆盖旧 acceptance；V4-08 final Accepted Head 只绑定它。

## A8. Promotion Evidence

至少：

```text
reports/v4_joint/V4_08_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json
reports/v4_joint/V4_08_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json
docs/evidence/V4_08_ACCEPTED_HEAD_PROMOTION_AND_V4_09_ENTRY_20260930.md
```

Validation 至少证明：

```text
external acceptance binding exact
candidate/evidence SHA exact
parameter SHA exact
membership binding exact
global head parent exact
data/dev heads unchanged
B2 capability not overclaimed
production permission false
no-symbol still PASS
promotion idempotent
```

# B. V4-09 Stock PREWATCH Engineering Entry

## B1. Authority

唯一 stage：

```text
V4-09 | Stock PREWATCH
```

权威公式：

```text
STOCK_PREWATCH_V1

raw_qualification
=
base_seed_state
AND
mandatory_core_quality_READY
```

V4-09 只输出：

```text
raw qualification
priority primitives
```

不得提前实现：

```text
D2 final_eligibility
State Reducer
Confirmation Event
Structure/Anchor
Radar/Focus
UI cutover
```

## B2. Source Boundary

V4-09 第一版 Pure-Core 输入：

```text
V4-05 accepted Core Profile / factors
V4-07 accepted Base Seed
accepted identity/universe
accepted target publication context
```

当前最自然 engineering replay：

```text
trade_date = 2026-09-28
```

因为：

```text
V4-05 Core = 2026-09-28
V4-07 Base Seed = 2026-09-28
```

不要为了追 9/30 进行 relabel、forward-fill 或混用不同交易日。

## B3. V4-08 不作为 Stock PREWATCH hard gate

权威合同 §22：

```text
Sector Context
只在 D3 影响解释和独立 context 排序键
不能成为 hard eligibility gate
```

所以禁止：

```text
sector_prewatch 必须 TRUE 才允许 stock
rotation_core_state 必须 IN 才允许 stock
B2 confirmed 必须 TRUE 才允许 stock
```

V4-08 的 accepted stage sequencing 只提供系统阶段完整性，不改变 Stock PREWATCH 资格公式。

## B4. mandatory_core_quality_READY 必须先冻结定义

合同给出名称，但不允许实现者自由发挥。

编码前生成：

```text
config/v4_09_mandatory_core_quality_contract_v1.json
```

明确：

```text
required input fields
每字段 producer
quality allowlist
UNKNOWN propagation
source/time semantics
price basis
same-session requirement
```

原则：只检查 `STOCK_PREWATCH_V1` 真正必需的 Core/Seed 事实。

不能：

```text
把所有 Profile 字段都要求 READY
把 Supplemental turnover 加进 mandatory
把 Sector Context 加进 mandatory
```

若 required 输入 UNKNOWN：

```text
mandatory_core_quality_READY = UNKNOWN
raw_qualification = UNKNOWN
```

不能 UNKNOWN → FALSE。

## B5. Raw Qualification 三值逻辑

必须 Kleene：

```text
base_seed_state TRUE  AND quality TRUE  → TRUE
base_seed_state FALSE AND quality TRUE  → FALSE
base_seed_state UNKNOWN                 → UNKNOWN
quality UNKNOWN                         → UNKNOWN
```

若 quality hard fail 有明确合同 FALSE，再按合同处理；不得临时发明。

## B6. Priority Primitives

阶段 §78 要求 raw qualification + priority primitives。

第一版按 §23/24：

### emergence

```text
HIGH   delta3 >= 10
MEDIUM delta3 >= 3
LOW    otherwise
UNKNOWN if required fact unknown
```

### structure

```text
HIGH
= compression_state == COMPRESSING_STRONG

MEDIUM
= compression_state == COMPRESSING
  OR ma_structure_state == BULL_TRANSITION

LOW
= otherwise evaluable
```

### risk

来源：

```text
core_extension_risk
```

枚举顺序：

```text
LOW < MEDIUM < HIGH < EXTREME
```

UNKNOWN 单独处理，不当 LOW。

## B7. Priority Bucket

只对：

```text
raw_qualification == TRUE
```

形成正式 PREWATCH priority bucket：

```text
A:
emergence HIGH
AND structure HIGH
AND risk LOW

B:
emergence HIGH
AND structure >= MEDIUM
AND risk <= MEDIUM

C:
emergence MEDIUM
AND structure HIGH
AND risk LOW

D:
其余 eligible
```

排序枚举必须机器冻结：

```text
bucket A < B < C < D
```

不得按字符串字典序。

## B8. 没有神秘总分

禁止：

```text
total_score
weighted_score
综合评分 87.34
```

输出轴必须保留：

```text
emergence
structure_quality
risk
```

后续 Context / Staleness 可按阶段加入，但不改 raw资格。

## B9. 当前 V4-07 Base Seed 全 UNKNOWN 的处理

当前 accepted V4-07：

```text
REAL_BASE_SEED_SIGNAL
= DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN
```

所以 9/28 V4-09 可能 TRUE=0、UNKNOWN 很多，这不是失败。

禁止：

```text
为了出现候选降低 delta3
为了非空把 UNKNOWN 当 FALSE
回退旧 V4-03 R3 RPS
```

验收关注逻辑、lineage 和 UNKNOWN 是否诚实。

## B10. Contract / Registry / AST

编码前必须完成：

```text
config/v4_09_stock_prewatch_contract_v1.json
config/v4_09_mandatory_core_quality_contract_v1.json
config/v4_09_field_registry_v1.json
config/v4_09_parameter_set_v1.json
config/v4_09_machine_ast_v1.json
config/v4_09_machine_vectors_v1.json
```

字段至少：

```text
security_id
trade_date
publication_id
base_seed_state
mandatory_core_quality_ready
raw_qualification
emergence_axis
structure_quality_axis
risk_axis
priority_bucket
matched_predicates
unknown_predicates
waiting_for
quality
input_digest
parameter_set_id
model_contract_id
```

## B11. 参数冻结

复用权威参数：

```text
delta3_medium = 3 percentage points
delta3_high   = 10 percentage points
```

来源必须绑定 latest master contract 和 accepted Core field units。

不得把 RPS 0..1 / 0..100 单位混淆。

parameter perturbation 必须证明 runtime 真正消费参数实例。

## B12. Full-market materialization

使用 2026-09-28 accepted same-session inputs：

```text
expected identity count = 5222
```

每个 security 一行。

统计：

```text
TRUE
FALSE
UNKNOWN
```

以及：

```text
A/B/C/D
UNKNOWN_BUCKET
NOT_ELIGIBLE
```

不允许只输出候选。

## B13. Persistence

新增 append-only migration：

```text
021_v4_09_stock_prewatch.sql
```

除非能证明现有表已有明确、无语义冲突的正式 namespace。

保存至少：

```text
publication identity
security_id
trade_date
raw qualification
axis values
bucket
quality/reasons
input digests
parameter/model ids
```

要求 same publication+security idempotent、different revision append-only、old accepted rows immutable、exact readback、rollback only removes migration 021 objects。

## B14. No-feedback

V4-09 禁止读取：

```text
same-day V4-08 sector result as hard gate
V4-10 state
V4-11 confirmation
V4-12 structure/support
V4-15 Radar
Focus
UI
future outcome
forward return
```

测试扰动这些字段，V4-09 raw qualification 必须不变。

## B15. NO_SYMBOL P0

继续永久门：

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

要求：

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

禁止 `if security_id == 某股票`、特殊名单控制资格、针对个股代码调参数。

## B16. Determinism / Generalization

至少：

```text
same-context replay byte-identical
logical digest identical
different target context 不改 source code
未来 input mutation 不改冻结 T result
```

不要再出现 source 固定：

```text
2026-09-28
5222
publication id
board counts
```

这些必须来自 run context。

## B17. Evidence

至少：

```text
reports/v4_09/V4_09_STAGE_ENTRY.md
reports/v4_09/V4_09_CONTRACT_FREEZE.json
reports/v4_09/V4_09_PARAMETER_BINDING.json
reports/v4_09/V4_09_MACHINE_VECTOR_COVERAGE.json
reports/v4_09/V4_09_FULL_MARKET_CANDIDATE.json
reports/v4_09/V4_09_INDEPENDENT_POSTCHECK.json
reports/v4_09/V4_09_DETERMINISM.json
reports/v4_09/V4_09_MULTI_CONTEXT_GENERALIZATION.json
reports/v4_09/V4_09_FEEDBACK_ISOLATION.json
reports/v4_09/V4_09_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
reports/v4_09/V4_09_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_09/V4_09_ISOLATED_REGRESSION.json
reports/v4_09/V4_09_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_09/V4_09_STAGE_CANDIDATE_MANIFEST.json
reports/v4_09/V4_09_CLOSURE.md
reports/v4_09/V4_09_EXTERNAL_REAUDIT_HANDOFF.json
```

## B18. V4-09 不能自行 external accept

Codex 最终只能到：

```text
V4_09_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行创建：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
V4_STAGE_ACCEPTED_HEAD -> V4_09
```

除非后续获得独立外部验收。

# C. Clean-checkout final gate

完成 A+B 后：

```text
clean detached checkout
disposable PostgreSQL
full required V4 regression
no config/.env
no-symbol
promotion validation
V4-09 targeted tests
```

必须记录实际 test count。

# D. Handoff

Codex 提交后报告：

```text
pushed HEAD

V4-08:
accepted head SHA
global stage head SHA
promotion receipt
promotion validation
data/dev head unchanged proof

V4-09:
contract / parameter / AST digests
full-market counts
TRUE/FALSE/UNKNOWN
A/B/C/D distributions
independent postcheck
determinism
multi-context
feedback isolation
migration readback
no-symbol
clean regression
```

然后停止，等待独立外部审计。

**任务结束**

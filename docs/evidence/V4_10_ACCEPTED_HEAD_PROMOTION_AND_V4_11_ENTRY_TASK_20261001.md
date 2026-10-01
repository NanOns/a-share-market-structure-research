# V4-10 Accepted Head Promotion + V4-11 Confirmation / Events 入场任务卡｜2026-10-01

**前置外部裁决：** `V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE`  
**审计 sealed HEAD：** `f0c6eb57f7c0c8fc2d0d6875d73295e349e7d315`  
**Accepted implementation：** `6a339e71d38ced6e97c077fddef8dc7a8dfbd104`  
**父阶段：** V4-09 Accepted / KEEP_ACCEPTED  
**任务性质：** Promotion + 下一阶段入场，不是 V4-11 实现任务

---

# 1. 唯一执行顺序

必须严格执行：

```text
Step 1  读取并验证 V4-10 R1.2 外部验收
Step 2  生成 V4_10_ACCEPTED_HEAD candidate
Step 3  独立 Promotion Validator
Step 4  Promotion PASS 后写 V4_10_ACCEPTED_HEAD
Step 5  更新 V4_STAGE_ACCEPTED_HEAD → V4_00_TO_V4_10_ACCEPTED
Step 6  生成 V4-11 Confirmation / Events Stage Entry
Step 7  STOP
```

禁止将：

```text
Accepted Head Promotion
+
V4-11 算法实现
```

混在同一个未经独立验证的提交中。

---

# 2. V4-10 Accepted Head

创建：

```text
data/v4/V4_10_ACCEPTED_HEAD.json
```

至少必须包含：

```text
stage = V4-10
status = ENGINEERING_PASS_INTERFACE_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
external_acceptance_decision = V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE

implementation_commit = 6a339e71d38ced6e97c077fddef8dc7a8dfbd104
audited_sealed_head = f0c6eb57f7c0c8fc2d0d6875d73295e349e7d315
```

并精确绑定：

```text
V4_10_R1_2_CONTRACT_FREEZE.json
V4_10_R1_2_STAGE_CANDIDATE_MANIFEST.json
V4_10_R1_2_INDEPENDENT_POSTCHECK.json
V4_10_R1_2_MODEL_BOUNDARY_ACCEPTANCE.json
V4_10_R1_2_INPUT_PROVENANCE_ACCEPTANCE.json
V4_10_R1_2_INPUT_MANIFEST_SHAPE_ACCEPTANCE.json
V4_10_R1_2_CONTROLLED_PUBLISHER_ACCEPTANCE.json
V4_10_R1_2_SCHEMA_MIGRATION_RECEIPT.json
V4_10_R1_2_ISOLATED_REGRESSION.json
V4_10_R1_2_CLEAN_CHECKOUT_RECEIPT.json
V4_10_R1_2_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
V4_10_R1_2_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20261001.md
```

父绑定必须为：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
sha256 = 641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d
```

---

# 3. Capability 声明必须精确

V4-10 Accepted Head 只能声明：

```text
STATE_REDUCER_INTERFACE = ENGINEERING_ACCEPTED
STATE_REDUCER_AUTHORITY = ENGINEERING_ACCEPTED
STATE_REDUCER_PERSISTENCE = ENGINEERING_ACCEPTED
STATE_REDUCER_MACHINE_VECTORS = ENGINEERING_ACCEPTED

FULL_D0_D1_D2_DAG = NOT_IMPLEMENTED
V4_11_CONFIRMATION = NOT_IMPLEMENTED
V4_12_STRUCTURE_SUPPORT = NOT_IMPLEMENTED

PRODUCTION_PERMISSION = false
SHADOW_PRODUCTION_PERMISSION = false
FOCUS_CUTOVER_PERMISSION = false
```

禁止写：

```text
FULL_STATE_SYSTEM_ACCEPTED
FULL_DAG_PASS
PRODUCTION_READY
```

---

# 4. Promotion Validator

新增 versioned validator，至少逐项检查：

```text
P01 V4-10 Accepted Head schema
P02 parent V4-09 Accepted Head exact
P03 implementation commit exact
P04 sealed head is descendant of implementation commit
P05 external acceptance document exact
P06 R1.2 contract freeze exact
P07 candidate manifest exact
P08 independent postcheck exact
P09 model boundary evidence exact
P10 provenance evidence exact
P11 controlled publisher evidence exact
P12 schema migration evidence exact
P13 clean regression exact
P14 no-symbol exact
P15 migration 022 byte-identical
P16 migration 023 byte-identical
P17 migration 024 exact accepted implementation
P18 business thresholds remain 2 / 10 / 3 / 3
P19 V4_DATA_ACCEPTED_HEAD unchanged
P20 V4_DEV_BASELINE_HEAD unchanged
P21 V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD unchanged
P22 A01-A09 remediation registry retained OPEN
P23 production/shadow/Focus remain false
P24 promotion idempotent
P25 clean detached validation
```

任何一项 FAIL：

```text
不得写正式 Accepted Head
不得推进 Global Stage Head
不得授权 V4-11
```

---

# 5. Global Stage Head

只有 Promotion Validator PASS 后才允许更新：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

从：

```text
V4_00_TO_V4_09_ACCEPTED
```

变为：

```text
V4_00_TO_V4_10_ACCEPTED
```

新增至少：

```text
v4_10_binding
v4_10_status
v4_10_external_acceptance
v4_11_entry
```

同时必须保留：

```text
V4-01 ... V4-09 accepted bindings
V4-05 Historical AS_RECORDED blocked state
V4-06 BaoStock strict binding open state
V4-07 prior-RPS degraded state
V4-08 capability scoped state
A01-A09 remediation OPEN registry
production=false
shadow=false
focus=false
```

Stage Head 前进不得被误解为 Data Head 前进。

---

# 6. V4-11 Stage Entry

依据 V4.2.2 §78：

```text
V4-11 = Confirmation / Events
```

Stage Entry 只授权合同设计与实现启动，不等于实现完成。

必须冻结/登记：

```text
LEGACY_ADAPTER_V1
CONFIRMATION_DETECTOR_V1
STATE_EVENT_V1
```

以及：

```text
field registry
producer identity
parameter set
machine AST
golden vectors
UNKNOWN semantics
time role
input publication contract
output schema
```

---

# 7. V4-11 Legacy Adapter

依据 §34.3，保留场景：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

必须从旧实现独立提取：

```text
source path
function/symbol
source SHA
call graph
parameters
input units
time semantics
output semantics
UNKNOWN semantics
```

发现旧逻辑内部依赖：

```text
Final State
Focus
same-day downstream
online supplemental
future outcome
```

则必须拆成纯函数，或保持 diagnostic。

禁止直接把旧代码包装后就声称 accepted D0。

---

# 8. D0 Confirmation Facts

D0 只生成确认事实，不直接改 Final State。

至少输出：

```text
security_id
trade_date
confirmation_status
matched_scenarios[]
primary_scenario
scenario_evidence[]
raw_predicates
unknown_predicates
producer_contract_id
parameter_set_id
source_publication_ids[]
input_digest
```

最终：

```text
CONFIRMED
```

由已接受的 V4-10 D2 reducer 消费。

---

# 9. Amount A 必须隔离

当前：

```text
AUD-AMOUNT-A-06 = OPEN
```

因此任何 Amount-A-dependent branch：

```text
不得进入 formal Confirmation path
```

只能：

```text
DISABLED
DIAGNOSTIC
UNKNOWN
```

禁止：

```text
fallback 0
fallback FALSE
读取旧 staging Amount A
```

---

# 10. STATE_EVENT_V1

只能在：

```text
D2 final state
+
frozen prior_session_state_head
```

之后计算。

事件集合：

```text
FIRST_OBSERVED
CONFIRMATION_INVALIDATED
RECONFIRMED
NEW_CONFIRMED
SCENARIO_UPGRADED
CONFIRMATION_WEAKENED
PERSISTENT_CONFIRMED
SCENARIO_CHANGED
NONE
```

事件 predecessor 固定使用：

```text
prior_session_state_head
```

禁止使用：

```text
same_day_revision_parent
```

同日 r1/r2/r3 相对于上一交易日仍为首次确认时：

```text
必须继续 NEW_CONFIRMED
```

不得因同日 revision 变成 PERSISTENT_CONFIRMED。

---

# 11. Security-level Dedup

每个：

```text
(publication_id, security_id)
```

只能有一个 canonical confirmation result。

保留：

```text
primary_scenario
matched_scenarios[]
scenario_evidence[]
```

同一股票多场景不能生成多行正式对象。

---

# 12. 独立向量最低覆盖

至少覆盖：

```text
NONE → CONFIRMED
SEED → CONFIRMED
PREWATCH → CONFIRMED
persistent confirmed
same-day revision remains NEW_CONFIRMED
reconfirmed after prior confirmed episode
scenario upgraded
scenario changed but not upgraded
confirmation weakened
hard invalidation wins over confirmation
required confirmation fact UNKNOWN
Amount A path disabled
multi-scenario dedup
producer mismatch
parameter mismatch
publication mismatch
future timestamp rejected
same-day feedback rejected
no-symbol-specific logic
```

---

# 13. Migration 编号治理

当前：

```text
024 = V4-10 R1.2 authority hardening
```

跨阶段 A09/N02 未来也需要 migration。

V4-11 若需要 schema migration：

```text
必须先由统一 migration allocator / registry 分配下一个未占用编号
```

禁止两个工作包并行抢同一 migration number。

历史 migration 不得修改。

---

# 14. 本轮完成状态

Promotion + Entry 完成后只允许声明：

```text
V4_10_ACCEPTED_HEAD_PROMOTION = PASS
V4_11_CONFIRMATION_EVENTS_ENTRY = AUTHORIZED
```

禁止声明：

```text
V4_11_IMPLEMENTED
V4_11_ACCEPTED
FULL_D0_D1_D2_PASS
```

完成 Stage Entry 后 STOP，等待下一轮独立审计，再进入 V4-11 implementation。

# V4-15E5 R1R1C｜Canonical Target & Signal Metadata Binding Repair Task R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 阶段：V4-15E5 R1R1C  
> 任务性质：定点 canonical metadata identity repair  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`68b3d97d1f5d98a4ed6be87bca3ce8c81696e587`  
> 前置审计：`V4_15E5_R1R1B_CANONICAL_RECONSTRUCTION_INTEGRATION_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md`  
> 目标最高状态：`R1R1C_CANDIDATE_EXTERNAL_AUDIT_REQUIRED`

## 0. 唯一目标

只关闭：

```text
R1R1B-M01 TARGET_CONTRACT_EXACT_BINDING
R1R1B-M02 CORE_SIGNAL_CONTRACT_EXACT_BINDING
```

不得重做 migration 032、reconstruction authority、205 population、snapshot 算法、model import、prediction outputs、permission/CAS 或 Priority 算法。

## 1. PASS_KEEP 冻结

运行前生成：

```text
R1R1C_PASS_KEEP_FREEZE.json
```

必须绑定并冻结 R1R1B 已通过能力：

```text
032 migration
205 reconstruction authorities
205 observations
205 snapshots
4100 feature values / 477 UNKNOWN
615 predictions
616 slots
exact E5 R1 output parity
accepted artifact imports
SHADOW permission
canonical CAS / rollback
API boundary
Priority synthetic fixture
V4-18 successor
protected state
targeted/scoped baseline
```

修复后以下 logical content 必须不变：

```text
source observation IDs
historical population
feature values
feature source digests
prediction outputs
prediction output digests
projection states
model artifacts
model roles
PRIORITY_V1
```

## 2. Blocker A｜Target Authority

当前错误：

```text
ABS_RETURN_N:T1
contract_id = FEP_E5_OBSERVATION_V1
formula = "accepted V4-15 ABS_RETURN_N:T1"
enabled = true
```

正式 authority：

```text
config/fep_target_registry_v1.json
contract_id = FEP_E1_TARGETS_V1
```

目标条目：

```text
target_id = ABS_RETURN_N:T1
family = ABS_RETURN_N
horizon = 1
scope_id = FEP_STOCK_ENTRY_CORE
definition_reference = FEP.5/ABS_RETURN_N
status = REGISTERED_NOT_ENABLED
training_allowed = false
engineering_adapter = true
```

设计 authority：

```text
docs/evidence/fep_e1/FEP_R2_MODULE_DESIGN_20260930.md
FEP.5
ABS_RETURN_N = R_N
```

## 3. Target Contract Repair

Canonical fixture 必须创建/使用：

```text
fep.contracts.contract_id = FEP_E1_TARGETS_V1
```

contract body 必须 exact-bind：

```text
config/fep_target_registry_v1.json
FEP.5 design authority
```

禁止继续把：

```text
FEP_E5_OBSERVATION_V1
```

用作 target contract。

## 4. Target Row

`fep.targets` 的 `ABS_RETURN_N:T1` 必须：

```text
target_id = ABS_RETURN_N:T1
contract_id = FEP_E1_TARGETS_V1
scope_id = FEP_STOCK_ENTRY_CORE
horizon = 1
value_kind = NUMERIC
formula = accepted ABS_RETURN_N definition
enabled = false
```

`unit / risk_set / allowed_quality` 必须从 accepted target/design/settlement authority 导出并封存，不得新造自由文本。

硬边界：

```text
engineering_adapter = true
!=
globally enabled target
```

历史 engineering projection 可以使用 registered engineering adapter，但不得把 target 状态升级成 ENABLED。

输出：

```text
CANONICAL_TARGET_AUTHORITY_BINDING.json
CANONICAL_TARGET_ROW_READBACK.json
```

## 5. Target Negative Tests

至少：

```text
TM-01 observation contract cannot be target contract
TM-02 wrong target registry contract rejected
TM-03 enabled=true rejected for REGISTERED_NOT_ENABLED
TM-04 wrong horizon rejected
TM-05 wrong scope rejected
TM-06 wrong target definition/family rejected
TM-07 formula drift rejected
TM-08 engineering_adapter cannot imply activation/production
```

## 6. Blocker B｜FIRST_PREWATCH Signal Authority

当前错误：

```text
fep.observations.core_signal_contract_id =
FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1
```

该 contract 只描述 historical reconstruction authority，不描述 FIRST_PREWATCH 事件语义。

当前已接受 formal signal contract：

```text
reports/fep_e2_r1r2/ENTRY_EVENT_STRATA_CONTRACT.json

contract_id = FEP_E2_ENTRY_EVENT_STRATA_V1_1
observation_scope = FEP_STOCK_ENTRY_CORE
formal_signals = FIRST_PREWATCH / NEW_CONFIRMED / REENTRY
```

其中 FIRST_PREWATCH：

```text
Accepted Radar ENROLLED
+ maturity PREWATCH
+ no parent episode
```

## 7. Signal Contract Repair

必须在 canonical contract ledger 中 exact-register 已接受 FIRST_PREWATCH authority。

默认应使用：

```text
FEP_E2_ENTRY_EVENT_STRATA_V1_1
```

如果项目内存在更上游、更直接且已正式接受的 FIRST_PREWATCH owner contract，也允许使用，但必须给出：

```text
exact path
bytes
sha256
why it is stricter/more direct
```

禁止新造新的 signal definition。

## 8. Observation Metadata Repair

205 条 historical observations 的：

```text
core_signal_contract_id
```

必须全部指向 exact accepted FIRST_PREWATCH signal/event contract。

保持：

```text
observation_id unchanged
entity_id unchanged
trade_date unchanged
episode_key unchanged
signal type unchanged
reconstruction_authority_id unchanged
snapshot input content unchanged
```

输出：

```text
CANONICAL_SIGNAL_CONTRACT_BINDING.json
CANONICAL_OBSERVATION_METADATA_READBACK.json
```

要求：

```text
205 / 205 exact contract
0 fallback
0 reconstruction-authority substitution
```

## 9. Authority 职责分离

修复后：

```text
reconstruction_authority_id
→ 历史数据 / availability / dependency authority

core_signal_contract_id
→ FIRST_PREWATCH event semantic authority
```

不得再混用。

## 10. Signal Negative Tests

至少：

```text
SM-01 reconstruction authority cannot be core signal contract
SM-02 observation contract cannot silently replace event-strata authority
SM-03 unknown signal contract rejected by canonical verifier
SM-04 wrong observation scope rejected
SM-05 contract without FIRST_PREWATCH rejected
SM-06 changed FIRST_PREWATCH predicate digest rejected
SM-07 wrong event stratum cannot substitute FIRST_PREWATCH identity
```

## 11. Migration 治理

默认：

```text
NO NEW MIGRATION
```

因为当前首先是 canonical seeding / metadata binding 问题。

不得修改：

```text
028
029
030
031
032
```

若实现者能证明现有 schema 无法保持 metadata invariant，才允许 runtime scan next free migration id 后做 additive migration，并输出：

```text
METADATA_SCHEMA_CONFLICT_DISPOSITION.json
```

禁止 rewrite 已提交 migration。

## 12. Canonical Fixture Rebuild

允许重新建立 disposable fresh / upgrade fixtures。

必须保持：

```text
205 observations
205 reconstruction authorities
205 snapshots
4100 feature values
615 prediction runs
615 predictions
616 slots
```

不得：

```text
new model fit
new hyperparameter search
new label resolution
new target semantics
new signal semantics
```

## 13. R1R1B Parity

生成：

```text
R1R1C_CANONICAL_VS_R1R1B_PARITY.json
```

要求：

```text
feature values identical
feature source digests identical
prediction outputs identical
prediction output digests identical
projection states identical
READY/REJECTED_QUALITY identical
model artifact bindings identical
```

允许改变的只有：

```text
target contract identity
signal contract identity
由上述 metadata 修复引出的派生 canonical identity
```

所有 identity changes 必须显式列出。

## 14. Permission / CAS PASS_KEEP

重新验证最小集合：

```text
3 SHADOW permission keys
roles = BASELINE / CHALLENGER / CHALLENGER
CHAMPION = NONE
all final heads = REVOKE
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CAS one-winner concurrency
CAS idempotency
rollback
```

不得改 B03 已通过设计。

## 15. API / Priority PASS_KEEP

确认：

```text
default API axes = null
diagnostic requires exact SHADOW context
FIRST_OBSERVED = false
REAL_OOS = false
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
Priority fixture = synthetic only
priority_projection_grants = 0
PRIORITY_V1 unchanged
```

## 16. V4-18 PASS_KEEP

保留：

```text
config/v4_18_migration_replay_contract_v1_2.json
tests/fep/test_v4_18_namespace_successor.py
```

本轮不得：

```text
grant V4-18 replay
create V4-18 accepted head
enable production cutover
```

## 17. Protected State

重新确认：

```text
V4_STAGE_ACCEPTED_HEAD unchanged
V4_DATA_ACCEPTED_HEAD unchanged
V4_15_ACCEPTED_HEAD unchanged
V4_16_ACCEPTED_HEAD = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
PRIORITY_V1 unchanged
Core/Profile/State/Radar/Cohort unchanged
TDX untouched
```

## 18. Tests

Targeted 至少覆盖：

```text
tests/fep_e5
tests/fep
TM-01 ~ TM-08
SM-01 ~ SM-07
```

要求：

```text
0 failed
```

Scoped regression 必须完整重跑：

```text
introduced active failures = 0
```

既有：

```text
52 known debt
4 skipped
2 governed deselections
```

继续透明保留。

## 19. Evidence

新增：

```text
reports/fep_e5_r1r1c/
```

至少包含：

```text
ENTRY_BASELINE.json
R1R1C_PASS_KEEP_FREEZE.json
CANONICAL_TARGET_AUTHORITY_BINDING.json
CANONICAL_TARGET_ROW_READBACK.json
CANONICAL_SIGNAL_CONTRACT_BINDING.json
CANONICAL_OBSERVATION_METADATA_READBACK.json
METADATA_NEGATIVE_MATRIX.json
R1R1C_CANONICAL_VS_R1R1B_PARITY.json
CANONICAL_LEDGER_READBACK.json
PERMISSION_PASS_KEEP_READBACK.json
CAS_PASS_KEEP_READBACK.json
API_PRIORITY_PASS_KEEP_READBACK.json
V4_18_PASS_KEEP_READBACK.json
PROTECTED_STATE_READBACK.json
TARGETED_SUMMARY.json
SCOPED_REGRESSION_SUMMARY.json
CHANGED_FILE_LIST.json
COMPLETION_REPORT.md
FEP_E5_R1R1C_CANDIDATE_SEAL.json
```

N/A 必须：

```text
status = NOT_APPLICABLE
reason = ...
not_a_pass = true
```

## 20. Candidate Seal

必须绑定：

```text
baseline = 68b3d97d1f5d98a4ed6be87bca3ce8c81696e587
R1R1B implementation = 58372af31c246fd86f18e70654c8f615ce0d983c
target registry exact bytes
event strata exact bytes
205/615/616 parity
permission/CAS pass-keep
tests
protected state
external_acceptance = false
```

## 21. 唯一成功状态

```text
V4_15E5_R1R1C_METADATA_REPAIR =
CANDIDATE_EXTERNAL_AUDIT_REQUIRED

R1R1B_M01_TARGET_CONTRACT_EXACT_BINDING =
PASS_CANDIDATE

R1R1B_M02_CORE_SIGNAL_CONTRACT_EXACT_BINDING =
PASS_CANDIDATE

RECONSTRUCTION_AUTHORITY = PASS_KEEP

E5_B01_CANONICAL_FEP_LEDGER = PASS_CANDIDATE
E5_B02_CANONICAL_IDENTITY_BINDING = PASS_CANDIDATE
E5_B03_CANONICAL_PERMISSION_DEPLOYMENT = PASS_CANDIDATE

TARGET_GLOBAL_ENABLE = false
NEW_TARGET_DEFINITION = false
NEW_SIGNAL_DEFINITION = false
NEW_TRAINING = false
NEW_LABEL_RESOLUTION = false

CHAMPION = NONE
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1C
```

## 22. 禁止越级

R1R1C 完成后不得自动：

```text
E5 PASS_FINAL
E6
V4-16 cutover
FWP / production cutover
MODEL_DISPLAY
PRIORITY_USE
REAL_DAILY activation
```

必须等待 R1R1C 独立外部审计。

## 23. 执行顺序

```text
verify baseline
→ freeze R1R1B pass-keep
→ exact-bind target registry
→ repair fep.targets metadata/state
→ exact-bind FIRST_PREWATCH signal contract
→ repair core_signal_contract_id
→ rebuild fresh/upgrade fixtures
→ prove 205/615/616 parity
→ metadata negative tests
→ permission/CAS pass-keep
→ API/Priority pass-keep
→ V4-18 pass-keep
→ targeted
→ scoped
→ protected state
→ seal
→ commit/push
→ remote readback
→ STOP
```

核心原则：

```text
canonical 不仅要数据行正确，
还必须 Target 合同和 Signal 合同 identity 正确。
```

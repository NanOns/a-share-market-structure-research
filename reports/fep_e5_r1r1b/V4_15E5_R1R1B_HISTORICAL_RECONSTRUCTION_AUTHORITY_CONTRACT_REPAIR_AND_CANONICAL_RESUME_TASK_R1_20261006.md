# V4-15E5 R1R1B｜Historical Reconstruction Authority Contract Repair & Canonical Resume Task R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 R1R1B  
> 任务性质：canonical contract repair + R1R1 resume  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 执行基线：`9a6ecd205c690b62063cc80810272dda8001cfe9`  
> 前置审计：`V4_15E5_R1R1A_BLOCKED_CONTRACT_CONFLICT_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md`  
> 目标最高状态：`R1R1B_CANDIDATE_EXTERNAL_AUDIT_REQUIRED`

---

## 0. 本轮唯一目的

修复已经被真实执行证明的 canonical contract gap：

```text
RECONSTRUCTED_CORRECTED historical observation
没有合法 canonical authority path
```

并在修复成功后继续完成原 R1R1 的：

```text
E5-B01 canonical ledger
E5-B02 canonical observation/snapshot/authority binding
E5-B03 canonical permission/deployment/CAS
```

本轮不是：

```text
重训模型
重新生成标签
重做 E2/E3/E4
新增 Priority 算法
启用 REAL_DAILY
模型晋级
生产切换
```

---

# 1. 运行前 freeze

执行任何 migration / write 前必须先 seal：

```text
R1R1B_CONTRACT_PROTOCOL_FREEZE.json
```

冻结以下语义：

```text
PIT_OBSERVED authority semantics
RECONSTRUCTED_ASOF authority semantics
RECONSTRUCTED_CORRECTED authority semantics
observation authority union
prediction-run authority union
permission role policy
FIRST_OBSERVED boundary
REAL_OOS boundary
production/display/priority boundary
```

运行前明确：

```text
PIT_OBSERVED != RECONSTRUCTED
CANONICAL_PUBLICATION != HISTORICAL_RECONSTRUCTION_AUTHORITY
historical reconstruction recorded now != publication accepted in historical T0
```

---

# 2. Migration 规则

不得修改：

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

必须：

```text
runtime 扫描 migration 目录
取 next free numeric id
生成新的 additive migration
```

当前审计观察：

```text
highest_existing_number = 31
```

但任务实现不得硬编码“032 一定可用”；运行时再次扫描。

输出：

```text
MIGRATION_ALLOCATION_READBACK.json
```

---

# 3. 新 canonical authority 类型

新增：

```text
fep.reconstruction_authorities
```

建议最小字段：

```text
authority_id                  PK
authority_contract_id         FK fep.contracts
scope_id                      FK fep.scopes
namespace_id                  FK v4.model_namespaces
trade_date                    date
evidence_origin               RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED
execution_mode                REPLAY
source_manifest               jsonb
source_manifest_digest        sha256
feature_contract_id           FK fep.contracts
accepted_head_identity        jsonb
reconstructed_at              timestamptz
historical_availability_claim text
as_recorded                   boolean
first_observed                boolean
real_oos                      boolean
```

硬约束：

```text
execution_mode = REPLAY
first_observed = false
real_oos = false
as_recorded = false for current RECONSTRUCTED_CORRECTED path
```

当前 E2 source：

```text
RECONSTRUCTED_CORRECTED
```

不得被升级成：

```text
PIT_OBSERVED
AS_RECORDED
FIRST_OBSERVED
REAL_OOS
```

---

# 4. Reconstruction Authority 必须绑定真实已冻结上游

当前 historical authority 至少绑定：

```text
config/fep_e2_historical_dataset_contract_v1.json

reports/fep_e2_r1r1/HISTORICAL_DATASET_SEAL.json
reports/fep_e2_r1r1/HISTORICAL_FEATURE_GATE.json
reports/fep_e2_r1r1/HISTORICAL_WINDOW_FREEZE.json
reports/fep_e2_r1r1/HISTORICAL_OBSERVATION_POPULATION.json

calendar artifact
historical universe artifact
adjusted canonical daily artifact
dated trading status artifact
identity projection
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD

exact owner-runtime code digests
exact parameter-set digests
```

禁止 authority manifest 使用：

```text
CURRENT
LATEST
TODAY
current HEAD inferred dependency
```

---

# 5. Observation Revision Authority Union

新 migration 必须使：

```text
fep.observation_revisions
```

明确支持两种互斥路径。

## A. CANONICAL_PUBLICATION

```text
authority_kind = CANONICAL_PUBLICATION
publication_id IS NOT NULL
reconstruction_authority_id IS NULL
evidence_origin = PIT_OBSERVED
```

必须继续执行原有：

```text
publication status = ACCEPTED
publication trade_date = observation trade_date
namespace exact match
publication accepted_at <= feature_cutoff <= slot_deadline
dependency_manifest publication exact match
```

不得弱化。

## B. HISTORICAL_RECONSTRUCTION

```text
authority_kind = HISTORICAL_RECONSTRUCTION
publication_id IS NULL
reconstruction_authority_id IS NOT NULL
evidence_origin IN (RECONSTRUCTED_ASOF, RECONSTRUCTED_CORRECTED)
execution_mode = REPLAY
```

不得要求：

```text
reconstructed_at <= historical feature_cutoff
```

因为 reconstructed_at 是当前正式记录时间。

但必须证明：

```text
authority.trade_date = observation.trade_date
authority.scope/namespace = observation scope
feature contract exact match
source manifest exact frozen bytes
dependency manifest exact authority id
```

---

# 6. Manifest Contract Repair

原 validator 强制：

```text
dependency_manifest.publication
```

新合同必须改为 authority-aware：

### Publication path

required:

```text
publication
accepted_head
algorithm_contract
parameter_contract
calendar
universe
adjustment_basis
feature_contract
membership
state_event_revision
enrichment_revision
```

### Reconstruction path

required:

```text
reconstruction_authority
source_dataset_contract
historical_population
accepted_head
algorithm_contract
parameter_contract
calendar
universe
adjustment_basis
feature_contract
membership
state_event_revision
enrichment_revision
```

两种 authority key：

```text
不得同时存在
```

禁止 reconstruction path 偷塞：

```text
publication = row_digest
```

---

# 7. Prediction Run Authority Union

必须同步修：

```text
fep.prediction_runs
```

不能只修 observation。

新增互斥：

```text
authority_kind
publication_id nullable
reconstruction_authority_id nullable
```

## Historical simulation

```text
prediction_evidence = HISTORICAL_SIMULATION
run.authority_kind = HISTORICAL_RECONSTRUCTION
```

## FIRST_OBSERVED

必须：

```text
run.authority_kind = CANONICAL_PUBLICATION
```

绝不允许：

```text
HISTORICAL_RECONSTRUCTION
→ FIRST_OBSERVED
→ REAL_OOS
```

---

# 8. Prediction Evidence DB Guard

新增/更新 DB trigger，至少保证：

```text
HISTORICAL_SIMULATION
  requires reconstruction authority

FIRST_OBSERVED
  requires canonical publication authority

LATE_RECONSTRUCTION / CORRECTED_RECONSTRUCTION
  cannot become FIRST_OBSERVED

reconstruction authority
  cannot grant REAL_OOS
```

不能只放在 Python。

---

# 9. Reconstruction Authority 不等于 fake publication

必须新增 negative tests：

```text
RA-01 reconstruction authority cannot insert into v4.publications as historical observed fact
RA-02 reconstructed_at may be after T0 without becoming PIT
RA-03 historical reconstruction cannot claim accepted_at historical publication semantics
RA-04 row digest cannot be authority_id substitution without registered authority row
RA-05 current publication cannot satisfy reconstruction authority
RA-06 authority trade_date mismatch rejected
RA-07 namespace mismatch rejected
RA-08 feature contract mismatch rejected
RA-09 missing frozen source binding rejected
RA-10 CURRENT/LATEST/TODAY dependency rejected
RA-11 reconstructed authority cannot FIRST_OBSERVED
RA-12 reconstructed authority cannot REAL_OOS
RA-13 reconstructed authority cannot production display
```

---

# 10. 205 Historical Observation Mapping

原 R1R1 已保留：

```text
205 observations
```

本轮必须做到：

```text
205 / 205 mapped
0 silent skip
0 fake publication
```

每条 observation 必须：

```text
source observation id
→ reconstruction authority
→ observation revision
→ snapshot
```

输出：

```text
HISTORICAL_RECONSTRUCTION_AUTHORITY_MAPPING.json
```

如果任意一条不能合法绑定：

```text
BLOCKED_AUTHORITY_MAPPING_INCOMPLETE
```

---

# 11. Snapshot Exact Binding

不得继续把整个：

```text
EXACT_MODEL_ROWS.jsonl.gz
```

的文件 digest 直接当 snapshot digest。

每个 snapshot 必须 exact-bind：

```text
observation
observation revision
feature contract
exact feature vector / accepted inference input
quality state
source digests
```

输出：

```text
CANONICAL_SNAPSHOT_BINDING_READBACK.json
```

要求：

```text
205 observations exact covered
615 model projections reuse same accepted snapshot identities as applicable
```

---

# 12. 恢复 B01｜Canonical Ledger

B02 authority path通过后，继续完成：

```text
fep.observations
fep.observation_revisions
fep.snapshots
fep.feature_values
fep.models
fep.model_sets
fep.model_set_members
fep.prediction_slots
fep.slot_model_bindings
fep.prediction_runs
fep.predictions
fep.slot_receipts
```

历史 projection：

```text
205 observations
3 model families
615 projections
planned slot denominator preserved
```

不能：

```text
drop rejected/unknown denominator rows
```

---

# 13. B03｜Narrow SHADOW Permission Role Repair

当前 028：

```text
CHECK(model_role='CHAMPION')
```

与：

```text
SHADOW_INFERENCE may compute set members
```

语义冲突。

新 additive migration 允许：

```text
capability = SHADOW_INFERENCE
→ model_role must equal exact role present in model_set_members
→ allowed roles: BASELINE / CHALLENGER / CHAMPION
```

但：

```text
DESCRIPTIVE_DISPLAY
MODEL_DISPLAY
PRIORITY_USE
```

仍必须：

```text
model_role = CHAMPION
```

必须保留 FK：

```text
(model_set_id, scope_id, target_id, horizon, feature_contract_id, model_role)
→ exact model_set_member
```

禁止：

```text
drop role FK
allow arbitrary role
grant display to baseline/challenger
fake CHAMPION
```

---

# 14. Canonical CAS Resume

authority + ledger + permission repair 后，重新执行：

```text
ALLOW
REVOKE
idempotency
wrong expected version
wrong prior activation
cross-target
cross-horizon
cross-model-set
concurrent initial CAS
atomic rollback
```

必须走：

```text
fep.cas_deploy(...)
```

不得 Python-only CAS 代替。

---

# 15. Fresh / Upgrade DB

必须两条路径全部通过：

```text
FRESH_DB
UPGRADE_DB
```

验证：

```text
new migration applied exactly once
028~031 unchanged
reconstruction authority path works
publication PIT path still works
permission role policy exact
```

新增特别回归：

```text
原 publication path 与原 validator 行为必须保持
```

---

# 16. API / Priority 边界

即使 canonical historical projection 成功：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
```

Priority V2 仍：

```text
synthetic / engineering fixture only
```

默认 API 仍不得展示：

```text
MODEL_DISPLAY
PRIORITY_USE
```

没有 Champion：

```text
CHAMPION = NONE
```

---

# 17. Protected State

必须保持：

```text
PRIORITY_V1 unchanged
PREWATCH eligibility unchanged
Core/Profile/State/Radar/Cohort unchanged
V4 accepted heads unchanged
R25 current state unchanged
TDX read-only
```

并输出 exact digest readback。

---

# 18. 测试要求

## Targeted

必须包含：

```text
existing R1R1 identity tests
new reconstruction-authority tests
observation authority union
prediction-run authority union
permission role repair
canonical ledger
canonical CAS
rollback
```

## Scoped regression

要求：

```text
introduced active failures = 0
```

既有 52 known debt：

```text
继续显式保留
```

不得从 summary 消失。

---

# 19. 必需新 Evidence

在原：

```text
reports/fep_e5_r1r1/
```

基础上至少新增：

```text
R1R1B_CONTRACT_PROTOCOL_FREEZE.json
HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json
HISTORICAL_RECONSTRUCTION_AUTHORITY_MAPPING.json
RECONSTRUCTION_AUTHORITY_DB_READBACK.json
OBSERVATION_AUTHORITY_UNION_READBACK.json
PREDICTION_RUN_AUTHORITY_UNION_READBACK.json
CANONICAL_SNAPSHOT_BINDING_READBACK.json
PIT_PUBLICATION_PATH_REGRESSION.json
RECONSTRUCTION_NEGATIVE_MATRIX.json
PERMISSION_ROLE_REPAIR_READBACK.json
```

原 NOT_APPLICABLE receipts 若本轮已执行，必须替换为真实本轮 readback；不能仍把 N/A 当 PASS。

---

# 20. Candidate Seal

成功时生成新：

```text
FEP_E5_R1R1B_CANDIDATE_SEAL.json
```

必须绑定：

```text
baseline = 9a6ecd205c690b62063cc80810272dda8001cfe9
new migration
contract freeze
authority manifest
205 mapping
snapshot identities
615 projection identities
permission/CAS proof
fresh/upgrade proof
tests
protected state
external_acceptance = false
```

---

# 21. 成功退出状态

唯一成功状态：

```text
V4_15E5_R1R1B_CANONICAL_INTEGRATION =
CANDIDATE_EXTERNAL_AUDIT_REQUIRED

HISTORICAL_RECONSTRUCTION_AUTHORITY =
PASS_CANDIDATE

E5_B01_CANONICAL_FEP_LEDGER =
PASS_CANDIDATE

E5_B02_CANONICAL_IDENTITY_BINDING =
PASS_CANDIDATE

E5_B03_CANONICAL_PERMISSION_DEPLOYMENT =
PASS_CANDIDATE

FAKE_PUBLICATION = false
HISTORICAL_AVAILABILITY_FABRICATION = false
PARALLEL_SCHEMA_AUTHORITY = false
FAKE_CHAMPION = false
NEW_TRAINING = false
NEW_LABEL_RESOLUTION = false
PRIORITY_V1_MUTATION = false
PROTECTED_STATE_MUTATION = false
TDX_MUTATION = false

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

NEXT =
STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1B
```

---

# 22. 失败状态

如果 contract repair 无法在不伪造历史 availability 的情况下完成：

```text
V4_15E5_R1R1B_CANONICAL_INTEGRATION =
BLOCKED_RECONSTRUCTION_AUTHORITY_CONTRACT

NEXT =
STOP_WAIT_EXTERNAL_ARCHITECTURE_REVIEW
```

不得：

```text
补造 historical publication
回填 fake accepted_at
降低 PIT publication validator
删除 FK
跳过 observation
```

---

# 23. 最终执行顺序

```text
verify baseline 9a6ecd...
→ freeze authority semantics
→ runtime scan next migration id
→ implement reconstruction_authority canonical table
→ repair observation authority union
→ repair prediction-run authority union
→ DB guards / negative tests
→ map all 205 historical observations
→ build exact canonical snapshots
→ resume B01 canonical prediction ledger
→ narrow B03 SHADOW role repair
→ canonical fep.cas_deploy
→ fresh DB
→ upgrade DB
→ Priority fixture / API boundary
→ targeted
→ scoped
→ protected-state readback
→ candidate seal
→ commit/push
→ GitHub remote readback
→ STOP
```

本轮核心不是“绕过 publication”。

而是把系统原本已经承认的：

```text
RECONSTRUCTED_CORRECTED
```

变成真正有独立 canonical authority 语义的正式历史重建路径，同时继续保持：

```text
PIT_OBSERVED 的 publication 约束完全不降级。
```

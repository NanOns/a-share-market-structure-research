# V4-15E5 R1R1A｜Blocked Contract Conflict Independent External Audit R1｜2026-10-06

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 R1R1 / R1R1A  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 原始 R1R1 基线：`2bdca9dd87d210f778f4ec90aa4fbaa5f1708866`  
> R1R1 诊断提交：`d2514c29250a4983d8726545a1367695d79343f8`  
> 当前远端 HEAD：`9a6ecd205c690b62063cc80810272dda8001cfe9`  
> 当前 HEAD 性质：blocked diagnostic publication receipt

---

## 0. 唯一总裁决

```text
V4_15E5_R1R1A_EXTERNAL_AUDIT =
PASS_FAIL_CLOSED_BLOCKED_CONTRACT_DESIGN_GAP

R1R1_REMOTE_PUBLICATION =
PASS_BLOCKED_RESULT_VISIBLE

R1R1_CANONICAL_INTEGRATION =
BLOCKED_CONTRACT_CONFLICT

PRIMARY_ROOT_CAUSE =
E1_CANONICAL_HISTORICAL_RECONSTRUCTION_AUTHORITY_MODEL_INCOMPLETE

E5_B01 =
OPEN_BLOCKER_DEPENDS_ON_B02

E5_B02 =
OPEN_BLOCKER_CONTRACT_REPAIR_REQUIRED

E5_B03 =
OPEN_BLOCKER_CONFIRMED_NARROW_REPAIR_REQUIRED

NEXT =
V4_15E5_R1R1B_HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT_REPAIR_AND_CANONICAL_RESUME
```

这次不能把“任务没有执行成功”归类为普通实现失败。

Codex 实际做对了最重要的一件事：

```text
没有伪造历史 publication
没有把 row digest 当 publication_id
没有拿当前 publication 回填历史 T0
没有跳过 205 个无法映射的 observation
没有伪造 CHAMPION
没有继续写 canonical prediction/permission/CAS
```

因此本轮的 fail-closed 本身通过审计。

真正需要修的是：

> E1 canonical FEP 合同没有为“事后构建、但明确标记为 RECONSTRUCTED_CORRECTED / HISTORICAL_SIMULATION 的历史观察”提供合法 canonical authority 类型。

---

## 1. 远端执行拓扑

当前远端相对原始 R1R1 基线：

```text
2bdca9dd...
    ↓
d2514c29...
    R1R1 authority diagnostic + identity gate + tests + blocked evidence
    ↓
9a6ecd20...
    blocked result remote readback / publication receipt
```

当前 HEAD：

```text
9a6ecd205c690b62063cc80810272dda8001cfe9
```

当前 HEAD 没有伪装成完成候选，明确写：

```text
BLOCKED_RESULT_PUBLISHED_NOT_CANDIDATE
complete_R1R1_implementation_head = null
candidate_ready = false
external_acceptance = false
```

结论：

```text
REMOTE_FAILURE_PUBLICATION_GOVERNANCE = PASS
```

---

## 2. R1R1 实际执行到哪里

诊断提交 `d2514c29...` 新增：

```text
src/workbench_analysis/fep_e5/canonical_identity.py
tests/fep_e5/test_e5_canonical_identity.py
scripts/run_fep_e5_r1r1_identity_gate.py
reports/fep_e5_r1r1/*
```

实际执行结果：

```text
logical historical observations = 205
exact canonical authority bindings supplied = 0
affected observations = 205
canonical rows written = 0
```

所有 205 条都保留在 conflict evidence 中，没有 silent drop。

正式状态：

```text
CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING
```

---

## 3. 这次 blocker 不是“数据库里少导了一批数据”

R1R1 诊断同时检查：

### E1 fresh fixture

```text
v4.publications = 0
fep.observations = 0
fep.observation_revisions = 0
fep.snapshots = 0
```

### E1 upgrade fixture

同样：

```text
v4.publications = 0
canonical fep facts = 0
```

### 项目配置 runtime authority

成功连接后：

```text
v4.publications exists
row count = 0
fep.observations absent in inspected runtime
```

因此问题不是：

```text
“某个 publication 表里有历史数据，Codex 没查到”
```

当前正式证据恰恰说明：

```text
项目从未为 2024-07 ~ 2026-09 的历史 replay
建立过逐日 canonical v4.publications 历史链
```

---

## 4. E2 历史数据的真实证据等级

E2 已接受历史数据合同：

```text
config/fep_e2_historical_dataset_contract_v1.json
```

明确声明：

```text
evidence_origin = RECONSTRUCTED_CORRECTED
execution_mode = HISTORICAL_SIMULATION
AS_RECORDED = false
FIRST_OBSERVED = false
REAL_OOS = false
production = false
shadow = false
```

并且明确限制：

```text
historical first availability NOT_PROVEN
```

历史数据来自冻结的真实数据/代码/参数组合：

```text
calendar
historical universe
adjusted canonical daily
dated trading status
identity projection
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
owner runtime code
parameter sets
```

所以这些历史 observation 有：

```text
真实 source lineage
真实 immutable artifact identity
真实 historical reconstruction
```

但没有：

```text
当年当日真实存在过的 canonical publication
```

这是两个不同概念。

---

## 5. E1 Schema 的核心合同矛盾

### 5.1 observation_revisions 允许 reconstructed evidence

`028_fep_schema_v1.sql`：

```text
evidence_origin IN (
  PIT_OBSERVED,
  RECONSTRUCTED_ASOF,
  RECONSTRUCTED_CORRECTED,
  DIAGNOSTIC_NON_PIT
)
```

这说明 FEP canonical schema 设计上明确希望支持历史 reconstruction。

### 5.2 但 publication_id 强制非空

同一个表又定义：

```text
publication_id text NOT NULL
REFERENCES v4.publications(publication_id)
```

### 5.3 validator 又要求 publication 在 T0 前已经 accepted

`030_fep_validation_cas_v1.sql`：

```text
p.status = ACCEPTED
p.trade_date = observation.trade_date
p.model_namespace_id = scope.namespace
p.accepted_at <= feature_cutoff <= slot_deadline
```

这套条件对真正 `PIT_OBSERVED` 是合理的。

但对于：

```text
RECONSTRUCTED_CORRECTED
```

如果 reconstruction 是 2026-10 才正式建立，而 observation trade_date 是 2024/2025/2026 早期，那么：

```text
真实 recorded_at / accepted_at
必然晚于历史 feature_cutoff
```

如果硬把 accepted_at 写成历史时间，就会变成：

```text
伪造 historical availability
```

这是禁止的。

---

## 6. prediction_runs 也存在同一结构问题

`028_fep_schema_v1.sql` 的：

```text
fep.prediction_runs
```

同样要求：

```text
publication_id text NOT NULL
REFERENCES v4.publications(publication_id)
```

因此即使只修：

```text
observation_revisions
```

后续 historical simulation prediction run 仍然会在同一个 authority 问题上再次阻断。

所以本次合同修复必须同时覆盖：

```text
observation authority
prediction run authority
```

不能只补 observation sidecar。

---

## 7. 为什么不能“补造一批历史 v4.publications”

`v4.publications` 不是普通日期索引表。

它带有：

```text
model_namespace
market_calendar session
prior-session publication chain
prior-session revision digest
state head
source manifest
computation identity
accepted_at
same-day revision lineage
append-only constraints
```

如果现在为 2024/2025 的 replay 人工插入一批 publication，并把：

```text
accepted_at
```

伪装成历史日期，只为了满足 FEP FK，那么它会错误表达：

> “这些 publication 在当时真实存在并被接受过。”

这与 E2 已冻结的：

```text
AS_RECORDED = false
```

直接冲突。

因此：

```text
HISTORICAL_PUBLICATION_BACKFILL_AS_IF_OBSERVED = FORBIDDEN
```

---

## 8. 正确修复方向

需要新增正式 canonical authority 类型：

```text
HISTORICAL_RECONSTRUCTION_AUTHORITY
```

它表达的不是：

```text
“历史 T0 当时已经发布”
```

而是：

```text
“在当前时间，对历史 T0 使用一组冻结、可复核、
无未来价格路径泄漏的真实历史输入进行重建；
该重建的 source/artifact/code/parameter identity 被正式登记。”
```

核心语义必须分开：

```text
PIT_OBSERVED
→ CANONICAL_PUBLICATION authority

RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED
→ HISTORICAL_RECONSTRUCTION authority
```

绝不能再共用同一个 `accepted_at <= feature_cutoff` 语义。

---

## 9. 推荐 schema 方向

下一轮应使用新的 additive migration，而不是修改 028~031 历史文件。

建议新增 canonical 表：

```text
fep.reconstruction_authorities
```

至少包含：

```text
authority_id
authority_contract_id
trade_date
scope_id / namespace_id
evidence_origin
execution_mode
source_manifest
source_manifest_digest
accepted_head_identity
feature_contract_id
reconstructed_at
availability_claim
as_recorded
first_observed
real_oos
```

其中当前 E2 historical replay 只能：

```text
evidence_origin = RECONSTRUCTED_CORRECTED
execution_mode = REPLAY / HISTORICAL_SIMULATION semantic
availability_claim = NOT_HISTORICALLY_OBSERVED
as_recorded = false
first_observed = false
real_oos = false
```

并绑定 E2 已冻结：

```text
calendar
universe
adjustment_identity
status
identity
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
owner runtimes
parameter sets
dataset/window/population/feature gates
```

---

## 10. observation_revision 必须改成 authority union

下一 migration 应使：

```text
fep.observation_revisions
```

支持二选一：

### 路径 A

```text
authority_kind = CANONICAL_PUBLICATION
publication_id != null
reconstruction_authority_id = null
```

只允许：

```text
PIT_OBSERVED
```

并继续执行现有严格：

```text
accepted_at <= feature_cutoff
```

### 路径 B

```text
authority_kind = HISTORICAL_RECONSTRUCTION
publication_id = null
reconstruction_authority_id != null
```

只允许：

```text
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
```

且：

```text
execution_mode = REPLAY
FIRST_OBSERVED = false
REAL_OOS = false
```

不得弱化路径 A。

---

## 11. prediction_runs 必须同步改

同理：

```text
fep.prediction_runs
```

需要 formal authority union：

```text
CANONICAL_PUBLICATION
or
HISTORICAL_RECONSTRUCTION
```

历史 E5 projection：

```text
prediction_evidence = HISTORICAL_SIMULATION
```

只能绑定：

```text
HISTORICAL_RECONSTRUCTION
```

未来真实 same-day inference：

```text
FIRST_OBSERVED
```

仍必须绑定：

```text
CANONICAL_PUBLICATION
```

禁止 historical authority 获得：

```text
FIRST_OBSERVED
REAL_OOS
production
live Priority
```

---

## 12. B03 合同冲突也已确认

当前：

```text
fep.permission_keys.model_role
CHECK(model_role='CHAMPION')
```

但 E5 当前合法状态：

```text
E2 role = BASELINE
E3/E4 role = CHALLENGER
CHAMPION = NONE
```

而 `030` 的注释其实已经明确：

```text
SHADOW_INFERENCE may compute set members
```

因此 schema 与自身注释不一致。

下一 additive migration 应窄化为：

```text
SHADOW_INFERENCE:
  model_role ∈ exact existing model_set_member role

DESCRIPTIVE_DISPLAY:
  CHAMPION only

MODEL_DISPLAY:
  CHAMPION only

PRIORITY_USE:
  CHAMPION only
```

并保留 exact FK。

---

## 13. 本轮诊断测试评价

R1R1 diagnostic：

```text
targeted = 313 passed / 1 skipped / 0 failed
upgrade identity = 7 passed
scoped = 2672 passed / 4 skipped / 52 known debt / 0 introduced
```

新增真实 PostgreSQL rejection 证明：

```text
fake publication rejected
wrong-date publication rejected
digest-as-publication rejected
missing authority retains full population
```

这些测试是有价值的。

但它们只能证明：

```text
fail-closed guard 正确
```

不能关闭：

```text
B01/B02/B03
```

当前 evidence 中把下游 canonical receipts 标成：

```text
NOT_APPLICABLE
not_a_pass = true
```

也是正确处理。

---

## 14. Protected State

当前没有：

```text
028~031 rewrite
canonical fake rows
Priority V1 mutation
accepted head mutation
new training
new label resolution
TDX mutation
production/display/priority grant
```

因此：

```text
PROTECTED_STATE = PASS
```

---

## 15. 最终状态

```text
V4_15E5_R1R1A_EXTERNAL_AUDIT =
PASS_FAIL_CLOSED_BLOCKED_CONTRACT_DESIGN_GAP

REMOTE_FAILURE_EVIDENCE =
PASS_EXACT_VISIBLE

CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING =
CONFIRMED_REAL_DESIGN_GAP

E1_RECONSTRUCTED_AUTHORITY_MODEL =
INCOMPLETE

E5_B01 =
OPEN_BLOCKER

E5_B02 =
OPEN_BLOCKER_CONTRACT_REPAIR_REQUIRED

E5_B03 =
OPEN_BLOCKER_NARROW_SCHEMA_REPAIR_REQUIRED

V4_16_FROM_THIS_BRANCH =
NOT_GRANTED

NEXT =
ISSUE_R1R1B_HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT_REPAIR_AND_CANONICAL_RESUME
```

这次不应该让 Codex 继续“找 publication”。

下一轮要正式修：

```text
canonical historical reconstruction authority
+
observation authority union
+
prediction-run authority union
+
narrow SHADOW model-role repair
```

然后再恢复原 R1R1 的 B01/B02/B03 canonical integration。

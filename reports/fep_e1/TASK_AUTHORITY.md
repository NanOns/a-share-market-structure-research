# V4-15E1｜FEP Dataset & PostgreSQL Foundation Implementation Task R1｜2026-10-05

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜未来条件期望与研究优先级层  
> 阶段：V4-15E1  
> 任务性质：正式工程实施任务卡 / 第一阶段  
> 执行分支：`codex/v4-system-reform`  
> 执行基线：`ce44488ae972cf0f4d9f4af34cb03d81be436387`  
> 本阶段目标状态：`DATASET_ENGINEERING_PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT`  
> 生产权限：全部保持 `UNGRANTED`

---

# 0. 唯一任务

本轮只执行：

```text
V4-15E1
FEP Dataset + PostgreSQL Foundation
```

把已经冻结并通过外部设计验收的 FEP R2，从“设计 DDL / 文档合同”推进为：

```text
真实 PostgreSQL migration
+
真实 FK / Trigger / Role / CAS
+
Observation / Feature Snapshot
+
V4-15 Label Source Adapter
+
Per-Fold As-Of Dataset
+
完整 denominator / revision / PIT 证据链
+
可重复工程验收
```

本轮不是模型阶段。

本轮完成后允许宣称的最高状态只有：

```text
FEP_DATASET_ENGINEERING = PASS_LOCAL
FEP_DATABASE_ENGINEERING = PASS_LOCAL
FEP_E1 = PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

本轮严禁宣称：

```text
MODEL_PASS
MODEL_DISPLAY
CALIBRATION_PASS
OOS_EFFECTIVENESS
PRIORITY_V2_EFFECTIVENESS
PRIORITY_USE
FEP_PRODUCTION_PASS
个股上涨概率
个股收益预测有效
```

---

# 1. 正式设计权威

本轮必须绑定以下冻结设计，不得自行重新设计 FEP。

## 1.1 主合同

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
```

正式 SHA256：

```text
203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205
```

仓库正式设计权威路径当前已由 V4-15 Contract Package 绑定：

```text
docs/evidence/
A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md
```

## 1.2 FEP R2 独立模块

```text
DA-MSR-V4.2.2-FEP-R2
```

设计 SHA256：

```text
f01ac9c550a71b8edb73436969e39172f6809404df9e19ffbfff2306c9456014
```

## 1.3 FEP R2 Schema

```text
FEP_SCHEMA_DESIGN_V2
```

设计 SHA256：

```text
536ee33f89e38b427b06ceffcb5e760964b0b4b64829b2a54d91c172f252a138
```

设计统计：

```text
33 tables
32 append-only fact/history guards
1 controlled mutable head table = deployment_heads
7 reference PL/pgSQL functions
```

## 1.4 外部设计验收

正式外部结论：

```text
EXTERNAL_DESIGN_ACCEPTANCE_PASS
```

文档：

```text
V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md
```

该结论只解除“可以开始 E1 实现”的设计门，不代表 implementation/database/model/priority 已通过。

---

# 2. 当前正式上游状态

当前仓库 HEAD：

```text
ce44488ae972cf0f4d9f4af34cb03d81be436387
```

当前 Stage Head：

```text
V4_00_TO_V4_15_ACCEPTED
```

V4-15 Accepted Head：

```text
data/v4/V4_15_ACCEPTED_HEAD.json

sha256 =
a3480dfc7e1d7b68656ea78e6ed68eb93c3381db9c099b8a6e0cb3a84c9d1d4d
```

V4-15 当前允许 FEP E1 消费的工程接口包括：

```text
FORWARD_EVALUATION_PROJECTION = ENGINEERING_ACCEPTED
RADAR_COHORT_RUNTIME = ENGINEERING_ACCEPTED
SETTLEMENT_RUNTIME = ENGINEERING_ACCEPTED
REAL_ACCEPTED_SOURCE_T0_INTEGRATION = PASS_CAPABILITY_SCOPED
REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK = PASS_CAPABILITY_SCOPED
PERSISTED_E2E = ENGINEERING_ACCEPTED
INDEPENDENT_ORACLE = ENGINEERING_ACCEPTED
```

同时必须保留这些真实限制：

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

因此：

> E1 可以把正式 Adapter / Dataset / PostgreSQL 底座做完，但不能因为数据库里有表，就把当前 2026-09-30 数据写成已经成熟的 REAL training label。

---

# 3. 与主系统的隔离边界

FEP 是 V4-15 之后的独立支线。

必须保持：

```text
Core Facts
Profile
Seed
Sector
PREWATCH
State
Radar
Validation
Forward
PRIORITY_V1
```

现有行为不变。

本轮禁止：

```text
修改 Core eligibility
修改 Radar 候选集合
修改 Validation enrollment
覆盖 V4-15 settlement authority
替换 PRIORITY_V1
修改 V4_STAGE_ACCEPTED_HEAD
修改 V4_DATA_ACCEPTED_HEAD
创建 V4_16_ACCEPTED_HEAD
修改 DM01 R4 acceptance head
授予 Shadow / Focus / Production
```

FEP E1 失败必须：

```text
只停 FEP
不回滚 Core
不影响现有页面和排序
```

---

# 4. E1 实施原则

## 4.1 全结构安装，分能力启用

FEP R2 Schema 的 33 张表是统一关系合同。

E1 应将完整结构转换为正式 PostgreSQL migration，使 FK / trigger / role / CAS 能在真实数据库中验证。

但是：

```text
安装完整结构
!=
E2/E3/E4/E5 能力已实现
```

E1 只功能化：

```text
Observation
Observation Revision
Feature Snapshot
Feature Values
Label Source Binding
Label Revision
Dataset
Expected Denominator Ledger
Fold Cutoff
Per-Fold Label Selection
Dataset Rows
基础 Contract / Scope / Field / Target Registry
Prediction Slot 的无模型结构
Permission / Activation / Deployment Head 的数据库治理骨架
```

下列未来表可建结构但保持无生产数据 / NOT_ENABLED：

```text
training_runs
models
model_sets
model_set_members
prediction_runs
predictions
reports
priority_projection
priority_projection_grants
```

不得为了“表已创建”提前构造模型 artifact 或 Priority 结果。

---

# 5. Migration 实施

## 5.1 不硬编码 migration 序号

设计文档当时写的是：

```text
src/workbench_db/migrations/v4_postgres/001...018
```

这是 2026-09-30 的设计现场，不是 2026-10-05 的永久编号。

执行时必须：

1. 扫描当前仓库正式 PostgreSQL migration；
2. 找到下一可用序号；
3. 记录 discovery evidence；
4. 只能在当前序号之后新增 FEP migration；
5. 不允许覆盖、重命名、重排既有 migration。

禁止直接假设：

```text
019
```

仍然可用。

## 5.2 正式 migration

至少应拆出清晰职责：

```text
FEP schema/domain/tables/indexes
FEP append-only guards
FEP validation triggers/functions
FEP role/privilege/CAS governance
```

具体是否一张或多张 migration 按现有仓库 migration 规范决定，但必须：

```text
fresh install 可重建
升级 install 可执行
rollback/drill 可验证
顺序确定
无隐式手工步骤
```

---

# 6. PostgreSQL Schema 必须覆盖的 33 张表

必须与冻结 R2 设计逐表 reconcile，不得漏表或擅自改主键语义：

```text
01  fep.contracts
02  fep.scopes
03  fep.field_registry
04  fep.field_scope
05  fep.targets
06  fep.observations
07  fep.observation_revisions
08  fep.snapshots
09  fep.feature_values
10  fep.label_source_bindings
11  fep.label_revisions
12  fep.datasets
13  fep.dataset_eligibility_ledger
14  fep.dataset_fold_cutoffs
15  fep.dataset_fold_label_selection
16  fep.dataset_rows
17  fep.training_runs
18  fep.models
19  fep.model_sets
20  fep.model_set_members
21  fep.permission_keys
22  fep.activations
23  fep.deployment_heads
24  fep.deployment_change_receipts
25  fep.prediction_slots
26  fep.slot_model_bindings
27  fep.prediction_runs
28  fep.predictions
29  fep.slot_receipts
30  fep.acceptance_receipts
31  fep.reports
32  fep.priority_projection
33  fep.priority_projection_grants
```

如果现有 PostgreSQL/V4 schema 与 2026-09-30 设计发生真实接口变化：

```text
不要静默适配
不要删 FK
不要把强约束降成 JSON 自觉
```

必须登记：

```text
FEP_E1_CONTRACT_CONFLICT
```

只暂停受影响 capability，并在报告里给 exact schema difference。

---

# 7. Append-only 与受控 mutable head

冻结设计要求：

```text
32 张事实/历史表
= UPDATE / DELETE 禁止

deployment_heads
= 唯一受控 mutable current pointer
```

E1 必须真实验证：

```text
UPDATE immutable table → FEP_APPEND_ONLY
DELETE immutable table → FEP_APPEND_ONLY
```

未来 migration 新增历史/事实表时：

```text
必须显式新增 guard
```

禁止靠一次：

```text
pg_tables loop
```

假装未来表会自动受保护。

必须有 table-inventory test：

```text
all fep tables
minus deployment_heads
==
all immutable-guarded tables
```

任何漏表：

```text
E1 BLOCKED
```

---

# 8. Database Role 与权限

E1 必须建立并验证最小权限角色。

至少区分：

```text
FEP schema owner / migration role
FEP application reader/writer
FEP deployment executor
read-only audit/test role
```

应用角色不得：

```text
直接 UPDATE/DELETE deployment_heads
直接 UPDATE/DELETE append-only fact/history
修改 trigger/function
修改 contract registry 历史
```

`fep.cas_deploy(...)` 必须：

```text
SECURITY DEFINER
固定 search_path = pg_catalog,fep
PUBLIC 无 EXECUTE
只有 sealed deployer role 可 EXECUTE
dedicated trusted owner
```

必须验证：

```text
search_path hijack
恶意同名函数/table
普通应用角色直接 DML
PUBLIC execute
owner/role escalation
```

全部 fail-closed。

---

# 9. CAS Deployment Head 数据库验收

本轮不授予任何生产 deployment，但数据库 CAS 治理必须真实工作。

Head key：

```text
(scope_id,
 capability,
 target_id,
 horizon,
 feature_contract_id)
```

注意：

```text
model_set_id
不是 head key
而是 head payload
```

必须验证：

### Initial

```text
expected_version = 0
expected_prior = null
ALLOW
→ head_version = 1
```

### Replacement

```text
expected_version = v
expected_prior_activation = current
→ version = v + 1
```

### Concurrent CAS

两个事务读取相同 version：

```text
只能一个成功
另一个 FEP_CAS_CONFLICT
```

### Transaction Rollback

CAS 冲突时：

```text
activation
deployment_change_receipt
deployment_head
```

必须同事务全部 rollback。

### Idempotency

同 `request_id` 且全参数一致：

```text
返回原 receipt/version
```

同 `request_id` 但任一参数变化：

```text
FEP_IDEMPOTENCY_CONFLICT
```

必须覆盖 `NULL` 参数反例，避免 SQL UNKNOWN 绕过。

### REVOKE

已有 head：

```text
只能撤销当前 grant_id
```

不得拿另一个 model_set/grant 伪造撤销。

### Future Activation

禁止提前把未来 activation 占到 current head。

---

# 10. Observation Contract

E1 第一正式数据 scope：

```text
FEP_STOCK_ENTRY_CORE
```

其他 scope 可以登记合同，但默认：

```text
NOT_ENABLED
```

不得借 E1 扩权。

Observation 身份必须符合：

```text
ENTRY:
逻辑事件唯一

DAILY_LANDMARK:
实体 × market day 唯一
```

不得把：

```text
UI 行
publication revision
重复 Radar 展示
```

当作新 observation。

必须有：

```text
observation_id
scope_id
entity_id
trade_date
signal_key
episode_key
slot_deadline
core_signal_contract_id
```

并验证：

```text
duplicate logical observation
wrong entity/scope
wrong trade_date
wrong signal identity
```

均不能静默插入。

---

# 11. Observation Revision 与 Feature Snapshot

必须实现：

```text
accepted publication/revision
→ observation_revision
→ immutable dependency manifest
→ feature snapshot
→ field values
```

规则：

```text
snapshot_created_at
可以晚于 T0

但 feature_cutoff
不能晚于该 observation 的正式 cutoff
```

不能：

```text
因为今天才重建旧数据
→ 就声称它是当时 FIRST_OBSERVED
```

必须区分：

```text
evidence_origin:
PIT_OBSERVED
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
DIAGNOSTIC_NON_PIT

execution_mode:
SHADOW
PRODUCTION
REPLAY
```

E1 只建立工程能力，不允许把 reconstructed historical snapshot 升级成 PIT_OBSERVED。

---

# 12. Feature Registry

生成正式机器 registry，例如：

```text
config/fep_feature_registry_v1.json
config/fep_scope_registry_v1.json
```

不得从旧英文别名猜字段。

每个 feature row 至少冻结：

```text
field_name
producer
source_field / field_path
data_type
unit
nullable
required
window contract
quality allowlist
availability rule
allowed scopes
consumer contract
```

来源只能是当前 accepted producer/registry。

当前无法证明存在的字段必须：

```text
NOT_IMPLEMENTED
```

不能为了让 R0 feature 清单“完整”临时发明字段。

全部 feature mapping 未逐字段验证前：

```text
FEP_E1_DATASET_COMPLETE = false
```

---

# 13. Feature Snapshot 必须 exact-bind

Feature Snapshot 必须保存并 digest：

```text
publication / accepted head identity
algorithm contract
parameter contract
calendar
universe
membership（需要时）
adjustment basis
state/event revision（需要时）
enrichment revision 或明确 NONE
feature contract
actual consumed dependency manifest
```

禁止：

```text
只存 latest path
运行时重新解析旧 observation
同 publication 不同 enrichment revision 合并成同 snapshot
```

相同语义输入：

```text
logical digest 稳定
```

非语义字段：

```text
created_at
run_id
```

不能影响 logical digest。

---

# 14. Label Source Adapter

E1 必须实现：

```text
V4-15 settlement authority
→ FEP label_source_binding
→ FEP label_revision
```

FEP 自己不得：

```text
重新计算 forward price
自己补 benchmark
自己重新结算 MFE/MAE
绕过 V4-15 quality
```

`label_source_bindings` 至少记录：

```text
authority_contract_id
upstream_key
upstream_revision
source_digest
label_event_end
source_fact_available_at
label_training_mature_at
label_revision_available_at
created_at
```

上游 exact row 不存在或 digest/revision 不匹配：

```text
不得创建 accepted training label
```

---

# 15. 当前真实数据的特殊边界

当前 V4-15 明确：

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
```

因此针对当前真实 accepted 2026-09-30 链：

允许：

```text
创建 observation/snapshot 工程 evidence
创建 expected-target denominator
创建 PENDING / UNKNOWN label ledger
验证 source adapter reachability
```

禁止：

```text
把 T+1/3/5/10/20 标成已真实成熟
training_allowed = true（没有正式 maturity evidence 时）
REAL_MATURED label PASS
```

工程 synthetic fixture 可以覆盖 mature label 正反例，但必须：

```text
ENGINEERING_FIXTURE
!=
REAL_ACCEPTED_EVIDENCE
```

---

# 16. 三时间链

E1 必须真实实现并测试三条独立时间：

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

禁止合并成：

```text
available_at
```

必须能够表达：

```text
T+2 原事实已经可知
T+5 完整 N-window 才训练成熟
T+6 修订版本才正式进入系统
```

Fold cutoff 为 T+3：

```text
不可训练
```

Fold cutoff 为 T+5，但 revision 到 T+6：

```text
仍不可训练
```

Fold cutoff ≥ 三者：

```text
才可能 ELIGIBLE
```

后到 revision 不得倒灌旧 fold。

---

# 17. Dataset Complete Denominator

`dataset_eligibility_ledger` 必须先登记：

```text
dataset
observation
target
expected / ineligible / pending / missing
reason
```

它只保存完整 expected denominator。

禁止在该全局 ledger 保存：

```text
selected_label_revision
```

因为 revision 选择必须是：

```text
per fold
per partition
as-of
```

即使 label 不成熟、缺失、RIGHT_CENSORED、UNKNOWN：

```text
仍保留 denominator row
```

禁止 complete-case 删除后假装样本从未存在。

---

# 18. Per-Fold / Partition PIT Dataset

必须实现：

```text
dataset_fold_cutoffs
dataset_fold_label_selection
dataset_rows
```

Partition：

```text
FIT
TUNE
CALIBRATION
OUTER_TEST
```

每个 partition 独立冻结：

```text
fold_dataset_cutoff
phase_started_at
```

`dataset_fold_label_selection` 按：

```text
dataset
fold
partition
observation
target
```

冻结：

```text
selected_label_revision
selected_label_digest
eligibility
selection_reason
```

`dataset_rows` 必须复合 FK exact-bind：

```text
dataset
fold
partition
observation
target
revision
digest
```

---

# 19. 必做 PIT Revision 反例

必须实际证明：

```text
label r1 available at T10
label r2 available at T20

Fold A cutoff = T10
→ 只能选 r1

Fold B cutoff = T20
→ 可以选 r2
```

强制反例：

```text
Fold A 偷读 r2
→ BLOCK
```

并且 dataset overall digest 必须冻结：

```text
all fold cutoffs
all label selections
full denominator
```

不得仅 digest 最终 rows。

---

# 20. Fold / Partition Leakage Guard

同一 fold 内：

```text
FIT
TUNE
CALIBRATION
OUTER_TEST
```

禁止共享：

```text
同 observation
同 trade_date 横截面
同 scope+entity+episode
```

episode 身份：

```text
(scope_id, entity_id, episode_key)
```

不同股票碰巧有相同局部 episode_key：

```text
不应误判为同 episode
```

必须测试：

```text
same observation overlap → BLOCK
same market date overlap → BLOCK
same entity episode overlap → BLOCK
different entity same episode string → ALLOW
```

E1 只验证数据库/接受服务层的基本隔离。

完整 purge/embargo 策略参数仍属于 E3，不得提前拍阈值。

---

# 21. Dataset Row Validation

只有：

```text
dataset_fold_label_selection.eligibility = ELIGIBLE
```

才允许进入 `dataset_rows`。

必须同时验证：

```text
dataset scope
feature_contract
observation scope
snapshot observation
snapshot feature_contract
target scope
target horizon
selected revision
selected digest
```

故意串：

```text
entity
scope
target
horizon
feature_contract
snapshot
revision
digest
```

任一项必须失败。

---

# 22. Target Registry

创建正式：

```text
config/fep_target_registry_v1.json
```

目标定义以 R2 为准。

可以登记：

```text
ABS_RETURN_N
POSITIVE_ABS_N
MARKET_EXCESS_N
POSITIVE_MARKET_EXCESS_N
SECTOR_EXCESS_N
MFE_N
MAE_N
PATH_MDD_CLOSE_N
MFE_ATR_N
MAE_ATR_N
PATH_MDD_ATR_N
FIRST_EXIT_PREWATCH_N
ANY_CONFIRM_N
ANY_INVALIDATE_N
ANY_EXPIRE_N
TREND_TRANSITION_N
```

`N ∈ {1,3,5,10,20}`。

但是 enable 状态必须尊重真实 capability。

下列设计目标仍：

```text
REGISTERED_NOT_ENABLED
```

除非另有正式机器合同和独立向量：

```text
BREAKOUT_SUCCESS/FAILED
TREND_ACCELERATE/FLATTEN/BREAK
RPS_CONTINUE/DECAY
breadth continuation
regime continuation
rotation continuation
```

E1 不得凭名称自动启用。

---

# 23. Prediction Slot Skeleton

E1 要建立 slot 数据结构，因为 FIRST_OBSERVED 语义依赖它。

允许创建：

```text
PLANNED
NO_ACTIVE_MODEL
```

slot。

不得为了填 FK 创建假 model。

无 active model：

```text
保留 slot / receipt
→ NO_ACTIVE_MODEL
```

而不是：

```text
删除 observation
或伪造 model row
```

slot selection 必须保持：

```text
selection_cutoff <= deadline
```

实际 model binding / inference 仍不属于 E1 正式能力。

---

# 24. Permission Skeleton

E1 建立但不授予正式能力：

```text
permission_keys
activations
deployment_heads
deployment_change_receipts
```

grant identity：

```text
scope_id
target_id
horizon
feature_contract_id
model_set_id
capability
```

capability：

```text
SHADOW_INFERENCE
DESCRIPTIVE_DISPLAY
MODEL_DISPLAY
PRIORITY_USE
```

本轮所有真实生产能力必须：

```text
UNGRANTED
```

可以用 isolated engineering fixtures 验证 CAS / grant exact identity。

禁止真实：

```text
MODEL_DISPLAY
PRIORITY_USE
```

---

# 25. FEP E1 参数冻结

创建：

```text
config/fep_policy_v1.json
```

E1 只允许冻结 E1 owner 的参数：

```text
observation scopes
slot deadline semantics
model selection cutoff semantics
sampling weight definition
CPU / memory / thread budget
batch size / runtime deadline
retention / rollback budget
```

无法从现有正式时序证明的值：

```text
UNSET
```

不得拍脑袋填“合理默认值”。

E2/E3/E5 参数保持：

```text
UNSET / OWNER_STAGE_NOT_REACHED
```

例如：

```text
minimum rows/dates/blocks
class support counts
missingness threshold
training window
retrain cadence
calibration method
OOD threshold
promotion effect threshold
Priority tuple
```

本轮不得提前优化这些数字。

---

# 26. PostgreSQL 实际验收环境

设计 SQL 的 `pglast` 解析通过不能代替 E1。

必须使用真实 PostgreSQL。

至少验证：

```text
migration apply
fresh DB bootstrap
upgrade-path bootstrap
FK
unique constraint
check constraint
PL/pgSQL execution
trigger
transaction rollback
concurrency
role/privilege
SECURITY DEFINER
fixed search_path
advisory lock
CAS
append-only guard
```

如果当前开发机 PostgreSQL 未配置：

不得用：

```text
SQLite
DuckDB
仅 SQL parser
mock database
```

替代并宣布 E1 PASS。

允许：

```text
Docker / isolated local PostgreSQL
```

前提是：

```text
版本明确
配置冻结
数据目录在项目允许目录
不占用户 C 盘临时空间
无生产凭据
```

---

# 27. Mandatory Negative / Counterfactual Matrix

至少覆盖以下正式向量。

## Schema / FK

```text
E1-01 wrong observation scope → BLOCK
E1-02 wrong target scope/horizon → BLOCK
E1-03 snapshot observation mismatch → BLOCK
E1-04 snapshot feature_contract mismatch → BLOCK
E1-05 label digest/revision mismatch → BLOCK
E1-06 dataset row points to different fold selection → BLOCK
```

## Time / PIT

```text
E1-07 source_fact_available_at > cutoff → BLOCK
E1-08 label_training_mature_at > cutoff + ELIGIBLE → BLOCK
E1-09 label_revision_available_at > cutoff → BLOCK
E1-10 early fold attempts late revision → BLOCK
E1-11 later fold legally uses newer revision → PASS
E1-12 reconstructed snapshot labeled PIT_OBSERVED → BLOCK
```

## Denominator

```text
E1-13 pending target absent from rows but present in denominator → PASS
E1-14 pending target silently absent from denominator → BLOCK
E1-15 global selected_label_revision in eligibility ledger → schema/contract BLOCK
```

## Fold isolation

```text
E1-16 same observation across partitions in one fold → BLOCK
E1-17 same trade_date across partitions in one fold → BLOCK
E1-18 same entity+episode across partitions → BLOCK
E1-19 different entities reuse same local episode string → PASS
```

## Append-only

```text
E1-20 immutable UPDATE → BLOCK
E1-21 immutable DELETE → BLOCK
E1-22 unexpected unguarded fact table inventory → BLOCK
```

## CAS

```text
E1-23 initial 0→1 ALLOW → PASS
E1-24 stale version concurrent CAS → exactly one PASS
E1-25 CAS conflict leaves no partial activation/receipt → PASS
E1-26 identical request_id replay → same receipt/readback
E1-27 request_id with changed args → IDEMPOTENCY_CONFLICT
E1-28 NULL CAS parameter → BLOCK
E1-29 fake REVOKE against non-current grant → BLOCK
E1-30 future activation takes head early → BLOCK
```

## Roles

```text
E1-31 PUBLIC execute cas_deploy → BLOCK
E1-32 application direct UPDATE deployment_heads → BLOCK
E1-33 malicious search_path shadow object → no privilege escape
```

## V4-15 label authority

```text
E1-34 FEP recomputes Forward label instead of exact binding → BLOCK
E1-35 upstream row/revision/digest missing → no training label
E1-36 current real horizon lacking maturity evidence → training_allowed=false
```

## Slot

```text
E1-37 duplicate prediction slot → BLOCK
E1-38 no active model → retained NO_ACTIVE_MODEL, no fake model
```

## Core isolation

```text
E1-39 E1 failure changes PRIORITY_V1 → BLOCK
E1-40 E1 migration changes existing V4 accepted data → BLOCK
```

---

# 28. Required Implementation Surfaces

Codex 必须先盘点当前仓库，再按实际结构落文件。

建议但不强制死路径：

```text
src/v4/expectancy/
  observation.py
  snapshots.py
  labels.py
  datasets.py
  contracts.py
  db.py

config/
  fep_scope_registry_v1.json
  fep_feature_registry_v1.json
  fep_target_registry_v1.json
  fep_policy_v1.json

src/workbench_db/migrations/v4_postgres/
  <next_available>_fep_*.sql

tests/fep/
  test_migration.py
  test_temporal.py
  test_dataset.py
  test_labels.py
  test_roles.py
  test_cas.py
  test_append_only.py
  test_v4_isolation.py
```

如果现有项目已有更合适正式模块路径：

```text
允许按项目规范落地
```

但报告必须给：

```text
design planned path
→ actual implementation path
```

映射。

禁止创建第二套平行数据库/第二套 V4 publications 体系。

---

# 29. Migration / DB Evidence

必须产生机器可读 evidence。

推荐：

```text
reports/fep_e1/
  ENTRY_BASELINE.json
  DESIGN_AUTHORITY_READBACK.json
  MIGRATION_DISCOVERY.json
  POSTGRES_ENVIRONMENT.json
  SCHEMA_INVENTORY.json
  FK_CONSTRAINT_GATE.json
  APPEND_ONLY_GUARD_GATE.json
  ROLE_PRIVILEGE_GATE.json
  SECURITY_DEFINER_GATE.json
  CAS_CONCURRENCY_GATE.json
  TRANSACTION_ROLLBACK_GATE.json
  V4_15_LABEL_ADAPTER_GATE.json
  THREE_TIME_CHAIN_GATE.json
  DATASET_DENOMINATOR_GATE.json
  FOLD_LABEL_SELECTION_GATE.json
  FOLD_PARTITION_ISOLATION_GATE.json
  FEATURE_REGISTRY_GATE.json
  SLOT_GATE.json
  NEGATIVE_MATRIX.json
  CORE_ISOLATION_GATE.json
  TARGETED_TEST_SUMMARY.json
  SCOPED_REGRESSION_SUMMARY.json
  FEP_E1_CANDIDATE_SEAL.json
  COMPLETION_REPORT.md
```

所有 JSON evidence 必须可独立 readback。

---

# 30. Database Proof Requirements

以下不能只写：

```text
PASS
```

必须保留原始可复核证据：

```text
PostgreSQL version
migration command
migration before/after schema
table inventory
constraint names
trigger inventory
role grants
function owner
function proconfig/search_path
transaction IDs / exception
CAS concurrent session result
before/after row counts
rollback readback
```

并至少保留一份：

```text
raw SQL/test log
```

禁止把 Python mock 返回值当 PostgreSQL 证据。

---

# 31. Determinism / Rebuild

至少做两套数据库验证：

## A. Fresh

```text
empty isolated database
→ existing V4 migrations
→ FEP migration
→ tests
```

## B. Upgrade

```text
current accepted V4 schema state
→ FEP migration
→ tests
```

要求：

```text
same FEP schema identity
same constraints
same trigger inventory
same policy/registry digest
```

Migration 不能依赖：

```text
人工先插某行
本地数据库遗留对象
开发者 shell history
未登记扩展
```

---

# 32. Core / FEP Failure Isolation

强制故障演练：

```text
FEP migration rollback
FEP snapshot failure
FEP label adapter failure
FEP dataset assembly failure
```

都必须证明：

```text
Core database readable
V4 accepted heads unchanged
PRIORITY_V1 unchanged
Radar candidate set unchanged
Validation enrollment unchanged
Forward source unchanged
```

FEP 不允许变成 Core 事务前置门。

---

# 33. Existing Accepted Bytes Protection

至少保护：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_15_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json
```

以及所有当前 FEP 上游 owner Accepted Head。

本轮：

```text
不得修改其 bytes
```

如为测试需要：

```text
必须复制到 isolated fixture
```

不能直接改正式 accepted object。

---

# 34. Resource Boundary

用户当前机器允许较高资源使用，但 E1 是数据库工程，不需要无意义拉满。

规则：

```text
不使用 C 盘大规模临时目录
临时数据库 / test data 优先 E:/F:/项目工作盘
不写 TDX 原始目录
不重新下载全市场数据
不启动模型训练
不启动 tree search
```

CPU/内存/并发参数需记录到 FEP_POLICY_V1。

如果真实 PostgreSQL integration test 使用 Docker：

```text
镜像/tag
volume
port
locale
timezone
PostgreSQL major version
```

必须冻结到 evidence。

---

# 35. E1 不以样本数量为阻塞

当前真实样本/成熟 label 不足：

```text
不阻塞 E1 数据工程验收
```

E1 验收的是：

```text
数据合同
数据库结构
时序边界
revision选择
PIT防泄漏
权限/CAS
adapter
重建能力
```

不是：

```text
统计显著性
模型收益
预测准确率
```

因此禁止为了让 E1 “看起来有结果”：

```text
降低 maturity gate
伪造真实 label
把 reconstructed 当 PIT
把 synthetic 当 real
```

---

# 36. Regression

除了 FEP E1 targeted tests，必须执行与修改面相关的既有测试。

至少覆盖：

```text
PostgreSQL migration framework
v4 publications / namespace contracts
V4-15 settlement / forward projection
V4-15 accepted input
DM01/Data Head protected-state readback
Priority V1 / V4-09 isolation
```

如果仓库全量测试成本可接受：

```text
执行当前主 scoped regression
```

必须报告：

```text
baseline failures
current failures
introduced failures
resolved failures
```

禁止单看 `pytest exit_code != 0` 就把既有债务算成本轮失败；
也禁止把新增失败包装成既有债务。

---

# 37. E1 Local Acceptance Matrix

必须逐项给：

```text
PASS / FAIL / NOT_VERIFIABLE
```

至少：

```text
E1-A01  Design authority exact binding
E1-A02  Migration sequence discovery
E1-A03  Real PostgreSQL fresh migration
E1-A04  Real PostgreSQL upgrade migration
E1-A05  33-table schema inventory
E1-A06  32 append-only guards + controlled deployment_heads
E1-A07  FK / unique / check integrity
E1-A08  DB roles / least privilege
E1-A09  SECURITY DEFINER / fixed search_path
E1-A10  CAS initial/update/concurrency/idempotency/rollback
E1-A11  Observation identity/revision
E1-A12  Feature registry exact mapping
E1-A13  Feature snapshot dependency manifest
E1-A14  V4-15 exact label-source adapter
E1-A15  Three-time-chain semantics
E1-A16  Complete denominator ledger
E1-A17  Per-fold label revision selection
E1-A18  Fold/partition leakage guards
E1-A19  Dataset-row exact FK identity
E1-A20  Pending/UNKNOWN/censored preservation
E1-A21  Planned slot / no-active-model semantics
E1-A22  Permission skeleton no production grant
E1-A23  Existing V4 accepted bytes unchanged
E1-A24  Core failure isolation
E1-A25  Deterministic rebuild/readback
E1-A26  Negative matrix complete
E1-A27  Targeted tests
E1-A28  Scoped regression no new failures
E1-A29  Evidence completeness
E1-A30  Production/Model/Priority permissions remain false
```

任一以下项 FAIL：

```text
A03/A04/A05/A06/A07/A08/A09/A10
A14/A15/A16/A17/A18/A19
A23/A24/A30
```

则：

```text
E1 BLOCKED
```

---

# 38. Local Exit Status

只有全部 CORE E1 gates 通过，才允许输出：

```text
V4_15E1_FEP_LOCAL_IMPLEMENTATION =
PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

FEP_DATABASE_ENGINEERING =
PASS_LOCAL

FEP_DATASET_ENGINEERING =
PASS_LOCAL

FEP_STOCK_ENTRY_CORE_DATA_PATH =
ENGINEERING_READY

FEP_REAL_MATURED_LABEL_EVIDENCE =
NOT_GRANTED_UNLESS_SEPARATELY_PROVEN

FEP_MODEL_ENGINEERING =
NOT_STARTED

FEP_CALIBRATION =
NOT_STARTED

FEP_MODEL_DISPLAY =
UNGRANTED

FEP_PRIORITY_USE =
UNGRANTED

FEP_PRODUCTION =
UNGRANTED

NEXT =
STOP_WAIT_V4_15E1_INDEPENDENT_EXTERNAL_AUDIT
```

不得自行创建最终：

```text
FEP_E1_ACCEPTED_HEAD
```

除非后续独立外部验收明确授权 Promotion。

---

# 39. 如果失败

如果 E1 有失败：

```text
不要自动进入 E2
```

输出：

```text
V4_15E1_FEP_LOCAL_IMPLEMENTATION =
BLOCKED

BLOCKERS =
[...]

PASS_KEEP =
[...]

NEXT =
STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION
```

必须保留：

```text
成功部分
失败反例
原始日志
失败 DB 状态/rollback 证据
```

不得为了“阶段完成”降低数据库门。

---

# 40. Codex 执行纪律

本轮执行前先读取：

```text
AGENTS.md
当前 migration 规范
当前 PostgreSQL test fixture
V4-15 Accepted Head
FEP R2 main contract
FEP R2 module
FEP R2 schema
FEP external design acceptance
```

然后：

```text
先 inventory
再 migration
再 schema/roles
再 adapter
再 dataset
再 negatives
再 regression
再 candidate seal
```

禁止：

```text
边写边偷偷改合同
绕过 PostgreSQL 用 mock 冒充
因真实样本不足停止 E1
提前训练模型
提前做 Priority V2
把 E1 与 10 月 8 日 DM01/R25 等待链耦合
```

FEP E1 与主系统真实 Shadow 继续并行。

---

# 41. 本轮完成定义

E1 的“完成”不是：

```text
数据库里出现 fep schema
```

而是：

```text
设计身份冻结
+
真实 PostgreSQL schema 可重建
+
33表/32 guard/controlled head 一致
+
角色权限 fail-closed
+
CAS 原子与并发正确
+
Observation/Snapshot exact lineage
+
V4-15 Label Adapter 不重算
+
三时间链正确
+
完整 denominator
+
per-fold label revision PIT
+
partition leakage guard
+
大量故意串对象反例真实失败
+
Core 完全不受影响
+
无任何模型/排序生产权限
```

只有达到这个标准，才进入：

```text
V4-15E1 Independent External Audit
```

外部通过后再发布：

```text
V4-15E2
Conditional Statistics Baseline
```

# V4-15E5 R1R1｜Canonical FEP Integration Repair｜正式执行任务卡 R1

> 项目：大A市场结构研究系统 V4  
> 支线：FEP｜Forward Expectancy & Priority  
> 阶段：V4-15E5 R1R1  
> 任务性质：**定点修复 / Canonical Integration Repair**  
> 日期：2026-10-06  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> **唯一执行基线 HEAD**：`2bdca9dd87d210f778f4ec90aa4fbaa5f1708866`  
> 上一轮被审计实现：`51a1aab3fc9fe5bb390ec768dfd9514a1db6af54`  
> 上一轮实现 Parent：`adcfa36466e0c33626cc6ffc5fbd37cfd65e98bb`  
> 外部审计权威：`V4_15E5_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md`  
> 外部审计 SHA256：`202385558843367b756a193499ee308f17bd7c6651b5efc38d3025bf88aaa0d2`

---

# 0. 唯一任务结论

本轮不是新阶段开发，不是 E6，不是 V4-16，也不是重新训练模型。

本轮唯一目标：

```text
关闭 E5 外部审计留下的三个 canonical integration blocker：

E5-B01 CANONICAL_FEP_LEDGER_INTEGRATION
E5-B02 CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING
E5-B03 CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION
```

当前正式状态必须按上一轮外部审计继承：

```text
V4_15E5_FINAL_EXTERNAL_AUDIT = BLOCKED_R1_CANONICAL_FEP_INTEGRATION
E5 = BLOCKED_NOT_FORMALLY_ACCEPTED
FEP_E5_ENGINEERING_ACCEPTED = false
```

本轮完成代码、数据库、测试和证据后，也只能进入：

```text
CANDIDATE_EXTERNAL_AUDIT_REQUIRED
```

不得由 Codex 自行宣布：

```text
E5 = PASS_FINAL
FEP_E5_ENGINEERING_ACCEPTED = true
V4-16 allowed
production allowed
```

---

# 1. 本轮执行前必须重新读取的权威材料

执行前必须逐项读取并记录 digest / Git identity：

## 1.1 项目治理

```text
AGENTS.md
```

特别遵守：

```text
- TDX source read-only
- tests != release readiness
- stage task complete != external acceptance
- push != next-stage permission
- audit items 独立跟踪
```

## 1.2 E5 外部审计

仓库已归档：

```text
reports/fep_e5_external_audit_r1/
V4_15E5_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md
```

必须核对 exact bytes：

```text
sha256 = 202385558843367b756a193499ee308f17bd7c6651b5efc38d3025bf88aaa0d2
```

并读取：

```text
AUDIT_ITEM_DISPOSITIONS.json
AUDIT_RECONCILIATION_READBACK.json
EXTERNAL_AUDIT_ARCHIVE_SEAL.json
COMPLETION_REPORT.md
```

## 1.3 E5 R1 已通过的工程能力

```text
reports/fep_e5_r1/
```

重点：

```text
PROTOCOL_FREEZE.json
MODEL_CATALOG.json
MODEL_EVIDENCE_CLASS.json
EXACT_UPSTREAM_INFERENCE_READBACK.json
ENTRY_PROJECTION_READBACK.json
PREDICTION_BINDING_READBACK.json
PERMISSION_MATRIX.json
ROLLBACK_DRILL.json
NEGATIVE_MATRIX.json
TARGETED_SUMMARY.json
SCOPED_REGRESSION_SUMMARY.json
FEP_E5_R1_CANDIDATE_SEAL.json
```

## 1.4 Canonical FEP E1 数据库合同

必须读取当前已接受 canonical contract：

```text
src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql
src/workbench_db/migrations/v4_postgres/029_fep_append_only_v1.sql
src/workbench_db/migrations/v4_postgres/030_fep_validation_cas_v1.sql
src/workbench_db/migrations/v4_postgres/031_fep_roles_v1.sql
```

以及 E1 相关 contracts / tests / evidence。

---

# 2. 当前问题的精确定义

E5 R1 已证明：

```text
独立工程原型能够：
- 历史 ENTRY projection
- 3 个 model family 序列化推理
- Priority V2 shadow fixture
- exact permission key
- isolated CAS
- rollback
- denominator / OOD / missing handling
- API no-overdisplay
```

但其正式持久化使用：

```text
fep_e5_engineering.*
```

而不是已经在 E1 建立的：

```text
fep.*
```

因此当前证明的是：

```text
旁路工程原型可工作
```

不是：

```text
canonical FEP contract 可工作
```

本轮只能修这个 gap。

---

# 3. 不得重做的已通过部分

以下能力直接继承，**不得因为修 canonical integration 再重新设计或重新调参**：

```text
Protocol Freeze
Model Evidence Class
E2 accepted conditional statistics artifact
E3 serialized interpretable model artifact
E4 serialized tree challenger artifact
Historical Serialized Inference Adapter
ENTRY / DAILY Isolation
Priority V2 Same-layer Shadow Logic
Denominator / Abstention Handling
OOD Handling
Risk-event Preservation
API No-overdisplay Rules
Rollback semantics
50-case Negative Matrix semantics
Targeted regression baseline
Scoped regression baseline
```

如果本轮为了 integration 修改这些逻辑，必须说明：

```text
WHY_REQUIRED_FOR_CANONICAL_BINDING
```

否则属于越权范围扩大。

---

# 4. 本轮绝对禁止事项

禁止：

```text
1. 新模型训练
2. 新超参数搜索
3. 新模型 cherry-pick
4. 新 Target 定义
5. 重新结算 / 重算 Label
6. 修改 E2/E3/E4 effectiveness verdict
7. 宣布 Champion
8. 伪造 Champion 只为满足 permission FK
9. 宣布 FIRST_OBSERVED
10. 宣布 REAL_OOS
11. 打开 MODEL_DISPLAY
12. 打开 PRIORITY_USE
13. 打开 REAL_DAILY_PRIORITY_SHADOW
14. 打开 FEP_PRODUCTION
15. 把 historical simulation 包装成真实盘后 Shadow
16. 修改 PRIORITY_V1 排序、eligibility、risk event
17. 修改 Core / Profile / State / Radar / Validation Cohort 主语义
18. 修改任何 Accepted Head
19. 修改 TDX 文件
20. 另建第三套 parallel FEP schema 规避 canonical contract
```

特别禁止：

```text
fep_e5_engineering_2
fep_e5_canonical_shadow
fep_r1r1_engineering
或任何等价平行 schema
```

`fep_e5_engineering.*` 可以保留为历史证据 / fixture，但：

```text
NON_AUTHORITY_ONLY
```

它不能再用于关闭 E5-B01/B02/B03。

---

# 5. Migration 治理硬规则

## 5.1 不得重写历史 migration

不得直接修改：

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
```

原因：

这些文件已经形成 E1 canonical contract 与历史验收证据。

如果本轮确认正式 schema 无法表达 E5 合法 engineering shadow 语义：

```text
先输出 CONTRACT_CONFLICT
再通过新的 additive migration 修复
```

## 5.2 新 migration 编号

执行前必须扫描：

```text
src/workbench_db/migrations/v4_postgres/
```

获取当前最高编号 / reservation。

不得预设下一个编号。

新 migration 必须：

```text
- additive
- backward-compatible
- 可 fresh build
- 可 upgrade build
- 不改变旧事实
- 不删除旧 FK / trigger / append-only 防线
```

---

# 6. Work Package A｜Canonical FEP Ledger Integration

目标：关闭：

```text
E5-B01 CANONICAL_FEP_LEDGER_INTEGRATION
```

## A1. 正式 ledger 必须使用 `fep.*`

Historical ENTRY projection 必须正式落入 / 经过：

```text
fep.prediction_slots
fep.slot_model_bindings
fep.prediction_runs
fep.predictions
fep.slot_receipts
```

需要 priority engineering fixture 时：

```text
fep.priority_projection
```

但由于：

```text
PRIORITY_USE = UNGRANTED
```

不得伪造正式 Priority permission；不得把 fixture priority projection 解释成 live research ranking。

## A2. 不得继续使用 payload-only parallel ledger 作为通过证据

R1R1 的 canonical persistence gate 必须证明：

```text
canonical_schema = fep
canonical_rows > 0
```

并能通过真实 FK / unique / trigger / append-only constraints。

以下状态不能算 PASS：

```text
fep.* = 0 rows
fep_e5_engineering.* = populated
```

## A3. Historical evidence semantics 必须保持

全部旧历史 projection：

```text
prediction_evidence = HISTORICAL_SIMULATION
FIRST_OBSERVED = false
REAL_OOS = false
```

不得因为写入 canonical tables 改写证据等级。

## A4. Preserve E5 R1 denominator

上一轮基准：

```text
Historical ENTRY observations = 205
3 model families
expected projection rows = 615
prediction_slots = 616
slot_model_bindings = 615
```

每 family：

```text
READY = 46
REJECTED_QUALITY = 159
```

本轮必须产生一个 exact reconciliation：

```text
E5_R1_LOGICAL_DENOMINATOR
vs
R1R1_CANONICAL_DENOMINATOR
```

任何：

```text
drop row
missing model slot deletion
OOD deletion
quality reject deletion
```

都属于 FAIL。

如果 canonical contract 正确要求将某些旧 engineering row 表达成不同的正式 row shape，可以改变物理行组织，但必须证明：

```text
logical population identical
prediction outputs identical
abstention/missing identities preserved
```

## A5. 不得重新训练或重新拟合

必须直接使用 E2/E3/E4 accepted serialized artifacts。

输出必须与上一轮 accepted engineering inference 在允许的序列化浮点容差内一致。

要求生成：

```text
CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION
```

---

# 7. Work Package B｜Canonical Observation / Snapshot / Publication Binding

目标：关闭：

```text
E5-B02 CANONICAL_OBSERVATION_SNAPSHOT_PUBLICATION_BINDING
```

## B1. 必须建立正式 identity chain

必须证明：

```text
historical source event
→ fep.observations
→ fep.observation_revisions
→ fep.snapshots
→ fep.targets
→ fep.models / fep.model_sets
→ fep.prediction_slots
→ fep.predictions
```

不是：

```text
artifact digest
→ 自定义 engineering snapshot id
→ 自定义 publication handle
```

## B2. Publication 必须是真实 canonical publication

`fep.observation_revisions.publication_id` 和 `fep.prediction_runs.publication_id` 必须引用：

```text
v4.publications.publication_id
```

且必须满足现有 trigger 语义：

```text
publication.status = ACCEPTED
publication.trade_date = observation.trade_date
publication.model_namespace_id = scope.namespace_id
publication.accepted_at <= feature_cutoff
feature_cutoff <= slot_deadline
```

禁止：

```text
- 把 E2 observation-row digest 填成 publication_id
- hash 一个 artifact 伪造 publication_id
- 创建与历史事实不对应的 accepted publication 只为过 FK
- 把 current accepted head 倒灌到历史 T0
```

## B3. Evidence Origin

历史修复允许合法使用：

```text
RECONSTRUCTED_ASOF
RECONSTRUCTED_CORRECTED
```

并使用：

```text
execution_mode = REPLAY
```

不得写：

```text
PIT_OBSERVED
```

除非可以证明原始 event 在 slot deadline 前真实第一次观察且满足全部 PIT 条件。

本轮默认不授予：

```text
FIRST_OBSERVED
```

## B4. Dependency Manifest 必须完整

每个 formal observation revision 必须正确绑定现有 contract 所要求的 dependency：

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

不得用：

```text
UNKNOWN-but-pass
CURRENT
LATEST
TODAY
```

替代历史 exact identity。

## B5. Snapshot 必须通过 canonical feature contract

必须证明：

```text
snapshot.feature_contract_id
== observation_revision.dependency_manifest.feature_contract
```

并验证：

```text
feature_digest
quality_digest
feature values
source digests
```

与对应 E2/E3/E4 accepted inference 输入 exact-bind。

禁止：

```text
把 EXACT_MODEL_ROWS.jsonl.gz 整体 hash 直接冒充 canonical snapshot
```

可以将 accepted artifact 作为 source evidence，但最终 canonical snapshot 必须是数据库内正式 identity。

## B6. 无法合法映射时必须显式 BLOCK

如果 205 个历史 observation 中存在无法找到满足 exact canonical 条件的：

```text
v4.publications
namespace
trade_date
accepted_at
historical dependency identity
```

必须输出：

```text
CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING
```

并列出：

```text
affected observations
missing authority
why not inferable
required narrow repair
```

不得偷偷：

```text
create fake publication
bind to current publication
skip affected rows
```

---

# 8. Work Package C｜Canonical Permission / Deployment / CAS

目标：关闭：

```text
E5-B03 CANONICAL_PERMISSION_DEPLOYMENT_INTEGRATION
```

## C1. 当前 canonical conflict 必须先被正式确认

当前 `028_fep_schema_v1.sql`：

```text
fep.permission_keys.model_role DEFAULT 'CHAMPION'
CHECK(model_role='CHAMPION')
```

而当前 E5 model set：

```text
E2 = BASELINE
E3 = model / diagnostic
E4 = CHALLENGER
CHAMPION = NONE
```

上一轮 R1 的合法目标又只是：

```text
SHADOW_INFERENCE = ENGINEERING_ONLY
```

因此本轮必须首先生成：

```text
CONTRACT_CONFLICT_DISPOSITION.json
```

明确：

```text
是否现有 canonical contract 可以在不伪造 Champion 的情况下表达 diagnostic SHADOW_INFERENCE。
```

如果答案为否：

```text
CONTRACT_CONFLICT = CONFIRMED
```

然后执行 narrow additive repair。

## C2. 推荐的窄修复语义

本轮允许的目标语义是：

```text
SHADOW_INFERENCE
→ 允许 exact model-set member role 作为 diagnostic/engineering shadow 权限锚点
→ 不赋予任何 display / priority / production 权限

DESCRIPTIVE_DISPLAY
MODEL_DISPLAY
PRIORITY_USE
→ 仍必须绑定 CHAMPION
```

因此 additive schema repair 至少必须保证：

```text
capability = SHADOW_INFERENCE
    model_role ∈ accepted model_set_members.role

capability ∈ {DESCRIPTIVE_DISPLAY, MODEL_DISPLAY, PRIORITY_USE}
    model_role = CHAMPION
```

并继续保留：

```text
FOREIGN KEY -> fep.model_set_members(... exact role ...)
```

禁止：

```text
- 删除 model_role
- 删除 FK
- capability 不分层全部允许 BASELINE/CHALLENGER
- 为通过测试把 E2/E3/E4 强行改成 CHAMPION
```

如果实现团队认为上述语义与 E1 freeze 存在更深冲突：

```text
不得静默选择另一语义
必须 CONTRACT_CONFLICT + evidence
```

## C3. 必须使用 canonical CAS

本轮正式 proof 必须调用：

```text
fep.cas_deploy(...)
```

验证：

```text
ALLOW SHADOW_INFERENCE
REVOKE SHADOW_INFERENCE
idempotent replay
wrong expected version
wrong prior activation
cross-target
cross-horizon
cross-model-set
atomic rollback
concurrent initial CAS
```

不能再以：

```text
fep_e5_engineering custom CAS
```

作为通过证据。

## C4. 权限结果必须保持关闭

即使 canonical SHADOW_INFERENCE engineering permission 测试通过，也必须保持：

```text
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
DESCRIPTIVE_DISPLAY = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
```

注意：

```text
canonical engineering SHADOW_INFERENCE capability proof
!=
真实 Daily Shadow 授权
```

---

# 9. Role / Writer Boundary

当前 E1 `031_fep_roles_v1.sql` 明确：

```text
application role 不具备 E2+ prediction / permission 等正式写权限
```

本轮不得为了测试方便直接扩大 production application 权限。

允许的工程做法：

```text
- disposable PostgreSQL fixture
- schema-owner / migration-owner controlled fixture seeding
- accepted test bootstrap
```

如果 canonical E5 runtime 确实需要一个新的最小 non-login writer role：

```text
必须单独提出 CONTRACT_CONFLICT / ROLE_REPAIR
并通过 additive migration
只授予最小 INSERT / EXECUTE 权限
不得给 UPDATE/DELETE append-only fact tables
不得给 deployment_heads direct DML
```

除非证据证明必要，否则本轮不扩大 production writer surface。

---

# 10. Priority Projection 边界

本轮不开发新的 Priority 算法。

允许验证：

```text
accepted E5 R1 synthetic fixture
→ canonical prediction refs
→ canonical fep.priority_projection
```

必须继续保留：

```text
V1 rank identity
eligibility
risk events
full denominator
missing prediction
OOD
missing model
```

但：

```text
PRIORITY_USE = UNGRANTED
```

所以本轮不得通过任何方式生成 live Priority activation。

如果 `fep.priority_projection_grants` 的 contract 要求真正 PRIORITY_USE grant 才能作为正式可消费 priority：

```text
本轮只证明 projection storage / diagnostic linkage
不得插入伪 priority grant
```

---

# 11. API / Service Integration

如果修改：

```text
src/workbench_service/expectancy_service.py
```

或其他 FEP read service，则必须做到：

```text
canonical accepted path
→ read canonical fep.*
```

不得：

```text
canonical API 名称
→ 实际继续读 fep_e5_engineering.*
```

## API 默认输出仍然禁止

默认接口不得暴露：

```text
model probability axes
raw model diagnostics
priority projection
```

除非 exact diagnostic permission context 明确允许。

而本轮：

```text
MODEL_DISPLAY / PRIORITY_USE = UNGRANTED
```

所以默认对外仍应 fail closed / hide。

---

# 12. Fresh / Upgrade PostgreSQL 双路径

R1R1 必须至少在两种数据库状态验证：

```text
A. fresh database
B. upgrade database
```

两边都必须：

```text
- 安装完整 migration chain
- canonical schema identity 正确
- additive repair migration 正确
- canonical observation chain 可写可读
- canonical prediction chain 可写可读
- canonical SHADOW permission/CAS 可验证
- rollback 后历史事实不变
```

并输出：

```text
FRESH_DB_READBACK.json
UPGRADE_DB_READBACK.json
```

不得只在单一手工数据库测试。

---

# 13. Canonical vs Isolated Namespace 对账

必须显式输出：

```text
ISOLATED_NAMESPACE_NONAUTHORITY_READBACK.json
```

至少证明：

```text
fep_e5_engineering = historical fixture / non-authority
fep = canonical authority for R1R1 acceptance
```

R1R1 通过条件之一：

```text
E5-B01/B02/B03 的所有 PASS evidence 都来自 canonical fep.* 路径
```

不能来自 parallel namespace。

---

# 14. Required Negative / Red-Team Matrix

现有 E5 50-case matrix 语义保留，本轮至少新增/重跑以下 canonical integration cases。

## N01 Parallel Schema Authority

输入：

```text
尝试使用 fep_e5_engineering 作为 formal acceptance source
```

预期：

```text
FAIL / NON_AUTHORITY
```

## N02 Third Parallel Schema

输入：

```text
创建第三套 FEP ledger 作为 workaround
```

预期：

```text
FAIL
```

## N03 Fake Publication

输入：

```text
artifact digest / row digest 充当 publication_id
```

预期：

```text
FK/contract FAIL
```

## N04 Current Publication Backfill

输入：

```text
用 current accepted publication 替代 historical exact publication
```

预期：

```text
FAIL
```

## N05 Unresolved Historical Authority

输入：

```text
无法找到 historical canonical publication
```

预期：

```text
CONTRACT_CONFLICT
not silent skip
```

## N06 Historical -> FIRST_OBSERVED

预期：

```text
FAIL
```

## N07 Historical -> REAL_OOS

预期：

```text
FAIL
```

## N08 Champion Fabrication

输入：

```text
为了 permission FK 将 E2/E3/E4 任一改为 CHAMPION
```

预期：

```text
FAIL
```

## N09 Non-Champion MODEL_DISPLAY

预期：

```text
DB / contract FAIL
```

## N10 Non-Champion PRIORITY_USE

预期：

```text
DB / contract FAIL
```

## N11 Cross Target Grant

预期：FAIL。

## N12 Cross Horizon Grant

预期：FAIL。

## N13 Cross Model Set Grant

预期：FAIL。

## N14 Direct deployment_heads DML

预期：FAIL。

## N15 CAS Wrong Version

预期：FAIL + no partial state。

## N16 CAS Wrong Prior Activation

预期：FAIL + no partial state。

## N17 Concurrent Initial CAS

预期：

```text
exactly one accepted winner
other transaction conflict
```

## N18 CAS Idempotent Replay

预期：

```text
same request -> same receipt/version
```

## N19 Injected Failure After Activation / Before Head

预期：

```text
activation + receipt + head atomic rollback
```

## N20 Result-driven Rebind

预期：FAIL。

## N21 Current-head Rebuild

预期：FAIL。

## N22 Denominator Drop

预期：FAIL。

## N23 Missing Model Slot Deletion

预期：FAIL。

## N24 OOD Row Deletion

预期：FAIL。

## N25 Real Daily Activation

预期：FAIL / NOT_GRANTED。

## N26 Priority V1 Mutation

预期：FAIL。

## N27 New Training

预期：FAIL。

## N28 Relabel / New Outcome Resolution

预期：FAIL。

## N29 Protected Accepted Head Mutation

预期：FAIL。

## N30 TDX Write

预期：FAIL。

---

# 15. Regression 要求

## 15.1 Targeted

必须覆盖：

```text
FEP E1
FEP E2
FEP E3
FEP E4
FEP E5
R1R1 canonical integration tests
```

上一轮参考：

```text
306 passed
1 skipped
0 failed
```

本轮不能只继承数字，必须真正重跑与本轮修改相关的 targeted suite。

## 15.2 Scoped Regression

上一轮：

```text
2665 passed
4 skipped
52 failed
0 introduced active failures
```

52 个 known debt 必须继续披露。

允许：

```text
某些 known debt 因本轮合法修复自然消失
```

不允许：

```text
- deselect failing tests
- 改 expected failure 口径隐藏新增 failure
- 把新增 failure 并入 known debt
```

最终必须明确：

```text
introduced_failures = 0
```

否则 R1R1 不可进入外部验收。

---

# 16. GitHub CI Readback

上一轮存在非阻断 note：

```text
AUDIT_NOTE_E5_01
```

本轮生成 `GITHUB_CI_READBACK.json` 时：

必须指向：

```text
R1R1 implementation HEAD
```

不得只检查 baseline commit。

如果 GitHub 没有 CI：

```text
NO_RUN / NO_STATUS
```

如实记录，不能伪造 PASS。

---

# 17. Protected State

执行前后必须 exact readback：

```text
V4_STAGE_ACCEPTED_HEAD
V4_DATA_ACCEPTED_HEAD
V4_15_ACCEPTED_HEAD
V4_16_ACCEPTED_HEAD
PRIORITY_V1 owner files
Core/Profile/State/Radar/Cohort protected files
R25 state
TDX source
```

预期保持：

```text
V4-16 Accepted Head = NOT_CREATED
R25 = WAIT_ACCEPTED_DAILY_INPUT
TDX = UNTOUCHED
```

任何未经任务授权的 mutation：

```text
R1R1 = FAIL
```

---

# 18. 实现文件建议

Codex 可以自行确定最终路径，但建议新增独立 canonical adapter，而不是把 isolated ledger 混成双义实现。

建议结构：

```text
src/workbench_analysis/fep_e5/canonical_ledger.py
src/workbench_analysis/fep_e5/canonical_identity.py
src/workbench_analysis/fep_e5/canonical_permission.py
```

或等价清晰结构。

要求：

```text
canonical path 与 isolated fixture path 名称清楚
不得一个 Ledger class 根据隐式配置偷偷切 schema
```

如果新增 migration：

```text
src/workbench_db/migrations/v4_postgres/<NEXT>_fep_shadow_permission_contract_v*.sql
```

实际编号必须运行时扫描，不得照抄占位名。

---

# 19. 测试文件建议

至少增加：

```text
tests/fep_e5/test_e5_canonical_integration.py
```

如需拆分：

```text
test_e5_canonical_identity.py
test_e5_canonical_permission.py
test_e5_canonical_cas.py
```

必须调用真实 PostgreSQL fixture 验证 FK/trigger/CAS，不能只有 Python mock。

---

# 20. 本轮必须生成的证据包

统一目录：

```text
reports/fep_e5_r1r1/
```

至少包含：

```text
V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR_TASK_R1_20261006.md

BASELINE_AUTHORITY_BINDINGS.json
CONTRACT_CONFLICT_DISPOSITION.json
MIGRATION_ALLOCATION_READBACK.json
CANONICAL_SCHEMA_REPAIR_READBACK.json
CANONICAL_IDENTITY_MAPPING.json
CANONICAL_PUBLICATION_BINDING_READBACK.json
CANONICAL_LEDGER_READBACK.json
CANONICAL_PREDICTION_BINDING_READBACK.json
CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION.json
CANONICAL_PERMISSION_MATRIX.json
CANONICAL_CAS_CONCURRENCY.json
CANONICAL_CAS_IDEMPOTENCY.json
CANONICAL_ROLLBACK_DRILL.json
CANONICAL_PRIORITY_FIXTURE_READBACK.json
ISOLATED_NAMESPACE_NONAUTHORITY_READBACK.json
FRESH_DB_READBACK.json
UPGRADE_DB_READBACK.json
API_READBACK.json
NEGATIVE_MATRIX.json
PROTECTED_STATE_READBACK.json
GITHUB_CI_READBACK.json
CHANGED_FILE_LIST.json
FEP_E5_R1R1_CANDIDATE_SEAL.json
COMPLETION_REPORT.md

targeted.log
targeted.xml
TARGETED_SUMMARY.json

scoped.log
scoped.xml
SCOPED_REGRESSION_SUMMARY.json
```

如果某项不适用：

```text
不得删除该 evidence name
必须写 NOT_APPLICABLE + reason
```

---

# 21. Evidence 中必须包含的数据库读回

`CANONICAL_LEDGER_READBACK.json` 至少给出：

```text
schema = fep
physical table counts
logical observation denominator
logical slot denominator
bindings count
prediction count by model family
prediction evidence distribution
quality distribution
unknown/OOD distribution
slot receipt distribution
priority projection fixture count
```

必须同时明确：

```text
fep_e5_engineering_used_as_authority = false
```

---

# 22. Identity Mapping Evidence

`CANONICAL_IDENTITY_MAPPING.json` 至少逐 logical observation 提供：

```text
source observation identity
source evidence digest
fep.observation_id
scope_id
entity_id
trade_date
signal_key
observation_revision
publication_id
publication accepted_at
feature_cutoff
evidence_origin
execution_mode
snapshot_id
feature_contract_id
feature_digest
quality_digest
slot_id
target_id
horizon
model_set_id
model_id
prediction_id
```

如果文件过大可以：

```text
summary JSON + compressed exact rows
```

但必须有可独立复核的完整 population。

---

# 23. Permission Evidence

`CANONICAL_PERMISSION_MATRIX.json` 至少列出：

```text
scope_id
target_id
horizon
feature_contract_id
model_set_id
model_role
capability
grant_id
activation_id
head_version
action
status
```

并必须出现：

```text
SHADOW_INFERENCE = engineering proof only
DESCRIPTIVE_DISPLAY = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
FEP_PRODUCTION = UNGRANTED
```

---

# 24. Candidate Seal

`FEP_E5_R1R1_CANDIDATE_SEAL.json` 必须绑定：

```text
baseline HEAD
implementation HEAD
parent identity
task card digest
external audit digest
new migration digest (if any)
code bindings
test bindings
evidence bindings
protected state digest
canonical schema identity
```

并写死：

```text
external_acceptance = false
```

---

# 25. 成功状态

只有以下全部满足，才允许 Codex 写：

```text
V4_15E5_R1R1_CANONICAL_INTEGRATION = CANDIDATE_EXTERNAL_AUDIT_REQUIRED

E5_B01_CANONICAL_FEP_LEDGER = PASS_CANDIDATE
E5_B02_CANONICAL_IDENTITY_BINDING = PASS_CANDIDATE
E5_B03_CANONICAL_PERMISSION_DEPLOYMENT = PASS_CANDIDATE

PARALLEL_SCHEMA_AUTHORITY = false
FAKE_PUBLICATION = false
FAKE_CHAMPION = false
NEW_TRAINING = false
NEW_LABEL_RESOLUTION = false
PRIORITY_V1_MUTATION = false
PROTECTED_STATE_MUTATION = false
TDX_MUTATION = false

REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
DESCRIPTIVE_DISPLAY = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
CHAMPION = NONE
REAL_OOS = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1
```

注意：

```text
PASS_CANDIDATE
!=
PASS_FINAL
```

---

# 26. 合同冲突状态

如果 B2 或 C1 无法在不伪造身份 / 不破坏旧合同的情况下解决，必须使用：

```text
V4_15E5_R1R1_CANONICAL_INTEGRATION = BLOCKED_CONTRACT_CONFLICT
```

并明确：

```text
blocker_id
exact failing contract
exact missing authority
attempted legal path
why workaround would violate contract
smallest proposed repair
```

此时：

```text
NEXT = STOP_WAIT_EXTERNAL_CONTRACT_REPAIR
```

不得继续 E6 / V4-16。

---

# 27. 本轮外部验收关注点

Codex 完成并 push 后，独立外部审计会重点检查：

```text
1. 是否真的写入 canonical fep.*，而不是换名字的 parallel schema。
2. 205 historical observations 是否有真实 v4.publications / revision / snapshot 链。
3. 是否使用 current publication 或 digest 伪造 historical publication。
4. 是否保持 HISTORICAL_SIMULATION，不冒充 FIRST_OBSERVED / REAL_OOS。
5. 是否为了过 FK 偷偷制造 Champion。
6. additive permission repair 是否仅放宽 SHADOW_INFERENCE，display/priority 仍 champion-only。
7. 是否真实调用 fep.cas_deploy，包含并发、幂等、冲突、rollback。
8. fresh / upgrade 两条 migration path 是否都通过。
9. canonical output 是否与 E5 R1 accepted inference 一致。
10. denominator / abstention / OOD / missing 是否完整。
11. Priority V1 / protected heads / TDX 是否完全未动。
12. targeted/scoped 是否无新增 regression failure。
13. implementation HEAD 的 CI readback 是否指向正确 commit。
```

---

# 28. 执行顺序

严格按以下顺序：

```text
Step 1  Verify exact baseline HEAD = 2bdca9dd87d210f778f4ec90aa4fbaa5f1708866
Step 2  Read AGENTS + external audit + E5/E1 authority
Step 3  Freeze authority digests / protected state
Step 4  Diagnose canonical identity availability
Step 5  Diagnose CHAMPION-only permission conflict
Step 6  Emit CONTRACT_CONFLICT_DISPOSITION
Step 7  If needed, allocate additive migration number
Step 8  Implement canonical identity adapter
Step 9  Implement canonical ledger path
Step 10 Implement narrow canonical SHADOW permission repair
Step 11 Run fresh PostgreSQL fixture
Step 12 Run upgrade PostgreSQL fixture
Step 13 Reproduce historical E5 R1 projections through canonical path
Step 14 Reconcile outputs / denominator
Step 15 Validate canonical CAS + rollback + concurrency
Step 16 Validate priority fixture without PRIORITY_USE grant
Step 17 Run negative matrix
Step 18 Run targeted tests
Step 19 Run scoped regression
Step 20 Read back protected state
Step 21 Generate candidate seal + completion report
Step 22 Commit and push
Step 23 Read back GitHub implementation HEAD / CI status
Step 24 STOP
```

不得在 Step 24 后自行启动：

```text
V4-16
E6
real Daily shadow
production permission
```

---

# 29. 本轮单任务卡原则

本轮只有这一张 implementation task card。

不再额外并行下发：

```text
E6 task
V4-16 task
model promotion task
real Daily task
UI production task
```

原因：

三个 blocker 的共同根因都是：

```text
E5 未接入 E1 canonical fep.* contract
```

应先完成一个定点 integration repair，再独立验收。

---

# 30. 最终执行提示

本轮不是“把原型复制到正式表”。

真正验收目标是同时满足：

```text
canonical identity
+
canonical FK / trigger
+
canonical append-only semantics
+
canonical permission
+
canonical CAS
+
历史证据等级不升级
+
无伪造 authority
+
无权限扩张
+
无新模型实验
+
无主线污染
```

如果任何一项只能通过“造一个看起来能过测试的身份”解决：

```text
必须 BLOCK
```

不能为了让 E5 PASS 牺牲 FEP 的 PIT / identity / permission 治理。

---

# 31. 任务卡状态

```text
TASK_CARD = ISSUED
BASELINE = 2bdca9dd87d210f778f4ec90aa4fbaa5f1708866
AUTHORIZED_SCOPE = V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR_ONLY
NEXT_AFTER_IMPLEMENTATION = INDEPENDENT_EXTERNAL_AUDIT_R1R1
```

# V4.2.2 FEP R2 外部定点复审与设计冻结结论

> 文档编号：DA-MSR-V4.2.2-FEP-R2-EXTERNAL-REAUDIT  
> 日期：2026-09-30  
> 审计范围：FEP R2 模块、R2 Schema、REV4-FEP-R2 主合同、R2 Patch Disposition、完整 External Reaudit Package  
> 唯一外部设计结论：`EXTERNAL_DESIGN_ACCEPTANCE_PASS`  
> 实现状态：`IMPLEMENTATION_NOT_VERIFIED`  
> 生产权限：`UNGRANTED`

---

# 1. 最终结论

本轮对上一轮外部审计提出的：

- P1-01 / R2-01：逐 fold / partition label revision PIT
- P1-02 / R2-02：细粒度 permission
- P1-03 / R2-03：Deployment Head / CAS
- P1-04 / R2-04：三时间链
- P1-05 / R2-05：ENTRY 与 Daily Priority 隔离
- P2-01 / R2-06：原始多方审计证据包
- P2-02：Append-only future migration guard
- P2-03：主合同 Header 基线语义

进行了定点复审。

结果：

```text
P1-01 PASS
P1-02 PASS
P1-03 PASS
P1-04 PASS
P1-05 PASS

P2-01 PASS
P2-02 PASS
P2-03 PASS
```

因此上一轮：

```text
EXTERNAL_DESIGN_ACCEPTANCE_BLOCKED_PENDING_R2
```

正式解除。

当前唯一设计状态：

```text
EXTERNAL_DESIGN_ACCEPTANCE_PASS
```

允许：

```text
FEP R2
→ 冻结为当前正式设计基线
```

但本结论严格不等于：

```text
IMPLEMENTATION_PASS
DATABASE_PASS
MODEL_PASS
CALIBRATION_PASS
FORWARD_EFFECT_PASS
PRIORITY_PRODUCTION_PASS
```

这些权限仍全部为：

```text
UNGRANTED / NOT_VERIFIED
```

---

# 2. 输入身份与复审包完整性

本轮核对的正式 R2 文件：

```text
MAIN_REV4_FEP_R2
SHA256
203FF46075B4039D1E2D45D54FD76CE09509535739CD6AAEF4DC394DE1015205

FEP_MODULE_R2
SHA256
F01AC9C550A71B8EDB73436969E39172F6809404DF9E19FFBFFF2306C9456014

FEP_SCHEMA_R2
SHA256
536EE33F89E38B427B06CEFFCB5E760964B0B4B64829B2A54D91C172F252A138

R2_PATCH_DISPOSITION
SHA256
C950F55747248C5BDB21E8F6C829823C1ED253E8492ABF77EAC3B54ADBAD7CDA
```

已独立解压：

```text
V4_2_2_FEP_R2_EXTERNAL_REAUDIT_PACKAGE_20260930.zip
```

包内共登记 20 个文件。

逐文件重新计算：

```text
SHA256
bytes
```

均与：

```text
MANIFEST.json
```

完全一致。

未发现：

```text
MISSING
HASH_MISMATCH
SIZE_MISMATCH
```

上传的四个 loose 文件也与 ZIP 中：

```text
CURRENT/*
```

逐字节一致。

---

# 3. 外部 R1 审计证据链

ZIP 中：

```text
EXTERNAL/R1_EXTERNAL_CROSS_AUDIT.md
```

SHA256：

```text
348549667E1E4DF710955C5712EE292DB9B7B20BAD2624DFB6984C1F4DEF7831
```

与上一轮外部审计原文件：

```text
V4_2_2_FEP_R1_EXTERNAL_CROSS_AUDIT_R1_20260930.md
```

逐字节一致。

因此不存在：

```text
修改外部审计原文
删减外部阻断项
替换审计结论
```

的问题。

原始四份内部审计：

```text
FEP_STATISTICS_REVIEW_20260930.md
FEP_TEMPORAL_REVIEW_20260930.md
FEP_INTEGRATION_REVIEW_20260930.md
FEP_INTEGRATION_SECOND_REVIEW_20260930.md
```

以及：

```text
FEP_R2_INTEGRATION_REVIEW_20260930.md
FEP_R2_TEMPORAL_REVIEW_20260930.md
```

均已纳入复审包。

P2-01 正式关闭。

---

# 4. P1-01｜逐 fold / partition Label Revision

## R1 问题

R1 中：

```text
dataset_eligibility_ledger
```

只能给：

```text
(dataset, observation, target)
```

保存一个：

```text
selected_label_revision
```

与：

```text
历史每个fold只能消费当时可见label revision
```

冲突。

---

## R2 修复

R2 已拆成：

```text
dataset_eligibility_ledger
```

只保存：

```text
完整expected denominator
```

不再保存全局：

```text
selected_label_revision
```

新增：

```text
dataset_fold_cutoffs
```

冻结：

```text
dataset
fold
partition
fold_dataset_cutoff
phase_started_at
```

新增：

```text
dataset_fold_label_selection
```

按：

```text
dataset
fold
partition
observation
target
```

保存：

```text
selected_label_revision
selected_label_digest
eligibility
selection_reason
```

`dataset_rows` 又通过复合 FK 精确绑定：

```text
同 fold
同 partition
同 observation
同 target
同 revision
同 digest
```

因此可以合法表达：

```text
Fold A cutoff = T10
→ label r1

Fold B cutoff = T20
→ label r2
```

并拒绝：

```text
Fold A
→ 偷读 T15 才可见的 r2
```

---

## 进一步加固

R2 还增加：

```text
validate_fold_cutoff
validate_fold_label_selection
validate_dataset_row
```

参考触发器。

设计中已明确：

```text
FIT
TUNE
CALIBRATION
OUTER_TEST
```

拥有各自：

```text
phase_started_at
fold_dataset_cutoff
```

且同 fold 跨 partition：

```text
same observation
same trade_date
same entity+episode
```

不得重叠。

结论：

```text
P1-01 = PASS
```

---

# 5. P1-02｜细粒度 Production Permission

R2 新增：

```text
permission_keys
```

正式 grant key：

```text
scope_id
target_id
horizon
feature_contract_id
model_set_id
capability
```

能力明确区分：

```text
SHADOW_INFERENCE
DESCRIPTIVE_DISPLAY
MODEL_DISPLAY
PRIORITY_USE
```

并且：

```text
permission_keys
activation
acceptance_receipt
priority reference
API readback
```

共享同一 exact grant identity。

所以：

```text
T+5 MARKET_EXCESS MODEL_DISPLAY
```

不会自动授权：

```text
T+20 INVALIDATION
```

也不会自动授权：

```text
另一个feature variant
另一个model set
另一个capability
```

生产 grant 又被明确限制为：

```text
CHAMPION
```

BASELINE / CHALLENGER：

```text
diagnostic / Shadow only
```

不会继承 Champion 的生产展示与排序权限。

结论：

```text
P1-02 = PASS
```

---

# 6. P1-03｜Deployment Head / CAS

R1 只有 append-only activation，没有真正 current head。

R2 已新增：

```text
deployment_heads
deployment_change_receipts
```

Head key：

```text
scope
capability
target
horizon
feature_contract
```

注意：

```text
model_set
```

不进入 head key，

而是：

```text
head payload
```

所以两个候选模型真正竞争：

```text
同一个 deployment head
```

而不是因为 model_set 不同变成两个独立 head。

---

R2 还提供：

```text
cas_deploy(...)
```

参考实现。

语义为：

```text
expected version=0
→ initial version=1

expected version=v
+ expected prior activation=A
→ version=v+1
```

并要求：

```text
activation
deployment_change_receipt
deployment_head
```

同一事务。

CAS 冲突：

```text
全部rollback
```

同 request_id：

```text
参数完全一致
→ readback原receipt

参数不一致
→ IDEMPOTENCY_CONFLICT
```

R2 内部复核过程中发现的：

```text
NULL比较绕过
```

也已经定点修复为：

```text
必需参数先拒NULL
+
IS DISTINCT FROM
```

Head：

```text
禁止DELETE
```

普通应用角色：

```text
禁止直接DML
```

未来需由 E1 在真实 PostgreSQL 中验证：

```text
SECURITY DEFINER
owner
search_path
EXECUTE privilege
并发
事务rollback
```

这是实现门，不再是设计缺口。

结论：

```text
P1-03 = PASS
```

---

# 7. P1-04｜三时间链

R2 已正式拆成：

```text
source_fact_available_at
label_training_mature_at
label_revision_available_at
```

分别表示：

```text
原事实及依赖何时实际可见
完整N-window何时允许进入训练
本次label revision何时真正可读
```

因此现在可以正确表示：

```text
T+2
CONFIRMED事实已知

T+5
ANY_CONFIRM_5
才训练成熟
```

而不会再被错误约束为：

```text
事实不能早于训练成熟
```

训练选择需要三者分别满足：

```text
<= fold_dataset_cutoff
```

所以：

```text
T+3
拒绝训练

T+5成熟
但revision T+6才到
仍拒绝T+5模型
```

语义正确。

结论：

```text
P1-04 = PASS
```

---

# 8. P1-05｜ENTRY 与 Daily Priority

R2 已写成硬合同：

```text
ENTRY-only FEP
= 事件日研究注释
```

不能：

```text
进入PREWATCH当天预测
→ 连挂5天
→ 冒充今天预测
```

今日 Radar 的：

```text
PRIORITY_USE
```

必须拥有：

```text
DAILY_LANDMARK
或正式注册的candidate-day scope
+
当日feature
+
当日prediction
+
预注册覆盖门
```

否则：

```text
保留 PRIORITY_V1
```

旧 ENTRY forecast 只能在：

```text
历史/as-of 面板
```

展示。

这正好解决上一轮最关键的产品语义问题：

> FEP 最终不是判断“当初为什么进池”，而是判断“今天同一候选池里谁值得优先研究”。

结论：

```text
P1-05 = PASS
```

---

# 9. P2-02｜Append-only Guard

R1 用：

```text
pg_tables循环
```

给当前表创建 trigger，

但未来新增表不会自动继承。

R2 已改成：

```text
当前32张immutable表
逐表显式创建immutable trigger
```

并规定：

```text
future fact/history migration
必须显式建guard
+
表清单测试
```

唯一例外：

```text
deployment_heads
```

因为它本来就是受控可变 current pointer。

其更新通过：

```text
controlled_head
```

触发器和 CAS 管理。

独立检查结果：

```text
DDL tables = 33
immutable guards = 32
controlled mutable table = deployment_heads
unguarded unexpected tables = 0
```

结论：

```text
P2-02 = PASS
```

---

# 10. P2-03｜Header 与版本治理

REV4-FEP-R2 已把：

```text
ORIGINAL DESIGN BASELINE
```

和：

```text
CURRENT AUDITED IMPLEMENTATION HEAD
```

彻底拆开。

当前主文：

```text
ORIGINAL DESIGN BASELINE
= codex/algorithm-v3-incremental-upgrade
  @ 3ef5bf...

CURRENT AUDITED IMPLEMENTATION HEAD
= codex/v4-system-reform
  @ 0581731c...
```

同时：

```text
REV3-FEP
```

旧“当前生效版本”措辞已经清除。

当前修订身份：

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
```

结论：

```text
P2-03 = PASS
```

---

# 11. 主合同集成复核

本次 REV3 → REV4 diff 没有重新大改原 V4 主链。

修改集中在：

```text
Header / Version Governance
Priority V1 与 Daily FEP边界
Field Registry
§90 FEP
测试矩阵
```

没有发现：

```text
Core eligibility被FEP改写
BaoStock权限被扩大
Validation Cohort被Prediction反馈
Priority V1被默认替换
原accepted heads被覆盖
V4-16～22被FEP阻塞
```

FEP 仍是：

```text
Accepted Core之后的独立旁路
```

且：

```text
V4-15E1～E5
```

仍为：

```text
V4-15之后可选支线
```

不是后续全部开发的总前置门。

结论：

```text
MAIN_CONTRACT_INTEGRATION = PASS
```

---

# 12. 仍然开放的门

设计通过后，下列事项依然保持 OPEN。

## E1 数据与数据库工程

必须真实运行：

```text
PostgreSQL migration
FK
trigger
CAS
并发
rollback
DB role
SECURITY DEFINER
search_path
append-only guard
故意串entity/target/horizon反例
```

当前仅：

```text
Design SQL
```

不是 migration PASS。

---

## E2 条件统计

必须冻结：

```text
minimum rows
minimum dates
minimum independent blocks
entities
episodes
class counts
missingness / representativeness
```

样本不足时只能：

```text
diagnostic
```

不能为了输出结果降低门。

---

## E3 模型

必须真实完成：

```text
Train
Tune
Calibration
Outer Test
purge
OOD
coherence
artifact registry
```

没有真实 OOS：

```text
不授予 MODEL_DISPLAY
```

---

## E5 Priority

只有 Daily scope：

```text
同日
同候选池
同K
同coverage
```

对比：

```text
PRIORITY_V1
vs
PRIORITY_V2
```

并且：

```text
收益
风险
拒绝覆盖
missingness
```

同时过门，

才允许：

```text
PRIORITY_USE
```

---

# 13. 两个非阻断实施建议

以下不是设计阻断，不影响本次 PASS。

## Advisory-01

API 当前文字仍偏向：

```text
expectancy_model_set_id
prediction_run_id
prediction_revision
```

单值 context。

未来若一个页面同时展示多个：

```text
target × horizon
```

且它们允许使用不同 model_set，

API 实现应：

```text
按target请求局部context
```

或返回：

```text
expectancy_bindings[]
```

避免把一个 model_set id 误当全页面唯一模型身份。

这是 API 实现细化项。

---

## Advisory-02

`slot_model_bindings` 当前保存：

```text
model_set_id
selected_at
selection_receipt_digest
```

E1 实现时建议 receipt payload 显式包含：

```text
grant_id
activation_id
deployment_head_version
```

并进入 digest / readback。

这样历史 slot 能直接证明：

> 当时究竟由哪个 deployment activation 选中了这个 model set。

不是当前设计阻断，但会提升未来审计可读性。

---

# 14. 当前正式状态

从本轮开始：

```text
FEP DESIGN
= EXTERNAL_DESIGN_ACCEPTANCE_PASS
```

设计版本：

```text
DA-MSR-V4.2.2-FEP-R2
```

主合同版本：

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
```

允许：

```text
冻结设计基线
更新项目正式基准
等待V4-15 Forward authority就绪
之后生成V4-15E1正式实施任务卡
```

不允许：

```text
现在提前创建生产migration
宣称已有预测能力
宣称模型有效
宣称有个股上涨概率
把FEP用于真实Priority排序
把历史回放冒充FIRST_OBSERVED
```

---

# 15. 对当前系统路线的最终判断

这次 R2 修订后，FEP 已经不再只是：

```text
在现有因子上套一个机器学习模型
```

它已经成为一套独立的：

```text
Observation
→ PIT Feature Snapshot
→ Authoritative Forward Label
→ Per-Fold As-Of Dataset
→ Conditional Statistics
→ Model / Calibration / OOD
→ Ex-Ante Prediction
→ Daily Priority Shadow
→ Capability-Gated Production
```

研究与验证链。

它和当前系统原来的：

```text
Facts
→ Factors
→ Profile
→ Seed
→ Sector
→ PREWATCH
→ State
→ Radar
→ Forward
```

保持解耦。

这也是目前最重要的一点：

> 未来即使预测模型表现失败，也不会把已经打磨好的全市场结构研究系统一起拖坏。

因此，本轮可以结束 FEP 的“设计阶段反复修改”，进入设计冻结状态。

后续不要继续无休止审设计。

下一次真正重新打开 FEP，应当是在：

```text
V4-15 Forward authority
及对应 State/Event authority
已经具备正式接口
```

之后，开始：

```text
V4-15E1
```

工程实现与真实数据库验收。

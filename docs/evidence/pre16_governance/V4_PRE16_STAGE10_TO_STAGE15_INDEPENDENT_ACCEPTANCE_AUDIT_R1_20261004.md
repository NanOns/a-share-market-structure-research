# V4 PRE-16｜阶段10～阶段15独立串联验收审计 R1｜2026-10-04

## 0. 审计目标

在进入 V4-16 Realtime Shadow Dual-Run 之前，对 V4-10～V4-15 做一次脱离各阶段自报 PASS 的独立串联审计，回答四个问题：

1. V4-10～V4-15 的实施顺序是否正确；
2. 每一阶段的 Accepted Head 是否超出当时独立外部验收授权范围；
3. 是否满足当前最新架构合同的阶段职责与验收边界；
4. V4-10～V4-15 是否与 V4-00～V4-09 的 Accepted 链连续，是否存在断链、越权或倒灌。

---

# 1. 审计基线

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Current remote HEAD:

`a1bb12f19e758784e55a1a93acaad1954861a0fc`

Current global Stage:

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_15_ACCEPTED
```

Current Data Head:

```text
contract_id =
V4_DATA_ACCEPTED_HEAD_V2

accepted_trade_date =
2026-09-30

external_acceptance =
EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
```

---

# 2. 适用的最新文档权威

## 2.1 主架构权威

当前仓库对 V4-15 明确绑定：

`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`

即：

```text
DA-MSR-V4.2.2-CODEX-REV4-FEP-R2
```

REV4 保留 REV2 主线并增加 FEP 支线。

对 V4-10～V4-16 主线，§78 顺序仍为：

```text
V4-10 State Reducer
→ V4-11 Confirmation / Events
→ V4-12 Structure / Anchor / Support
→ V4-13 Profile Advanced Projection
→ V4-14 Replay Gate B
→ V4-15 Radar / Cohorts / Settlement
→ V4-16 Realtime Shadow Dual-Run
```

因此本审计使用：

```text
REV4 §78
+
REV4 §81 DoD
+
各阶段后续正式外部验收与 Accepted Head
```

共同作为验收标准。

## 2.2 FEP 不改变 V4-16 主线准入

REV4 新增：

```text
V4-15E1～V4-15E5
```

但正文明确：

```text
E1–E5 是可选支线
不是 V4-16～V4-22 的顺序前置条件

V4-16 可在 FEP NOT_READY 下继续 Core Shadow
不得等待未来真实样本才开展其它独立工程
```

因此：

```text
FEP 未完成
!=
V4-15 主线未完成

FEP 未完成
!=
V4-16 工程入口阻塞
```

---

# 3. 唯一总裁决

```text
PRE16_STAGE10_TO_STAGE15_INDEPENDENT_REAUDIT =
PASS_WITH_PRE16_GOVERNANCE_RECONCILIATION_REQUIRED

V4_10 =
PASS_KEEP_ENGINEERING_INTERFACE_SCOPE

V4_11 =
PASS_KEEP_CAPABILITY_SCOPED_ENGINEERING

V4_12 =
PASS_KEEP_SCOPED_ENGINEERING

V4_13 =
PASS_KEEP_SCOPED_ENGINEERING_AFTER_CROSS_STAGE_REPAIR

V4_14 =
PASS_KEEP_REPLAY_GATE_B_CAPABILITY_SCOPED

V4_15 =
PASS_KEEP_RUNTIME_CAPABILITY_SCOPED

V4_00_TO_V4_15_ACCEPTED_CHAIN =
PASS_CONTIGUOUS

LATEST_REV4_MAINLINE_ALIGNMENT =
PASS

UPSTREAM_LIMITATION_PROPAGATION =
PASS_FAIL_CLOSED

FEP_OPTIONAL_BRANCH =
NOT_A_V4_16_BLOCKER

PRE16_CURRENT_CROSS_STAGE_AUDIT_AUTHORITY =
RECONCILIATION_REQUIRED_P0_GOVERNANCE

V4_16_CONTRACT_FREEZE_ENTRY =
HOLD_UNTIL_PRE16_GOVERNANCE_RECONCILIATION_PASS
```

结论不是“10～15 需要重做”。

结论是：

> V4-10～V4-15 的算法阶段链、Accepted Head 和阶段放行顺序整体成立；在 V4-16 开始之前，需要补一个很小但必须完成的“当前跨阶段审计状态权威”治理闭环。

---

# 4. V4-00～V4-15 依赖链是否连贯

REV4 的逻辑依赖链是：

```text
Source / Identity
→ Facts / Factors
→ Core Profile
→ Replay A
→ Seed
→ Sector / Rotation
→ PREWATCH
→ Confirmation / Structure
→ Final State
→ Events / Radar / Cohorts / Settlement
→ Replay B
→ Realtime Shadow
```

实际 Accepted 链对应为：

```text
V4-00～05
Foundation / Canonical / Factors / Replay A
        ↓
V4-07
Stock Base Seed
        ↓
V4-08
Sector / Rotation
        ↓
V4-09
Stock PREWATCH
        ↓
V4-10
State Reducer interface
        ↓
V4-11
D0 Confirmation / Events
        ↓
V4-12
D1 Structure / Anchor / Support
        ↓
V4-13
Advanced Projection / Context / LOO integration
        ↓
V4-14
Replay Gate B
        ↓
V4-15
Radar / Cohort / Settlement
        ↓
V4-16
Realtime Shadow
```

V4-06 Supplemental Enrichment 本来就是非 V4-07 硬前置的可选分支。

因此总体拓扑与最新 §78 一致。

---

# 5. Exact Accepted-Head 连续性

## 5.1 V4-09 → V4-10

`V4_10_ACCEPTED_HEAD.json` 的 `parent_binding` 精确绑定：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
sha256 =
641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d
```

PASS。

## 5.2 V4-10 → V4-11

`V4_11_ACCEPTED_HEAD.json` 的 `parent_binding` 精确绑定：

```text
data/v4/V4_10_ACCEPTED_HEAD.json
sha256 =
ad9fc4643652feb3684223817f2e9c300167d128e2e8a07179e86f65094fd1e1
```

PASS。

## 5.3 V4-11 → V4-12

`V4_12_ACCEPTED_HEAD.json` 精确绑定：

```text
v4_11_parent =
data/v4/V4_11_ACCEPTED_HEAD.json
sha256 =
d8d96dce559eb968e6446f0626766980f6fb045fca1219e3e01fcd0a980b9928
```

PASS。

## 5.4 V4-12 → V4-13

V4-13 amended Accepted Head 的 accepted input set 包含：

```text
V4-12 Accepted Head
V4-08 PIT Membership
V4-07
V4-08 amended
V4-04/05
```

并使用 accepted-only binder。

PASS。

## 5.5 V4-13 → V4-14

`V4_14_ACCEPTED_HEAD.json` 精确绑定：

```text
amended_predecessor =
data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json

sha256 =
98f222ba4d62318ee900a69b8cad7c25359a30bcc7097efe0a55b8ffea09aa65
```

PASS。

## 5.6 V4-14 → V4-15

`V4_15_ACCEPTED_HEAD.json` 精确绑定：

```text
predecessor_v4_14 =
data/v4/V4_14_ACCEPTED_HEAD.json

sha256 =
830d68d2139fd7f1b1adaf426f23b7d9ee1f4ac463763c5bd0bd35c5b4a58589
```

并另外绑定 V4-07～V4-14 owner heads。

PASS。

---

# 6. V4-10 独立验收

## 6.1 最新文档职责

REV4 §78：

```text
V4-10 State Reducer

RESEARCH_STATE_V1 接口与独立向量；
最终集成须等 D0/D1 交付。
```

## 6.2 实际 Accepted Scope

V4-10 Accepted Head：

```text
STATE_REDUCER_AUTHORITY = ENGINEERING_ACCEPTED
STATE_REDUCER_INTERFACE = ENGINEERING_ACCEPTED
STATE_REDUCER_MACHINE_VECTORS = ENGINEERING_ACCEPTED
STATE_REDUCER_PERSISTENCE = ENGINEERING_ACCEPTED

FULL_D0_D1_D2_DAG = NOT_IMPLEMENTED
V4_11_CONFIRMATION = NOT_IMPLEMENTED
V4_12_STRUCTURE_SUPPORT = NOT_IMPLEMENTED
```

外部验收：

```text
V4_10_EXTERNAL_ACCEPTANCE_PASS_R1_2_ENGINEERING_SCOPE
```

明确不声称完整 DAG。

Clean detached regression：

```text
1116 passed
0 failed
0 errors
```

并验证 controlled publisher、DB lineage、model boundary、prior authenticity、input provenance。

## 6.3 裁决

```text
V4_10 = PASS_KEEP
```

不存在“接口测试冒充完整 DAG”的越权。

---

# 7. V4-11 独立验收

## 7.1 最新文档职责

```text
Confirmation / Events

Legacy exact AST / golden examples
D0 facts
D2 后 event diff
Amount A 隔离
```

## 7.2 实际 Accepted Scope

正式接受：

```text
LAUNCH_CONFIRM =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY

RECOVERY_TURN =
ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY
```

保持降级：

```text
STRONG_PULLBACK =
DIAGNOSTIC_ONLY_NOT_FORMAL

TREND_CONTINUE =
DIAGNOSTIC_ONLY_NOT_FORMAL

HISTORICAL_AS_RECORDED_EVENT =
NOT_PROVEN

FULL_D0_D1_D2_DAG =
NOT_IMPLEMENTED
```

R5 独立外审明确检查：

- accepted V4-07/V4-09 owner exact parity；
- formal t-1 UNKNOWN 保持 UNKNOWN；
- D2 sealed owner bridge；
- V4-10 reducer AST 未被偷改；
- no raw fallback。

## 7.3 裁决

```text
V4_11 = PASS_KEEP_CAPABILITY_SCOPED
```

未把诊断能力升级成正式能力。

---

# 8. V4-12 独立验收

## 8.1 最新文档职责

```text
Structure / Anchor / Support

D1 algorithm
coordinate rebase
breakout / pullback / recovery
support / acceptance
```

## 8.2 实际实现

最终 R13 外审关闭 Basic Breakout Episode 的核心跨日缺口，证明：

- t-1 breakout episode continuation；
- duplicate creation guard；
- owner-anchor immutability；
- same-day revision predecessor；
- failed → new episode；
- persisted oracle；
- fail-closed UNKNOWN。

最终 capability map 与最新 §78 对齐。

## 8.3 真实源缺口没有被掩盖

V4-12 Accepted Head 对无法取得正式 target-date owner 的字段明确保留：

```text
DO_NOT_RECONSTRUCT_FROM_RAW_BARS
```

包括 ATR20、CLV、MA20/60、prior fields、alpha/beta 等。

因此真实目标日能力：

```text
REAL_TARGET_DATE_STRUCTURE_SIGNAL =
DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY
```

而不是为了让结构算法出结果而越权读取 raw/provider。

## 8.4 裁决

```text
V4_12 = PASS_KEEP_SCOPED_ENGINEERING
```

这是正确的 capability-scoped 通过，不是生产能力 PASS。

---

# 9. V4-13 独立验收

## 9.1 最新文档职责

```text
Profile Advanced Projection

Context
LOO
Structure projection
complete DAG integration
```

## 9.2 R16R1 结果

外审：

```text
R16R1_EXTERNAL_AUDIT =
PASS_SCOPED_ENGINEERING
```

但没有直接允许 Promotion。

它发现：

```text
CSG-01
historical accepted objects incorrectly resolve moving Stage Head bytes

CSG-02
obsolete historical current-stage gates
```

因此强制：

```text
R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS
```

后才能 Promotion。

## 9.3 修复纪律

R17A：

```text
828 passed
0 failed
0 errors
0 skipped
0 deselected
```

然后 R17B 独立 promotion gate P01–P15 全部 PASS，再正式推进 Stage Head 到 V4-13。

后续 R17R1 又修复 formal active binding consistency，并生成当前：

```text
V4_13_ACCEPTED_HEAD_AMENDED_R1
```

## 9.4 能力边界保持正确

仍保留：

```text
historical_LOO = NOT_VERIFIABLE
legacy_B2 = NOT_IMPLEMENTED
algorithmic_support_sector = UNKNOWN_REAL_ACCEPTED_CAPABILITY
relative_sector_state = UNKNOWN_REAL_ACCEPTED_CAPABILITY
V4_13_REAL_SIGNAL_CAPABILITY =
DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY
```

## 9.5 裁决

```text
V4_13 = PASS_KEEP_SCOPED_ENGINEERING
```

而且 V4-13 是 10～15 中治理处理最规范的一段之一：发现跨阶段缺陷后先修治理，再 Promotion，没有绕过门禁。

---

# 10. V4-14 独立验收

## 10.1 最新文档职责

```text
Replay Gate B

ALGORITHM_STATE_REPLAY_PASS
完整 D0/D1/D2 时序与修订
```

## 10.2 实际外审

最终：

```text
R18R1R1R1_EXTERNAL_AUDIT =
PASS_FINAL_V4_14_RUNTIME_CAPABILITY_SCOPED
```

通过：

- Full D0/D1/D2 engineering replay；
- exact edge-consumption truth；
- deterministic replay；
- same-day revision isolation；
- cross-process previous session；
- rollback drill；
- independent rollback oracle。

Clean regression：

```text
1168 passed
0 failed
0 errors
0 skipped
0 deselected
```

## 10.3 没有越权历史效果

Accepted Head 明确：

```text
ALGORITHM_STATE_REPLAY =
DEGRADED_PASS_CAPABILITY_SCOPED

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED

REAL_SIGNAL_CAPABILITY =
DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY
```

## 10.4 Promotion 顺序正确

只有外审通过后，R19A 才：

```text
create V4_14_ACCEPTED_HEAD
advance Stage Head to V4-14
```

然后只允许 V4-15 contract-first freeze。

## 10.5 裁决

```text
V4_14 = PASS_KEEP_REPLAY_GATE_B_CAPABILITY_SCOPED
```

---

# 11. V4-15 独立验收

## 11.1 最新文档完整职责

REV4 §78 要求：

```text
字段全量登记
事件样本
控制分配
market/sector benchmark
due planner
价格结算
结果修订
Why Now
readback
```

不能只因为 Settlement 跑通就算 V4-15 完成。

## 11.2 Contract completeness

`config/v4_15_contract_package_v1.json` 正式包含：

- Radar contract/event registry；
- Why Now schema；
- Conflict/Hypothesis schema；
- Cohort + revision policy；
- Radar/Cohort field registry + machine vectors；
- Due Planner；
- Forward Price Path；
- Outcome Status / Competing Outcome；
- Market Benchmark；
- Sector Benchmark；
- Rotation Basket；
- Control Assignment；
- Settlement Revision / Readback；
- Settlement field registry + vectors；
- full V4-15 field registry；
- DAG registry；
- source capability matrix；
- quality degradation；
- storage schema；
- integrated machine vectors。

因此 §78 的主要 contract surface 完整。

## 11.3 Runtime completeness

Radar/Cohort runtime：

```text
R20C = PASS_LOCAL
```

真实 2026-09-30 accepted-source scope：

```text
owner_rows = 5224
ledger = 117
logical_events = 117
namespace = RECONSTRUCTED_ASOF
```

Why Now 与 Conflict 实际进入 event observation。

当没有足够证据产生真正竞争 hypothesis 时：

```text
hypotheses = []
quality = HYPOTHESIS_SET_INCOMPLETE
```

没有为了满足模板而编造第二解释。

Settlement：

```text
Due Planner = IMPLEMENTED_ENGINEERING
Benchmark/Control runtime = IMPLEMENTED_ENGINEERING
Settlement runtime = IMPLEMENTED_ENGINEERING
Revision/Readback = implemented/tested
```

Full persisted E2E 和 independent oracle 均通过。

## 11.4 真实能力边界正确

R20R1/R20R1R1/R20R1R2 进一步修正：

- 不允许 generic `REAL_ACCEPTED_SOURCE_SETTLEMENT` 过宽；
- 正式 DM01 Data Head lineage；
- native DM01 row 与 V4-15 forward projection 分层；
- real T0 exact admission；
- future path 不存在时保持 pending。

最终：

```text
CURRENT_REAL_MATURITY_EVIDENCE = NONE
PROVED_HORIZONS = []
UNPROVED_HORIZONS = [1,3,5,10,20]

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

HISTORICAL_PIT_EFFECTIVENESS =
NOT_GRANTED
```

R21 最后完成 V4-15 Accepted Head + Stage Head + CurrentStageAuthority 的原子 Promotion。

## 11.5 裁决

```text
V4_15 = PASS_KEEP_RUNTIME_CAPABILITY_SCOPED
```

主线 V4-15 可以关闭。

---

# 12. 上游限制有没有被错误升级

这是本轮最重要的反向检查之一。

结果：

```text
PASS
```

V4-12/V4-13 的真实 owner/历史 PIT/LOO 等缺口，在 V4-14/V4-15 中没有被升级成无条件 PASS。

仍能看到：

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
REAL_SIGNAL_CAPABILITY = DEGRADED...
historical_LOO = NOT_VERIFIABLE
legacy_B2 = NOT_IMPLEMENTED
CURRENT_REAL_MATURITY_EVIDENCE = NONE
```

说明后续阶段没有通过故事性“补齐”上游证据。

---

# 13. 当前发现的唯一 PRE-V16 治理问题

## GOV-PRE16-01｜Current Cross-Stage Audit Status Authority Stale / Ambiguous

当前 `V4_STAGE_ACCEPTED_HEAD.json` 仍带有：

```text
open_audit_registry
→ reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json
```

该 R1 registry 是 2026-10-01 的治理入口快照，其中仍写：

```text
all_capabilities_remain_unaccepted = true
A01/A02/A04/... = OPEN/QUEUED
```

但仓库后来已经产生新的正式状态，例如：

```text
V4_DATA_ACCEPTED_HEAD_V2
=
EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN

V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1
=
EXTERNALLY_ACCEPTED_SCOPED_PRODUCER
```

以及较新的：

```text
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R13_CONSOLIDATION_R3
V4_PARALLEL_SCOPED_ACCEPTANCE_SUMMARY_HEAD_R3
```

所以旧 R1 作为历史证据没有错，但继续以名称：

```text
open_audit_registry
```

出现在当前 Stage Head 中，容易被误读为“当前全局审计状态”。

### 定级

```text
TYPE =
GOVERNANCE_CURRENT-STATUS_AUTHORITY_AMBIGUITY

SEVERITY =
P0_BEFORE_V4_16_ENTRY

RETROACTIVE_STAGE_INVALIDATION =
NO

ALGORITHM_REPAIR_REQUIRED =
NO

ACCEPTED_HEAD_REWRITE_REQUIRED =
NO
```

它不推翻 V4-10～V4-15，因为后续每个阶段都有自己精确绑定的外审、Accepted Head 和 capability boundary。

但 V4-16 要开始真正的 PIT_OBSERVED/SHADOW，必须在启动前拥有一个唯一、可机读的“当前跨阶段能力/开放审计状态”权威，不能让 Shadow 根据历史 R1 状态做权限解释。

---

# 14. 推荐修复方式

禁止覆盖或删除：

```text
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json
```

它应继续作为历史治理入口。

新增一个正式的当前状态权威，例如：

```text
data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1.json
config/v4_cross_stage_current_audit_authority_v1.json
```

它应从当前 exact accepted evidence 派生，而不是手写 PASS。

至少区分：

```text
ACCEPTED_SCOPED
OPEN_ENGINEERING
OPEN_EXTERNAL_REAUDIT
ACCUMULATION_CONTINUES
PERMANENT_CAPABILITY_LIMITATION
NONBLOCKING_VALIDATION_DEBT
```

并明确：

```text
historical registry != current authority
```

V4-16 后续合同必须显式绑定这个 current audit head。

---

# 15. 不应借本轮治理修复做的事情

禁止：

```text
重算 V4-10～15 算法
修改 V4-10～15 Accepted Head
修改 V4_DATA_ACCEPTED_HEAD
重新解释历史 PIT
给 Production/Shadow/Focus 权限
把真实 Forward 未成熟改成 PASS
把 FEP 变成 V4-16 前置门
```

---

# 16. 当前仍然开放但不阻塞 V4-16 工程的能力债

包括但不限于：

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME =
NOT_GRANTED_PENDING_MATURITY_EVIDENCE

V4_15_FWD_ADJ_VECTOR_01 =
OPEN_NONBLOCKING_TEST_ENHANCEMENT

部分 V4-12/V4-13 real-signal owner capability =
DEGRADED / UNKNOWN

Forward/PIT observation accumulation =
continues naturally
```

这些影响对应能力的“证明程度”，不阻塞独立工程开发。

---

# 17. 最终流程判断

## 流程正确性

```text
PASS
```

V4-10 没有冒充完整 DAG；
V4-11/V4-12 分别补 D0/D1；
V4-13 做集成；
V4-14 才做完整 Replay Gate B；
V4-15 在 Shadow 前交付 Cohort/Settlement。

## 与 V4-00～09 的连贯性

```text
PASS_CONTIGUOUS
```

存在 exact Accepted Head 链，没有发现断链。

## 满足最新 REV4 主线验收标准

```text
PASS_CAPABILITY_SCOPED
```

需要强调：

“满足”指其各自被授权的工程/能力范围。

不等于：

```text
历史 PIT 全证明
真实 Forward 全成熟
Production-ready
Shadow-stable
```

## V4-16 是否现在就直接执行

```text
NO
```

先完成：

```text
PRE16_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_RECONCILIATION
```

通过独立外审后，再执行已经设计好的 V4-16 R22 Contract Freeze / Entry。

---

# 18. 唯一下一步

```text
PRE16-GOV-R1
Current Cross-Stage Audit Authority Reconciliation

→ independent external audit
→ PASS
→ resume R22 V4-16 Contract Freeze / Entry
```

无需重开 V4-10、V4-11、V4-12、V4-13、V4-14 或 V4-15。

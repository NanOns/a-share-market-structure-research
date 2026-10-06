# 大A市场结构研究系统 V4｜V4-00～V4-22 + FEP 全阶段线上模型 × Codex 线下模型交叉审计验收 R1

> 日期：2026-10-06  
> 项目：大A市场结构研究系统 V4  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 审计 HEAD：`b7ca247745976aa390387a0701601b00ac0d8498`  
> 设计基线 Drive 文件：`A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md`  
> Drive ID：`1Uf3TIISWhU8Q_X16CvTaCybXeU1k1Axb`  
> 设计文档编号：`DA-MSR-V4.2.2-CODEX-REV4-FEP-R2`  
> 审计范围：V4-00A～00H、V4-01～V4-22、V4-17G、FEP V4-15E1～E5  
> 特别排除：`A08_CURRENT_RUNTIME` 正在执行中的治理传播任务，本报告不对其最终传播结果作裁决。  
> 文档性质：设计合同 / 当前代码 / 算法 / 数据结构 / Accepted Head / 独立外审证据的全阶段交叉审计。

---

# 0. 最重要的基线结论

## 0.1 Drive 设计文件与仓库设计文件完全一致

本轮先对用户刚上传至 Drive 根目录的：

```text
A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md
```

与仓库当前：

```text
docs/evidence/
A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md
```

执行文本级比较。

结果：

```text
drive_chars = 152543
repo_chars  = 152543

exact_text_equal = true
normalized_lf_equal = true
```

因此：

```text
DESIGN_BASELINE_IDENTITY = PASS_EXACT
```

本轮不存在“线上模型与 Codex 使用了不同设计版本”的问题。

后文所有阶段审计均以这份设计为最高基线，并结合后续已经正式接受的阶段 amendment / capability-scoped external acceptance。

---

# 1. 审计方法

本轮不采用：

```text
“阶段历史上写过 PASS”
→
“当前代码一定完整”
```

而是按以下顺序：

```text
设计 §78 唯一实施阶段表
        ↓
阶段目的与硬边界
        ↓
当前代码 / contract / migration / data structure
        ↓
Accepted Head
        ↓
后续 amendment / external audit
        ↓
Current Audit Head
        ↓
当前真实能力 / 未完成 gate
```

每个阶段分别回答：

1. 设计目的是什么；
2. 代码/算法/数据结构是否已经实现；
3. 为什么可以验收；
4. 为什么不能验收为“全能力完成”；
5. 还缺什么；
6. 未完成项属于：
   - 真正实现缺口；
   - 设计允许的 capability degradation；
   - historical PIT 不可证明；
   - 真实样本/成熟度门；
   - 生产切换门；
   - 后续阶段职责。

---

# 2. 状态定义

本报告使用以下统一状态。

## FULL_PASS

设计要求在该阶段的 Required Scope 已完整实现并外审接受。

## PASS_AMENDED_SCOPE

原始阶段范围经过正式 amendment 调整，当前实现与 amendment 后设计完全一致。

## SCOPED_PASS

核心工程实现与合同正确，但某些 capability 因数据/owner/PIT/历史证据不足而 fail-closed，不允许扩大为全能力 PASS。

## ENGINEERING_PASS_REAL_GATE_PENDING

算法、数据结构、运行时已经实现；真实 Shadow / Forward maturity / OOS 证据尚未发生。

## CONTRACT_DESIGN_PASS_IMPLEMENTATION_PENDING

合同设计与反例已经外审，但真实 writer / cutover / migration runtime 尚未实现或尚未获准执行。

## REAL_GATE_PENDING

没有代码 bug；必须等真实 accepted publication、真实交易日、成熟 outcome 或生产权限。

## NOT_GRANTED

明确没有权限，禁止被解释成 PASS。

---

# 3. 全项目唯一总体结论

```text
DESIGN_BASELINE_IDENTITY =
PASS_EXACT

V4_00_TO_V4_15_ACCEPTED_CHAIN =
PASS_CONTIGUOUS

V4_00_TO_V4_15_DESIGN_CONFORMANCE =
PASS_WITH_CAPABILITY_SCOPED_LIMITATIONS

FEP_E1_TO_E5 =
ENGINEERING_COMPLETE_FOR_CURRENT_SCOPE

V4_16 =
ENGINEERING_READY
OPERATIONAL_STAGE_NOT_COMPLETE

V4_17 =
ENGINEERING_EXTERNALLY_ACCEPTED
REAL_READBACK_PENDING

V4_17G =
NOT_GRANTED_WAIT_REAL_SHADOW

V4_18 =
CONTRACT_DESIGN_ACCEPTED
RUNTIME_REPLAY_NOT_IMPLEMENTED

V4_19 =
CONTRACT_DESIGN_ACCEPTED
FOCUS_CUTOVER_NOT_IMPLEMENTED

V4_20 =
CONTRACT_DESIGN_ACCEPTED
DEFAULT_UI_CUTOVER_NOT_IMPLEMENTED

V4_21 =
CONTRACT_DESIGN_ACCEPTED
REAL_CONTINUED_OBSERVATION_NOT_STARTED

V4_22 =
CONTRACT_DESIGN_ACCEPTED
FINAL_PROJECT_PASS_NOT_GRANTED

PRODUCTION =
false

FOCUS_CUTOVER =
false

DEFAULT_UI_CUTOVER =
false

REAL_SHADOW_OBSERVATIONS =
0

PIT_OBSERVED_REAL_SAMPLES =
0

FEP_PRODUCTION =
UNGRANTED

REAL_OOS =
NOT_GRANTED

CHAMPION =
NONE
```

**排除当前正在执行的 A08 后，本轮没有发现新的 P0/P1“当前代码实现方向与设计合同相反”的问题。**

但这并不等于 V4-00～22 全部完成。

真正完整的说法是：

> V4-00～15 已形成连续工程 Accepted Chain；  
> FEP E1～E5 已完成当前 engineering scope；  
> V4-16/17 的真实运行前基础设施已建立；  
> V4-17G～22 的核心剩余工作是实际真实 Shadow、稳定门、Migration Replay、Focus/UI Cutover、Continued Forward 和最终独立验收。

---

# 4. 阶段总表

| 阶段 | 设计目标 | 当前结论 | 是否完整实现阶段最终目标 |
|---|---|---|---|
| V4-00A～H | 基线、PIT、publication、TDX、adjustment、supplemental、算法合同、rollback | FULL_PASS | 是，Required Scope |
| V4-01 | TDX历史Bootstrap / Universe / lifecycle | FULL_PASS_REQUIRED_SCOPE | Required Scope是；全历史authority不是 |
| V4-02 | Canonical Daily / PIT Period / Price Limit | PASS_WITH_DEGRADED_HISTORICAL_SCOPE | 当前链是；历史AS_RECORDED不是 |
| V4-03 | Pure-Core Factors | PASS_AMENDED_SCOPE | 是，amended scope |
| V4-04 | Full-Market Core Profile | FULL_PASS_REQUIRED_SCOPE | 是 |
| V4-05 | Replay Gate A | DEGRADED_PASS_CONFORMANT | 工程Replay是；historical PIT不是 |
| V4-06 | Supplemental Enrichment | DEGRADED_PASS_OPTIONAL | 工程是；BaoStock全能力不是 |
| V4-07 | Stock Base Seed | ENGINEERING_PASS_SCOPED | 工程是；real signal有降级 |
| V4-08 | Sector / Rotation Core | ENGINEERING_PASS_CAPABILITY_SCOPED | 否，B2/Amount-A部分能力仍缺 |
| V4-09 | Stock PREWATCH | ENGINEERING_PASS_CAPABILITY_SCOPED | 工程是；A08本轮排除 |
| V4-10 | State Reducer | FULL_PASS_STAGE_PURPOSE | 是；完整DAG按设计在V4-14 |
| V4-11 | Confirmation / Events | ENGINEERING_PASS_CAPABILITY_SCOPED | 部分scenario正式，部分diagnostic |
| V4-12 | Structure / Anchor / Support | ENGINEERING_PASS_CAPABILITY_SCOPED | 工程是；historical/real-owner能力不全 |
| V4-13 | Advanced Projection / LOO | ENGINEERING_PASS_CAPABILITY_SCOPED | 工程是；historical LOO/上游能力不全 |
| V4-14 | Replay Gate B | ALGORITHM_STATE_REPLAY_DEGRADED_PASS | 工程完整；historical PIT effectiveness未授权 |
| V4-15 | Radar / Cohort / Settlement | RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED | 工程完整；真实maturity未完成 |
| V4-15E1 | FEP Dataset / Identity / Registry | ENGINEERING_ACCEPTED | 工程是；REAL FIRST_OBSERVED未有 |
| V4-15E2 | Conditional Statistics | ENGINEERING_ACCEPTED_CAPABILITY_SCOPED | FIRST_PREWATCH:T1是；全scope不是 |
| V4-15E3 | Interpretable Model | ENGINEERING_ACCEPTED_CAPABILITY_SCOPED | 工程是；有效性/OOS不是 |
| V4-15E4 | Tree Challenger | ENGINEERING_ACCEPTED_OPTIONAL | 是，作为challenger；未成为Champion |
| V4-15E5 | Projection / Permission / Priority Shadow | ENGINEERING_COMPLETE_CURRENT_SCOPE | 工程是；生产/真实Priority不是 |
| V4-16 | Realtime Shadow Dual-Run | ENGINEERING_READY | **否，真实Shadow未开始** |
| V4-17 | Shadow UI | ENGINEERING_EXTERNALLY_ACCEPTED | 工程是；真实readback未完成 |
| V4-17G | Shadow Stable / Forward Gate | NOT_GRANTED | 否 |
| V4-18 | Migration Replay Gate | CONTRACT_DESIGN_PASS | **运行实现未开始** |
| V4-19 | Focus Source Cutover | CONTRACT_DESIGN_PASS | **实际Cutover未开始** |
| V4-20 | Default UI Cutover | CONTRACT_DESIGN_PASS | **实际Cutover未开始** |
| V4-21 | Continued Forward Observation | CONTRACT_DESIGN_PASS | **真实累计未开始** |
| V4-22 | Independent Audit | CONTRACT_DESIGN_PASS | **Final Pass未执行/未授予** |

---

# 5. V4-00｜Phase 0 基础框架

设计 §78 把 V4-00 拆成 A～H。

历史 `V4_PHASE0_FINAL_RECEIPT_R5` 曾写：

```text
PENDING_JOINT_EXTERNAL_REVIEW
```

但该旧状态已经被后续：

```text
V4_00_01_02_03_FOUNDATION_FINAL_EXTERNAL_ACCEPTANCE_R2_20260929.md
```

正式 supersede。

后者明确：

```text
V4_00 = EXTERNAL_ACCEPTANCE_PASS
Phase0 00A~00H = FULL_PASS
```

并执行：

```text
275 passed
2 skipped
0 failed
0 error
```

## V4-00A｜Baseline Freeze

### 目的

冻结：
- HEAD；
- DB backup/restore；
- accepted / Focus heads；
- 旧输出；
- inherited audit。

### 当前实现

已存在 Stage/Data/Accepted Head、历史归档、hash-bound evidence 与 protected-state 机制。

### 结论

```text
PASS
```

没有发现当前 HEAD 破坏基线冻结原则。

---

## V4-00B｜Security Lifecycle / Universe / PIT

### 目的

冻结：
- 日期有效身份；
- knowledge time；
- Universe；
- historical coverage；
- 不支持范围。

### 实现

核心数据结构由后续 migrations 010～012 与 identity/lifecycle owner 实现，Phase0 契约层已完成。

### 结论

```text
PASS_REQUIRED_SCOPE
```

注意：全历史法律实体/类型的 `AS_RECORDED` authority 并没有被伪造，后续 V4-01 继续按 capability scope 限制。

---

## V4-00C｜Publication / Revision / Namespace

### 目的

实现：
- frozen predecessor；
- consumer manifest；
- revision；
- atomic acceptance；
- namespace migration。

### 数据结构

Phase0 PostgreSQL migrations：

```text
001_v4_phase0_foundation.sql
002_namespace_integrity.sql
003_phase0_contract_alignment.sql
004_publication_head_revision_identity.sql
005_market_session_publication_chain.sql
006_fact_source_guard_table_specific_fields.sql
007_state_and_namespace_publication_identity.sql
008_prior_session_state_freeze_integrity.sql
009_publication_head_guard_sql_alias_fix.sql
```

### 结论

```text
PASS
```

后续 V4-09/FEP/Shadow 均沿用 publication/revision/append-only 思路，说明这里不是“只写文档”。

---

## V4-00D｜TDX VIPDATA Source Contract

### 目的

有界下载、staging、manifest、校验、archive、overlap。

### 当前

TDX 主链保持 read-only source authority，后续 DM01/Data Head 继续依赖 accepted local/TDX authority。

### 结论

```text
PASS
```

---

## V4-00E｜Historical Adjustment / Coordinates

### 目的

仿射 adjustment、公司行为、历史可见性、Anchor / outcome 坐标。

### 当前

Adjustment lineage、coordinate basis 与后续 V4-12/V4-15 Forward 均有明确 contract。

此前全链路审计发现的 V4-15 affine validation 缺口已经在七项修复中关闭。

### 结论

```text
PASS_REQUIRED_SCOPE
```

仍存在：

```text
AUD_R3C_ADJUSTMENT_COORDINATE_EXACTNESS
```

待独立 re-audit，但它被正式定义为 production-cutover scoped debt，不重开 00～15 accepted chain。

---

## V4-00F｜BaoStock Supplemental Contract

### 目的

BaoStock 仅作为 supplemental，strict binding、有界请求，不能阻断 Core。

### 当前

这一原则在 V4-06、DM01、FEP 中均保持。

### 结论

```text
PASS_CONTRACT
```

BaoStock 的某些 live strict-binding 能力后续仍 degraded，但这是本阶段设计允许的：

```text
Supplemental missing
!=
Core blocked
```

---

## V4-00G｜Algorithm Contract Framework

### 目的

建立：
- AST；
- schema；
- parameter instance；
- producer registry；
- Legacy extractor；
- 三种窗口语义；
- benchmark missing policy；
- retention；
- capability-specific parameters。

### 当前

V4-03～15 的 machine AST、parameter set、producer identity、vector 都沿此框架实现。

### 结论

```text
PASS
```

---

## V4-00H｜Capability / Performance / Rollback

### 目的

scope、预算、失败回执、恢复演练、rollback、Phase0 final receipt。

### 当前

整个项目已经实际采用：

```text
FULL_PASS
DEGRADED_PASS
CAPABILITY_SCOPED
NOT_GRANTED
BLOCKED_AFFECTED_SCOPE
```

而不是一个全局 PASS。

### 结论

```text
PASS
```

---

# 6. V4-01｜TDX History Bootstrap

## 设计目的

```text
Raw archive
Historical Universe
Security lifecycle
重叠核验
历史不足允许 scope degradation
```

## 当前代码 / 数据结构

主要包括：
- lifecycle / identity discovery；
- dated alias；
- source fingerprint；
- migrations 010～012；
- exact accepted identity/universe。

外审完整扫描：

```text
4,035,729 rows
786 sessions
5,351 source keys
```

并正确识别：

```text
SZ.300114 -> SZ.302132
effective_date = 2025-02-17
```

## 为什么通过

- candidate union 完整；
- resolution 一一对应；
- unresolved = 0；
- stable security_id 未被错误重编号；
- 代码变更/公司实体语义有独立证据。

Accepted Head：

```text
status = FULL_PASS_REQUIRED_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
```

## 为什么不是“所有历史身份能力都100%证明”

后续 authority audit 已明确：

```text
HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_LOCAL_TDX_AUTHORITY
= NOT_PROVEN
```

对 pre-capture 历史不能制造 first availability。

## 最终

```text
V4-01 = FULL_PASS_REQUIRED_SCOPE
DESIGN_CONFORMANCE = PASS
```

缺口属于 design-allowed historical capability limitation，不是算法 bug。

---

# 7. V4-02｜Canonical Daily / PIT Periods

## 设计目的

实现：
- Raw Daily；
- Adjusted Daily；
- closed/as-of weekly/monthly；
- Trading Status；
- ST；
- Price Limit / special phase；
- PIT / adjustment basis。

## 当前

Accepted Head：

```text
PASS_WITH_BSE_SCOPE_DEGRADED
EXTERNALLY_ACCEPTED
```

当前 `V4_DATA_ACCEPTED_HEAD_V2` 已推进到：

```text
accepted_trade_date = 2026-09-30
external_acceptance = EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
```

当前 9/30 component 中：

```text
RAW_DAILY       FULL_PASS
IDENTITY        FULL_PASS
TRADING_STATUS  FULL_PASS
ISST            FULL_PASS
SPECIAL_PHASE   FULL_PASS

ADJUSTED_DAILY  DEGRADED_PASS
PERIOD_ADJUSTED DEGRADED_PASS
PRICE_LIMIT     DEGRADED_PASS
```

降级项均保留 explicit UNKNOWN/reason。

## 为什么通过

设计要求的关键不是“强行没有 UNKNOWN”，而是：

```text
不能把未证明状态伪造成正常值
```

当前实现符合。

## 尚缺

- pre-capture historical `AS_RECORDED` 不可证明；
- adjustment 部分 unsupported/unproved；
- current audit 仍保留：
  - SUSPENDED state admission re-audit；
  - adjustment coordinate exactness re-audit。

## 最终

```text
V4-02 = PASS_REQUIRED_SCOPE_WITH_EXPLICIT_DEGRADATION
```

不是全历史能力 FULL PASS。

---

# 8. V4-03｜Pure-Core Factors

## 设计目的

```text
CORE_FACTOR_V1
Market primitives
Sector native primitives
Benchmark基础价格路径
```

## 正式范围变更

V4-03 原本部分 Sector full-market 责任后经：

```text
V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1
```

正式迁往 V4-08。

因此当前正确状态不是“旧合同全做完”，而是：

```text
FULL_PASS_AMENDED_SCOPE
```

## 当前 Accepted Head

```text
STOCK_CORE        PASS
RELATIVE_RPS      PASS
MARKET_REFERENCE  PASS
MARKET_REGIME     PASS
SECTOR_NATIVE_CONTRACT PASS

SECTOR_NATIVE_FULL_MARKET
= BLOCKED / MOVED_TO_V4_08
```

## 结论

```text
PASS_AMENDED_SCOPE
```

这里的范围迁移是明确 amendment，不是设计漂移。

---

# 9. V4-04｜Full-Market Core Profile

## 设计目的

只实现 Pure-Core：

```text
Trend
Position
MA Structure
Relative
Compression
Participation / Amount-Price Result
Core Extension Risk
```

明确：

```text
不含 Turnover
不依赖 BaoStock
不依赖 Advanced Structure
不依赖最终 Sector Context
```

## 当前

`src/v4/profile_core.py` 和 full-market candidate 已物化。

Accepted Head：

```text
FULL_PASS_REQUIRED_SCOPE
```

主要能力全部 PASS。

## 为什么通过

这阶段做到了最重要的分层：

```text
Daily Profile
!=
筛选器

Core
!=
Supplemental
```

没有把后续 Turnover/Structure/Focus 反灌进 Core。

## 结论

```text
FULL_PASS_REQUIRED_SCOPE
```

---

# 10. V4-05｜Replay Gate A

## 设计目的

验证：

```text
DATA_FACTOR_REPLAY_PASS
```

并按 capability scope fail closed。

## 当前 Accepted Head

```text
DATA_FACTOR_REPLAY_DEGRADED_PASS
```

能力：

```text
CURRENT_FORWARD_ADJUSTED_PRICE  FULL_PASS
CURRENT_FORWARD_STOCK_CORE      DEGRADED_PASS
MARKET_REFERENCE                FULL_PASS

HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
= BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE

WEEKLY / MONTHLY / MARKET_REGIME
= DEGRADED_PASS
```

## 为什么可以通过

§78 明确：

```text
失败只阻断 affected successor
```

本阶段不要求为了“全绿”制造历史 PIT。

## 尚缺

```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

这是 permanent capability limitation，不应补造。

## 最终

```text
SCOPED_DEGRADED_PASS
DESIGN_CONFORMANCE = PASS
```

---

# 11. V4-06｜Supplemental Enrichment

## 设计目的

```text
TURNOVER_CONTEXT_V1
stock_profile_enrichments
supplemental_participation_context
```

且：

```text
V4-06不是V4-07前置
```

## 当前

Accepted Head：

```text
DEGRADED_PASS
V4_06_ENGINEERING = EXTERNALLY_ACCEPTED
BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED_DEGRADED
```

实现包括：
- `v4_06_supplemental.py`
- turnover context / enrichment
- migrations 013 / 014。

## 结论

```text
PASS_OPTIONAL_SCOPED
```

BaoStock 不完整不构成主链失败，完全符合设计。

---

# 12. V4-07｜Stock Base Seed

## 设计目的

从 F0 Pure-Core 构建：

```text
BASE_SEED_V1
```

禁止读：
- Anchor；
- Sector final；
- Final State；
- Focus；
- Supplemental 反向反馈。

## 当前

`src/v4/base_seed.py`
+
migration 015。

Accepted Head：

```text
ENGINEERING_PASS
```

但：

```text
REAL_BASE_SEED_SIGNAL =
DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN
```

## 为什么通过

Seed 计算骨架与隔离规则已验证。

## 尚缺

Real signal 仍受 accepted prior-RPS bootstrap unknown 影响。

这不等于 Base Seed 算法没实现。

## 最终

```text
ENGINEERING_PASS_SCOPED
```

---

# 13. V4-08｜Sector / Rotation Core

## 设计目的

§78 要求：

```text
共同成员
B0
B1
B2
纯Core legacy sector资格adapter
```

## 当前实现

代码位于：

```text
src/sector/*
migrations 016～020
```

Accepted Head 已通过：

```text
B0_SECTOR_PREWATCH_RAW
B1_ROTATION_CORE
SECTOR_NATIVE_CORE
ACCEPTED_CONTEXT_ROUTING
```

但：

```text
B2_AMOUNT_A =
DIAGNOSTIC_AUDIT_OPEN

B2_LEGACY_CONFIRMED_WARM =
NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE

REAL_SIGNAL_CAPABILITY =
DEGRADED
```

## 与设计的关系

这不是完全实现全部 §78 表面能力。

但设计 §34.3 同时明确：

> Legacy detector 若内部读取 Final State / Focus / online supplement，必须拆成纯函数或保持 diagnostic；未提取模块只阻断对应场景。

因此当前状态属于：

```text
DESIGN_ALLOWED_CAPABILITY_DEGRADATION
```

不是可以随便标 FULL PASS。

## 当前仍缺

Current Audit Head：

```text
A04_H21_CONSUMER
= ACCUMULATION_CONTINUES

A04_HISTORICAL_AMOUNT_A
= BLOCKED_AFFECTED_SCOPE
```

所以：

```text
AMOUNT_A_H21_FORMAL_CONSUMER
HISTORICAL_AMOUNT_A_FORMAL_CONSUMER
```

仍不能正式开放。

## 最终

```text
ENGINEERING_PASS_CAPABILITY_SCOPED
FULL_DESIGN_SURFACE = NOT_COMPLETE
```

这是 00～15 中最需要避免被误写成“全部完成”的阶段之一。

---

# 14. V4-09｜Stock PREWATCH

> 按用户要求，`A08_CURRENT_RUNTIME` 当前执行中的治理传播不纳入本报告最终裁决。

## 设计目的

```text
STOCK_PREWATCH_V1
raw qualification
priority primitives
```

## 当前

代码：

```text
src/v4/stock_prewatch.py
src/v4/stock_prewatch_persistence.py
```

DB：

```text
021_v4_09_stock_prewatch.sql
025_v4_09_consumer_identity_hardening.sql
```

Accepted Head：

```text
ENGINEERING_PASS_CAPABILITY_SCOPED
```

能力：

```text
STOCK_PREWATCH_RAW = ENGINEERING_ACCEPTED
PRIORITY_V1        = ENGINEERING_ACCEPTED
```

## 为什么通过

- whitelist input；
- UNKNOWN dominance；
- producer identity；
- consumer identity；
- immutable artifact；
- no same-day feedback；
- forbidden fields不改变输出；
- deterministic multi-context。

## 尚缺

```text
REAL_SIGNAL_CAPABILITY =
DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN
```

A08 current-runtime admission 本轮排除。

## 最终

```text
V4-09_ALGORITHM_ENGINEERING = PASS
A08_CURRENT_RUNTIME = EXCLUDED_BY_USER
```

---

# 15. V4-10｜State Reducer

## 设计目的

§78 特别说明：

```text
V4-10只需实现：
RESEARCH_STATE_V1接口
独立向量

完整运行必须等V4-11/12
并在V4-14验收
```

## 当前

代码：

```text
src/v4/research_state.py
src/v4/research_state_persistence.py
```

DB：

```text
022
023
024
```

Accepted Head：

```text
ENGINEERING_PASS_INTERFACE_SCOPE
```

当时：

```text
FULL_D0_D1_D2_DAG = NOT_IMPLEMENTED
```

这是**设计要求**，不是缺陷。

后续 V4-14 已完成全 DAG replay。

## 最终

```text
V4-10_STAGE_PURPOSE = FULL_PASS
```

不能因为 V4-10 Head 写 `FULL_D0_D1_D2_DAG=NOT_IMPLEMENTED` 就判失败。

---

# 16. V4-11｜Confirmation / Events

## 设计目的

```text
Legacy exact AST / golden vectors
D0 Confirmation facts
D2 after-event diff
Amount-A隔离
```

设计列出的 legacy scenarios：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

同时设计明确：

```text
无法纯化的legacy函数可保持diagnostic
只阻断对应scenario
```

## 当前

Accepted：

```text
LAUNCH_CONFIRM       ENGINEERING_ACCEPTED_FORMAL_D0
RECOVERY_TURN        ENGINEERING_ACCEPTED_FORMAL_D0

STRONG_PULLBACK      DIAGNOSTIC_ONLY
TREND_CONTINUE       DIAGNOSTIC_ONLY

D2_SEALED_OWNER_BRIDGE
= ENGINEERING_ACCEPTED
```

历史：

```text
HISTORICAL_AS_RECORDED_EVENT = NOT_PROVEN
```

## 结论

```text
ENGINEERING_PASS_CAPABILITY_SCOPED
```

不是 full four-scenario formal pass。

## 尚缺

- STRONG_PULLBACK formal consumer；
- TREND_CONTINUE formal consumer；
- historical AS_RECORDED event；
- current audit 中 event-prior UNKNOWN / D2 prior authenticity re-audit。

这些限制与设计 fail-closed 原则一致。

---

# 17. V4-12｜Structure / Anchor / Support

## 设计目的

D1：

```text
Anchor
coordinate rebase
breakout
pullback
recovery
support / acceptance
old anchor invalidation
```

## 当前

`src/workbench_analysis/v4_12_*`

Accepted capabilities 包括：

```text
ACTIVE_ANCHOR_SELECTOR
ANCHOR_COORDINATE_REBASE
MULTI_ANCHOR_SNAPSHOT
BREAKOUT_EPISODE_CONTINUITY
BREAKOUT_DUPLICATE_GUARD
PER_ANCHOR_PULLBACK_RECOVERY_RETENTION
PER_ANCHOR_SUPPORT_ACCEPTANCE
TIME_COUNTER_SEMANTICS
SOURCE_AUTHORITY_FAIL_CLOSED
```

## 尚缺

```text
HISTORICAL_AS_RECORDED_D1 = NOT_PROVEN

REAL_TARGET_DATE_STRUCTURE_SIGNAL =
DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY
```

Current Audit：

```text
V4_12_REAL_OWNER_CAPABILITY =
NONBLOCKING_VALIDATION_DEBT
```

## 最终

```text
ENGINEERING_PASS_CAPABILITY_SCOPED
```

工程实现完整度高，但不能宣称 historical/real owner 全能力。

---

# 18. V4-13｜Profile Advanced Projection

## 设计目的

```text
Context
LOO
Structure Projection
Full integration
```

## 当前

`src/workbench_analysis/v4_13_*`

已接受：

```text
PROFILE_ADVANCED_PROJECTION
TARGET_EXCLUDED_LOO_CORE
STRUCTURE_READ_ONLY_PROJECTION
COMPONENT_PROVENANCE
REVISION_PUBLICATION
CURRENT_MEMBERSHIP_RELATION
```

## 未完成能力

```text
historical_LOO = NOT_VERIFIABLE
legacy_B2 = NOT_IMPLEMENTED
algorithmic_support_sector = UNKNOWN_REAL_ACCEPTED_CAPABILITY
relative_sector_state = UNKNOWN_REAL_ACCEPTED_CAPABILITY
```

Current Audit：

```text
V4_13_REAL_OWNER_CAPABILITY =
NONBLOCKING_VALIDATION_DEBT
```

## 结论

```text
ENGINEERING_PASS_CAPABILITY_SCOPED
```

---

# 19. V4-14｜Replay Gate B

## 设计目的

```text
ALGORITHM_STATE_REPLAY_PASS
完整D0/D1/D2时序
revision
same-day isolation
previous-session state
rollback
```

## 当前

`src/workbench_analysis/v4_14_*`

Accepted Head：

```text
ALGORITHM_STATE_REPLAY_DEGRADED_PASS
```

已通过：

```text
DETERMINISTIC_REPLAY
FULL_D0_D1_D2_REPLAY
CROSS_PROCESS_PREVIOUS_SESSION
SAME_DAY_REVISION_ISOLATION
REAL_ACCEPTED_SOURCE_REPLAY
ROLLBACK_RECEIPT
```

未授予：

```text
HISTORICAL_PIT_EFFECTIVENESS
```

## 为什么可以通过

设计要求的工程 Replay Gate 已完成。

不能把 reconstructed replay 冒充 historical AS_RECORDED，是正确处理。

## 最终

```text
V4-14 = ENGINEERING_REPLAY_PASS
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

---

# 20. V4-15｜Radar / Cohorts / Settlement

## 设计目的

这是主链进入真实 Forward 前的关键阶段：

```text
字段全登记
Radar
事件样本
完整Validation Cohort
Control assignment
Market/Sector benchmark
Due planner
Price settlement
Outcome revision
Why Now
Readback
```

## 当前代码

```text
src/workbench_analysis/v4_15_radar_cohort.py
src/workbench_analysis/v4_15_settlement.py
src/workbench_analysis/v4_15_settlement_successor.py
src/workbench_analysis/v4_15_persistence.py
```

Accepted Head：

```text
RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED
```

已接受：

```text
RADAR_COHORT_RUNTIME
SETTLEMENT_RUNTIME
PERSISTED_E2E
INDEPENDENT_ORACLE
FORWARD_EVALUATION_PROJECTION
REAL_DM01_DATA_HEAD_REACHABILITY
REAL_DM01_ROW_SCHEMA_ADMISSION
REAL_ACCEPTED_SOURCE_T0_INTEGRATION
REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK
```

## 本轮前置全链路修复

此前发现：
- benchmark contract surface；
- affine validation。

现已修复并通过七项修复外审。

## 仍缺

Current Audit：

```text
REALTIME_ACCEPTED_COHORT_MATURITY
= NONBLOCKING_VALIDATION_DEBT

REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
= NONBLOCKING_VALIDATION_DEBT

V4_15_FWD_ADJ_VECTOR_01
= OPEN_NONBLOCKING_TEST_ENHANCEMENT
```

原因很简单：

```text
真实T+N还没成熟
```

不能用 replay 代替。

## 最终

```text
V4-15_ENGINEERING = PASS
V4-15_REAL_MATURITY = PENDING
```

---

# 21. FEP 总体定位

FEP 是 V4-15 后 optional branch。

设计明确：

```text
E1～E5
不是 V4-16～22 的总前置门
```

FEP 不修改：
- Core；
- Profile；
- Seed；
- eligibility；
- State；
- Radar candidate universe；
- Forward authority。

当前 E1～E5 已：

```text
COMPLETE_FOR_CURRENT_ENGINEERING_SCOPE
```

但：

```text
REAL_OOS = NOT_GRANTED
CHAMPION = NONE
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
FEP_PRODUCTION = UNGRANTED
```

---

# 22. FEP E1｜Dataset / Identity / Registry

## 设计目的

```text
Observation
Feature snapshot
Target registry
完整分母
As-of revisions
Model registry foundation
Prediction slot
DDL
```

## 当前

代码：

```text
src/workbench_analysis/fep_e1/*
```

PostgreSQL 基础：

```text
028_fep_schema_v1.sql
029_fep_append_only_v1.sql
030_fep_validation_cas_v1.sql
031_fep_roles_v1.sql
032_fep_reconstruction_authority_shadow_v1.sql
033_fep_signal_contract_integrity_v1.sql
```

E1 final：

```text
PASS_FINAL_EXTERNAL
47/47 feature mapping
```

## 未授予

```text
REAL_FIRST_OBSERVED_ENTRY
REAL_MATURED_LABEL_EVIDENCE
```

## 结论

```text
ENGINEERING_ACCEPTED
```

---

# 23. FEP E2｜Conditional Statistics Baseline

## 设计目的

```text
日期平权
固定backoff
support
weighted empirical quantile
完整分母
```

## 当前

正式接受 scope：

```text
FIRST_PREWATCH × ABS_RETURN_N:T1
```

并实现：
- event strata；
- exact denominator；
- date-balanced weight；
- support policy；
- deterministic backoff；
- negative matrix。

## 未覆盖

```text
pooled ENTRY
REENTRY
NEW_CONFIRMED
其它target/horizon/scope
```

其中部分受 prior-episode owner gap 影响。

## 结论

```text
ENGINEERING_ACCEPTED_CAPABILITY_SCOPED
```

不是所有 FEP target 都完成。

---

# 24. FEP E3｜Interpretable Model

## 设计目的

```text
time split
purge
regularized interpretable model
calibration
OOD
coherence
experiment registry
```

## 当前

FIRST_PREWATCH:T1 engineering pipeline 通过：
- chronological split；
- purge；
- training-only preprocessing；
- baseline compare；
- one-shot outer；
- OOD/coherence diagnostics。

## 限制

```text
REAL_OOS = NOT_GRANTED
calibration result weak
OOD limitation material
Outer coverage low
model effectiveness not accepted
```

## 结论

```text
MODEL_ENGINEERING_PASS
MODEL_EFFECTIVENESS_PASS = NO
```

这和设计“工程验收 ≠ 有效性”一致。

---

# 25. FEP E4｜Optional Tree Challenger

## 设计目的

可选 challenger。

设计明确：

```text
失败或NO_INCREMENT
都不阻断E5
```

## 当前

E4 engineering pass。

结果：

```text
E2 MAE < E4 MAE < E3 MAE
```

即 E4：
- 比 E3 好；
- 没有击败 E2。

因此：

```text
CHAMPION = false
```

## 结论

```text
E4_ENGINEERING = PASS
E4_INCREMENT_VS_E2 = NO
```

这是设计允许的成功结果。

---

# 26. FEP E5｜Projection / Priority Shadow

## 设计目的

```text
canonical prediction ledger
fine-grained permission
deployment head / CAS
API
rollback
Priority Shadow
按scope OOS gate
```

## 当前

经历 E5 canonical integration 及后续修复后：

```text
E5_B01 canonical ledger = CLOSED_PASS
E5_B02 canonical identity = CLOSED_PASS
E5_B03 permission/deployment = CLOSED_PASS
target metadata binding = CLOSED_PASS
signal contract binding = CLOSED_PASS
```

七项全链路 hardening 中又完成：
- `core_signal_contract_id` DB semantic guard；
- legacy `fep_e5_engineering.*` ledger isolation。

## 当前权限

```text
FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_DAILY_PRIORITY_SHADOW = NOT_GRANTED
FIRST_OBSERVED = NOT_GRANTED
REAL_OOS = NOT_GRANTED
CHAMPION = NONE
```

## 结论

```text
FEP_E1_TO_E5 =
COMPLETE_FOR_CURRENT_ENGINEERING_SCOPE
```

不能写：

```text
FEP production ready
```

---

# 27. V4-16｜Realtime Shadow Dual-Run

## 设计目标

```text
PIT_OBSERVED + SHADOW
真实冻结日账本
每日运行 settlement
Legacy production继续
```

## 当前工程实现

已存在：
- V4-16 contract package；
- runtime engineering accepted head；
- real Shadow SQLite schema；
- slot/runtime policy；
- DM01 R4/R4R1/R4R2 bridge；
- capability resolution；
- durable settlement queue；
- integrity sidecars；
- exact activation-head restart；
- queue CAS/idempotency；
- rollback/restart。

七项全链路修复现已全部通过。

## 当前真实状态

```text
runtime_authorized = false
real_shadow_authorized = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

V4_16 = false
```

## 为什么不能把 V4-16 写 PASS

因为 §78 要求的是：

```text
Realtime Shadow Dual-Run
```

而不仅是“写完 runtime”。

当前还没有一次真实 accepted Shadow publication。

## 本轮排除

A08 正在执行，本报告不裁决其 propagation。

## 结论

```text
V4-16_ENGINEERING = READY
V4-16_STAGE_FINAL = NOT_COMPLETE
```

---

# 28. V4-17｜Shadow UI

## 设计目的

```text
同context token
展示完整已实现组件
只读
不写production Focus
```

## 当前

外审：

```text
PASS_FINAL_V4_17_SHADOW_UI_ENGINEERING_SCOPED
```

已验证：
- GET-only；
- no real data fallback；
- simulation isolation；
- immutable context token；
- future real readback path；
- U01～U18；
- existing UI regression；
- storage schema compatibility。

## 未完成

```text
V4_17_REAL_SHADOW_READBACK = NOT_GRANTED
V4_17_FINAL_ACCEPTANCE = NOT_GRANTED
```

因为：

```text
REAL_SHADOW_OBSERVATIONS = 0
```

## 结论

```text
ENGINEERING_EXTERNALLY_ACCEPTED
REAL_END_TO_END_PENDING
```

---

# 29. V4-17G｜Shadow Stable / Provisional Forward Gate

## 设计目的

按 capability：

```text
Shadow stability
最低Forward
rollback
真实样本
```

历史 replay 不能凑天数。

## 当前

```text
V4_17G = NOT_GRANTED
```

没有真实 Shadow session，自然无法执行稳定门。

## 结论

```text
REAL_GATE_PENDING
```

不是代码 bug。

---

# 30. V4-18｜Migration Replay Gate

## 设计目标

真正执行：

```text
MIGRATION_REPLAY_PASS
```

必须处理：
- predecessor；
- open episode；
- pending settlement；
- namespace；
- user state；
- cutover gap；
- rollback；
- idempotency。

## 当前

V4-18 contract design 已经过外部验收。

当前 successor：

```text
config/v4_18_migration_replay_contract_v1_3.json
```

仍明确：

```text
mode = CONTRACT_DESIGN_ONLY
implementation_entry = BLOCKED_WAIT_REAL_SHADOW_GATE
```

并且六个未来 interface：

```text
MigrationSnapshotReader
MigrationPlanBuilder
MigrationReplayWriter
MigrationGapReconciler
MigrationRollbackController
MigrationIndependentOracle
```

全部：

```text
implemented = false
```

## 一个治理注意点

V1_2 设计曾外审接受；当前 V1_3 是后续 namespace/FEP inventory successor，仍保持设计-only语义。

在真正进入 V4-18 runtime 前，必须把当时最终 successor exact external acceptance 固定下来。

## 结论

```text
CONTRACT_DESIGN = PASS
RUNTIME_IMPLEMENTATION = NOT_STARTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
```

---

# 31. V4-19｜Focus Source Cutover

## 设计目标

只有 capability 同时满足：

```text
Shadow Stable
Forward Gate
Migration Replay
dependencies
```

才把 accepted V4 source 进入 production Focus。

## 当前

Contract design external PASS。

但：

```text
production_routing_writer_implemented = false
production_databases_opened = false
Focus source cutover = false
production_permission[*] = false
```

## 结论

```text
CONTRACT_DESIGN_PASS
ACTUAL_CUTOVER_NOT_IMPLEMENTED
```

这符合实施顺序。

---

# 32. V4-20｜Default UI Cutover

## 设计目标

只有已经获得 production permission 的模块默认使用 V4。

其它模块继续：

```text
LEGACY_PRODUCTION
or
explicit SHADOW
```

支持 mixed page，不允许 global “V4 production” 假标签。

## 当前

Contract design 已外审接受。

当前：

```text
DEFAULT_UI_CUTOVER = false
production_permission[*] = false
```

Default production UI 继续 Legacy。

## 结论

```text
CONTRACT_DESIGN_PASS
RUNTIME_CUTOVER_NOT_STARTED
```

---

# 33. V4-21｜Continued Forward Observation

## 设计目标

继续积累：

```text
Shadow evidence
Production evidence
Forward outcomes
```

不在这一阶段第一次开发 Settlement。

## 当前

Contract design / native-session repair 已通过。

已解决：
- Shadow native session owner；
- native status；
- missed/evaluable semantics；
- production session authority formalization。

但：

```text
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED
```

没有 real observation writer 被启用。

## 结论

```text
CONTRACT_DESIGN_PASS
REAL_EXECUTION_NOT_STARTED
```

---

# 34. V4-22｜Independent Audit

## 设计目标

最终独立审计：
- data；
- algorithm；
- publication；
- migration；
- UI；
- Forward；
- rollback；
- open items。

## 当前

V4-22 audit contract design、fail-closed schema、closure evidence、item-level authority validation 已经过多轮修复与外审。

当前：

```text
V4_22_CONTRACT_DESIGN = PASS
V4_22_FINAL_AUDIT_ENTRY = BLOCKED_WAIT_REAL_GATES
V4_22_FINAL_PASS = NOT_GRANTED
```

## 为什么不能最终 PASS

真实前置尚未发生：

```text
REAL_SHADOW_OBSERVATIONS = 0
V4_17G = NOT_GRANTED
MIGRATION_REPLAY_PASS = NOT_GRANTED
production_permission[*] = false
Focus_source_cutover = false
DEFAULT_UI_CUTOVER = false
REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED
```

## 结论

```text
AUDIT_FRAMEWORK = PASS
PROJECT_FINAL_ACCEPTANCE = NOT_GRANTED
```

---

# 35. 当前 Current Audit Head 中仍需保留的真实缺口

以下不是本轮新发现 bug，而是当前正式账本中仍未关闭的能力。

> `A08_CURRENT_RUNTIME` 按用户要求排除。

## 35.1 Amount-A / V4-08

```text
A04_H21_CONSUMER
= ACCUMULATION_CONTINUES

A04_HISTORICAL_AMOUNT_A
= BLOCKED_AFFECTED_SCOPE
```

影响：

```text
AMOUNT_A_H21_FORMAL_CONSUMER
HISTORICAL_AMOUNT_A_FORMAL_CONSUMER
```

---

## 35.2 Historical PIT

```text
HISTORICAL_PIT_EFFECTIVENESS
= PERMANENT_CAPABILITY_LIMITATION
```

禁止：

```text
reconstruction -> AS_RECORDED
```

---

## 35.3 Pre-capture / Forward accumulation

```text
A03 = ACCUMULATION_CONTINUES
A07 = PERMANENT_CAPABILITY_LIMITATION
```

这些不阻断独立工程，但阻断对应 production claim。

---

## 35.4 V4-10～14 historical / production re-audit

仍有：

```text
AUD_R3C_ACCEPTED_SUSPENSION_STATE_ADMISSION_01
AUD_R3C_ADJUSTMENT_COORDINATE_EXACTNESS
AUD_R3C_D2_ADMISSION_AND_PRIOR_AUTHENTICITY
AUD_R3C_EVENT_PRIOR_UNKNOWN_01
AUD_R3_GIT_EXACT_BYTE_PORTABILITY
AUD_R3_REAL_WINDOW_AND_EPISODE_CAPABILITY
```

Current Audit Head 明确：

```text
accepted V4-10..15 remain PASS_KEEP_NO_REOPEN
```

所以它们是 production/capability re-audit debt，不是“10～15开发失败”。

---

## 35.5 V4-12 / 13 real owner

```text
V4_12_REAL_OWNER_CAPABILITY
V4_13_REAL_OWNER_CAPABILITY
```

仍为 scoped validation debt。

---

## 35.6 V4-15 real maturity

```text
REALTIME_ACCEPTED_COHORT_MATURITY
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME
```

必须等真实市场时间。

---

# 36. 数据结构与 migration 交叉审计结论

当前结构与设计的核心层次是一致的。

## Foundation

```text
001～009
publication / revision / namespace / prior-session / source guard
```

## Identity / Lifecycle

```text
010～012
```

## Supplemental / Turnover

```text
013～014
```

## Seed

```text
015
```

## Sector / Rotation

```text
016～020
```

## PREWATCH

```text
021
025
```

## State

```text
022～024
```

## Confirmation

```text
026～027
```

## FEP

```text
028～033
```

028～032 保持 immutable；033 为 additive signal-contract integrity hardening。

## V4-16 Shadow

独立 SQLite migrations：

```text
v4_16_r24_real_shadow_v1.sql
v4_16_settlement_queue_v2.sql
v4_16_real_shadow_integrity_v2.sql
```

这与设计“Core/PostgreSQL accepted ledger”和“Shadow独立 namespace + durable settlement”是一致的。

---

# 37. 线上模型与 Codex 线下模型的交叉审计结论

本轮真正需要回答的是：

> Codex 是否一路开发偏离了它自己设计的系统？

结论：

```text
没有发现主架构偏航。
```

主要原因：

1. Drive 设计和 repo 设计逐字一致；
2. V4_STAGE_ACCEPTED_HEAD 明确只到 00～15；
3. 00～15 的 capability-scoped/degraded 状态与设计 fail-closed 原则一致；
4. V4-10 没有被错误要求提前实现完整DAG；
5. V4-03 Sector ownership 的迁移有正式 amendment；
6. V4-06 Supplemental 没有被错误变成 Core 前置；
7. V4-11 对无法纯化 legacy detector 保持 diagnostic，符合设计；
8. V4-14 没有用 reconstructed replay 冒充 historical PIT；
9. V4-15 Settlement 在 Shadow 前已工程实现；
10. FEP 没有回写 Core/PRIORITY_V1；
11. FEP E4 没有因为 tree 不增益就阻断 E5；
12. V4-16～22 没有用“合同设计通过”冒充“真实运行完成”；
13. Production/Focus/UI 均仍保持 false；
14. 七项代码/合同 hardening 已全部收口。

---

# 38. 本轮最重要的纠偏：哪些阶段绝不能写“已经全部完成”

以下不能写成 FULL COMPLETE：

```text
V4-08
V4-11
V4-12
V4-13
V4-14 historical PIT
V4-15 real maturity

FEP E2/E3/E5 real/effectiveness/production

V4-16
V4-17 final
V4-17G
V4-18 runtime
V4-19 cutover
V4-20 cutover
V4-21 real observation
V4-22 final audit
```

这并不代表它们“开发失败”。

正确语言分别是：

```text
SCOPED_ENGINEERING_PASS
REAL_GATE_PENDING
CONTRACT_DESIGN_PASS_IMPLEMENTATION_PENDING
NOT_GRANTED
```

---

# 39. 当前真正的项目进度

如果按“代码工程是否基本开发完成”：

```text
00～15：基本完成
FEP E1～E5：当前scope完成
16：runtime engineering完成
17：Shadow UI engineering完成
18～22：设计/合同基本完成
```

如果按“整个 V4 产品是否已经完成”：

```text
没有。
```

真正尚未经历的主链是：

```text
A08 propagation（本轮排除）
        ↓
R25 / First Real Shadow
        ↓
真实Shadow readback
        ↓
V4-17G capability stable / forward gates
        ↓
V4-18 migration replay 实际实现与执行
        ↓
V4-19 Focus capability cutover
        ↓
V4-20 Default UI capability cutover
        ↓
V4-21 continued real observation
        ↓
V4-22 final independent audit
```

---

# 40. 对当前开发策略的建议

## 40.1 不要重做 00～15

除非未来新的精确证据推翻 accepted contract，否则：

```text
NO GLOBAL REOPEN
```

现有 open debt 按 affected capability 处理。

## 40.2 不要为了“阶段全绿”补造历史数据

特别禁止：

```text
reconstructed -> AS_RECORDED
historical simulation -> REAL
PIT feature -> FIRST_OBSERVED prediction
UNKNOWN -> FALSE/0
```

## 40.3 18～22 不要继续只做文档

它们的 contract design 已经足够。

真实 Shadow gate 一旦满足，重点应从：

```text
再写合同
```

切换到：

```text
真实 runtime execution
真实 receipts
真实 replay
真实 cutover
真实 rollback
```

## 40.4 FEP 暂时不要继续加模型

E2 baseline 当前仍是最强已接受工程 baseline。

当前更重要的是：

```text
真实FIRST_OBSERVED
真实matured labels
真实OOS
```

而不是继续堆 challenger。

---

# 41. 唯一最终裁决

```text
CROSS_MODEL_FULL_STAGE_AUDIT_R1 =
PASS_WITH_EXPLICIT_INCOMPLETE_REAL_GATES

DESIGN_VS_REPO =
NO_GLOBAL_ARCHITECTURAL_DIVERGENCE_FOUND

V4_00_TO_V4_15 =
ACCEPTED_CONTIGUOUS
WITH_CAPABILITY_SCOPED_LIMITATIONS

FEP_E1_TO_E5 =
ENGINEERING_COMPLETE_FOR_CURRENT_SCOPE

V4_16_TO_V4_22 =
NOT_FULLY_COMPLETE

MAIN_REASON =
REAL_SHADOW_MIGRATION_CUTOVER_FORWARD_FINAL_AUDIT_GATES_NOT_YET_EXECUTED

NEW_P0_P1_CODE_CONTRACT_BUG_OUTSIDE_A08 =
NONE_FOUND_IN_THIS_AUDIT

A08_CURRENT_RUNTIME =
EXCLUDED_BY_USER_CURRENTLY_EXECUTING
```

最准确的项目描述是：

> **主线代码骨架和算法体系已经基本开发完成，并且总体遵循 Codex 线下设计方案；当前已经从“继续大规模开发算法”进入“真实 Shadow → 迁移 → capability cutover → Forward accumulation → final audit”的阶段。**  
>  
> **但不能把 V4-18～22 的合同设计完成，等价成实际迁移、Focus/UI生产切换和最终验收已经完成。**  
>  
> **FEP 也只能称“当前 engineering scope 完成”，不能称生产预测系统完成。**

---

# 42. 后续恢复入口

本报告之后的主恢复入口：

```text
1. 完成并验收 A08 Current Runtime governance propagation；
2. 重建 R25 packet；
3. First Real Shadow；
4. V4-17 real readback；
5. V4-17G；
6. V4-18 runtime implementation + migration replay；
7. V4-19 capability Focus cutover；
8. V4-20 capability UI cutover；
9. V4-21 real continued observation；
10. V4-22 final independent audit。
```

在第 1 项完成前，不应重开 00～15 或 FEP 的已接受工程实现。

**文档结束**

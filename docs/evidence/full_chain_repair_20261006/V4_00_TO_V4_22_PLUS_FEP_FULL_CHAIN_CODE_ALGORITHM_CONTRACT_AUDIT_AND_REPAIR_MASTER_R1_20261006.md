# 大A市场结构研究系统 V4｜V4-00～V4-22 + FEP 全链路代码 / 算法 / 合同 / 数据结构一致性审计与修复总任务卡 R1

> 日期：2026-10-06  
> 项目：大A市场结构研究系统 V4  
> Repository：`NanOns/a-share-market-structure-research`  
> Branch：`codex/v4-system-reform`  
> 独立审计基线 HEAD：`20a1373cd26b3687a6f2b43b16aa3e91351871d8`  
> 设计基线：`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`  
> Design ID：`DA-MSR-V4.2.2-CODEX-REV4-FEP-R2`  
> 审计范围：V4-00～V4-22、DM01/R25 真实运行桥、FEP E1～E5  
> 文档性质：**独立全链路代码算法合同级审计 + Codex 统一修复任务卡**  
> 目标：在不推翻已接受历史事实、不伪造真实样本、不提前开放生产权限的前提下，把当前代码与最新版正式设计及明确批准的后续变更重新对齐。

---

# 0. Codex 执行前必须先读

本轮不是新增功能设计轮，也不是重新实现 V4。

本轮只做：

```text
DESIGN / CONTRACT
        ↓
CURRENT ACCEPTED AUTHORITY
        ↓
CURRENT CODE / ALGORITHM
        ↓
CURRENT DATA STRUCTURE / MIGRATION
        ↓
CURRENT RUNTIME ADMISSION
        ↓
TEST / NEGATIVE VECTOR / READBACK
```

逐项修复本审计发现的真实偏差。

除本文明确列出的修复点外：

```text
不得重写已 Accepted 的历史业务算法
不得重新选择历史样本
不得修改历史 outcome
不得制造 PIT_OBSERVED
不得制造 FIRST_OBSERVED
不得制造 REAL_OOS
不得制造 REAL_SHADOW_OBSERVATIONS
不得开放 Production / Focus / Default UI
不得自动创建 V4_16～V4_22 Accepted Head
不得把 contract-design PASS 改称 production PASS
不得因为测试通过移动正式 Accepted Head
```

任何已有 Accepted Head / migration / contract 的修改都必须遵守：

```text
历史版本 immutable
→ additive successor
→ exact parent binding
→ 独立外审
```

---

# 1. 本次独立总裁决

```text
FULL_CHAIN_CODE_ALGORITHM_CONTRACT_AUDIT =
REPAIR_REQUIRED_BEFORE_FIRST_REAL_SHADOW

V4_00_TO_V4_15_ACCEPTED_HISTORY =
PASS_KEEP_NO_GLOBAL_REOPEN

FEP_E1_TO_E5_ENGINEERING_HISTORY =
PASS_KEEP_CAPABILITY_SCOPED

V4_16_FIRST_REAL_SHADOW_READINESS =
BLOCKED_BY_CURRENT_RUNTIME_REPAIR_ITEMS

V4_17_TO_V4_22_DESIGN_CHAIN =
PASS_KEEP_REAL_GATES_PENDING

FEP_PRODUCTION =
UNGRANTED

PRODUCTION =
UNGRANTED

FOCUS_CUTOVER =
false

DEFAULT_UI_CUTOVER =
false
```

本审计没有发现需要推翻 V4-00～V4-15 Accepted Chain 的证据。

但在**首次真实 Shadow 之前**，当前代码仍有机器级 capability gating、settlement runtime、Shadow ledger 约束等缺口；V4-15 Forward 与 FEP 也存在合同级一致性债务。

---

# 2. 严重级别

```text
P0 =
首次真实 Shadow / 实时账本运行前必须关闭；
存在 fail-open、错误 authority、真实账本污染或运行路径失配风险。

P1 =
当前 engineering history 可保留；
但在对应真实 capability / production / settlement / FEP permission 开启前必须关闭。

P2 =
当前不形成错误业务结果；
但存在双重实现、未来误调用、治理歧义或维护风险，应在主线稳定前硬化。

REAL_GATE_PENDING =
不是 bug。
必须等待真实交易日、真实 accepted source 或规定的连续样本。
禁止用代码修复“解决”。
```

---

# 3. 阶段 00～22 + FEP 逐项验收矩阵

| 阶段 | 当前审计状态 | 代码 / 算法 / 合同级结论 | 本轮处理 |
|---|---|---|---|
| V4-00 | PASS_KEEP | Phase0 旧 R5 receipt 的 PENDING 已被后续正式 external acceptance / authority normalization 明确 supersede；不存在当前双重权威 bug | 不重开 |
| V4-01 | PASS_KEEP_WITH_LIMITATION | Identity 主链可保留；历史 legal lifecycle/type 的非 PIT 能力限制已被正式保留 | 不重开 |
| V4-02 | PASS_KEEP | 当前 2026-09-30 Data Head 已由后续 DM01/A10/A12 修复链正式推进；10/1 旧 blocker 不再作为当前 bug | 不重开旧 A12 |
| V4-03 | PASS_KEEP_AMENDED | amended accepted head、PIT/replay/field ownership继续有效 | 不重开 |
| V4-04 | PASS_KEEP_SCOPED | Amount-A producer 已 scoped accepted；H21 formal consumer 与 historical Amount-A 仍按 Current Audit Head 限制 | 保留真实门 |
| V4-05 | PASS_KEEP_DEGRADED_SCOPE | Replay A / factors / Core 能力边界明确 | 不重开 |
| V4-06 | PASS_KEEP_DEGRADED_OPTIONAL | BaoStock strict binding 等降级为已知能力边界，不是主链 bug | 不重开 |
| V4-07 | PASS_KEEP | Base Seed 算法/owner 与 UNKNOWN 传播未发现新硬错误 | 不重开 |
| V4-08 | PASS_KEEP_CAPABILITY_SCOPED | Sector/Rotation accepted scope 与 Amount-A 限制保持 | 不重开 |
| V4-09 | **OPEN CURRENT-RUNTIME AUTHORITY** | 历史 hardening PASS，但 `A08_CURRENT_RUNTIME` 仍为 `OPEN_EXTERNAL_REAUDIT`；V4-16 blocker 映射存在机器级缺陷 | **P0-01** |
| V4-10 | PASS_KEEP | Reducer interface/accepted AST 后续被 V4-14 full DAG 消费；未发现新业务算法漂移 | 不重开 |
| V4-11 | PASS_KEEP_CAPABILITY_SCOPED | D0 Confirmation / event UNKNOWN 边界保持；部分 R3C 项仍待 re-audit | Governance debt |
| V4-12 | PASS_KEEP_CAPABILITY_SCOPED | Structure/anchor/support 主逻辑保持；部分 adjustment/real-window re-audit debt 仍存在 | Governance debt |
| V4-13 | PASS_KEEP_CAPABILITY_SCOPED | Advanced projection / LOO 能力边界保持 | 不重开 |
| V4-14 | PASS_KEEP | Full D0/D1/D2 replay engineering chain 可保留；historical PIT effectiveness 仍 NOT_GRANTED | 不重开 |
| V4-15 | **REPAIR_REQUIRED** | Forward benchmark 返回结构与 affine validation 与冻结合同不完全一致 | **P1-04/P1-05** |
| V4-16 | **REPAIR_REQUIRED_BEFORE_REAL_SHADOW** | capability blocker 解析、settlement successor/worker、real Shadow DB semantic integrity 仍有缺口 | **P0-01/P0-02/P1-03** |
| V4-17 | PASS_KEEP_ENGINEERING | Shadow UI engineering 已接受；真实 readback 尚无真实 publication | REAL_GATE_PENDING |
| V4-18 | PASS_KEEP_DESIGN | Migration replay contract design 已接受；runtime implementation 正确等待 real Shadow gate | REAL_GATE_PENDING |
| V4-19 | PASS_KEEP_DESIGN | Focus capability-scoped cutover design 已接受 | REAL_GATE_PENDING |
| V4-20 | PASS_KEEP_DESIGN | Default UI mixed Legacy/V4/Shadow design 已接受 | REAL_GATE_PENDING |
| V4-21 | PASS_KEEP_DESIGN | Continued Forward contract 已接受；真实 observation 尚未开始 | REAL_GATE_PENDING |
| V4-22 | PASS_KEEP_DESIGN | Independent audit contract design 已接受；Final Pass 等待真实 gates | REAL_GATE_PENDING |
| FEP-E1 | PASS_KEEP_ENGINEERING | dataset / label / three-time authority / denominator 设计保持 fail-closed | 不重开 |
| FEP-E2 | PASS_KEEP_ENGINEERING | conditional statistics、date-balanced weight、fixed backoff 未发现新硬错误 | 不重开 |
| FEP-E3 | PASS_KEEP_ENGINEERING | interpretable model time split / Outer boundary 保持 | 不重开 |
| FEP-E4 | PASS_KEEP_DIAGNOSTIC | tree challenger bounded search、seen-Outer diagnostic boundary 保持 | 不重开 |
| FEP-E5 | **PASS_KEEP + HARDENING REQUIRED** | canonical `fep.*` 已闭环，但 signal contract DB hardening 未完成，legacy parallel schema 仍可执行 | **P1-06/P2-07** |

---

# 4. P0-01｜V4-16 blocked scope 使用 issue_id 与 capability 做错误集合比较，当前机器 blocker 可失效

## 4.1 证据

当前：

`config/v4_16_runtime_activation_authority_v3.json`

```json
"allowed_capabilities": [
  "PURE_CORE_STOCK"
],
"blocked_capabilities": [
  "A04_H21_CONSUMER",
  "A04_HISTORICAL_AMOUNT_A",
  "A08_CURRENT_RUNTIME"
]
```

`config/v4_16_runtime_dependencies_v4.json` 与：

`config/v4_16_r25_packet_preflight_v2.json`

沿用相同结构。

但 Current Audit Head：

`data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.json`

明确：

```text
A08_CURRENT_RUNTIME
affected_capabilities =
[V4_09_N01_CURRENT_RUNTIME_PREWATCH]

current_state =
OPEN_EXTERNAL_REAUDIT

blocks_affected_capability_in_shadow =
true
```

同理：

```text
A04_H21_CONSUMER
→ AMOUNT_A_H21_FORMAL_CONSUMER

A04_HISTORICAL_AMOUNT_A
→ HISTORICAL_AMOUNT_A_FORMAL_CONSUMER
```

这些是：

```text
issue_id
```

不是 runtime capability token。

当前 real runtime 继承路径中使用类似：

```python
not set(requested_capabilities) & set(deps["blocked_capabilities"])
```

而 requested scope 是：

```text
PURE_CORE_STOCK
```

结果：

```text
PURE_CORE_STOCK
∩
A08_CURRENT_RUNTIME
=
∅
```

即：

> blocker 被记录了，但不能通过这个集合运算真正阻断其 affected capability。

R25 preflight 当前只验证：

```python
set(deps["blocked_capabilities"]) == expected_issue_ids
```

并没有把：

```text
issue_id
→ affected_capabilities
→ requested capability dependency graph
```

机器解析出来。

## 4.2 根因

把两个完全不同的 identity domain 混在一个字段：

```text
blocked issue ids
vs
runtime capability ids
```

同时缺少 machine-resolved dependency graph。

## 4.3 风险

这是 fail-open 风险。

最危险的是：

```text
A08_CURRENT_RUNTIME
```

因为当前 V4-09 historical hardening 已通过，但：

```text
current_runtime_accepted = false
current_runtime_external_acceptance = PENDING
```

Current Audit Head 仍要求该 affected capability 在 Shadow 中 fail-closed。

如果 `PURE_CORE_STOCK` 的实时 owner projection 实际消费当前 PREWATCH，而机器 gate 不解析这个依赖，就可能在未关闭 A08_CURRENT_RUNTIME 前进入真实 Shadow。

## 4.4 必须修复

不要再使用：

```json
"blocked_capabilities": [
  "A08_CURRENT_RUNTIME"
]
```

表示 issue。

改成至少：

```json
"blocked_issue_ids": [
  "A04_H21_CONSUMER",
  "A04_HISTORICAL_AMOUNT_A",
  "A08_CURRENT_RUNTIME"
]
```

并新增版本化机器投影：

```text
runtime_capability_dependency_graph
current_audit_issue_resolution
effective_blocked_runtime_capabilities
```

推荐结构：

```json
{
  "issue_id": "A08_CURRENT_RUNTIME",
  "current_state": "OPEN_EXTERNAL_REAUDIT",
  "affected_capabilities": [
    "V4_09_N01_CURRENT_RUNTIME_PREWATCH"
  ],
  "blocks_affected_capability_in_shadow": true
}
```

再由：

```text
requested capability
→ required sub-capabilities
→ current open audit issue
```

计算最终 admission。

必须明确决定：

```text
PURE_CORE_STOCK
```

是否依赖：

```text
V4_09_N01_CURRENT_RUNTIME_PREWATCH
```

若依赖：

```text
A08_CURRENT_RUNTIME 未关闭
→ R25 / Real Shadow 对该 scope BLOCKED
```

若不依赖：

必须通过正式 capability contract 证明它完全不消费该结果，而不是靠 token 名字猜。

## 4.5 验收

至少增加：

```text
CAP-BLOCK-01
open issue + exact affected capability
→ BLOCK

CAP-BLOCK-02
open issue + transitive dependent capability
→ BLOCK

CAP-BLOCK-03
open issue + unrelated capability
→ ALLOW only if all own gates pass

CAP-BLOCK-04
closed/superseded issue
→ no stale block

CAP-BLOCK-05
unknown issue id
→ fail closed

CAP-BLOCK-06
affected_capabilities drift vs Current Audit Head digest
→ fail closed

CAP-BLOCK-07
A08_CURRENT_RUNTIME open + runtime path actually consumes current PREWATCH
→ R25 cannot emit READY

CAP-BLOCK-08
A04 H21 still accumulating
→ no AMOUNT_A_H21 formal consumer activation
```

## 4.6 状态

```text
P0
MUST_CLOSE_BEFORE_FIRST_REAL_SHADOW
```

---

# 5. P0-02｜V4-16 Settlement runtime 未完整升级到 R4R2/V4 authority，且 durable queue/claim/ack 语义未真正落地

## 5.1 设计要求

`config/v4_16_settlement_worker_contract_v1.json`

冻结：

```text
execution_order =
ACCEPTED_SHADOW_PUBLICATION
→ DUE_PLANNER
→ DUE_QUEUE_OUTBOX
→ ACCEPTED_FUTURE_DATA_HEAD
→ SETTLEMENT
→ APPEND_EVALUATION_REVISION
→ READBACK
```

并要求：

```text
delivery = AT_LEAST_ONCE
claim = COMPARE_AND_SET_QUEUE_ITEM
ack = ONLY_AFTER_IMMUTABLE_RESULT_REVISION_ACCEPTED
failure = RETRY_WITH_BACKLOG_REASON_NO_SOURCE_FALLBACK
```

V4.2.2 §46 同样明确：

```text
V4-16 开始每日结算
Focus/UI 不得限制结算
```

## 5.2 当前实现缺口 A：settlement-only restart 仍绑定 V3

`scripts/v4_16_go_forward_shadow_runtime.py`

中的：

```python
class SettlementObligationController:
```

仍硬编码：

```python
self.dependency_path =
"config/v4_16_runtime_dependencies_v3.json"
```

并使用历史：

```text
GoForwardInputAuthority
```

而当前正式 real startup 是：

```text
scripts/v4_16_go_forward_shadow_runtime_r4r2.py
config/v4_16_runtime_dependencies_v4.json
config/v4_16_go_forward_input_authority_v1_1.json
R25 exact target-session bridge
```

R4R2 文件只 successor 主 `RealShadowController`，没有 successor settlement-only controller。

## 5.3 当前实现缺口 B：没有与冻结合同等价的 durable worker

当前主 runtime 可以：

```text
写 due fact
调用 settle(...)
```

但本审计未找到正式 successor runtime 中与以下语义等价的 durable machine worker：

```text
claim
lease / ownership
CAS
ack
backlog
retry reason
at-least-once delivery
exact result idempotency
```

`config/v4_16_settlement_worker_contract_v1.json` 自身仍明确：

```json
"runtime_implemented": false
```

这说明：

> Settlement contract 已冻结，但真实 worker 尚未完成正式实现。

## 5.4 风险

首次 Shadow 当天可能尚无 T+1 到期结果，但一旦进入后续交易日：

```text
real enrollment
→ due horizon
→ process restart / worker retry
```

当前可能出现：

- settlement-only restart 读取 stale V3 dependency；
- 正常 due 无法恢复；
- 重试缺少 durable claim/ack；
- 多 worker 情况重复结算；
- backlog 没有 machine state；
- acceptance 与 ack 不是同一受控事务语义。

## 5.5 修复方法

建立 successor：

```text
V4_16_SETTLEMENT_WORKER_RUNTIME_V2
```

不要修改旧 V1 历史合同。

至少实现：

```text
SettlementObligationControllerR4R2
or
versioned dependency injection
```

必须绑定：

```text
runtime_dependencies_v4
go_forward_input_authority_v1_1
DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1
R25 target-session bridge
current accepted activation authority
exact accepted future Data Head
```

并实现 durable queue：

```text
due_queue
claim_owner
claim_version
claim_at
retry_count
backlog_reason
evaluation_source_digest
accepted_outcome_revision
ack_at
```

推荐 CAS：

```text
READY
→ CLAIMED(version+1)
→ SETTLED
→ ACKED
```

同一个：

```text
queue_key
+
evaluation_source_digest
```

重复执行必须返回同一结果或明确 idempotent receipt。

新的 evaluation source digest：

```text
append new evaluation revision
```

不得修改旧 revision。

## 5.6 验收

至少：

```text
SETTLE-R4R2-01
first real enrollment → due generated

SETTLE-R4R2-02
process restart → exact due restored

SETTLE-R4R2-03
old V3 dependency → rejected for new R4R2 real DB

SETTLE-R4R2-04
two workers same queue item → one CAS winner

SETTLE-R4R2-05
crash after claim before result → retry safe

SETTLE-R4R2-06
crash after result before ack → idempotent re-read/ack

SETTLE-R4R2-07
same evaluation source digest rerun → no duplicate revision

SETTLE-R4R2-08
corrected source digest → append revision

SETTLE-R4R2-09
pre-due source read → forbidden

SETTLE-R4R2-10
Focus/UI absence → settlement still executes

SETTLE-R4R2-11
stop new Shadow acceptance → existing due obligations still settle
```

## 5.7 状态

```text
P0
MUST_CLOSE_BEFORE_FIRST_REAL_SHADOW_AUTHORIZATION
```

至少必须在 first real Shadow authorization 时证明 worker 已可在下一 due session 安全恢复。

---

# 6. P1-03｜Real Shadow SQLite ledger 的 DB-level semantic integrity 弱于设计

## 6.1 当前 schema

`migrations/v4_16_r24_real_shadow_v1.sql`

使用：

```text
facts(
  kind,
  id,
  namespace,
  execution_mode,
  evidence_origin,
  payload JSON,
  digest
)
```

并已有：

```text
append-only
storage origin guard
unique logical enrollment
unique slot revision
unique publication revision
unique due
unique observation revision
observation predecessor trigger
```

这些是正确的。

## 6.2 与设计仍有差距

REV4 / V4-16 storage design要求：

```text
exact publication
model lineage
source digest
state lineage
cohort
settlement/outbox
```

可 fail-closed 关联。

当前 DB 本身没有充分约束：

```text
publication → accepted slot
publication → source manifest
enrollment → exact owner logical event
enrollment → accepted realtime admission
realtime_admission → exact accepted slot revision
due → exact accepted enrollment + frozen_t0
outcome → exact due + evaluation_source_digest
state → publication/model/state lineage
activation → exact accepted authority
```

这些大多依赖 Python 在一个特定调用路径里检查。

## 6.3 根因

为了早期快速实现使用 generic JSON fact ledger，业务引用没有全部提升到 DB-level constraints / triggers。

## 6.4 风险

当前受控 Python 路径正常时不会立即出错。

但：

```text
未来新 worker
维护脚本
异常恢复
人工修复工具
另一条 db.append 调用
```

都可能写入：

```text
origin 正确
但业务引用错误
```

的 orphan fact。

这种错误进入 append-only ledger 后很难修复。

## 6.5 修复

旧 migration 不修改。

新增 versioned successor migration。

两种方案均可：

### A. 推荐：关键 identity 提升为列

至少对：

```text
slot
publication
manifest
enrollment
realtime_admission
due
outcome
state
activation
```

建立 typed sidecar/reference table。

### B. 保留 JSON ledger，但加 per-kind triggers

例如：

```text
kind=due
→ payload.enrollment_id 必须存在 accepted enrollment

kind=realtime_admission
→ slot_id/revision 必须存在 ACCEPTED_ON_TIME slot

kind=publication
→ slot_id/revision/source_manifest_digest exact match

kind=outcome
→ due identity + evaluation source identity 必须存在
```

## 6.6 验收

必须直接对 DB 做 negative insert：

```text
orphan publication
orphan enrollment
wrong slot revision
wrong logical_event_id
orphan due
wrong horizon
outcome without due
outcome wrong evaluation source
state wrong model lineage
realtime admission wrong source manifest
```

所有必须由 DB 自身 reject，不能只靠 application layer reject。

## 6.7 状态

```text
P1
MUST_CLOSE_BEFORE_REAL_LEDGER_ACCUMULATION_BECOMES_LONG_LIVED
```

建议和 P0-02 同一轮处理。

---

# 7. P1-04｜V4-15 Forward benchmark runtime 输出字段与冻结合同不一致

## 7.1 设计合同

`config/v4_15_forward_market_benchmark_contract_v1.json`

要求字段：

```text
benchmark_id
benchmark_members
initial_weights
fixed_shares
benchmark_constituent_policy
benchmark_endpoint_coverage
benchmark_missing_weight
benchmark_suspended_weight
benchmark_delisted_weight
benchmark_unknown_weight
benchmark_valuation_coverage
benchmark_marked_weight
benchmark_quality
observed_contribution
relative_market_return
relative_market_return_marked
quote_age
quote_trade_date
```

Sector：

`config/v4_15_forward_sector_benchmark_contract_v1.json`

要求独立：

```text
sector_benchmark_id
sector_members
relative_sector_return
relative_sector_return_marked
MFE_CLOSE
MAE_CLOSE
```

## 7.2 当前 runtime

`src/workbench_analysis/v4_15_settlement.py`

`benchmark()` 当前返回核心字段，但存在 contract surface drift：

缺少/未明确输出：

```text
benchmark_valuation_coverage
benchmark_marked_weight
quote_age
quote_trade_date
```

且使用通用：

```text
relative_return
```

而不是正式 contract 字段：

```text
relative_market_return
```

Sector 复用 generic identity，未提供明确：

```text
sector_benchmark_id
```

## 7.3 注意：不要误修 marked estimate

当前参数：

`config/v4_parameter_registry_v1.json`

仍：

```text
V4_BENCHMARK_MINIMUM_ENDPOINT_WEIGHT_COVERAGE = null
V4_BENCHMARK_MAXIMUM_SUSPENSION_QUOTE_AGE = null
```

Market benchmark contract 也明确：

```text
marked_estimate.permission = false
```

所以：

> 本轮不能擅自启用 MARKED_ESTIMATE。

修复的是**schema/contract completeness**，不是给未冻结参数拍值。

## 7.4 修复

返回结构必须显式满足 contract。

在 permission 未开启时：

```json
{
  "benchmark_valuation_coverage": <known valuation weight>,
  "benchmark_marked_weight": 0,
  "relative_market_return_marked": null,
  "quote_age": null,
  "quote_trade_date": null,
  "marked_permission": false,
  "marked_reason": "PARAMETER_GATE_NOT_FROZEN"
}
```

Market 输出：

```text
relative_market_return
```

Sector 输出：

```text
sector_benchmark_id
relative_sector_return
```

不要让一个 generic `relative_return` 同时承担两个正式语义。

## 7.5 兼容要求

已有历史已接受 outcome 数值不得重写。

可：

```text
additive schema projection / successor output
```

旧 artifact 通过 adapter 只读兼容。

## 7.6 验收

至少：

```text
all actual endpoints
single verified suspension with marked gate disabled
delisted terminal verified
identity unknown
adjustment unknown
data missing
sector n<2
target stock exclusion
market vs sector identity separation
all required contract fields exist
```

## 7.7 状态

```text
P1
MUST_CLOSE_BEFORE_FORWARD_BENCHMARK_IS_USED_FOR_REAL_GATE
```

---

# 8. P1-05｜V4-15 Forward affine adjustment 数值校验不完整

## 8.1 设计

REV4 §46A：

```text
T0 + future OHLC
必须全部转换到同一 evaluation_basis_date
使用已验证 local affine adjustment
不能拿不同 daily QFQ snapshot 直接相除
```

## 8.2 当前实现

`price_path()` 已检查 endpoint 的：

```text
verified_identity
verified_adjustment
evaluation_basis_date
alpha/beta
```

但仍存在：

### A. interior rows

后续：

```python
value(r, key)
```

直接使用每个 row 的：

```text
transform_coefficients
```

没有先逐 row 验证：

```text
alpha finite
alpha > 0
beta finite
required keys
```

### B. T0 transform

`T0_transform_coefficients` 可被直接用于：

```text
p0
```

但没有统一完整 numeric validation。

如果出现 NaN：

```python
p0 <= 0
```

并不能可靠过滤 NaN。

### C. benchmark()

Market/Sector benchmark 同样直接使用：

```text
T0_transform_coefficients
transform_coefficients
```

未做统一 finite / alpha-positive 验证。

## 8.3 风险

非法 adjustment metadata 可能产生：

```text
NaN
Infinity
非法负 alpha
错误 basis denominator
```

进入 Forward result，而不是 fail closed 为：

```text
ADJUSTMENT_UNKNOWN
```

## 8.4 修复

建立唯一：

```python
validate_affine(coeff)
```

要求：

```text
dict
exact required keys
alpha numeric finite > 0
beta numeric finite
```

`price_path()`：

- T0 transform 必须 validate；
- endpoint 必须 validate；
- every interior actual row 必须 validate；
- basis date 必须 exact；
- adjustment identity 必须按合同一致性验证。

`benchmark()` 对每个 member 的：

```text
T0 transform
endpoint transform
```

同样执行。

任何失败：

```text
ADJUSTMENT_UNKNOWN
```

不能继续输出 numeric complete return。

## 8.5 必测

```text
alpha = 0
alpha < 0
alpha = NaN
alpha = Inf
beta = NaN
missing alpha
missing beta
interior row invalid but endpoint valid
T0 transform invalid
basis mismatch
mixed adjustment identity
```

## 8.6 状态

```text
P1
MUST_CLOSE_BEFORE_REAL_FORWARD_SETTLEMENT
```

---

# 9. P1-06｜FEP `core_signal_contract_id` 缺少 DB-level referential / semantic guard

## 9.1 当前 schema

`src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql`

：

```sql
core_signal_contract_id text NOT NULL
```

但没有：

```text
FK → fep.contracts
```

也没有 DB trigger 强制：

```text
FIRST_PREWATCH
→ FEP_E2_ENTRY_EVENT_STRATA_V1_1
```

当前 exact binding 由：

`src/workbench_analysis/fep_e5/metadata_binding.py`

应用层验证。

## 9.2 当前正式定位

这已经在 FEP E5 Final Closure 中登记为：

```text
FEP_SIGNAL_DB_LEVEL_HARDENING =
OPEN_NONBLOCKING_PRODUCTION_GOVERNANCE_DEBT
```

所以本项不是重新推翻 E5。

## 9.3 风险

如果未来另一个 canonical writer 绕过：

```text
metadata_binding.verify_signal()
```

DB 可接受：

```text
unknown signal contract id
reconstruction authority id
wrong event contract
```

进入 observations。

## 9.4 修复

028～032 禁止修改。

新增 additive migration。

最少：

```sql
FOREIGN KEY(core_signal_contract_id)
REFERENCES fep.contracts(contract_id)
```

再增加 semantic trigger：

```text
scope
signal_key / signal_type
event contract
```

必须匹配已接受的 signal/event authority。

不能 hardcode 成永远只允许 FIRST_PREWATCH；应支持 versioned signal-contract registry，但当前 FIRST_PREWATCH 必须 exact-bind：

```text
FEP_E2_ENTRY_EVENT_STRATA_V1_1
```

## 9.5 DB negative vectors

```text
unknown contract
target contract substituted as signal
reconstruction authority substituted as signal
wrong scope
wrong FIRST_PREWATCH predicate authority
wrong signal family
contract exists but wrong family
```

必须 DB reject。

## 9.6 状态

```text
P1
MUST_CLOSE_BEFORE:
FEP_PRODUCTION
REAL_DAILY_PRIORITY_SHADOW
MODEL_DISPLAY
PRIORITY_USE
```

---

# 10. P2-07｜旧 `fep_e5_engineering.*` 平行 ledger 仍作为可执行代码存在

## 10.1 文件

```text
src/workbench_analysis/fep_e5/ledger.py
src/workbench_analysis/fep_e5/schema.sql
src/workbench_analysis/fep_e5/projection.py
```

仍然维护：

```text
fep_e5_engineering.*
```

而 E5 canonical integration 已正式迁移到：

```text
fep.*
```

及：

```text
src/workbench_analysis/fep_e5/canonical_ledger.py
```

## 10.2 当前判断

本审计没有证据证明当前正式 canonical entry 仍把旧平行 schema 当 authority。

因此不是重新打开 E5-B01。

但旧 schema 仍能：

```text
install
write
CAS
projection
```

存在未来被误调用后重新形成“双 ledger 真相”的风险。

## 10.3 修复

不要删除历史代码。

将其明确降级：

```text
HISTORICAL_ENGINEERING_FIXTURE_ONLY
```

建议：

```text
Ledger.install()
Ledger.put()
Ledger.cas()
```

默认拒绝非 test/legacy fixture context。

例如要求显式：

```text
FEP_LEGACY_ENGINEERING_FIXTURE=true
```

且 production/runtime path 永远不能设置。

更推荐代码层：

```text
legacy namespace module
+
explicit deprecated/historical adapter
```

正式 current imports 只能指向 canonical ledger。

## 10.4 验收

```text
current E5 canonical runner cannot install legacy schema
production-style DSN cannot use legacy ledger
test fixture explicit opt-in works
canonical fep.* unchanged
historical reports remain readable
```

## 10.5 状态

```text
P2
GOVERNANCE_HARDENING
```

---

# 11. 当前开放但不能靠“代码修复”伪关闭的真实 / 审计债务

以下必须继续保留，不得在本轮修复时改成 PASS。

## 11.1 Amount-A H21

Current Audit Head：

```text
A04_H21_CONSUMER =
ACCUMULATION_CONTINUES

accepted_sessions = 1
missing_H21 = 20
```

所以：

```text
AMOUNT_A_H21_FORMAL_CONSUMER
```

不能提前开启。

## 11.2 Historical Amount-A

```text
A04_HISTORICAL_AMOUNT_A =
BLOCKED_AFFECTED_SCOPE
```

不能用重建数据补 first availability。

## 11.3 V4-09 current runtime PREWATCH

```text
A08_CURRENT_RUNTIME =
OPEN_EXTERNAL_REAUDIT
```

本轮 P0-01 修的是：

```text
机器 blocker 语义
```

不是自动把 A08_CURRENT_RUNTIME 变 PASS。

如果 current runtime 需要进入首次 real Shadow：

必须完成：

```text
current-runtime specific external re-audit
```

或者证明目标 capability 根本不依赖该 scope。

## 11.4 R3C / pre16 re-audit 项

当前仍存在例如：

```text
AUD_R3C_ACCEPTED_SUSPENSION_STATE_ADMISSION_01
AUD_R3C_ADJUSTMENT_COORDINATE_EXACTNESS
AUD_R3C_D2_ADMISSION_AND_PRIOR_AUTHENTICITY
AUD_R3C_EVENT_PRIOR_UNKNOWN_01
AUD_R3_GIT_EXACT_BYTE_PORTABILITY
```

这些当前被定义为：

```text
capability-scoped
not global V4-16 blocker
production cutover relevant
```

本轮不得直接删除。

如果对应代码没有变化：

可通过新的 exact independent re-audit disposition 关闭。

## 11.5 Parameter freeze

以下仍是：

```text
ENGINEERING_CANDIDATE
```

例如：

```text
benchmark marked coverage
suspension quote age
sector forward gates
rotation forward gates
required forward quality
```

未正式冻结之前：

```text
对应 production / marked consumer 必须保持 disabled
```

不能由 Codex 自己拍数值。

---

# 12. 不属于 bug 的项目

以下内容明确禁止 Codex“修复”。

## 12.1 V4-16 真实样本为 0

```text
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

这是市场时间/真实 authority 条件，不是程序 bug。

## 12.2 V4-17 Final 未通过

因为：

```text
没有真实 Shadow publication/readback
```

正确。

## 12.3 V4-18 runtime 尚未正式执行

Contract design 明确要求：

```text
WAIT_REAL_SHADOW_GATE
```

正确。

## 12.4 V4-19 Focus 未 cutover

缺：

```text
Shadow stable
Forward gate
Migration replay
capability permission
```

正确。

## 12.5 V4-20 Default UI 未 cutover

缺 production permission，正确。

## 12.6 V4-21 real continued observation 未开始

正确。

## 12.7 V4-22 Final PASS 未授予

正确。

## 12.8 FEP REAL_OOS / Champion / Priority 未授予

正确。

不能因为 FEP E1～E5 engineering closed 就制造：

```text
CHAMPION
REAL_OOS
PRIORITY_USE
MODEL_DISPLAY
FEP_PRODUCTION
```

---

# 13. 修复顺序

必须按以下顺序：

## Batch A｜P0 Runtime Safety

```text
P0-01 capability / issue blocker semantic repair
P0-02 R4R2 settlement worker + durable queue
```

完成后：

```text
STOP
targeted audit
```

不要和大量 P1 混成无法定位的大提交。

## Batch B｜V4-16 Ledger Hardening

```text
P1-03 real Shadow DB semantic constraints
```

## Batch C｜V4-15 Forward Contract Repair

```text
P1-04 benchmark output schema
P1-05 affine validation
```

## Batch D｜FEP Hardening

```text
P1-06 canonical signal DB guard
P2-07 legacy parallel ledger isolation
```

## Batch E｜External re-audit dispositions

重新核：

```text
A08_CURRENT_RUNTIME
R3C open items
```

只关闭有 exact evidence 的项目。

---

# 14. 修改边界

## 14.1 禁止修改历史 migration

特别是：

```text
FEP 028
029
030
031
032
```

必须 immutable。

V4 已接受 migrations 同理。

## 14.2 Accepted Heads

本轮默认：

```text
NO ACCEPTED HEAD MOVEMENT
```

除非某 repair task 后另行通过独立外审并明确授权 successor promotion。

## 14.3 历史 business outputs

禁止重写：

```text
accepted historical Core
accepted historical PREWATCH
accepted historical State
accepted historical Cohort
accepted FEP E2/E3/E4 outputs
accepted 205 canonical historical observations
accepted 615 predictions / 616 slots
```

修复应优先：

```text
successor adapter
new constraint
new schema version
new contract version
```

## 14.4 TDX

继续：

```text
READ ONLY
```

---

# 15. 每个修复包必须输出的 evidence

每个 P0/P1 修复必须有：

```text
ENTRY_BASELINE.json
CHANGED_FILE_LIST.json
DESIGN_BINDING.json
BUG_REPRODUCTION.json
REPAIR_DISPOSITION.json
NEGATIVE_MATRIX.json
TARGETED_TEST_SUMMARY.json
SCOPED_REGRESSION_SUMMARY.json
PROTECTED_STATE_READBACK.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

其中：

`BUG_REPRODUCTION.json` 必须证明修复前的实际缺陷，不允许只描述理论风险。

---

# 16. Regression 要求

不能只运行新增 test。

至少分：

```text
targeted
affected-stage
cross-stage
protected-state
```

P0-01 必须覆盖：

```text
V4-09
V4-15
V4-16
R25
Current Audit Head
```

P0-02/P1-03 必须覆盖：

```text
V4-15 settlement
V4-16 runtime
restart
rollback
due/outcome
R25
```

P1-04/P1-05：

```text
V4-15
FEP label adapter
Forward consumers
```

P1-06/P2-07：

```text
FEP E1～E5
canonical fep.*
permission/CAS
API/Priority fail-closed
```

所有历史 known debt：

```text
保持 explicit
不得删除
不得改名规避 diff
```

必须输出：

```text
introduced_failure_nodes = 0
```

---

# 17. Protected State 必须保持

修复后必须证明：

```text
V4_STAGE_ACCEPTED_HEAD
unchanged unless separately authorized

V4_DATA_ACCEPTED_HEAD
unchanged in this repair

V4_15_ACCEPTED_HEAD
unchanged

DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1
unchanged unless exact successor explicitly required

V4_16_ACCEPTED_HEAD
NOT_CREATED

V4_17_ACCEPTED_HEAD
NOT_CREATED

V4_18_ACCEPTED_HEAD
NOT_CREATED

V4_19_ACCEPTED_HEAD
NOT_CREATED

V4_20_ACCEPTED_HEAD
NOT_CREATED

V4_21_ACCEPTED_HEAD
NOT_CREATED

V4_22_ACCEPTED_HEAD
NOT_CREATED

Production = false
Focus cutover = false
Default UI cutover = false

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_OOS = NOT_GRANTED
CHAMPION = NONE
```

直到真实 runtime 流程另行授权。

---

# 18. Codex 不得使用的“修复捷径”

禁止：

```text
把 A08_CURRENT_RUNTIME 直接改 PASS
删除 current audit issue
把 blocked issue id 改名后不做 capability resolution
仅增加一个 if "PURE_CORE_STOCK" in ... 的硬编码补丁
绕过 Current Audit Head
用 latest/glob/mtime 选 authority
修改 accepted historical output 让新测试通过
把 UNKNOWN 改 FALSE
把 unavailable 改 0
把 reconstruction 改 PIT_OBSERVED
把 engineering fixture 改 REAL
把 settlement queue 简化成同步函数后声称满足 durable outbox
给未冻结 benchmark 参数填经验值
直接删除 legacy FEP schema
修改 028～032
直接开启 FEP display/priority
直接创建 V4-16 Accepted Head
```

---

# 19. 建议新的修复 artifact / contract 名称

可参考：

```text
config/v4_16_runtime_capability_resolution_v1.json
config/v4_16_runtime_dependencies_v5.json
config/v4_16_settlement_worker_contract_v2.json

migrations/v4_16_real_shadow_integrity_v2.sql
or versioned equivalent

config/v4_15_forward_benchmark_runtime_contract_v1_1.json

src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql
```

实际编号必须先走 repo migration allocator，不得直接占号。

---

# 20. 修复完成后的唯一允许自报状态

Codex 完成所有代码后，只允许：

```text
FULL_CHAIN_REPAIR =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

不得自报：

```text
FULL_PASS
V4_FINAL_PASS
PRODUCTION_READY
FIRST_REAL_SHADOW_AUTHORIZED
FEP_PRODUCTION_READY
```

---

# 21. 本次审计特别说明：历史 PASS 不等于当前无 bug

本轮采取的是：

```text
latest design
vs
latest accepted authority
vs
latest remote code
```

而不是：

```text
“某阶段历史外审通过”
→
“当前代码永远正确”
```

因此：

- 已接受历史结果默认保留；
- 当前 successor/runtime 新路径仍需重新审查；
- historical accepted scope 与 current runtime scope 必须严格分开。

这也是本轮发现：

```text
A08 historical PASS
但 A08_CURRENT_RUNTIME still OPEN
```

以及：

```text
R4R2 startup accepted
但 settlement-only restart 仍 V3
```

这类问题的原因。

---

# 22. 最终修复清单

```text
P0-01
V4-16 blocked issue/capability identity domain mismatch
→ repair before first real Shadow

P0-02
V4-16 settlement-only restart + durable worker incomplete/stale
→ repair before first real Shadow

P1-03
Real Shadow SQLite semantic DB constraints weaker than contract
→ harden before long-lived real ledger

P1-04
V4-15 Forward benchmark runtime output schema mismatch
→ repair before real benchmark gate

P1-05
V4-15 affine adjustment numerical validation incomplete
→ repair before real Forward settlement

P1-06
FEP core_signal_contract_id DB semantic hardening missing
→ repair before any FEP real/display/priority permission

P2-07
legacy fep_e5_engineering parallel ledger remains executable
→ isolate as historical/test-only
```

同时保持：

```text
A04 H21 = real accumulation pending
Historical Amount-A = blocked affected scope
A08_CURRENT_RUNTIME = external re-audit pending
R3C items = preserve until exact re-audit
V4-17～22 real gates = pending, not bugs
FEP real OOS / champion / priority = pending, not bugs
```

---

# 23. 本轮总体结论

当前系统不是“代码已经全部无问题，只差等数据”。

更准确状态是：

```text
核心设计链与历史 Accepted Chain 基本成立；

但第一次 Real Shadow 前，
仍有 2 个 P0 runtime safety / authority 问题必须关闭；

V4-15 Forward 有 2 个 P1 合同/数值边界问题；

V4-16 real ledger 有 1 个 P1 数据结构完整性问题；

FEP 有 1 个 P1 DB hardening + 1 个 P2 legacy isolation 问题；

其余 V4-17～22 的未完成项主要是真实 gate，
不得用开发伪造完成。
```

因此下一步不是继续开发新的 Stage。

下一步是：

```text
执行本文修复
→ 独立全链路 re-audit
→ P0/P1 close
→ 等真实 accepted target-session
→ R25
→ First Real Shadow
```

**文档结束**

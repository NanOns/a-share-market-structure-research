# V4-09 Accepted Head Promotion + V4-10 State Reducer Engineering Entry 任务卡｜2026-09-30

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**起始 HEAD**：`981332582c1982d9da3af922688e682946822119`  
**外部决定**：`V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE`  
**权威合同**：REV4 FEP R2 §31、§32、§33、§78 及相关字段/时间/状态章节

---

# 0. 本任务的边界

本轮分两步：

```text
A. V4-09 Accepted Head Promotion
B. V4-10 State Reducer interface + independent vectors engineering
```

不能把 B 扩大成：

```text
完整 Final State DAG
完整 Confirmation 集成
完整 Structure/Anchor/Support 集成
V4-14 Replay Gate B
Focus/UI cutover
production
```

REV4 FEP R2 §78 已明确：

```text
V4-10 可实现 reducer 接口和独立向量
完整运行必须等 V4-11 / V4-12
最终在 V4-14 验收
```

---

# 1. V4-09 Promotion 输入

唯一可 promotion 的 candidate：

```text
tested implementation commit
5eca56d3555a826c4cca94d6e3d7ae9d11628be6

evidence seal / audited HEAD
981332582c1982d9da3af922688e682946822119

external decision
V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

正式 artifact：

```text
data/v4/artifact_store/v4_09/
V4_09_STOCK_PREWATCH_2026-09-28_edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e.jsonl.gz
```

SHA：

```text
8b92cbd96a8145005bad89374349582c075cf367722b956a75243d59aa64d18d
```

logical digest：

```text
edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e
```

---

# 2. V4-09 Accepted Head

创建：

```text
data/v4/V4_09_ACCEPTED_HEAD.json
```

必须明确：

```text
status
= ENGINEERING_PASS_CAPABILITY_SCOPED

external_acceptance
= EXTERNALLY_ACCEPTED

external_acceptance_decision
= V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

能力至少分开：

```text
V4_09_ENGINEERING
= ENGINEERING_ACCEPTED

STOCK_PREWATCH_RAW
= ENGINEERING_ACCEPTED

PRIORITY_V1
= ENGINEERING_ACCEPTED

REAL_SIGNAL_CAPABILITY
= DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN
```

不得写成：

```text
REAL_SIGNAL_FULL_PASS
PRODUCTION_READY
```

---

# 3. V4-09 Accepted Head 必须绑定

至少：

```text
V4-09 stock prewatch contract
mandatory quality contract
field registry
machine AST
parameter set
150 algorithm vectors
R1.1 priority provenance contract
15 producer vectors
runtime
immutable artifact
candidate manifest
independent postcheck
artifact immutability evidence
materialized T/T+1/revision evidence
schema receipt
clean regression
no-symbol
external acceptance document
V4-08 amended accepted head
```

---

# 4. V4-08 Amended Head 是唯一正式上游

V4-09 Accepted Head 必须绑定：

```text
data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json

SHA
f2a35cebd18e8caf723e7900133333ce4b8df1a8314cb190dade7b0ea7624a3f
```

不得重新指向 superseded：

```text
data/v4/V4_08_ACCEPTED_HEAD.json
```

旧头只允许作为：

```text
superseded_history
```

---

# 5. Global Stage Promotion

Promotion 成功后：

```text
accepted_stage_range
= V4_00_TO_V4_09_ACCEPTED
```

新增：

```text
v4_09_binding
→ V4_09_ACCEPTED_HEAD.json
```

同时：

```text
v4_10_entry
= AUTHORIZED_FOR_STATE_REDUCER_INTERFACE_AND_INDEPENDENT_VECTORS
```

保持：

```text
production_permission        = false
shadow_production_permission = false
focus_cutover_permission     = false
```

Protected Heads 不得移动。

---

# 6. Promotion Validator

不能只验证自洽 hash。

至少独立检查：

```text
external decision exact
audited HEAD / implementation commit exact
V4-08 amended head exact
V4-09 artifact path/hash/logical digest exact
runtime exact
contracts exact
producer provenance evidence PASS
artifact immutability evidence PASS
clean regression PASS
no-symbol PASS
capability not overclaimed
permissions false
V4-10 entry scope exact
V4-09 accepted head idempotent
```

---

# 7. V4-10 Stage Entry

创建正式 stage entry / contract freeze。

V4-10 当前允许做：

```text
RESEARCH_STATE_V1 reducer interface
input schema
output schema
state axes
precedence
UNKNOWN semantics
hysteresis interface
expiry/reentry interface
machine AST
parameter references
independent synthetic vectors
persistence engineering schema
```

当前不允许把缺失 V4-11/V4-12 的真实 detector 伪造成可用输入。

---

# 8. RESEARCH_STATE_V1 五轴

§30：

```text
Maturity:
NONE
SEED
PREWATCH
WARM
CONFIRMED

Health:
IMPROVING
STABLE
WEAKENING
DAMAGED
EXHAUSTED
UNKNOWN

Validity:
VALID
INVALIDATED
UNKNOWN

Tracking:
ACTIVE
FOLLOWUP
CLOSED

Scenario:
股票
SETUP
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
NONE

板块
BASE_BUILD
BREADTH_BUILD
RECOVERY_BUILD
BROADENING
REACCELERATING
SUSTAINED
NONE
```

这些是不同轴。

禁止：

```text
把 Health 当 Maturity 比较
把 Scenario 当资格等级
把 Tracking 当风险强弱
```

---

# 9. Final State Reducer 核心顺序

依据 §31 冻结为 machine-readable rule order。

必须至少覆盖：

## R1 Model Boundary

```text
先确定合法 prior state / lineage
模型边界事件单独记录
```

## R2 Hard Invalidation First

关联旧 research episode 的：

```text
frozen invalidation_AST
OR
core_price_damage = TRUE
```

则：

```text
health            = DAMAGED
validity          = INVALIDATED
final_eligibility = FALSE
maturity          = NONE
tracking          = FOLLOWUP
```

同日 confirmation 不得覆盖。

## R3 Required Facts UNKNOWN

无硬失效，但必需事实 UNKNOWN：

```text
保留 last_known maturity
state_freshness   = STALE
validity          = UNKNOWN
health            = UNKNOWN
final_eligibility = UNKNOWN
```

禁止：

```text
UNKNOWN → FALSE
```

也不新增 enrollment / exit。

## R4 Fully Evaluable Stage Selection

```text
CONFIRMED
> WARM
> PREWATCH
> SEED
> NONE
```

但：

```text
Stock V1
无独立 WARM detector
→ NOT_APPLICABLE

Sector
可有 legacy WARM
```

不得为股票发明新的 WARM 算法。

## R5 Downgrade Hysteresis

升级：

```text
same-session effective
```

下降候选：

```text
需要连续 2 个可评估市场会话
```

UNKNOWN / suspension：

```text
break consecutive count
不当 FALSE
```

## R6 Health

硬 damage 已优先。

否则：

```text
risk EXTREME → EXHAUSTED

delta3 < -3 → WEAKENING

delta3 > 3 → IMPROVING

otherwise → STABLE
```

Sector：

```text
使用 dq5
```

没有必要历史：

```text
UNKNOWN
```

## R7 Tracking

```text
无 episode + NONE
→ CLOSED

active qualification
→ ACTIVE

exit
→ FOLLOWUP

所有 outcome/follow-up 完成
→ CLOSED
```

---

# 10. Expiry Interface｜§32

V4-10 可以实现计数接口和 machine vectors。

规则：

```text
SEED/PREWATCH
连续 10 个可评估会话
无阶段升级
且 delta3/dq5 未提高 >=3pp
→ EXPIRED
```

结果：

```text
maturity = NONE
tracking = FOLLOWUP
```

UNKNOWN / suspension：

```text
不增加 expiry count
```

但：

```text
market_age
仍正常增长
```

不得每日重新锚定 improvement baseline 来逃避 expiry。

---

# 11. Reentry Interface｜§33

正式退出后：

```text
次一市场会话及以后
重新满足资格
→ new episode
```

要求：

```text
parent_episode_id = old episode
```

禁止：

```text
退出当天直接 REENTERED
stage upgrade / downgrade 建新 episode
MODEL_BOUNDARY 冒充 REENTERED
```

旧 episode 的：

```text
follow-up
outcome
```

必须继续独立存在。

---

# 12. V4-10 输入边界

当前可真实接入：

```text
V4-07 Seed
V4-09 PREWATCH
已 accepted 的基础 Core / risk / delta3
prior state synthetic / engineering fixtures
```

当前尚未正式可集成：

```text
V4-11 Confirmation
V4-12 Structure / Anchor / Support
完整 episode invalidation AST
完整 stock confirmation scenarios
```

这些缺失必须：

```text
NOT_IMPLEMENTED
NOT_APPLICABLE
UNKNOWN
```

不能：

```text
默认 FALSE
伪造 positive detector
用旧 V3 result 直接偷接
```

除非该 legacy producer 已经按正式 extraction contract 验收。

---

# 13. Machine Vectors 最低覆盖

至少覆盖：

```text
hard invalidation > confirmation
required UNKNOWN preservation
PREWATCH > SEED
CONFIRMED > PREWATCH
stock WARM NOT_APPLICABLE
upgrade immediate
downgrade day1 hold
downgrade day2 apply
UNKNOWN breaks downgrade streak
suspension breaks downgrade streak
risk EXTREME → EXHAUSTED
delta3 +/-3 boundaries
tracking ACTIVE/FOLLOWUP/CLOSED
expiry session 9 / 10 boundary
expiry UNKNOWN interruption
reentry next-session rule
same-day reentry forbidden
model boundary not reentry
```

并覆盖各 axis UNKNOWN。

---

# 14. 不要提前宣称完整 V4-10 PASS

R1 的 V4-10 结果应该类似：

```text
V4_10_REDUCER_INTERFACE_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不能写：

```text
V4_10_FULL_STATE_REDUCER_ACCEPTED
```

因为 §78 已明确：

```text
完整运行等待 V4-11 / V4-12
完整验收在 V4-14 Replay Gate B
```

---

# 15. Persistence

如新增 reducer 工程 persistence：

必须：

```text
publication/revision append-only
prior_state binding explicit
input state publication IDs explicit
model_contract_id explicit
parameter_set_id explicit
matched / unknown predicates
transition reasons
state freshness
episode identity
```

任何 UPDATE/DELETE 仍按现有 V4 append-only 纪律处理。

---

# 16. Permanently Forbidden

继续 P0：

```text
个股代码特判
symbol whitelist
future outcome feedback
Focus feedback
UI feedback
同日 PREWATCH ↔ State 反向反馈
UNKNOWN → FALSE
为了非空调整参数
```

---

# 17. OPEN Audits 独立继续

不要借 V4-10 修改：

```text
V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
AUD-AMOUNT-A-06
DM01_REAL_INCREMENTAL_BUILDERS
LEGACY_VALID_MEMBER_EXACT_PRODUCER
FORWARD_PIT_HISTORY_ACCUMULATION
```

这些继续并行，不阻断无关 reducer interface 工程。

---

# 18. 正式证据

至少生成：

```text
data/v4/V4_09_ACCEPTED_HEAD.json

reports/v4_joint/
V4_09_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json
V4_09_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json

reports/v4_10/
V4_10_STAGE_ENTRY.md
V4_10_CONTRACT_FREEZE.json
V4_10_MACHINE_VECTOR_COVERAGE.json
V4_10_INDEPENDENT_POSTCHECK.json
V4_10_SCHEMA_MIGRATION_RECEIPT.json
V4_10_ISOLATED_REGRESSION.json
V4_10_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
V4_10_CLEAN_CHECKOUT_RECEIPT.json
V4_10_STAGE_CANDIDATE_MANIFEST.json
V4_10_CLOSURE.md
V4_10_EXTERNAL_REAUDIT_HANDOFF.json
```

---

# 19. Handoff

最终必须报告：

```text
pushed HEAD

V4-09:
accepted head SHA
global stage SHA
artifact SHA/logical digest
external decision
capabilities
protected heads
promotion validation

V4-10:
contract SHA
AST SHA
parameter SHA
runtime SHA
vector count
state-axis coverage
UNKNOWN coverage
hysteresis/expiry/reentry vectors
schema readback
clean regression
no-symbol
known NOT_IMPLEMENTED / NOT_APPLICABLE inputs
```

然后停止等待独立外部复验。

---

**任务结束**

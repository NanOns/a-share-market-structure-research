# V4-08 R5｜Sector / Rotation Core 实现、参数冻结与 B2 Legacy Adapter 提取任务卡

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Required Starting HEAD:** `75767711835207109927f2babfb547415f89d3fb`  
**Date:** 2026-09-30

---

# 0. External authority

本任务承接：

```text
V4_08_R4_1_GOVERNANCE_EXTERNAL_ACCEPTANCE_PASS
V4_08_PIT_MEMBERSHIP_BASELINE_EXTERNAL_ACCEPTANCE_PASS_R1
```

但：

```text
V4_08_STAGE_EXTERNAL_ACCEPTANCE_BLOCKED_ALGORITHM_COMPLETION_REQUIRED
```

R5 不再重做 membership / identity / calendar / symbol governance。

---

# 1. R5 总目标

完成 §78 对 V4-08 的剩余正式交付：

```text
共同成员
B0
B1
B2
纯Core legacy sector资格adapter
V4-08 参数冻结
formal producer / persistence / readback
```

并将 V4-08 从：

```text
membership engineering only
```

推进到：

```text
Sector / Rotation Core engineering complete
```

---

# 2. 先做 scoped PIT membership promotion

本轮允许创建：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

绑定精确已验收 artifact：

## Source revision

```text
SHA256 =
bbc1089d86c1a191a902af3145068a8409604a7e1181f8e864cb12db35854eee
```

## Snapshot

```text
SHA256 =
ff28518c4f530d39574258131436c92970ebf7761fd979e932fbb6499f435bf1
```

## Facts

```text
SHA256 =
164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d
```

First accepted date：

```text
2026-09-30
```

不得创建最终：

```text
V4_08_ACCEPTED_HEAD.json
```

---

# 3. Membership promotion receipt

必须记录：

```text
membership_acceptance_scope = FORWARD_PIT_MEMBERSHIP_ONLY
first_accepted_trade_date = 2026-09-30
formal_row_count = 50162
INDUSTRY = 5224
THEME = 44938
```

并明确：

```text
does_not_grant_sector_algorithm_acceptance = true
does_not_grant_rotation_production_permission = true
```

---

# 4. Workstream A｜实现 V4_08_SECTOR_NATIVE_V1 producer

不得复用旧：

```text
src/sector/phase2.py
BASIS = CURRENT_TDX_MEMBERSHIP
```

直接冒充 V4 producer。

新 producer 必须只消费：

```text
accepted PIT membership head
accepted Core facts
accepted Base Seed output
accepted market calendar
accepted prior sector publication when needed
```

---

# 5. Sector Native formal primitives

至少实现并持久化合同定义的：

```text
sector_rsN
sector_rsN_pct
rank_velocityK
dq5
breadth_ret1
ma20_width
deltaK
strong_member
strong_member_retention
seed_width
participation_proxy
concentration
```

所有字段必须带：

```text
producer
source publication
target_trade_date
max_source_trade_date
membership snapshot id
parameter/model identity
quality
reason
```

---

# 6. Common-member computation

所有 delta / retention / endpoint change 必须显式使用：

```text
M_t ∩ M_(t-K)
```

并保存：

```text
current_member_count
prior_member_count
common_member_count
endpoint_known_count
coverage
```

没有 prior accepted PIT membership：

```text
UNKNOWN
```

不能回退到 current-membership replay 作为正式值。

因此第一天 2026-09-30 很多历史 member-delta 字段出现 UNKNOWN 是正常的。

---

# 7. Seed-dependent degradation

Prior-RPS 仍 OPEN。

所以：

```text
Base Seed real signal capability
=
DEGRADED
```

所有 seed-dependent sector fields 必须：

```text
value = null
quality = UNKNOWN
reason = DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL
```

禁止：

- 使用旧 V4-03 staging；
- 把 UNKNOWN 当 FALSE；
- 把 k=0 当真实 seed width；
- 降低阈值强造候选。

---

# 8. Non-seed fields 不得被 Prior-RPS 阻塞

Prior-RPS 不能阻塞：

```text
sector membership
sector RS
breadth
MA width
non-seed concentration
common-member infrastructure
rank denominator
episode infrastructure
B2 non-seed paths
```

这些应继续开发和验收。

---

# 9. Workstream B｜实现 B0 producer

正式模型：

```text
V4_08_SECTOR_PREWATCH_B0_V2
```

runtime 必须执行冻结 AST。

不得再复制 Python 阈值。

必须从 parameter set 解析：

```text
V4_08_SECTOR_MIN_MEMBERS
V4_08_SECTOR_MIN_QUOTE_COVERAGE
V4_08_PREWATCH_DQ5_MIN
V4_08_PREWATCH_SEED_WIDTH_MIN
```

并验证 digest。

---

# 10. B0 UNKNOWN

2026-09-30 若：

```text
dq5
base_seed_width
prior PIT-dependent fields
```

尚无正式数据，则：

```text
B0 state = UNKNOWN
```

不是 FALSE。

必须保存 predicate truth table 与 reason。

---

# 11. Workstream C｜实现 B1 Rotation producer

使用：

```text
ROTATION_CORE_V1_R3
```

当前四态：

```text
TRUE
FALSE
UNKNOWN
NOT_APPLICABLE
```

已经通过，不重写其核心语义。

实现：

```text
rotation_episode_id
pulse_date
frozen basket
base_seed_set
breadth_positive_set
pulse baseline
episode age
accepted flag
terminated flag
prior_rotation_state
```

---

# 12. First-day / history insufficiency

2026-09-30 是第一张正式 PIT membership。

因此：

```text
prior accepted PIT membership = unavailable
multi-session frozen episode history = unavailable
```

对应字段必须：

```text
UNKNOWN
NOT_APPLICABLE
NO_PRIOR_ACCEPTED_PIT_HISTORY
```

不能等待未来几天才写代码。

实现今天就完成；以后新 PIT 日到来后自然开始产生真实路径。

---

# 13. Workstream D｜冻结五个 retention 参数

当前五个 null：

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

R5 必须形成独立参数决策包。

---

# 14. 参数冻结禁止事项

禁止：

```text
直接填 0.5
看当前输出哪个结果好就选哪个
看未来收益优化参数
用第一天真实候选数量反推门槛
```

参数冻结必须基于：

- 语义；
- 单调性；
- 数学边界；
- 规则相互关系；
- synthetic vectors；
- diagnostic sensitivity；
- 预期 workload 仅作为产品负荷检查，不作为收益优化。

---

# 15. 参数决策包

建议：

```text
reports/v4_08/V4_08_R5_RETENTION_PARAMETER_DECISION_PACKAGE.json
```

每个参数记录：

```text
candidate range
tested values
semantic interpretation
monotonicity
affected states
sensitivity result
selected value
why selected
why alternatives rejected
future outcome data used = false
```

然后生成新：

```text
V4_08_ALGORITHM_PARAMETER_SET_R5
```

不要覆盖旧 candidate set。

---

# 16. 参数 binding test

必须证明：

```text
runtime output
```

由参数实例驱动。

临时测试 fixture 改动任一参数：

```text
output / predicate truth changes
```

且：

```text
production code has no literal fallback
```

独立 verifier 也必须读取参数实例，不能复制数值。

---

# 17. Workstream E｜B2 Legacy Adapter 精确提取

当前：

```text
NOT_IMPLEMENTED_PENDING_EXACT_SOURCE_AST_AND_GOLDEN_SAMPLES
```

必须关闭。

从实际 legacy source 提取：

```text
source file
function / symbol
source SHA
call graph
parameters
units
time semantics
quality / UNKNOWN semantics
input dependencies
output states
```

---

# 18. B2 Pure-Core boundary

B2 只能消费：

```text
accepted Core
accepted PIT membership
accepted B0 native facts
accepted Base Seed facts
```

禁止：

```text
same-day final stock PREWATCH
Focus
Radar
turnover
future outcomes
future confirmation
STYLE
UNKNOWN-as-FALSE
```

---

# 19. Amount A 特殊处理

若 legacy B2 内部存在尚未通过独立审计的 Amount A：

```text
affected branch = DIAGNOSTIC / BLOCKED
```

不得：

```text
把 participation_proxy 偷换成 Amount A
```

不依赖 Amount A 的独立 pure-Core branch 可继续正式实现。

---

# 20. B2 AST

必须生成机器可执行 AST：

```text
field_id
operator
parameter_id / constant
producer
time_role
quality_requirement
UNKNOWN behavior
```

并绑定：

```text
source SHA
AST digest
parameter digest
field registry digest
```

---

# 21. B2 Golden Samples

至少包含：

```text
positive
negative
UNKNOWN
boundary
same-shape-different-cause
Amount-A affected branch
```

golden expected 必须独立形成，不能由 producer 输出回填。

---

# 22. Workstream F｜正式全市场 V4-08 materialization

生成：

```text
Sector Native facts
B0 predicate/results
B1 Rotation facts
B2 qualification
```

对 2026-09-30 全市场 sector universe 运行。

允许大量：

```text
UNKNOWN
NOT_APPLICABLE
```

只要原因真实。

禁止为了“看起来有结果”而降级规则。

---

# 23. Persistence

若现有 schema 不足，新增 append-only migration。

不得修改历史 migration。

至少保存：

```text
publication_id
sector_id
sector_type
membership_snapshot_id
model_contract_id
parameter_set_id
input digests
output state
predicate facts
quality
reason
max_source_trade_date
created_at
```

---

# 24. Formal consumer permission

R5 工程完成后：

```text
formal_consumer_enabled
```

是否可开启，要按 capability 分开。

可以是：

```text
SECTOR_NATIVE_NON_SEED = ENABLED
B0_SEED_DEPENDENT = DEGRADED_UNKNOWN
ROTATION_HISTORY_DEPENDENT = SHADOW/UNKNOWN
B2_NON_AMOUNT_A = ENABLED
B2_AMOUNT_A = DIAGNOSTIC
```

不要只给一个 global boolean。

---

# 25. Feedback isolation

必须测试修改以下内容不会改变 B0/B1/B2 raw output：

```text
same-day final stock PREWATCH
Focus
Radar
Support
V4-06 turnover
future confirmation
future outcome
```

---

# 26. No-symbol-special-case 永久门

R4.1 的：

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

必须加入 R5 clean regression。

Hard gated：

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
```

要求：

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = 0
```

---

# 27. Real forward accumulation 不阻塞实现

不要等待：

```text
5日
20日
多个 rotation episode
```

才完成代码。

第一天数据不足时：

```text
UNKNOWN / NOT_APPLICABLE
```

就是正确输出。

随着 10/8、10/9 等未来 session 到来，系统自动积累真正 PIT history。

---

# 28. Prior-RPS 并行

Prior-RPS repair 继续独立。

R5 不把它强行夹进 V4-08 主任务导致整体停摆。

但所有 dependent capability 必须保留真实 degraded 状态。

---

# 29. Clean checkout

最终 implementation commit：

- clean detached checkout；
- disposable PostgreSQL；
- no `.env`；
- process DSN；
- migrations；
- V4-01..08 required regression；
- governance hard gate；
- generic parameter perturbation；
- B2 golden tests；
- full-market materialization tests。

记录实际 test count，不写死。

---

# 30. Required evidence

至少：

```text
reports/v4_08/V4_08_R5_STAGE_ENTRY.md

reports/v4_08/V4_08_R5_PIT_MEMBERSHIP_PROMOTION.json

reports/v4_08/V4_08_R5_SECTOR_NATIVE_IMPLEMENTATION.json
reports/v4_08/V4_08_R5_SECTOR_NATIVE_FULL_MARKET.json
reports/v4_08/V4_08_R5_COMMON_MEMBER_QUALITY.json

reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json
reports/v4_08/V4_08_R5_B0_FULL_MARKET.json

reports/v4_08/V4_08_R5_ROTATION_IMPLEMENTATION.json
reports/v4_08/V4_08_R5_ROTATION_FULL_MARKET.json

reports/v4_08/V4_08_R5_RETENTION_PARAMETER_DECISION_PACKAGE.json
reports/v4_08/V4_08_R5_PARAMETER_BINDING_PERTURBATION.json

reports/v4_08/V4_08_R5_B2_LEGACY_SOURCE_EXTRACTION.json
reports/v4_08/V4_08_R5_B2_MACHINE_AST.json
reports/v4_08/V4_08_R5_B2_GOLDEN_VECTORS.json
reports/v4_08/V4_08_R5_B2_INDEPENDENT_POSTCHECK.json

reports/v4_08/V4_08_R5_FEEDBACK_ISOLATION.json
reports/v4_08/V4_08_R5_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json

reports/v4_08/V4_08_R5_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_08/V4_08_R5_ISOLATED_REGRESSION.json
reports/v4_08/V4_08_R5_CLEAN_CHECKOUT_RECEIPT.json

reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R5_CLOSURE.md
reports/v4_08/V4_08_R5_EXTERNAL_REAUDIT_HANDOFF.json
```

---

# 31. Terminal states

如果代码、参数、B2、producer 全部完成，即使真实 Seed/History 仍因外部数据能力不足：

```text
V4_08_R5_READY_FOR_EXTERNAL_ACCEPTANCE_ENGINEERING_SCOPE
```

建议外部最终状态可为：

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_ENGINEERING_SCOPE_DEGRADED_REAL_SIGNAL
```

如果自身实现仍缺：

```text
V4_08_R5_BLOCKED_<EXACT_SCOPE>
```

---

# 32. Global head

R5 开发过程中：

```text
accepted_stage_range = V4_00_TO_V4_07_ACCEPTED
```

保持。

只有独立外部验收 R5 后，才决定是否将全局阶段推进到 V4-08。

---

# 33. Handoff

Codex 完成后必须报告：

- pushed HEAD；
- PIT membership scoped accepted head digest；
- Sector Native producer path/hash；
- B0 producer path/hash；
- B1 producer path/hash；
- B2 exact source extraction；
- five frozen retention values + parameter set digest；
- parameter perturbation results；
- 2026-09-30 full-market output distributions；
- UNKNOWN/NOT_APPLICABLE reasons；
- seed-dependent degraded counts；
- feedback-isolation results；
- no-symbol governance result；
- clean regression；
- Prior-RPS status；
- Amount A status；
- no final V4-08 Accepted Head assertion unless explicitly authorized。

然后停止，等待独立外部验收。

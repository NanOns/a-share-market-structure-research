# V4-04 R2 Full-Market Core Profile Closure Task

## 1. 当前基线

Repository:

`NanOns/a-share-market-structure-research`

Branch:

`codex/v4-system-reform`

Input HEAD:

`ca906884526e41a8cc8d4a47eabba3d5329f0a10`

当前 V4-04 状态：

`IN_PROGRESS / NOT_V4_04_PASS`

V4-04 已获得正式入场权限：

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`
→ `v4_04_entry = AUTHORIZED_FULL_CHAIN`

不得重新打开已完成的 V4-00～V4-03，也不得因为 V4-04 缺少派生字段而修改 V4-03 Accepted Business Artifact。

本任务只负责完整关闭 V4-04。

V4-05 不得在本任务中提前执行。

---

# 2. Governing Contracts

最高业务合同：

`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`

重点执行：

- §10B Trend State
- §10C Position State
- §10D MA Structure State
- §10E Relative Market State
- §10F Compression State
- §10G Amount / Volume / Participation
- §10I Core Extension Risk
- §72 Parameter Registry
- §73 禁止硬编码
- §78 V4-04 Full-Market Core Profile
- §81.4 Contract Completeness DoD
- §87A Field → Algorithm Contract Registry

同时遵守：

`AGENTS.md`

---

# 3. 当前 R1 只作为部分实现保留

保留：

`src/v4/profile_core.py`

`tests/v4_04/test_profile_core_rules.py`

`docs/audits/V4_04_CORE_PROFILE_EXECUTION_R1_20260929.md`

不得删除 R1 历史。

但不得把当前 R1 声称为 V4-04 PASS。

当前两个 unit-test functions 只能证明局部规则原型，不构成 Full-Market Core Profile 阶段验收。

---

# 4. 第一任务：先补齐 V4-04 机器合同

在继续 Full-Market Builder 前，先建立 V4-04 自己的正式 machine-readable contract。

至少形成：

`config/v4_04_field_registry_v1.json`

`config/v4_04_output_schema_v1.json`

`config/v4_04_algorithm_contracts_v1.json`

如参数已经由既有 Parameter Registry 冻结，则引用既有 `parameter_id / parameter_set_id`，不复制或偷偷修改阈值。

每个 V4-04 字段必须声明：

- field_id
- data_type
- unit
- producer
- producer_contract_id
- parameter_set_id
- required / optional
- time semantics
- window semantics
- price basis
- source identity
- UNKNOWN policy
- quality propagation
- output digest semantics
- consumer stage

不得由代码临时发明字段语义。

若 §78、§87A、既有 V4-03 deferred registry 之间出现字段 ownership 冲突：

记录明确 `CONTRACT_CONFLICT`

只暂停该字段能力，不得自行猜测合同。

---

# 5. V4-04 Required Field Closure

必须完整实现 §10B–§10G + §10I 以及 §87A 明确属于 V4-04 的 Pure-Core 字段。

## 5.1 Trend

必须至少包含：

- `trend_state`
- `weekly_trend_state`
- `monthly_trend_state`

Daily：

严格执行 `TREND_STATE_V1` first-true AST。

Weekly：

只能读取 CLOSED_ONLY weekly bars：

`WEEKLY_UP = Cw > MA5w AND MA5w > MA5w[-1]`

DOWN 反向，其余 FLAT。

Monthly：

只能读取 CLOSED_ONLY monthly bars：

使用 `MA3m`，同样规则。

进行中的周/月 bar 不能参与正式状态。

---

## 5.2 Position

不能只输出现在的 `position_state`。

必须覆盖：

- `position_state`
- `bias20_atr`
- `pos60`
- `pos250`
- `dist_high20_atr`
- `near_high20_state`
- `near_high60_state`
- `drawdown20_state`
- `drawdown60_state`

严格执行 §10C。

不得把 near-high / drawdown 解释成突破确认或统一风险。

---

## 5.3 MA Structure

必须正式输出：

`ma_structure_state`

其输入包括：

- MA5
- MA10
- MA20
- slope20

MA10 不允许通过修改 V4-03 Artifact 解决。

从 Accepted V4-02 Canonical Daily 按冻结窗口合同派生。

---

## 5.4 Relative Market

正式输出：

`relative_market_state`

必须显式保存真正影响状态的依赖：

- rps5
- rps20
- rps20_delta3
- rel_market_1
- rel_market_5
- compression_state
- ma_structure_state

当前 `relative()` 只把 numeric primitive 放入 evidence 是不完整的。

修改 evidence schema，使 dependency state 也可被保存、hash 和独立复算。

---

## 5.5 Compression

正式输出：

`compression_state`

输入：

- range_ratio
- atr_ratio
- vol_ratio
- amount_ratio20
- minimum_liquidity

当前代码必须修复：

`minimum_liquidity` 必须进入 rule evidence / input digest。

V4-03 没有该字段时，不得声明阻塞。

按照已冻结合同从 Accepted V4-02 amount history 派生：

`prior20 mean amount >= 20,000,000 CNY`

必须遵循正式 valid-session / prior-window 语义，不得把当前 T 日错误计入 prior20。

---

## 5.6 Amount / Volume / Participation

正式输出：

- `amount_state`
- `volume_state`
- `core_participation_result`

禁止继续只留下无限制的：

`ratio_state(inputs, arbitrary_key)`

应建立显式 producer，或者至少严格 allowlist：

`amount_state ← amount_ratio20`

`volume_state ← volume_ratio20`

所有 first-true / UNKNOWN / CLV branch 规则必须和 §10G 一致。

---

## 5.7 Extension Risk

正式输出：

- `core_extension_risk`
- `severe_extension`

执行：

- EXTREME
- HIGH
- MEDIUM
- LOW

保持 branch-required / UNKNOWN 语义。

不得引入 turnover。

---

# 6. Accepted Input Resolver

不得直接凭文件名读取 staging 文件。

新增正式 Accepted Input Resolver。

从以下 authority 开始：

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

解析并校验：

- V4-01 Accepted identity
- V4-02 Accepted Head
- V4-03 Accepted Head Amended R1

至少绑定以下来源：

- V4-02 Accepted Canonical Daily
- V4-02 Accepted closed weekly periods
- V4-02 Accepted closed monthly periods
- V4-03 accepted full-scope Stock Core factors
- required Universe / identity / calendar

对每个 consumed artifact：

- 验证 path
- 验证 SHA256
- 验证 source_cutoff
- 验证 contract/version
- 验证 board scope
- 验证 trade_date/asof

任何 identity/hash 不一致：

`FAIL CLOSED`

禁止静默寻找“另一个差不多的文件”。

---

# 7. Missing Primitive Derivation

只对 V4-04 合同需要、而 Accepted V4-03 没提供的字段进行派生。

至少包括：

- MA10
- pos250
- dist_high20_atr
- near_high20_state inputs
- near_high60_state inputs
- drawdown20_state inputs
- drawdown60_state inputs
- weekly MA5 / previous MA5
- monthly MA3 / previous MA3
- minimum_liquidity

优先复用 V4-03 已有：

- prior_high20
- prior_high60
- HHV20
- HHV60
- ATR20
- close
- amount / amount ratios 等

禁止重复计算已有 Accepted factor 后产生第二套语义。

派生字段必须拥有独立：

- contract_id
- parameter identity
- input digest
- window identity
- source digest
- quality / unknown reason

---

# 8. Full-Market Core Profile Builder

新增正式 Full-Market Builder。

必须覆盖 V4 Required Equity Scope：

- SH_MAIN
- SZ_MAIN
- CHINEXT
- STAR

BSE 保持此前 accepted optional-degraded 语义，不得反向阻断 required boards。

as-of/source cutoff：

`2026-09-24`

Builder 必须做到：

- Accepted-input-only
- PIT / time semantics explicit
- deterministic
- fail-closed
- no future data
- no Sector Context dependency
- no BaoStock dependency
- no Advanced Structure dependency
- no scanner dependency
- no trading dependency

---

# 9. Final Core Profile Row

每一个 stock/date Core Profile row 至少保存：

- security_id
- symbol/display identity
- trade_date
- board
- publication_id / staging identity
- source_cutoff
- 所有 V4-04 Core states
- 对应 primitive / derived field quality

每个 state：

- value
- contract_id
- parameter_set_id
- input evidence
- input digest
- source digest
- UNKNOWN reason

以及：

- profile component status
- profile quality
- source_asof
- technical_window_identity
- actual_count / calendar-span 等必要窗口 metadata

UNKNOWN 必须与：

- NOT_IMPLEMENTED
- NOT_APPLICABLE
- PENDING_SOURCE
- DEGRADED

明确区分。

---

# 10. Rule Evidence 修复

当前：

`State.evidence: dict[str, float | bool | None]`

不足以表达 `relative()` 的：

- compression_state
- ma_structure_state

必须改造成可以保存完整 typed dependency evidence 的结构。

同时修复：

- compression evidence 缺少 `minimum_liquidity`
- relative evidence 缺少 dependency states

所有影响最终枚举值的条件必须可以从 row evidence 独立重放。

---

# 11. Tests

不得再以当前两个测试函数结束 V4-04。

至少覆盖所有 Rule AST branch、边界和 UNKNOWN 路径。

包括：

## Trend

- 每个 first-true branch
- slope ±0.1 边界
- price = MA 边界
- core_price_damage TRUE/FALSE/UNKNOWN

## Weekly / Monthly

- Weekly CLOSED_ONLY
- Monthly CLOSED_ONLY
- 未闭合 period 不得污染正式状态

## Position

- 所有 bucket
- near-high ABOVE/NEAR/BELOW
- drawdown SHALLOW/MODERATE/DEEP
- ATR=0 / history insufficient UNKNOWN

## MA Structure

- alignment
- transition
- mixed

## Relative

- ACTIVE_EMERGENCE
- PASSIVE_RESILIENCE
- LEADING_ACCELERATING
- LEADING_STABLE
- IMPROVING
- WEAKENING
- LAGGING
- NEUTRAL
- dependency UNKNOWN

## Compression

- EXPANDING_EXTREME
- EXPANDING
- COMPRESSING_STRONG
- COMPRESSING
- NORMAL
- UNKNOWN

## Amount / Volume

- 全 buckets

## Participation

- 全 branches
- CLV unknown

## Extension Risk

- 全 branches
- branch-specific missing inputs

另外必须有：

- Accepted identity mismatch fail-closed test
- hash mismatch fail-closed test
- source cutoff mismatch test
- board coverage test
- full-market schema test
- deterministic rerun test
- UNKNOWN propagation test

测试数量不设人为最低值，以语义覆盖完整为准。

---

# 12. Full-Market Production

完成实现后，必须真正运行一次 Required Scope Full-Market V4-04 production。

不得只使用 synthetic fixture 宣布完成。

生成 versioned staging artifact。

同时生成至少：

- stage manifest
- row count / board count receipt
- field completeness receipt
- UNKNOWN / quality inventory
- consumed source manifest
- input identity receipt
- parameter/contract digest receipt
- determinism receipt

---

# 13. Independent Recompute

必须实现独立 postcheck。

不能直接调用生产 producer 再比较自己。

独立重算至少核对：

- input identity
- row identity
- 关键 primitives
- 所有状态 AST
- weekly/monthly CLOSED_ONLY
- minimum_liquidity
- MA10
- pos250 / near-high / drawdown
- amount/volume
- extension risk
- output digest

抽样必须包含：

- 正常股票
- 近期上市
- 停牌/复牌
- 高位
- 低位
- UNKNOWN row
- 不同 required boards
- threshold boundary

并进行 deterministic full rerun digest comparison。

---

# 14. Publication / Acceptance

只有在所有 Required Scope gate 通过后，才能创建：

V4-04 Final Stage Receipt

以及：

`data/v4/V4_04_ACCEPTED_HEAD.json`

再更新 global Stage Accepted Head。

Accepted Head 必须 hash-bind：

- implementation commit
- field registry
- algorithm contracts
- parameter identity
- input accepted heads
- full-market artifact
- manifest
- tests
- independent postcheck
- determinism evidence

Publication 必须原子接受。

失败 staging 不得成为 visible accepted output。

---

# 15. Explicit Forbidden Work

本任务禁止：

- 修改 TDX source root
- 重新打开 V4-00～03 已接受业务语义
- Sector membership repair
- V4-08 work
- BaoStock Turnover / §10H
- Structure / Anchor / Support
- PREWATCH
- Radar
- Focus cutover
- scanner execution
- trading execution
- V4-05 Replay Gate A

V4-05 只有在 V4-04 完成独立验收后才能入场。

---

# 16. Final Required Status

本任务结束时只能输出其中之一：

`V4_04_FULL_PASS_CANDIDATE`

或：

`V4_04_BLOCKED_<EXACT_SCOPE>`

禁止：

- PARTIAL 被包装成 PASS
- unit tests 被包装成 Full-Market acceptance
- 规则文件存在被包装成 production ready

若为 `PASS_CANDIDATE`：

停止执行。

提交全部代码、配置、测试、full-market artifact identity、stage receipts 和审计文档，等待独立外部验收。

不得自行开始 V4-05。

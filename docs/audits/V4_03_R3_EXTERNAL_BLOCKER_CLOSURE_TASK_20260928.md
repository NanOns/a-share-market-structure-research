# V4-03 R3 剩余阻断项闭环任务卡

- 项目：大A市场结构研究系统 V4
- 阶段：V4-03 Pure-Core Factors
- 任务性质：R3 / External Blocker Closure
- 日期：2026-09-28
- 执行分支：`codex/v4-system-reform`
- 当前审计基线 HEAD：`c8c8f1287c913bebbe5e5d19eee01af7fbb96309`
- 当前关键实现提交：`1636838fdf7b130fa97a01b778fc1a05a2f9bb07`
- 当前外部结论：`EXTERNAL_ACCEPTANCE_BLOCKED`
- 当前 V4-04 门禁：`BLOCKED`
- 本任务完成后目标：只关闭 V4-03 仍然真实存在的 blocker；不得提前实现 V4-05 Replay Gate A，不得返工已经通过的 V4-03 审计项。

---

## 0. 任务总原则

本轮不是“重做 V4-03”，而是对已经完成的大部分实现进行**剩余阻断项闭环**。

必须严格遵守：

1. 已经通过的内容不得无理由重构。
2. 不得把 V4-05 的完整历史 Data/Factor Replay Gate 提前塞回 V4-03。
3. 不得因为 Sector membership 缺失而无限阻断与 Sector 无依赖的 Stock Core；Sector 必须按 capability scope 处理。
4. 当前任何 candidate、diagnostic、测试 PASS 都不得自动升级成 stage acceptance。
5. V4-04 在本任务完成并通过新的独立外部验收之前继续 `BLOCKED`。
6. 不得修改 V4-01 / V4-02 accepted input identities。
7. 不得启动 scanner、正式交易、Focus cutover 或任何后继阶段生产能力。
8. 不得写入 TDX root。
9. 不得通过伪造历史 sector membership、当前成员回填历史、未来信息回填 PIT 等方式“解决”输入缺口。
10. 不得为了凑 PASS 修改审计标准；如需修改合同，必须形成显式、版本化、可审计的 amendment。

---

# 1. 当前已经通过的内容 —— 禁止返工

以下项视为本轮冻结通过，不得重新大改：

## 1.1 B02 — MARKET_REGIME trend WEAK 语义

状态：

`PASS`

已确认：

- STRONG / WEAK 对称；
- mixed state -> NEUTRAL；
- insufficient input -> UNKNOWN；
- future offset 未引入。

除非本轮 Market Regime materialization 暴露新的可复核硬错误，否则不得重写规则。

---

## 1.2 C01 — suspended T0 下 prior extrema

状态：

`PASS`

已确认：

- prior_high / prior_low 不错误依赖当前 T0 actual bar；
- technical window 与 current-required 字段已区分；
- 停牌 T0 行为有测试覆盖。

不得返工。

---

## 1.3 C02 — 47 字段 output schema

状态：

`PASS`

`config/v4_03_output_schema_v1.json` 已形成 47 字段正式 schema。

不得重新改变字段数量、名称或基本 producer scope，除非为修复明确的 producer identity 冲突。

---

## 1.4 C03 — 47 字段统一集成

状态：

`PASS`

已形成：

- 5,222 securities；
- 47 fields；
- 独立逐字段 value / quality / reason / identity postcheck；
- mismatch = 0。

**不得再把“逐历史 T 全量 replay”作为 C03 的未完成项。**

完整 Data/Factor Replay Gate 属于：

`V4-05 Replay Gate A / DATA_FACTOR_REPLAY_PASS`

本轮不得提前实现完整 V4-05。

---

## 1.5 C06 — Sector field-local denominator

状态：

`PASS`

quote / amount / ret1 / MA20 已按字段局部质量集合计算。

不得恢复统一 row-level quality gate。

---

## 1.6 C07 — Market path unknown suffix semantics

状态：

`PASS`

已确认：

- 当前 series version 一旦出现未知 daily return，后续 suffix 继续 UNKNOWN；
- 重新起算必须新 `series_version`；
- 不允许同一 series 内偷偷 rebase。

注意：C07 语义通过不代表 C05 的完整 historical market path 已物化。

---

## 1.7 B01 原始实现缺陷

以下旧问题视为已关闭：

> AST 仅做结构校验，从未真正进行数值执行。

当前已经存在 `RULE_AST_V2` 数值执行器和 47 合同执行路径。

本轮 B01 只处理“machine-contract golden vectors 覆盖不足”，不得推翻已有执行器重新造第三套框架。

---

## 1.8 C04 digest 独立重建子项

当前 R2 independent postcheck 已独立重建：

- `input_digest`
- `window_identity`
- `output_digest`

且 identity mismatch 为 0。

这一子项视为通过。

本轮 C04 只处理**正式 PIT / accepted prior-RPS lineage**。

---

# 2. P0-1：补齐 Machine-Contract Golden Vectors

## 2.1 当前问题

当前 47 个算法合同虽然已经真实执行 AST，但每个字段通常只有：

- 1 个 `OBSERVED`
- 1 个 `UNKNOWN_INPUT`

且 `UNKNOWN_INPUT` 主要通过清空全部 history / relative input 实现。

这不足以满足 V4-03 task 原始验收门中的正反向 golden-vector 覆盖要求。

## 2.2 本轮要求

不得为每个字段机械复制大量无意义向量。

应按**算法族 / window contract / failure semantics**设计共享 fixture + 独立 contract vectors，至少真实覆盖以下边界：

### A. Technical-bar window

必须覆盖：

- exact N actual bars；
- one-short history；
- confirmed suspension 跨越但不消耗 actual-bar count；
- suspension at T0；
- resume after suspension；
- unexplained gap -> UNKNOWN；
- mixed adjustment identity -> UNKNOWN；
- nonpositive required price -> UNKNOWN；
- current bar unavailable 对 current-required 字段与 prior-only 字段的差异。

### B. Cross-section session window

必须覆盖：

- endpoint missing / suspended；
- intermediate confirmed suspension；
- unexplained intermediate gap；
- exact session endpoint；
- PIT Universe 成员变化；
- n < 2；
- partial evaluable set；
- coverage / count identity。

### C. Arithmetic / denominator

必须覆盖：

- zero denominator；
- flat range；
- amount/volume denominator = 0；
- log / return 非法输入；
- UNKNOWN propagation 在具体节点发生，而不是仅“所有 input 清空”。

### D. Ranking

必须覆盖：

- strict ordering；
- full tie；
- partial tie；
- missing member；
- target missing；
- Universe membership change；
- deterministic reorder invariance。

### E. Adjustment / source identity

必须覆盖：

- 同坐标；
- source revision mismatch；
- adjustment basis mismatch；
- input source identity 改变导致 digest 改变。

## 2.3 实现约束

优先扩展现有：

- `config/v4_03_ast_numeric_fixture_v1.json`
- `config/v4_03_algorithm_contracts_v1.json`
- `src/v4/contracts/algorithm_contract_numeric_v12.py`
- `scripts/verify_v4_03_ast_numeric_vectors.py`

不得再新造平行的 AST framework。

允许：

- 一个 fixture 内多个 named cases；
- 多个共享 edge-case fixture；
- contract vector 引用 case + expected。

要求 machine executor 对每个 case 真正执行 AST。

## 2.4 必须生成的证据

建议新增：

`reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json`

至少记录：

- contract_set_sha256
- framework_sha256
- parameter_registry_sha256
- fixture_sha256 / fixture set hashes
- contract_count
- vector_count
- case_category_count
- passed_count
- failed_count
- per-category coverage
- exact numeric tolerance
- negative/tamper detection
- status

最终不得使用模糊：

`94 vectors passed`

替代覆盖说明。

必须明确：

`哪些语义边界被哪些 case 覆盖`。

---

# 3. P0-2：C04 Prior RPS 正式 PIT Lineage 闭环

## 3.1 当前问题

目前：

`prior_rps_origin = DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`

当前代码在 cutoff 运行中现场重新计算 t-1 / t-3 的历史 RPS。

数学值可以正确，但这不能形成正式 prior artifact lineage。

## 3.2 本轮目标

建立**历史 as-of 身份明确的 prior RPS staging artifact / lineage**，使 delta 字段消费的是可审计、阶段拥有的历史 prior identity，而不是一段现场临时 hash。

需要闭环的字段至少包括：

- `rps5_delta1`
- `rps5_delta3`
- `rps20_delta3`

## 3.3 可接受方案

优先方案：

### 方案 A — V4-03 stage-owned historical RPS staging

对本轮 cutoff 所需 prior dates：

- t-1
- t-3

按对应历史 PIT Universe、对应 endpoint data、对应 adjustment/source identity 生成独立 RPS artifact。

每个 artifact 必须具有：

- trade_date
- field_id
- contract_id / version
- parameter_set_id
- universe_snapshot_id
- member/evaluable count
- input_source_digest
- adjustment_basis_identity
- input_digest
- output_digest
- artifact_sha256
- evidence_origin

随后 current delta producer 只消费该 artifact 的正式 digest。

### 方案 B — 若合同允许 same-stage historical staging chain

可以在一次 stage pipeline 中先生产：

`historical RPS staging`

然后再生产：

`current relative/delta staging`

但必须有明确先后 DAG 和 artifact boundary。

不得继续：

`在 delta 计算函数内部临时计算 prior scores + 自造摘要`。

## 3.4 重要限制

本轮只需要关闭 V4-03 对当前正式 staging 所需的 prior lineage。

**不得为了这一项提前构造全部 786 日 full replay acceptance。**

全历史 Replay Gate 仍属于 V4-05。

## 3.5 Independent Postcheck

独立程序必须从 accepted V4-01/V4-02 inputs 重建：

- prior PIT Universe
- prior RPS values
- prior artifact input digest
- prior artifact output digest
- current delta input digest
- final delta value

不得导入生产 relative/rps producer。

必须做到：

`prior artifact SHA / digest 与 producer 消费值一致`。

## 3.6 必须生成的证据

建议：

- `V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json`
- `V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json`

最终 full-scope candidate 中必须移除：

`DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`

并替换成真实 lineage 描述。

---

# 4. P0-3：完成 V4-03 Historical Market Reference Path

## 4.1 当前问题

当前 R2：

`market_path_status = NOT_COMPUTED_HISTORICAL_DAILY_CHAIN_PENDING`

且：

`market_path_candidate_sha256 = null`

这是真正属于 V4-03 的未完成项，不是 V4-05 replay。

## 4.2 本轮目标

根据 V4-03 task 和：

`V4_03_MARKET_REFERENCE_PATH_V1`

生成完整、版本化、可审计的 historical market reference path staging artifact。

## 4.3 数据语义

每个历史 market step 必须使用：

- 对应 start session 的 PIT Universe；
- 对应 accepted daily data；
- 对应 adjustment identity；
- 对应 market calendar；
- field-local evaluable members；
- coverage / missing count；
- `MARKET_RELATIVE_REFERENCE_V1` 产生的 daily market return。

不得：

- 使用当前 2026-09-24 Universe 回填历史；
- 将 endpoint 1/3/5 平均收益冒充 daily rebalanced path；
- 使用 future constituent knowledge；
- 遇到 UNKNOWN 后静默跳日。

## 4.4 输出要求

historical path 每行至少保存：

- start_session
- end_session
- daily_return
- level
- quality_state
- unknown_reason
- start_universe_snapshot_id
- evaluable_set_identity
- universe_count
- evaluable_count
- coverage
- adjustment_basis_id / identity
- market_calendar_id
- input_source_digest
- window_identity
- input_digest
- output_digest
- series_version

## 4.5 Independent Postcheck

必须使用独立实现：

- 重算 daily equal-weight endpoint return；
- 重建每个历史 session 的 PIT member set；
- 重算 path level；
- 重算 identity / digests；
- 检查 UNKNOWN suffix 规则。

不得导入生产 `historical_market_path()` 作为 independent calculator。

## 4.6 必须生成证据

建议：

- `V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz`
- `V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json`
- `V4_03_MARKET_REFERENCE_PATH_INDEPENDENT_POSTCHECK_R3.json`

要求：

- artifact SHA 固定；
- rows/session count 明确；
- first session / last session 明确；
- PIT identity mismatch = 0；
- numeric mismatch = 0；
- digest mismatch = 0。

---

# 5. P0-4：完成 Market Regime Native Daily Materialization

## 5.1 当前问题

目前只有：

- `market_axis_primitives()`
- `market_trend_axis()`
- unit tests

但：

`regime_full_market_materialization = NOT_PRODUCED`

因此函数级实现并不等于 V4-03 native artifact 已完成。

## 5.2 本轮目标

为 V4-03 scope 中的 market primitives 形成真实 daily staging artifact。

至少包括：

- breadth_axis
- participation_axis
- stress_level
- stress_change
- trend_axis

并保存完整输入身份。

## 5.3 输入必须可审计

每个 axis 的原始输入必须明确来自哪个已冻结 fact / calculation。

不得只保存最终枚举而不保存：

- primitive raw value
- denominator
- coverage
- quality
- source digest
- parameter identity

尤其：

### trend

必须保存：

- index_close
- index_ma20
- index_ma20_t_minus_5
- input/source identity

### stress

必须保存：

- stress numerator / denominator 或实际 raw primitive
- limit coverage
- prior stress identity

### breadth / participation

必须明确计算 universe 与 denominator。

## 5.4 Independent Postcheck

独立 postcheck 必须重算：

- raw primitive
- threshold comparison
- final axis
- field quality
- input/output digests

并记录 mismatch。

## 5.5 必须生成证据

建议：

- `V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz`
- `V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json`
- `V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json`

---

# 6. P0-5：Native Contract Registry 机器合同闭环

## 6.1 当前问题

当前 native registry 的 4 个 contract：

- `MARKET_RELATIVE_REFERENCE_V1`
- `V4_03_MARKET_REFERENCE_PATH_V1`
- `MARKET_REGIME_V1_PRIMITIVES`
- `V4_03_SECTOR_NATIVE_PRIMITIVE_V1`

当前只有描述性：

`algorithm: {...}`

没有：

- executable AST；
- independent vectors。

这与 V4-03 task 的 Contract Generation 验收门不一致。

## 6.2 本轮要求

二选一。

### 优先：方案 A — 补机器合同

为 native contracts 增加可执行 AST / rule tree 与 independent vectors。

如现有 `RULE_AST_V2` 无法表达 path state / aggregate object / member-set identity，可以：

- 使用 versioned native-rule AST extension；
- 或明确扩展 RULE_AST_V2 operator。

但必须：

- 版本化；
- validator 可执行；
- vectors 可执行；
- 不修改既有 1.1 contract 原文件；
- 不把生产函数本身当 evaluator。

### 备选：方案 B — 正式 contract amendment

只有在证明现有通用 AST 不适合表达 stateful native path 时，才允许形成正式 amendment：

- 明确 native contract 为 machine-readable deterministic rule schema，而不是 RULE_AST；
- 明确为什么；
- 定义 machine validator；
- 定义 independent vectors；
- 外部验收必须接受 amendment。

不得仅说：

`native 太复杂，所以 description algorithm 足够。`

## 6.3 Vector 要求

Native vectors 至少覆盖：

### Market reference
- normal coverage
- missing threshold
- Universe n<2
- tie 不相关但 evaluable-set identity 改变
- endpoint unavailable

### Market path
- normal chain
- missing daily return
- UNKNOWN suffix
- new series rebase
- PIT Universe change

### Market regime
- threshold exact boundary
- above / below
- UNKNOWN input
- mixed trend -> NEUTRAL
- coverage insufficient

### Sector native
- field-local denominator
- empty member set
- partial evaluable rows
- member reorder determinism
- member change
- missing membership identity

---

# 7. P0-6：修复 `trend_axis` Producer Identity 冲突

## 7.1 当前冲突

当前：

`config/v4_03_native_scope_map_v1.json`

声明：

`trend_axis -> MARKET_REGIME_TREND_WEAK_ERRATUM_V1`

`src/v4/factors/native.py::market_trend_axis()`

也输出：

`contract_id = MARKET_REGIME_TREND_WEAK_ERRATUM_V1`

但：

`config/v4_03_native_contract_registry_v1.json`

中的 `MARKET_REGIME_V1_PRIMITIVES` 又把：

`trend_axis.producer_contract_id = MARKET_REGIME_V1_PRIMITIVES`

这违反：

`一个消费字段只能有唯一 producer identity`

## 7.2 修复要求

推荐：

- `MARKET_REGIME_TREND_WEAK_ERRATUM_V1` 作为 `trend_axis` 唯一 producer；
- `MARKET_REGIME_V1_PRIMITIVES` 只聚合/引用该字段，不再次声明自己生产 trend_axis。

如果设计上决定反过来，则必须：

- scope map
- native registry
- runtime output
- schema
- tests
- receipts

全部统一。

不得保留“双 producer”。

## 7.3 验收

新增 contract-consistency test：

对全部 V4-03 field：

`scope map producer == registry producer == runtime producer/schema producer`

不一致直接 FAIL。

---

# 8. P1：Sector Membership 的正确处理

## 8.1 当前事实

当前 accepted V4-01/V4-02 baseline 没有可用于历史 sector full-market materialization 的 accepted PIT sector membership。

因此：

`V4_03_SECTOR_NATIVE = BLOCKED`

当前 fail-closed 是正确的。

## 8.2 严禁

不得：

- 当前 sector member list 回填历史；
- legacy non-PIT member list 冒充 accepted PIT；
- 用 inferred membership 伪造 historical member snapshot；
- 为赶 V4-03 PASS 临时放宽 historical sector contract。

## 8.3 两种合法路径

### Path A — 真正补 accepted sector membership source

只有已有可验证历史 source 时执行。

需要独立 task / source contract / acceptance。

### Path B — Capability-scoped degradation

如果当前没有可靠历史 membership，则本轮应正式记录：

`V4_03_STOCK_CORE = eligible_for_acceptance once stock/market blockers close`

`V4_03_MARKET = eligible_for_acceptance once market blockers close`

`V4_03_SECTOR_NATIVE = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`

并声明：

- V4-04 Stock Core 可在 Stock+Market 通过后单独授权；
- V4-08 Sector / Rotation 继续 BLOCKED；
- 所有 sector-dependent stock paths 继续 BLOCKED / SHADOW_ONLY。

这一 scope 处理必须有正式 stage disposition / dependency map，不能只写 README。

---

# 9. P1：修复 R2 Task Traceability

## 9.1 当前问题

当前仓库真实存在：

`docs/audits/V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_20260927.md`

但多份 R2 evidence 引用：

`V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_R2_20260928.md`

当前仓库中该文件不存在。

## 9.2 修复方式

二选一：

### A. 正式创建 R3 governing task

建议直接将**本任务卡**提交仓库：

`docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md`

并声明：

- base task = `V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_20260927.md`
- R1/R2 external audits = evidence
- 本文件只修复剩余 blocker
- 不重定义 V4-05 replay scope

随后所有新 R3 receipts 引用此 task。

### B. 修正旧 R2 evidence 的 governing reference

如果不创建 R2 文件，则不能继续声称不存在的 R2 task 是 governing contract。

**推荐采用 A。**

---

# 10. 测试要求

本轮必须至少运行：

```bash
pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py
```

新增测试必须包含：

1. expanded AST golden cases；
2. prior RPS staging lineage；
3. prior artifact tamper detection；
4. Market path full historical chain；
5. Market path independent digest；
6. Market Regime materialization；
7. Native contract/vector validator；
8. trend_axis unique producer；
9. Sector scoped-block behavior；
10. deterministic replay for new R3 artifacts。

---

# 11. Determinism / Tamper Tests

对以下 artifact 至少执行两次 deterministic replay：

- prior RPS staging；
- full-scope candidate；
- market reference path；
- market regime native；
- contract vector receipt。

要求：

`same accepted inputs + same contract + same parameter set -> same SHA`

必须增加 tamper tests：

- 修改 prior RPS artifact 一个 score -> downstream validation FAIL；
- 修改 Universe snapshot id -> FAIL；
- 修改 market path daily return -> path output digest FAIL；
- 修改 contract expected vector -> vector acceptance FAIL；
- 修改 trend producer identity -> consistency test FAIL。

---

# 12. 证据产物要求

本轮完成后至少提交以下机器证据。

建议文件名：

```text
reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json
reports/v4_03/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json
reports/v4_03/V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json
reports/v4_03/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json
reports/v4_03/V4_03_MARKET_REFERENCE_PATH_INDEPENDENT_POSTCHECK_R3.json
reports/v4_03/V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json
reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json
reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json
reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json
reports/v4_03/V4_03_DETERMINISM_REPLAY_R3.json
reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json
```

可根据实现略微调整文件名，但职责不可合并到一个无法审计的大 JSON 中。

---

# 13. Stage Disposition 规则

R3 执行结束时，不得直接生成 PASS。

先生成：

`V4_03_STAGE_DISPOSITION_R3`

必须逐 capability 给出：

- STOCK_CORE
- RELATIVE_RPS
- MARKET_REFERENCE
- MARKET_REGIME
- SECTOR_NATIVE

每项状态只能是：

- PASS_CANDIDATE
- BLOCKED
- DEGRADED
- NOT_APPLICABLE

并列出：

- contract hashes
- source hashes
- artifact hashes
- tests
- independent postchecks
- residual blockers
- downstream dependency permissions

---

# 14. 最终 V4-03 接受条件

只有以下全部成立，才允许重新提交外部验收：

## Stock / Relative

- 47 fields schema unique；
- 47-field candidate integrated；
- machine AST executable；
- golden vectors 覆盖 task 边界；
- prior RPS lineage 不再是 `DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`；
- independent value/quality/digest postcheck PASS。

## Market

- historical market reference path 正式 materialized；
- PIT historical Universe identity 完整；
- Market Regime daily primitives materialized；
- independent market path/regime postcheck PASS；
- trend_axis producer 唯一。

## Native contracts

- Native deterministic contract 可机器验证；
- independent vectors 存在并执行；
- producer/schema/runtime identities 一致。

## Sector

以下二者之一：

A. accepted PIT sector membership + full native artifact PASS；

或：

B. 正式 capability-scoped degradation，明确 Sector/Rotation blocked，但不污染 Stock Core。

## Governance

- R3 task 已提交；
- 不再引用不存在的 governing task；
- V4-01/V4-02 accepted identities 未改变；
- scanner/trading/TDX writes = 0；
- no premature V4-04 execution；
- final external acceptance 尚未通过前不得创建 accepted head。

---

# 15. 明确禁止提前做的工作

本轮禁止实现：

- V4-04 Full-Market Core Profile；
- V4-05 全历史 Data/Factor Replay Gate A；
- V4-06 Turnover；
- V4-07 Seed；
- V4-08 正式 Sector qualification / Rotation；
- PREWATCH；
- Structure / Anchor / Support；
- Radar；
- Cohort / Settlement；
- Shadow；
- Focus；
- Trading。

特别强调：

**不要为了关闭 C03 去做全部历史 T 的 47-field replay。**

该工作属于 V4-05。

---

# 16. Codex 最终提交说明必须回答的问题

最终提交报告不得只写“全部测试通过”。

必须逐条回答：

1. B01 golden-vector gate 是否关闭？新增了哪些 edge cases？
2. prior RPS 是否仍含 `DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`？如果没有，新的 lineage 是什么？
3. historical market path 是否已形成 artifact？session 数量、SHA、PIT source 是什么？
4. Market Regime 是否已形成 daily artifact？独立 postcheck 是否重算？
5. 4 个 native contracts 如何满足 machine-contract + vector requirement？
6. `trend_axis` 最终唯一 producer 是谁？
7. Sector membership 是真正解决，还是 capability-scoped degradation？
8. 是否修改任何 V4-01/V4-02 accepted identity？
9. 是否启动任何 V4-04/V4-05 后继逻辑？
10. 当前是否有资格申请 V4-03 final external acceptance？

---

# 17. 本轮预期结果

理想结果不是“强行 FULL PASS”。

正确结果应是以下之一。

## Result A — 全量 V4-03 可验收

```text
STOCK_CORE = PASS_CANDIDATE
RELATIVE_RPS = PASS_CANDIDATE
MARKET_REFERENCE = PASS_CANDIDATE
MARKET_REGIME = PASS_CANDIDATE
SECTOR_NATIVE = PASS_CANDIDATE

V4_03_EXTERNAL_REVIEW_READY = TRUE
V4_04_ENTRY = STILL_BLOCKED_UNTIL_EXTERNAL_ACCEPTANCE
```

## Result B — Sector scoped degraded，但 Stock/Market 已闭环

```text
STOCK_CORE = PASS_CANDIDATE
RELATIVE_RPS = PASS_CANDIDATE
MARKET_REFERENCE = PASS_CANDIDATE
MARKET_REGIME = PASS_CANDIDATE
SECTOR_NATIVE = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP

V4_03_EXTERNAL_REVIEW_READY = TRUE_WITH_CAPABILITY_SCOPE
V4_04_STOCK_CORE_ENTRY = PENDING_EXTERNAL_ACCEPTANCE
V4_08_SECTOR_ENTRY = BLOCKED
```

## Result C — 任一 Stock/Market P0 未关闭

```text
V4_03_EXTERNAL_REVIEW_READY = FALSE
V4_04_ENTRY = BLOCKED
```

不得把 Result C 包装成 PASS。

---

# 18. 提交建议

建议最终实现 commit message：

```text
[V4-03] Close remaining stock market and native contract blockers
```

如需单独治理提交：

```text
[V4-03] Freeze R3 blocker closure task and scoped acceptance rules
```

最终 push 后，提供：

- 精确 commit SHA；
- `git status`；
- 测试摘要；
- 新增/修改文件清单；
- 所有 R3 receipt；
- 当前 stage disposition；
- 明确请求独立外部验收。

在独立外部验收签发之前：

```text
V4_03_FINAL_ACCEPTANCE = NOT_GRANTED
V4_04_ENTRY = BLOCKED
```

## 仓库内治理关系

基础任务：V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_20260927.md。R1/R2 外部审计为证据。本 R3 只闭环剩余阻断项，不重定义 V4-05 Replay Gate A。

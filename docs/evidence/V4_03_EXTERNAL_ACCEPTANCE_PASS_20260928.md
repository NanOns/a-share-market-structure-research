# V4-03 独立外部验收结论

- 日期：2026-09-28
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 验收 HEAD：`e19bd4f376d9e47ae14610ad5c93247f3513c4bd`
- 提交：`[V4-03] Correct REV2 market regime primitives and R3 evidence`
- 当前业务优先级：增量更新能力暂缓，不作为 V4-03 主功能放行条件；开发期允许后续通过代码重新全量运行历史数据。

## 1. 最终裁决

```text
V4_03_EXTERNAL_ACCEPTANCE = PASS_WITH_CAPABILITY_SCOPE

V4_03_STOCK_CORE = PASS
V4_03_RELATIVE_RPS = PASS
V4_03_MARKET_REFERENCE = PASS
V4_03_MARKET_REGIME = PASS

V4_03_SECTOR_NATIVE = DEGRADED_BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
V4_03_OVERALL = PASS_WITH_SECTOR_SCOPE_DEGRADED

V4_04_STOCK_CORE_ENTRY = AUTHORIZED_AFTER_FINAL_SEAL
V4_08_SECTOR_ENTRY = BLOCKED
INCREMENTAL_UPDATE = DEFERRED_NON_BLOCKING
```

## 2. Market Regime REV2 公式复验

上一轮硬错误已真实关闭。

- `breadth_axis`：使用 `M_t ∩ M_(t-3)` PIT 共同成员，并进一步要求两端 `ret1` 都可评估，在完全相同成员集合分别重算 breadth，最后得到 `breadth_delta3`。符合 REV2 §27 与共同成员 delta 定义。
- `participation_axis`：当日 PIT Universe 每只成员按自身此前 20 个有效实际交易 bar 计算 `amount_ratio20`，confirmed suspension 可跨过，unexplained gap / mixed basis 令对应成员 UNKNOWN，最终取横截面 median。符合 `median(member amount_ratio20)`。
- `stress_level`：按当日 PIT members 的有效涨跌停事实覆盖与 `down_limit_count/evaluable_count`。
- `stress_change`：使用 t 与 t-1 PIT 共同成员、且两端 limit status 均可评估的同一集合，分别重算两端跌停比率再比较。符合“同成员比率日差”。
- `trend_axis`：继续由 `MARKET_REGIME_TREND_WEAK_ERRATUM_V1` 唯一生产，无回归。

## 3. Market Regime 独立证据

`V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json`：

- rows = 786
- evidence_origin = `V4_03_PIT_STAGING_CANDIDATE`
- formula_contract = `MARKET_REGIME_V1_REV2_SECTION_27`
- output SHA = `89aae8484aa98837c3d6c685d48365edae2913ac506dd12916f8c56e92a9b139`

`V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json`：

- rows_checked = 786
- mismatch_rows = 0
- independent_producer_imports = []
- contract_conformance = PASS
- candidate receipt SHA match = true

独立实现重新计算 common-member breadth、member amount-ratio median、same-member stress change 和 trend 输入，因此上一轮的 `MARKET_REGIME_CONTRACT_FORMULA_MISMATCH` 已关闭。

## 4. Native machine contract

**PASS**。

`V4_03_NATIVE_DETERMINISTIC_RULE_SCHEMA_R3` 已升级至 v1.1.0，并新增 `MARKET_REGIME_REV2_RAW`，机器合同不再只验证 threshold mapping，而是冻结：

- PIT common-member t/t-3 breadth derivation；
- member amount_ratio20 的 prior-20-actual-bar 规则；
- suspension/gap/basis 语义；
- PIT common-member t/t-1 stress derivation；
- raw primitive -> axis mapping。

`V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json`：4 contracts、25 vectors、0 fail、`market_regime_raw_derivation_covered=true`。

## 5. PIT metadata

**PASS**。

R3 正式候选路径已从错误的 `DIAGNOSTIC_NON_PIT` 改为：

`V4_03_PIT_STAGING_CANDIDATE`

同时保留 `CANDIDATE_NOT_STAGE_ACCEPTANCE`，正确区分 PIT correctness 与 stage acceptance/publication permission。

## 6. Determinism

**PASS**。

verifier 已改为：若 baseline 已存在，则要求 `baseline == replay1 == replay2`。

当前 prior_rps / market_path / full_scope / market_regime / contract_vectors 五类 artifact 均三者 SHA 一致。

## 7. 既有主链通过项

继续保持 PASS：

- 47-field output schema；
- 5,222 securities × 47 fields unified candidate；
- 47 字段 independent values / quality / identity postcheck；
- input_digest/window_identity/output_digest 独立重建；
- stage-owned prior RPS staging；
- t-1/t-3 prior RPS lineage；
- 786-session PIT historical market reference path；
- path UNKNOWN suffix/new-series 语义；
- trend unique producer；
- stock/relative AST numeric + golden vectors；
- C01/C02/C03/C06/C07。

## 8. Sector capability

当前 `SECTOR_NATIVE = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`，这是事实，不应伪造历史 membership。

但 REV2 支持 capability scope，且 V4-04 Stock Core 不依赖 Sector Context/Rotation。因此本次接受：

```text
V4_03_SECTOR_NATIVE = DEGRADED/BLOCKED
V4_08_SECTOR_ENTRY = BLOCKED
SECTOR_DEPENDENT_STOCK_PATHS = BLOCKED_OR_SHADOW_ONLY
```

不再让 Sector 单点阻断整个 V4-03。

## 9. 增量更新能力

根据当前项目优先级：

```text
INCREMENTAL_UPDATE_CAPABILITY = DEFERRED_NON_BLOCKING
```

开发期先保证主功能正确；缺少增量更新时可重新执行全量计算。增量刷新主要影响后续运行效率、调度和缓存工程，不改变当前纯因子/Market 主链算法正确性，因此不作为 V4-03/V4-04 的前置门。

## 10. 测试与限制

仓库报告：`python -m pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py` -> 47 passed。

GitHub 当前没有 CI check / workflow run，因此严格记录：

```text
DEVELOPER_TEST_RECEIPT = PRESENT
EXTERNAL_FULL_RUNTIME_REEXECUTION = NOT_PERFORMED
```

本次不把这一点作为阻断：关键公式已直接源码复核，独立实现、receipt、SHA 和 determinism chain 相互一致，未发现剩余主功能硬错误。

## 11. Governance

当前仍没有 `V4_03_ACCEPTED_HEAD.json`，没有提前执行 V4-04/V4-05，scanner/trading/TDX writes 未越权。开发方正确停在等待外部接受的位置。

## 12. 外部接受决定

正式给出：

```text
EXTERNAL_ACCEPTANCE_PASS_WITH_CAPABILITY_SCOPE
```

接受范围：Stock Core、Relative/RPS、Market Reference、Market Regime。

降级范围：Sector Native。

未作为当前生产门评估：Incremental Update、V4-05 Full Data/Factor Replay、V4-08 Sector/Rotation、Scanner/Trading/Focus。

## 13. 下一步

V4-03 不再继续算法开发，只做 Final Seal：

1. 归档本次外部验收；
2. 生成 V4-03 final stage receipt；
3. 生成 `V4_03_ACCEPTED_HEAD.json`；
4. 更新 `V4_STAGE_ACCEPTED_HEAD.json`；
5. 固定状态 `PASS_WITH_SECTOR_SCOPE_DEGRADED`；
6. 固定 contract/source/artifact/receipt SHA；
7. 明确 Sector dependency remains blocked；
8. 授权 `V4_04_STOCK_CORE_ENTRY = AUTHORIZED`；
9. Final Seal 不再重跑/重构算法；
10. 封板后立即进入 V4-04 Full-Market Core Profile。

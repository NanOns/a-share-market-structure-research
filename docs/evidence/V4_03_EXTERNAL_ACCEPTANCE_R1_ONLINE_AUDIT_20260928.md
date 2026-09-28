# V4-03 R1 修复提交线上外部验收记录

- 验收日期：2026-09-28
- 验收对象：`codex/v4-system-reform` @ `458ff68a2260576eb5ed50ad3461a422662f3faa`
- 远端核对：线上验收模型确认 origin 分支 HEAD 与目标 SHA 一致；本仓库也已核对相同 SHA。
- 外部验收来源：ChatGPT 项目“大A”中的独立验收会话 `6aba41ef-8ed4-83ee-a2ba-bd26cd51efe5`，标题“外部验收结论”。
- 阶段合同：按 `V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_R2_20260928.md`、`V4_03_EXTERNAL_ACCEPTANCE_R1_20260928.md` 和仓库 `AGENTS.md` 核对本次 V4-03 修复。只有全部阶段条件得到证据支持并签发阶段验收后，才允许进入 V4-04；测试通过不等于发布就绪。

## 总裁决

`EXTERNAL_ACCEPTANCE_BLOCKED`。修复提交落地了若干局部合同和代码修复，并形成 47 字段诊断候选产物；但最终 V4-03 阶段验收未获批准，V4-04 继续阻断。该外部结论不替代仓库中的阶段回执，也未授权后续阶段入场。

## B01/B02、C01-C07 逐项结果

| 原审计项 | 外部状态 | 外部验收依据与保留条件 |
|---|---|---|
| B01 AST 表达能力 | FAIL | `config/v4_algorithm_contract_framework_v1_2_0.json`、`src/v4/contracts/algorithm_contract_v12.py`、`config/v4_03_algorithm_contracts_v1.json` 已提供版本化 `RULE_AST_V2` 及 47 份合同结构检查；但 validator 未执行每份合同的 `independent_vectors`，不足以证明 AST 与实现数值一致。需执行合同正反向向量并保存可复跑回执。 |
| B02 trend WEAK 歧义 | PASS | 版本化趋势修订、`src/v4/factors/native.py` 和 `tests/v4_03/test_core_vectors.py` 覆盖对称 WEAK、混合态 NEUTRAL、输入不足 UNKNOWN。市场级完整物化仍未完成。 |
| C01 停牌 T0 的 prior extrema | PASS | `src/v4/factors/core.py` 拆分排除当前 bar 与当前 bar 必需语义，测试覆盖停牌 T0 的 prior extrema、技术窗口及依赖当前值字段。阶段级复核仍受完整历史门禁约束。 |
| C02 47 字段 schema | PASS | `config/v4_03_output_schema_v1.json`、`tests/v4_03/test_algorithm_contract_v12.py` 和 `reports/v4_03/V4_03_SCOPE_FREEZE_RECEIPT_R1.json` 支持 schema 通过；生产身份散列尚未由独立验收逐字节再生。 |
| C03 47 字段正式集成 | FAIL | `scripts/run_v4_03_full_scope_candidate.py`、`reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json` 和 `scripts/independent_v4_03_full_scope_postcheck.py` 显示 5,222 行 × 47 字段候选和全字段独立值/质量复核零差异。但候选为 `DIAGNOSTIC_NON_PIT`，限 200 个市场会话，状态为 `FULL_47_FIELD_CANDIDATE_NOT_STAGE_ACCEPTANCE`。完整历史首个可用日期、预热期、PIT 重放、accepted staging 和正式阶段回执仍缺。 |
| C04 relative PIT／质量／digest 身份 | FAIL | `src/v4/factors/relative.py` 已输出会话、Universe、复权、来源、prior RPS 引用、质量及 digest；但 prior RPS 标记为 `DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`，独立复核也未逐字节重建 producer 的 `input_digest` 和 `window_identity`。需 accepted prior PIT RPS 身份及独立重算完整输入/窗口 digest。 |
| C05 market／sector native 合同闭环 | FAIL | `config/v4_03_native_contract_registry_v1.json`、`config/v4_03_native_scope_map_v1.json` 补齐合同范围；但 `reports/v4_03/V4_03_SECTOR_NATIVE_BOUNDARY_ACCEPTANCE_R1.json` 记录 `full_market_artifact=NOT_PRODUCED`，冻结输入中缺 accepted PIT sector membership；market regime 轴也没有完整逐日产物。需获得 accepted membership 并完成 market/sector 全量物化及独立复核。V4-08 的正式资格和排名须留在其自身阶段。 |
| C06 sector 字段级质量分母 | PASS | `src/v4/factors/native.py` 对 quote、amount、ret1、MA20 分别建立可评估集合；`tests/v4_03/test_core_vectors.py` 覆盖字段分母不同的情况。真实全市场 sector 产物仍受 C05 阻断。 |
| C07 market path 缺失语义 | PASS | `src/v4/factors/native.py` 与 native 合同明确同一 `series_version` 缺失后永久 UNKNOWN，新版本才重新起算；合成向量覆盖缺失和新版本；`reports/v4_03/V4_03_MARKET_PATH_INDEPENDENT_POSTCHECK_R1.json` 报告 200 行零差异。真实候选 `unknown_daily_return_count=0`，因此真实样本没有触发缺失后缀分支；完整历史路径仍需阶段验收。 |

## 独立验收范围与证据限制

外部验收回执报告 37 项相关测试通过、47 字段值与质量独立复核零差异、四类产物确定性重跑 SHA 一致。审计模型检查了独立 postcheck 的源码，认为其计算逻辑并非直接调用因子生产函数。

审计模型未在本轮环境取得项目本地输入数据，因此没有亲自重跑 5,222 行计算，也没有重新计算大型压缩产物字节哈希；GitHub commit status 与 workflow runs 均为空。以上证据只支持有界诊断范围内的结果，不支持最终阶段放行。

## 阶段验收与下一步

- 本次外部接受：未通过，状态为 `EXTERNAL_ACCEPTANCE_BLOCKED`。
- V4-03：不得签发最终 PASS；内部 receipt 仍须明确 `NOT_GRANTED`。
- V4-04：`BLOCKED`，禁止入场。
- 下阶段工作：执行 B01 独立数值向量；补齐完整历史预热和 PIT 重放；取得已接受的 prior PIT RPS 及 sector membership；完成 market/sector native 全量物化；独立重建 input/window identity digests；在全部阶段证据齐全后重新提交 V4-03 外部验收。
- 范围保护：本记录不改变 V4-01/V4-02，不启动 scanner 或交易功能，不触写任何 TDX 输入目录。

## 来源会话结论

线上审计模型给出的唯一结论：`EXTERNAL_ACCEPTANCE_BLOCKED`；V4-04 不得入场。本记录将该答复作为验收证据归档，不把它解释成用户指令，也不把诊断候选或测试通过提升为阶段验收。

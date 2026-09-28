# V4-03 外部验收 R1 问题修复与 R2 阶段处置

日期：2026-09-28。基线：`V4_DEV_BASELINE_HEAD.json`，数据截止日 2026-09-24。合同为 V4-03 Pure-Core Factors 实施任务 R2 与外部验收 R1。此文记录本次修复证据；不替代外部验收。

## 问题与证据

| 审计项 | 本次结果 | 证据与边界 |
| --- | --- | --- |
| B01：47 份 AST 合同仅校验结构 | 已修复实现，待外部验收 | `config/v4_03_algorithm_contracts_v1.json` 版本提升至 1.1.0；`config/v4_03_ast_numeric_fixture_v1.json` 固定独立数值夹具；`src/v4/contracts/algorithm_contract_numeric_v12.py` 独立执行 AST。`V4_03_AST_NUMERIC_VECTOR_ACCEPTANCE_R2.json`：47 合同、94 向量，含正常和 UNKNOWN_INPUT，全部通过。负例测试可检出篡改期望值与缺失负例。 |
| C03：200 日截断 | 截止日候选已扩展，最终要求未完成 | `V4_03_CORE_FULL_HISTORY_CANDIDATE_RECEIPT_R2.json`：读取冻结上游全部 786 个交易日，自 2023-07-04 起，截止日 5222 行。`V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R2.json`：5222 行、47 字段。尚未逐历史 T 重放首次可用日；证据仍为 `DIAGNOSTIC_NON_PIT`。 |
| C04：身份摘要缺独立复算 | 截止日候选摘要已复算，前序 RPS 来源仍待接受 | `V4_03_INDEPENDENT_POSTCHECK_R2.json`：5222 行、47 字段数值、质量、`input_digest`、`window_identity` 独立重算；来源及市场引用身份不匹配数均为 0。前序 RPS 仍由冻结历史快照现场计算，没有前一 PIT 已接受产物，不能宣称通过完整 PIT 链。 |
| C05：板块历史来源和原生产物 | 阻塞 | 冻结 V4-01/V4-02 接受清单没有可接受的历史板块成员组件；本次不将 legacy 或推断成员伪装为已接受输入。板块全市场产物和完整市场轴未签收。 |

独立复核读取冻结 V4-01/V4-02 数据和参数注册表，不导入因子生产器；其 PASS 仅指候选逐字段比对通过，不是阶段签收。`pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py`：38 passed。

## 阶段合同与结论

阶段范围：四板 Required Scope 的 39 个 Core 字段、8 个 Relative 字段、可解释的版本化合同、真实数据候选与独立复核。当前验收结果为 **EXTERNAL_ACCEPTANCE_BLOCKED / CONTINUE_UNAFFECTED_WORK**。B01 实现问题已修；C03 历史每日首次可用性、C04 已接受前序 RPS 链、C05 已接受板块成员来源和板块原生产物仍未满足最终阶段合同。不可发布 V4-03 最终 PASS，V4-04 不放行。下一阶段先取得并单独验收板块历史来源，完成逐 T 的 PIT 轨迹与前序 RPS 接受链，再重跑全市场产物及外部验收。

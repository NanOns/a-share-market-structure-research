# M8C-03 能力降级门合同 v1.1

`REFERENCE_CAPABILITY_GATE_V1_1` 按证券和交易日独立评估参考价、规则、涨跌停和换手率能力。能力必须由实际逐行证据决定；静态规则存在、页面顶部的 `PARTIAL` 或有一条结果行，都不能把缺失依赖标为 `BOUND`。

- 参考价精确能力需要 `quote_capability=EXACT`、`reference_status=KNOWN`、来源和除权状态完整；
- 涨跌停精确能力还需要有效规则行、`rule_verified=true`、日期匹配、rule_id 匹配以及已知上市阶段；
- 缺少流通股本只影响换手率，不得连带否定已经独立证明的涨跌停能力；
- `APPROXIMATE` 与 `UNKNOWN` 不进入精确涨跌停/连板分母；
- 每个原因码和样本分母必须可追溯到同一个 snapshot/slice。

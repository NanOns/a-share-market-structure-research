# V3 P05-02：五类独立股票信号

## 结论

依据最新 V3 主实施文档 §6.1、§18.8、§20 C20-02，P05-02 验收结果：**FULL_PASS**。

## 阶段合同

- 合同 ID：`STOCK_ATTENTION_PREVIEW_1`。
- 入口：`workbench_analysis.stock_attention.classify_stock_attention()`；批量入口 `classify_stock_frame()`。
- 只消费 P05-01 基础特征，不访问板块、旧 candidate pool、最终 shortlist、数据库或网络。
- 输出 BREAKOUT、SETUP、RECOVERY、TREND_BACKGROUND、STRUCTURE_BREAK、EXTENDED、逐谓词 checks、reason codes 和 unknown signals。
- 三值逻辑：任一必要条件已知 false 则信号 false；没有 false 但存在缺失则 UNKNOWN；全部为 true 才命中。
- TREND_BACKGROUND 只是事实背景，不独立产生 `focus_trigger`；重点触发仅由 BREAKOUT/RECOVERY 且非 STRUCTURE_BREAK 产生。

## C20-02 谓词映射

源码 `PREDICATE_CONTRACT` 逐项登记规格谓词到 v3.1 配置键或 `FIXED_*` 严格语义。SETUP 和 RECOVERY 均显式执行 liquidity 与 position 完整性相关字段；没有因旧配置缺键而绕过流动性门。

关键边界：BREAKOUT 的新高使用严格 `dist_high20 > 0`；金额阈值为 `>=1.20`；SETUP 的区间端点包含；RECOVERY 的当前价上穿 MA5 与 RPS 改善使用严格大于；STRUCTURE_BREAK 要求当前和上一有效主交易日连续低于 `.98*MA20`。

## 验收证据

合成测试覆盖：微跌 SETUP；资金不足使 SETUP/RECOVERY 为 false；资金未知返回 UNKNOWN；BREAKOUT 金额阈值本身、阈值下最小差、NULL；新高不自动 EXTENDED；EXTENDED 排除研究触发但不抹掉趋势背景；单日/连续两日结构破坏；趋势背景不独立进入重点。

真实 normalized 最近 110 个交易日只读运行（6,178 只证券）：

| 信号 | true | unknown | 正例（仅工程核对） |
|---|---:|---:|---|
| BREAKOUT | 188 | 663 | BJ.920010、BJ.920060、SH.600072 |
| SETUP | 643 | 650 | BJ.920810、BJ.920857、SH.600007 |
| RECOVERY | 33 | 632 | SH.600061、SH.600155、SH.600621 |
| TREND_BACKGROUND | 1,458 | 664 | BJ.920006、BJ.920008、BJ.920010 |
| STRUCTURE_BREAK | 1,514 | 661 | BJ.920002、BJ.920003、BJ.920007 |

另有 EXTENDED 18、独立 focus trigger 210。该分布只证明代码在真实输入上可运行且具有正/反/缺失样例，不代表效果、概率或未来收益。

全回归：`pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 `189 passed in 49.88s`；compileall 与 diff check 通过。未写生产数据库，未修改 TDX。

## 下一阶段

进入 P05-03：冻结信号解释、生成真实分布报告和正/反/缺失解释，不隐藏调整阈值。

# V3 P05-03：信号固定解释与初始分布

## 结论

依据最新 V3 主实施文档 §6.1、§18.8、§20 C20-02，P05-03 验收结果：**FULL_PASS**。本阶段冻结既有配置和谓词合同，生成解释性分布；不以命中数量为目标调整任何阈值，也不作效果、概率或未来收益声明。

## 阶段合同与输入身份

- 阶段合同：`v3-p05-03-signal-distribution-v1.0`；特征合同：`RESEARCH_FEATURES_PREVIEW_1`；信号合同：`STOCK_ATTENTION_PREVIEW_1`。
- 配置：`research-attention-config-v3.1`；记录与重算的参数哈希均为 `61d191402bafbc4f2c9bd13bf88361650bed574daa5d455bf15219ad5aa7173f`。
- 真实只读输入：`data/normalized/adjusted_daily.parquet`，SHA-256 `2e4d5e343205ab79021d32b2d0a29013b39960fb6370ca5f0f446e2a719e83c6`；最近 110 个主交易日、679,580 行，最终交易日 `2026-09-10`，6,178 只证券。
- 产物：[P05-03_SIGNAL_DISTRIBUTION.json](../reports/upgrade_v3/P05-03_SIGNAL_DISTRIBUTION.json)。该 JSON 为每种信号分别保存三条 true、false、unknown 样例及逐谓词 checks；它是本阶段的可复核解释证据。

## 初始分布

| 信号 | true | false | unknown | 主要拒绝条件 | 主要缺失条件 |
|---|---:|---:|---:|---|---|
| BREAKOUT | 188 | 5,327 | 663 | `NEW_HIGH20` 5,241；`AMOUNT_EXPANSION` 4,624 | `ABOVE_MA20`/`AMOUNT_EXPANSION`/`NEW_HIGH20`/`NOT_EXTENDED` 各 663 |
| SETUP | 643 | 4,885 | 650 | `NEAR_HIGH20` 3,068；`RPS5_DELTA3` 3,055 | `RPS5_DELTA3` 663；`CLOSE_TO_MA20`/`NEAR_HIGH20` 661 |
| RECOVERY | 33 | 5,513 | 632 | `AMOUNT_EXPANSION` 4,336；`CURRENT_ABOVE_MA5` 4,068 | `RPS5_DELTA3` 663；`AMOUNT_EXPANSION` 661 |
| TREND_BACKGROUND | 1,458 | 4,056 | 664 | `RPS20` 3,860；`ABOVE_MA20` 3,072 | `MA20_RISING_5` 664；`ABOVE_MA20`/`RPS20` 663 |
| STRUCTURE_BREAK | 1,514 | 4,003 | 661 | `PREVIOUS_BELOW_MA20` 3,934；`CURRENT_BELOW_MA20` 3,385 | 两项各 661 |

流动性质量交叉核对为 true 5,186、false 331、unknown 661；EXTENDED 为 true 18、unknown 663。由此确认流动性和风险字段的缺失不会静默转为通过，而是进入 UNKNOWN 或明确的拒绝条件。

## 固定解释样例

JSON 产物中每种信号均有可复核的 true、false、unknown 三组样例，均带完整 checks。正例分别包括：BREAKOUT `BJ.920010`、SETUP `BJ.920810`、RECOVERY `SH.600061`、TREND_BACKGROUND `BJ.920006`、STRUCTURE_BREAK `BJ.920002`。反例通过首要 false 谓词解释；例如 BREAKOUT 的 `BJ.899050` 同时不满足 `ABOVE_MA20`、`AMOUNT_EXPANSION`、`NEW_HIGH20`。缺失例通过 null checks 解释；例如 TREND_BACKGROUND 的 `BJ.430017` 的三个必要谓词均为 null。其余四类信号的反例和缺失例同样逐条保留在 JSON 中。

## 验收与边界

`signal_distribution()` 的定向测试验证 true/false/unknown 计数、拒绝代码、缺失代码和样例抽取；真实输入脚本返回 `PASS`。脚本只读 normalized parquet，仅原子写入上述报告；`database_written=false`、`tdx_modified=false`、`thresholds_changed_during_distribution=false`、`effectiveness_claim=false`。未启动 scanner、未写生产数据库、未访问或修改 TDX。

## 下一阶段

G05 关闭，进入 P06-01；后续板块聚合仍必须只消费具有版本合同的本阶段股票信号和证据。

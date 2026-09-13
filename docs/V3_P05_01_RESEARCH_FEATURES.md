# V3 P05-01：统一基础特征输入

## 结论

依据最新 V3 主实施文档 §4、§6.1、§18.8 和 C20-02/04/09，P05-01 验收结果：**FULL_PASS**。

本阶段只完成独立股票基础特征和输入身份合同，不提前实现 P05-02 的 BREAKOUT、SETUP、RECOVERY、TREND_BACKGROUND、STRUCTURE_BREAK 判定。

## 阶段合同

- 合同 ID：`RESEARCH_FEATURES_PREVIEW_1`。
- 入口：`workbench_analysis.research_features.build_stock_research_features()`。
- 纯计算：不读数据库、不读网络、不写文件；调用方必须绑定 run、publication、snapshot、relation revision、calendar 和 cutoff。
- 主交易日历决定窗口位置；缺少某个主交易日的股票行时保留缺口，不按“最近若干条记录”压缩窗口。
- 价格位置特征只使用 `TDX_NATIVE_QFQ` 的 `adj_close`；原始价格除权跳变不替代复权价格。
- `ret5`、`rps5`、`rps20`、`rps5_delta3` 字段独立，不以 RET 回填 RS/RPS。
- `amount_vs_prior20` 与 `liquidity20` 均使用排除当日的前 20 个主交易日；正式流动性阈值保持 2,000 万元。
- turnover 只接受来源值和非空 `turnover_basis`；不从成交额/市值猜算。
- high100 输入完整性单独输出，需要当前日加前 100 个主交易日全部有效，不受 85 日预热预算截断。

## 配置裁决

C20-02 已在配置版本 `research-attention-config-v3.1` 关闭：SETUP 与 RECOVERY 均显式声明 `requires_liquidity=true` 和 `requires_position_fields=true`。新参数哈希为：

`61d191402bafbc4f2c9bd13bf88361650bed574daa5d455bf15219ad5aa7173f`

旧 v3.0 哈希只作为历史基线保留，不再代表 P05 后的当前参数合同。

## 验收证据

合成/手算测试覆盖：

- bias20、sigma20、dist_high20、range5/20、amount_vs_prior20 和 rps5_delta3 手算对照；
- NULL、停牌、零波动；
- 主日历中间缺日不压缩窗口；
- 未来行被 cutoff 排除；
- 原始价除权跳变时仍按复权价计算；
- price basis 不一致、turnover 无 basis、重复业务键和空 context fail-closed；
- RS5/RPS5 与 RET5 不混用；high100 要求 101 个有效收盘。

真实输入只读核验：`data/normalized/adjusted_daily.parquet` 最近 110 个主交易日，共 679,580 行；输出 6,178 只证券，其中 READY 5,213、PARTIAL 965、high100 完整 5,213、liquidity20 通过 5,186、amount ratio 有效 5,515。该核验未写生产库或产物表。

全回归：`pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 `183 passed in 44.28s`；compileall 与 diff check 通过。

## 边界和下一阶段

- P05-01 输出是基础事实和质量状态，不表达上涨概率，也不生成研究资格。
- 板块聚合 m1/b1/rel1/q5/q20 等属于 P06；股票信号判定属于 P05-02。
- 下一任务：`P05-02`，实现五种基础信号及 C20-02 的逐谓词验证。

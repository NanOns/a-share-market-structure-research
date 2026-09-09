# M8A 技术历史合同 v1

## 1. 范围

本合同实现 `TECHNICAL_HISTORY_V2_1_PREVIEW` 的 M8A-01：使用已封存的
`TDX_NATIVE_QFQ` 输入，按主交易日历计算个股技术日因子。M8A-02 已通过独立
strength 分片提供新高/RPS；M8C 参考价/股本能力仍保持独立，不改变 M6/V1 已封存字段。

## 2. 因子口径

- `ma5/10/20/60`：当前及此前观察的 `adj_close` 均值；窗口有缺失时为 `NULL`。
- `ret5/10/20/60`：当前 `adj_close / n 个交易日前 adj_close - 1`，要求完整的
  `n+1` 个观察，窗口中有缺失时为 `NULL`。
- `amount_ma5/10/20`：原始 `raw_amount`，包含当日；`amount_ratio20` 保留旧合同，
  为当日成交额除以包含当日的 20 日均额。
- `amount_vs_prior20` 与 `volume_vs_prior20`：当日值除以前 20 个交易日均值，
  明确排除当日；分母非正或不足 20 个观察时为 `NULL`。
- `amount_class`：`[0,1.5)` NORMAL、`[1.5,2)` INCREASED、`[2,3)` NOTABLE、
  `[3,+∞)` SIGNIFICANT；未知值不归类。
- `ma_alignment`：严格 `MA5>MA10>MA20>MA60` 为 `BULLISH`，严格反向为
  `BEARISH`，其余完整值为 `MIXED`，缺值为 `NULL`。

所有输入先按证券和日期稳定排序；不会通过跳过缺失行延长窗口，也不会接受
截止日之后的输入。每行保存合同版本、价格基准、质量代码和口径 JSON。

## 3. 存储与接口

迁移 `008_technical_history` 建立不可变 `stock_technical_daily`，主键为
`(slice_id, security_id, trade_date)`。同一 `slice_id` 再次写入时只允许键集合和
全部持久化内容完全相同，不允许静默覆盖。

API10 为 `GET /api/stocks/technical`，只读取所选发布成功绑定的分析快照及其
`technical` entries。未绑定快照返回 `409 ANALYSIS_NOT_BUILT`；RPS 查询读取同一
快照的 strength entries，缺失时返回 `RPS_NOT_BUILT`，不以空值冒充已完成能力。

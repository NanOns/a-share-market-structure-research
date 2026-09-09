# M8A-03 历史图表合同 v1

API12 的历史图表按选定发布解析一个成功绑定的分析快照，并从该发布已封存且
内容校验通过的本地输入读取单股数据。图表变换不扫描全市场，也不接受客户端
路径。

- `RAW` 使用 `raw_open/high/low/close`，返回 `chart_basis=RAW_UNADJUSTED`。
- `ADJUSTED`/`TDX_NATIVE_QFQ` 使用同一份封存输入中的 `adj_open/high/low/close`，
  并固定 `adjustment_as_of=cutoff_date`；返回值中的 OHLC 与 MA 不混用价格基准。
- MA5/10/20/60 在完整的主交易日历行上计算。证券无行或价格无效时返回明确的
  gap 点，不能将前后日期压缩，也不能用旧值填充。
- 返回 `chart_basis` 与 `factor_evidence_basis`；图表锚与技术因子证据用途分开。
- 缓存键固定包含 `snapshot_id`、证券、价格口径、调整锚、days、fields 和合同版本，
  使用有条目数和近似字节上限的 LRU；不无限增长。

RPS 为可选字段；对应快照没有 strength 分片时返回 NULL，并以能力状态说明，
不伪造已完成的 RPS。正式发布头和旧图表路径不因 API12 自动切换。

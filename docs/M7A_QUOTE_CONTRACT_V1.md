# M7A 报价绑定合同 v1

合同 ID：`workbench-quote-v2.1`
适用步骤：`M7A / 7A-03`
状态：preview；不重写已封存发布，不触发正式入口切换。

## 字段口径

报价服务从封存的 `data/normalized/adjusted_daily.parquet` 读取同一发布日期的原始行情。`latest_price` 与 `raw_close` 均为原始收盘价；`adj_close` 只属于因子/技术计算口径，不得用于首页当日涨幅。

每条报价返回 `raw_open`、`raw_high`、`raw_low`、`raw_close`、`raw_amount`、`quote_prev_close`、`quote_ret1`、`quote_ret1_basis`、`quote_state`、`quote_date`、`source_ref`、`source_identity_sha256` 和 `publication_id`。旧客户端继续得到 `latest_price`、`turnover_amount` 与 `RET1`，三者分别兼容映射到原始价、原始成交额和 `quote_ret1`。

## 前收和涨幅优先级

1. 当日行情存在受信任的 `reference_prev_close`（或等价已绑定字段）时，使用它，`quote_ret1_basis=REFERENCE_PREV_CLOSE`，状态为 `VALID`。
2. 没有参考前收时，仅当当前日和前一市场交易日都有真实、可交易、非合成的原始 K 线，且复权因子未发生变化，才使用原始收盘比，标记 `RAW_CLOSE_PREVIOUS_TRADING_DAY` 和 `VALID_DEGRADED`。
3. 复权因子变化时返回 `UNKNOWN_CORPORATE_ACTION`，不生成涨幅；复权因子字段缺失或两日无法比较时，`quote_ret1_basis=ADJUSTMENT_METADATA_UNAVAILABLE`、状态仍为 `UNKNOWN_CORPORATE_ACTION`，同样不生成涨幅；没有真实前收时返回 `MISSING_PREVIOUS_CLOSE`，不以最后已知价冒充当日涨幅。

上一市场交易日由数据中的实际市场日期序列确定，不由“上一条发布头”推断；停牌证券缺少当日真实 K 线时不生成有效当日涨幅。

## 来源绑定与不变量

- `source_ref` 精确到源文件、证券和日期；`source_identity_sha256` 绑定所选发布的输入身份。
- API 只读取与所选 publication、日期、source identity 和文件 SHA-256 全部匹配的 SourceManifest。缺少绑定或文件哈希变化时返回报价不可用，不回退到当前全局文件。
- 所有报价均绑定 `publication_id` 和 `quote_date`，当前文件变化不能静默重写旧发布的报价解释。
- `quote_ret1` 只描述历史价格变化，不代表未来涨跌或交易建议。
- 未验证的参考前收、除权状态或交易状态不得伪装成精确涨幅；旧 `RET1` 也必须保留相同的安全状态。

# M13A 市场周期合同 v1

合同 ID：`M13_MARKET_CYCLE_V1`  
适用阶段：M13A-01、M13A-02、M13A-03  
依据文档：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 13 节、22.8 节。

## API32：市场历史聚合

`GET /api/market/cycle?publication_id=...&days=60&metrics=breadth,amount,ma,new_high,queues`

- 默认窗口 60 日，允许 1–250 日；只读取当前发布版本绑定的本地分析快照。
- 每个 `MarketPoint` 按 A 股股票去重，`up_count + down_count + flat_count == quote_valid_count`。
- 成交额、MA20、MA60、新高、队列分别保留自己的有效分母；缺失值不计入有效分母，不转成 0。
- `new_high_counts` 的 `valid_count/hit_count` 按窗口分开；队列保留各队列计数和去重后的 `queue_unique_count`。
- 涨跌停状态及板块状态在输入未构建时显式返回 `null`，能力标记为 `NOT_BUILT`，不伪造市场情绪。
- 返回 `snapshot_id`、`history_basis`、`as_of_trade_date`、窗口和日期元数据。
- 市场聚合使用独立的 `statistical_scope`：默认包含科创板；不得复用个股页面的 `display_scope`。返回的 `display_count`/成交额/广度分母均按该统计范围计算。

## API33：单日明细

`GET /api/market/day-detail?publication_id=...&trade_date=...`

返回单个聚合点和固定快照下的技术、新高、队列下钻参数；不内嵌股票全集，不改变排序或分析结果。

单日明细同样返回 `statistical_scope`。明细下钻到个股技术、队列或新高页面时，才应用个股展示范围；下钻页面不改变已生成的市场聚合值。

## UI 约束

市场周期页支持 30/60/90/120/250 日窗口，首屏只渲染聚合点；点击日期读取单日明细。页面明确显示快照、历史基础、字段能力和分母，不使用概率或自动交易表达。

## 独立综合审计规则

若发现某项实现与升级方案均不是当前最佳方案，需单独登记综合审计项，写明范围、证据、影响与独立验收；此规则适用于所有阶段，不限定为金额 A，也不得并入阶段通过结论。

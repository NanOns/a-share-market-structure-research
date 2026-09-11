# M11 属性库查询合同 v1.0

合同 ID：`M11_ATTRIBUTE_LIBRARY_V1_0`

本阶段只交付只读属性查询，不执行集合交集、强势关联预计算或 UI 联动。

## 数据边界

- API23 和 API27 必须读取同一个发布绑定的分析 snapshot；不能把当前发布的 `membership_entries` 与历史分析 slice 混用。
- 板块属性来自该 snapshot 的 `sector_base` slice，股票归属来自同一 snapshot 的 `member_state` slice。
- 每个响应包含 snapshot、slice、输入哈希、逻辑哈希、语义合同、成员快照和历史 basis，便于追溯。
- 缺少分析 snapshot 或任一输入 slice 时返回 `ATTRIBUTE_LIBRARY_NOT_BUILT`，不得用旧版 `/api/sectors` 临时替代。

## 语义隔离

语义桶固定为：`NORMAL_ATTRIBUTE`、`PRICE_BEHAVIOR_TAG`、`EVENT_TAG`、`STATUS_TAG`、`UNKNOWN_TAG`。价格行为、事件和状态标签可以被查询和展示，但 `is_attribute=false`，不会被冒充为正常行业/概念/风格属性，也不会进入 M11-02 的集合执行器。

关键词只产生人工复核提示；最终桶由精确 ID 覆盖、显式字段或保守默认规则确定。当前阶段不写入语义覆盖。

## API23：属性库

`GET /api/sector-library?publication_id=P&page=1&page_size=50&q=&type=&bucket=`

返回 `items`、分页信息、`as_of_trade_date`、`snapshot_id`、`contract_id`、`bucket_counts` 和 `source`。每个 item 至少含板块 ID/名称/类型、语义桶及隔离标记、总成员数、有效成员数、覆盖率、语义规则 ID/原因和来源追溯块。默认按名称、ID排序。

## API27：个股归属

`GET /api/stocks/{security_id}/memberships?publication_id=P&page=1&page_size=50&bucket=`

返回该股在同一 snapshot 截止日的板块归属，`items` 以语义桶分组所需字段排序，另返回 `groups`、分页信息和 `source`。标签归属原样保留，但响应不得生成或填充强势关联结论；强势关联属于后续阶段。

# M14-06 低优先龙虎榜合同 V1

- 阶段：`M14-06-LH-LIST`
- 合同 ID：`M14_LH_LIST_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14.1、14.2、14.3、22.9 节
- 当前能力状态：`UNAVAILABLE`

## 1. 能力边界

龙虎榜是独立的 `LH_LIST` 能力，不从热榜、原因证据、报价或本地快照推导。它只作为低优先证据展示，不参与主线、队列、候选排序或概率判断。

准入后的最小记录必须包含 `evidence_id`、`source_id`、`security_id`、`source_code`、`trade_date`、`published_at`、`first_seen_at`、`raw_ref`、`source_url`、`seat_name`、`buy_amount`、`sell_amount` 和 `amount_unit`；来源映射和金额单位必须独立记录。金额未知保持 NULL，不用 0 代替。

## 2. 日期与历史合同

- `trade_date` 是榜单发生交易日，不得用抓取日替代；
- `published_at` 是来源发布时间，`first_seen_at` 是本地首次获得时间，二者不得混用；
- 严格历史视图要求 `trade_date` 不晚于请求截止日，且 `published_at`、`first_seen_at` 不晚于 `as_of`；
- 缺少交易日、发布时间、来源映射或正文引用时，条目不得进入严格历史视图；
- 事后补充必须独立标记，不得回填成当日已知事实。

## 3. 当前空态与隔离

当前没有成熟且已验证的免费来源，因此返回 `UNAVAILABLE`、`NO_VERIFIED_LH_SOURCE` 和空 `items`。不得启用 API38 的 `LH_LIST` evidence_type，不得新增网络采集或生产批次。

`personal_research_only=true`、`publication_enabled=false` 是硬约束；不得写入 TDX 或改变 `analysis_snapshot`。

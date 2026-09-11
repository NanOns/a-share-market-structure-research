# M14-05 可选盘中报价合同 V1

- 阶段：`M14-05-QUOTES`
- 合同 ID：`M14_QUOTES_LATEST_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14.1、14.2、14.3 节及第 22.9 节
- 当前能力状态：`NOT_VERIFIED`
- 热榜页面状态：允许 `DISPLAY_ENRICHMENT_ONLY` 请求级补充；不等同于本合同正式准入，不启用 API39。

## 1. 独立能力

报价必须来自独立报价端点和独立报价批次。热榜载荷不得被解释为价格、涨幅、成交额、成交量或报价时间；本阶段不从 `HOT_RANKINGS` 补报价。

报价视图必须返回 `batch_id`、`source_as_of`、`quote_time`、`source_code`、`security_id`、`price`、`ret1`、`amount`、`volume`、`quote_state` 及明确的 `price_unit`、`amount_unit`、`volume_unit`。`source_as_of` 缺失时不得伪造为观察时间。

## 2. 时间、单位和映射

- 只有 `quote_time` 不晚于请求 `as_of` 的条目才可进入严格历史视图；未来或缺失时间拒绝；
- 价格、金额、成交量的单位必须由来源证据明确记录，未知单位不入严格视图；
- 代码映射必须使用独立、可追溯的来源映射合同，未知代码保留 NULL，不按前缀猜测；
- `quote_state` 显式区分 `VALID`、`MISSING`、`SUSPENDED`、`UNKNOWN`，未知不填 0；
- 在线报价与本地封存报价分开，不改变本地快照或已有技术指标。

## 3. 当前空态和验收

当前没有完成报价来源准入，因此正式报价视图返回 `NOT_VERIFIED`、`NO_VERIFIED_QUOTE_SOURCE`、空 `items`，不启用 API39。热榜页面可以请求一个仅存在于当前请求内的报价补充对象；该对象只能标记 `time_semantics=OBSERVED_AT_ONLY`，不得进入严格历史视图，也不得被当成正式报价批次。失败不阻塞本地主流程。正式准入必须独立完成条款、报价时间、单位、代码映射、缓存预算和 10 个交易日观察。

`personal_research_only=true`、`publication_enabled=false` 是硬约束；不得写入 TDX、生产在线表或 `analysis_snapshot`。

# M14 热榜 API 集成合同 V2

- 阶段：`M14-HOT-RANK-DIRECT-01`
- 合同 ID：`M14_HOT_RANK_API_V2_0`
- 路由：`GET /api/hot-rankings`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` API37、14-03 和 22.9

## 请求

- `source`：`EASTMONEY_HOT_RANK`、`TONGHUASHUN_HOT_RANK`，默认东方财富；
- `list_type`：可选，默认使用来源批次列表类型；
- `mode`：固定为 `LATEST`，表示本次请求从来源获取的当前榜单；不支持历史回看；
- `page`、`page_size`：视图行分页，`page_size≤100`；
- `co_listed=1`：返回来源独立的 `source_views`，不把不同平台的名次合并成一个排名。

请求不触发热榜快照落盘。分页在一次请求内固定内存结果；下一次刷新重新请求来源。

## 响应

响应必须返回 `storage_scope=EPHEMERAL_ONLINE`、`source_id`、`source_as_of`、`observed_at_utc`、`time_semantics=LATEST_REQUEST`、`page`、`page_size`、`total` 和 `items`。每行保留 `source_code`、`security_id`、`security_name`、`platform_rank`、`source_rank_change`、`source_row_order` 和本地补充字段；映射失败行必须带 `mapping_status=UNMAPPED`，不能静默改名。

热榜页可挂载独立报价补充对象 `quote`，其 `source_id`、单位、`quote_state` 和时间语义必须单独返回；热榜排名不能被解释为报价。当前报价能力仅允许 `DISPLAY_ENRICHMENT_ONLY` 请求级补充，不代表 `M14_QUOTES_LATEST_V1_0` 正式准入，也不启用 API39。报价端点没有可靠来源时间时，只能标记 `time_semantics=OBSERVED_AT_ONLY`，不能进入严格历史视图。原因区只返回 `reason_status`；没有独立原因来源时返回 `UNAVAILABLE_NO_VERIFIED_REASON_SOURCE`，不能把热榜标签或题材当成涨停原因。

`platform_rank` 始终是来源原始排名；`source_rank_change`仅表示来源返回的原始变化字段，不转译为本系统跨时点排名变化。两个来源必须分别展示，不能按本地字段合并或重排。

## 集成边界

热榜属于本地项目在线展示能力，公开来源响应只作为当前页面输入，不进入本地快照、正式DB或离线回放资产。数据仍需经过版本化解码、字段校验、时间校验和精确代码映射；名称与基础字段从本地证券主数据补齐。失败返回明确错误，不阻塞本地主流程，不修改 `analysis_snapshot`。本合同不把原因、报价或龙虎榜状态推导为可用。

## 本阶段不做

- 不保存 `online_payloads`、`online_batches`、`online_rank_entries` 的热榜记录；
- 不提供 `AS_OF`、`batch_id`、历史热榜、跨刷新排名变化或跨平台合并排名；
- 不以热榜结果修改本地证券主数据或任何分析快照；
- 当前仓库 `AGENTS.md` 仍有网络数据禁令，真正启用直取前必须先由项目所有者同步解除/修改该规则；本合同修改本身不绕过该前置条件。

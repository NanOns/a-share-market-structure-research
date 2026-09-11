# M14-03 热榜视图合同 V1（历史批次方案，已被直取方案取代）

> 本文件只用于解释此前已生成的隔离测试产物，不再作为热榜执行依据。当前执行依据为 `docs/M14_HOT_RANK_API_CONTRACT_V1.md` 中的 `M14_HOT_RANK_API_V2_0`：请求时直取、内存拼接、本地补名称、展示后释放，不保存热榜快照。

- 阶段：`M14-03-HOT-RANK`
- 合同 ID：`M14_HOT_RANK_VIEW_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14.2、14.3 节及第 22.9 节
- 输入：`M14_BATCH_FOUNDATION_V1_0` 产生的个人研究隔离热榜批次

## 1. 能力边界

热榜按 `source_id + list_type + page` 独立生成视图，不把东方财富、同花顺的名次合并成一个伪平台排名。视图只读批次文件，不写 `analysis_snapshot`、发布头、因子、scanner、API/UI 消费表或生产对象。

每一行同时保留：`source_code`、`security_id`、`platform_rank`、`security_name`、`source_rank_change`、`source_row_order`。`platform_rank` 按来源原值返回，视图不得因为代码映射、过滤或缺名而重排。

## 2. 时间和比较合同

- 返回当前 `batch_id`、`source_as_of`、`observed_at_utc` 和 `time_semantics`；观察时间不得伪装成来源时间；
- 当前批次缺 `source_as_of` 时仍可展示最新隔离热榜，但 `comparison_status=UNAVAILABLE_SOURCE_AS_OF_MISSING`，不得生成严格排名变化；
- 上一批次必须来自同一 `source_id + list_type + page`，且两批都有 `source_as_of`；
- 首版比较窗口为 15 分钟（含边界）。超窗返回 `UNAVAILABLE_COMPARISON_WINDOW_EXCEEDED`；
- 可比较时返回 `comparison_batch_id`、`rank_change_basis=PREVIOUS_CAPTURE`、`previous_rank` 和 `rank_delta=previous_rank-platform_rank`；
- 来源字段 `source_rank_change` 原样保留，但绝不作为 `rank_delta` 或比较批次的替代品；
- 没有可比批次时，`previous_rank`、`rank_delta`、`comparison_batch_id` 必须为 NULL。

## 3. 失败与隔离

输入批次缺少身份、时间、列表字段或出现重复代码时，视图构建失败并输出明确错误，不产生半成品。个人研究对象继续带 `personal_research_only=true`，`publication_enabled=false`。

本阶段验收只证明批次视图合同成立，不代表来源获得生产许可，也不启用 API37 或在线 UI。东方财富、同花顺许可边界和同花顺 `source_as_of` 缺失继续作为独立开放项。

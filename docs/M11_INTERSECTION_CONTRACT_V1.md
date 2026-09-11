# M11 集合执行器合同 v1.0

合同 ID：`M11_SECTOR_INTERSECTION_V1_0`

本阶段只提供只读集合查询。请求通过 POST 承载结构化条件，但不保存查询状态、不修改发布或分析数据。

## 集合规则

- `include_sector_ids` 去重后必须为 2–4 个 ID；重复选择不改变结果。
- `operator=INTERSECTION` 要求个股同时属于全部 include 板块；`UNION` 要求属于任一 include 板块。
- `exclude_sector_ids` 去重后最多 20 个；排除优先于后续技术/结构筛选。
- 结果恒为 `(include 集合运算结果 - exclude 集合) -> 同 snapshot 条件筛选 -> 排序 -> 分页`。
- `total` 和 `candidate_total_before_filters` 均在分页前计算；空集合结果为 0，不把缺失值当成 0 或 False。
- 默认只保留 `CN_A_CORE_V1` 可展示的 A 股标识；B 股、BJ、新三板及退市标识不进入结果。

## 条件规则

`filters` 内字段按 AND 组合，`queues_any` 内按 OR 组合。`queues_any=[]` 表示不施加队列条件；`bands=[]` 表示显式无研究带，结果为空。未知或 NULL 的队列、研究带、技术值、新高状态都不能通过对应筛选。

支持 `queues_any`、`bands`、`new_high_window`、`ma_alignment`、`amount_vs_prior20_min` 和 `rps20_min`。排序必须使用显式白名单，不存储综合分数。

## 接口

`POST /api/sector-intersection/query`

请求必须包含 `publication_id` 和 2–4 个 `include_sector_ids`。`basis` 支持 `AUTO`、`OBSERVED`、`RECONSTRUCTED`；`trade_date` 缺省取绑定 snapshot 的最新成员状态日，指定日期不在 snapshot 时返回 `TRADE_DATE_UNAVAILABLE`。

响应返回 `items`（含 `matched_sector_ids`）、集合运算参数、过滤条件、分页前计数、绑定 snapshot/slice/输入哈希/逻辑哈希和数据 basis。所有分析表必须来自同一 snapshot；不存在完整输入时不得回退旧版接口。

# M15-01 首页编排合同 V1

- 阶段：`M15-01`
- 合同 ID：`M15_OVERVIEW_V1_0`
- 优先研究合同：`M15_PRIORITY_RESEARCH_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 15、20.2、22.10、23.2 节

## 范围

首页在 API01/API02 确认当前发布版本后，请求 API30 与 API31。API30 的分析内容必须绑定当前发布选择的分析快照；API31 保留候选池既有研究顺序，仅补充 StockRow 可见字段。首页不计算新评分，不把板块排名临时替代主线分类。

API30 返回 `item`：

- `market_summary.cards` 固定六张市场摘要卡；旧 `market_daily` 不可用时，可读取同快照的 `market_cycle` 分片，并标注 `source`；
- `strong_sectors.INDUSTRY` 与 `strong_sectors.THEME` 固定分组，每组最多六个，按快照 `rank` 升序；不混入 STYLE 或未知板块类型；
- `mainline_counts` 按 M10 当前日期分类计数；快照不存在时为 `UNAVAILABLE`，不得用板块排名填充；
- `representatives` 按 `security_id` 去重，保留 `sector_sources` 全部来源；确认代表优先于候选代表；
- `priority_research.endpoint` 明确指向 API31，优先研究列表不嵌入 API30。

每个分析分组允许独立降级。响应必须回显 `publication_id`、`snapshot_id`、`resolved_basis`、`trade_date`、`returned_range` 和本合同 ID。请求日期不得晚于发布截止日。

## UI 验收

首页显示市场卡、行业/概念强势板块、主线状态、去重代表股和 API31 优先研究分页。卡片/行操作必须保留当前 `publication_id` 与日期上下文：市场卡进入市场周期，技术卡进入个股技术，板块行进入对应板块筛选，主线计数进入对应分类，股票行进入统一个股透视。外部或数据库文字只通过 `textContent` 渲染。

本合同仅覆盖首页编排，不代表 M15-02 路由收口、M15-03 性能门、M15-04 全量审计或 M15-05 正式入口切换已完成。

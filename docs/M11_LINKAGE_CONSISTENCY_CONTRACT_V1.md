# M11-04 联动一致性合同 V1

合同 ID：`M11_LINKAGE_CONSISTENCY_V1`  
适用计划：`workbench-upgrade-plan-v2.1`  
阶段：M11-04（预览）

## 目标

API25 和 API26 必须在同一分析 snapshot 与同一日级 member_state 分片上查询。板块查股票、股票查板块都复用已物化的 `member_rank` 与 `rank_valid_count`，不得在请求过滤后重新排名。M11-03 的 association 仅作为关联字段附加，不改变完整成员列表的排名或分页口径。

## API25

`GET /api/linkage` 支持 `sector_id` 或 `security_id` 至少一个，并支持 `basis`、`trade_date`、`page`、`page_size`、`q`。返回的 `sector_member_rank`、`sector_member_count`、`member_rank_valid_count` 来自同一日的 `sector_member_state_daily`/`sector_base_daily`；`q` 和 security 过滤只作用于展示结果，不作用于排名。

若 association 分片存在，返回 `association`、`association_rank`、`association_eligible`、`association_rejection_reasons`、`association_contract_id` 和 `association_history_basis`。标签板块可以出现在 memberships 中，但不能被提升为强势关联。

## API26

`GET /api/linkage/history` 要求 `sector_id`，可选 `security_id`、`days`、`basis`、`trade_date`、分页参数。结果按日期降序、成员名次升序、证券 ID 排序，返回成员状态和独立的加入/退出、强弱变化字段；不把完整成员状态展开成无意义的全市场笛卡尔积。

## 一致性验收

- 正查和反查对同一证券—板块关系的名次、有效名次数一致。
- 对同一股票搜索或 `q` 筛选，不改变其板块内原始名次。
- API25/API26 的 snapshot、trade_date、history_basis 可追溯且不混用。
- 当前数据命中数量不作为经济有效性证明；历史回算不足时显示可用范围，不补造事实。

旧 publication 没有 M11 分析绑定时保留兼容读取路径；一旦存在 M11 分析绑定，必须使用本合同路径。M10 金额 A 等综合审计事项独立管理。

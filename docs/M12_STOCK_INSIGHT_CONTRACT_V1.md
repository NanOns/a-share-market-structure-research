# M12 统一个股透视合同 V1

合同 ID：`M12_STOCK_INSIGHT_V1`  
适用计划：`workbench-upgrade-plan-v2.1`  
阶段：M12（预览）

## API29

`GET /api/stocks/{security_id}/insight` 默认返回 `overview,technical,sector_context`，支持 `include=overview,technical,structures,sector_context` 和 `days=1..250`。首屏聚合不内嵌长 K 线；历史页签按需调用 API12/13。

overview 使用当前发布绑定的本地 quote；technical 复用已物化技术分片；structures 复用结构摘要；sector_context 复用 M11-03 association 分片。API29 不重复计算因素，不使用在线来源，不把 NULL 转成零或“近期强势”。

响应必须带 `snapshot_id`、`history_basis`、`basis_metadata`、`capabilities` 和 `data_quality`。技术字段缺失时保留 NULL 并说明能力状态；回算数据不得被描述为历史时点事实。

## 统一透视交互

所有股票入口使用同一个透视抽屉/弹层，路由状态至少包含 `publication_id`、`security_id`、`tab` 和 `days`。概览、技术、板块上下文首屏可用；历史页签懒加载 API12/13，图表必须明确 RAW/ADJUSTED 口径；证据内容使用分组和安全文本渲染。关闭后迟到响应不得重新打开抽屉。

任何跨模块或综合性“实现与方案均非最佳”问题单独登记范围、证据和验收，不限定为金额A。

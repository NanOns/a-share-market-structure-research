# FP01–FP14 最新合同入场与缺口矩阵

最新 Drive 合同 17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu 已读取；原文存 DRIVE_LATEST_FP_TASKS.md。最新 R43 交接 1fXrGxfkNq0rSqPtPkmaI1zt2ezVH0f-T 已回读。父设计 REV2 §62A–§69、§81.2 与既有升级/失败记录仍适用。

本轮为原合同下的第一批工程入场、控制面修复及实际缺口QA，不改写设计。已有 FP 历史工程成果继续沿用，不把旧阶段测试或本轮数据读取计作10/08完整FP验收。FP14历史BLOCKED保持。

| 包 | 实际状态/证据 | 下一工作包 | 正式验收 |
|---|---|---|---|
| FP01 生产语义与版本化发布合同 | 限定运营读取与旧权限隔离；用户原始事件找到 | 独立回读原会话；未来权限更改必须调用 USER_PERMISSION_ORIGINAL_EVENT_GATE_V2，并独立校验范围与发布门 | NOT_GRANTED_BY_THIS_RUN |
| FP02 生产数据总线 | 10/08 Head 正常、5224画像、5209行情 | 独立日期的 Source QA/身份/生命周期/GBBQ 与 operational successor builder；不能扩写固定四日 DATES | NOT_GRANTED_BY_THIS_RUN |
| FP03 BFF及字段合同 | 具体缺失 Owner/阶段、错误 token409、越界日期400 | 补全各缺失 route 的真实 producer/schema；数值/单位/窗口/时点抽样核验 | NOT_GRANTED_BY_THIS_RUN |
| FP04 六入口框架 | 六导航可达、10/08日标、首页运行异常修复 | 补齐独立区块失败隔离与中文显示；原六入口联调1366/1920/Edge | NOT_GRANTED_BY_THIS_RUN |
| FP05 今日总览与市场四轴 | 四轴可读；变化/风险/net-information缺失明确 | 接入真实变化/风险/去重净信息 Owner；无源不能显示0或无风险 | NOT_GRANTED_BY_THIS_RUN |
| FP06 板块研究与轮动 | 400板块、煤炭32成员；时间线缺失不再阻断成员 | 绑定 dated timeline/overlap owner；递归Rotation独立oracle另项，不声称严格历史PIT | NOT_GRANTED_BY_THIS_RUN |
| FP07 个股画像与图表 | 真实代码搜索与F/R/成员关联可读；图表Owner明确缺失 | 复用真实历史/原生调整坐标，接入日周月chart；证券中文名称/别名及H解释Owner缺口定点修复 | NOT_GRANTED_BY_THIS_RUN |
| FP08 Focus生命周期 | 2477关注对象和真实事件读域可读 | 逐字段检查Episode/T0/Anchor/Observation/outcome；自动写入与读域独立门 | NOT_GRANTED_BY_THIS_RUN |
| FP09 市场指数涨跌停与事件 | 四轴已接；breadth/indices/limits/ladders路由缺失明确 | 复用冻结RAW/价格规则/market input_bindings中的真实Owner，适配各子路由；逐项数值对账 | NOT_GRANTED_BY_THIS_RUN |
| FP10 Forward结算与风险研究 | statistics/plans/fep/settlement缺失Owner已登记 | 接入真实enrollment/期限/结算/FEP权限链；统计未成熟保持pending，不伪造分母 | NOT_GRANTED_BY_THIS_RUN |
| FP11 诊断与旧模块 | sources当期可读；health/fep子页缺失明确 | 接入dated健康/源/规则/FEP诊断；旧日更脚本显式迁移，不能误改PIT Head | NOT_GRANTED_BY_THIS_RUN |
| FP12 PIT回放与比较 | 当期replay/compare无Owner；旧9/30独立上下文保持 | 接入freeze/as_of/compare合同；四日运营重建不冒充严格历史PIT | NOT_GRANTED_BY_THIS_RUN |
| FP13 全站浏览器验收 | IAB六入口、搜索、详情和成员实际截图/DOM | 完成每域真实功能、数值、Edge1366/1920、离线/失败隔离/性能；不能以HTTP200宣布通过 | NOT_GRANTED_BY_THIS_RUN |
| FP14 生产发布与日常运营 | 限定适配器原端口重启读取成功；数据Head未改 | FP13完整合同过门后独立UI/read联合CAS发布、失败回滚与真实每日successor；当前不授予FULL_PRODUCT | NOT_GRANTED_BY_THIS_RUN |

## 真实HTTP路由覆盖

| 路由 | HTTP | 数据状态 | 缺失Owner/阶段 |
|---|---|---|---|
| /api/v4/context | 200 | READY |   |
| /api/operations/status | 200 | ENVELOPE_READ |   |
| /api/v4/original-0930/context | 200 | READY |   |
| /v4 | 200 | ENVELOPE_READ |   |
| /api/v4/stocks | 200 | READY |   |
| /api/v4/sectors | 200 | READY |   |
| /api/v4/home | 200 | READY |   |
| /api/v4/stocks | 200 | READY |   |
| /api/v4/sectors | 200 | READY |   |
| /api/v4/focus | 200 | READY |   |
| /api/v4/focus/events | 200 | READY |   |
| /api/v4/market | 200 | READY |   |
| /api/v4/market/breadth | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_MARKET_BREADTH_OWNER FP09 |
| /api/v4/market/indices | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_MARKET_INDICES_OWNER FP09 |
| /api/v4/market/limits | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_MARKET_LIMITS_OWNER FP09 |
| /api/v4/market/ladders | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_MARKET_LADDERS_OWNER FP09 |
| /api/v4/events | 200 | READY |   |
| /api/v4/sources | 200 | READY |   |
| /api/v4/diagnostics/sources | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_DIAGNOSTICS_SOURCES_OWNER FP11 |
| /api/v4/diagnostics/health | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_DIAGNOSTICS_HEALTH_OWNER FP11 |
| /api/v4/diagnostics/fep | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_DIAGNOSTICS_FEP_OWNER FP11 |
| /api/v4/forward | 200 | READY |   |
| /api/v4/forward/statistics | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_FORWARD_STATISTICS_OWNER FP10 |
| /api/v4/forward/plans | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_FORWARD_PLANS_OWNER FP10 |
| /api/v4/forward/fep | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_FORWARD_FEP_OWNER FP10 |
| /api/v4/forward/settlement | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_FORWARD_SETTLEMENT_OWNER FP10 |
| /api/v4/replay | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_REPLAY_OWNER FP12 |
| /api/v4/compare | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_COMPARE_OWNER FP12 |
| /api/v4/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9 | 200 | READY |   |
| /api/v4/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/profile | 200 | READY |   |
| /api/v4/stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_STOCKS_SEC-00096141BD5420F5CB3120E687CDA5B9_CHART_OWNER FP07 |
| /api/v4/sectors/INDUSTRY:T0101 | 200 | READY |   |
| /api/v4/sectors/INDUSTRY:T0101/members | 200 | READY |   |
| /api/v4/sectors/INDUSTRY:T0101/timeline | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_SECTORS_INDUSTRY:T0101_TIMELINE_OWNER FP06 |
| /api/v4/sectors/INDUSTRY:T0101/overlap | 200 | SOURCE_INCOMPLETE | DATED_OPERATIONAL_SECTORS_INDUSTRY:T0101_OVERLAP_OWNER FP06 |
| /api/v4/stocks | 409 | ENVELOPE_READ |   |
| /api/v4/stocks | 400 | ENVELOPE_READ |   |

六入口真实生产浏览器快照见 LIVE_BROWSER_SIX_ENTRY_QA.json 和 live_browser_*.jpg/.txt。当前使用 IAB；Edge专用、两种尺寸完整全站验收尚未授予。首页已暴露并修复原JS的缺失列表.length异常；板块缺失timeline/overlap不再阻断实际成员。

P0-A：ENGINEERING_HTTP_NAMESPACE_PASS，68 隔离HTTP；原端口实际读回 37 HTTP，含409/400反例。P0-B：本机原始用户事件可回读，独立外部签收未授予。P0-C：BLOCKED_EXACT_REASON / OPERATIONAL_SUCCESSOR_BUILDER_AND_SOURCE_QA_NOT_ADMITTED，last-good=2026-10-08。

下一阶段：上述定向工作包逐包工程和外部验收；完整FP01–FP14尚未通过，Rotation全状态机验证独立跟踪。
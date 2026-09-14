# V3 七池当天来源参数修复（2026-09-14）

## 阶段合同

- 审计项：`V3-EXT05-CURRENT-DAY-DATE-PARAM`，独立于其它在线数据集。
- 依据：`WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3` P09 在线来源能力门、`V3_ONLINE_LATEST_TRADE_DATE_20260914` 的最近交易日合同；`v3-p09-online-products-v1.0`、`v3-p09-runtime-capabilities-v1.0`。
- 结果：`FULL_PASS`（七池当天读取切片）；不扩大为 P09 整体发布就绪。

## 原因与修复

2026-09-14 15:53 北京时间实测，EXT05 的 `pool_name=limit_up&date=2026-09-14` 返回 HTTP 200、`data:null`，规范化报 `EMPTY_EVENT_POOL`；同池只传 `pool_name=limit_up` 返回 56 行。页面对七池均传最近交易日，因此同时显示不可用。历史日 `2026-09-11` 的显式日期请求仍返回行。

`_url` 对请求日等于北京时间自然日的 EXT05 请求省略 `date`，使用来源实时池；历史日仍携带规范化日期。请求 DTO 保留原请求日期；来源无日期字段，时间依据仍标为 `OBSERVED_AT_ONLY`，覆盖状态仍为 `UNKNOWN`，不冒充来源确认的逐池日期或完整分页。无数据时仍 fail-closed。

## 验收与下一阶段

- 七池实源当天读取：强势股、涨停、炸板、昨日涨停、跌停、新股、次新股均 `AVAILABLE`；第一页返回条数分别为 30、30、30、30、18、3、30。
- P09 产品定向测试 21 项通过，新增当天/历史日 URL 回归断言。
- 服务受控重启（PID 58216 → 40576）后，真实 HTTP `/api/v3/events/pools?trade_date=2026-09-14&page=1&page_size=20` 七池均 `AVAILABLE`。
- 未访问或修改 TDX 根，未保存 EXT05 原始响应、行、批次或快照。
- 下一阶段：持续独立跟踪 EXT05 实时池缺少来源日期及完整分页覆盖声明，不把本修复当作该缺口已解决。

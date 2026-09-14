# V3 在线最近交易日与实时热榜修复（2026-09-14）

## 阶段合同

- 审计项：`V3-ONLINE-LATEST-TRADE-DATE-AND-REALTIME-RANK`
- 合同：`V3_ONLINE_LATEST_TRADE_DATE_V1`
- 结果：`DEGRADED_PASS`

日期型在线产品不再读取本地发布版本的交易日，也不把北京时间自然日直接当作交易日。页面先请求 `GET /api/v3/online/latest-trade-date`，由 EXT03 与 EXT02 的公开来源响应确认最近可用交易日并选择最大值。交易日当天返回当天；周末、节假日或来源尚未形成当天交易数据时，返回来源确认的上一交易日。无法得到来源确认时保持 `UNAVAILABLE`，不猜测日期。

个股热度四榜继续直接请求 `GET /api/v3/hot-rankings`，不传 `trade_date`，使用请求时最新榜单，且遵守 `FORBIDDEN_REQUEST_TIME_ONLY`：不保存原始响应、行或批次。

## 证据与验收

- 2026-09-14 15:38（北京时间）实测：EXT03 与 EXT02 均返回 `source_trade_date=2026-09-14`。
- 页面实测在线交易日显示 2026-09-14；市场事件速览、最强题材均显示当天数据。本地发布版本仍为 2026-09-11，二者没有串用。
- 热度四榜实测四组均为 `AVAILABLE`，响应记录请求时 `requested_at/received_at`，无交易日请求参数。
- EXT01 在线涨停归档当日不可用，页面保持空态；事件速览因此为 `DEGRADED`，未回退并伪装 2026-09-11 数据。该来源能力仍需后续独立补齐。
- 页面可见文字已删除“龙字诀”和“龙字决”，模块名称改为“七池明细”等功能名称。
- `py_compile`、JavaScript 语法检查、2 项定向路由/入口测试及 `git diff --check` 通过。
- 服务已受控重启，PID 从 61112 更新为 58216，状态 `READY`。

## 变更范围

- `src/workbench_service/app.py`
- `src/workbench_service/static/v2/index.html`
- `src/workbench_service/static/v2/v3-unified.js`
- `src/workbench_service/static/online-p09-v3.html`
- `tests/upgrade_v3/test_p09_remaining_routes.py`
- `tests/upgrade_v3/test_v3_unified_entry.py`

未修改生产数据库、静态板块关系或 TDX 输入目录。

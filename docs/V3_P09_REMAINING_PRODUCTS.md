# V3 P09 剩余在线产品：阶段记录

## 阶段合同

本阶段依据 V3 主文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §18.12、§19.3–§19.5、§20.8、§22.2 执行，合同为 `v3-p09-online-products-v1.0`。范围是 EXT02、EXT03、EXT04、EXT05、EXT06、EXT07、EXT08、EXT09，以及对应 API、页面和 P09-04 在线上下文；EXT10/EXT11 不重启，EXT11 按 §22 维持退役状态。

## 输入、转换、存储、产品、证据

- 输入/来源：`config/online_source_registry_v3.json` 的 EXT02–EXT09；当前探测回执为 `reports/upgrade_v3/P09-01-B-REMAINING-CURRENT-PROBE.json`。
- 转换：`src/workbench_online/p09_products.py`。EXT03 日期转换为北京时间零点 Unix 秒，EXT02/EXT04 日期和必需查询参数按真实响应合同组装；EXT04 数组字段长度不一致时失败关闭；事件、题材、热榜、板块、话题均保留来源顺序和来源字段，不重新排名、不猜倍率。
- 存储：本阶段 EXT02–EXT09 均为请求时 DTO；raw、row、batch、缓存和 snapshot 均不落盘。EXT01 收盘批次仍由既有 `event_store.py` 独立负责。EXT07–09 明确 `REQUEST_TIME_ONLY`。
- API：`/api/v3/events/overview`、`/api/v3/events/pools`、`/api/v3/events/topics`、`/api/v3/events/distribution`、`/api/v3/events/topics/{id}/members`、`/api/v3/events/stocks/{id}`、`/api/v3/hot-rankings`、`/api/v3/hot-plates`、`/api/v3/hot-topics`、`/api/v3/research/sectors/{id}/online-context`。
- 页面：`/v3/online` 汇总速览、七池、题材/分布、四榜、热门板块和热门话题；`/v3/events` 保留 EXT01 简图与单股来源证据。
- 验收：`tests/upgrade_v3/test_p09_remaining_products.py`、`scripts/verify_p09_remaining_products.py` 及机器回执 `reports/upgrade_v3/P09-REMAINING-PRODUCTS.json`。

## 接受结果

工程链为 `FULL_PASS`：八个剩余数据集都有版本化适配器、独立失败状态、请求预算、API/页面入口和禁止持久化证据。真实源能力按数据集独立记录；2026-09-11 探测中 EXT02、EXT03、EXT04、EXT05、EXT07、EXT08、EXT09 可解析，EXT06 返回来源错误并保持 `UNAVAILABLE`。因此按 V3 §22.2，P09 总体源状态为 `DEGRADED_PASS`，不得伪称整体源 `FULL_PASS`；本地功能不被该源失败阻断。

## 下一阶段

进入 `P09-INDEPENDENT-AUDIT`：检查路由覆盖、失败关闭、日期/分页预算、热榜零持久化、EXT11 退役边界、TDX 只读和本阶段回执；发现问题直接修复后重新回归。

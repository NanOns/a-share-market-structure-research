# V3 P09-01-B-LZ-EXT01：同花顺涨停池当前复测

## 阶段合同

依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B`、§18.12、§19.3–§19.4、§22.2–§22.3，本小任务只执行龙字诀主链 `EXT01`。

- 合同：`V3_LZ_EXT01_LIMIT_UP_1` / `v3-lz-ext01-limit-up-v1.0`。
- 请求：同花顺 `limit_up_pool`，`page=1`、`limit=50`、`filter=HS,GEM2STAR`、`order_field=330323`、`order_type=0`、交易日 `20260911`。
- 字段参数：只发送已登记的明文候选字段，不臆造数字 field code；代码、倍率、时间语义必须由当前响应确认。
- 证据：只保存脱敏结构、字段名、计数、覆盖和哈希元数据；不保存禁止的 raw 或规范化事件行。
- EXT11 的历史 BLOCKED 保留，但不再重试，也不作为 EXT01 前置。

## 验收证据

机器回执：[P09-01-B-LZ-EXT01_CURRENT_PROBE.json](../reports/upgrade_v3/P09-01-B-LZ-EXT01_CURRENT_PROBE.json)。

本次当前复测实际结果：HTTP `200`、`application/json`、`17546 bytes`；顶层为 `status_code/status_msg/data`，`data` 含 `date/info/limit_down_count/limit_up_count/msg/page/trade_status`；行路径固定为 `$.data.info`，本页 40 行。行字段已观察到 `code/name/latest/change_rate/amount/order_amount/currency_value/turnover_rate/open_num/reason_type/first_limit_up_time/last_limit_up_time` 以及来源附加字段 `change_tag/high_days_value/is_again_limit/is_new/market_id/market_type`。

顶部路径和分页只完成结构探测：`limit_up_count`、`limit_down_count` 存在，但本任务不把顶部值当作已完成全量分母；当前仅 `page=1/limit=50`，`complete_pagination=false`。`change_rate`/`latest` 可观察为有限值，`amount` 的单位/转换仍未固定；`order_amount`、`currency_value`、`turnover_rate`、时间字段和原因字段保持源字段证据，等待后续重复样本确认。

| 检查项 | 结果 |
|---|---|
| HTTP/JSON | `200`、`application/json`；失败时标 `UNAVAILABLE`，不把空值当 0 |
| 行结构 | `$.data.info`，当前页 40 行；字段集合已写入机器回执 |
| 字段倍率/时间 | 未确认前保持 `UNRESOLVED`；不开放严格字段消费 |
| 分页 | 本小任务仅单页探测，不宣称完整覆盖 |
| 持久化 | raw、规范化行、生产表均为 0；仅原子写元数据回执 |
| 定向测试 | `python -m pytest -q tests/upgrade_v3/test_p09_01_b_lz_ext01.py` |

## 放行与下一步

若合法响应含可识别行结构，本小任务最多为 `DEGRADED_PASS`：只能进入 EXT01 数据层准备，字段倍率和完整分页仍需后续小任务固定；若当前源不可用，则记录 `UNAVAILABLE`，按 §22 转验 EXT03/04，不阻断其它独立龙字诀来源。

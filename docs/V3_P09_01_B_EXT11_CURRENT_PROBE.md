# V3 P09-01-B-EXT11：东方财富公开报价当前复测

## 结论

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`、§19.3、§19.4、§20.6，本小任务结果为：**BLOCKED（当前复测未稳定获得可解析响应）**。

本次正式复测复用了既有 `workbench_online.eastmoney_quotes.fetch_eastmoney_quotes` 适配器，以 8 秒超时、2,000,000 字节响应上限、零重试请求两个规范证券 ID；源端返回 `RemoteDisconnected`，没有形成可接受的当前响应证据。原始响应只在内存中处理，未写入文件、数据库或热榜/报价批次。

## 当前证据

| 项目 | 结果 |
|---|---|
| 来源 | `EXT11 / EASTMONEY_QUOTES` |
| 响应 | `RemoteDisconnected`；本次没有 HTTP 状态码/正文 |
| 覆盖 | 0/2；覆盖率 0.0 |
| 市场范围 | 本次未取得当前市场覆盖证据；静态合同仍为 SH/SZ，BJ 不支持 |
| 解析路径 | 未进入 `data.diff` 解析 |
| 价格/涨幅/金额/成交量 | 本次未取得当前值；单位保持未确认 |
| 换手率 | 本次未取得；不能宣布完整能力 |
| `quote_time` | 本次未取得；禁止用采集时间冒充 |
| 严格时间排名 | `NOT_VERIFIED` |

## 验收与下一步

- 阶段状态：`BLOCKED`。
- 观察性展示和严格 LIVE 排名均不启用；不得把源端断开当作空数据或可用能力。
- 不使用 `f170` 或采集时间冒充 `quote_time`；不因 BJ 不支持而拒绝 SH/SZ 覆盖。
- 机器回执：[P09-01-B-EXT11_CURRENT_PROBE.json](../reports/upgrade_v3/P09-01-B-EXT11_CURRENT_PROBE.json)。
- 定向测试：`python -m pytest -q tests/upgrade_v3/test_p09_01_b_ext11_probe.py`。
- 下一动作：人工重新启动 `P09-01-B-EXT11-RETRY`；EXT11 未取得可接受当前证据前不进入 EXT01。

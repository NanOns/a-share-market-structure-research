# P12-15 换手率来源人工核对后复测矩阵（2026-09-16）

> 测试时间：2026-09-16T04:02:35.814122+00:00；仅做在线来源测试，不运行换手算法或扫描器。

| 来源 | 单股 | 任意批量 | 排行榜批量 | 换手率 | 流通股本 | 短频测试 | 状态 |
|---|---|---|---|---|---|---|---|
| TENCENT | PASS | PASS | — | YES | NO | PASS | AVAILABLE |
| SOHU | PASS | FAIL | PASS | YES | NO | PASS | DEGRADED |
| STCN | PASS | FAIL | — | YES | YES | PASS | DEGRADED |
| STOCKSTAR | PASS | FAIL | — | NO | YES | PASS | DEGRADED |
| SINA | PASS | PASS | — | NO | NO | PASS | DEGRADED |
| XUEQIU | FAIL | FAIL | — | NO | NO | — | UNAVAILABLE |
| THS | FAIL | FAIL | — | NO | NO | — | UNAVAILABLE |

## 关键结论

- 腾讯仍是本轮唯一的任意证券批量换手率来源；1/2/20/50 条均使用项目现有适配器测试。
- 搜狐单股端点可取价、量、额、换手率；沪/深/北交所换手率排行榜端点每次各返回 50 条，但不能替代任意候选批量查询。
- 证券时报单股 JSON 可取换手率、价、量、额、流通股本和总股本；逗号拼接股票代码返回零值占位，不能作为批量端点。
- 证券之星单股 HTML 能取静态流通/总股本；没有找到公开批量接口，本轮不据此计算换手率。
- 雪球未绕过 WAF/调试限制；新浪未找到日度换手率数据合同；同花顺未找到无需签名的稳定公开端点。

## 使用边界

- 所有 `AVAILABLE/DEGRADED` 都是本次有限访问测试，未核实换手率分母；不能直接写为 FLOAT_SHARE。
- 实时来源仍需在目标交易日收盘后经本地 close/amount/volume 指纹绑定，才能进入项目的可用证据层。
- 未请求东财、凤凰财经和大智慧：按本轮用户指定范围排除。

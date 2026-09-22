# P12-14 东财换手率接口诊断

## 结论

`ulist.np/get` 支持逗号分隔的批量 `secids`，当前证券映射 `SH -> 1`、`SZ -> 0` 及字段 `f168` 没有发现格式错误。当前环境失败与批量数量无关：1只、2只、20只、50只均在收到HTTP响应前被远端断开。

## 修正后的请求合同

- endpoint：`https://push2.eastmoney.com/api/qt/ulist.np/get`
- `secids`：`0.002491` 或逗号拼接多个值。
- `fields`：`f2,f3,f6,f12,f13,f14,f47,f168,f170`。
- 增补公开客户端常用的 `ut=fa5fd1943c7b386f172d6893dbbd1d0c`。
- 增补 `Referer: https://quote.eastmoney.com/`。
- `fltt=2`、`invt=2`、浏览器User-Agent。

## 诊断矩阵

| 检查 | 结果 |
|---|---|
| 东财个股HTML `quote.eastmoney.com/sz002491.html` | HTTP 200 |
| `ulist.np/get` 1只 | `RemoteDisconnected` |
| `ulist.np/get` 2只 | `RemoteDisconnected` |
| `ulist.np/get` 20只 | `RemoteDisconnected` |
| `ulist.np/get` 50只 | `RemoteDisconnected` |
| 增加 `ut` | 仍断开 |
| 增加 `np/pn/pz` | 仍断开 |
| 移动端参数及User-Agent | 仍断开 |
| 单票 `stock/get` | 仍断开 |
| 历史 `push2his` K线 | 仍断开 |
| urllib | 远端无HTTP响应即断开 |
| curl/Schannel | `server closed abruptly` |
| Chromium浏览器 | `ERR_EMPTY_RESPONSE` |

## 证据解释

失败发生在JSON解析、证券数量校验和字段处理之前。三个独立网络客户端得到相同空响应，且单只与批量表现一致，因此不能归因于批量不受支持或当前 `secids` 格式错误。更符合证据的解释是东财 `push2`/`push2his` 数据主机当前对本机出口、访问频率或边缘节点策略执行了连接级拒绝；具体服务端规则无法从公开响应确认。

此前002491的22.70%验证了换手字段和单位口径，但不等于 `push2` 主机在每次运行时都可用。正式20只探测回执也记录为 `RemoteDisconnected`，没有可复用的成功东财批量响应。

## 系统处理

保留东财为主源并修正标准参数。生成阶段遇到连接级失败后使用版本化腾讯备用合同；所有备用结果仍必须通过本地目标交易日收盘价、成交额、成交量指纹绑定。页面不直接访问任一外部源。

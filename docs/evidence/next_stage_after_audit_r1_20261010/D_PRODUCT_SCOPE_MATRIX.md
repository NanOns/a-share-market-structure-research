# FP13 已投产研究读取范围矩阵

证据 D_HTTP_READBACK.json：68个有界真实HTTP请求及原字节SHA；当前T0=2026-10-09，token=受保护运营Head。HTTP200仅证明响应成功，计算READY与SOURCE_INCOMPLETE分别列出。

| 真实请求域 | HTTP | 业务状态 | 数量 | 解释 |
|---|---|---|---|---|
| `context` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `stocks` | 200 | READY | 5224 | 事实可读；未知字段仍逐项保留 |
| `sectors` | 200 | READY | 400 | 事实可读；未知字段仍逐项保留 |
| `focus` | 200 | READY | 2805 | 事实可读；未知字段仍逐项保留 |
| `home` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `market` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `market/breadth` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `market/indices` | 200 | READY | 5 | 事实可读；未知字段仍逐项保留 |
| `market/limits` | 200 | READY | 5224 | 事实可读；未知字段仍逐项保留 |
| `market/ladders` | 200 | READY | 72 | 事实可读；未知字段仍逐项保留 |
| `events` | 200 | READY | 913 | 事实可读；未知字段仍逐项保留 |
| `focus/events` | 200 | READY | 2805 | 事实可读；未知字段仍逐项保留 |
| `forward` | 200 | SOURCE_INCOMPLETE | None | 缺源域不可计算；不阻塞其他研究区块 |
| `forward/statistics` | 200 | SOURCE_INCOMPLETE | None | 缺源域不可计算；不阻塞其他研究区块 |
| `forward/plans` | 200 | SOURCE_INCOMPLETE | 0 | 缺源域不可计算；不阻塞其他研究区块 |
| `forward/fep` | 200 | SOURCE_INCOMPLETE | None | 缺源域不可计算；不阻塞其他研究区块 |
| `forward/settlement` | 200 | SOURCE_INCOMPLETE | None | 缺源域不可计算；不阻塞其他研究区块 |
| `sources` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `diagnostics/health` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/sources` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/contracts` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/jobs` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/legacy` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/shadow` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `diagnostics/fep` | 200 | SOURCE_INCOMPLETE | 0 | 缺源域不可计算；不阻塞其他研究区块 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/profile` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/timeline` | 200 | EMPTY_VALID | 0 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/why-not` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `sectors/INDUSTRY:T0101` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `sectors/INDUSTRY:T0101/members` | 200 | READY | 32 | 事实可读；未知字段仍逐项保留 |
| `sectors/INDUSTRY:T0101/timeline` | 200 | READY | 5 | 事实可读；未知字段仍逐项保留 |
| `sectors/INDUSTRY:T0101/overlap` | 200 | READY | 40 | 事实可读；未知字段仍逐项保留 |
| `focus/SEC-00096141BD5420F5CB3120E687CDA5B9/episodes` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `focus/SEC-00096141BD5420F5CB3120E687CDA5B9/timeline` | 200 | READY | 4 | 事实可读；未知字段仍逐项保留 |
| `focus/SEC-00096141BD5420F5CB3120E687CDA5B9/anchors` | 200 | READY | 2 | 事实可读；未知字段仍逐项保留 |
| `focus/SEC-00096141BD5420F5CB3120E687CDA5B9/observations` | 200 | READY | 4 | 事实可读；未知字段仍逐项保留 |
| `focus/SEC-00096141BD5420F5CB3120E687CDA5B9/outcomes` | 200 | READY | 10 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 420 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 420 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 91 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 91 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 22 | 事实可读；未知字段仍逐项保留 |
| `stocks/SEC-00096141BD5420F5CB3120E687CDA5B9/chart` | 200 | READY | 22 | 事实可读；未知字段仍逐项保留 |
| `stocks` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `stocks` | 200 | READY | 1 | 事实可读；未知字段仍逐项保留 |
| `stocks` | 200 | READY | 5224 | 事实可读；未知字段仍逐项保留 |
| `stocks` | 200 | READY | 5224 | 事实可读；未知字段仍逐项保留 |
| `replay` | 200 | SOURCE_INCOMPLETE | 0 | 缺源域不可计算；不阻塞其他研究区块 |
| `compare` | 200 | READY | 0 | 事实可读；未知字段仍逐项保留 |
| `candidates/cohort` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `candidates/sectors/INDUSTRY:T0101` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |
| `candidates/cohort` | 200 | READY | None | 事实可读；未知字段仍逐项保留 |

六页面HTML与六个当前JS模块原字节已读回；模块SHA与本地相同。1366/1920本轮真实DOM/截图均未通过：IAB报net::ERR_BLOCKED_BY_CLIENT，Chrome不可用。不得把HTTP或模块测试写成双视口产品验收。

当前单独可提审范围：股票事实/日周月行情、板块当前事实/成员、市场事实、Focus受限研究读取、诊断来源、历史corrected日期读取；均仍受原权限合同限制。FP13完整产品签收及FP14_FULL不签PASS。

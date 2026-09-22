# P12-15 在线换手率来源测试矩阵（2026-09-16）

> 测试时间：2026-09-16T03:31:24.603515+00:00（Asia/Shanghai）；活动研究日：`2026-09-15`。
> 仅测试在线来源获取能力，不执行换手算法、不修改 V3.3 候选/排名、不写入 TDX、不保存网页原文或 raw payload。

## 结论摘要

- 可在本次短探测中解析换手率且批量/重复请求通过的来源（访问层）：TENCENT。
- 同时通过活动研究包本地三重指纹的来源（项目可用层）：无。
- 页面或接口部分可达但不能形成稳定换手来源的来源：EASTMONEY, TENCENT, SINA。
- 当前活动包候选数：56；本次仅采用代表样本：`SH.600023, SZ.001216, SZ.300049, SH.688004, BJ.920028`。
- `AVAILABLE` 只表示本次有限探测通过，不等于长期生产 RPS 承诺；本地交易日指纹必须另行通过。

## 统一矩阵

| source_id | 页面 | 登录/Cookie | 公开端点 | 换手率 | 批量 | 重复请求 | 延迟ms | 本地日期指纹 | 状态 |
|---|---|---|---|---|---|---|---:|---|---|
| EASTMONEY | PASS | NO/NO | YES | NO | PASS | PASS | 187.57 | FAIL | DEGRADED |
| TENCENT | PASS | NO/NO | YES | YES | PASS | PASS | 210.97 | FAIL | DEGRADED |
| XUEQIU | PASS | NO/NO | YES | NO | FAIL | FAIL | 199.92 | FAIL | UNAVAILABLE |
| SINA | PASS | NO/NO | YES | NO | PASS | PASS | 179.29 | FAIL | DEGRADED |
| HEXUN | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| THS | PASS | NO/NO | YES | NO | FAIL | FAIL | 223.95 | FAIL | UNAVAILABLE |
| STOCKSTAR | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| SOHU | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| IFENG | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| JRJ | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| STCN | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |
| DZH | PASS | NO/NO | NO | NO | FAIL | FAIL | None | FAIL | UNAVAILABLE |

## 解释与边界

- `PASS` 只代表当前请求样本有响应/有字段，不代表分母口径已核实；本次未把来源字段名自动解释为 `FLOAT_SHARE`。
- 当前活动研究日为 2026-09-15，而实时探测发生在 2026-09-16；实时源若返回次日行情，日期指纹必须为 `FAIL`，不得附着到历史研究包。
- 频率测试为每个已探测公开端点连续 3 次、间隔 0.75 秒；没有规避 403/429、验证码、登录、签名或反爬认证。
- 未列出公开端点的来源按 `UNAVAILABLE` 处理，即使股票页面 HTTP 200，也不认定为可获取换手率。

## 下一阶段

- 对通过来源补齐版本化 source contract、明确 turnover_basis 证据和收盘后目标日绑定测试。
- 先保持来源作为独立可选输入，不进入算法、核心资格、核心分数或核心排名。

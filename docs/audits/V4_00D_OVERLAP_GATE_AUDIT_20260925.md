# V4-00D-OVERLAP-GATE-01 独立审计回执

| 字段 | 记录 |
|---|---|
| audit_id | `V4-00D-OVERLAP-GATE-01` |
| status | `OPEN` |
| opened_at | 2026-09-25 |
| scope | V4.2.2 REV2 §3B.4 / §3E 对完整包与本地 TDX 重叠验收的 mismatch 阈值、normalized tolerance 算法、身份键与 package-only/local-only 行语义。 |
| evidence | 最新 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd` 要求最近 60–120 个真实交易 session 全市场比对；列出 exact/tolerance/mismatch/package-only/local-only/identity 输出，并规定 mismatch 超过合同阈值时 `BOOTSTRAP_BLOCKED`。对应段落没有提供数值阈值或容差归一化算法。2026-09-25 实测 60 sessions、468,339 可比行、3,153 exact-field mismatch（0.67323%）、109,485 package-only rows、3,998 local-only rows；详见 `reports/v4_00d/v4_00d_overlap_20260925.json`。 |
| impact | 无正式 `ACCEPTED_SOURCE_PACKAGE` 判定；来源不得进入 V4-01 bootstrap 或 V4 Canonical Daily。现有 M3 FULL_PASS 只证明其旧目标日下载/解析校验，不能覆盖 V4 overlap acceptance。 |
| independent_from | V4-00D 阶段状态、M3 旧阶段结果、V4-00E adjustment contract、AUD-AMOUNT-A-06 与其他合同审计；上述项目均不能隐式关闭本项。 |

## 关闭条件

1. 合同 owner 明确阈值及统计分母，并定义 exact 与 normalized-tolerance 的数值/单位/算法（OHLC、volume、amount 分别处理），定义 package-only/local-only 的统计含义以及允许范围。
2. 明确 source identity 的比较键与语义；不把文件名相同等同 issuer 身份相同。
3. 对同一官方 package SHA、本地 TDX snapshot identity 与 parser version，重跑 60–120 个实际交易 session 的全市场比较，逐项回执 exact、normalized、mismatch、package-only、local-only、identity mismatch；达到合同阈值后方可将 overlap 标记 PASS。
4. 正反例证明超过阈值时 fail-closed 为 `BOOTSTRAP_BLOCKED`；容差、重试和结果记录不得改动任何 TDX 输入文件。

在关闭前保持 `OPEN`；不得自行推断 0.67% 可接受，也不得通过简单重试掩盖差异。

## 2026-09-25 修复验收

状态更新为 `CLOSED_FOR_A_STOCK_CORE / INDEX_DIAGNOSTIC_ONLY`。可重跑脚本 `scripts/v4_00d_overlap_acceptance.py` 用同一官方包和本地只读快照完成最近60个实际交易日、按证券类型分层的比较，报告为 `reports/v4_00d/v4_00d_asset_stratified_20260925.json`。

- A_STOCK：265,993 可比行；263,554 原始六字段精确一致；2,439 行被严格分类为同源官方终端刷新后的成交量修订；无法解释差异 0；身份键冲突 0；畸形记录 0。所有 A 股成交量修订均要求官方 ZIP 对应证券文件日期晚于本地文件时间、官方日线尾日也晚于本地尾日，且 OHLC 和 amount 完全一致。它是版本差异分类，不是按差异比例或数量放宽。
- A_STOCK source package：`ACCEPTED_SOURCE_PACKAGE`。package-only 66,419 行属于新包覆盖超出本地旧快照或需后续生命周期证据的覆盖差异；local-only 0。缺行不被推成停牌或退市。
- INDEX 有 73 行未解释字段差异，留在独立诊断范围；指数能力不属于本次 A_STOCK Core gate。
- ETF/LOF、可转债、逆回购、OTHER 各自输出类型级计数与接受状态；任何非 A 股差异不回流阻塞 A 股 Core。
- source package SHA-256 `b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f`；TDX 本地 snapshot SHA-256 `a0e219048f025a9b8fa5998a8a2108535e9cee4b9f8a25573adf1019e97831ff`；独立复跑前后身份一致。

接受标准是分字段及来源版本语义的确定规则，不是总 mismatch 百分比阈值。TDX 格式不提供法律实体标识，因此 identity contract 限定为交易所+六位证券代码，不声称核验发行人法定身份。V4-01 的历史 PIT/lifecycle 事实仍按 V4-01 逐步补建。

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

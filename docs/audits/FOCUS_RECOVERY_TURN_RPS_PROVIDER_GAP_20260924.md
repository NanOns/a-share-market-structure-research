# RECOVERY_TURN RPS20 历史 provider 缺口

| 字段 | 记录 |
|---|---|
| audit_item | `RECOVERY_TURN_INVALIDATION_PROVIDER_INCOMPLETE` |
| scope | 提供 PIT-safe 的逐交易日 `RPS20` 与 `rps20_delta3`，绑定当日 accepted universe、价格调整身份、日历和完整横截面输入；独立验收 RECOVERY_TURN 的 RPS invalidation 分支。 |
| evidence | `FOCUS_PREDICATE_FACTS_BY_DATE_V3` 对 `rps20_delta3` 保持 `null`，并把 `RECOVERY_TURN_INVALIDATION_PROVIDER_INCOMPLETE` 纳入事实摘要身份；tracked V3.3 invalidation 元数据显式列出 provider gap。结果 UNKNOWN 时 validity capability 也暴露此原因。当前未验证全市场点时 membership 和完整横截面历史，故不计算或回填 RPS。 |
| acceptance_result | `OPEN / FAIL_CLOSED_PROVIDER_GAP_EXPLICIT`。这是能力缺口的显式登记，不代表 RECOVERY_TURN 完整 invalidation 已验收。 |
| next_stage | 先冻结 point-in-time universe、RPS20 横截面排序、最小覆盖、复权口径、横截面缺失和输入身份合同；实现按日 provider 后，用具有 accepted identities 的历史片段验证 signal day 到 T+3 的 `rps20_delta3`，再独立验收 invalidation AST 的 TRUE/FALSE/UNKNOWN 分支。 |

旧 V2 事实摘要不回写；新事实使用 V3 digest 合同。真实停牌/复牌 Forward 样本仍另属未来数据验收门。

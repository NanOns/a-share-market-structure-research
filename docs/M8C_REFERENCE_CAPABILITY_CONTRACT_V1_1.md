# M8C-01 参考价能力合同 v1.1

`REFERENCE_CAPABILITY_V1_1` 将参考价、交易状态、风险/板块、上市阶段和除权核验拆开保存。仅凭本地 OHLC、前后两根 bar 或调整因子相等，不足以证明当日法定参考价为 `EXACT`；没有独立、可追溯、按日期生效的参考价/公司行为证据时，raw close 重建只能是 `APPROXIMATE`。

## 本地 OHLC 的安全边界

本地 OHLC 可以提供可观察的前一有效 raw close，但不能单独证明连续主交易日、普通阶段、除权状态或法定
参考价。调整因子状态还必须通过白名单、公司行为覆盖和生效日链路验证；字段相等本身不构成“无除权”证明。
因此当前本地物化器统一输出 `APPROXIMATE/UNKNOWN`，直到接入并独立验收逐日参考价与事件证据。

每行必须绑定 `security_id + trade_date + source_snapshot_id`，并保存 `quote_capability`、`reference_status`、`reference_basis`、`listing_phase`、`ex_rights_reference_unknown`、规则身份与质量码。缺失字段不允许补默认值。

M8C-01 只登记能力，不把换手率或涨跌停状态硬编码为可用。所有未知状态继续进入 M13，但只能以 UNKNOWN/排除原因呈现。

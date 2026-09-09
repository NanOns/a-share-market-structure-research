# M8C-03 能力降级门合同 v1

`REFERENCE_CAPABILITY_GATE_V1_0` 按 `security_id + trade_date` 输出能力状态和日期汇总，
三类状态固定为 `EXACT`、`APPROXIMATE`、`UNKNOWN`。缺失或未验证不会被当成精确能力。

- 参考前收、股本单位/口径和规则验证分别进入门控；任一必要组件 UNKNOWN，则整体不可用。
- 仅有显式 `rule_verified=true` 的规则结果才允许限价能力为 EXACT。已登记但未核验的
  规则保持 UNKNOWN，不自动变成 AVAILABLE。
- 按日期输出三类数量、比例和 `available_count`；APPROXIMATE/UNKNOWN 不进入精确换手率或
  涨跌停统计。缺失值仍为 NULL，并附质量码。
- JSON 报告使用原子替换写入工作区报告目录；不写 TDX、不联网、不修改发布头、
  observations 或 outcomes。

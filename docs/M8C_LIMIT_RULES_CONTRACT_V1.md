# M8C-02 涨跌停规则合同 v1

`LIMIT_RULES_V1_0` 是日期敏感、版本化的规则解析与状态服务。仓库不内置未经核验的
当前法规数值；调用者必须提供 `limit_rule_versions` 记录，并带有交易所、板别、风险
状态、生效起止日期、比例、最小价位、舍入方式和来源引用。

- 规则按 `trade_date + exchange + board + risk_status` 精确解析。生效区间重叠、没有
  匹配版本或来源缺失都会失败/返回 UNKNOWN，不静默选一条规则。
- 价格使用 `Decimal` 计算并按规则档位舍入；比较使用精确档位相等，不使用任意一分钱
  容差。输出 `LIMIT_UP`、`LIMIT_DOWN`、`NOT_LIMIT`、`SUSPENDED` 或 `UNKNOWN`。
- 新股无适用涨跌幅、除权参考价未知、参考前收缺失、板别/风险状态未知，都不退化为
  默认 10% 或 `NOT_LIMIT`；理由码会随结果返回。
- 该服务只计算规则状态，不写 observations/outcomes、不自动抓取法规、不修改 TDX
  源目录。正式启用前仍需用经核验的本地规则表和边界样本登记版本。

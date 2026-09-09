# M8A-02 新高与 RPS 合同 v1

本步骤实现 `TECHNICAL_HISTORY_V2_1_PREVIEW` 的新高和横截面相对强弱部分。

- 新高窗口固定为 20、30、60、100 个主交易日；`new_high_n` 只在
  `adj_close[t] > max(adj_close[t-n:t-1])` 且前置窗口完整时为真。
- 与前高持平输出 `at_prior_high_n=true`，不计为新高；新高连续天数按窗口独立
  维护，明确非新高归零，未知值中断并输出 NULL；早期不足窗口标记
  `is_left_censored`。
- `dist_prior_high_n=adj_close/prior_max_close-1`，前高非正或窗口不完整时为 NULL。
- RPS 对同日、同范围且 `ret_n` 有效的股票使用平均并列名次除以 N；N<100 时
  RPS 和 RS 均为 NULL，并记录实际有效样本数。

新高不从旧 `DIST_HIGH` 字段推断；RPS 不与 RS 混名。所有输出保存合同版本、
价格基准、窗口、样本数与质量代码。表写入按 slice 不可变，API11 只读取所选
成功绑定快照的 `high`/`strength` 分片；没有对应分片时返回未构建状态。

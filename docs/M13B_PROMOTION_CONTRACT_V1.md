# M13B-02 晋级集合与晋级历史合约 V1

## 1. 合约身份

- `contract_id`: `LIMIT_PROMOTION_V1_0`
- 阶段：M13B-02
- 输入：同一分析快照中已完成的 `limit_ladder_daily`
- 输出：`limit_promotion_daily` 与 API35 `/api/limit-ladder/promotion-history`
- 统计性质：描述性历史计数与分数，不代表概率、预测或交易建议

本合约只消费本地、已冻结的 M8C 限价状态和 M13B-01 晋级阶梯结果；不从名称、涨跌幅近似值或未来数据推断涨停。

## 2. 前一日集合

对每个相邻交易日 `(previous_trade_date, trade_date)` 和逻辑层级 `previous_level ∈ {1, 2, 3, 4PLUS}`：

1. 前一日 `limit_state=UP`、`streak_known=true`、`streak` 为整数、`ladder_level=previous_level` 的行，组成“已确认前一日集合”。
2. 前一日为 `UP` 但任一确认字段未知或不属于四个层级的，计入 `previous_unconfirmed_count`，不进入今日分母。
3. `previous_up_count` 保留前一日所有 `UP` 行数量，用于说明“全部涨停”和“合格关联”的差异。

## 3. 今日判定与分母

对每个已确认前一日成员，在今日查找同一证券：

- 今日缺行、`UNKNOWN`，或今日 `UP` 但 `streak_known=false`：`excluded_unknown += 1`。
- 今日 `SUSPENDED`：`excluded_suspended += 1`。
- 今日 `NO_LIMIT`：`excluded_no_limit += 1`。
- 今日为已知 `UP/DOWN/NONE`，且不是以上三类：进入 `eligible_count`。
- 今日为已知 `UP`，且 `streak = previous_streak + 1`：`success_count += 1`；这是唯一的成功条件。

因此：

```text
eligible_count = success_count + 已知但未连续晋级的今日结果
rate = success_count / eligible_count（eligible_count=0 时为 NULL）
```

排除项不作为失败项，且永不填入 `eligible_count`。这保证“昨日 10 个：今日 6 个连续、2 个已确认未封板、1 个停牌、1 个未知”得到 `success_count=6`、`eligible_count=8`、`rate=0.75`。

## 4. 结果字段

`limit_promotion_daily` 每个 `(slice_id, trade_date, previous_level)` 唯一一行，至少包含：

- `previous_trade_date`, `trade_date`, `previous_level`
- `previous_up_count`, `previous_unconfirmed_count`
- `success_count`, `eligible_count`
- `excluded_unknown`, `excluded_suspended`, `excluded_no_limit`
- `rate`、`contract_id`

没有可确认前一日集合的层级也保留零计数行，`rate=NULL`，以便历史图表区分“没有样本”和“尚未构建”。

## 5. 失败与能力边界

- 同一证券同一日期出现重复阶梯行：拒绝计算。
- 缺少 `limit_ladder_daily`、对应分析域或 M8C 输入未物化：API 返回 `NOT_BUILT`，不返回零值晋级率。
- `previous_level` 的逻辑编码固定为字符串 `1/2/3/4PLUS`。设计表中的 `I` 表示层级字段而非可直接存储的 SQL 类型；该编码差异单独登记为审计事项。

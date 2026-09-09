# M8B-03 日级覆盖合同 v1

`HISTORICAL_COVERAGE_V2_1_RECONSTRUCTED` 将 M8B-01 的技术/成员结果与 M8B-02
的五类结构结果按交易日汇总为市场聚合输入。它是只读的内存适配器，不执行 M9
板块周期、不写正式发布，也不写 observations/outcomes。

- 每个输入日期单独记录价格口径、技术行数、报价有效数/覆盖率、因子有效数/覆盖率、
  成员数与成员板块数；缺失日期不前填。
- 队列统计按 `STEADY/PULLBACK/BREAKOUT/LEADER/EARLY_QUEUE` 分开计数，并另存
  命中去重股票数。没有结构行是 `NOT_BUILT`；有结构行但命中为零是 `AVAILABLE`，
  两者不混淆。
- `DATA_INSUFFICIENT` 结构行保持 unknown 计数；不能把 unknown 转为未命中。未提供
  预期股票全集时标记 `EXPECTED_UNIVERSE_NOT_SUPPLIED`，不伪造覆盖分母。
- 回算行固定 `history_basis=RECONSTRUCTED`、`real_observation=false`、
  `observation_compatible=false`。即使传入真实成员日期，也只作为附加标记，不把回算
  结果称为真实观察。
- 输入超过 cutoff、技术键重复、结构键重复或要求非回算口径时拒绝；结果按日期稳定排序。

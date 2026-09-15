# P12-04 RANK_AND_LOO_V3_3 阶段验收

阶段合同`P12-04_RANK_AND_LOO_V3_3_ACCEPTANCE_V1`。执行前核对`AGENTS.md`、V3 v2.1升级方案§10–§12、§19及[P12-03验收](P12_03_SCANNER_V3_3_ACCEPTANCE_20260915.md)。本阶段实现纯合同`TODAY_RESEARCH_RANK_AND_LOO_V3_3_CANDIDATE_01`，不发布bundle、不物化170天。

当前publication冻结关系版本共52,028条去重行业/概念边，覆盖5,578股。逐股票×板块剔除目标股后，要求有效其他成员≥5、覆盖≥0.70、上涨比例≥0.55、中位收益>0且CURRENT明确TRUE；明确支持192股、明确不支持5,344股、UNKNOWN 42股。按关系数分层：1–2条关系444股（支持2）、3–5条1,455股（支持31）、6+关系3,679股（支持159）。支持数量不参与评分，分层仅作偏差审计。六只真实股票的逐板块LOO、样本、覆盖、B1/M1和关系hash写入[LOO证据](../reports/p12_04/current_loo_probe.json)。历史成员不可用，因此变化LOO保持UNKNOWN。

与P12-03当前漏斗合并后得到113只唯一合格股票：主类别启动104、正式延续9；SUPPORTED 17、INDEPENDENT 96。延续STOCK_ONLY原有140只完整保留，只有CURRENT+LOO明确TRUE者进入正式延续。四类主类别按固定顺序选择，不跨类比比分；具备完整字段的延续9只可评分，启动因正式RPS5_DELTA3缺失而104只全部保留为`QUALIFIED_UNRANKED`。简单影子排序与复杂排序使用完全相同的113只资格样本，无资格上限。证据见[排名探针](../reports/p12_04/current_rank_probe.json)。

固定反例覆盖目标股剔除、五成员板块剔除后样本不足、轨道FALSE、历史成员缺失、重复关系去重、固定主类别、未评分保留和评分边界；P12-04定向7项通过。阶段验收结果 **`DEGRADED_PASS`**：今日LOO、支持模式、固定主类别、评分和简单排序对照通过；跨日变化LOO及历史支持仍因历史成员缺口降级，不能宣传为PIT或效果证据。机器门见[回执](../reports/p12_04/p12_04_stage_gate.json)，下一阶段为`P12-05_REPLAY_V3_3`。

# P12-02 FACTOR_V3_3 阶段验收

阶段合同 `P12-02_FACTOR_V3_3_ACCEPTANCE_V1`。执行前核对 `AGENTS.md`、[V3 v2.1升级方案](V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md) §5、§7、§9.2、§19，以及[P12-01基线](P12_01_BASELINE_V2_ACCEPTANCE_20260914.md)。Phase 0基线为`FULL_PASS_TDX_NATIVE`。本阶段只对候选因子和事件状态机验收，不发布新扫描器或研究bundle。机器门见[阶段回执](../reports/p12_02/p12_02_stage_gate.json)。

正式登记供下一阶段消费的候选实现合同为 `TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01` 与 `PULLBACK_EPISODE_V1_CANDIDATE_01`；源码及参数摘要由[依赖锁探针](../reports/p12_02/dependency_lock_probe.json)核对，Git HEAD可恢复。因子输入须同一目标日`TDX_NATIVE_AFFINE_QFQ`调整锚、连续主日历序号、实际bar；RAW额量与报价实体单列。风险参数为prior波动底线4%、绝对跌幅8%、波动倍数2，属于首轮候选，不声称最优。事件合同逐会话更新种子、峰、回调及终态；峰前金额和回调金额不含确认日。跨锚旧信号布尔值须来自冻结输入，缺失时只许重构诊断。

旧 `STOCK_ATTENTION_PREVIEW_1` 实际执行谓词来自 `src/workbench_analysis/stock_attention.py:classify_stock_attention` 的`checks`，不能把配置声明直接等同于执行。当前代码核对发现配置中 `BREAKOUT/SETUP/RECOVERY.requires_position_fields`、`RECOVERY.requires_previous_close_below_ma5`、`TREND_BACKGROUND.close_gte_ma20`、`TREND_BACKGROUND.ma20_delta5_gt`、`STRUCTURE_BREAK.consecutive_valid_sessions` 未作为对应可配置开关被旧分类器消费。实际固定比较仍保留在代码，例如RECOVERY确实比较前收≤前MA5，TREND比较现价≥MA20和MA20五日上升，STRUCTURE比较当前与前日低于MA20；此处**仅否认配置开关生效**，不否认固定比较本身。P12-03必须锁定这些真实谓词，并用新合同明确处理开关差异，不能声称旧配置全部生效。

验证证据：[历史输入](../reports/p12_02/historical_input_pilot.json)、[真实换锚](../reports/p12_02/reanchor_pilot.json)、[RPS全集](../reports/p12_02/rps_population_pilot.json)、[来源与RAW静态重复性](../reports/p12_02/remaining_history_validation.json)、[三日期全股因子重放](../reports/p12_02/three_day_factor_replay.json)。03-31、06-30、09-14各6,182股；纯计算窗口READY分别5,444、5,446、5,511。三日候选因子分片两次写入逐日哈希一致，风险按市场与prior波动四分组记录，分组股票及三值风险计数均回合6,182。最新日重算调整OHLC与当前Parquet差异0，候选与P05四个重叠因子逐值差异0。公式人工复算、`ddof`、金额口径、极端风险三值、事件端点与左截断反例通过；相关31项回归通过。临时分片删除，无生产数据库写入。

**验收结果 `DEGRADED_PASS`**，范围是因子事实、风险、回踩状态机和RPS变化可比性的候选合同，允许开始 `P12-03_SCANNER_V3_3`。3月与6月没有当日GBBQ及universe封存，只能 `RECONSTRUCTED_CURRENT_SOURCE`；正式历史RPS变化仍NULL，真实冻结信号的历史episode不可宣称PIT，生产run/bundle依赖锁绑定留待P12-06。上述能力缺口不阻断本阶段候选公式验收，但不得转写成扫描器今日准入、历史效果或发布就绪结论。170天物化不是P12-03前提，保持未执行。下一阶段仅`P12-03_SCANNER_V3_3`；独立历史PIT审计项继续开放。

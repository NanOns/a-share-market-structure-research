# P12-05 REPLAY_V3_3 阶段验收

阶段合同`P12-05_REPLAY_V3_3_ACCEPTANCE_V1`。执行前核对`AGENTS.md`、V3 v2.1升级方案§14、§17、§19及[P12-04验收](P12_04_RANK_AND_LOO_V3_3_ACCEPTANCE_20260915.md)。按预登记时间顺序使用03-31开发诊断、06-30验证诊断、09-14锁定观察，最长前瞻10会话、参数调节NONE；当前成员关系复用模式明确为`RECONSTRUCTED_CURRENT_MEMBERSHIP`。

四组基线在每个日期与完整诊断启动样本等量：旧priority重构、仅RPS20、股票触发不含板块、完整启动，样本数分别70、295、107。启动的板块支持是分组而非共同硬门，因此本样本中股票触发与完整启动相同，已显式记录。合并去重后产生3,736条期限结果：3月596条OBSERVED；6月2,239条OBSERVED并保留1条DATA_GAP；9月900条NOT_DUE。评价合同为`HORIZON_END_TDX_AFFINE_QFQ_V1`，每个1/3/5/10期限以自身到期日e为复权截止和价格锚。

消融记录：当前延续从140个STOCK_ONLY到9个正式LOO结果；去除EXTENDED位置门后三日启动数量分别由70/295/107变为74/326/118；历史信号年龄不可恢复时统一使用公开的保守Freshness 0.20并标`AGE_LEFT_CENSORED`，不改变资格。相同输入的逻辑摘要可重复，当前哈希写入[回放证据](../reports/p12_05/replay_evaluation.json)。

验收结果 **`DEGRADED_PASS`**：实现正确性与重构诊断、同日等量基线、消融和时间隔离满足阶段门；只有两个已到期信号日，锁定段未到期，且成员/事件源不是历史PIT，因此效果保持`EFFECT_OBSERVATION_PENDING`，不据此选择参数、声称统计有效或发布概率。机器回执见[阶段门](../reports/p12_05/p12_05_stage_gate.json)。下一阶段为`P12-06_BUNDLE_V3_3`。

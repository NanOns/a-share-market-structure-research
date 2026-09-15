# P12-05 REPLAY_V3_3 进度记录

执行前核对`AGENTS.md`、V3 v2.1升级方案§14、§17、§19及[P12-04验收](P12_04_RANK_AND_LOO_V3_3_ACCEPTANCE_20260915.md)。预登记按时间固定：2026-03-31为开发诊断、2026-06-30为验证诊断、2026-09-14为锁定观察；最长前瞻10会话，参数调节为NONE。历史关系按用户决定复用当前冻结关系，身份固定为`RECONSTRUCTED_CURRENT_MEMBERSHIP`。

首轮只重放满足完整股票事实的诊断启动候选：三日分别70、295、107只。3月与6月的1/3/5/10会话共1,460条结果全部OBSERVED；9月14日之后没有本地交易日，428条全部NOT_DUE。评价使用`HORIZON_END_TDX_AFFINE_QFQ_V1`，每个期限以各自到期日e为截止与复权锚，未来结果不反馈信号。相同输入连续重跑的逻辑结果SHA-256均为`45064096ffecda5614ea381d17f106fdb13225d8b33d5471d40faf8a17e0deeb`。机器证据见[诊断回放](../reports/p12_05/replay_evaluation.json)。

后续四组同日等量基线和LOO/位置门/新鲜度消融已经补齐，本进度记录由[正式P12-05验收](P12_05_REPLAY_V3_3_ACCEPTANCE_20260915.md)收口；阶段结果为限定范围`DEGRADED_PASS`，效果仍为`EFFECT_OBSERVATION_PENDING`。

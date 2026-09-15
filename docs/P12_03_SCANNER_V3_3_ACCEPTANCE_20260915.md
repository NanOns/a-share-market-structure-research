# P12-03 SCANNER_V3_3 阶段验收

阶段合同 `P12-03_SCANNER_V3_3_ACCEPTANCE_V1`。执行前核对 `AGENTS.md`、V3 v2.1升级方案§8、§9、§19及[P12-02验收](P12_02_FACTOR_V3_3_ACCEPTANCE_20260915.md)。P12-02为有范围的`DEGRADED_PASS`，允许本阶段开始；本阶段不实现P12-04的最终LOO、评分和主类别。

新增纯扫描合同 `TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01`。输入仅为P12-02因子、锁定旧信号事实、事件确认事实和明确支持状态；输出启动、回踩、修复、延续四类的三值资格，并逐类保留`known_failed_checks`、`unknown_checks`与质量。公共门和安全门不能被旧等级、旧信号、RPS或板块标签绕过。启动区分最高价平台与收盘平台；修复的R20分支独立于旧RECOVERY；延续保存`STOCK_ONLY`影子结果且正式结果要求CURRENT+LOO TRUE；`SETUP_WATCH`只排除已知确认场景，其他场景UNKNOWN保持原样，不阻断观察状态。

[当前全量漏斗](../reports/p12_03/current_funnel.json)使用2026-09-14的6,182股：启动TRUE/FALSE/UNKNOWN为104/6,076/2；回踩为0/3,560/2,622；修复为0/6,022/160；延续STOCK_ONLY为140/6,041/1；正式延续为0/6,041/141；SETUP_WATCH为403/5,779/0。每类三值合计均为6,182。回踩历史冻结种子、正式RPS5变化及CURRENT LOO缺失均保留UNKNOWN，没有借旧等级或当前全集重构补TRUE。固定反例覆盖三值、已知失败与未知并存、安全否决、R20独立分支、延续支持门、SETUP观察、单价bar及旧等级绕门；P12-02/03相关33项回归通过。

验收结果 **`DEGRADED_PASS`**。扫描器资格、解释和全量漏斗满足P12-03阶段门，允许下一阶段`P12-04_RANK_AND_LOO_V3_3`。降级范围来自历史PIT冻结信号、正式RPS5变化以及尚未实施的P12-04 LOO；因此当前漏斗不发布为正式今日清单，不宣称效果，也未物化170天。机器回执见[阶段门](../reports/p12_03/p12_03_stage_gate.json)。

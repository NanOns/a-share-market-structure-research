# V4-03 R3 剩余阻断项闭环记录

治理任务：`docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md`；基础任务：`docs/audits/V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_20260927.md`。本记录只判断 R3 候选和能力范围，不签发最终外部验收。

1. **B01 golden vectors**：已有 47 份 `RULE_AST_V2` 机器合同继续使用同一数值执行器。新增 30 个具名边界案例，覆盖 exact N / one-short、停牌穿越与 T0、复牌、未解释缺口、复权与来源变化、零分母、非法 LOG、横截面端点与中间缺口、排名并列/缺失/成员变化/重排。R2 的 94 个向量仍保留。`V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json` 逐类别记录执行结果；边界案例为算法族共享，不声称每字段机械复制 30 个案例。
2. **Prior RPS**：R3 全域候选的 `prior_rps_origin` 已改为 `V4_03_STAGE_OWNED_HISTORICAL_STAGING_R3`。t-1 的 RPS5、t-3 的 RPS5/RPS20 先以冻结 V4-01 PIT 股票池和 V4-02 日线生成独立 staging artifact，再由 current delta 消费产物 SHA 与行摘要。独立程序重算历史股票池、收益、分数、输入/输出摘要和最终 delta。旧的 `DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED` 不再是 R3 候选的 prior 来源。
3. **Historical market path**：形成 786 行、2023-07-04 至 2026-09-24 的 daily-rebalanced research index staging artifact；785 个逐日收益用各步起始 PIT 股票池计算，接受的 V4-01 Universe 与 V4-02 daily/calendar/status 为输入。每行记录数量、覆盖、来源、复权、窗口与输出摘要。独立复核重新计算每日等权收益、路径值与摘要；UNKNOWN 后缀规则保持不变。具体 SHA 见 `V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json`。
4. **Market Regime**：形成同范围 786 行原生产物。breadth 为上涨减下跌占可评估收益行比例；participation 为 PIT 股票池可评估成交额总量对前 20 个市场日总量均值之比；stress 为跌停行占可评估涨跌停事实行比例；trend 使用上述研究指数的 close、MA20、五日前 MA20。每项保存原始分子、分母、覆盖、质量、阈值参数身份和来源摘要。独立程序从冻结 PIT 股票池、日线、涨跌停事实及历史路径重算 786 行，0 行不匹配。前期窗口不足时字段为 UNKNOWN，不填造值。
5. **四份 native 合同**：使用候选修订 `V4_03_NATIVE_DETERMINISTIC_RULE_SCHEMA_R3`，见 `docs/audits/V4_03_NATIVE_RULE_SCHEMA_AMENDMENT_R3.md`。独立执行器不导入生产因子，实现 PIT 等权、未知后缀路径、市场轴阈值及板块字段局部质量集合；20 个合成向量机器执行。该修订仍需外部接受。
6. **trend_axis**：唯一 producer 为 `MARKET_REGIME_TREND_WEAK_ERRATUM_V1`。primitive registry 不再声明自己生产此字段；scope、runtime、registry reference 的一致性检查 PASS。
7. **Sector**：采用正式 capability-scoped degradation，未伪造历史板块成员。`SECTOR_NATIVE=BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`；V4-08 Sector/Rotation 继续 BLOCKED，sector-dependent stock paths 为 BLOCKED 或 SHADOW_ONLY。Stock Core 和 Market 候选独立评估。
8. **上游身份**：没有修改 V4-01/V4-02 accepted head、manifest 或输入数据。R3 receipt 固定上游 SHA；TDX root 写入计数为 0。
9. **后继阶段**：没有启动 V4-04/V4-05 或 scanner/trading。逐历史 T 的完整 47 字段 Replay Gate A 留在 V4-05 合同内；本轮只形成 V4-03 所需的历史市场路径与三个前序 RPS 坐标。
10. **验收申请资格**：若所有 R3 独立回执和确定性重跑持续 PASS，按能力范围具备申请外部验收的候选资格。`V4_03_FINAL_ACCEPTANCE=NOT_GRANTED`，`V4_04_ENTRY=BLOCKED_UNTIL_EXTERNAL_ACCEPTANCE`。本轮只推送代码和证据，不自行发起云端审计。

机器汇总以 `reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json` 为准，列出每项能力、合同与输入 SHA、产物 SHA、测试、独立回执、残余 blocker 和下游权限。

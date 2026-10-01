# A02 Prior-RPS Bootstrap 候选收口

基线 `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`。执行 authority 是本轮总调度卡与 A02 R2 任务卡；它们授权工程候选，不构成独立外部验收。

状态：`A02_PRIOR_RPS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`。最终技术证据为 `reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json`，历史 R1/R2 均保留。RPS publication 格式 `V4_RPS_PIT_HISTORY_V1 / 1.0.0`，完整契约及 reader/producer 补强见 `config/a02_rps_pit_history_v1.json`、`config/a02_history_publication_reader_producer_r2.json`。

使用已经独立接受的 R7 有界 QFQ 历史、DM01 9/28→9/29→9/30 链、日期有效身份和 accepted 日历，冻结 9/22、9/23、9/24、9/28、9/29、9/30 六份不可变 publication。价格端点、区间、source revision、algorithm/parameter identity、universe identity、calendar identity、source/source-head binding、实际本轮 cutoff、logical digest 均显式保留。重读直接重构 135,413 条真实 source 记录并校验 250,680 个端点、rank 和 delta 值，零差异；pairwise 与 pandas average-rank oracle 均独立于 sorted-group producer。

这六份是基于 accepted inputs 的新候选，尚未被外部接受。历史语义仅为 `RECONSTRUCTED_CORRECTED`，没有 first availability 或 AS_RECORDED 声明。首份已发布且可计算候选为 9/22；首个完整 T-1 为 9/23，首个完整 T-3 为 9/28。这是本轮有界 publication 链的边界，不是全历史最早可计算日。缺失 prior、calendar/identity authority revision、新加入成员、历史区间缺行、unsupported adjustment 和坐标不一致都有显式 UNKNOWN；没有在 V4-07 reader 中重算历史。

原 V4-07/V4-09 算法和参数保持原字节，真实 9/28 5,222 个 accepted 身份的 old UNKNOWN 与 candidate RPS 分支全量重放。Seed 状态从 `TRUE=0 / FALSE=2443 / UNKNOWN=2779` 变为 amendment `TRUE=976 / FALSE=3755 / UNKNOWN=491`；V4-09 有 2,811 个身份发生业务变化。全量 old/new 输出和所有字段业务 diff 都已保存。新 Core/Factor/Seed 使用独立 candidate publication namespace，V4-09 精确绑定实际新 Seed bytes，当前真实 availability 不被回填为历史可用。

这些变化只能形成 amendment candidate。没有更新 V4-05/V4-07/V4-09 或 Stage/Data Accepted Head，没有开放 Production/Shadow/Focus，没有执行 V4-12。正式 reader 明确拒绝 self acceptance。下一步由本轮独立外部审计判断 publication 链与各下游 amendment，主线 V4-11 不受本工作包治理状态阻塞。

验证：`python -m pytest tests/v4_a02_r2 tests/v4_a05_r2 -q`；独立 source/readback：`python scripts/verify_a02_a05_candidate_readback_r1.py`。clean checkout 与 No-Symbol 由 root 批次统一执行并绑定本轮 receipt，不借用旧测试或旧 clean receipt。

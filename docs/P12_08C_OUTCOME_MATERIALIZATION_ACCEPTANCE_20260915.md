# P12-08C 后验结果物化引擎验收

## 阶段合同

依据升级文档 §17.1，实现 `HORIZON_END_TDX_AFFINE_QFQ_V1` 到期评价：每个期限统一以到期日 e 为调整锚，对 `[t,e]` 的原始 O/H/L/C 使用冻结的本地仿射调整引擎，输出 FRET、MFE、MAE。评价身份包含信号 run、证券、episode、期限、到期日、评价合同、评价源摘要、调整版本和 revision。未到期不消费评价源；缺信号日、到期日、窗口或价格时输出 `DATA_GAP`，不填0。

本阶段合同为 `TODAY_RESEARCH_FORWARD_OUTCOME_MATERIALIZED_V3_3_CANDIDATE_01`。真实数据尚未到期，本阶段只用合成反例验收计算实现，不将合成结果混入真实报告。

## 验收结果

**DEGRADED_PASS**。P12-07/08/08B/08C 定向回归17 passed，compileall 与 `git diff --check` 通过。送股合成反例中原始价格从10变为5，经到期日共同锚计算 FRET=0、MFE=+10%、MAE=-10%；缺到期行情保留 `DATA_GAP` 且没有收益字段。

真实结果文件包含452条 `NOT_DUE`、0条 `OBSERVED`、0条 `DATA_GAP`。由于没有真实到期行，脚本拒绝消费临时评价源，也没有生成任何真实收益值。产物为 `reports/p12_08/outcome_results.json`，阶段门为 `reports/p12_08/p12_08c_stage_gate.json`，均原子写入。未写生产数据库或通达信目录，效果状态继续为 `EFFECT_OBSERVATION_PENDING`。

## 下一步

等待新的真实收盘数据。先封存下一日信号；期限到期时冻结对应行情、GBBQ事件和摘要，再运行真实物化并形成新的评价 revision。达到20个真实信号日之前不得进入V3校准。

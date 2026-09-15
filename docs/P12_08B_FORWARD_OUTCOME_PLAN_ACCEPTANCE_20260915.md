# P12-08B 后验评价计划验收

## 阶段合同

依据升级文档 §17.1，后验评价采用 `HORIZON_END_TDX_AFFINE_QFQ_V1`，期限固定为1、3、5、10个交易会话。评价身份绑定信号 run、证券、episode、期限、到期日、评价合同和 revision。信号对象与评价对象分离；未到期、到期未物化和数据缺口不得填0，也不得提前计算盘中结果。

本阶段合同为 `TODAY_RESEARCH_FORWARD_OUTCOME_V3_3_CANDIDATE_01`，范围只包括 episode 首日去重、到期计划和 fail-closed 状态，不计算收益，也不进入参数校准。

## 验收结果

**DEGRADED_PASS**。113个稳定 episode 生成452条期限计划。受管收盘数据截至2026-09-14，全部452条为 `NOT_DUE`，`DUE_UNMATERIALIZED` 为0，产物没有 FRET、MFE 或 MAE 字段。定向 P12-07/08/08B 回归14 passed，compileall 与 `git diff --check` 通过。

计划写入 `reports/p12_08/outcome_plan.json`，阶段门写入 `reports/p12_08/p12_08b_stage_gate.json`，均采用原子写入。没有修改通达信目录，也没有写生产数据库。效果状态保持 `EFFECT_OBSERVATION_PENDING`。

## 下一步

等待新的真实收盘数据和V3.3活动包，先封存下一交易日观测；各期限到期后再以到期日e为锚物化独立评价 revision。达到20个真实信号日之前不进入V3校准。

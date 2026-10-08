# FEP R2 时序与标签版本独立复核

日期：2026-09-30。仅设计审计，不执行数据库，不修改主稿，不代表外部审计人认可。适用合同为当前R2草案、配套R2设计DDL及外部R1交叉审计。范围为P1-01逐fold/partition标签修订和P1-04三时间，不替代其他权限/部署/统计审计。

## 结论

**DESIGN_REMEDIATION_REVIEWED / IMPLEMENTATION_GATES_OPEN / EXTERNAL_REAUDIT_PENDING**。

外部P1-01指出的“全局唯一label revision与逐fold as-of冲突”和P1-04指出的“事实可见时间不得早于训练成熟的错误CHECK”在R2结构中已消除。实际截止、质量与跨partition防泄漏仍只写成待实现接受验证，不能称当前DDL已经执行这些防线，也不应标外部PASS。此前R1报告中的设计通过结论不能覆盖此次发现的新Schema问题。

## P1-01：逐fold/partition FK真实匹配

外部报告170–287行指出的问题成立。R2 SQL 104–114行完整分母ledger不再保存selected revision；117–123行cutoff主键为(dataset,fold,partition)；124–137行selection主键再含(observation,target)，同时精确FK到label revision及digest。138–154行dataset_rows复合FK完整携带dataset/fold/partition/observation/target/revision/digest。

因此同一observation/target可在fold A选择r1，fold B选择r2，且dataset_rows不能把fold A的r2伪装成A已选择的r1，也不能用错误digest代替正确revision内容。这是约束层面的结构修复，不只是文字改名。

但FK只证明“引用的是该fold登记的选择”，不证明选择本身合法。如下记录仍可能通过现有局部DDL：早fold cutoff=9月10日，而selection直接选择9月15日可见r2；或者selection为QUALITY_EXCLUDED且revision非空，其dataset_row仍满足FK。SQL359–374行已将三时间<=fold cutoff及ELIGIBLE要求列为接受服务门，因此属于明确尚未实现门，不是假定CHECK已执行。

必需验收向量：

1. r1可见9月1日、r2可见9月15日；fold A截止10日选择r1，fold B截止20日选择r2，合法。
2. A的selection指向r2必须在dataset接受前拒绝；不是等到预测才发现。
3. A行引用B partition的选择、错误digest或不存在revision，必须由FK拒绝。
4. PENDING/MISSING_LABEL无需虚假revision即可进入完整分母；不产生训练行。
5. QUALITY_EXCLUDED或training_allowed=false即便有数值，不能成为accepted训练行。

## P1-04：三时间与到期/质量

R2 SQL77–80行拆为source_fact_available_at、label_training_mature_at、label_revision_available_at，唯一相关局部CHECK为revision_available>=source_fact_available。R2正文45、57行分别限定三时间<=本fold/partition cutoff，并说明早事件不自动证明整个N-window质量。

这允许T+2事件事实已知、T+2投影已记录、T+5才训练成熟，不再人为倒填知识时间。T+3模型仍因mature_at不满足而拒绝；T+5成熟但T+6才收到revision时，T+5模型仍拒绝。早期PENDING revision必须等待成熟后的权威状态/版本确认，不能仅凭日历日期流逝将training_allowed自动变真。

必需验收：T+2/T+5合法行局部CHECK接受；三时间中任何一项晚于fold cutoff均禁止训练；修订依赖中任一晚到时间必须进入source_fact_available_at的实际依赖最大可见时间；成熟后仍缺N窗事件源质量的样本保持不可训练。

## 额外应明确的接受条件

- 同fold内FIT/TUNE/CALIBRATION/OUTER_TEST必须是互斥观察集合，并按正文要求落实日期/episode边界隔离。新主键含partition使相同observation可写进FIT与OUTER_TEST；这不是DDL错误，但接受层必须明确拒绝，否则修复per-partition选择后可能出现新泄漏入口。
- cutoff上界应按使用者区分：FIT标签<=该fold拟合开始；校准标签<=该fold校准拟合开始；OUTER_TEST标签只能用于预测之后冻结的评分截止，不得强迫外层测试标签<=原模型fit开始，也不得让较晚评分截止给FIT授权。training_runs目前只有整体fit_started/finished及calibration_finished，逐fold/phase开始时间需进入可验证manifest或phase run表，接受层按它验证。
- dataset_fold_cutoffs/selection和rows必须一并进入接受manifest digest；只查dataset全局截止不足以防跨fold更正泄漏。

## 接受结果与下一阶段

本次确认两项外部问题已有正确的结构性修复方向和对应复合FK；仍需上述接受条件的明确映射及E1/E3数据库/服务反例。主审完成其他领域复核后可形成R2候选并交外部复审，不能自行把外部审计状态改成PASS。本报告未执行SQL，未证明触发器/接受服务实际存在。

输入 `D:/Users/lps/Desktop/V4_2_2_FEP_R1_EXTERNAL_CROSS_AUDIT_R1_20260930.md` SHA256 `348549667e1e4df710955c5712ee292db9b7b20bad2624dfb6984c1f4def7831`。

输入 `artifacts/fep_r2_20260930/FEP_R2_SCHEMA_DESIGN_20260930.sql` SHA256 `4d30538941005182ee2cabea30e059ec3ccdf85c190c6cf6e7db4447b8425766`。

输入 `artifacts/fep_r2_20260930/FEP_R2_MODULE_DRAFT.md` SHA256 `65b200b64b72e48ec617d2d6b51c9fece0acb12c88cf4e7462720858b8af8873`。


## R2最终增量复核：触发器参考已补（2026-09-30）

当前SQL465–515行新增validate_fold_cutoff、validate_fold_label_selection、validate_dataset_row参考实现。静态阅读确认已比较fold cutoff与dataset上界、source及revision可见时间；ELIGIBLE选择另检查成熟及training_allowed；训练行必须指向ELIGIBLE选择；同fold跨partition日期/observation/episode冲突由advisory lock下查询拒绝。因此前述“仅注释”描述仅适用于本报告初审输入，当前草案已提供可审查的触发器代码，但本审计未执行数据库，不能改称触发器运行验收通过。

仍须同步正文/SQL注释的phase cutoff精确定义：FIT cutoff不晚于该fold fit_started；TUNE cutoff不晚于预注册selection_started；CALIBRATION cutoff不晚于calibrator_fit_started；OUTER_TEST cutoff为冻结评分知识截止，可晚于原模型fit。OUTER_TEST标签仅进入evaluation，不能进入对应模型fit、选参或校准。逐phase起止时间与评分截止必须在manifest有显式字段并由接受服务验证，不能用training_runs单一fit_started替代全部phase。这是防止把晚到评分标签回灌训练的必要语义。

额外实现检查：episode_key若不是scope内全局唯一，应在跨phase episode比较中一并比entity_id，否则不同证券局部episode号相同可误阻塞；若契约保证全局唯一须明确登记。并发隔离仍须真实PostgreSQL isolation level下运行反例，静态advisory lock存在不代表并发验收已通过。

当前结果保持 DESIGN_REMEDIATION_REVIEWED / IMPLEMENTATION_GATES_OPEN / EXTERNAL_REAUDIT_PENDING。没有自行授予外部PASS。

增量核对输入 `artifacts/fep_r2_20260930/FEP_R2_SCHEMA_DESIGN_20260930.sql` SHA256 `0ba6cbb468b4c045712dc47f66bb95777ffdc4001f383c2a8ee81598d8c40a67`。

增量核对输入 `artifacts/fep_r2_20260930/FEP_R2_MODULE_DRAFT.md` SHA256 `f6b796e56a846f78654c282200c9a7506a3a8c89fbdbcaaaa59d96f66e3df179`。

增量核对输入 `artifacts/fep_r2_20260930/FINAL_REV4_FEP_R2_DRAFT.md` SHA256 `be2f86e367fed8f15c3796ceb0ece73b33a58c501f1a5a8208b8fb90b0bb82e1`。


## 最后只读确认：phase与episode澄清已落稿（2026-09-30）

已核验R2正文FEP.8（第111行）与SQL：fold cutoff表有phase_started_at及cutoff<=phase_started_at CHECK（120–122行）；training_runs增加fold_id及phase_manifest（156行）；539–545行明确FIT/TUNE/CALIBRATION/OUTER_TEST消费者各自时刻、TEST仅评分及manifest一致性接受验证。跨phase episode检测514行已同时比较scope_id、entity_id、episode_key，避免不同股票复用局部episode号误拒绝。

因此本报告所提phase cutoff澄清和episode身份设计问题已修复。P1-01/P1-04在本次独立静态审计范围内为DESIGN_REMEDIATED；实际PostgreSQL执行、并发、manifest与时间真实性验收仍未运行。总体状态保持IMPLEMENTATION_GATES_OPEN / EXTERNAL_REAUDIT_PENDING，不能改作外部PASS。

确认输入 `artifacts/fep_r2_20260930/FEP_R2_SCHEMA_DESIGN_20260930.sql` SHA256 `536ee33f89e38b427b06ceffcb5e760964b0b4b64829b2a54d91c172f252a138`。

确认输入 `artifacts/fep_r2_20260930/FEP_R2_MODULE_DRAFT.md` SHA256 `f01ac9c550a71b8edb73436969e39172f6809404df9e19ffbfff2306c9456014`。

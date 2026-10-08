# FEP R0 独立时序与泄漏审计

日期：2026-09-30；审计范围：R0 全文时序、样本及出版链，与现行 CODEX-REV2 交叉核对。仅文档审计，不等同代码/真实数据验证。R0 中指向 Codex 的命令视为待审设计文本。本报告为独立跨域审计项，不能由现有阶段测试通过替代验收。

结论：可以作为新增能力方向，但以下 P1 在规范合并前必须落实修正规则；证据不足可以允许模块开发而关闭生产权限，不能凭空设市场有效阈值。主系统不得等待 FEP 模型具备统计支持。

| 编号 | 级别 | 原文证据（R0 行号） | 可复现反例 | 必须修正规则及验收 |
|---|---|---|---|---|
| TEMP-01 | P1 | §19 1222–1224，§22 1313–1341；REV2 1939–1945 | 9月1日样本 T+5 已到期；9月15日才收到修订终价；回放9月10日训练时仅检查成熟日，会读入15日版本。 | 区分 horizon_due_at、label_first_available_at、label_revision_system_available_at、label_settled_at。每个 target 单独选择 training_cutoff 内可见的末端无冲突 revision；同时满足 due 和全部输入可见以及质量。模型 manifest 保存精确 label_revision_id/evaluation_source_digest。补到/修订只追加，旧训练集不改。验收 late-arrival、分叉、删除、更正均不改变历史训练摘要。原例应写“9月29日创建的 T0 观察尚未成熟”，不能一概排除29日刚结算的老观察标签。 |
| TEMP-02 | P1 | §23、§60–63、§70 2867–2870、§71 2893、§72–73；REV2 4840–4841 | 10月1日训练好模型，回放9月30日 publication；其所有特征都在30日可见，但模型用了10月1日信息。没有 activation/deadline 约束会把结果计为9月30日正式预测。 | 冻结 model data_cutoff、训练完成、artifact accepted、promotion accepted、effective_from、预测开始/完成/接受时间；prediction_slot 预先绑定 model_set_id 或严格 as-of activation resolution，完整模型及校准器须在 slot 的 model_selection_cutoff 前可用。feature acceptance≤inference start≤prediction accepted≤deadline。晚完成/现代模型旧日推理标 RECONSTRUCTED，绝不填 PIT_OBSERVED。版本回滚也有前向生效记录，不能改旧 slot。 |
| TEMP-03 | P1 | §9 732–740，§105 3744–3749，§107 3788–3804；REV2 6312 | publication 接受时要求 snapshot 冻结，但 FEP 失败若同事务则阻塞Core；若异步从最新表读取，次日重试会读到修订事实，并可能创建第二个原始预测。 | accepted Core 原子写出含 publication/consumed-manifest 身份的 FEP outbox；异步读取其不可变输入生成快照，digest deterministic，不修改 Core；FEP 独立 slot=(publication logical day/model lineage,scope,model_set_id,预注册slot-contract)，first accepted及deadline独立，迟到失败保留日志。旧publication使用原消费事实，禁止live/latest。UNKNOWN/未完成不阻断 Core、Focus、settlement。端到端验收 crash before/after outbox、重复投递、deadline晚到及修订。 |
| TEMP-04 | P1 | §17 1111–1132、§18 1151–1181、§19 1194–1233；REV2 4632–4636 | 同一 PREWATCH 在 T+2确认、T+4失效；三个within-N二元标签同时为真。T0已CONFIRMED对象没有PREWATCH风险集；T+20未发生事件仍没有合法类别。 | 竞争风险 target 按T0固定episode/risk-set，首事件规则与REV2一致，同日硬失效优先；完整N日无首事件为 EVENT_FREE_AT_N，非 EXPIRED。尚未观察满N、缺事件源、模型/lineage变化分别为 censor/unknown/noncomparable，不能当negative。确认后价格继续结算。结构标签需明确事件合同版本；未来换新版 State 不得混接老标签。保持独立非竞争方向标签，不声称全部目标互斥。 |
| TEMP-05 | P1 | §19 1194–1233、§20 1250–1265、§52 2339–2379；REV2 4600–4606 | 全市场推理只有雷达cohort标签，训练天然只看到入选股票；另一实现每日PREWATCH及同日revision都加训练行，会重复放大同一episode。 | 独立 observation population 契约：RADAR事件或每日观察必须明确选一并版本化；MARKET_WIDE 建独立冻结Universe观察/settlement enrollment，复用数学不冒充算法cohort。logical_observation_id 与 publication revision observation 分层；唯一训练样本=(population_contract,logical_observation_id,horizon,target_family,evidence policy)，一个训练manifest只选一个revision；entity/date/episode相关性记录。不允许同一样本原始及corrected叠加。 |
| TEMP-06 | P1 | §31 1664–1676、§32 1704–1718、§35 1789–1818 | 基础模型按时序训练，但标准化/分箱/缺失填补或概率校准在整个验证段拟合，再报告该段OOS；purge天数再大也挡不住。 | 所有学得的分箱、imputer、scaler、feature selection、回退统计、calibrator、OOD参考分布随fold只用当时可见训练资料；校准独立时间段或严格OOF，最终评估段不参与选择。purge按真实label区间/可见时间，不仅按名义N；未来折再训练允许使用已成熟旧验证标签，但不得回改早折预测。训练/校准/评估日期组隔离，model artifact digest包含完整流水线。 |
| TEMP-07 | P2 | §9 769–777、§73 2917–2937、§77 2997–3013；REV2 4615 | 将“Feature与Target统一adjustment identity”解读为都用T+20调整源，导致T0特征吸收未来除权信息；反之强迫同一T0源又无法结算未来公司行为。 | T0 feature 原始冻结身份不变；label允许按其到期evaluation基准换算并保存独立身份与显式basis-transform。两者“可比坐标”不等于“同一信息时点/同一source digest”。ATR从T0坐标映射到label比较坐标只缩放差值，不加仿射平移。修订标签沿TEMP-01可见规则。 |
| TEMP-08 | P2 | §21 1273–1299、§73 2935–2937 | FIRST_OBSERVED字段被当PIT来源类型；一项重构预测首次计算也叫first observed，随后混入真实向前证据。 | evidence_origin/execution_mode 与 revision_view 正交：FIRST_OBSERVED只指真实按时slot接受结果；更广的FIRST_COMPUTED不自动成为PIT。重构样本保持RECONSTRUCTED_ASOF/CORRECTED，实际观察预测与后修订标签成对报告，不抹掉不利历史。CURRENT_MEMBERSHIP_REPLAY不得经统计回退变正式sector证据。 |

## 合并时推荐的最小强制不变量

1. 每一数据修订可见性取系统实际观察/入库时间，不能用业务有效日或供应商标称公开日替代。
2. target availability按target组件计算，某项已成熟不得为整行所有horizon/target解锁。缺值不填0；成熟不是可训练。
3. Dataset manifest冻结feature、target、修订和全部学得预处理；prediction manifest还冻结model_set、校准器、上下文、slot与本次实际推理环境。logical内容digest排除created_at/run_id等非语义元数据，数值规范化规则版本化。
4. 正式预测必须是在观察截止前真的完成并接受，且完整模型当时可用。历史replay复现能力与真实前瞻证据不得互换。
5. 独立capability降级：sector可选依赖缺失不能让Core expectancy一并失败；模型schema依赖需要冻结，不能推理时任意删列或挑更好的fallback。
6. 只描述研究路径期望；T0盘后收盘参考不是可成交入场，不得把回报/校准概率命名为交易胜率或保本承诺。M14边界原样保留，禁止借FEP扩展M14为概率来源。

## 接受结果与下一阶段

DOCUMENT_AUDIT_FINDINGS，TEMP-01至TEMP-06为规范合并前必须闭合的P1，TEMP-07/08需同步澄清。闭合可通过主合同中明确版本化规则、FK/唯一键及独立反例验收要求实现；它不意味着真实样本、模型效果或生产权限已通过。下一阶段由主审汇总去重、与统计/架构审计交叉检查后再修改最终方案；本报告未改最终方案。

输入SHA256：

- R0：`103195034c992fba06c3ab8ce79abc87bd6b4d19eb0973b8e5775da3d2250f69`
- REV2：`744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`


## 第二轮：FEP_R1_DRAFT 与设计DDL复核（2026-09-30）

阅读 artifacts/fep_20260930/FEP_R1_DRAFT.md 与 docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql；未执行DDL或改主稿。

TEMP-01至TEMP-06在语义设计上已有对应闭合：FEP.3严格label revision知识截止与完整模型激活链；FEP.2独立outbox和不可变输入；FEP.4独立population、target质量及修订单位；FEP.5/6明确首事件风险集、NONE及缺失；FEP.9全部学得转换和校准按时序隔离。TEMP-08通过三轴证据与不可回写原始slot闭合。设计修复仍须后续独立反例实现验收，不能标生产通过。

剩余发现：

- TEMP-R1-01（P1，合并前修正DDL）：SQL第156行prediction_slots.model_set_id NOT NULL，而第194行slot_receipts必须引用slot。无active model当天无法创建slot，也不能留下MODEL_MISSING/MISSED receipt，与FEP.4完整分母和FEP.16第11项冲突。建议预期slot先独立存在，model选择结果为NO_ACTIVE_MODEL或BOUND；具体选中模型使用唯一不可变binding，prediction必须引用非空binding。也可使用等价nullable模型集方案，但必须有成组CHECK和只有BOUND可创建prediction的接受验证，不能制造虚假模型。验收：零模型、撤销后无fallback、active模型缺artifact时仍有固定分母且不得产FIRST_OBSERVED值。
- TEMP-R1-02（P2，补精确坐标语义）：FEP.5说T0 ATR和P0全部转同evaluation basis，但应明确T0 feature snapshot原身份永不替换，label单独保存evaluation source identity和basis transform；ATR为差值只乘scale，不加affine offset。这能完整关闭TEMP-07，防实现者用未来调整源重做特征。
- TEMP-R1-03（P2，确定性补强）：FEP.4 dataset长表及SQL dataset_rows主键已防同fold重复；建议接受验证显式要求每(dataset,observation,target,fold)一个selected feature revision和label revision，并以冻结evidence policy说明同一observed样本可否使用cutoff内corrected label。只读latest仍禁止。此项为已有规则精确化，不新增全局阻断。

接受结论：R1核心时间语义可并入；TEMP-R1-01应先修设计DDL，TEMP-R1-02应同步补一句规则。其余不构成继续开发主线的门。修复后可以标DESIGN_REVIEW_PASS_WITH_IMPLEMENTATION_GATES，仍不意味生产模型或真实样本已通过。


## 最终时序复核：设计修正已核验（2026-09-30）

- TEMP-R1-01：已关闭设计阻断。当前DDL prediction_slots（165–174行）不再强制model_set；slot_model_bindings（175–183行）独立且每slot唯一；predictions复合FK指向binding。266–269行明确初始selection_status不可变、后续binding/receipts权威、选择截止前绑定及NO_ACTIVE_MODEL分母留存。无模型日可记录slot而无需虚假模型；实现时仍须故意缺模型/晚绑定验收。
- TEMP-R1-02/TEMP-07：已关闭设计歧义。FEP_R1_DRAFT.md第61行明确T0原始知识时间/source digest不变，label单独evaluation source，ATR只乘正尺度不加平移；FINAL_REV3_FEP_DRAFT.md第7123行同步了同文规则。
- TEMP-R1-03：现有dataset_rows唯一键、expected-target ledger及接受验证已覆盖单fold单选择与完整分母，修订选择继续受FEP.3截止及evidence policy约束。

最终结论：**DESIGN_REVIEW_PASS_WITH_IMPLEMENTATION_GATES**。在本次时序审计范围内，没有剩余阻止设计并入的已知P1。可并入REV3候选；不声称代码、数据库约束服务、真实观察数据、统计效力或生产预测通过。本次未执行数据库，也未修改主稿。后续E1–E5必须落实跨表接受校验、不可变知识时点、late revision/无模型slot/错deadline/坐标反例及真实证据门。

最终复核输入 `artifacts/fep_20260930/FEP_R1_DRAFT.md` SHA256 `7a3cb5896cc4e1560c39ec41d730efff3e636af461368061c9b8b12b2d877877`。

最终复核输入 `artifacts/fep_20260930/FINAL_REV3_FEP_DRAFT.md` SHA256 `93552ef08304ab7d9f841045123edaa1a31c8847af68d8462c211d6b385ede5f`。

最终复核输入 `docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql` SHA256 `79d116ab57d20f93f8c1dec4d071e2ddb86ea073c8a043fe29bb4eca4289f88f`。

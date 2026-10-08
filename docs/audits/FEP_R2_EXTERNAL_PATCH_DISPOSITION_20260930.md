# FEP R2 外部审计定点处置、修改说明与QA

日期：2026-09-30。适用输入为线上审计 `DA-MSR-V4.2.2-FEP-EXTERNAL-AUDIT-R1`，SHA256 `348549667E1E4DF710955C5712EE292DB9B7B20BAD2624DFB6984C1F4DEF7831`。

当前状态：R2_PATCHED / EXTERNAL_REAUDIT_PENDING / IMPLEMENTATION_NOT_VERIFIED。
线上R1唯一外部结论 `EXTERNAL_DESIGN_ACCEPTANCE_BLOCKED_PENDING_R2` 保留。本次逐项修复并交付复核证据，不自行授予外部PASS。FEP最终设计冻结、migration及E1正式任务卡继续等外部R2复审；V4现行主工程线不受FEP门阻断。

## 核对结论

五个P1均成立。上轮内部设计复核漏掉了正文和Schema之间的逐fold选择、细粒度授权和CAS结构差异，本次修正该接受范围。R1的时序、统计、backoff权重、首事件、独立人群、无模型/无label分母及旁路架构全部保留。R2是定点更新，不重新设计预测目标或Core。

| 外部项 | R2修改 | 文档/DDL处置 | 实现及外部验收 |
|---|---|---|---|
| P1-01 / R2-01 | expected ledger取消全局selected revision；新增fold+partition cutoff/selection；训练row复合FK绑定同fold revision+digest，三时间触发器参考 | DESIGN_REMEDIATED；早fold r1、晚fold r2可以独立表达 | DB运行未验；外部pending |
| P1-02 / R2-02 | permission_keys明确scope+target+horizon+feature_contract+model_set+capability；activation、acceptance、API与Priority共享grant_key | DESIGN_REMEDIATED；T5授权不蕴含T20授权 | 真实权限/服务未验；外部pending |
| P1-03 / R2-03 | deployment_heads、prior activation/version、变更receipt、CAS参考函数；冲突整事务回滚，只有head受控UPDATE | DESIGN_REMEDIATED；初始/替换/撤销/重投都有结构与反例 | PL/pgSQL、并发/角色未验；外部pending |
| P1-04 / R2-04 | source_fact_available_at、label_training_mature_at、label_revision_available_at分别保存；删错误due CHECK | DESIGN_REMEDIATED；T2事实已知/T5成熟合法，T3不能训练 | 权威adapter及成熟质量未验；外部pending |
| P1-05 / R2-05 | ENTRY只能事件日注释；今日全Radar PRIORITY_USE必须DAILY_LANDMARK/candidate-day同日预测及预注册覆盖门 | DESIGN_REMEDIATED；旧ENTRY不能长期作为今日预测 | daily label/coverage及排序未验；外部pending |
| P2-01 / R2-06 | 完整原始四份多方报告、外审、R2复核、diff、QA及hash manifest收入ZIP | EVIDENCE_PACKAGED | 外部可上传复核；未声称已push GitHub |
| P2-02 | 当前32张事实/历史表逐表显式guard；future migration必须清单测试；head单独受控触发器 | DESIGN_REMEDIATED | 未实际DB建表 |
| P2-03 | 主Header分ORIGINAL DESIGN BASELINE与CURRENT AUDITED IMPLEMENTATION HEAD | DOCUMENT_FIXED | 当前核对HEAD仍0581731c… |

## 内部复核新增小项

- Priority projection与权限回执以projection_id/run_id复合FK关联，不能借其它run的receipt。
- CHAMPION-only生产展示/排序明确；同集合baseline/challenger不继承该生产授权。
- CAS必需参数NULL入口拒绝、重投比较用IS DISTINCT FROM，避免SQL UNKNOWN放过不同请求；相同request_id严格一致回读。
- 每fold各partition日期/observation/同实体episode隔离；episode身份包含scope+entity，不能将不同股票同号误判为同episode。
- FIT、TUNE、CALIBRATION、OUTER_TEST各自phase_started_at和phase_manifest明确；TEST评分截止可晚于模型拟合，TEST label不进入该模型训练/选择/校准。

## 实際修改与版本

- 主文更新为DA-MSR-V4.2.2-CODEX-REV4-FEP-R2，§90替换为R2，并同步Header、当前版本声明和注册表引用。
- 模块独立文件为FEP R2；DDL版本FEP_SCHEMA_DESIGN_V2，新增fold选择、permission/head/receipt及验证参考。
- R1原始模块/DDL、REV3仓库证据及原始审计文件保留；桌面现行主文采用备份后原子更新。R1修订记录是历史，不代表当前最终外部冻结。
- 此次只写文档和未部署设计SQL，不启动训练、scanner、数据库migration或生产切换。

## QA结果与准确边界

PostgreSQL SQL语法由pglast v8.4解析通过：89条语句；33张表；85条本地/外部引用定义已检查，本地FK目标列及唯一键匹配；32张事实/历史表显式guard，deployment_heads独立受控。
文档编号、§引用、围栏及当前版本声明检查通过。手工可算/关系情景检查涵盖per-fold r1/r2、T2事实/T5成熟、T5/T20权限区别及旧version并发请求只接受一次。上述是设计反例，不冒充SQL事务运行测试。

PL/pgSQL解析器不支持自定义fep schema rowtype，故未将函数体执行/依赖、权限与并发标PASS；也没有在实际PostgreSQL建表。E1必须在外部设计接受后于隔离环境验证角色、FK、触发器、事务回滚、并发与故意串对象反例。代码实施、真实数据及Forward效果均NOT_VERIFIED。

## 文件身份

| 文件 | SHA256 |
|---|---|
| 修改前REV3-FEP | `93552EF08304AB7D9F841045123EDAA1A31C8847AF68D8462C211D6B385EDE5F` |
| 修改后REV4-FEP-R2 | `203FF46075B4039D1E2D45D54FD76CE09509535739CD6AAEF4DC394DE1015205` |
| FEP R2模块 | `F01AC9C550A71B8EDB73436969E39172F6809404DF9E19FFBFFF2306C9456014` |
| FEP R2 Schema | `536EE33F89E38B427B06CEFFCB5E760964B0B4B64829B2A54D91C172F252A138` |

## 复核包与下一阶段

- [更新后的主方案](<D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md>)
- [R2独立模块](<D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R2_20260930.md>)
- [R2设计SQL](<D:/Users/lps/Desktop/FEP_R2_SCHEMA_DESIGN_20260930.sql>)
- [完整外部复审包](<D:/Users/lps/Desktop/V4_2_2_FEP_R2_EXTERNAL_REAUDIT_PACKAGE_20260930.zip>)
- [内部集成复核](<E:/codex work/大A交易/docs/audits/FEP_R2_INTEGRATION_REVIEW_20260930.md>)
- [内部时序复核](<E:/codex work/大A交易/docs/audits/FEP_R2_TEMPORAL_REVIEW_20260930.md>)

ZIP包含文件清单与每文件SHA256，不含数据库、TDX数据、模型artifact或凭据。原始四份审计报告完整保留首轮发现及后续结论；新增R2报告也明确其内部复核范围，不冒充另一位外部模型的PASS。

下一阶段：将该包交线上模型进行R2定点复审；外部接受前仅继续设计修订与不受影响的V4主线。其后待V4-15接口就绪，再冻结实施参数/机器映射与正式E1任务卡。本说明不作为解除外部门的替代证据。

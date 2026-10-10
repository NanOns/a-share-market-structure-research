# Producer 外审后定点修复交付

任务依据：用户指定的修复卡与外审；BASE_SHA 经 git fetch 核实为 5f4cc15f4809ee4e50ff283ce6b92115fda9f253。
适用合同：现行 REV2/REV4、FP06、FP14、Producer R1/R2 STAGE_ENTRY 与外审修复卡。Phase 0 已有 DEGRADED_PASS 记录；本次不启动新 scanner。临时文件、pytest 与新增产物均在 G:。

P0：撤回旧正则错误归因，原四源码字节及独立输出归档；修新 V1 的复制错误。新增 V3 三值资格比较和追加研究诊断；缺 missing_state 源不再以 Lifecycle 状态当 legacy 真值。旧 A05/AST/原审计与第一次诊断保留。独立跨消费者资格审计继续 OPEN，正式 D2 不准入。

P1-02：首次源捕获标注 PRELIMINARY_PREVIOUS_HEAD_SCOPE，冻结原字节与时钟；新日 Head 建成后追加 SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1 原收据对账。不同证券全集和变更成员正例、缺源/期间变化/中断反例走 capture_daily_sources → freeze_for_review 实际调用。重试复用原收据，无旧成员暗继承。完整 source candidate 仍不等于 strict Owner 准入。未使用未来实日数据。

P1-03：新增 full_state_first_observed_v1，真实代码将完整 State 场景、事件、版本、benchmark、逐项时钟生成冻结源并连接 freeze_source_candidate → extract_candidate；prepare_capture 的独立 Writer grant 分离由端到端测试验证。缺源、missing_state、子集、迟到、截止后首获、同 revision 变更拒绝。无真实权威 State Producer，正式入组 BLOCKED。原 20896 研究场景及 eligible_at_T0=false 保留。

P1-04：当前 token 验合法研究访问，历史候选沿当前接受 Head 的 hash-linked predecessor 与固定归档验证其当日身份；按原 owners/membership 读取，不以当前 token 强行要求历史 SHA 相等。拒绝未接受、篡改、未来、旧 token、错 session；历史缺源明确降级。定点双 Head 单元测试已执行；浏览器/API 跨日实服务验收尚未完成，不能称已上线。

P2-05：28765 未重启或切换。原 28766/双尺寸截图仅支持旧工程预览。此次生产可见性与浏览器复验未完成，不签产品 PASS。若需上线，独立范围是加载这些只读候选路由、保持两个 Head、准备旧进程版本回滚并完成 API/浏览器 QA；须另获生产重启授权。Forward/FEP SOURCE_INCOMPLETE 与正式分母 null 保持。

结论：仅提交工程复验包，EXTERNAL_ACCEPTANCE_BLOCKED；不自签正式 PASS。正式 Sector D2、Cohort、FEP、FP14 各自仍 BLOCKED。原件时间不满足则降级。下一步为外部复验、实际下一交易日采集 QA 与独立权限准入。

验收证据：01 原字节/资格/追加结果；06_TEST_REEXEC 最终 JUnit 是实际非重复测试节点，早期失败文件仅为修复过程证据；05_PRODUCT_ADMISSION 核验冻结和 Head；07_GATE_MATRIX_R1.json 为范围矩阵；08 为 Git/Drive 读回。测试通过不建立正式 release readiness。

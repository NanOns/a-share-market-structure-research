# 大A V4｜下一轮精确修复任务卡 R1：真实新日身份、State可信来源、D2到期语义、范围化产品验收

- 日期：2026-10-10；最高依据：本轮独立外审《V4_NEXT_STAGE_A_E_INDEPENDENT_AUDIT_R1_20261010.md》、最新V4.2.2 REV4、`AGENTS.md`、原A～E总调度。
- BASE_HEAD：`d7b19feabc8e17ca4948bfdef38047f10fd6f97c`，Codex启动先`git fetch`并读取remote最新；不得覆盖后继提交。
- 当前最后实际交易日：2026-10-09；预计下一实际交易日2026-10-12；首次实际调度18:35北京时，按已有19:05/19:35/20:05/20:35/21:05/22:05执行。**周末只做工程和合成演练，不伪造10/12观测。**
- 必守：受保护运营Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`、严格Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`在本轮不变；D:/new_tdx只读；所有临时/Git checkout/test放G盘；**无用户新增生产28765重启授权、无正式权限签发授权**。

## P0-1｜修真实新日Identity Owner源和主DD闸分类（第一优先）

1. 基于真实`verify_source_gate`的原TDX/BaoStock数值/日期/身份对照，把`NATIVE_PROVIDERS_RECONCILED`与`PREVIOUS_HEAD_IDENTITY_SCOPE_MISMATCH`单独记录为不可混淆的事实层；当前BaoStock原始真实校验通过而与旧Pool不符时不得仅报 `WAIT_BAOSTOCK_DAILY`。保留来源原字节、两个集合、目标日期、请求/接收时间、旧Head SHA。
2. 新增版本化**同日Identity Authority候选生产和独立准入**，输入包括新日证券列表、TDX源身份/GBBQ、BaoStock相符原件、Listing/Dlisting/重命名时态、同日成员版本和观察时钟。生产候选不能直接被普通caller假授权；如果无法从已存在源建立某种身份事实，保留精确UNKNOWN而不是猜测。
3. 新合法来源经**独立审查及原子发布合同**准入后方可让当前日身份池参与主DD校验。若本轮不具备正式准入，旧保护门保持不变，同时诊断 `WAIT_DATED_IDENTITY_AUTHORITY` 并保留last-good；不允许改一条条件把所有新增代码自动放过，也不让一处缺源阻断其他独立研究域。
4. 跨日两Head实际函数演练：正常同范围、新证券、退市、改代码、停牌、成员增删/异版本、TDX/BaoStock矛盾、包缺行、合规同日、非法回建、重试、CAS失败及回滚。断言候选原件可保存、原式strict主体不降级、只有合法同日身份证明才能进入Owner。
5. **收尾必须给唯一`REAL_T0_READY`或`WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER`和可运行10/12手册。** 凭证源从未发生的事项才留实时待验证，不应把工程接口也列为无限等待。

验收：代码和独立差异Oracles能证明“provider正常但旧池改变”不会再被静默当作BaoStock挂掉；旧正式授权仍fail-closed；新日身份准入机制受来源与身份合同约束。产物：`B_IDENTITY_AUTHORITY_PRODUCER.md`、`B_GATE_REASON_CONTRACT_R2.json`、`B_IDENTITY_CROSS_DAY_ORACLE.json`、定点JUnit。

## P0-2｜State Source Review 的真实可信边界；保留现有Bridge

1. 不重写既有 `state_publisher_bridge_v1.py` 合成成功通道。对其`reviewer_role/decision` 声明做显式安全隔离：调用者能创建的文件、普通Head、合成fixture和Git evidence无权单独签 `STATE_SOURCE_ADMITTED`。新建独立可信源解析器的正反例、签发身份/范围/有效期/撤销/原件版本/原始来源实际时钟/Head-CAS绑定；所需真实审查服务若不存在，落成可检查合同与`UNTRUSTED_REVIEW_CANDIDATE`，不得冒充已部署production adapter。
2. 做一份精确的 `STATE_REAL_SOURCE_REQUIREMENTS.json`：State/Membership/Model/Episode Event/Benchmark各自Owner、可获取的真源、最早合法观察时点、未到齐字段、何时必须`SOURCE_GAPS`；10/09研究重建和synthetic 记录保持隔离。
3. 加独立负例：**同源工作区伪造reviewer_role**、伪造grant、错时钟、不同revision、Member旧日标签冒用、没有合法Episode、仅有Focus Top-K、错误benchmark来源、已接受Head CAS不一致。必须证明这些均不能打开正式Cohort。
4. 新日合法源发生后再按具体日期审核；本轮可验收的是**可信接口设计及fail-closed工程**，不是凭空创建过去first-available或真实行政审批。

验收：Bridge可消费**确实由可信已接受Review源提供**的绑定；缺该源返回`NOT_ADMITTED`；合成fixture保持工程测试身份，任何生产grant仍为FALSE。产物：`A_TRUSTED_REVIEW_BOUNDARY.md`、`A_AUTHORITY_NEGATIVE_ORACLE.json`、最小源码/tests。

## P1-3｜D2 Episode `PENDING`和`UNKNOWN`分类修补

检查`episode_genesis_candidate_v2.observe`：子horizon结果已有`PENDING/COMPLETE/UNKNOWN`，但`followup_complete`尚不能区别全部未到期与到期后缺Source。**先核对原冻结D2字段布尔/三值合同**，保留`followup_complete`合法类型，新添`followup_status/next_due_date/unknown_due_reasons`等明示分类；切勿将未到期计为失败或成熟。补单一和混合horizon、悬停/退市、来源迟到、日历断档、旧事件无合法Owner的负例；历史Genesis不可回填为实时。产物：`C_FOLLOWUP_SEMANTICS_R2.md`、源码及pytest/前端接口抽样。

## P1-4｜FP13 范围化研究功能验收，不被浏览器环境无限阻塞

1. 现有68真实HTTP和5JS测试保留，按市场/股票/板块/Focus/诊断/真实Chart/历史阅读等**合法已上线只读scope**申请独立范围化签收；业务 `SOURCE_INCOMPLETE` 不算READY，正确保留Forward/FEP/严格回放未开放。
2. 解决1366/1920本机浏览器执行环境：首选用户实际Windows浏览器/本机真实工作台，以DOM、图片、Console、请求日志验证日期回切/搜索/第二页/组件错误隔离/触摸禁用旧token；如IAB仍被限制，只记录**一次明确的BLOCKED_BROWSER_ENV**，附可复现操作清单并停止无效重复尝试；独立功能开发不停工。
3. 控制研究候选页面清楚区分`RECONSTRUCTED_RESEARCH_ONLY`、真实当前首次观察、源截止日、候选冻结时、源再观察时；不把300 TRUE、79研究CONFIRMED当成正式Cohort或成熟Forward。
4. 本轮不重启28765，不偷签FP14_FULL。可提交独立范围化 `FP13_RESEARCH_READ_SCOPE_PENDING_EXTERNAL_SIGNOFF`；完整功能另分模块债务。

产物：`D_BROWSER_ENV_EXIT_PLAN.md`、`D_RESEARCH_SCOPE_ACCEPTANCE_MATRIX.md`、真实/缺失领域图文回读，或一份精确环境阻断清单。

## P2-5｜FEP维持正确关闭 + 最小准备

FEP不作为主线P0。仅复用现有E_HOLD文件，当前无真Model Registry/PIT Source Owner/成熟FIT labels/独立Grant，则六预测字段`SOURCE_INCOMPLETE/null`，不重跑同质失败检查，不出5日收益预测，不计算虚假胜率。

## 门禁与统一收尾

- 任务执行时核验`AGENTS.md` Phase0门和最新base；开发方出源码、可重复单测、独立oracle、当前两个Head before/after、Git commit/远端SHA及QA证据，禁止只写报告；MD和轻证据同轮自动Drive归档并验证原始SHA。
- **分域状态**：`OPERATIONS_READ_SCOPED`、`IDENTITY_AUTHORITY_ENGINEERING`、`STATE_REVIEW_TRUST_BOUNDARY`、`D2_EPISODE_ENGINEERING`、`FP13_BROWSER_SCOPE`、`REAL_FIRST_CAPTURE_PENDING`、`FORMAL_COHORT_NOT_GRANTED`、`FEP_HOLD`、`FP14_FULL_NOT_GRANTED`。不能用一个`BLOCKED`覆盖全部。
- 真实10/12 18:35后单独执行Source/Identity/Member/GBBQ/State/Episode和CAS现场QA。涉及生产28765停止/重启、改真实准入源或签Writer Grant必须先有**用户明确范围授权和独立验收**，本卡不授予此类操作。
- 失败不为制造PASS改旧Head、删日志、清异常样本或把2026-10-10周末合成时钟改写为10/12真实观察。

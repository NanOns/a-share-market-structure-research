# 大A V4｜Producer Precision R3 独立外审与正式能力未开放原因 R1

- 日期：2026-10-10（北京时间），最后可观测工作日T0：2026-10-09。
- 项目：`NanOns/a-share-market-structure-research`，分支 `codex/v4-fp14-r2-repair`。
- 冻结 Git HEAD：`3356e833fcf604c36db0cd856a8e31ed91fc8472`；上轮冻结：`5f4cc15f4809ee4e50ff283ce6b92115fda9f253`；ahead 6。
- 最新开发方现场生产加载提交：`0c9305129cfe90148008d898162f0f40959d1af5`，PID 42552，端口127.0.0.1:28765。该加载提交到冻结Git HEAD后两次提交无 `src/config/scripts/tests` 源码变化；不能据此断言本机进程此刻依然存活。
- 运营 Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；严格 PIT Head SHA：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`；开发方前后回读一致。
- **唯一全局正式裁决：`EXTERNAL_ACCEPTANCE_BLOCKED`；本轮代码/页面结论：`PASS_SCOPED_ENGINEERING_AND_PRODUCTION_RESEARCH_READ`，需独立范围化签收；正式 Sector D2、Cohort、FEP 仍各自 `NOT_GRANTED`。**

## 一、本轮任务执行核查

比较远端代码和仓库实际文件，确认已新增/修改：

1. `src/sector/operational_candidate_v1.py` 修复新适配器多余转义，`valid_member_qualification_v3.py` 和 `operational_candidate_v3.py` 引入三值来源口径，明确撤回“旧 phase2/A05 正则错误”的错误归因。原 `phase2.py` 与 `legacy_valid_member_a05_v1.py` 使用的单转义正则本来正确；旧 `missing_state` 业务语义不能用新 Lifecycle status 无条件替代。新 V3 只在研究诊断域，未改冻结 A05 / AST。
2. 新增 `source_scope_reconciliation_v1.py`；`source_capture_candidate_v1.py` 支持 `PRELIMINARY_PREVIOUS_HEAD_SCOPE`，DD `execute_sources` 在 readiness 门前冻结真实可得原字节，后续同日新 Owner 创建后对账当日成员/证券范围。跨日新增/移除、失败和重试已在隔离测试覆盖；下一真实T0尚未现场验证。
3. 新增 `full_state_first_observed_v1.py` 把外部**已经存在且完整**的 `FULL_MARKET_STATE_PRODUCER_OUTPUT_V1`、as-recorded成员与model版本接入 `freeze_source_candidate` 和 `extract_candidate`。这是真正的接入/提取实现，但**不是当日权威 State 生产者本身**：输入必须由另一条合法的、当时观察的上游发行。本代码不签发 Source Owner、Writer grant，也不写正式Cohort。
4. `candidate_research_read_v2.py` / `producer_dependency_archive_v1.py` 支持旧日期获接受Head链和严格SHA计算依赖原字节回读，补充分离的旧 token/篡改/未接受/缺源测试。真实未来D0→D1的独立日期仍待真实新日。
5. 生产 PID 42552 读取收据：10/09板块候选AVAILABLE、Cohort研究候选RESEARCH_CANDIDATE_FROZEN，5,224证券/20,896场景/300研究TRUE；10/08候选无当时原件为NOT_CAPTURED，股票10/08可读，10/12未经接受为HTTP400，旧token 409。两视口Focus、板块、历史股票分页DOM有开发方留档。此轮是用户授权的实际工作台重启；不是全FP14签收。

**证据限制**：以上生产HTTP、浏览器和147项回归由Codex的归档收据支持，本审计通过远端SHA、源码、报告对照确认，**没有亲自访问Windows本机28765或独立重跑所有pytest/当日全量数值**。故判PASS_SCOPED_EVIDENCE_READY，不伪造“独立现场全项PASS”。

## 二、为什么“权威State、正式D2/Cohort/FEP”仍未开放？

严格区分四层：`研究候选产生` → `指定T0当时真实原始信息和计算原件冻结` → `独立接纳来源/算法/Owner` → `正式权限/消费者启用`。前面的产物不自动证明后面的事实。

| 能力 | 已有的真实工程 | 真正缺少的来源和正式门 | 谁补/何时可补 | 开门后准确授权范围 |
|---|---|---|---|---|
| **权威 State** | 5,224股票×4场景的研究候选及冻结接口；接收 `FULL_MARKET_STATE_PRODUCER_OUTPUT_V1` 的适配器 | 有合法新T0 first-available 的**全市场权威State原始生产输出**，其源Owner/成员/窗口/算法版本、场景入选和排除、Episode/Event、benchmark、实际冻结时钟；10/09复算被明确标 RECONSTRUCTED；当前运营Owner仍 `AS_RECORDED=false/PIT_ELIGIBLE=false` | Codex现在能完成原始State Producer的实际发布实现及隔离测试；首份真实当日原件须交易日到来后实际获取，审源通过才能授予正式身份 | 先可获 `STATE_SOURCE_ADMITTED`，不等于 Cohort写入权 |
| **Sector D2** | 400板块的Native/运营研究数值，R5 AST研究候选，WARM/CONFIRMED诊断和Episode候选函数 | 精确原板块member及A05 valid-member来源、当日q20/dq5_3和SETUP/RECOVERY、原Episode Genesis及冻结失效合同、due/settlement、scenario等六字段真源；新V3三值资格仍需独立比较真实legacy missing_state；9/24 A05范围不可扩写到10/09 | Codex继续建设合法新T0各Producer并附可重放数值；独立审核算法/来源/时间/成员后，只批准合格字段与范围，未生成Episode/到期项保持NO_PRIOR_EPISODE/PENDING/UNKNOWN | `SECTOR_D2_FORMAL_OWNER_PASS` 是正式生命周期读的门；研究候选可单独准入而不等待它 |
| **Cohort** | `freeze_source_candidate → extract_candidate → prepare_capture`，完整研究候选但 `eligible_at_T0=false`、`observed_count=null`；新权威State**输入适配器** | 独立接受的 **State Owner**及完整 eligible/ineligible 原始ledger、first-available、事件身份、benchmark、不可变收据；还需独立 Validation Cohort Owner 与**按日期/版本绑定的Writer grant**，经正式CAS；旧2290事后筛选事件不能回填 | Codex现在补真正State发布代码/测试与Source/Writer接口；新实际T0产生首获记录，独立审源后按已接受版本授予写权限。不是用户提供密码或每次手工产生SHA | `COHORT_REAL_ENROLLMENT_PASS`：仅合法新日首获信号可入组；T+1/3/5到期后才能做结算统计，不承诺马上有胜率 |
| **FEP** | 工程模型、隔离PG只读解析与 fail-closed gate；工作台明确 SOURCE_INCOMPLETE | 正式生产Model Registry的已接纳revision/CHAMPION、模型适用scope/target/horizon/capability、正式DB Owner及Head/CAS、当前独立approval和授权时间窗、as-recorded预测输入和实际成熟FIT训练标签、不可变prediction Owner、六字段ready。**源码当前current_gate也尚无可信源获批后自动正向开门的生产接线** | 可立即准备可信Authority注册/独立验收和Shadow模型校验，但如无实际成熟数据与来源，不能把候选授权当正式预测。先不阻塞股票/板块/Cohort开发 | `FEP_PRODUCTION_AUTHORIZED`：严格到单模型版本、特定目标/期限/能力；不能使用口头“一键全部开” |

### 关于“凭证”和批准权限的边界

1. **SHA不是资格证书**：文件哈希只能证明字节没有变化；不能自动证明原始事实真实、在T0前就存在或算法被正式接受。
2. **用户可以授权**研发、只读预览、范围化生产加载及风险受控发布；不能通过口头授权创造过去未冻结的历史资料或已成熟训练标签。
3. **独立批准可以设计为有范围的一次性生产合同准入和自动执行的日更门**，不必每个新交易日都停下来等人工逐字段签字；但首次源码/数据合同、权限边界需要外审，运行中新T0必须按合同生成真实可追溯收据。
4. **不要求所有项目同日一起PASS**。现有研究页面和日更可范围化上线；真实FEP、严格Amount H21历史、长期T+5统计不应挡住可用研究域。

## 三、下一个真实交易日到来之前，还能做什么

**最高优先，不用等待新行情：**

- P0-A：实现真正的 `FULL_MARKET_STATE_PRODUCER_OUTPUT_V1` 上游发行者，将现有完整全市场State计算结果的独立输入、逐场景资格、基准、Episode/Event、member_version、不可变SHA和真实冻结时钟写成隔离候选。现有 `full_state_first_observed_v1.py` **只会读取它，不能凭空产生它**；不得沿用历史复算资格。
- P0-B：将板块三值有效成员资格与旧 `missing_state`、normal/sector_valid定义做真实小样本数值黄金对照，逐字段来源入场判断。TRUE/FALSE/UNKNOWN不能把缺数据记FALSE，也不能将10/09回放79 TRUE提升为正式历史。
- P0-C：将「源捕获→新日新Lifecycle/成员→same-day reconcile→State/sector候选→检查旧Head不变→失败后可重试」做隔离**全流程桌面演练**；注入新上市、退出、停牌、成员变更，缺原件按SOURCE_GAPS。捕获前后Head不能借用另一日身份。
- P1-D：为已经上线的10/09候选研究做独立源码/HTTP/DOM范围化回读；针对10/08缺源、历史分页、错误token、未经接受10/12、Source SHA失效进行反例审查，形成可维护的已验收研究产品范围。真实未来D1切换仍要等新日。
- P1-E：FEP只补可信Authority从合规真实Source Owner到精确范围准入的**工程接线和负例**，不试图在没有真实成熟数据前启用生产预测。补FP14可独立的生产回滚演练，不以FEP等待拒绝研究域。

**真实下一个交易日（预计2026-10-12）才允许做：**盘后实际获得BaoStock/TDX/同日成员原字节，逐项保存 `requested_at/received_at/first_available/captured_at`，按真实Source cutoff对应PIT，而不是把盘后18:35抓到的信息写成当天15:00已知；执行当日scope对账和所有场景冻结，再审新T0合法Source/Owner。次日上线后的跨Head真正回读以及T+1/3/5结果到期，必须分别追加验证。

## 四、重点进一步风险与审计裁决

- 当前独立源证实**程序执行链仍是候选源而非正式源**；正式D2/Cohort/FEP缺门的报告属实，但不能被用作Codex停工理由。
- `src/workbench_analysis/full_state_first_observed_v1.py` 只检查输入自己声明 `PIT_OBSERVED` 等标签及来源哈希并输出隔离候选，**不是独立签名的权威数据生产事实**；下一步不可拿其工程可运行结果直接签真实入组。
- `src/workbench_analysis/fep_e5/admission.py::current_gate` 目前从历史工程model加载，`evaluate`固定fail-closed；即便新增Source也不会自动获得正式模型正向授权。生产接线必须另做可信决策器审计，不能用caller dict替代。
- 生效生产进程相对Git HEAD仅证据变化，无业务源码差异；生产HTTP 200和页面截图证明用户研究阅读工程状态，不证明三个正式消费者已经READY。

## 五、独立外审唯一结论

- `PROD_RESEARCH_READER = PASS_SCOPED_EVIDENCE_READY`
- `PRODUCER_CROSS_DAY_CAPTURE = PASS_SCOPED_SYNTHETIC; ACTUAL_NEW_T0_PENDING`
- `STATE_FIRST_OBSERVED_ADAPTER = PASS_SCOPED_CANDIDATE; ACTUAL_AUTHORITATIVE_PRODUCER_MISSING`
- `SECTOR_DIAGNOSTIC = PASS_SCOPED_RESEARCH; FORMAL_D2 = BLOCKED`
- `COHORT_REAL_ENROLLMENT = BLOCKED`
- `FEP_PRODUCTION_AUTHORIZED = BLOCKED`
- `FP14_FULL_RELEASE = EXTERNAL_ACCEPTANCE_BLOCKED`

**下一任务不应再发“搜索Owner凭证”的同质报告**：现在主动开发上游正式Producer，在历史隔离样本测试后，等待真实新T0的首次原始观察，再做逐能力独立准入。对无法追溯证明的旧历史以NOT_VERIFIABLE收尾。

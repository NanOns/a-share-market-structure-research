# 大A V4｜整体进度外审后·下一轮工程总调度与任务卡 R1

- 日期：2026-10-10，周六；当前最后真实T0=2026-10-09，下一合法实际T0预计2026-10-12。
- 唯一审计依据：《V4_OVERALL_PROGRESS_INDEPENDENT_AUDIT_R1_20261010.md》、V4.2.2最新执行合同第78节、AGENTS.md，以及 GitHub 本轮 `pre_next_t0_execution_r1` 产物。
- 基准远端HEAD：`c0b9903fe596c1884c04f5529d6699034548850e`；**执行前先fetch并记录新的exact_BASE，不覆盖当前后继提交。**
- 受保护运营Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`、严格Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`；原来的Head在当前演练不可更改。
- 目录约束：`D:/new_tdx`只读、所有临时和测试在`G:/codex_tmp`，工作目录`G:/codex work/大A交易`。稳定28765现状保留，**无新增生产重启/用户权限授权**，禁止授权代码自己签外部PASS。
- **总目标**：把工程已经完成的状态如实结案；聚焦一个真实上游来源→State/板块→首次冻结→准入的可执行闭环。既有研究产品继续显示，不用等成熟FEP或20个交易日才进行前端/基础工程。

## TASK 0（P0，开工只读，禁止重复堆证据）｜单一能力门账本与新HEAD差异

- 从本卡BASE到最新 remote `git diff --name-status`，只修变更影响的源码、输出与测试。读取 `final/STATE_PUBLISHER_ISOLATED_RUN.json`，后续使用 final 目录覆盖先前同轮 provisional readback；原版永不删除。
- 导出**一张**状态表，列 `OPERATIONS_CURRENT`、`STATE_PUBLISHER_RESEARCH`、`STATE_SOURCE_PIT`、`D2_RESEARCH`、`D2_FORMAL`、`COHORT_CAPTURE/ENROLLMENT`、`FEP_SHADOW/PRODUCTION`、`FP13_READ_QA`、`FP14_FULL`，每行出owner、exact source、代码、阻断、next action、是否涉及真实未来日期。
- **PASS**：不把 `TRUE=300` 说成已正式300次交易，不把10/09事后重建说成第一手观察，不把200 pytest称正式样本。

## TASK A（P0，立刻开发）｜State Publisher→FirstObserved 的真正合同闭环

1. 先编写 `STATE_PUBLISHER_TO_FIRST_OBSERVED_FIELD_DIFF.md`，以**源码实际schema**列完整差异：Publisher输出为gzip原件，`RECONSTRUCTED_RESEARCH_ONLY / OBSERVED_SOURCE_CANDIDATE`，model无`first_available/frozen_at`，State缺完整`state_lineage_id/frozen_signal_version/capture_deadline`，每行`episode_id/event_type/benchmark=null`，eligible_at_T0=false；`freeze_first_observed`要求`PIT_OBSERVED` + true as-recorded membership + model/State合法first_available/frozen_at + event/benchmark完整。
2. 查V4-15现有`STATE_EVENT`、`COHORT`、`FORWARD_MARKET_BENCHMARK`、`FORWARD_SECTOR_BENCHMARK`和Episode Owner/生成函数，明确哪些字段有现成权威Publisher可以复用，哪些确实`SOURCE_PRODUCER_NOT_IMPLEMENTED`。给每一字段 `owner/binding/version/date/cutoff`，**不编造事件、benchmark或填`NOT_APPLICABLE`替代正式必需原件**。
3. 实现版本化受控**候选形态**适配器：直接从当前真实Publisher源及已冻结原件生成first-observed所需原始出版接口；若缺Event/Benchmark及合法PIT不可升级，输出`SOURCE_GAPS`和逐字段事实，并保留未授权的完整研究输出。不能靠自称`PIT_OBSERVED`或自行生成Granted签名。仅成功来源才能进入隔离`freeze_first_observed→freeze_source_candidate→extract_candidate→prepare_capture`的精确正向夹具。
4. 用固定**两组**隔离E2E夹具：正向（所有真实逻辑产生的字段/带合成明确标记的测试原件）→producer→quarantine→firstobserved→完整eligibility ledger→独立GRANT preflight；反向：历史corrected、首次时钟晚、假current会员、缺event、缺benchmark、打乱相同revision、只有Focus Top-K、未来日期、错误Owner SHA、变化成员。安全日志记录测试成功不代表生产授权。
5. 真实10/09 5,224×4隔离原件不重算无必要。特别对300 TRUE随机与固定抽样进行**原AST + 原target_values的小型数值独立oracle**，校验本轮200项测试并未全部独立验证算法含义。
- **交付**：`A_SCHEMA_DIFF.md`、`A_SOURCE_OWNER_MAP.json`、`A_STATE_PUBLISHER_BRIDGE_IMPLEMENTATION.md`、最小源码+pytest/JUnit、正负夹具绑定SHA、`A_FORMAL_GATE_DISPOSITION.json`。
- **工程PASS**：接口/字段可到达、负例fail-closed、历史身份不升级，现有DD受限运营继续可用。正式 Cohort 仍需真实当日首获与独立Grant。

## TASK B（P0，立刻开发）｜下一T0第一次真实采集“上线前”硬件/代码预检

1. 从现有`DailyJobs→execute_sources→source_capture→candidate build/seal→SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1→Publisher→Scope Admission`的真实函数调用层，继续使用隔离两HEAD/二个成员版本测试，补全**源未齐但已经取得的原始字节必须留下**、首次可用与received时钟、源日期/Identity/TDX GBBQ与BaoStock同日对账。
2. **P0关注点**：`verify_source_gate`仍依赖 previous accepted Head的`life.identity`/expected_codes校验实际当天BaoStock全集。遇新上市/换代码/成员新增时，保留新当天原始输入，但要清楚分开“主DD事实闸是否还依赖旧身份”及“候选补录”。在独立合同批准前不可放开原闸，只生成具体失配诊断与**合法新日期Identity authority候选**，让下轮可由真实原件验收；不要因旧pool误报BaoStock本身不可用。
3. 写10/12 runtime checklist：18:35首次尝试、19:05/19:35/20:05/20:35/21:05/22:05重试，Source(期望/实际), source requests/receipts, old/new Head, owners, `prior membership`, candidate clock, PIT eligibility逐字段读取。现场的真实成功/失败必须等10/12，不允许改系统时间伪造。
4. 为可能的生产Python模块加载改动生成 `B_SAFE_SCOPE_DEPLOYMENT_PLAN.md`，包括PID/端口检查、code SHA、no active job、当前两个Head备份路径、失败回滚；**不能擅自重启稳定28765**，未授权就用隔离端口预检。
- **交付**：`B_NEXT_T0_RUNTIME_PREFLIGHT.md`、`B_OLD_HEAD_NEW_IDENTITY_NEGATIVES.json`、`B_T0_CAPTURE_RUNBOOK.md`、最小测试/JUnit、需用户许可事项。

## TASK C（P1，不等行情）｜正式D2：六项生产字段的真实起点和可靠研究呈现

- 对照已冻结R5 AST/A05 9/24 golden，编写 `C_D2_SOURCE_AND_EPISODE_GENESIS_MAP.json`，逐项列 CONFIRMED、WARM、frozen_invalidation、contract ID、followup_complete、scenario 的Producer代码、具体原件、合法出生时间、下一次可获取时点及允许的状态。
- 研究TRUE/FALSE/UNKNOWN只出在 research consumer；9/24黄金不允许自动开放10/09正式入场；原missing_state缺源标UNKNOWN，不当FALSE。
- 为**未来真实Episode**实现Creation-bound成员+失效条件+scenario priority+due plan的端到端**隔离正负例**，支持无先前Episode的`NO_PRIOR_EPISODE`、未成熟`PENDING`、到期缺settlement`UNKNOWN`。有合法原件之前不能自建“当时已经成立”的Episode。
- 校验rank/q20、dq5_3、非Amount分支独立来源；Amount H21缺20历史天时不拖累Native业务。
- **交付**：`C_D2_FORMAL_VS_RESEARCH_ADMISSION.md`、可运行最小生产接口+测例；正式D2仅在具体字段/源审完后局部申请。

## TASK D（P1，可与A/B/C并行）｜FP13已投产研究读域与缺失功能产品清单

- 真实28765**只读**QA：六主入口、板块/股票/Focus/市场/诊断、历史页面、股票日周月K、搜索、变化量/关注路径、Forward缺源、日期切换；分别记录**事实数据可读**与`SOURCE_INCOMPLETE`字段；HTTP200不代表计算READY。
- 两视口至少1366与1920；当前业务现有产品、组件失败隔离/503受控重试、错误token409、未来日期400、跨日回放、来源展示时钟、不允许把研究300或79写成正式成熟度。
- FP13合同按现有**独立能通过的范围**提交矩阵；FP14只准备受限研究范围的发布/回滚合同，不能自行放宽正式全量门。
- **交付**：`D_PRODUCT_SCOPE_MATRIX.md`、`D_CURRENT_UI_SEMANTIC_QA.md`、轻量DOM/截屏/请求回执、剩余业务功能列表；缺Owner的已知问题不反复让全页面UNKNOWN。

## TASK E（P2，资源受限）｜FEP与长样本统计保留正确“关闭”并独立工程推进

- 当前FEP source/authority确实未具备：`current_gate`仍fail-closed、没有Accepted Model Registry / as-recorded prediction / matured FIT /独立有效grant，六字段null。**停止重复跑300个只读权限检查。**
- 如果需要工程推进，限定在可信registry/Head/CAS/Owner生产适配器的**隔离正反例**、shadow baseline质量检测。E3/E4模型可选，不成为Core Shadow、FP13研究读域前置。
- Cohort在第一真实T0可合法冻结后，每日继续T+1/T+3/T+5到期填充；未成熟不给胜率、不要靠历史Focus样本凑数。
- **交付**：仅一页`E_HOLD_AND_ADMISSION_REQUIREMENTS.md`，除非A/B/C里已有获准真源，不新发宏大的FEP版本。

## 验收分层、时间安排与Codex的结束条件

**10/10–10/11（市场休市）**：TASK A+B为P0，C+D并行，E低优先。可演练模拟真实程序函数但任何“10/12已首次观察”必须FAIL。已受保护Owner与现实生产一律不改。

**10/12（真实交易日收盘后约18:35起）**：由原DailyJobs实际采集并保留首获SHA/时钟；用新日Owner进行same-day universe/member对账；保证现有main DD能独立完成或明确源阻断并保留last-good。将新的当前T0 State/sector Source按各字段事实判 `CURRENT_OBSERVED_CANDIDATE`或`SOURCE_GAPS`。允许对可核实的新T0逐权限外审，**并不要求首日就有成熟T+5**。

**之后1–5个合法会话**：Cohort首次正式冻结来源/独立Grant若签出则开始向前结算；板块Episode有真Genesis后开始到期追踪；修UI持续观察/变化显示。第21个严格连续新样本可重新评估未来Amount H21窗口，不能推导旧9月窗口为合法。

**分层正式门**：`ENG_PRODUCER_READY` → `REAL_FIRST_CAPTURE_SOURCE_REVIEWED` → `STATE_SOURCE_ADMITTED` → `COHORT_WRITE_GRANT_SCOPED` / `SECTOR_D2_FIELD_ADMITTED` → `FP13_PRODUCT_SCOPE_SIGNOFF` → `FP14_RELEASE_SCOPE_SIGNOFF`。`FEP_PRODUCTION_AUTHORIZED`为后续独立支线。所有首获的源证据采用不可变原件，单字段不合格不阻塞无关scope。

**闭环要求**：实际代码/最小可复现oracle、源身份/hash、`no past backfill`负例、状态账本、受保护Head前后比对、remote Git HEAD读回、正式MD及轻量证据同步Drive并读取云端字节SHA。Codex只允许请求独立审计，不自签EXTERNAL_ACCEPTANCE_PASS。若工程已达到本轮PASS_SCOPED但真源尚未发生，以明确PENDING和下一交易日现场计划收尾，禁止无限继续生成SOURCE_NOT_PRESENT清单。

### 直接交给Codex的最简调度文本

> 按本卡执行，在真实下一个交易日之前优先完成State Publisher→FirstObserved合同级桥接、旧Head→新日源/身份/成员预检和真实日更运行手册；并行补未来D2 Episode六字段上游及已投产研究读域的独立QA。严格使用现有Source Owner、冻结AST和V4-15原结算，不得将研究候选冒充正式Cohort或FEP，不得修改过去first_available，不得擅自重启28765。完成可运行源码、定点反例、原件SHA、Git与Drive读回后申请外审；正式新T0首获、授权与成熟统计另行判定。

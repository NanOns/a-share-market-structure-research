# 大A V4｜最新整体项目进度独立审计 R1

- 审计时间：2026-10-10（Asia/Shanghai，周六）
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-fp14-r2-repair`
- **冻结远端 HEAD**：`c0b9903fe596c1884c04f5529d6699034548850e`
- 前轮基线：`3356e833fcf604c36db0cd856a8e31ed91fc8472`。GitHub 比较：**ahead=2，behind=0**；含新的 State Publisher / D2 Oracle / 控制链预演和证据。
- 最新可复核运营数据 T0：**2026-10-09**。
- 受保护运营 Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`。
- 严格数据/PIT Head SHA：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。
- 最新生产服务证据：`127.0.0.1:28765`、PID 42552、源码加载提交 `0c9305129cfe90148008d898162f0f40959d1af5`；本轮新远端提交明确包含新增Python Publisher、State/D2源码及候选展示修改，**当前生产进程未加载本轮新 Python Publisher/新的时间展示字段**。
- **总裁决：`V4_FULL_EXTERNAL_ACCEPTANCE_BLOCKED`；`CORE_OPERATIONS_AND_RESEARCH_DISPLAY_PASS_SCOPED_EVIDENCE_READY`；`STATE_PUBLISHER_ENGINEERING_PASS_SCOPED`；`V4_16_REAL_SHADOW / FORMAL_D2 / COHORT / FEP / FP14`仍分别未准入。**

## 1. 来源及验证边界

先同步当前 Drive《V4_PRE_NEXT_T0_EXECUTION_RESULT_20261010.md》（file ID `1xLDYzTQJI0UZpiFtFdYM8ikWcEBBbh0u`），再依据 GitHub `compare_commits`、AGENTS.md、仓库正式 V4.2.2 合同第78节的阶段定义、最新新增源码、测试源码与 `docs/evidence/pre_next_t0_execution_r1_20261010/` 的 final 证据回读。历史阶段参考 `r18`、`r20/r21/r22`、`r23/r24`、`r30/r31r2`及 `fp13/fp14` 的原独立验收结论。

本审计者**实际检查**远端源码和结果结构，但**没有亲自在用户 Windows/G 盘运行 200 个 pytest、控制 localhost 浏览器、重算压缩的 20,896 条全量原件或执行10/12未来真实行情**。200 PASS、前后台 HTTP、生产 PID 与真实浏览器画面属于可核对的**开发者冻结现场证据**，不能提升为外审者现场全量独立实测；对没有证据的历史阶段不补造 PASS。

## 2. 当前成果实况

| 主链 | 可支持的事实 | 审计等级 | 未完成事项 |
|---|---|---|---|
| 历史/RAW、日周月、基本 Core | V4 前段已有逐阶段接受产物；10/09 当前运营 Head 真实可读，BaoStock/TDX 当前日源与补充数值原件已核对 | **历史分范围工程通过；运营数据受限发布** | 旧历史严格 PIT 身份不因后续最新成员回算而变真，Amount H21 9月20日缺首次成员原件 |
| 自动日更 | `DailyJobs` AUTO_ON、上轮的10/09 accepted Head 和 next_trigger 10/12 18:35；源码的 source readiness、失败重试、原子Head和last-good存在 | **已实际运行到10/09；新 Producer 旁路只在隔离预演** | 10/12实际源获取、范围对账、发布/CAS/异常恢复需要真实日校验 |
| State Publisher | 新 `full_market_state_publisher_v1.py::build` 对每只股票调用冻结 confirmation，非复制缓存状态；历史10/09输出 5,224×4=20,896；TRUE=300、FALSE=10,046、UNKNOWN=10,550；完整原件 gzip+SHA、quarantine | **工程范围化通过** | 原始State的first_available=null、所有 eligible_at_T0=false；Episode/event/benchmark 尚无权威来源；正式 Source Owner 不可开门 |
| 板块 Native/Rotation/D2 | 400板块当前研究数值；`phase2/A05`旧正则正确，9/24 golden 3,553成员、6,188资格观察、541板块值据开发侧0差异；研究CONFIRMED/WARM可算 | **研究范围可用，正式D2未授权** | 10/09原始 missing_state、正式六字段/首个Episode/真实成熟跟踪及A05日期授权未闭环 |
| 股票、板块、Focus、市场、诊断及研究页面 | 生产28765六入口、10/09候选、10/08缺源、10/12未经接纳拒绝、旧token 409及浏览器记录；新FEP/Forward缺源不阻塞主营读域 | **生产研究读取范围化证据就绪** | 全FP13矩阵/FP14整体发布仍未正式通过；本轮新 Python时间字段未载入 |
| Validation Cohort | 当前完整研究场景及 first-observed adapter、`freeze→extract→prepare` 合法/非法输入测试 | **工程候选通过；真实入组仍为零个获准来源，正式观察分母null** | 真实当天权威State、来源/模型/成员/事件/benchmark、独立Owner/Write Grant、首次冻结/到期结算 |
| FEP | 工程模型、canonical PG只读查询、权限负例和迁移合同；当前六字段SOURCE_INCOMPLETE、生产授权False | **工程准备就绪，生产关闭正确** | 正式Model Registry/Champion/成熟FIT、as-of Prediction Owner、独立approval/精确Grant、生产可信决策器连接 |
| Forward/长样本 | V4-15 runtime/Head 曾范围化通过，时序/结算工程存在 | **历史工程能力存在，真实独立样本成熟度尚缺** | 从未来合法T0自动积累T+1/T+3/T+5，不将Focus筛选/重建历史作为成功样本 |

特别区分：**200项回归是工程回归，不是200个交易样本；300条TRUE是股票×场景中的研究标签，不是300次提前捕捉成功。**

## 3. V4-00～V4-22 统一阶段定位（根据第78节现行单一阶段表）

以下是**工程范围与现有授权的定位**，不是以报告文件数量直接得出“X/22全通过”。旧阶段是否已正式验收应以各阶段单独Accepted Head/独立终审为准。

| 合同阶段 | 原定义 | 当前合理定位 |
|---|---|---|
| 00（A-H） | 基准/数据契约/发布与能力门 | 基础合同已有；历史局部PIT资料仍保持限制 |
| 01 | TDX历史建仓 | 已建设，既有阶段接受和日更使用 |
| 02 | Daily Canonical/PIT | 运营日更已具备；部分老历史严格first-asof不成立 |
| 03 | Pure-Core Factors | 既有独立验收和Accepted源；后续算法叠加不能冒充其历史PIT |
| 04 | 全市场Core Profile | 全市场画像主链已实现；运营Head为corrected受限性质 |
| 05 | Replay Gate A | 既有Replay A验收范围，不等于所有新日期严格PIT |
| 06 | Supplemental Turnover | 工程分支已具备；按实际BaoStock Source scope给权限 |
| 07 | Stock Base Seed | 基础生产/黄金样例既有阶段交付 |
| 08 | Sector/Rotation Core | 当前板块Native/Rotation算法存在；旧成员历史和正式D2需另审 |
| 09 | Stock PREWATCH | 已有全市场初筛输出；不等于当时真实首次观察 |
| 10 | State Reducer | 工程链和历史回放已实现；真实State首次冻结仍缺 |
| 11 | Confirmation/Events | 冻结确认算法存在，State新Producer重新运行；真实Event身份链需补 |
| 12 | Structure/Anchor/Support | 既有算法/runtime工程；真实Episode及后续继承尚待获准事实 |
| 13 | Advanced Projection | 历史范围化工程实现，LOO/轮动完整独立评估分域保留 |
| 14 | Replay Gate B | R19审计显示 **`ALGORITHM_STATE_REPLAY_DEGRADED_PASS` capability scoped**，不能称无条件全通过 |
| 15 | Radar/Cohorts/Settlement | R21外审明确 **`PASS_FINAL_V4_15_PROMOTION_CAPABILITY_SCOPED`**；不授予真实成熟样本/生产Focus权限 |
| 16 | Realtime Shadow Dual-Run | Runtime / source readiness 工程架构已做；R23/R24真实Shadow激活因实际来源与身份门受阻，不能称真实双轨已启动 |
| 17 / 17G | Shadow UI / Stable & Provisional Gate | UI/准入合同及工程演练存在；完整正式Shadow及稳定门未获准 |
| 18 | Migration Replay Gate | 有迁移/回滚工程合同与演练；未见 `MIGRATION_REPLAY_PASS` 全范围签发 |
| 19 | Focus Source Cutover | 不能把受限运营Focus只读当成已通过正式Source cutover；按capability继续阻断 |
| 20 | Default UI Cutover | 用户授权当前V4研究工作台局部生产读域；**不等于全部能力默认V4及完整发布** |
| 21 | Continued Forward Observation | R30/R31保留合同与ledger设计；真实 Shadow 观察未开始/样本不足，需未来逐日累计 |
| 22 | Independent Audit | R31R2设计与机器审计合同工程修复，原件仍 `V4_22_FINAL_AUDIT_ENTRY=BLOCKED_WAIT_REAL_GATES`、`V4_22_FINAL_PASS=NOT_GRANTED` |

FEP E1–E5是第78节独立的预测支线，不是V4-16～22或FP13研究读域的全局前置门。前端另有FP01–FP14合同：当前研究产品已有范围化实际发布，但FP13最终产品完整度与FP14完整发布未正式验收。

## 4. 本轮新发现的关键功能缺口：State Publisher→First-Observed合同尚未衔接

这是下轮的**P0工程缺口**，不能简单归因于“10/12数据尚未产生”。

1. `full_market_state_publisher_v1.build` 的新发布输出使用 `RECONSTRUCTED_RESEARCH_ONLY`或`OBSERVED_SOURCE_CANDIDATE`，全部`eligible_at_T0=False`，每行`episode_id/event_type/benchmark=null`，model仅给 `model_contract_id/parameters_sha256/window_version/scenarios/dependencies`；它没有发行 `state_lineage_id/frozen_signal_version/capture_deadline` 等完整First-Observed字段。
2. `full_state_first_observed_v1.freeze_first_observed` **必须读取** `evidence_class='PIT_OBSERVED'`、`membership_basis='AS_RECORDED'`、State有`state_lineage_id`和`frozen_signal_version`，model与成员有真实 `first_available/frozen_at`，行具有 `episode_id/event_type/benchmark` 和合法逐项时间。
3. 现有 `quarantine_publisher` 的确能冻结前者**作为隔离研究候选**，但没有从真实受控Source Owner合法提升到后者的版本化Publisher/审核决策器；不能靠将标签改成PIT或把研究300个TRUE改为正式eligible破解。
4. 运营Daily仍以 `AS_RECORDED=false` / `PIT_ELIGIBLE=false` 写入当前重建State；下一真实日到达后如果只有同样模式，本源型问题不会自动消失。因此必须区分 **未来真实日初次读取的原始数据** 和 **依赖旧成员/历史窗口形成的重建State**，在源级别给出有凭据的as-of身份。

**闭环要求**：单独的“当日接受的真源→正式候选state/membership/model原件→独立校验→隔离first-observed→独立Writer grant”的完整代码形状、真实数据缺口和负例在10/12前准备好；真实权威原件要等实际来源发生后现场判定。

## 5. 本轮其余风险与事实限制

- **日期切断**：截至本审计日周六10/10，下一交易日预计10/12；现有`18:35`是盘后实际采集/冻结，不得称为当日15:00已知，更不能作当时盘中买点。
- **测试性质**：`TEST_RESULT.json` 200 tests/0fail/0skip为Codex跑的真实测试节点清单，但当前外审未现场独立执行；D2 golden 0差异来自开发提交的receipt，未由审计者重算原3,553+6,188全量。
- **运行加载**：本轮Python Publisher及BFF的新钟点字段尚未获用户另行授权运行加载。已有PID42552支持旧研究读域，不代表当前 HEAD全代码全部已加载。
- **历史Amount H21**：9月缺20个原当时成员首次观测，旧窗口仍 `NOT_VERIFIABLE`。若无新的原始线索，不再重扫；新日期每天捕获，滚动建未来21日窗口。
- **非阻断原则**：当下市场、股票、板块、Focus、诊断只读不被FEP、H21或Cohort缺准入整体拉黑；这不意味着“无证据字段填0/false”或者削弱权限门。

## 6. 下阶段总体决策与并行顺序

**主线A（P0，新交易日前）：真实原始State Source→完整First-Observed合同的工程桥接。** 逐字段Owner和时钟及event/benchmark来源；使用原V4-15接口；完整合成数据隔离E2E。缺真源只冻结研究，不得签生产。

**主线B（P0，新交易日前）：日更18:35来源采集/运行未加载增量的发布预检。** 在隔离两Head/成员变化的执行链完成后，提交精确需加载Python模块清单、回滚路径/用户授权窗口；现有稳定服务不为赶进度任意重启。

**主线C（P1）：D2全六字段真实Episode起点、资格和到期机制，继续研究候选/正式分层。** A05原资格9/24 oracle可保留为限定范围证据；新T0名册、当日原排名、先前Episode和后续结算必须逐日真实产生。

**并行D（P1）：FP13研究已启用子域独立外审与逐功能修复。** UI可继续工作，补缺图/变化/历史联动、性能、组件隔离、正文对真实Source身份和时间披露；FP14只争取**受限研究发布范围**签收，禁止把FEP/Cohort当现成指标。

**后续E（新10/12 T0）：观察与权限准入。** 实际当日原请求/接收/first-available、当前成员快照/全市场scope、真实重复发布/校验、LAST_GOOD/CAS、同日State和Sector candidate；逐项判分层Source。T+1/3/5另按真实成熟逐步追加，不要求首日产生未来结果。

**延后F（P2）：FEP可信生产模型与预测。** 现有生产保持OFF，等Accepted Cohort/label与模型Owner、精确Grant具备再开；可低成本继续工程合同但不能阻断A/B/C/D。

### 唯一下一步

把同日配套《V4_NEXT_STAGE_EXECUTION_MASTER_AFTER_OVERALL_AUDIT_R1_20261010.md》交Codex执行。不要再执行“大扫历史/缺SHA清单/重复全量LOO/复制几百份空值”的循环。新任务中 A/B/D 工程现在可完成，C 可继续，E必须等真实新交易日；涉及生产进程重启需单独明确授权。

## 7. 证据定位

- 冻结GitHub：`https://github.com/NanOns/a-share-market-structure-research/commit/c0b9903fe596c1884c04f5529d6699034548850e`
- 最近执行结果：Drive `V4_PRE_NEXT_T0_EXECUTION_RESULT_20261010.md`，ID `1xLDYzTQJI0UZpiFtFdYM8ikWcEBBbh0u`。
- 本轮：`docs/evidence/pre_next_t0_execution_r1_20261010/final/`、`GATE_STATUS_R1.json`、`TEST_RESULT.json`、`STATE_PUBLISHER_SOURCE_AND_OUTPUT.md`。
- 源码：`src/workbench_analysis/full_market_state_publisher_v1.py`；`full_state_first_observed_v1.py`；`producer_bootstrap_v1.py`；`source_scope_reconciliation_v1.py`；`src/sector/d2_research_source_matrix_v1.py`。
- 阶段权威来源：Drive `A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md`第78节；Git `docs/evidence/r22/V4_R21_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md`；`docs/evidence/r31r2/R31R2_REPAIR_ACCEPTANCE.md`；`docs/evidence/fp13_20261008/FINAL_ACCEPTANCE.json`；`fp14_20261008/FINAL_ACCEPTANCE.json`。

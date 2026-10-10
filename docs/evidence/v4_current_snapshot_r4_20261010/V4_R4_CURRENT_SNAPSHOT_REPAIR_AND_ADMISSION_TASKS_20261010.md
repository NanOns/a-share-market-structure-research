# 大A V4｜R4 当前快照定点修复与正式输入接纳任务卡（不等待下一交易日）

- 任务编号：`V4-R4-CURRENT-SNAPSHOT-FORMAL-GATES-20261010`
- 任务性质：**可立即执行的正式任务卡 / Codex 执行合同**；与同轮《V4_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261010.md》配套。
- 项目：`NanOns/a-share-market-structure-research`；目标分支：`codex/v4-fp14-r2-repair`。
- 编制时 HEAD：`6b6d5cbd2b115335918aeeafcec9ae5a46f9eb99`；执行前 `git fetch`、锁定真实 `BASE_SHA`，禁止把编制时提交号当固定最新值。
- 当前合法数据 T0：`2026-10-09`；运营 Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；旧严格 PIT Head SHA：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。执行前后做真实字节核对。
- 工作根：`G:/codex work/大A交易`；所有新增临时/pytest/缓存放 `G:/codex_tmp`；`D:/new_tdx` 及一切 TDX 输入目录只读。
- 用户已限制工作重点：不建设热更新、Windows 服务、托盘、ACL 修复、整机重启、自动交易，不重复传输 551MB TDX ZIP 或多 GB Owner。
- **授权范围：本轮是源证据清理、正式输入契约及隔离候选实现、API/UI 修复、测试和证据归档；不默认授权修改 Accepted Head、激活尚未准入能力、运行真实 FEP 预测或以 corrected 历史冒充 strict PIT。**

## 0. 直接给 Codex 的指令

完整读取本文件、配套 R3 外审、`AGENTS.md`、V4.2.2 REV2 正式因子与页面合同、REV4 FEP R2、R3 最新 `11_DEEPENING/`、`09_CONTINUATION/`、`08_REMAINING_LEDGER.json`。首先做 `PRE-00`，随后**同时启动** `R4-A AMOUNT_H21`、`R4-B SECTOR_D2`、`R4-C COHORT`、`R4-D FEP_GATE`、`R4-E PRODUCT_RUNTIME` 的可并行内容。依赖到已接受正式 Owner 的发布步骤只做隔离候选、证明及申请独立验收，不得绕过权限。最后按 `R4-F` 汇总和提交。

**最重要：2026-10-12 尚未到达的真实交易日数据、首次真实后继日更、T+1/T+3/T+5 到期成熟度，不允许作为整轮开工前置条件。** 这些属于旧 DD R2.2 及长期追踪任务；本轮应交付现有数据能证明的全部工程、根因、负例、权限矩阵和真实可读功能。某包缺历史原件时明确标 `HISTORICAL_SOURCE_NOT_AVAILABLE` 并判终局边界，不暂停其余工作。

### 0.1 上轮已通过范围，原则上不重跑

- 现有 10/09 published LOO 50,214 对象、401,544 比较（开发方证据范围，待独立随机复跑）；不重新建全量旧输入，只验证新变更影响的对象。
- 15,632 可比金额行中的 345 条表示差异已建立 `HALF_UP→binary32` 精确复现路径；**不得再写“345 条未解释”**。也不能误当成 M10/H21 正式通过。
- 既有 22,452 + 6,021 算术检查、240 pulse、325 UNKNOWN 原因比较、已完成真实五会话案例；没有更换源/算法 SHA 的不重复执行。
- 当前搜索、分页、历史日期、Focus INVALIDATED 退出及局部错误隔离可继承已有工程证据，但新版 28765 实际加载尚待核对。

### 0.2 统一六维状态（不得只给一个 PASS）

所有任务、每一字段至少记：`FORMULA_LOGIC / DATED_INPUT / FORMAL_OWNER / API_UI_BINDING / HISTORICAL_AS_RECORDED_PIT / FUTURE_MATURED_OUTCOME`，每维输出 `PASS_SCOPED / FAIL / UNKNOWN / SOURCE_NOT_PRESENT / NOT_AUTHORIZED / NOT_TESTED` 与 source path、SHA、T0、first-available、窗口、成员版本、真实消费者、下一动作。实际没读到的数据为 UNKNOWN 而不是 0。不存在真实 Owner 的子模块不得假装“计算逻辑正确所以整个模块已生产”。

---

## 1. PRE-00｜锁定事实、差异影响和保护线（P0，立即）

1. 读取当前工作树，`git fetch origin`、`git status`、远端/本地分支和精确 `BASE_SHA`，保留用户本地未提交更改；比对本轮 R3 真实 diff 与 `STAGE_COMPLETION.json`、`PRODUCTION_LOADING_AND_HEAD_PROTECTION.json`。
2. 核对 accepted_trade_date=10/09、真实 Head/strict PIT 字节哈希、成员 `TDX_LATEST_MEMBER_RETRO_V1` 实际首次观测于 10/09 09:44，记录严格 `AS_RECORDED=false`；不可把历史 corrected 变为 PIT。
3. 对三份 Drive R3 报告（初始、续做、深度推进）及三个阶段 evidence SHA 汇总、去重。已证明领域 `PASS_KEEP`，仍受限领域映射到 R4-A～E，不重复创建功能平行链。
4. 输出 `00_BASELINE_AND_REUSE.json`（精确 SHA、执行版本、旧验证何处复用、可并行领域、发布禁区）和 `00_PROTECTED_BEFORE.json`。

**硬门：** 若原 Head 与真实仓库期望不一致，先停涉及正式数据写入的分支；不影响纯代码/离线审计继续。不能跳过登录用户尚未授权的服务停止或直接切换生产。

---

## 2. R4-A｜Amount A H21 历史 20 日：先证据追溯，后“可核验终局”与消费者修复（P0）

### A01. 精确缺口与不可伪造边界

R3 提供的原样本为 378 条真实 H21 候选全 `UNKNOWN`；21 个观察会话仅 `2026-09-30` 存在可绑定的正式当日成员观测，缺以下 20 个交易日原始成员版本/首次可用链：

`2026-09-01, 09-02, 09-03, 09-04, 09-07, 09-08, 09-09, 09-10, 09-11, 09-14, 09-15, 09-16, 09-17, 09-18, 09-21, 09-22, 09-23, 09-24, 09-28, 09-29`。

上述日历与计数来自前轮候选台账；本轮先从实际正式 calendar / H21 窗口身份再次计算并核实，不凭文字固定。

### A02. 不引入后见的来源追溯（现在可以做）

1. 只读扫描**已有**本机历史归档、原始 TDX 文件封存版本、备份、采集 Job Receipt、成员增量日志、Git 旧 evidence 和 Drive 原历史收据；每个目标日记录 `trade_date, source_path, raw_bytes_sha, first_capture_timestamp, collector_run_id, membership_version, canonical_trade_date, availability_verified, accepted_authority`。
2. 严格分离：`ORIGINAL_CAPTURE_AT_T0`、`DATED_LATER_CAPTURE`、`LATEST_RECONSTRUCTED_10_09`、`NO_ORIGINAL_BYTES`。不能从文件修改时间推断 T0 可用；10/09 最新成员绝不回填为九月当时的原始版。
3. 发现真的历史 source 时独立验证来源、身份、成员去重、20 日时间顺序、当日 amount 的 RAW/停牌/量纲/分母与可用时刻；只让经正式准入且等价条件满足的具体日进入 H21 候选，不能因某个观测合格而整个 21 日绿灯。
4. 找不到时把 `H21_STRICT_HISTORY_NOT_VERIFIABLE` 作为**终局历史证据状态**而非“修复程序未完成”；不要循环重试不存在的历史成员接口，不要用未来 10/12 交易日替换原缺失历史。

### A03. 明确两个可选但隔离的研究域

- `STRICT_H21_PIT`: 需要 21 个实际同日 first-available 成员观测，缺 20 就 fail-closed；`formal_consumer_enabled=false`。
- `CORRECTED_LATEST_MEMBERSHIP_RESEARCH`: 可在独立命名的实验/诊断域用事后最新成员回算研究对比，但必须标 `PIT_ELIGIBLE=false / SURVIVORSHIP_BIAS_PRESENT`；**不写入正式 Amount A Owner，不接给要求 strict PIT 的信号/模型/门禁**。是否采用该研究域必须符合既有合同或明确新增版本化设计，不能偷偷接生产。
- 从首次合法未来新日开始，每日留存真实 immutable membership first-capture，为**未来**真实 H21 窗口持续积累。日更由 DD R2.2 执行，本任务只完善每日 capture/lineage 合同、脚本和单测，不提前伪造未来当日收据。

### A04. 消费者与经济口径闭环

1. 审计 `stock amount / amount_ratio20 / amr20_mean_prior`、`sector participation_proxy`、正式 `sector Amount A`、`market total amount` 四条**不同**字段族，给出公式、窗口、单位、RAW/QFQ 规则、null/停牌、TDX Native/BaoStock 源、Owner、BFF/UI 消费者。
2. 保留 TDX Native 原始 amount 现有主权威。14,292/995/345 表示层归因仅能解决比较“数字怎样被表示”；供应商经济成交额定义是否一致应留独立证据与 `ECONOMIC_EQUIVALENCE_UNPROVEN`，不凭 exact floating conversion 签供应商算法结论。
3. 已可用字段可做现有输入的独立 spot check + 全字段映射断言；不受 H21 strict 门依赖的股票/市场数值不应一起被 UNKNOWN。只有具体消费者有已证错误时才修；不得用 stock `amount_ratio20` 代替 sector Amount A。

**A 包产物：** `A_H21_MISSING_20_SESSION_PROVENANCE.csv`、`A_H21_SOURCE_SEARCH_MANIFEST.json`、`A_H21_STRICT_VS_CORRECTED_BOUNDARY.md`、`A_AMOUNT_CONSUMER_LINEAGE.json`、`A_AMOUNT_INDEPENDENT_DIFF.json`、`A_FIX_AND_VERDICT.md`。

**验收**：来源发现过程、逐日 first-availability/缺源终局、数字单位与消费者行为通过，可标 `AMOUNT_ENGINEERING_AND_PROVENANCE_AUDIT_PASS_SCOPED`；若原始 20 日缺少则**必须**保留 `FORMAL_H21_BLOCKED_HISTORICAL_EVIDENCE`；不得自签 Amount A 正式 PASS。无需等待 10/12。

---

## 3. R4-B｜板块 D2：正式来源提取、输入契约、Episode 前态与接纳候选（P0）

### B01. 正式六个缺口不得绕过

以 R3 `SECTOR_FORMAL_EXTRACTION_PROPOSAL.json` 和 `SECTOR_D2_EXACT_CONTRACT_GAPS.json` 为当前诊断基准逐字段审计：

| 字段/前态 | R3 实际缺口 | 现在应做 |
|---|---|---|
| `CONFIRMED` | 历史 `legacy_b2_r5.evaluate_b2` 仍可能返回 UNKNOWN，未接纳正式确认提取 | 逐输入成员、名次、coverage、T0 可用状态，设计确切版本化 extraction 及可否确认的反例 |
| `WARM` | 旧 SETUP/RECOVERY、q20/dq5_3 与 Amount A 相关条件未合法落地 | 只能用有正式 Owner 和合法窗口的组成事实；Amount A strict 缺源分支必须 UNKNOWN，不能做“默认正常” |
| `frozen_invalidation` | 缺正式 Creation-frozen Episode 与 T-1 sector 输入 | 设计持久化 Episode identity、创建时冻结失效条件、事件变更与重复观察幂等，模拟边界做单测，不伪造真实旧 episode |
| `episode_invalidation_contract_id` | 上游合约版本未落地 | 给入组时绑定的真实合同 ID、版本和 Hash，而非代码默认常量 |
| `followup_complete` | 结算到期 Owner 未实现/接纳 | 独立 `due_plan`、右删失、尚未到期 UNKNOWN，不把“不存在后继交易日”解释为完成 |
| `scenario` | V4-11/V4-12 情景正式字段缺源 | 仅已支持情景落真实来源；无源精确禁用，不可借首页 Rotation 文案替代 |

### B02. 允许执行的真实开发

1. 先把上述六种契约的 `Producer → exact input owner → extraction rule → status tri-value → prior state → candidate owner` 画成字段矩阵；明确已有 `dq5`、合法 Native 计算范围与 AmountA 依赖。
2. 生成版本化**正式设计修订候选**与 JSON schema：对象类型必须 `SECTOR`，而非把 `STOCK` adapter 改名；冻结 member_set_asof、唯一成员分母、T0/前态 date、quality、first_available、window_identity、producer parameter set、null policy、schema migration/version。
3. 在隔离目录构建可复算的 `sector input → D2 reducer → readiness/health` 候选；对 400 个当前板块抽样和整体数量守恒，明确真实哪些可计算，哪些因 `CONFIRMED/WARM`/AmountA 受限。不能把 B0 PREWATCH 或 Rotation phase 命名成熟度。
4. 按有源/无源、先前状态改变/不变、同日冲突、节假日跨会话、身份池/成员变化、无足够历史、失效当天不能重入等正负例做独立参考 oracle；实证存在则修最小代码/adapter，没正式原始输入时保持 `SOURCE_NOT_PRESENT`。
5. 现有页面的日期、成熟度 UNKNOWN、Why-now、质量提示、板块与证券跳转不必等待新 Owner。只有获得正式准入、确切 accepted Owner 并经隔离 QA 的字段，才准备申请正常发布；**R4 未授权直接向运营 Head 写入或开启新 D2**。

**B 包产物：** `B_SECTOR_EXTRACTION_CONTRACT_R1.md`、`B_SECTOR_ENTRY_SCHEMA.json`、`B_SECTOR_PRODUCER_INPUT_MATRIX.json`、`B_SECTOR_ORACLE.py`/输入/输出、`B_SECTOR_READINESS_CANDIDATE_RECEIPT.json`、`B_SECTOR_ADMISSION_BLOCKERS.md`。

**验收**：合格 contract+detector extraction+缺口级候选+oracle 可现在走到 `ENGINEERING_CANDIDATE_PASS_SCOPED`；只有真实被接纳的完整字段和正式 owner 通过原合同发布门才可 `SECTOR_D2_FORMAL_OWNER_PASS`。缺乏 WARM/CONFIRMED/冻结前态时不得伪装全板块 readiness 通过。**独立 Phase B 不能因 Amount H21 missing 而停止不依赖 Amount 的板块功能。**

---

## 4. R4-C｜Validation Cohort：从纯只读契约走向“合法入组生产链就绪”（P0）

### C01. 既有框架必须复用

读取 `src/workbench_analysis/v4_15_radar_cohort.py`、`v4_15_forward_r2.py`、`v4_15_settlement.py`、`validation_cohort_read_contract_r3.py`、正式 V4-15/Forward/FEP 合同、`COHORT_FIELD_CAPABILITY_MATRIX.json`。不能因当前 `/api/v4/forward/statistics` 缺数据就重新造第二套 Cohort 算法。**Focus 2,805 Episodes 与 Validation Cohort 入组是不同对象，禁止互换。**

### C02. 实际事件/冻结权限盘点

1. 扫描现有真实日期的 `signal_event_at_T0`、候选全部资格/未资格、source revision、`publication_id`、真实 first-available 与 freeze receipt。每条给 `PIT_OBSERVED / RECONSTRUCTED / FIRST_AVAILABLE_AFTER_T0 / UNPROVEN`，后两类不许正式倒灌历史 enrollment。
2. 有真实当时 first-capture 的合法记录才允许提交给**隔离 admission candidate**；没有则 `NO_ASOF_ENROLLMENT`，但完成未来每个新交易日自动生成 immutable enrollment 的代码和门控接口准备，不等真实结果成熟。
3. 重构 producer/adapter 的最小接线点，让正式 frozen event 只受 Accepted Head/source manifest 提供，内部 JSON 字段 `authorized_read=true` 不能成为外部或调用者任意可设置的权限。正式权限由不变的 Head、grant、SHA 校验且关联 T0 前 first-availability；没有合法源则 fail-closed。

### C03. 安全负例与到期管理

补齐不少于以下场景：`publication_id`/`benchmark`/`frozen_signal_version` 缺失或空、重复 event 同 identity 不同 revision、第一次可用晚于冻结、naive/跨时区时间、周末或节假日 T+1/T+3/T+5、停牌/退市未知、同日多个合法 anchor、Focus 来源替代、T0 之后结果回填、旧 token/未来未发布日期/错 Member-asof、缺真实统计 Owner 分母为 UNKNOWN 而非 0。

`read_statistics` 纯函数可以保留，但生产路线必须新增可信的调用方 wrapper 验证发行证据、读域权限及 source SHA；只有 caller-supplied `authorized_read` 的 dict 不可直接发生产 `READY`。不改写旧冻结结果或修订未来结果为旧预测。

### C04. 隔离 API/UI

真正有合法历史 enrollment 的只读显示才计算 observed/matured/settled 统计；在没有正式 enrollment owner 时，现有 `/forward/statistics`、`/settlement`、`/plans`、`/fep` 分域返回精确 `NO_AUTHORIZED_COHORT_OWNER / NO_AUTHORIZED_SETTLEMENT_OWNER / MODEL_OR_PERMISSION_NOT_READY`；Focus 原始 Episode 仍能正常显示、搜索、独立计数。

**C 包产物：** `C_LEGACY_EVENT_FIRST_AVAILABLE_INVENTORY.json`、`C_AUTHORIZED_ADMISSION_DESIGN.md`、`C_COHORT_PUBLISHER_CANDIDATE.py`（如已有功能优先补原模块，不创建并行后端）、`C_ADMISSION_DENIAL_TESTS.json`、`C_API_SCOPED_READ_QA.md`、`C_LIVE_ENROLLMENT_BLOCKER.md`。

**验收：** 当前源足以验证的冻结、权限、无前视、去重、到期和 fail-closed 可标 `COHORT_ENGINEERING_READY_SCOPED`；无真正 T0 first-available 及正式授权时 `REAL_COHORT_ENROLLMENT_NOT_GRANTED` 仍为 OPEN。允许**准备下一实际合法 T0 自动积累功能**，但不得在本轮擅自激活生产写入。

---

## 5. R4-D｜FEP 只做合法模型/授权入场准备，不生成虚假预测（P1）

1. 对照 REV4 FEP R2/现有 V4-15E3～E5 合同，列已有 model registration、训练数据当时 first-available、model_revision、prediction_revision、accepted model set、grant key、审核状态与真实可用率。已存在正式产物先寻找，不默认“全部不存在”，也不从模型代码存在推定合法生产模型已批准。
2. 明确 `MODEL_NOT_FOUND`、`MODEL_NOT_ACCEPTED`、`GRANT_MISSING`、`INPUT_ASOF_NOT_VERIFIED`、`SAMPLE_NOT_MATURE`、`NO_SCORING_AUTHORITY` 五类原因，输出字段级禁入映射及用户可见中文解释。
3. 实现或修复隔离模型注册与能力检查、已冻结预测数据不可改写规则、负例及 API/DOM 局部降级；**无需模拟 10/12 模型预测成功**，不得在生产跑新的盈利概率/黑箱主观推荐。
4. 允许先完成 schema / owner/version /审计前置门；真实模型的授权只有用户/正式审批轨道明确给出后才可能进入生产，Codex 自测不得签发 grant。

**D 包产物：** `D_FEP_ACCEPTED_MODEL_AND_GRANT_INVENTORY.json`、`D_FEP_PERMISSION_NEGATIVES.json`、`D_FEP_GATE_UI_QA.md`、`D_FEP_ACTIVATION_DECISION.md`。

**验收**：`FEP_ENGINEERING_GATE_READY` 不等于 `FEP_PRODUCTION_AUTHORIZED`；若模型/合法权限确实缺失，显示后者继续 BLOCKED，这是正确状态，不构成本轮其它工程 FAIL。

---

## 6. R4-E｜生产工作台代码加载与 FP13 定点外审（P0 部署确认，非运维改造）

### E01. 源码存在不等于生产已加载

R3 冻结证据清楚显示 `127.0.0.1:28765` 旧生产服务未加载本轮竞争解释，而 `28767` 隔离读服务已进行了浏览器 QA。使用**既有正常、安全、用户允许的关闭并重启流程**加载已提交代码；不许 `taskkill /F`、改 Windows ACL、未经授权杀进程/重启整机。不增加热加载、托盘、自启或 Windows 维护系统。如果旧服务不能安全停止，保留 `PROD_RESTART_PENDING`，让用户按现有正常方式关闭。

### E02. 新服务只读观察

重新启动后记录 `pid / startup_time / python_executable / repo_root / exact HEAD / core_product_bff SHA / research_hypotheses_r3 SHA / cohort contract SHA / active port`；不能只拿磁盘文件 SHA 代替**运行进程实际加载**的代码。保留 10/09 运营 Head、历史 PIT Head、AUTO flag 和老日收据原值，未授权时不发新数据或改 Head。

### E03. 真生产六入口抽查

在 **28765** 上按 `1366×768` 与 `1920×1080`，用已接受 10/09 Owner 核对六入口：日期/T0/来源、股票代码与中文搜索、股票日周月 RAW/QFQ、板块成员与过滤分页、Focus 失效关闭及独立 Cohort 缺源、市场 breadth 单点503时其余四轴/指数可用、恢复、diagnostics/PIT restricted、历史切换后旧日不能读新图表。抽验每入口至少一条 `source SHA→API JSON→DOM value/unit/quality`，明确浏览器原始 DOM 与手工转录摘录的不同可信度。旧 token 409，未来日期400，业务 200+SOURCE_INCOMPLETE 不作 PASS。

- 若 28765 正常重启完成：`PRODUCTION_RUNTIME_LOADED_VERIFIED`（仅当前已接受 10/09 读域），附实证；否则 `PROD_RESTART_PENDING`，其余 A/B/C/D 开发**继续**。
- FP13 的本轮可完成状态是 `FP13_SNAPSHOT_EVIDENCE_READY_FOR_INDEPENDENT_AUDIT`，FP14 联合正式产品发布与回滚仍按已有独立合同及权限进入。

**E 包产物：** `E_PROCESS_IDENTITY_AND_LOADED_MODULES.json`、`E_PRODUCTION_HEAD_NO_CHANGE.json`、`E_FP13_BROWSER_ACTUAL_MATRIX.json`、`E_FAULT_AND_RETRY_RECEIPT.json`、`E_RUNTIME_VERDICT.md`。

---

## 7. R4-F｜独立复算、逐包签发、最小归档及下一日接口（P0）

### F01. 独立验证优先补洞，不重复天量历史

- 从上轮 R3 的轻量 zip（已校验存在的部分）取独立 oracle 对随机证券/板块做外审方独立复算，核对真实 input SHA 与 expected 来源；Amount A 新增 21 日历史若缺字节，**不能**“离线跑 fixture 全绿”冒充历史真实通过。
- 对 B/C 新增候选按 `schema → 原始现值 → 负例 → API/DOM` 跑独立参考验证；记录精确 `input SHA, code SHA, expected, actual, delta, reason, sample_date, source_availability_at`。
- 对生产代码是否正常加载采用真服务 SHA 和原始浏览器捕获，不复用 28767 证据冒充 28765。

### F02. 统一验收矩阵（最少这些状态）

| Work | 可以现在完成的部分 | 独立保留的绝对门 |
|---|---|---|
| A Amount | 20 历史日原件实查/缺源终局、金额映射、可用字段计算证明 | H21 若缺原始成员/first capture：`FORMAL_AMOUNT_H21_NOT_VERIFIABLE` |
| B Sector | 6字段确切合同、提取器、隔离候选、负例与现有 UI | 未正式接纳 Producer/episode/due/owner：`SECTOR_D2_OWNER_OPEN` |
| C Cohort | immutable enrollment producer/reader、安全入场校验、统计到期与拒绝测试 | 未有合法 first-available event/正式 Owner：`NO_AUTHORIZED_ENROLLMENT_OWNER` |
| D FEP | 模型/版本/权限清册、禁入原因及 UI | 无模型/授权/首获真实数据：`FEP_CAPABILITY_NOT_READY` |
| E runtime | 安全重启可做，真实 28765 源绑定可测 | 尚无实际重启或受限：`PROD_RESTART_PENDING` |
| PIT | 找得到的历史原件逐项保留；旧 corrected 权限明确 | 无旧 first-capture 的老 T0 永久 NOT_VERIFIABLE，不借未来数据“补证” |
| Next day | 只预留可运行 E2E 检查命令/独立日志目录 | `WAIT_REAL_SESSION`；10/12 实际 source 完整以旧 DD R2.2 卡验收 |

### F03. 产物目录与完整交付

建议正式目录：`docs/evidence/v4_r4_current_snapshot_20261010/`，至少包含 `00_MASTER_RESULT_R4.md`、`01_A_AMOUNT/`、`02_B_SECTOR/`、`03_C_COHORT/`、`04_D_FEP/`、`05_E_RUNTIME/`、`06_EXTERNAL_RECHECK_MINIPACK/`、`07_GATES_LEDGER.json`、`08_EVIDENCE_MANIFEST_SHA256.json`、`09_DRIVE_READBACK_RECEIPT.json`；R3 原始作答/开发收据和代码不覆盖，R4 作为追加证据版本。

- Git 提交：每 A/B/C/D/E 单独可追踪，异常只改首个真实错误；`git push` 后核查 exact remote result SHA、Git diff、工作树未清除不相关文件。
- Drive：直接同步到原 `DA-TRADER-TRAINING_大A主观交易员培养计划/00_项目基准与进度/V4全功能生产前端任务卡_20261008`（或当前经证实的同一任务目录），归档正式 MD 与小型 JSON/ZIP，读回 bytes/SHA/CRC；禁上传 4GB Owner、551MB TDX ZIP。Drive 写入成功才视正式文件交付完成。
- `00_MASTER_RESULT_R4.md` 按 GATE 报具体 PASS_SCOPED/FAIL/NOT_VERIFIABLE、根因、下一步；禁止仅写“5/5全部通过”。Codex 最多写 `EXTERNAL_RECHECK_REQUESTED`，外审由独立方签发。
- 不要继续反复补同一工作包的版本，只因无历史资料或权限而永远做表面工作。**每一不可解决的缺证项目要交“已遍历哪些真实位置/什么不能证明/在什么新事实出现前保持关闭”的终局陈述**。

### F04. 与 10 月 12 日既有 DD R2.2 合同接口

1. 预计下一个真实 A 股交易日为 `2026-10-12`。它的 `SourceReady(TDX Native/BaoStock bar/BaoStock factor/identity/GBBQ)→RAW/QFQ→D/W/M→Core/RPS→Sector/Market/Focus→Owner QA→CAS→六 API readback` 仅在真实源发布和合法工作台加载后执行。
2. A/B/C/D 的功能在该日合法新证据出现后只追加第一份正式 dated 收据，必须保持 T0 首次可用时间；新的 FEP 模型权限、strict 历史成员20日、长期成熟 OOS 不能借新日自动升绿。
3. 实际失败则修第一个真实断点，保留旧 last-good，不能强制发布或反向改写 10/09。

## 8. R4 提前结束条件（避免无限工程等待）

若各包可执行的源码、契约、负例、API/UI 修复及外审小包完成，且历史来源搜索已留下可复核 `NO_ORIGINAL_BYTES` 结论，用户尚未给正式新权限时允许本轮以**`ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES`**收尾；同时明确整个 V4 全正式准入仍为 `EXTERNAL_ACCEPTANCE_BLOCKED`。只有确切已证算法或产品错误尚未修好时，本轮受影响包才 FAIL。**不允许将 20 天历史缺源、Cohort 无真实 T0 入组、FEP 无 grant 这些事实性缺口反复伪装成“继续写测试即可变绿”。**

## 9. 给 Codex 的最简输入

> 读取本 R4 合同与随附 R3 外部审计。按 PRE-00 开始，A Amount H21 历史缺证、B Sector D2 正式输入接纳、C Cohort 真正 as-of 入组、D FEP 模型/权限、E 用户生产加载五路推进；目前可执行的代码/负例/审计/界面要全部做完。缺实际旧日 as-recorded、正式授权或 10/12 真实数据时，精确记缺源/权限/未来门，不伪造、不整体停工。保留 Accepted Head/旧 PIT，禁止触碰 TDX 输入或做 Windows 运维大工程。每包提交 Git、最小证据包并同步 Drive 回读，最终外审单独申请。

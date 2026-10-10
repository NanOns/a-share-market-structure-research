# 大A V4｜R4 本轮外审后·下一个可直接执行的任务卡 R1（2026-10-10）

- **唯一最高依据**：本轮《V4_R4_POST_AUDIT_EXTERNAL_RECHECK_R2_20261010.md》，仓库 AGENTS.md、REV2及REV4 FEP R2正式合同。
- **冻结基准 SHA**：`336827bf0bc152a4c5c9ba7ec6e4662751fe7422`；执行前 `git fetch` 确认实时HEAD，不得从旧SHA开始覆盖当前提交。
- **当前 T0**：`2026-10-09`；受保护运营 Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；strict PIT Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。
- **本轮只做真正未闭环的功能与证据**；不重做 R3 operational LOO 50,214、401,544比较，不重做金额345表示差异，不重做 B 的400个全空值演示、不重复换端口重启已正常的进程。TDX输入只读，产物在 G盘；不能变更已接受 Head、旧冻结、模型权限或超越用户授权。

## PRE：确认有效生产身份和继承状态

1. 锁定 exact BASE_SHA、检查工作区和远端差异；只读检查 `28765` 新进程 PID、命令、实际加载模块 SHA、启动时刻、当前代码SHA及两个受保护Head；若无变化保留既有通过结果；避免为生成新文档强制重启。
2. 读取 `12_BCD_DEVELOPMENT/PRODUCTION_MODULE_ATTESTATION.json` 和 `11_CONTINUATION/01_E_BROWSER/E_BREADTH_503_BROWSER_RECEIPT.json`；`1c47f6ca...→当前SHA` 无源代码变化应被保留为继承依据。

## E｜生产与FP13，优先独立验收而非继续重构

- 用真实当前token从28765只读核对六入口关键业务字段、六入口导航、10/09当前数据、真实历史688349/9/30 13.240、301628/10/09 INVALIDATED、Focus页面、股票搜索过滤、分页返回、T0不混日、市场指数/宽度/交易额。
- 对旧token/空token/正确token返回409/409/200归类；不得把200+`SOURCE_INCOMPLETE`计作指标可用。
- 复验**受控浏览器**一次503→局部失败、其余区域不变→点击重试恢复，分别1366×768/1920×1080；浏览器一次故障拦截不得写成真实服务器宕机。
- 若代码、真实端口及浏览器证据没有变更，只做差异抽查并申请 `FP13_SCOPED_BROWSER_EXTERNAL_RECHECK`；FP14联合正式授权另行审核。
- 产物 `E_FP13_INDEPENDENT_RECHECK_MATRIX.md` 和 `E_CURRENT_PROCESS_READBACK.json`。

## D｜候选DB状态的精确订正 + 正式授权来源门

- 在 `trusted_authority.read_canonical_candidate` 中修复 `errors` 非空时仍可能返回 `CANONICAL_AUTHORITY_CANDIDATE_VERIFIED` 的显示/语义瑕疵，统一 `DB_FACTS_READ_VERIFIED`、`CANDIDATE_INCOMPLETE`、`FORMAL_APPROVAL_MISSING`等可辨状态；严格保持 `production_authorized=false`。
- 使用隔离 DB 做至少：完全候选、缺prediction owner、`engineering_only` CAS、缺label成熟、过期grant、no independent approval 等正负测试；在所有缺正式授权情形明确输出候选不完成及原因，**不修改已接受业务模型**。
- 继续核实正式model version / Head-CAS /审批Owner / as-recorded训练及prediction source 实际缺失，给精确消费者启动前置，而不是仅报笼统MODEL_NOT_READY。没有正式原件时正常以阻断收尾。
- 产物 `D_STATUS_CONTRACT_CORRECTION.md`、`D_NEGATIVE_CANDIDATE_JUNIT.xml`、`D_EXACT_TRUSTED_PRODUCTION_REQUIREMENTS.json`。

## B｜板块D2：已建适配器的真实上游及入场条件

- 不再把已有 D0/D1/D2/Rotation 的诊断代码重新造一遍。按六字段列Producer、历史黄金输入范围、是否存在 `10/09` first-capture及Accepted Head binding、窗口/成员版本、字段可用与必需的入场授权。
- 明确 A05 只接受9/24的实际证据，10/09返回`A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED`；给出合法的新原件生成路径/独立准入合同，不得直接改变9/24授权日期或仅换`as-recorded`标签。
- 能合法接纳的非 H21 Native 事实继续允许当前产品显示；要求完整 `SECTOR_D2_FORMAL_OWNER_PASS` 的项目继续BLOCKED直到真正原件可用，特别是 Episode原始冻结、正式WARM、CONFIRMED、due、scenario。
- 产物 `B_FORMAL_PRODUCER_ADMISSION_DECISION.md`（只写新证据/原件/阻断决策），不得再复制数千行全空值 JSON。

## C｜Cohort：未来合法首次冻结的最后接口，而非回填旧事件

- 对 `freeze_source_candidate→extract_candidate→prepare_capture→DD候选`做少量真实源精确反例，特别是 T0之前/之后首获、冻结窗口、篡改原件、空eligible/ineligible理由、重复出版revision、错误State Owner源、读写grant分别校验。
- 确保未来真正正式 State producer获准时每个合法新T0只冻结**所有**信号一次；DD失败只影响Cohort能力不得使现有RAW/市场/股票日更中断。
- 旧2290历史事件一律不可回填入组；当前`observed_count=null`且`production_write_authorized=false`为正确阻断。不能以模拟10/12新日声明“真实Cohort上线”。
- 产物 `C_REAL_T0_CAPTURE_ADMISSION_CHECKLIST.md` 和差异负例；没有新原件则结束此包，不无期限追加版本。

## A｜Amount/PIT保留已经审计的历史终局

- 当前严格 H21 缺20个原始历史成员观测日，按原账本 `H21_STRICT_HISTORY_NOT_VERIFIABLE`；无新线索不重扫全盘、不重跑比例。新实际交易日由既有DD R2.2流程捕获首次可用，未来连续21合法会话再评估真正H21；历史9月仍无法由未来数据补证。

## FINAL｜统一验收账本，给Codex的明确收尾条件

- **P2 必修**：`07_SCOPE_GATE_MATRIX.json` 顶层FP13 503恢复PASS与`stages.E.acceptance=FP13_FAULT_RECOVERY_OPEN`冲突。做版本化追加订正，注明生效证据SHA与时刻，保留历史原始判定；`12_BCD_DEVELOPMENT/STAGE_CONTRACT.acceptance=IN_PROGRESS`注明是开工冻结不是现行状态。
- 分别记录 `PROD_CODE_LOADED`、`PROD_API_SCOPED`、`FP13_BROWSER_SCOPED`、`FP14_FULL_RELEASE`、`SECTOR_D2_FORMAL`、`COHORT_REAL_ENROLLMENT`、`FEP_PRODUCTION_AUTHORIZED`、`H21_STRICT`，不可用一个PASS覆盖全部。
- 独立证据：本轮变更的源码、测试、至少一个真实失败与成功返回、输出SHA、T0、Head不变与API数据量纲；不存在实际源就只给`SOURCE_NOT_PRESENT`与合规的后续入场条件。
- Git每包跟踪、推送后核对remote HEAD；正式MD和**轻量**复核包按项目规则同步Drive并回读字节SHA。Codex仅可申请外审，不签`EXTERNAL_ACCEPTANCE_PASS`。
- 若E业务可读且D状态语义问题消除、B/C源/权限绝对门明确，本轮可以`ENGINEERING_SCOPE_COMPLETE_WITH_DECLARED_FORMAL_GATES`结案；全V4正式状态仍`EXTERNAL_ACCEPTANCE_BLOCKED`直到真实正式Owner、历史PIT与FP14批准完成。无需等10/12才执行此轮工程/审计。

## Codex最简调度文本

> 按本R1任务卡执行，优先只读复验当前28765和FP13真实业务、修FEP canonical候选status在错误非空时仍称VERIFIED的问题，同时补板块正式Producer准入决策和Cohort真实T0最后接口，统一R4相互冲突的账本状态。已有全量历史和无源候选不可无意义重跑；缺合法旧原件/生产模型权限则精确保留BLOCKED，其他模块继续推进。完成代码、单测、远端推送与Drive读回后申请外部独立验收。

# 大A V4｜R4 后续全系统工程闭环执行任务卡 R3

> 版本：R3 / 2026-10-11（北京时间）  
> 状态：`TASK_CARD_ISSUED / ENGINEERING_ONLY`，不是外部验收、生产切换或任何历史 PIT/FEP 授权  
> 项目：`NanOns/a-share-market-structure-research`  
> 正式目标分支：`codex/v4-fp14-r2-repair`，已核对 HEAD `fbd23a6ba08d0948fe7ad421d1765fe363648522`  
> 当前隔离候选分支：`codex/r4-pg-only-20261011`，2026-10-11 核对 HEAD `595f49f1b16e52907419da8a164f1de42e817353`  
> 最新代码变更核心 SHA：`4f7e49d22a3f703813c62db0d8132d04eb6f2ae6`，随后有证据提交；实际执行源须以 `EXECUTION_SOURCE_BINDINGS.json` 为准，不能用证据提交的 SHA 冒充测试时已加载代码  
> 最高执行边界：V4 现行功能及其真实可达依赖、PostgreSQL-only；不运行/修复完整 V3 和更早套件  
> 已读取上位 Drive：《V4_R4_CONSOLIDATED_EXECUTION_MASTER_PG_ONLY_20261011.md》《V4_R4_BATCH2_INDEPENDENT_REAUDIT_R2_20261011.md》《V4_R4_R2_REPAIR_REPORT_20261011.md》，以及仓库 `docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md` 与最新 `R2_DISPOSITION.json`。本卡是**增量续行卡**，不覆盖上位合同与历史外审。

## 0. 先确定“闭环”到底指什么

本轮将五类结果**分开**判定：

1. `ENGINEERING_IMPLEMENTED`：代码写了、隔离能力测试通过。**目前已有部分完成**。
2. `V4_ENGINEERING_FULL_PASS`：V4 合法功能/消费者/PG-only/正确性/回归/前端所有立即可验证的工程门完成，并有可重放证据。
3. `EXTERNAL_ACCEPTANCE_PASS`：独立外审在**精确冻结提交**上核对全部工程门，核实源码、复现、独立 oracle、原始 JUnit/日志、保护完整性；开发者自签不算。
4. `PRODUCTION_LOADED_AND_VERIFIED`：完成明确授权的生产切换、在役 PID 全加载证明、完整读写权限、失败回滚和 Windows 现场验收。**工程通过不自动授权生产**。
5. `PENDING_REAL_SESSION / PENDING_MATURITY / PENDING_PERMISSION`：新的真实首获、历史合法 PIT、20 日会话、T+1/3/5/10/20 成熟/OOS和其他需要现实时间或许可的门。这些不能靠重放或合成清零，也不阻塞前述可做工作。

总状态目前仍为 `EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE`。目标是先把第2类真正完成，再做第3类；第4、5类独立管理。不得为了把总状态变绿而合并不同语义的门。

## 1. 最新进度（必须继承，禁止倒退/重复建轮）

- R4 R2 有界能力回归 **206 PASS / 0 FAIL / 0 ERROR / 0 SKIP**；其中仅119节点与旧4568相交，87为新测试。不得相加得到“全系统通过”。
- 原 245 模块／4,568 节点冻结执行为 3,810 PASS、237 FAIL、209 ERROR、312 SKIP，仍需逐节点合法性/处置；`global_v4_legal_denominator=null`。
- 新 PG 研究快照 R2 已实现四表内容寻址；Series/Journal/Shadow、联合 Head V2 已有隔离测试，不是全部正式消费者已接管。
- 原已接受 research 快照源只读迁 PG：6,337 objects、12,106 aliases、50,162 members、1 metadata，全表规范摘要差异0；证明有界**存储等价**，不能取代源字段质量、内容身份/版本和下游消费验收。
- 五冻结 T0×五跨行业证券×D/W/M×RAW/QFQ×三分页共450图表请求，独立源 oracle 差异0；但仅210 `READY`，240 `SOURCE_INCOMPLETE`。缺少合法周期 Owner 的记录必须留为 OPEN/UNKNOWN，不伪造历史 PIT/周月数据。
- 六产品路由额外30请求，Forward 仍可因来源未授权返回 `SOURCE_INCOMPLETE`；浏览器390×844出现 `document_width=487` 的移动端溢出。
- 旧生产 Head、PID、正式库及旧 SQLite 文件未在 R4 中被授权切换；相关保护范围仅有限源 SHA 被复测，不可扩大声称。
- 确证旧 `src/workbench_analysis/operational_daily_jobs_v1.py` 仍直接有 `sqlite3.connect()` 与 `jobs.sqlite3`。新 PG repo 存在，不等于所有当前 V4 运行入口已经改走 PG。

## 2. 执行总原则、环境和前置

1. 立即拉取两个分支、记录 HEAD、工作树、在役 PID、服务端口、manifest/authority、PG database/system_identifier/schema、各受保护文件 SHA；工作仅在 `G:/codex_tmp` 和 G 盘隔离工程库执行。若上面冻结 HEAD 已改变，以新实际 HEAD 重新冻结并生成 diff/影响测试清单。
2. 绝不向 `D:/new_tdx`、生产 DSN、accepted/strict/operational Head、旧 `jobs.sqlite3/history.sqlite/research.sqlite` 回写；只读迁移 oracle 必须隔离进程、原文件哈希前后相同。
3. 只审现行 V4 与其可达遗留依赖；当前真实 V4 依赖即使文件名带 v3/legacy 也纳入；独立老 V3 工作台不纳入、不运行全仓裸 `pytest`。
4. 所有新 PG 实现从 default startup、桌面、job worker、HTTP、历史/回放、事件、Focus、Forward/FEP、异常/恢复入口验证真实选路与 SQL intent；错误 DSN 必须 fail-closed，禁止 SQLite/DuckDB fallback。
5. 隔离能力绿灯≠正式 API 消费成功≠外部验收≠生产加载；每个结果绑定实际源码 hash、source manifest、测试命令、DB identity、时间和完整原始收据。
6. 任何新提交修改已复核核心实现，必须据调用图自动列出受影响门并重测；不借用旧源 SHA 的绿灯。

## 3. 立即执行：五张 P0 工作包（以 P0-1/P0-2 优先，余项并行）

### P0-1｜合法的“完整 V4 测试分母”与 4568 节点逐项清账

**目标**：把 `global_v4_legal_denominator=null` 变成一个有充分范围依据、不可随意缩小的确定整数，并闭环当前可运行的所有节点。

1. 冻结 `V4_RUNTIME_ENTRY_GRAPH`：default V4 server、desktop、daily scheduler+executor、PG snapshot/index/reader、history/replay、market/sector/stock/Focus/Events/Forward、FEP engine/权限、Windows 启动及所有受支持的动态入口。为动态 import、HTTP route、worker/subprocess、配置可选分支构造**实际可触发**探针；不能仅凭 AST/grep证明不可达。
2. 冻结 `V4_NORMATIVE_CAPABILITY_MATRIX`：V4.2.2 当前合同每一业务能力、必要字段、质量、来源、时点、真实调用者、用户可见界面、负例与 owner；对每能力配置至少一个正确性测试与必需异常测试。
3. 对旧 4,568 每个稳定 node ID 给出 `INCLUDE_V4 / LEGACY_ONLY_EXCLUDED / REPLACED_BY_V4_EQUIVALENT / BLOCKED_SOURCE_OR_PERMISSION`、业务功能对应、真实运行入口、证据路径和人工/独立可审核的排除依据。原 FAIL/ERROR/SKIP 保留，只另加当前结果列。
4. 原 446 FAIL+ERROR：逐项拆出 PG 后端冲突、真实业务错误、原 V4 fixture 缺档、旧 V3 纯隔离、权限/启动故障及误 PASS；312 SKIP 逐项给出 V4 合法状态。使用不被 `pytest.raises(ValueError/Exception)` 吸收的 `BaseException` 数据库非法接入护栏；审视旧3,810 PASS 是否出现护栏伪成功。
5. 对 V4 合法节点补精确冻结 PG 夹具与首获/重构状态，不用模拟的 `PIT_ELIGIBLE=true` 填洞。按子系统分批运行，再在**同一冻结 source SHA + clean PG**做一次完整命令级 clean-slate run，产出全JUnit与 node ID 对照。

**出口**：`V4_RUNTIME_REACHABILITY_FULL.json`、`V4_NORMATIVE_CAPABILITY_MATRIX.csv`、`V4_TEST_LEGAL_SCOPE_FINAL.json`（确定分母和取数规则）、`TEST_NODE_DISPOSITION_FINAL.csv`、`V4_CLEAN_FULL_REGRESSION.xml`、独立选样复跑脚本。工程范围内 `FAIL=0/ERROR=0`；每个 SKIP/排除均有已复审的合法依据；未获现实 source/Grant 的条件测试独立标记，不用造样本替代。

### P0-2｜真正的“全部真实消费者”与 DB-01～DB-12 PG-only 执行链

**目标**：不能仅审仓储文件，必须证明确实被 V4 所有**受支持入口**消费。

1. 冻结生产者→持久化→发布 Head→API/worker→UI/下游的有向消费图，至少包括 `DailyJobs`／Windows `jobs`／`engine`、Snapshot R2、Series、Journal、Shadow R2、历史索引、Focus、Radar、市场/板块/个股、Forward/FEP/settlement、事件、回放及恢复。
2. 对每个节点以 `producer_contract/version/source_digest/T0/first_available/quality/PG_schema/read_descriptor/consumer_function/API_route/UI_element` 记录**真实调用**，用隔离 PG 的 HTTP/桌面/任务 worker 集成运行（不是直接 import 单元测试）证明取的是预期新 repo。
3. DB01/02：将默认 `DailyJobs`、自动调度真实 executor、重试/rearm/checkpoint/幂等/CAS、崩溃恢复、桌面启停/status/control 全接 PG；确认旧 `operational_daily_jobs_v1.py` 是兼容封装还是仍可达旧存储，合法 V4 路径出现 SQLite 则失败。测试双worker竞争、重复启动、异常中断/重新启动、取消与发布竞争、手动恢复及用户暂停。
4. DB03：默认 `make_product_handler`、页面六入口、chart RAW/QFQ D/W/M 全走 PG 且按同 Head/T0；对历史 alias、停牌、部分周期未获合法源、分页/越界/错误 token、冷/热和并发给出原数据 oracle；不能偷注入隔离 constructor 越过正常 authority 路径。
5. DB04/05：研究快照、事件、板块成员、Focus、历史日期及持续发布与回滚，验证 PG 内容身份、完整 consumers、版本化合同、真 CAS/双writer/健康检查中篡改及 PREPARED 恢复；旧 research.sqlite 只作为冻结对照，不使 accepted authority 自动换成新投影。
6. DB06/08/09/12：证明 `api_connection.py` 等 DuckDB/Postgres 桥、ops/history、所有合法动态入口在 PG 失败/配置缺失/回放/异常路径上不连 DuckDB/SQLite；发现遗漏新增 DB-XX，不使用“因为默认首页没经过”排除其它支持入口。独立旧 V3 保留且证明隔离。
7. 正式消费者权限不存在时标记 `PENDING_PERMISSION`，但其无权限 fail-closed、契约/类型/异常传递/只读/可恢复等工程能力仍须完成。Shadow 模拟序列不能称真实历史首获。

**出口**：`V4_ALL_REAL_CONSUMERS.csv` 每个生产者和消费者有 TRUE调用/条件分支/来源缺口、`V4_DATABASE_RUNTIME_INTENTS.jsonl`（源 SHA、堆栈、入口、读写、PG DB identity）、`PG_ONLY_RUNTIME_ZERO_FALLBACK.json`、`V4_E2E_CONSUMER_MATRIX.json`。合法 V4 已启用且可测的消费者 `UNTESTED=0`、`NON_PG_BACKEND_ATTEMPT=0`；其余条件消费者精确列出许可/来源前置，而非空泛“开放”。

### P0-3｜跨模块数据内容、版本、等价、回滚及最小权限

1. 对已实现的 Snapshot R2、Series、Journal、Shadow R2 的**全部内容**、PG实例/库OID/schema、source/manifest摘要、时间/质量/字段单位全链 readback，验证读事务 `REPEATABLE READ READ ONLY`、seal前后源值一致。
2. 验证同一个对象/Head 不可因迁移或后台运行时更改数据；独立不同语言/算法的 oracle 复核关键字段及规范 digest，不只跑同一 builder 的自比较。
3. 旧已接受对象四表 `6337/12106/50162/1` 保留源逐行规范摘要；新投影产生的 740,703 差异的归因与**新语义是否批准**分开。Focus 328 个 ID 重建的影响必须验证收藏/跟踪/持久引用/旧链查询，不得静默替换旧身份。
4. 联合 Head V2 做多 writer、CAS 失效、部分提交、PG断开、客户端读取期间切换、读写权限降级、旧版读回、恢复新 descriptor、跨实例恢复新签名，出具完整事务与状态转换证据。
5. 跑“冻结源原件仍完全相同”可验证清单；已知早采/晚采、硬链接/子进程限制不可在未经补证时改为 FULL。

**出口**：`PG_CONTENT_AND_IDENTITY_ORACLE.csv`、`JOINT_RELEASE_CAS_FAILURE_RECOVERY.json`、`PG_ROLE_GRANTS_NEGATIVE.json`、`OLD_NEW_AUTHORITY_DIFF_APPROVAL_MATRIX.csv`、`ROLLBACK_E2E.md`。隔离 PG 内容比较和回滚差异为0；未经用户授权正式 Head/role 一律不切。

### P0-4｜全量算法/§87A字段合法语义分母/复权56消费者

1. 从当前 V4.2.2 REV4 正文抽取每条**规范性需求原子**，而不是把84版本/674注册记录/37,264 schema 属性视作设计已实现；分别给出合法需求总数与 §87A 版本化字段总数，去重规则公开。
2. 字段矩阵至少包括：字段/公式/单位/窗口/阈值、输入及来源 SHA/首次可用时点、PIT与缺失质量、生产者、PG schema/索引、合法板块成员/横截面、真实消费者、API/UI、反事实和同形异因负例、当前代码定位和状态。
3. 特别审 Core、Amount A、RPS、行业概念/板块主线、状态D0/D1/D2、结构突破/回踩/失败、主线早期观察、Focus全集与Validation Cohort严格分离、事件和Forward；字段存在/JSON可解析≠实现正确。
4. 精确复权 v0.3 typed numerator/denominator、来源 digest 及 `exact_*`缺失 fail-closed；对**56类真实调用者**逐类标 `REACHABLE / LEGACY / CONDITIONAL`，有源字节、输出变化、复算oracle、PIT/质量、字段/图表/Rank/Core/Focus/Forward影响。若旧有理数信息不全，不把 `Fraction(近似Decimal)` 冒充精确因子。
5. 检验 7 股16价差修订、1,081 Core历史值变化及845历史RPS敏感结果时，继续说明重构成员≠历史合法 PIT；形式不足的旧日期不能伪装真 `FIRST_OBSERVED`。
6. 对本阶段无法得到合法20日H21/PIT和Forward成熟的对象输出 `UNKNOWN / RECONSTRUCTED / PENDING_MATURITY`，同时实现相应缺失处理与前置校验。

**出口**：`V4_NORMATIVE_ATOM_DENOMINATOR.json`、`V4_FIELD_SEMANTIC_COMPLIANCE.csv`、`EXACT_FACTOR_56_CONSUMERS.csv`、`ALGORITHM_INDEPENDENT_ORACLES/`、`DATA_QUALITY_AND_TIME_CONSTRAINTS.json`。所有立即可审需求 `PASS` 或有明确业务 bug 修复/独立验证；真实来源/成熟尚缺者独立列门，不能对外声称其正式已通过。

### P0-5｜全链整合与外部复核准备

1. 上述 P0-1～4 在相同隔离版本上集成，执行**一次完整端到端**：原来源冻结→PG ingestion→daily producer→market/sector/stock→状态/信号/Focus/Cohort→snapshot/series/journal→联合Head→六入口/API/chart/history/replay→Forward正确 fail-closed→重启恢复/回滚；记录同一 T0 / token。
2. 复查 R3已修 FA-001/005/013/014/017，更新当前有效函数/源码 SHA/行号，历史位置保留。FA-020治理扫描性能须优化且所有匹配、行号/类别/文件路径和原完整负例结果完全一致。
3. 六入口完成桌面宽/390移动宽实际浏览器操作和可用数据验证；修复 `390x844 document_width=487` 溢出，检查长表、筛选、chart切换、真实错误、未知数据、历史日期跨页保持、数量与接口数一致。不能把HTTP200误当可视结果。
4. 按实际工作负载分别给出首页6.31MB基准、冷/热延迟、P95、1/4/8并发、吞吐/RSS，以及内容哈希全表复验开销；改造 immutable snapshot/投影/有界分页，但不能降低安全检查或在无批准阈值下自签性能PASS。
5. 出最终 scope/PG/全功能/字段/算法/UI/安全/资源/恢复多轴审计目录和所有OPEN的唯一 owner；交给独立外审。开发者不能在此签 `EXTERNAL_ACCEPTANCE_PASS`。

**出口**：`V4_FULL_ENGINEERING_E2E_RESULT.md`、`V4_FINAL_ENGINEERING_GATE_MATRIX.json`、原始JUnit/log/Browser证据、完整源码和数据绑定 SHA、全链实际数据库连接日志、完整真实消费者证据、错误及恢复脚本。失败任何核心门维持 `ENGINEERING_BLOCKED`，不靠删测试收尾。

## 4. 三类可并行的后续门，不许伪造提前关闭

### C1｜2026-10-12 及以后的真实交易日

只有实际交易会话成立且数据合法到达时：记录源采集时间、provider/source SHA、首获/发布时间、PIT资格、缺失/停牌、PG事务、QA、联合 Head CAS/读回、六入口同T0/同token及重启重跑。无法准时得到新源则 `PENDING_REAL_SESSION` 或 `SOURCE_INCOMPLETE`，不得合成新的日更证据。可以先做好所有采集和故障演练，不等待现实日期停止P0。

### C2｜H21、真实 Cohort 与 Forward/FEP成熟

H21 必须有真实的20个合格历史 PIT 会话；完整 Cohort 包括入选/未入选，不能用用户 Focus 代替；FIRST/ANY label、D0/D1/D2及 T+1/3/5/10/20 逐个按照固定的交易日定义成熟。无足够真实 OOS 就保留 `PENDING_MATURITY`，工程功能可以完成，不允许真实模型或 Priority V2 被自动授权。

### C3｜Windows实体/生产 PG 正式切换

必须先拿到 P0全工程闭环、独立外审的可批准门、备份/逐表对照/回滚、角色最小权限、真实安装/启动/停止/登录/托盘/断网及真实进程全加载证明的计划；由用户另行确认维护窗口与授权。不能因任务卡、push、隔离PG PASS而直接停在役PID、改生产DSN或正式 Head。

## 5. 建议批次与强制停点

| 批次 | 并行范围 | 必须提供的检查点 | 未达标的动作 |
|---|---|---|---|
| B0（立刻） | 冻结SHA/环境；合法范围与动态调用图（P0-1第一半）；真实DB选路（P0-2第一半） | 精确 V4范围、owner、完整未关闭清单 | 不进入总验收，不随便缩小4568 |
| B1（同日可并行） | PG调度/桌面、消费者迁移、内容身份与CAS（P0-2/3）；语义分母/复权（P0-4） | 每包有真E2E和负例，不只有unit | 单点失败只阻断依赖，其他包继续 |
| B2（工程整合） | 补V4合法fixture、4568逐节点处置、全 V4 clean run、六入口/性能 | 确定测试分母＋完整JUnit＋无非PG意图＋同Head消费 | 未绿继续修，不能把206替代全测 |
| B3（独立外审） | 在最终冻结SHA上独立复核数据、代码与报告 | `SCOPED` 与 `FULL`分开签、剩余C门分开报告 | Codex不能自签外审或生产 |
| B4（未来事实/授权） | 新T0、真实成熟、实体Windows/生产切换 | 分项真实来源/权限/回滚/在役证明 | 不影响B0–B3持续推进 |

## 6. 最终统一验收口径

工程可以独立完整收尾，当且仅当：

- **合法 V4 需求及测试分母均确定**，分母来源、节点集合、excluded旧V3的复审理由和新增覆盖无歧义；V4立即可执行的全回归无未解释FAIL/ERROR/非法SKIP，且原4568不被抹去。
- **全部受支持 V4 当前业务入口在动态运行下只有PG业务数据库意图**，PG不可用时fail-closed，无SQLite/DuckDB业务后门；旧库读取仅为隔离只读oracle。
- **全部立即可接通的真实消费者**在真实HTTP/桌面/worker/回放/发布链被验证，没有仅以“类存在”“直接unit PASS”替代真实走通；数据来源未批准的消费者必须有可定位条件门，不称已正式消费。
- **计算/身份/状态/Head/PIT边界**有独立数值/字段/来源/时间/权限oracle；跨版本差异经单独批准，恢复/回滚反例通过。
- **六入口、前端、性能与Windows工程功能**有完整可读的证据，性能阈值未批准的保持容量状态OPEN；Windows实机和正式生产切换单列授权。
- 报告机器状态分为 `V4_ENGINEERING_FULL_PASS`、`V4_DATABASE_RUNTIME_PG_ONLY`、`V4_LEGAL_REGRESSION`、`V4_NORMATIVE_SEMANTICS`、`EXTERNAL_ACCEPTANCE`、`PRODUCTION_LOADED`、`REAL_T0_PIT_H21_FEP`；不得用单个总体PASS覆盖细分事实。

当 B0–B3通过而C1–C3仍缺未来事实或权限，正确写法是：**`V4_ENGINEERING_FULL_PASS; EXTERNAL_ENGINEERING_ACCEPTANCE_PASS; FORMAL_REAL_SESSION/MATURITY/PRODUCTION_ADMISSION_PENDING`**，不是无限期待未来“全部GREEN”，也不是假称正式 FEP/实盘已上线。

## 7. Codex 一次性启动指令

读取本任务卡与上位《V4_R4_CONSOLIDATED_EXECUTION_MASTER_PG_ONLY_20261011.md》，再读取仓库当前 `docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`、`r4_external_repair_r2_20261011/R2_DISPOSITION.json` 和最新 R4 报告；冻结隔离 HEAD 后按 B0→B1→B2 实施。只处理真实 V4 与合法可达依赖，完全 PostgreSQL-only；禁止运行整套 V3/老系统测试。优先解决唯一合法 V4测试分母及全部真实消费者，继续完成DB01/02/06/08/09/12、Snapshot/Series/Journal/Shadow联合Head、精确复权56类、§87A字段与算法语义、六入口/性能。可立即完成的工作不得等待10/12真实交易日或FEP成熟。保留所有旧基线，隔离G盘PG、TDX和已接受Head只读，禁止生产切换及新Grant。每批推送代码、原始证据、实际执行源SHA、合法分母、独立oracle与读回收据，同步Google Drive正式项目任务夹。直到独立外审签收前，总状态继续BLOCKED；清楚区分工程闭环与未来数据/权限门。


# 大A V4｜R4 全系统整改与独立验收总任务卡（R3审计合并版 + PostgreSQL-only架构统一）

> **合同版本**：R4-MASTER-R1 / 2026-10-11（北京时间）  
> **性质**：交付给 Codex 的唯一下一轮总调度卡、开发和验收合同；不等于任何生产变更、正式 Grant 或外部验收许可。  
> **目标仓库**：`NanOns/a-share-market-structure-research`  
> **目标分支**：`codex/v4-fp14-r2-repair`（开工先重新冻结 origin HEAD；制作本卡时为 `fbd23a6ba08d0948fe7ad421d1765fe363648522`）  
> **输入1（最高的本轮外审事实依据）**：Drive《V4_FULL_SYSTEM_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261011.md》，文件 ID `1_1huGRGIcE5briW38cZBLxBvdOtbD1nt`  
> **输入2（Codex R3证据）**：`docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md` → `full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md`、`EFFECTIVE_AUDIT_ITEMS_R3.json`、`B3_V4_FULL_REGRESSION_RESULT.json`、原始 JUnit 与源 SHA。  
> **输入3**：现行 V4.2.2 REV4、正式 FEP R2、当前有效阶段合同、`AGENTS.md`、当前用户范围指令。冲突时：用户明确的 **V4-only + PostgreSQL-only** 范围优先；旧规范保留历史原件并记录版本化冲突处置。  
> **唯一当前系统状态**：`EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE`。本卡发布并不改变之。  
> **冻结要点**：用户仅要求 **V4 版本全部功能/设计/当前相关的真实运行路径**；**不修、不验、不跑 V3 及更早旧系统的整套测试**。V4 生产业务数据存储、事务状态、索引、读写服务和数据库运算连接统一 PostgreSQL；不得以“PG是主库”掩盖 SQLite 或 DuckDB 业务路径。

---

## 0. R4 总目标、工作范围及禁止事项（P0，不得跳过）

### 0.1 目标

R4 结束时应当同时做到：

1. **架构**：当前 V4 主服务、桌面端、自动日更、历史图、研究快照、持续发布以及 V4 合法可达的研究与运维消费者，在业务数据库职责上全部采用 PostgreSQL；停止生产/正式候选路径上的 SQLite 数据库和持久化 DuckDB 文件依赖，且 V4 正式运行时不依赖内存 DuckDB `postgres_scanner` 作为数据库兼容引擎。
2. **现有缺陷**：将 R3 已修 A1/A2/A3/A5 正式归档为“范围内工程通过、外部复审待签/已签”的精确状态；继续处理 A4 精确复权真实消费、A6 页面容量、FA-020 扫描性能、R3 回归失败，不把候选数值通过宣称为正式生产生效。
3. **验收**：构建基于真实 V4 功能/依赖/契约的**合法测试分母**，有独立 PG 环境、确切源码 SHA、原始日志/JUnit 与逐项 FAIL/ERROR/SKIP 处置。R3 245个模块/4,568个用例是**必须解释的原始冻结基线**，既不能偷偷缩小分母，也不能不经判断声称它等于全部合法 V4 测试。
4. **推进节奏**：A/B/数据库设计、隔离实现、代码修复、独立反例验证可以并行。后继真实交易日、20 个合法 H21 PIT 会话、Forward OOS、实体 Windows 安装等**各自保留门禁**，不得成为其它可开发任务停工的借口。

### 0.2 绝对范围——仅 V4，不包含以前系统

**允许、要求覆盖**：
- V4.2.2 正式模块、§87A 全画像/字段、V4-00～22 当前阶段设计及其**实际可达依赖**；V4 核心数据/市场/板块/个股/Focus/状态/信号/日更/Research UI/六入口、正式合同下的 FEP、Windows V4 桌面端；V4 使用的历史兼容接口适配层。
- `src/workbench_service/`、`src/workbench_analysis/`、`src/workbench_db/` 等目录中**真正从 V4 入口可达**的旧名字函数，或者 V4 兼容包装；它们因可达而属于 V4 义务。测试是否纳入由**生产调用证据+适用规范**决定，不由目录名或 `v3` 子串决定。
- `tests/v4...`、`tests/fep...`、V4/PG 合同等直接测试以及**现行 V4 的真实依赖测试**；迁移组件的隔离 PG / 原旧索引只读对照。

**本轮明确排除**：
- 老 V1/V2/V3 工作台、历史 M2/M12、旧 DuckDB 单库、旧版 GUI/扫描器战法本身的功能升级、旧 V3 的全部集成/回归 suite；不调用 `pytest` 全仓库收集并强行把老库迁移到 V4 作为验收前提。
- 旧 `run_*`、早期 `workbench` 兼容入口在**没有证据能从当前 V4 主入口抵达**时，仅登记 `LEGACY_UNREACHABLE_PRESERVED`，不主动修复、删文件或执行其测试。
- 历史报告或旧审计里的 DuckDB 路径不能因字符串出现即定成 V4 实际事故；相反任何真实 V4 SQL/存储调用即使位于旧文件也不能排除。
- 旧版向后兼容诉求**不得反向要求 R4 运行 DuckDB 兼容测试、补齐老 DuckDB 测试夹具或恢复其运行**。

**安全底线**：
- `D:/new_tdx` 及所有 TDX 根永远只读；旧 Owner、strict/accepted/operational Head、当前生产 PG 库、SQLite 原始日记/索引、发行物、旧 T0 冻结、真实 Grant 全部只读保护。候选仅写新命名空间和 G 盘工程根：`G:/codex_tmp`、`G:/codex work`。
- 未经用户单独授权不改变生产 PID/监听端口 28765、不重启在役服务、不切换当前数据 Head、不执行历史回填冒充 PIT、不启用实盘预测/自动交易、不更改治理硬门。
- 不许通过删除/改名测试、全局 `skip/xfail`、临时禁用契约、允许静默退回 SQLite/DuckDB、修改历史接受产物，来换取“全绿”。

### 0.3 数据库边界的统一定义

- **PostgreSQL-only**：凡用于 V4 业务逻辑的**持久化状态、行情/因子/研究表、任务/队列/锁/CAS、版本化索引、服务查询和正式计算数据库连接**，统一原生 PG 驱动/SQL；业务报表可使用纯 Python/Pandas 等分析而无 DuckDB 数据库连接。
- **合法文件**：TDX 本地原始数据、GBBQ、ZIP、CSV、Parquet、JSON、MD、不可变 Head、图片、审计证据、日志、模型产物等属于源资料/审计附件或导出文件，**不因其不是 PG 而删除**；但不能把 SQLite/Parquet/JSON 文件悄悄当成正式业务状态库、唯一索引或事务控制的后门。
- **旧数据库原件**：`jobs.sqlite3`、`history.sqlite`、`research.sqlite` 等在迁移窗口只允许源侧冻结/只读对照；新 V4 正式运行不得在这些文件上执行写入、查询或降级回退。旧原件长期按治理策略留档，不原地覆盖。
- **DuckDB 两种状态须分别判定**：文件持久化 DuckDB；内存 DuckDB + `postgres_scanner` 接入 PG（虽 PG 保存表，也**不满足本卡的 V4 原生 PG 运行时目标**）。旧 V3 不可达使用不参与整改，但登记范围证据。

---

## 1. 上轮结论继承与唯一问题基线（不得重写历史）

| 问题/批次 | R3 已证明 | R4 必须关闭的剩余门 | 立即能否推进 |
|---|---|---|---|
| FA-001 / A1 | 首页风险事件优先级 `setdefault` 修复、1,956 组合+5日只读 | 最新 SHA 外审收尾、真实生产加载单列 | 可以 |
| FA-005 / A2 | 工程 G 根 allowlist、kind 防路径注入、junction等18项 | 当前配置/源SHA与独立路径验证；不授权FEP实盘 | 可以 |
| FA-013/014 / A3 | 代码别名/日期比较、stock RPS vs sector RS、四模式浏览器 | 当前源码定位与有效状态、真实只读复核 | 可以 |
| FA-017 / A5 | 全空 LOO candidate02 和输入日期检查 | 候选闭环，正式 D2/LOO 另门 | 可以 |
| FA-016 / A4 | 精确有理数v0.3候选：5,224股/2,162,962日线/8,636,512QFQ格，7股16价差订正 | 56类调用者、精确系数 transport/无效输入fail-closed、1,081 Core变化/845 rank敏感性、PIT和正式 Owner 准入 | 可以 |
| FA-004 / A6 | 首页约6,313,877 B；冷读约12.73/9.80秒；并发 1/4/8 P95约1.01/2.98/4.44秒；RSS约4.55 GB | 明确性能门、不可变请求快照、载荷/并发优化和复验 | 可以 |
| FA-006 / B3 | 245模块、4,568项：3810 PASS/237 FAIL/209 ERROR/312 SKIP；598项定向重跑未全绿 | 正确V4分母、guard误通过审计、446失败与312跳过逐节点处理、全量重跑 | 可以 |
| FA-009 / B1 | 84版本、674记录、298字段名、37,264原子；5组小范围语义复核 | 合法设计全分母与每字段producer/source/time/quality/API/UI/反例 | 可以 |
| FA-002/003/011 / B2、D | FIRST 120排列、ANY部分合成；正式标签仍disabled | prior/PIT/D0D1D2、完整Cohort、成熟/OOS和Formal Grant | 工程可推进；部分需等待合法源 |
| FA-012 / B4 | 当前可比较金额表示已有受控数值证据 | 378板块H21需要合法20日PIT，不得默认KNOWN | 实现/审计可推进；正式门等待 |
| FA-018 | `operational_daily_jobs_v1.py` 使用 SQLite | 改 PG 调度全职责及桌面控制、迁移和重启恢复 | 可以 |
| FA-019 | 图表pack和BFF使用`history.sqlite`，实际绑定约426MB | PG 历史索引与所有图表查询合法替代 | 可以 |
| FA-020 | symbol治理扫描重复前缀计行O(N×M) | 优化+原规则/命中/行号语义不变 | 可以 |
| AR3-E04 | `EFFECTIVE_AUDIT_ITEMS_R3.json`个别行号指向修复前位置 | 有效定位函数/源码SHA/当前行号，保留历史位置 | 可以 |
| FA-008 / C | 10/12后继真实交易日截至本卡未发生 | 真正下一交易日首次接收/增量/冻结/回放 | 等真实源 |
| FA-007 / E | Windows工程包证据不等于实体生产加载 | 用户授权真实安装/重启/回滚/进程加载证明 | 需另授权 |

上表中回执大规模数值为 Codex 冻结环境的**可复核证据声称**；外审没有独立取全量用户本机 G 盘数据重跑，不得改写其真实性边界。R3报告和R1/R2原件均版本保留。

---

## 2. R4-00｜先冻结 V4 范围与验收环境（全批次共同前置）

**负责人**：Codex 自定并写入 `OWNER_REGISTRY_R4`，禁止空 Owner 不说明。**验收状态**：`NOT_STARTED`，不可预填PASS。

1. 拉取目标分支最新远端 commit SHA；记录工作树脏文件、运行态旧 PID、版本、当前PG DSN指纹（**不得泄露口令**）、合法 schema、所有保护目录的 SHA/文件数。
2. 读取 Drive/R3输入和适用 V4 合同；冻结版本与审计事实来源：`R4_SCOPE_AUTHORITY.json`。仓库变更过程中若新 commit 到来，必须按自上次冻结 diff 增补和重测，不能继续使用已过期 SHA 宣称最新。
3. 基于真实可达入口（`run_workbench_service.py` 默认V4 → `EngineController` → `core_product_server_r1`/`DailyJobs`；桌面 V4；V4正式 daily entry；实际 V4 查询/发布消费者）形成 `V4_RUNTIME_CALL_GRAPH_R4.json`。包括动态 import、UI API 请求、后台worker/subprocess、脚本启动、权限条件、生产实际加载hash；不能只用 AST 字符串频率代替可达性。
4. **双清单**：`V4_INCLUDED_CAPABILITIES` + `LEGACY_EXCLUDED_WITH_JUSTIFICATION`。每个旧模块必须有“是否在V4生产调用路径/适用设计/实际被调条件/对应测试”证据。不许因目录名 `tests/phase1`、`tests/governance`、`v3`、`duckdb` 等机械判断。
5. 以 `config/v4_audit_regression_scope_r3.json` 245 included / 620 excluded 为**旧基线**冻结 `R4_V4_TEST_SCOPE_V2.json`。对两类都做实际依赖复核，指出被遗漏的V4真实义务，并剔除确证仅旧V3且不被V4消费的测试；变更前后每模块/用例count、原因和覆盖合同都要报告。
6. 仅启用 **G盘独立 PostgreSQL**，验证 `data_directory` 真实路径、pg版本、数据库身份、迁移001—033状态与约束，不使用生产DSN。对 SQLite/DuckDB V4运行连接设置独立不可误判负例的 fail-fast guard；**迁移对照测试允许在隔离进程对冻结旧文件作只读访问**，不计正式 V4运行例外。
7. 修正 B3旧 `ValueError` 数据库护栏：不应被业务 `pytest.raises(ValueError/Exception)` 误满足，使用专用Guard异常与 per-node 真实触发证据；比较首次4568执行中哪些PASS没有业务语义保证。

**退出证明**：产出静态+动态 V4 范围清单、范围差异表、冻结 SHA、隔离PG/断路测试与 `R4-00_SCOPE_GATE.json`。若不可知，状态 `NOT_VERIFIABLE`，不能造真。

---

## 3. R4-01｜全 V4 数据库使用审计与 PostgreSQL-only 架构合同（P0主线）

### 3.1 必审模块矩阵（新增DB-01～DB-09）

| ID | 现有源码定位 | 事实/风险级别 | 必须审计或整改 |
|---|---|---|---|
| DB-01 | `src/workbench_analysis/operational_daily_jobs_v1.py` | **已证当前V4**：`runtime/dynamic_daily/jobs.sqlite3`、`sqlite3.connect`、WAL/FULL；FA-018 | PG调度、策略、job/attempt/event/checkpoint/rearm/cancel/异常与重启迁移 |
| DB-02 | `src/workbench_desktop/jobs.py`、`engine.py` | **已证当前桌面链**：SQLite连接+状态读 | 统一使用 PG job repository，桌面启停/status不得另读旧SQLite；Windows断线fail-closed |
| DB-03 | `scripts/build_core_product_read_pack_r1.py`、`src/workbench_service/core_product_bff_r1.py` | **已证当前V4 chart**：建/查 `history.sqlite`，FA-019 | 建PG版本化历史读索引；RAW/QFQ、D/W/M、时点、身份、暂停/缺失、分页读数一致 |
| DB-04 | `src/workbench_service/production_v4.py` | **存在V4代码及已绑定快照Owner**：`research.sqlite`/`daily_research.sqlite` 及只读 SQL | 建 PG 研究快照模型/只读 BFF；判断当前默认入口是否调用，再做候选迁移；不误称一定在当前默认PID运行 |
| DB-05 | `src/workbench_service/research_bff.py`、`v4_server.py`、`continuous_daily_release.py` | **V4潜在可达旁路**：`ProductionV4ResearchReader` 和SQLite持续发布校验 | 显式入口/权限/当前 manifest 调用证据；所有合法 V4 旁路去 SQLite，过期旁路标记并隔离不可达 |
| DB-06 | `src/workbench_db/api_connection.py`、`research_builder_repository.py` | **混合引擎存在**：内存 DuckDB + `postgres_scanner`/PostgresResearchBuilder | 证明与现行V4路径关系；若可达替换原生 psycopg/PG SQL，记录等值、排序、NULL、时间、decimal及性能 |
| DB-07 | `src/workbench_service/app.py`、`run_workbench_service.py`的 `--legacy-v3` | **旧链存在**：DuckDB文件、旧PG+DuckDB适配 | 用户本次**不修旧V3**；证明当前V4默认入口不会走旧工作台；阻止隐式 fallback；保留 `--legacy-v3`为不在当前V4验收范围的历史入口，不可混同 |
| DB-08 | `src/workbench_ops/storage.py`、`src/workbench_db/{backend_provider,storage_connection,config_store,repository,read_repository,history_job_repository,...}` | 混合旧repo和PG repo，默认可能建DuckDB | 对所有 V4 可达的运维/备份/历史写入/API解析做实际DI与调用证明；可达则原生PG替换，不可达记legacy保留 |
| DB-09 | V4/FEP/Radar/Focus/Forward/市场状态及 jobs/快照以外的数据库接口 | **尚未穷尽**，不能凭当前九行称全局无遗漏 | 遍历V4入口真实 import/call graph、连接工厂、配置/环境变量、数据库文件 open intent、server subprocess、HTTP consumer，发现任何第三方DB新增版本化 `DB-XX` |

> **必须区分**：FA-018调度SQLite、FA-019图表SQLite、`production_v4.py`快照SQLite为不同持久化职责，不能只迁移两个文件就宣称全系统 PG-only。用户设计约束覆盖当前V4正式及其合法可达旁路；旧遗留不可达不必修复。

### 3.2 数据库发现手段（不准只做grep）

- **静态**：Python AST、import别名/动态导入、`sqlite3`/DuckDB/SQLAlchemy/数据库URL、文件后缀、`connect` 工厂、函数/方法封装、`PG` 混合桥、Popen脚本引用、UI route→BFF→repo。
- **运行态**：G盘隔离主服务与 V4 桌面工程副本，冻结 HEAD，逐入口发出真实合法请求；patch/hooks/profiling记录 `sqlite3.connect`、`duckdb.connect`、`psycopg.connect`以及engine/db identity，写 `DB_CONNECTION_INTENT_LEDGER_R4.jsonl`，按模块、SQL用途、调用栈、入口、版本、读写、实际文件等分类；任何未授权非PG意图触发失败，不允许 fallback 隐瞒。
- **数据目录**：识别 SQLite实际存在、可读、可写、被 manifest绑定和与当前生产 PID 的关系；不可证明可达性用 `SOURCE_CONFIRMED_REACHABILITY_OPEN`，而非冒充实际使用/不存在。
- **数据库提供者规范**：所有V4 PG仓储实现统一配置/生命周期/连接池、超时、权限、事务及迁移策略；不得同名 `Postgres` 包装在内部建DuckDB作为默认 query engine。
- **外部核查**：每类基于冻结源/受控输入独立比较新旧完整结果+反例；对V4真实运行检查不需要已达到20日 H21 或 FEP真实OOS。

### 3.3 交付

`DB_INVENTORY_R4.csv`（至少列：ID、模块路径、入口、caller/callee、current_pid_loaded、database_engine、persistence_file_or_schema、operation、read_write、authority、risk、migration_batch、source_sha、reproduction、status）、`V4_DB_CALL_GRAPH_R4.json`、`DB_DESIGN_POSTGRESQL_ONLY_R4.md`、`DB_BACKEND_NO_FALLBACK_GATE_R4.json`。每一非PG依赖要有责任人和合同，不能只给示例。

---

## 4. R4-02～R4-05｜PG 业务改造执行卡（开发不必等待10/12）

### R4-02 / DB-01+02：日更调度+桌面控制 PG 迁移（P0）

**设计要求**：新版本 `V4_PG_OPERATIONAL_JOB_STORE_R1`（名称可版本化但不可偷改旧合同）。PG表/约束覆盖：`scheduler_policy`、dispatch、attempts、rearm、jobs、job_days、checkpoint、audit events、worker lease、idempotency key、source revision、cancel/retry/terminal state。定义键、唯一约束、版本号、timestamp时区、事务范围、原子CAS、取消竞争与进程恢复。任何 `ON CONFLICT` 要说明冲突处理，不得丢历史。

**迁移**：只读冻结旧 `jobs.sqlite3` 的一致性快照和SHA；对每张表/状态映射做 count、主键、字段值、时间、排序、状态机、事件链校验，重复执行幂等、不重放已发布 T0、不多派发同日任务；在 G 盘隔离 PG 做升级/回滚，原 SQLite 保留；切换窗口只在正式授权后。

**测试**：启停与托盘/桌面status、调度开关、同日多次source重试、revision rearm、断网/PG失联、重复启用、取消vs提交并发、跨日、夏令时/上海时间、进程崩溃、WAL源的只读复制可用性、并发两worker竞争、CAS和恢复；对旧状态另取只读 oracle。不得把 `sqlite3.Error` 捕获静默当 `PG` 成功。

**硬门**：DB-01+02 `ENGINEERING_PASS` 要求全场景符合，生产服务当前状态/Head/PID不变。未实测断电者单列 `PENDING_PHYSICAL_RESTART`，不伪签。

### R4-03 / DB-03：历史K线 PG 读索引迁移（P0）

**设计要求**：新 versioned PG表/视图，键至少含 `read_pack_version/head_token/T0/security_id/trade_date/price_basis`（如周月聚合需明确粒度与派生策略）。保证同一个请求永不读混合发布日期。日期 cutoff、symbol历史 alias、OHLCV/amount、RAW/QFQ与质量/UNKNOWN、停牌、复权事件校验、D/W/M、区间/分页、周月未结束处理全部与已准入原冻结语义一致。

**迁移与验收**：旧 `history.sqlite` 只读、完整sha保留；G盘 PG 构建新候选，逐股逐bar、统计、QFQ订正版版本切换前后的差异来源，月/周、虚假未来、空值、非交易日/停牌/旧代码、图形动态范围、多日期、分页全检查；需要在当前5个冻结日做完整HTTP/浏览器读回比较。**复权v0.3未授权时不得悄然改变其已接受QFQ，需另版本区分。**

**索引/性能**：索引规划/EXPLAIN、5,224股整体、热/冷浏览、同时请求数、PG磁盘/索引成本、保留档案一致性。当前 chart URL不能回退读取 SQLite。

### R4-04 / DB-04+05：V4研究快照/持续发布 PG 迁移（P0）

**先确认可达性**：`production_v4.py`/`research_bff.py`/`v4_server.py`/`continuous_daily_release.py` 具有真实 SQLite 代码和冻结 snapshot 指针，但不是所有分支都已证明从当前生产默认入口调用。必须用 route map、读取授权、联合发布 `joint_release`、真实 dated accepted read 测试核实。

**如果合法V4功能仍可达**：迁移 `objects/aliases/members` 与完整研究快照域（market、sectors、stocks、radar、events、Focus、Forward、settlement、sources）、过滤/排序、分页、状态质量、字段来源、历史日期、身份别名、观测时点、snapshot read isolation 和 `joint CAS`。PG 新命名空间/manifest bind，原旧 snapshot SQLITE 可作为隔离比较 oracle；连续发布 QA 不再直接 `sqlite3.connect`。做到实际 PG commit+manifest一致后才能标为新候选。

**如果不可达且仅为历史**：给出可重现的 `LEGACY_UNREACHABLE` 证明并从 V4 loader/依赖树移除其可执行路径，不强行迁移用户不会再使用的旧系统；但这必须通过 V4 所有受支持入口、历史回放入口、生产升级/回滚路径的负测试证明。不能因为默认首页没调用就排除历史日期/rollback消费者。

### R4-05 / DB-06～09：DuckDB兼容/运维等非PG路径收束（P1）

1. 对 `PostgresDuckDBApiConnectionProvider`、`PostgresResearchBuilderRepository`、`DuckDBStorageConnectionRepository`、`event_store`、历史写/读库、backup/config/migrations、旧 V3 API 逐一给出 `V4_REACHABLE_YES/NO/CONDITIONAL/UNKNOWN` 和可达证据。
2. 任何合法 V4 默认或启用功能可达的内存 DuckDB bridge，迁为 PG 原生查询/psycopg + Python无数据库分析；保留时间/Decimal/NULL/排序/窗口/聚合/大表分页、事务和本来合法的样本集合等价性；不得因改SQL丢掉业务功能。
3. 保留不可达的旧 V3 模块源码/历史测试，不运行、不批量升级、不迫使完成其旧门；对 V4 生产启动添加禁止旧 DB fallback 的实际验证。
4. 如果出现 SQLite 以外的数据库（例如另一个轻量索引、嵌入式状态库、ORM fallback），追加 `DB-XX`，不可在没有证据时声明“只剩两处”。
5. 定义 `V4_DB_PG_ONLY_ACCEPTANCE`：生产V4受支持入口动态运行 **0 SQLite持久化连接意图、0 DuckDB数据库引擎连接、0向SQLite/DuckDB业务DB写入/降级**；且PG DSN错误时显式失败而非启动旧数据库；旧历史不可达或工程隔离的 source-read 不计入正式runtime，但要明确标识与证明。

---

## 5. R4-06｜V4-only 测试分母与全量回归修复（P0，并行主线）

### 5.1 原始证据不可覆写

R3 V4 manifest：245 modules / 4,568 cases = **3,810 PASS + 237 FAIL + 209 ERROR + 312 SKIP**。4568是执行过的已知集，不等于已获证“全部 V4 需求”；旧 full-run 的 BaseException/ValueError护栏混淆仍影响某些正向判断。另对598节点定向复验为435 PASS、98 FAIL、64 ERROR、1 SKIP，**不得拼接**成为新“全量通过”。

R3 446 个 FAIL+ERROR 的现有分类：
- SQLite意图被拒97：涉及DB改造，不是简单标记范围外；
- 缺精确冻结fixture 143：只修当前V4真正需要的输入；
- 历史PG fixture/identity缺口49：恢复当前V4合法source/order，不能模拟 accepted；
- 未解析断言/运行时73：必须查业务语义；
- 真正历史V3兼容2：若不可达可合法排除；若V4适配必须改为PG测试；
- 文件权限1；
- 独立PG启动超时81：先检测PG真实ready/DSN/init schema，再从测试问题定位。  
分类数量合计446，但每条是否正确仍需逐节点复核。

### 5.2 执行规则

1. **只启动显式V4测试套**：根据 `R4_V4_TEST_SCOPE_V2.json` 的经复核实际V4能力收集，禁止裸 `pytest`、旧 M2/M12 suite、为了跑旧库而装 DuckDB fixtures。V4真实能力即使被旧文件名测试覆盖，也要改写为PG-only的V4对应测试，而不是直接删掉保障。
2. 全新独立G PG cluster/DB，可核源SQL建表；通过实际服务、reader、job worker、chart与multi-date测试；禁止指向真实生产或开发主库。
3. **V4 runtime no non-PG**：在正常V4完整测试中，SQLite/DuckDB连接一律报非业务异常；**仅旧数据迁移oracle**可以在独立进程/只读快照访问原旧库并提供有界数据比较。不得为了满足旧版测试关闭护栏。
4. 修正负例：不得让数据库拒绝异常被 `ValueError`/`Exception` 断言误吸收；对原3810 PASS中受旧护栏影响的节点归类 `SEMANTIC_REPLAY_REQUIRED`。
5. 对每一个 FAIL/ERROR/SKIP 形成 `TEST_NODE_DISPOSITION_R4.csv`：nodeid、source SHA、适用V4 contract、执行入口、上轮状态、本轮结果、first failure、根因、是否实际业务断言、owner、修复commit、复验文件、合法豁免依据；**只允许已证实为纯旧V3、非V4可达**的排除，计数单列不作PASS。
6. 测试计数必须保留：原R3 4568原分母、新增V4能力测试、新排除确证旧V3、新V4合法分母、新PASS/FAIL/ERROR/SKIP。不得未解释就把 4568缩为100或将旧失败删失。
7. 完成所有可立即运行的V4测试后再**一次完整clean-slate**（已修护栏、已迁PG、精确fixture）全量重跑，提供JUnit/运行参数/每模块实际结果/变更源SHA；此结果失败则显式 `FULL_REGRESSION_NOT_GREEN`；缺新交易日或权限则分别标记条件门，不污染本轮可完成工程验收。
8. 对 SQLite兼容历史测试，不能先全局跳过再称“V4仅PG所以全部通过”；正确顺序是迁PG后重写适用V4断言，并用真实版本对照。

**硬出口**：`R4_V4_ONLY_REGRESSION_RESULT.json`、全JUnit、原始 stdout/stderr、`TEST_NODE_DISPOSITION_R4.csv`、guard阴性正例、生产外源的只读保证；外部审计独立挑样重现，不能Codex自签系统PASS。

---

## 6. R4-07｜R3 已修事项独立收尾与证据一致性

- **FA-001/A1**：同实体 INVALIDATED/EXITED/WEAKENED 等优先级组合顺序不变；五个冻结日对照；当前源码行号+SHA更新，区分latent修复和已发生线上事故。
- **FA-005/A2**：G `codex_tmp`/`codex work/fep_engineering` 精确根，路径穿越、junction/软链接、权限限制与kind 负例；不得扩大整个G盘写权。
- **FA-013/14/A3**：股票旧/新代码 alias 与不同时点、股票RPS/板块RS四模式、未知/歧义拒绝、HTTP+DOM；复核不误接未来身份。
- **FA-017/A5**：单成员/全空/交叉板块/共同T0、同市场无目标/只目标、单日校验；仅 candidate02，正式D2/PIT权限不变。
- **AR2-E01/AR3-E04**：新有效问题视图保留历史 `location`，增加 `effective_source_sha`、`effective_symbol`、`effective_line_range`、`supersedes`, 自动检查路径存在/当前SHA行号匹配。杜绝误引R3旧位置。

**出口**：每项 `SCOPED_EXTERNAL_ACCEPTANCE_PASS` / `NOT_VERIFIABLE` / `FAIL`，生产是否真实加载为另一字段，不得混同。

---

## 7. R4-08｜FA-016 精确前复权下游全链核对（P0正确性）

- v0.3精确有理数 `Fraction` 与每有效事件逆序合成的数学定义、2位HALF_UP、正负tie、同日多次、停牌间隔事件、非法除数、复权身份和事件来源及调整基准须写成**typed coefficient + immutable source digest**合同。
- `AdjustmentFactor.qfq_price()` / `hfq_price()`的 `exact_*` 缺失时目前存在 `Fraction(self.qfq_mul)` 的有限小数降级路径；对 v0.3 正式路径设明确 `EXACT_COEFFICIENT_MISSING`/不可用状态，不能丢精确有理数运输后仍宣称 v0.3 完全精确。
- 按R3已列 56 类消费者，形成真实调用图；逐一对 Core 画像、MA/ATR/return、RPS、相对强弱、结构/突破/趋势、状态D0/D1/D2、Focus、Forward/settlement、周/月K与API/UI的 **T0、PIT、source/quality、真实输出 delta、错误传播**。
- 完整复核旧价差7股16格，历史2,547证券日期/99,333 Core比较/1,081格变更和845 rank敏感性；原RPS使用当前成员重构**非合法历史PIT**，不得当正式历史绩效数据。
- 保留原 v0.2 已接受Owner字节，新 v0.3 独立版本、因子/字段/快照/消费者/候选manifest，支持回滚，正式迁移需额外授权；本轮优先工程验证和全量影响图，不因真实10/12未到而阻塞。

---

## 8. R4-09｜FA-004与FA-020性能优化（非数据库问题不阻塞主线）

**服务性能**：先登记产品合理负载、响应预算、带宽/内存约束与阈值来源（由设计依据确定，未经授权不可自造验收PASS）；保留R3基准 `6,313,877B / 首次约12.73、9.80秒 / 1、4、8并发吞吐与P95`，做同Head/token、两T0、冷/热、六入口、数据变更期间、权限失效、故障恢复的原始字节/语义对照。通过按请求不可变snapshot/版本化缓存/有界分页/瘦首页载荷改善；不直接去掉共享snapshot锁制造竞态。运行后比较CPU/RSS/P95、吞吐、完整数值，报告不可改善原因。

**治理扫描**：`scan_no_symbol_specific_runtime_logic.py`重复 `text.count('\n',0,match.start())` 的 O(N×M) 成本，版本化优化为单遍/索引计行；同时证明全部证券命中、行号、category、path、策略与中文/CRLF/Unicode、边界文本完全一致；保留原硬门，不移除真实风险项。仅审V4范围的治理扫描输入，旧V3原生扫描流程不入场。

---

## 9. R4-10｜继续全因子及正式研究主链审计（与DB改造并行）

1. **B1/FA-009**：从当前V4.2.2合同规范正文抽取真正合法需求/版本分母，逐字段包括公式、时间、输入/质量、owner、PIT、应用场景、PG表/consumer、HTTP/UI、正常/同形异因/边界反例；84版本674字段记录37,264个schema原子目前不能算完毕，39模块保持PARTIAL直到逐一满足。
2. **B2/FA-002/003**：旧日prior、D0/D1/D2、行业与概念历史成员变化、正式 M14/H21、完整 Radar、Validation Cohort（包括未入选）、用户Focus与样本分母隔离、Forward owners按现有合法输入继续设计和工程验证。没有历史首获证据必须 `RECONSTRUCTED / PIT_ELIGIBLE=false`。
3. **FEP**：FIRST按最早交易日/同日风险次序、ANY不互斥、T+1/3/5/10/20、右截尾、date-equal权重、ITT控制冻结/OOS防信息泄漏，正式label目标仍 `REGISTERED_NOT_ENABLED` 则保持门禁；不因sqlite迁完而误启用模型。
4. **Amount A/H21**：5,224最新股票的表示与有限窗口证据可复用，378板块的合法20日PIT仍UNKNOWN，不能填缺日冒充正式可消费。
5. **M14与符号检查**：原探针缺失如实标记；24个literal/identifier证据逐项业务路径审计，至少 `market_source_acquisition.py` 的真实smoke fallback单列；不能把所有symbol命中归为QA后全豁免。
6. **真实T0**：2026-10-12及后继的首获/增量/PG提交/当前六入口、FEP标签成熟各按其自然时间和独立授权验证，不暂停已具备条件的开发和审计。

---

## 10. 执行分批与并行、门禁状态

| 波次 | 可同时执行的卡 | 前置 | 执行后能标什么状态 | 不能标什么 |
|---|---|---|---|---|
| W0（立即） | R4-00范围/环境、R4-01 DB调用图、R4-06回归分流、R4-07旧修复独立收尾 | 读取本卡+冻结HEAD | `SCOPE_FROZEN`、`INVENTORY_READY`、各项`SCOPED_*` | 不可写全系统PASS |
| W1（立即并行） | R4-02 PG调度、R4-03 PG图表、R4-04研究快照、R4-05混合适配器治理 | W0中每对应路径和保护根确认 | `PG_CANDIDATE_ENGINEERING_PASS`（按包） | 不可直接接管现行进程/覆盖旧SQLite |
| W1（同时） | R4-08精确复权、R4-09性能、R4-10正式语义链 | 各合同及源SHA已冻结 | `SCOPED_NUMERIC_PASS/SCOPED_RECHECK` | 不可解锁 PIT/FEP/真实OOS |
| W2（隔离合并） | PG接口联调、跨DB事务/rollback、全合法V4用例无护栏误通过 clean run | W1对应候选ready | `R4_ENGINEERING_INTEGRATION_PASS`，如实列所有剩余门 | 不可声称已在生产生效 |
| W3（独立外审） | 外部复核差异、保护 SHA、PG-only动态连接无违规、全量业务回归 | W2证据包齐 | 单项外审结论；系统状态需按全部门独立判断 | Codex不得自签系统外审 |
| W4（未来真实源/授权） | 下一T0日更、FEP成熟、Windows实体部署和生产切换 | 时间/来源/显式授权 | 各自真实正式门的独立PASS/FAIL | 不得提前模拟通过 |

**不允许顺序上的错误**：即使 W4 没有完成，W0～W3必须持续开发与验证；W2通过也不强迫把受时间/权限门阻塞的整个系统宣布“全功能完成”。

---

## 11. 每项交付格式、QA、客观退出判定

每个子卡必须提交一个 **可审计增量包**（MD + JSON/CSV/JUnit/源代码diff及SHA），至少具有：

```text
R4_<BATCH>_RESULT.md
R4_<BATCH>_MACHINE_DISPOSITION.json
R4_<BATCH>_SOURCE_BINDINGS.json
R4_<BATCH>_TEST_JUNIT.xml
R4_<BATCH>_NEGATIVE_VECTORS.json
R4_<BATCH>_INDEPENDENT_ORACLE_DIFF.json
R4_<BATCH>_PROTECTED_READBACK.json
R4_<BATCH>_NEXT_OPEN_ITEMS.md
```

特殊包还需：
- PG数据库：`V4_DB_CALL_GRAPH_R4.json`、`DB_INVENTORY_R4.csv`、PG DDL migration/rollback、source DB readonly SHA、表/字段/行级delta、CAS和重启重放、无fallback的动态证据、真实DB路径证据、权限与时间交叉测试。
- V4范围/回归：`R4_V4_TEST_SCOPE_V2.json`、`TEST_NODE_DISPOSITION_R4.csv`、完整JUnit/log和 guard 误通过清单、两版分母 reconcile、隔离PG身份/readback；最后一次 clean run 不同于历史原run。
- 精确复权：typed coefficient传输和56类调用者、全部合法时间/源字段和消费者差异，正式/候选分离。
- 全设计：逐 Normative 需求原子字段主矩阵，module PASS/PARTIAL/FAIL/BLOCKED 数据有同一合法分母；不能用只扫描源码数字替代语义。

所有 JSON 须包含 `contract_id`、`base_head`、`source_SHA`、`run_utc`、`scope`、`denominator`、`negative_vectors`、`previous_status`、`current_status`、`evidence_links`、`owner`、`limitations`、`next_conditions`。对于生产无权限/未来日未发生，精确状态 `PENDING_PERMISSION` / `PENDING_REAL_SESSION` / `PENDING_MATURITY`，不得扩大为 FAIL，也不得标PASS。

### 验收拒绝条件（命中任何一条则对应门 `FAIL/BLOCKED`）

- V4合法运行/查询/发布路径仍需 SQLite 业务数据库或 DuckDB 引擎；PG坏时偷偷走旧库；迁移候选覆盖 accepted Owner 或生产调度。
- 测试分母无合法解释缩小、旧V3测试被强行纳入V4、V4必需测试因名称旧而排除、原 `FAIL/ERROR` 消失无逐节点证据。
- 把模拟/重构历史成员、未批准标签、缺20日PIT、负例由 guard 拒绝误通过，包装成正式可交易的成功。
- 跨日期/Head读取混用、生产数据库意外打开/写入，或者当前SQLite/WAL源文件被破坏。
- 仅有 Codex 自测 PASS、无可复核源码/数据SHA/外部结论；或旧R3报告被覆盖。

### 收尾文件与恢复入口

1. 递增生成 `docs/audits/full_system_r4_pg_only_<date>_<sha>/`，原 R1/R2/R3 文件逐字保留；更新 `FULL_SYSTEM_AUDIT_CURRENT.md` 指向 R4 的**有效索引**和继承项，不静默修改历史裁决。
2. 生成 `EFFECTIVE_AUDIT_ITEMS_R4.json`，FA-001～020、AR2/AR3和新增DB-XX均有唯一current disposition/真正Owner/源SHA定位；缺Owner继续OPEN不假填。
3. 明确分别报告：`V4_SCOPE_ACCEPTANCE`、`DB_PG_ONLY_ENGINEERING`、`V4_FULL_REGRESSION`、`EXTERNAL_ACCEPTANCE`、`PRODUCTION_LOADED`、`PIT/H21/FEP/REAL_T0/WINDOWS` 门，**一个状态不可替代另一个状态**。
4. 完成推送后提供最后 commit SHA、每包文件清单和真实可复现命令，重读保护 Head/旧SQLite字节及成功包、说明尚未通过与后续任务；Drive为长期正式项目主仓，按用户约定将QA通过的任务与审计结果同步归档。

---

## 12. Codex 一次性启动命令（直接复制到Codex）

> 读取 `V4_R4_CONSOLIDATED_EXECUTION_MASTER_PG_ONLY_20261011.md` 全文，并读取 Drive R3 独立外审报告、仓库当前有效审计入口和 AGENTS.md。只处理 V4 现行功能和合法可达依赖；数据库唯一目标为 PostgreSQL-only，任何 V4 业务SQLite/持久化DuckDB/内存DuckDB兼容查询都须归类整改，旧 V3/更早系统及其全套测试不在范围内。严格按 R4-00～R4-10执行：先冻结V4真实入口与测试分母，修复PG调度/桌面、历史图表、研究快照/发布旁路、合法V4 DuckDB混合适配器；继续上轮A/B修复及全量回归分流、精确复权、性能。可以并行开发，不等待真实10/12日数据与FEP成熟而停工。只使用G盘工程环境，保护TDX和所有旧Head/生产进程/旧SQLite原件，未授权不接管生产。每批交付独立可复核SHA/原JUnit/负例/实际PG读回/差异/版本化状态并推送，最终独立验收未签前保持 `EXTERNAL_ACCEPTANCE_BLOCKED/AUDIT_INCOMPLETE`。不得自签通过、缩小分母、执行旧V3全仓库pytest或静默回退数据库。

**本卡唯一签发状态：`R4_EXECUTION_AUTHORIZED_FOR_ISOLATED_ENGINEERING_ONLY`。** 生产变更、Windows实体安装、真实Grant及时间门均未由本卡授权。


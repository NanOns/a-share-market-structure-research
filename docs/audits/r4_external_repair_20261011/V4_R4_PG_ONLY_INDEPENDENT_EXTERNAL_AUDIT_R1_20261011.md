# 大A V4｜R4 PostgreSQL-only 隔离工程成果独立外部审计 R1

> 日期：2026-10-11（北京时间）；性质：独立外部审计与下一轮修复依据（不授权生产变更）  
> 总任务卡：`V4_R4_CONSOLIDATED_EXECUTION_MASTER_PG_ONLY_20261011.md`  
> 原独立基准：`V4_FULL_SYSTEM_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261011.md`  
> 仓库：`NanOns/a-share-market-structure-research`  
> 原目标分支：`codex/v4-fp14-r2-repair`，HEAD `fbd23a6ba08d0948fe7ad421d1765fe363648522`  
> 候选隔离分支：`codex/r4-pg-only-20261011`，检查时 HEAD `5f67ce474d0b1ed474a8b8bb02b8e794df10629e`（领先基线6提交，219改动文件）  
> 正式状态：**`EXTERNAL_ACCEPTANCE_BLOCKED` / `AUDIT_INCOMPLETE`**。工程候选：**`SCOPED_ENGINEERING_PROGRESS_VERIFIED_WITH_DEFECTS`**。

## 1. 审计方法、独立性与证据有效性

先查询 Drive 正式任务卡、R3 独立审计，以及最新上传的两份 R4 候选 ZIP，再读取两个 GitHub 分支的精确 HEAD 和比较结果。重点审计较新 `R4_QA_ENGINEERING_PARTIAL_20261011_141ddee5.zip`（Drive ID `1NbM_fjjuw8uHaE2I9HGnI5GjHuBScfKx`），并直接展开源码、逐项核验 ZIP 内清单、JUnit、JSON、CSV、代码缺陷。

- ZIP SHA-256：`6c7b1cf597227bb98d996f24c7bb2037a569c5d4cbc2e6c0cfea767808cae055`。内含219文件（含自身 MANIFEST）；218个清单文件的 SHA-256 独立重新计算，**218/218一致**。
- 包的 `PACKAGE_MANIFEST.json` 的 `git_head=141ddee54429dd214030cb5fd1c45f1fd44a06d1`、`implementation_test_sha=8df65de3e0ff622e398296d768996b2a226c2177`；分支检查时最新提交为 `5f67ce4...`，其后续变动以收据/归档为主；历史回执必须绑定各自执行时源码，不得全部追溯挂最新 SHA。
- 独立解析 `R4_SCOPED_f64e1318_JUNIT.xml`：103 tests/0 failures/0 errors/0 skipped（本地回执核验，不是外部机器亲自重跑）。早期的 `R4_FEP_E1_FRESH_01_JUNIT.xml` 留有94用例中17失败，`R4_02_TEST_JUNIT.xml` 留有7用例中4失败，后续修复/重跑必须用时间链而非抹去失败。
- 本轮未获用户 Windows 本机 PG、所有真实行情目录与进程控制访问；不声称亲自执行了实际 5,224 只股票的 PG 对照或在线浏览器，也不声称 R4 生产 PID 已加载候选代码。反例源码行为与导入依赖由本审计独立复现。

## 2. 核心交付结果与证据边界

| 项目 | 本轮可靠进展 | 独立结论 |
|---|---|---|
| Git/Drive | 候选分支6个提交，R4 ZIP已归档、219文件/218条哈希对照一致 | **交付隔离版有效**；目标分支未集成、生产未切换 |
| PG 调度 DB-01/02 | `operational_daily_jobs_pg_r1.py`、Desktop PG 入口、七表历史迁移；PG实际断连HTTP 503且不回退；工程崩溃/竞争进程回执 | **SCOPED_ENGINEERING_PASS**；真实执行器 checkpoint/CAS、在役系统与恢复权限未闭环 |
| PG 图表 DB-03 | `v4_history_pg_r1.py` 原生 PG index；五 T0 读回；一只股票×五日×RAW/QFQ×D/W/M共30请求，其中14 READY、16因正式周期 Owner 缺失而 SOURCE_INCOMPLETE；异常 token/authority负例 | **SCOPED_PASS，正式发布阻断**；默认 accepted history manifest 仍是旧SQLite，必须先形成已接受PG绑定 |
| PG 研究快照 DB-04 | 九域候选实现，冻结相同 source/producer 对6337 objects、12106 aliases、50162 members零差异 | **同源对照有效**；与旧已接受 published snapshot 的 `objects` digest **不一致**，不得把“同源通过”替代“旧出版物无损迁移” |
| BFF/持续发布 DB-05 | 显式 PG reader/失败阻断，代码已更改 | **PARTIAL**；正式路由全覆盖、joint CAS/rollback待证 |
| DuckDB DB-06～09 | 纯排名函数从旧构建器抽取，局部禁止 legacy import 的3个用例通过；V4/V3 入口隔离持续盘点 | **PARTIAL/UNKNOWN**；未证明所有 V4 动态入口完全排除 DuckDB/SQLite |
| Series/Focus DB-10/11 | 原生 PG Series、copy-on-write Journal、CAS和定向负例 | **SCOPED_PASS**；真实全消费者、连续日更和首获身份未全面验证 |
| 可选 Shadow DB-12 | 尝试切换 PG-only readback | **FAIL（新增代码错误，见§3）** |
| 精确复权 FA-016 | `exact_factor_transport_r1.py` 分子/分母 typed transport、来源 digest、日期检查 | **候选工程通过**；56类实际消费者、整链 PIT/Rank/Core/Focus/Forward 未闭环 |
| 性能 FA-004/020 | 扫描器原文件对照和局部计算剥离 | **部分工程通过**；首页 6 MB 级响应、锁争用与正式阈值未关闭 |
| 全量 V4 测试 FA-006 | 原4568节点台账完整保留；另有受控103/103定向回归 | **FAIL_FULL_REGRESSION / DENOMINATOR_OPEN** |

本轮不是“没有修改代码”，也不是“全系统全部通过”。正确级别：**实际工程修复已推进，正式 V4 PostgreSQL-only 验收仍阻断**。

## 3. 新增确定性缺陷 / 阻断

### R4-E01（P1）`shadow_context.py` 异常处理遗留 `sqlite3.Error` 且未导入

候选源码 `src/workbench_service/shadow_context.py` 移除了 `import sqlite3`，但 `:172` 仍有 `except (KeyError, TypeError, ValueError, OSError, sqlite3.Error)`。基线 R3 仍有 `import sqlite3`，属于R4移除SQLite时引入的新回归。

本次外部独立 Python 最小复现：直接加载候选原文件，用同名 `ResearchContextError` stub，不改函数体，构造 malformed `{}` fixture 调用 `_load()`，得到：

```
ACTUAL_EXCEPTION=NameError("name 'sqlite3' is not defined")
UNDERLYING_EXCEPTION=KeyError('context')
```

正确行为应是将输入异常归为 `ResearchContextError('SHADOW_SOURCE_INVALID')`，而非 `NameError`。修复时删除 SQLite 依赖并单独处理 `psycopg.Error`/契约错误；必须验证 malformed source、PG 错误、无 Shadow 授权等负例。不能将该用例排除为旧V3测试。

### R4-E02（P0 切换门）原 accepted 图表 authority 与 PG-only reader 不兼容

`src/workbench_service/core_product_bff_r1.py:98-118` 读取默认 `config/core_product_read_authority_r1.json` 指向旧 manifest。当前已接受索引证据记录 `history.sqlite` 大小 **426,196,992 B**；候选 `pack():114-115` 遇到没有 `engine='postgresql'` 立即 `PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK`。已测30 HTTP均绑定显式 **isolated_history_authority**，不是正常启动路径的历史索引。

这不是要求允许SQLite回退，而是要求**正式切换前先隔离构建、完全验收、授权绑定PG索引**，并对默认无注入的服务作全端点负例/成功用例。否则新的应用二进制先上生产会直接中断现有图表。

### R4-E03（P1）既有已接受研究快照不满足旧出版物零差异

`R4_04_REAL_SNAPSHOT_RESULT.json`：PG staged snapshot 与原已接受 SQLite 快照的三表计数一致（6337/12106/50162），但 `objects` 全表 digest 不一致，原回执实际抛出 `REAL_SNAPSHOT_ORACLE_DIFFERENCE_REQUIRES_REVIEW`。之后 `R4_04_SAME_SOURCE_ORACLE_RESULT.json` 在**重新冻结相同 producer/source**后零差异。**这证明新PG构建器对相同输入的兼容性，不证明对旧发布快照的迁移等价。**

要求逐对象比较、溯源归类，区分旧版时间、已接受改动、字段质量差异与转换问题；联合 CAS/rollback 未通过不得更换旧 authority。

### R4-E04（P1）R4合法测试分母仍未确定、原全回归远未关闭

`TEST_NODE_DISPOSITION_R4.csv` 独立统计 4568 唯一基线记录：原3810 PASS、237 FAIL、209 ERROR、312 SKIP；在这份 R4 逐节点台账中 `SCOPED_PASS=164`、`NOT_RUN=4404`，且全部 `fix_commit=''`、`owner='Codex / root'`、`scope_disposition=CONTRACT_REVIEW_OPEN_NO_EXEMPTION`。这 **不是** 164/4568的正式新总通过率，定向节点亦有重测/源绑定差异。

`R4-00_SCOPE_GATE.json` 明确 `current_status=NOT_VERIFIABLE`、`legal_denominator=null`。必须按真实 V4 功能、PG 数据边界、动态可达性为每个用例提供合法纳入/排除理由；旧V3独立功能不得进入分母，但被V4调用的旧文件也不得因目录名而假装无关。使用修订 `BaseException` 护栏 clean-slate 重跑，不能把旧guard潜在假PASS算入正式证据。

### R4-E05（P2，证据边界）保护源基线部分在改动后冻结

`R4_SOURCE_BASELINE_QUALIFICATION.json` 记录10,171保护对象读回：10,169未变，2个源码位置最早保护清单采集晚于修改，前后sha有差异；虽然已恢复原源码，不能宣称“全部10,171在任何时刻均原字节未变”或生产PG库已审计。同样，只有进程内写护栏对4种恶意写法有负例回执，不能替代子进程或TDX所有配置根清单。

## 4. R4-00～R4-10 门状态

| 阶段 | 外部审计结论 | 最重要未关闭条件 |
|---|---|---|
| R4-00 范围/图谱 | **NOT_VERIFIABLE** | 所有V4运行入口+权限+动态数据库调用覆盖不足；合法分母NULL |
| R4-01 PG全能力盘点 | **PARTIAL** | DB-06/08/09/12与兼容调用仍待逐例排除或改造 |
| R4-02 调度/桌面 | **SCOPED_PASS / OPEN** | 正式执行器重启、checkpoint、并发、CAS、实机安装与批准切换 |
| R4-03 历史图表 | **SCOPED_PASS / OPEN** | 默认已接受PG绑定、广样本、周期Owner缺口、容量、无注入产品HTTP |
| R4-04 研究快照 | **SCOPED_PASS_SAME_SOURCE / OPEN** | 已出版物全差异解释、joint CAS、完整回滚 |
| R4-05 Journal/Series | **SCOPED_PASS / OPEN** | 真实Focus/Forward消费、历史冻结/重开身份及跨日协同 |
| R4-06 V4-only全回归 | **BLOCKED** | 4404节点未R4重跑、范围/fixture/责任分解未闭环 |
| R4-07 R3收尾 | **PARTIAL** | 源定位及相关API/browser实际稳定SHA复查、正式加载未证 |
| R4-08 精确复权 | **PARTIAL** | 56类真实消费、缺精确系数拒绝、PIT历史敏感性、版本升级 |
| R4-09 性能/扫描器 | **PARTIAL** | 首页容量+阈值及所有治理规则完整运行 |
| R4-10 全字段/Forward/FEP/PIT | **BLOCKED_FORMAL / ENGINEERING_CONTINUES** | 合法规范需求分母、成熟时序、D0/D1/D2、H21、OOS/Grant |

## 5. 本轮修复交付应该如何推进（不是继续跑V3测试）

**第一批（立即可做）**：
1. R4-E01 修Shadow异常残留，新增真正触发 `_load()` 错误的回归；所有V4模块做类似异常引用的AST扫描与最小负例。
2. R4-E02 完成 PG history authority 构建与读回合同，包括默认无隔离注入的真实产品 handler、完整原索引SHA及T0对照；旧头保护，隔离/候选优先，不擅自切生产。
3. R4-E03 逐字段/逐对象解释旧accepted快照与新PG同源快照的差异，CAS失败恢复负例；不得用同源零差异冲销既有出版物差异。
4. R4-E04 落实只审V4的纳入/排除/真实调用映射，产生合法测试分母与owner；PG-only guarded clean-slate可并行分批复跑，保持原4568账目与原失败。
5. DB-06/08/09/12补完整动态入口及非PG探针；凡仍可达的SQLite/DuckDB真实运行链迁移/隔离，明确仅V3旧功能不需要修。

**第二批（不因真实交易日停工）**：调度真实执行器恢复、回放与可回滚授权；Snapshot joint release；Journal/Series真实消费；复权56消费与全字段需求；性能业务阈值、非交易日/缺数据负例。

**独立外部/时间门**：真实后继T0只有新交易日首次可用后才验；FEP成熟/OOS只按真实时间累计；Windows实体和现行PID/PG用户授权单独签字。任何工程候选自检、Drive上传、commit/push不能替代正式独立签收。

## 6. 最终裁决

**当前候选：`SCOPED_ENGINEERING_PROGRESS_VERIFIED_WITH_DEFECTS`。**

**V4整体：`EXTERNAL_ACCEPTANCE_BLOCKED` / `AUDIT_INCOMPLETE`；PostgreSQL-only `NOT_YET_VERIFIED`。** 不允许正式目标分支合并后直接重启在役产品并改切数据库。先修新增NameError、再完成默认图表PG绑定/旧已接受快照差异处置、确立合法V4-only测试分母与真实调用图；其它工程可继续，不需要等待下一个交易日。

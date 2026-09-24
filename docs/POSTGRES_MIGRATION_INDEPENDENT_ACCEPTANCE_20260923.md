# PostgreSQL 数据迁移独立验收（2026-09-23）

| 字段 | 结果 |
|---|---|
| stage | `PGM_INDEPENDENT_ACCEPTANCE_20260923` |
| stage_contract | 以 `DAILY_FOCUS_POSTGRES_DESIGN_V2_1_CHANGE_NOTES_20260922`、`POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_20260922` 和 `POSTGRES_MIGRATION_EXECUTION_RECORD_20260922` 的全量、引用、切换及运行态门禁为准 |
| acceptance_result | **BLOCKED（当前生产迁移验收）**；冻结副本与历史 shadow 行数核对通过 |
| next_stage | 恢复工作台服务后重新执行实时 PG 只读逐表/摘要、最新 publication 和 HTTP 回归；保留本审计问题直到证据通过 |

## 独立证据

1. 对冻结 DuckDB 文件重新计算 SHA-256：`525501b881c094a3f62dcb95f1d375b5d29149ddfb57b032cbdd9ae43916a96d`，与执行记录一致。以 DuckDB `read_only=True` 独立枚举得到 103 张表、2,314,834 行；与 `shadow_read_report.json` 中 103 张表的源/目标行数逐表比较，差异 0。该 shadow 报告生成于 2026-09-22 04:03 UTC，属于历史证据，不是本次对 PG 的直接查询。
2. 当前 `config/workbench.yaml` 为 `engine: postgresql`、`cutover_state: ACTIVE`；历史切换回执显示服务 PID 45908、`READY`、`FULL_PASS`，生成于 2026-09-22 14:39 UTC。
3. 本次探测 `127.0.0.1:5432` TCP 可达；`127.0.0.1:28765` TCP 不可达，`/api/operations/status` 连接被拒绝。故无法独立确认现时服务、页面、API 和最新 head 可用。
4. 本进程没有 `WORKBENCH_PG_DSN` 或 `PGPASSWORD`。未使用回执替代目标库直查；本次无法独立完成目标 PG 的实时逐表摘要、约束、文件引用与最新同步数据核对。最新同步回执时间为 2026-09-22 17:25 UTC，晚于冻结快照。

## 独立审计项

| 编号 | 范围与证据 | 独立接受条件 | 当前状态 |
|---|---|---|---|
| PGM-IA-01 | 切换后服务可用性：当前 HTTP 端口拒绝连接，而历史回执称 READY | 服务恢复后，同一运行实例的 status、关键 API、页面和任务只读 smoke 均通过 | OPEN / BLOCKED |
| PGM-IA-02 | 当前 PG 数据一致性：缺少本次只读连接；冻结源与 2026-09-22 shadow 行数相符，但有后续增量 | 使用只读 PG 凭据，按同一 immutable identity 对全部仍被引用表核对行数和逻辑摘要，重点核对最新 publication/head、研究与关系域 | OPEN / NOT_CHECKED |
| PGM-IA-03 | 文件引用和在线退役：141 条可用性、9+3 入口分类仅有历史回执 | 实时重验 active artifact 路径/摘要、PG 唯一 head 和在线服务无共享 DuckDB 连接 | OPEN / NOT_CHECKED |

本次只读审计未运行生成任务、未修改数据库或 TDX 来源目录。已有工作区未提交修改未触碰。

## 后续现场故障复核（2026-09-23）

用户打开工作台后，服务 PID 14632 的 `/api/operations/status` 报告实际数据库为 `data/database/market_research.duckdb`，未报告 PostgreSQL backend；`/api/publications?include_analysis=1` 最新仅到 2026-09-21，且分析能力域为空。相同服务的 `/api/v3/research/today` 则从文件型 bundle 返回 2026-09-22。这是同一页面混用旧 DuckDB 发布头和新 bundle 的直接证据，不能解释为 22 号数据已被删除。

根因是 `run_workbench_service.py` / 托盘启动器此前只按 `runtime/operations_config.json` 中的旧 DuckDB 路径启动，未读取 `config/workbench.yaml` 已激活的 PostgreSQL backend，也未注入 `WORKBENCH_API_BACKEND=postgresql`。当前交互环境无 `WORKBENCH_PG_DSN`，Windows User/Machine 环境变量和 libpq pgpass 均未找到；独立直连 PG 因无密码被拒绝。已修启动器为 fail-closed，并在确认活动任务数 0 后停止 PID 14632 的错误后端实例。未重跑生成或回退任何数据。

新增独立审计项 `PGM-IA-04`：启动入口和服务配置漂移。接受条件：持久化提供 PG 凭据，启动器在无凭据时拒绝 DuckDB 回退；有凭据时工作台 status 显示 PostgreSQL，发布列表最新 2026-09-22，受影响分析模块按同一 publication 通过 API 与页面验收。当前状态 `OPEN / BLOCKED_BY_PG_CREDENTIAL`。

### 恢复回执

用户提供本机账号后，凭据写入被 Git 忽略的 `config/.env`，文件 ACL 限当前 Windows 用户；未写入受版本控制的配置。启动器从该文件加载 `WORKBENCH_PG_DSN`，并依据 `config/workbench.yaml` 激活 PG，缺失凭据时拒绝启动。新服务 PID 21904 的 `/api/operations/status` 报告 `backend=postgresql`、`READY`；`/api/publications?include_analysis=1` 返回 8 条，最新 `2026-09-22 / m4-547e88ce22e6d89590876c7ea1d68ca0`，11 个分析域均为 `AVAILABLE`；`/api/v3/research/today` 返回 2026-09-22、`READY`、273 条；`/v3` HTTP 200。`PGM-IA-04` 运行态/API 子项通过；浏览器实际视觉展示尚待复核。全量跨库摘要审计项 `PGM-IA-02` 仍独立开放。

随后用 Edge headless 加载 `/v3` 至 network-idle，页面文字显示 2026-09-22 为当前版本、22 号研究首页及市场摘要有值，浏览器 `pageerror` 为 0。`PGM-IA-04` 的页面恢复子项通过；全量数据库迁移审计仍按原合同另行核验。

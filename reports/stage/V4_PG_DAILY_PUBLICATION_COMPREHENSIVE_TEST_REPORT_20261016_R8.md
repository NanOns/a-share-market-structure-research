---
stage_id: V4_PG_DAILY_PUBLICATION_R8_20261016
code_sha: PENDING_COMMIT
baseline_sha: 36a65ac22b8535d5ffe3782c9bc18752b463dd27
branch: codex/v4-workspace-cleanup
scope: R7 independent audit findings, source-byte root cause, real executor diagnostic bridge, PIT reader hardening, SQL static review, isolated validation preparation
test_scope: R8-focused source/core/executor/schema tests; CI-equivalent full-suite attempt
conclusion: partial code repair; real source authority, PG publication and page closure remain blocked
status: R8_CODE_PARTIAL_PASS
sql_static: PARSER_AND_STATIC_CHECKS_ONLY
pg_live_read: READ_ONLY_SCHEMA_DRIFT_CONFIRMED
pg_isolated: NOT_RUN_NOT_AUTHORIZED
pg_production_write: NOT_AUTHORIZED_NOT_RUN
source_authority: BLOCKED_NO_INDEPENDENT_ACCEPTANCE_RECEIPT
core_ready: BLOCKED_NO_ACCEPTED_SOURCE_OR_PG_ROWS
pit: BLOCKED_SOURCE_EVIDENCE_NOT_PIT_ELIGIBLE
daily_e2e: DIAGNOSTIC_ONLY_NO_SUCCESSFUL_PUBLICATION
page: NOT_RUN_NO_PUBLICATION_OR_SERVICE
ci: LOCAL_WORKFLOW_SUITE_PASS; GITHUB_RUNS_PENDING_PUSH
production: UNCHANGED
approval_status: no authorization for isolated or production PostgreSQL writes, Head switch, 28765 deployment, destructive cleanup or history rewrite
---

# V4 PG 日发布 R8 阶段报告

## 范围与代码结果

执行前核实工作区位于 `codex/v4-workspace-cleanup`，HEAD 等于冻结基线 `36a65ac22b8535d5ffe3782c9bc18752b463dd27`；R8 修改仅在该主仓库内进行，未创建 worktree。按 R8 任务卡、R7 阶段报告和适用的 R8 来源修复、运行时性能、增量身份及现役 snapshot 规范执行。本轮未启动 scanner，阶段 0 不适用。

- 将现役日更 executor 经 hash 绑定的 source freeze/readiness 传入来源 PG adapter，输出 `PLAN_ONLY_NO_DATABASE_IO` 诊断候选，明确 `persisted=false`。实际 2026-10-12 证据得到 3 个来源事实，状态为 `DIAGNOSTIC_ONLY / SOURCE_PIT_AUTHORITY_UNAVAILABLE`；不签发接受回执、不访问 PG、不改变原有发布流程。新增版本化运行时接受清单路径合同，并将 TDX GBBQ 输入路径移入只读来源配置合同；工程回放隔离根改为显式环境配置，避免在生产模块内写死机器路径。
- Core Reader 现在要求调用者在同一 PG 连接上提供 `READ ONLY + REPEATABLE READ` 事务，并在同一 snapshot 校验 publication `ACCEPTED/accepted_at`、来源/包时间不晚于 cutoff、T0、receipt 绑定及 `AS_RECORDED/PIT_ELIGIBLE`。缺失或越过 cutoff 的证据失败关闭；核心完整性与发布门槛仍保持 unresolved。
- SQL 036 增加 `record_locator` 与已绑定 manifest 的一致性守卫；SQL 037 删除与主键同键的冗余索引。新增完整 001–037 隔离 DDL 校验入口，必须显式配置隔离 DSN 和独立确认值，且限定 loopback、指定库名前缀、非 5432/网页端口。它只在获批且预置的隔离数据库上运行，不创建或启动数据库，不读取 live DSN。
- 本轮没有实现独立接受权威，没有把真实日线/画像/行业输出接入 PG Core rows、Publication/Head 和默认页面读路径，也没有完成成功的日发布 E2E。缺失的真实 authority、PG schema 与业务数据不是测试桩可以代替的。

## 官方来源 SHA 不一致根因

对冻结 `operational_daily_exact_release_policy_v2.json` 中 66 个算法绑定和 604 个组件绑定逐项比对，发现 39 个归档文件（29 算法、10 组件）的当前 LF 文件与原冻结 SHA/字节数不一致。恢复原 CRLF/混合换行形式后，39 个候选字节流均精确匹配声明的 SHA 与长度；目标 `v4_operational_new_listing_r1.json` 从当前 833 字节、SHA `8dda3cba15f930c91e41e151604eab90c728f0a4c4768cb0bbc49d1364a52bae`，恢复 14 个 CRLF 后为冻结记录的 847 字节、SHA `59c29bd5ea5a591995dea12675c4191b3277d9d240d180c57eaf15bc6e690fc6`。两份混合换行源也只有按原换行分布恢复才能精确重现。

因此证据支持换行字节表示不一致，而不支持内容漂移；具体转换发生在归档复制还是 Git 暂存/提交过程，当前证据无法确认。目标路径可达历史中只有提交 `1cbaaa7f35e4ce1d26636f2bd2cc5a0206700f26`，该提交及其父版本都存有 833 字节 LF blob。未声称全 Git 对象库不存在原始字节。R1.1 冻结 policy、源码归档、审计回执和历史 SHA 均未改动。

旧 `R1_1_RUNTIME_ACCEPTANCE.json` PASS 只证明运行时保全合同；`FINAL_RUNTIME_CANDIDATE_R1_1.json` 明确 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`historical_PIT_permission=false`。它们不能授权新的日更来源接受或 PIT。要前向闭环，仍需来源权威提供独立、带时间的接受回执及 PIT 授权，再以新版本记录原始字节与 Git 往返保真；不能从自哈希计划或旧 PASS 推导接受权。

## 验证与实际状态

- R8 定向本地测试：**68 passed**，覆盖 executor、真实 hash-bound source diagnostic bridge、Core Reader cutoff/隔离级别检查、source ingest、PG candidate、036/037 静态兼容及隔离 runner 参数防护。
- 隔离 runner `--plan` 列出 **38** 个 SQL 文件（含两份独立 010）；pglast 语法解析结果由静态审计记录为 034/035/036/037 各 10/5/15/13 条语句。静态 parser 不编译 PL/pgSQL 函数体，不能替代 PG 实跑。
- GitHub Actions 当前 V4 job 的本地等价命令（candidate、owners、contracts、source manifest、daily ingest/core、SQL static、executor、pre-next T0、exact-policy，加本轮 R8 用例）**99 passed in 23.95s**。push/PR GitHub Actions 结果待提交后读取。
- 另外尝试仓库全部 pytest：共收集 7,650 项，但未完成。`-x -vv` 首个确定失败为 `tests/fep/test_feature_owner.py::test_all_47_accepted_historical_fields_and_seven_relative_rps_are_copied`，实际报 `FEP_EXACT_BINDING_MISMATCH`：合同绑定的 V4.03 receipt 期望 6,714 字节，当前工作区文件是 129 字节 Git LFS pointer（对象未 hydration）。运行中其余 FEP PostgreSQL 配置用例被跳过。首次不加 `-x` 的全量运行在约 2% 处无进度并被中断，曾显示多个失败/错误标记，未取得完整汇总，故不报告全仓通过。
- `git diff --check` 通过。PostgreSQL 只读事务复核身份为 `market_research`、`127.0.0.1:5432`、角色 `postgres`，该查询事务 `transaction_read_only=on`。ledger 仅有 12 项到 012；010 source manifest 及 013–037 无 ledger entry。现役 schema 有部分未对应 ledger 的后续列，缺 `source_manifest_contract_id` 和 `daily_core_result_snapshots/rows`。行数：source packages 0、source revisions 40,455、publications 0、publication heads 0；未执行 SQL 034–037。
- 端口只读检查发现 PostgreSQL 5432 双栈监听（PID 8260）；28765、28766 均未监听。没有启动网页服务，因此页面 parity 未运行。没有 PG DDL/DML、核心行写入、Head CAS、生产数据更改、正式 Head 切换或部署。

## 状态矩阵

| 维度 | 状态 | 证据/阻断 |
|---|---|---|
| CODE | `R8_CODE_PARTIAL_PASS` | Reader PIT cutoff、executor 诊断桥、SQL guard 和隔离 runner 已实现；核心生产/页面接线仍未闭环。 |
| SQL_STATIC | `PARSER_AND_STATIC_CHECKS_ONLY` | 036/037 和迁移计划静态检查；未做 PG DDL/PLpgSQL 编译。 |
| PG_ISOLATED | `NOT_RUN_NOT_AUTHORIZED` | 无隔离库写授权；runner 仅准备。 |
| PG_LIVE_READ | `READ_ONLY_SCHEMA_DRIFT_CONFIRMED` | shared DB 仅事务只读；台账至 012、现役 schema 漂移、R6 relations 缺失。 |
| SOURCE_AUTHORITY | `BLOCKED` | 无独立来源接受权威/receipt；历史文件明确非 PIT。 |
| CORE_READY | `BLOCKED` | 无 accepted source、真实 PG core rows 及 completeness gate。 |
| PIT | `BLOCKED` | freeze/readiness 为 `AS_RECORDED=false/PIT_ELIGIBLE=false`。 |
| DAILY_E2E | `DIAGNOSTIC_ONLY` | 使用真实 hash-bound 证据得到安全关闭计划；没有成功写入/发布。 |
| PAGE | `NOT_RUN` | 无 Publication 数据、服务未启动；28765/28766 未监听。 |
| CI | `LOCAL_WORKFLOW_SUITE_PASS; GITHUB_PENDING` | 仓库 V4 job 等价本地测试集 99 passed；待本提交 push 后读取 GitHub Actions。全仓测试未完成且含独立 LFS hydration 失败。 |
| PRODUCTION | `UNCHANGED` | 未触碰生产 PG、Head、28765 或调度。 |

## 下一阶段

在独立来源权威给出新接受与 PIT 证据、并单独授权隔离 PG DDL/DML 后，先处理 live schema/ledger 漂移兼容，再对 034–037 做事务完整性、冲突回滚、正负行集和重放验证；之后接通真实 core producer、Publication 与默认页面读回，执行真实日更成功路径和真实增量性能测量。生产写入、正式 Head 切换和 28765 部署仍须各自单独授权。

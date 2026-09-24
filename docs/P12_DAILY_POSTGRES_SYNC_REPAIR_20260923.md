# 9 月 23 日发布同步阻断修复记录

> 阶段状态：`FULL_PASS`。按 P12 页面一键生成 V2 与 PostgreSQL 日同步事务合同完成。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `docs/P12_DAILY_PAGE_GENERATION_REPAIR_20260916.md` 的同入口完成条件；`docs/POSTGRES_MIGRATION_INDEPENDENT_REACCEPTANCE_20260923.md` 的 `PG_RUNTIME_HEADS_V1` 原子更新合同；`docs/P12_DAILY_DATABASE_LOCK_REPAIR_20260917.md` 的构建锁隔离合同。 |
| stage_contract | `P12_DAILY_PG_SYNC_RUNTIME_HEAD_SOURCE_BOUNDARY_V1` |
| scope | 仅修复日级编排 PostgreSQL 同步器的源/目标表合同。DuckDB compute workspace 提供 publication、analysis、research run/candidate 源行；`research_bundle_heads` 与 `analysis_snapshot_heads` 是 PostgreSQL 事务内构造的目标 projection，不要求复制回 DuckDB。V3.3 页面构建任务必须校验并同步当前 publication 对应的完整 bundle。保持 PostgreSQL 原子事务、身份检查、bundle artifact digest 验证和 TDX 只读。 |
| failure_evidence | 2026-09-23 `runtime/postgres_migration/20260922/pg_latest_publication_sync_report.json`: publication `m4-51729396603ef27a36e4b0390302766d`、trade date `2026-09-23`；`BLOCKED`，错误 `RuntimeError: required table missing: research_bundle_heads`，PG 事务已回滚。只读检查 compute DB：`research_runs_v3_3` / `research_candidates_v3_3` 有目标日数据；`research_bundle_heads` / `analysis_snapshot_heads` 不存在，符合它们是 PG-only serving projections 的合同。PG publication head 仍为 `2026-09-22`。 |
| repair | 移除将 PG-only head projections 错当 DuckDB source table 的 preflight 条件；改为分别验证 DuckDB base source 与 PG projection target。V3.3 任务显式要求目标 publication 对应 `COMPLETE` bundle、bundle artifact 目录和 candidate 数一致；事务内 upsert bundle head 并核对 head 身份及候选数。增加 `--dry-run`，对现有 9 月 23 日隔离 compute DB 执行全事务验证后回滚，再执行正式原子提交。 |
| acceptance_result | `FULL_PASS`。3 项同步表合同测试通过；P12 busy UI + sync 合同 + M4 发布器定向测试 `20 passed`；Python 编译、两份 JS 语法检查与 `git diff --check` 通过。9 月 23 日完整 PG 同步先 `DRY_RUN_PASS` 并回滚，再 `FULL_PASS` 提交；报告时间 `2026-09-23T12:34:22Z`。PG 验证：publication head=`m4-51729396603ef27a36e4b0390302766d`，LOCAL_RECONSTRUCTED snapshot=`m10-mainline-preview-d046260fc8f20c5b`，V3.3 bundle head=`8d59680ccc5ffcd4bc8a3c8cd8ddaca8ac2d84770584e4b02a414b87b6c8618c`，候选 273 行。HTTP publications API 首项为 2026-09-23；浏览器首页状态为 `数据就绪`，V3.3 显示 273 股，市场总览与板块数据均可读。 |
| next_stage | 日级发布完成；Focus 首个 `REAL_FORWARD` 仍须按 FOCUS-03 技术身份审计与发布门独立预检。技术 JSON/JSONB hash 身份差异仍 `FAIL_CLOSED`，本次未修改已接受技术结果。 |

## 验收边界

- 不再次运行 M3/M4/P12 生成，不重算或覆盖当前已生成的隔离 bundle。
- dry-run 必须执行复制、artifact 登记、runtime-head upsert 和硬校验，并以 rollback 结束。
- 正式同步只在 dry-run 全通过后运行；任一检查失败时整笔 PostgreSQL 事务回滚。
- 当前技术结果 JSON/JSONB hash 身份审计仍单独 fail closed；本次同步修复不得改变已接受技术行或技术身份。

## 本次执行结果

- 根因：同步器 preflight 把 PostgreSQL projection 表 `research_bundle_heads`（以及 `analysis_snapshot_heads`）错误要求为 DuckDB source 表。Compute workspace 按架构不会持有这些 PG heads；程序因此在复制事务开始前中止，M4 记录在 PG，但分析绑定和 V3.3 head 未提交，publication API 不显示 9 月 23 日。
- 修复：同步器现在分别校验 DuckDB base source 与 PostgreSQL projection target；页面的 V3.3 build 明确要求完整 `COMPLETE` research bundle，并校验 bundle artifact 路径与候选行数。PG snapshot head 和 bundle head 都在一个事务内 upsert 并做身份验证。
- 恢复：复用现存隔离 compute DB，不重跑 M3/M4/P12；dry-run 回滚通过后原子提交同步。`runtime/postgres_migration/20260922/pg_latest_publication_sync_report.json` 最终为 `FULL_PASS`。
- 未改 TDX 输入，未改技术结果哈希、技术行或技术 identity；`P12-08` 的前向效果仍为 `EFFECT_OBSERVATION_PENDING`，属于效果观察状态，不阻断 9 月 23 日日发布。

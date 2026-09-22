# PostgreSQL 迁移执行记录（2026-09-22）

> 阶段合同：`POSTGRES_MIGRATION_EXECUTION_RECORD_V1`
> 对应设计：`POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_20260922.md`
> 本记录只登记已经执行的迁移阶段，不代表在线主库已经切换。

## 1. 阶段结论

```text
PGM-00 / PGM-01 / PGM-02 / PGM-03 / PGM-04 / PGM-05-shadow / PGM-06-shadow / PGM-07-drill / PGM-08-rehearsal = DEGRADED_PASS
legacy 全量数据复制 = COMPLETE
PG_SCHEMA_V1 = COMPLETE
在线主库切换 = NOT_STARTED
Focus Tracker 开发 = BLOCKED_UNTIL_CUTOVER_ACCEPTED
```

已完成源库冻结、目标库建立、全库 legacy 复制和逐表行数校验。PostgreSQL 目前是迁移验证库，工作台服务已恢复运行但仍使用旧 DuckDB；没有进行页面、生成任务或 Focus Tracker 的 PG 切换。

## 2. 目标实例

| 项目 | 实际值 |
|---|---|
| PostgreSQL | 18.6 x86-64 Windows |
| Host/port | `127.0.0.1:5432` |
| Database | `market_research` |
| Migration user | `postgres`（仅迁移阶段，尚未作为应用账号） |
| Evidence schema | `legacy` |
| Formal application schema | `workbench` |
| Encoding | UTF8 |
| Locale | `Chinese (Simplified)_China.936` |

密码未写入仓库、文档、命令行记录或迁移产物。

## 3. 源快照证据

| 项目 | 实际值 |
|---|---|
| 源文件 | `data/database/market_research.duckdb` |
| 冻结副本 | `runtime/postgres_migration/20260922/market_research.source.duckdb` |
| 文件大小 | `1,771,843,584` bytes |
| SHA-256 | `525501b881c094a3f62dcb95f1d375b5d29149ddfb57b032cbdd9ae43916a96d` |
| DuckDB 表数 | 103 |
| DuckDB 总行数 | 2,314,834 |
| 迁移读取方式 | 冻结副本、read-only |

迁移前通过受控维护接口停止工作台，确认 DuckDB 句柄释放后复制快照；迁移完成后重新启动原工作台并验证 HTTP 200 和 DuckDB read-only 可读。

## 4. 执行批次

成功批次：`legacy-20260922T035019Z`

首轮批次 `legacy-20260922T034819Z` 在遇到源 JSON 非标准 `NaN` 时中止，已在 `legacy.migration_runs` 标记为 `ABORTED`，没有作为成功批次使用。迁移器随后将 JSON `NaN/Infinity` 映射为 JSON `null` 后重跑；该规则只作用于 PostgreSQL 目标值，源快照保持不变，表级 digest 保留在 `legacy.table_runs`。

## 5. 校验结果

```text
legacy.table_runs COMPLETE: 103
source_row_count <> target_row_count: 0
目标 legacy 业务表: 103
目标迁移目录表: legacy.migration_runs / legacy.table_runs
```

每个表都记录了源行数、目标行数、规范化后的源行摘要和完成时间。空表也被建立并复制，不能因为当前为 0 行而删除。

## 6. 已落地的迁移工具

`scripts/migrate_duckdb_to_postgres_legacy.py`

- `--plan`：只读输出源表和行数；
- 默认模式：从冻结快照复制到 `legacy`；
- 支持 `--table` 分表重跑；
- 目标表使用显式列类型映射，不使用 `SELECT *` 方言复制；
- JSON 使用 PostgreSQL `jsonb`，对 DuckDB 非标准常量执行显式规范化；
- 迁移批次和逐表结果写入 `legacy.migration_runs` / `legacy.table_runs`；
- 密码只能通过 `PGPASSWORD` 或 libpq 环境提供，不接受命令行密码。

## 7. PGM-03 正式 schema

正式 schema 已建立在 `workbench`，不覆盖 `legacy`：

| 项目 | 实际值 |
|---|---:|
| 正式表数 | 103 |
| PostgreSQL schema migration | `PG_SCHEMA_V1 / COMPLETE` |
| 约束总数 | 871 |
| PK/UNIQUE | 112，全部 APPLIED |
| FK/CHECK | 83，全部 APPLIED |
| 正式 schema 行数差异 | 0 |
| 执行批次 | `pgschema-20260922T035853Z` |

约束顺序是：复制表和数据 → NOT NULL → PK/UNIQUE → FK/CHECK。DuckDB 的 007—035 没有在 PostgreSQL 重放；其历史身份保留在 `legacy.schema_migrations`，PG 自身版本记录在 `workbench_meta.schema_migrations`。

已落地工具：`scripts/build_postgres_workbench_schema.py`。该工具失败时会回滚当前语句并写入 `workbench_meta.migration_table_attempts` 或 `workbench_meta.migration_reference_checks`，不会静默忽略约束。

## 8. PGM-04 ArtifactCatalog 与消费者目录

已建立 `workbench_meta.artifact_catalog` 和 `workbench_meta.consumer_catalog`：

| 项目 | 实际值 |
|---|---:|
| 文件资产记录 | 141 |
| V3.3 bundle | 102 |
| Forward observation | 15 |
| Forward evaluation source | 8 |
| outcome plan/result | 3 |
| normalized Parquet | 1 |
| 静态代码消费者 | 97 |
| `MIGRATE_TO_PG` | 19 |
| `OFFLINE_DUCKDB_ALLOWED` | 43 |
| `RETAIN_UNTIL_AUDIT_CLOSE` | 35 |
| `UNCLASSIFIED` | 0 |

`UNCLASSIFIED` 已清零。当前 19 个服务/运维入口列为 `MIGRATE_TO_PG`，43 个分析/回放入口列为 `OFFLINE_DUCKDB_ALLOWED`，35 个历史修复/审计脚本保留到审计关闭；这些入口还没有改代码，只是进入迁移清单。

## 9. PGM-05 shadow-read 基础

已新增只读适配器 `src/workbench_db/postgres_repository.py` 和对账脚本 `scripts/postgres_shadow_read.py`。针对冻结 DuckDB 快照和 `workbench` schema 的 103 张表执行结果：

```text
tables=103
failures=0
status=PASS
report=runtime/postgres_migration/20260922/shadow_read_report.json
```

这只是数据层 shadow read，不是 HTTP API 双读；现有页面和任务仍未改用 PG。

适配器的连接初始化已修正为 PostgreSQL 合法的 `set_config` 参数化调用；修复前的演练失败已作为适配器缺陷记录，不影响当前 DuckDB 服务。

## 10. PGM-06 时间语义与 API shadow read

已完成：

- 97 个消费者全部从 `UNCLASSIFIED` 归类为 `MIGRATE_TO_PG`、`OFFLINE_DUCKDB_ALLOWED` 或 `RETAIN_UNTIL_AUDIT_CLOSE`；
- 建立 `workbench_meta.timestamp_semantics_catalog`，42 个 TIMESTAMP 列中 38 个经 writer 证据确认并转为 `timestamptz`；4 个仍保留 `timestamp without time zone` 并标记 `PENDING_REVIEW`（外部证据三列无生产持久化 writer、行情 `quote_time` 无统一来源时区契约）；
- 建立 `src/workbench_db/postgres_repository.py`；
- 对 `/api/publications?include_analysis=0` 做同请求 shadow read，7 条结果、latest head 均一致；报告位于 `runtime/postgres_migration/20260922/api_shadow_read_report.json`。

API shadow read 仍不是在线切换。当前 19 个服务/运维入口尚未改为使用 PG；4 个时间列仍等待来源合同确认，不能用机器本地时区猜测。

时间审计工具 `scripts/review_postgres_timestamp_semantics.py` 已把 writer 证据和未决原因写入 `workbench_meta.timestamp_semantics_catalog` 的 `evidence/review_basis/contract_version` 字段。

## 11. PGM-07 备份与恢复演练

已执行 PostgreSQL custom-format 备份和真实临时库恢复：

| 项目 | 实际值 |
|---|---|
| 备份文件 | `runtime/postgres_migration/20260922/market_research.pg_dump` |
| 备份大小 | `312,541,959` bytes |
| SHA-256 | `f3db37b86985ffbf6a4b2355ba8df69ca3565846caf61f11b3ea223546c582db` |
| 恢复库 | `market_research_restore_20260922` |
| 恢复检查 | schema=3、publications=15、research_candidates_v3_3=2205 |
| 清理 | 恢复库已删除，生产库未修改 |

恢复演练通过，PG 备份可作为回退基础；应用配置回退和 DuckDB→PG 主库切换回退仍在下一阶段演练。

## 12. 尚未完成的硬门

以下事项仍未通过，不能把 PostgreSQL 称为生产主库：

1. 4 个未确认来源时间字段的来源合同确认（或保持不可用于严格 AS-OF 的墙上时间）；
2. `ArtifactCatalog` 中外部 bundle/Forward 文件的运行时路径解析收口；
3. 专用应用账号、最小权限和连接池；
4. API、publisher、任务、运维和脚本的 DuckDB 直连收口；
5. PG 与 DuckDB 双读结果对账扩展到写入路径；
6. 维护窗口切换、回退和旧 DuckDB 只读归档；
7. 切换后运行 smoke、页面回归和每日任务验收。

## 13. PGM-08 隔离切换演练

已执行 `scripts/pg_cutover_rehearsal.py`，报告：`runtime/postgres_migration/20260922/cutover_rehearsal_report.json`。

```text
repository session: PASS (UTC, statement_timeout=30s)
key tables: publications=15, research_candidates_v3_3=2205
consumer gate: MIGRATE_TO_PG=19, UNCLASSIFIED=0
write transaction rollback: PASS (temporary probe absent after rollback)
current service /api/operations/status: HTTP 200 READY
current service /api/publications?include_analysis=0: HTTP 200
online switch: NOT_PERFORMED
data generation: NOT_TRIGGERED
status: PASS
```

演练只使用临时表和回滚事务，没有写入业务表，没有修改运行配置，没有触发生成任务；当前服务仍使用 DuckDB。

## 14. 下一阶段

下一步固定为 `PGM-09 / application adapter integration and config rollback rehearsal`：先在隔离配置下把 19 个入口切到 `workbench` schema，执行页面关键接口回归、写入事务演练和应用配置回退演练；通过后才允许维护窗口正式切换。未完成应用适配器和回退演练前，不开始 Focus Tracker 业务表和算法实现。

## 15. 阶段记录

| 字段 | 值 |
|---|---|
| stage | `PGM-00/01/02/03/04/05-shadow/06-shadow/07-drill/08-rehearsal` |
| stage_contract | `POSTGRES_MIGRATION_EXECUTION_RECORD_V1` |
| evidence | 目标连接、冻结快照 SHA-256、103 表复制、逐表行数对账、服务恢复、API shadow、PG 备份恢复、PGM-08 隔离切换演练报告 |
| acceptance_result | `DEGRADED_PASS / SHADOW_BACKUP_RESTORE_AND_CUTOVER_REHEARSAL_COMPLETE` |
| next_stage | `PGM-09 / application adapter integration and config rollback rehearsal` |
| code_changes | 新增 legacy 迁移器、PG schema builder、Artifact/consumer catalog builder、PG repository、数据层/API shadow-read、时间语义审计器、切换演练器；未修改在线主路径 |
| source_changes | 未修改 DuckDB 和 TDX 输入 |

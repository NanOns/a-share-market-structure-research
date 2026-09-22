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

## 14. PGM-09 应用切换前置盘点

已执行 `scripts/pg_application_cutover_inventory.py`，报告：`runtime/postgres_migration/20260922/application_cutover_inventory.json`。

```text
MIGRATE_TO_PG consumers: 19/19 recorded
unmapped direct consumers: 0
current backend: DUCKDB (all 19)
target backend: POSTGRESQL
application switch: NOT_STARTED
acceptance: DEGRADED_PASS_PRECUTOVER_INVENTORY
```

盘点同时建立 `workbench_meta.migration_consumer_cutovers`，逐入口登记目标适配器、当前后端、回退合同和证据。19 个入口全部仍是 `NOT_MIGRATED`，所以不能把配置文件单独改成 PostgreSQL，也不能在当前阶段重启服务宣称完成切换。现有设计文档中的正式最终切换门仍未开始。

已完成第一个只读适配器切片：`TodayResearchBundleReader` 支持显式注入 PostgreSQL repository，bundle 文件仍从受管文件读取，股票名称投影从 `workbench.research_runs_v3_3/research_candidates_v3_3` 读取。`scripts/today_research_pg_shadow.py` 对列表和详情请求完成 DuckDB/PG 语义对账：`list_match=true`、`detail_match=true`、两侧总数均为 467。该适配器尚未注入现有 HTTP 服务，因此应用切换状态仍为 `NOT_STARTED`。

第二个只读切片完成 publication head 投影：`PostgresRepository.publication_heads()` 与现有 `/api/publications` 的 `include_analysis=0/1` 两种响应均对账通过，各 7 条、latest head 一致；嵌套 `analysis_capabilities` 的 domain/date/slice/basis 质量计算已按相同规则移植并逐项匹配。

同一研究域的板块元数据和全量股票名称投影也已完成 shadow：板块 `498/498`、股票 `5464/5464`，均与冻结 DuckDB 一致；今日研究包列表/详情再次对账通过。报告分别位于 `runtime/postgres_migration/20260922/research_metadata_pg_shadow_report.json` 和 `today_research_pg_shadow_report.json`。

研究状态原始行投影也已完成：最新 `research_run_id=research-05f59f1294d348f3bf3c9fd6f57fcb81` 的 `research_sector_states` 共 532 行，DuckDB/PG 行数及 JSON 语义摘要一致。该结果只证明数据层投影，不等同于 `ResearchQueries` 已注入线上服务。

板块成员角色原始行也已对账：同一 run 的 `research_sector_member_roles` 共 15,546 行，DuckDB/PG JSON 语义一致。当前关系快照在 `membership_entries` 中为 0 行，报告明确标记 `DEGRADED_PASS_EMPTY_SOURCE`；线上成员列表会回退读取 `relation_edge_intervals`，因此该关系边投影必须单独完成，不能把空表一致误报为成员迁移完成。

关系边回退链路已完成独立 shadow：针对 publication `m4-9540768dfa3c23169cac2e2b2da25711`，按 `relation_publication_bindings` 的 source scope 与 revision 区间连接 `relation_edge_intervals`，DuckDB 与 PostgreSQL 均返回 72,457 行，排序后的语义摘要 SHA-256 均为 `2f0410b61282bbc168c8f084b6ebe1db03d857cca0327920d7dafd1736f58338`，`rows_match=true`，结果为 `PASS`。报告位于 `runtime/postgres_migration/20260922/relation_edges_pg_shadow_report.json`。这证明线上成员列表的实际关系边数据层 fallback 已可由 PG 重建，但尚未把该 repository 注入 `ResearchQueries` 或 HTTP 服务，不能据此宣称应用切换完成。

已完成适配器集成与配置回退隔离演练：`scripts/pg_adapter_integration_rehearsal.py` 显式注入 `PostgresRepository` 到 `TodayResearchBundleReader`，今日研究列表/详情均为 `READY`（467 条），publication heads 7 条且均包含分析能力投影；最新研究 run 的 sector state 532 行、member role 15,546 行均可由 PG 适配器读取。配置回退只在临时沙盒中原子替换，回退后 SHA-256 恢复为 `d2e0612b6c387f294eb5724bb1b0dc03e14f28664896d449e452b2595eb2d21b`，跟踪配置未被触碰。结果为 `DEGRADED_PASS_PRECUTOVER_ADAPTER_AND_ROLLBACK`，报告位于 `runtime/postgres_migration/20260922/pg_adapter_integration_rehearsal_report.json`；该演练仍未注入线上 HTTP 服务。

已建立 backend-neutral 的 `PublicationReadRepository` 合同和 `DuckDBReadRepository` 只读实现，并让 `PostgresRepository` 满足同一合同。`scripts/workbench_read_contract_shadow.py` 对冻结快照和 PG 的四项公共投影完成对账：publication heads `7/7`、股票名称 `5464/5464`、板块元数据 `498/498`、关系边 `72457/72457`，所有摘要一致，结果为 `DEGRADED_PASS_READ_BOUNDARY_SHADOW`。报告位于 `runtime/postgres_migration/20260922/workbench_read_contract_shadow_report.json`。该合同仅覆盖只读投影，未把写入职责伪装成已迁移。

下一步固定为 `PGM-09 / repository write boundary design`：按盘点表继续拆分 `ResearchRepository`、`OperationsRepository` 和 `ArtifactCatalog` 的事务/幂等/路径合同，先在临时表和回滚事务中验证写入，再考虑受控配置注入；通过前仍不修改线上主路径，不开始 Focus Tracker 业务表和算法实现。

## 15. 阶段记录

| 字段 | 值 |
|---|---|
| stage | `PGM-00/01/02/03/04/05-shadow/06-shadow/07-drill/08-rehearsal/09-inventory` |
| stage_contract | `POSTGRES_MIGRATION_EXECUTION_RECORD_V1` |
| evidence | 目标连接、冻结快照 SHA-256、103 表复制、逐表行数对账、服务恢复、API shadow、PG 备份恢复、PGM-08 隔离切换演练、19 个应用直连点切换盘点、今日研究包读路径 shadow、publication head shadow、研究元数据 shadow、研究状态/成员角色原始行 shadow、关系边 fallback shadow、适配器注入与配置回退隔离演练、统一只读 repository 合同 shadow、空 membership_entries 降级证据 |
| acceptance_result | `DEGRADED_PASS / SHADOW_BACKUP_RESTORE_CUTOVER_REHEARSAL_AND_APPLICATION_INVENTORY_COMPLETE` |
| next_stage | `PGM-09 / repository write boundary design` |
| code_changes | 新增 legacy 迁移器、PG schema builder、Artifact/consumer catalog builder、统一只读 repository 合同及 DuckDB/PG 实现、今日研究包、publication head、研究元数据、研究状态、成员角色与关系边只读适配器、数据层/API shadow-read、适配器注入与配置回退隔离演练、时间语义审计器、切换演练器、应用直连点盘点器；未修改在线主路径 |
| source_changes | 未修改 DuckDB 和 TDX 输入 |

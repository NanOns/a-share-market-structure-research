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
| 静态代码消费者（最新目录） | 113 |
| `MIGRATE_TO_PG`（最新目录） | 12 |
| `OFFLINE_DUCKDB_ALLOWED`（最新目录） | 79 |
| `RETAIN_UNTIL_AUDIT_CLOSE`（最新目录） | 22 |
| `UNCLASSIFIED` | 0 |

`UNCLASSIFIED` 已清零。早期盘点曾记录 97 个消费者；经过适配器边界收口和误报清理，最新静态目录为 113 个：12 个服务/运维入口列为 `MIGRATE_TO_PG`，79 个离线/分析入口列为 `OFFLINE_DUCKDB_ALLOWED`，22 个历史修复/审计脚本保留到审计关闭。分类变化是目录修正，不代表任何线上入口已经切换。

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

- 早期 97 个消费者全部从 `UNCLASSIFIED` 归类；随着入口边界收口，最新静态目录为 113 个，仍全部落在 `MIGRATE_TO_PG`、`OFFLINE_DUCKDB_ALLOWED` 或 `RETAIN_UNTIL_AUDIT_CLOSE`；
- 建立 `workbench_meta.timestamp_semantics_catalog`，42 个 TIMESTAMP 列中 38 个经 writer 证据确认并转为 `timestamptz`；4 个仍保留 `timestamp without time zone` 并标记 `PENDING_REVIEW`（外部证据三列无生产持久化 writer、行情 `quote_time` 无统一来源时区契约）；
- 建立 `src/workbench_db/postgres_repository.py`；
- 对 `/api/publications?include_analysis=0` 做同请求 shadow read，7 条结果、latest head 均一致；报告位于 `runtime/postgres_migration/20260922/api_shadow_read_report.json`。

API shadow read 仍不是在线切换。当前最新清单中的 12 个服务/运维入口尚未改为使用 PG；时间字段合同已全部收口，但应用后端切换硬门仍未通过。

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
consumer gate: MIGRATE_TO_PG=12, UNCLASSIFIED=0
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
MIGRATE_TO_PG consumers: 12/12 recorded
unmapped direct consumers: 0
current backend: DUCKDB (all 12)
target backend: POSTGRESQL
application switch: NOT_STARTED
acceptance: DEGRADED_PASS_PRECUTOVER_INVENTORY
```

盘点同时建立 `workbench_meta.migration_consumer_cutovers`，逐入口登记目标适配器、当前后端、回退合同和证据。12 个入口全部仍是 `NOT_MIGRATED`，所以不能把配置文件单独改成 PostgreSQL，也不能在当前阶段重启服务宣称完成切换。现有设计文档中的正式最终切换门仍未开始。

已完成第一个只读适配器切片：`TodayResearchBundleReader` 支持显式注入 PostgreSQL repository，bundle 文件仍从受管文件读取，股票名称投影从 `workbench.research_runs_v3_3/research_candidates_v3_3` 读取。`scripts/today_research_pg_shadow.py` 对列表和详情请求完成 DuckDB/PG 语义对账：`list_match=true`、`detail_match=true`、两侧总数均为 467。该适配器尚未注入现有 HTTP 服务，因此应用切换状态仍为 `NOT_STARTED`。

PGM-09 重新扫描并清理了消费者目录中的陈旧记录：当前静态目录为 113 个消费者，其中 `MIGRATE_TO_PG=12`、`OFFLINE_DUCKDB_ALLOWED=79`、`RETAIN_UNTIL_AUDIT_CLOSE=22`、`UNCLASSIFIED=0`。`TodayResearchBundleReader` 已移除 `duckdb.connect` 直连，`SourceFreezer`、结果对象协调器、切片协调器、维护状态读取和配置历史读取也分别通过 `PublicationReadRepository`、`ResultObjectRepository`、`SliceRepository`、`OperationsMetadataReader`、`ConfigVersionStore` 边界收口；离线默认使用 DuckDB 适配器，切换阶段可注入 PostgreSQL。另将 `TurnoverEnrichmentService` 的内存 `read_parquet` 会话明确标记为 `OFFLINE_DUCKDB_ALLOWED`，因为它不打开 `market_research.duckdb`、不写库且只生成请求时指纹。上述变化减少的是静态误报和直连面，不代表 PostgreSQL 已成为线上主库。

结果对象适配器在真实 PG 上完成独立演练：首次写入、同一 identity 重放复用、缺失 daily-basis 字段触发事务回滚、回滚后无残留，并在清理后恢复业务表状态；报告为 `DEGRADED_PASS_RESULT_OBJECT_REPOSITORY`，位于 `runtime/postgres_migration/20260922/pg_result_object_repository_rehearsal_report.json`。该演练未写入线上研究数据，也未接入主生成任务。

切片适配器随后完成真实 PG 演练：基础切片可见、依赖切片可见、缺失 daily-basis 字段触发事务回滚且无残留；报告为 `DEGRADED_PASS_SLICE_REPOSITORY`，位于 `runtime/postgres_migration/20260922/pg_slice_repository_rehearsal_report.json`。Parquet 对象仍由本地受管文件写入，PG 只负责切片元数据和依赖关系。

本轮继续关闭运维配置历史的连接边界：新增 `ConfigVersionStore` 合同、DuckDB 兼容实现和 PostgreSQL 实现，`OperationsConfig` 的版本持久化与历史查询不再在业务模块内直接调用 `duckdb.connect`；`scripts/pg_config_store_rehearsal.py` 完成 PG 写入、读取、清理闭环，结果为 `DEGRADED_PASS_CONFIG_STORE`。默认线上配置仍保持 DuckDB 兼容实现，未改变服务后端，也未触发配置切换。

随后为存储对象登记、租约、清理计划和运维状态元数据增加了可注入的 `StorageMetadataRepository` 边界，`StorageGovernance.register/acquire_lease/release_lease/preview_cleanup()` 与 `MaintenanceService.status()` 可在隔离调用中使用 PostgreSQL；`scripts/pg_storage_write_integration_rehearsal.py` 验证重复登记、跨事务读取、租约释放、PG 清理预览、清理计划 round-trip、运维状态读取，并验证文件隔离在该混合模式下 fail-closed，结果为 `DEGRADED_PASS_STORAGE_WRITE_INTEGRATION`。文件隔离和永久删除仍未切换，线上服务仍使用 DuckDB。

4 个未决时间字段已补齐版本化来源合同：`PostgresOnlineRepository` 只接受带显式 offset 的 ISO-8601 时间，缺失 `quote_time` 或无时区输入直接拒绝；目标 PostgreSQL 表当时均为 0 行，因此按 `PG_TIMESTAMP_SEMANTICS_V3` 安全升级为 `timestamptz`。`scripts/pg_online_time_contract_rehearsal.py` 验证证据/报价写入、无时区拒绝、报价时间缺失拒绝和事务回滚，结果为 `DEGRADED_PASS_ONLINE_TIME_CONTRACT`。当前 timestamp 盘点为 `APPLIED=42`、`PENDING_REVIEW=0`；这只关闭时间语义合同，不启用任何在线数据源。

当前 12 个应用入口已逐项重新盘点但仍保持 `NOT_MIGRATED`，没有把“已有 adapter slice”冒充“线上已切换”：`storage.py`、`maintenance.py` 和 `app.py` 已有局部 PG 边界；`backup.py`、`migration.py`、publisher、研究 run/slice 写入器、配置切换和主 API 仍存在 DuckDB 事务或默认后端依赖。`SourceFreezer`、结果对象协调器、切片协调器、维护状态读取和配置历史读取已从静态待迁移目录移除，但其实际 PG 使用仍需由上层在切换阶段注入；`scripts/pg_application_cutover_inventory.py` 的 evidence 字段逐入口记录这些局部进展和剩余阻塞。

第二个只读切片完成 publication head 投影：`PostgresRepository.publication_heads()` 与现有 `/api/publications` 的 `include_analysis=0/1` 两种响应均对账通过，各 7 条、latest head 一致；嵌套 `analysis_capabilities` 的 domain/date/slice/basis 质量计算已按相同规则移植并逐项匹配。

同一研究域的板块元数据和全量股票名称投影也已完成 shadow：板块 `498/498`、股票 `5464/5464`，均与冻结 DuckDB 一致；今日研究包列表/详情再次对账通过。报告分别位于 `runtime/postgres_migration/20260922/research_metadata_pg_shadow_report.json` 和 `today_research_pg_shadow_report.json`。

研究状态原始行投影也已完成：最新 `research_run_id=research-05f59f1294d348f3bf3c9fd6f57fcb81` 的 `research_sector_states` 共 532 行，DuckDB/PG 行数及 JSON 语义摘要一致。该结果只证明数据层投影，不等同于 `ResearchQueries` 已注入线上服务。

板块成员角色原始行也已对账：同一 run 的 `research_sector_member_roles` 共 15,546 行，DuckDB/PG JSON 语义一致。当前关系快照在 `membership_entries` 中为 0 行，报告明确标记 `DEGRADED_PASS_EMPTY_SOURCE`；线上成员列表会回退读取 `relation_edge_intervals`，因此该关系边投影必须单独完成，不能把空表一致误报为成员迁移完成。

关系边回退链路已完成独立 shadow：针对 publication `m4-9540768dfa3c23169cac2e2b2da25711`，按 `relation_publication_bindings` 的 source scope 与 revision 区间连接 `relation_edge_intervals`，DuckDB 与 PostgreSQL 均返回 72,457 行，排序后的语义摘要 SHA-256 均为 `2f0410b61282bbc168c8f084b6ebe1db03d857cca0327920d7dafd1736f58338`，`rows_match=true`，结果为 `PASS`。报告位于 `runtime/postgres_migration/20260922/relation_edges_pg_shadow_report.json`。这证明线上成员列表的实际关系边数据层 fallback 已可由 PG 重建，但尚未把该 repository 注入 `ResearchQueries` 或 HTTP 服务，不能据此宣称应用切换完成。

已完成适配器集成与配置回退隔离演练：`scripts/pg_adapter_integration_rehearsal.py` 显式注入 `PostgresRepository` 到 `TodayResearchBundleReader`，今日研究列表/详情均为 `READY`（467 条），publication heads 7 条且均包含分析能力投影；最新研究 run 的 sector state 532 行、member role 15,546 行均可由 PG 适配器读取。配置回退只在临时沙盒中原子替换，回退后 SHA-256 恢复为 `d2e0612b6c387f294eb5724bb1b0dc03e14f28664896d449e452b2595eb2d21b`，跟踪配置未被触碰。结果为 `DEGRADED_PASS_PRECUTOVER_ADAPTER_AND_ROLLBACK`，报告位于 `runtime/postgres_migration/20260922/pg_adapter_integration_rehearsal_report.json`；该演练仍未注入线上 HTTP 服务。

已建立 backend-neutral 的 `PublicationReadRepository` 合同和 `DuckDBReadRepository` 只读实现，并让 `PostgresRepository` 满足同一合同。`scripts/workbench_read_contract_shadow.py` 对冻结快照和 PG 的四项公共投影完成对账：publication heads `7/7`、股票名称 `5464/5464`、板块元数据 `498/498`、关系边 `72457/72457`，所有摘要一致，结果为 `DEGRADED_PASS_READ_BOUNDARY_SHADOW`。报告位于 `runtime/postgres_migration/20260922/workbench_read_contract_shadow_report.json`。该合同仅覆盖只读投影，未把写入职责伪装成已迁移。

已完成首个写入边界探针：`PostgresWriteRepository` 为 `jobs` 和 `storage_objects` 提供参数化、幂等 upsert 与读取接口，`scripts/pg_write_boundary_rehearsal.py` 在真实 PG 事务中连续 upsert 后强制回滚；回滚前状态为 `RUNNING`/`ROLLBACK_PROBE`，回滚后两条业务记录均不存在，结果为 `DEGRADED_PASS_TRANSACTIONAL_IDEMPOTENCY_ROLLBACK`。报告位于 `runtime/postgres_migration/20260922/pg_write_boundary_rehearsal_report.json`。该写入边界尚未被任何线上任务调用。

已完成 `ResearchRepository` 首个写入合同：`PostgresResearchRepository` 复用研究任务字段校验和 canonical JSON，按 `(publication_id, trade_date, snapshot_id, membership_snapshot_id, algorithm_version, parameter_hash, dependency_bindings)` 生成稳定 `input_key`；`start` 对相同输入幂等复用，`complete` 对已完成 run 幂等返回，并把 sector state/member role 与 run 状态放在同一外部事务。`scripts/pg_research_write_contract_rehearsal.py` 验证了 start 重放、complete 重放、可见性和强制回滚；回滚后 `research_runs`、`research_sector_states`、`research_sector_member_roles` 均无残留，结果为 `DEGRADED_PASS_RESEARCH_IDENTITY_IDEMPOTENCY_ROLLBACK`。报告位于 `runtime/postgres_migration/20260922/pg_research_write_contract_rehearsal_report.json`。该 writer 尚未接入研究生成任务。

已完成 `OperationsRepository + ArtifactCatalog` 的首个合同切片：`PostgresArtifactCatalog` 将运行时地址收敛为 `managed_root_id + relative_path + sha256 + size_bytes`，拒绝绝对路径、`..` 穿越、盘符路径和受保护根；登记使用参数化 upsert，仍由外部事务决定提交。`scripts/pg_operations_artifact_contract_rehearsal.py` 在临时受管文件上验证登记、摘要 round-trip、强制回滚和 3 类非法路径拒绝，结果为 `DEGRADED_PASS_MANAGED_ROOT_ARTIFACT_ROLLBACK`。报告位于 `runtime/postgres_migration/20260922/pg_operations_artifact_contract_rehearsal_report.json`。该 catalog 尚未替换线上 source freezer、publisher 或 storage service。

本轮继续处理 publisher 入口，但只完成边界收口，未宣称迁移完成：`OneClickPublisher` 不再直接创建 DuckDB repository，也不再直接打开数据库读取 job status；新增 `PublicationRepositoryFactory` 与 `PublicationStatusReader` 合同，当前由 `DuckDBPublicationRepositoryFactory`/`DuckDBPublicationStatusReader` 提供兼容实现，并保留 `MIGRATION_CONTRACT` 标记，直到 PostgreSQL publisher writer、状态读取和全量提交事务完成真实 rehearsal。现有 M4/M2 publication binding 测试继续通过；该入口在 `migration_consumer_cutovers` 中仍为 `NOT_MIGRATED`。

本轮补齐 publisher 状态读取的 PG 实现：新增 `PostgresPublicationStatusReader`，按 `jobs` 与最新 `job_events` 投影出与 DuckDB reader 相同的 `status/publication_id/progress/updated_at_utc` 合同；`scripts/pg_publication_status_reader_rehearsal.py` 在真实 PG 上验证状态与事件 round-trip、清理后 `JOB_NOT_FOUND`，结果为 `DEGRADED_PASS_PUBLICATION_STATUS_READER`，报告位于 `runtime/postgres_migration/20260922/pg_publication_status_reader_rehearsal_report.json`。发布主写事务、bulk 导入和 relation binding 尚未有 PostgreSQL 实现，线上 publisher 仍未切换。

随后建立 `PostgresPublicationWriter`：提供 publication identity、按交易日计算 revision、显式允许的日表批量写入、publication head 绑定和成功状态更新，所有操作在同一 PostgreSQL transaction 中提交；`scripts/pg_publication_writer_rehearsal.py` 验证 publication round-trip、stock 日表批量行、head 绑定、强制回滚和清理，结果为 `DEGRADED_PASS_PUBLICATION_WRITER`，报告位于 `runtime/postgres_migration/20260922/pg_publication_writer_rehearsal_report.json`。relation binding、artifact 写入、outcome identity 和 `OneClickPublisher` 主流程尚未注入该 writer，publisher 入口仍为 `NOT_MIGRATED`。

publisher 的关系依赖也已建立 PG 边界：`PostgresRelationRepository` 支持 relation revision、edge interval、sector attribute version、UNCHANGED 重复观察和事务回滚；`scripts/pg_relation_repository_rehearsal.py` 验证首次 revision、同内容重复观察不递增、变更产生新 revision、回滚无残留和清理，结果为 `DEGRADED_PASS_RELATION_REPOSITORY`，报告位于 `runtime/postgres_migration/20260922/pg_relation_repository_rehearsal_report.json`。该仓储尚未注入 `OneClickPublisher` 的 relation binding，publisher 主流程仍保持 `NOT_MIGRATED`。
publisher 的关系依赖也已建立 PG 边界：`PostgresRelationRepository` 支持 relation revision、edge interval、sector attribute version、UNCHANGED 重复观察和事务回滚；`scripts/pg_relation_repository_rehearsal.py` 验证首次 revision、同内容重复观察不递增、变更产生新 revision、回滚无残留和清理，结果为 `DEGRADED_PASS_RELATION_REPOSITORY`，报告位于 `runtime/postgres_migration/20260922/pg_relation_repository_rehearsal_report.json`。`OneClickPublisher` 现在支持显式注入 `relation_writer_factory`，默认仍使用 DuckDB `RelationRepository`；PG writer 可在同一外部事务中接入，但 publication 主 SQL、artifact/outcome 和 app 默认 factory 仍未切换，publisher 主流程继续保持 `NOT_MIGRATED`。

本轮先固化 backend 配置合同：`config/workbench.yaml` 保持当前 `duckdb` 为 active backend，同时登记 `postgresql_target`（`WORKBENCH_PG_DSN`、`workbench` schema、维护窗口要求、PG 不可用时 fail-closed、`cutover_state=NOT_STARTED`）。这只是可审计的目标配置，不会被当前服务自动读取或触发切换；正式切换仍需完成全部应用入口和维护窗口回退演练。

随后处理历史分析激活入口：`AnalysisActivationService` 不再直接调用 `duckdb.connect`，新增 `AnalysisActivationRepository` 连接边界，当前仅由 DuckDB 兼容实现提供连接；准备快照、激活 publication、复制结果组、绑定 snapshot 和更新 head 的多表事务仍完整保留在服务内，直到 PostgreSQL 事务实现与回滚/幂等 rehearsal 完成前，该入口继续标记为 `NOT_MIGRATED`。M7B activation 测试 `3 passed`，未触发线上激活。

继续处理历史分析任务入口：`HistoryJobService` 的连接、短锁重试和任务状态/事件读写已收敛到 backend-neutral 的 `HistoryJobRepository/HistoryJobStore`，服务仍保留取消、进度、恢复和事件顺序语义；当前线上默认仍是 DuckDB，PG 仅可显式注入，尚未接入服务默认路径，因此 `history_jobs.py` 仍为 `NOT_MIGRATED`。M7B history job 与 activation 回归测试合计 `6 passed`，未提交线上任务或生成数据。

本轮补齐了历史任务 PostgreSQL 状态边界：新增 `PostgresHistoryJobRepository`，对 `jobs`、`job_attempts`、`job_events` 提供参数化 upsert、状态/进度更新、按 attempt 的事件序号、活动 HISTORY_ANALYSIS 过滤和事务删除；事件插入使用 `ON CONFLICT DO NOTHING` 重试，避免并发取消/进度写入造成重复序号。`HistoryJobService` 已改为只依赖显式 store 合同，DuckDB 和 PostgreSQL 可通过同一事务接口注入。`scripts/pg_history_job_repository_rehearsal.py` 在真实 PG 上验证 job/attempt round-trip、事件序号 `1,2`、活动任务过滤、强制事务回滚和清理，结果为 `DEGRADED_PASS_HISTORY_JOB_REPOSITORY`，报告位于 `runtime/postgres_migration/20260922/pg_history_job_repository_rehearsal_report.json`。该 adapter 尚未注入线上 `app.py`，也未完成真实 PG 取消/恢复端到端演练，因此入口继续标记为 `NOT_MIGRATED`；下一门是显式注入服务并完成端到端取消、恢复、失败重试演练。

随后处理增量研究写入入口：`IncrementalBuildCoordinator` 的数据库连接已改为注入 `IncrementalWriterRepository`，保留现有计划校验、域写入器、快照绑定和事务语义；目前只有 DuckDB 兼容实现，所有域 writer 的 PostgreSQL SQL/事务尚未完成，因此该入口仍为 `NOT_MIGRATED`。现有 P04-02 测试仍被仓库中旧的 `034_v3_signal_outcomes` 版本断言阻塞（实际最新迁移为 `035_v3_3_research_registry`），该失败与本次连接边界改动无关，未擅自修改测试基线。

继续处理研究构建入口：`build_latest_research_run` 现在通过 `ResearchBuilderRepository` 获取数据库连接，算法计算、Parquet 读取和 `ResearchRunStore` 提交顺序未改变；由于 SQL 仍包含 DuckDB `read_parquet` 与 DuckDB 专用查询语义，当前只完成连接边界，PG 实现和双引擎结果对账仍是独立门，`research_builder.py` 继续保持 `NOT_MIGRATED`。相关元数据/排序/历史对齐测试 `6 passed`，未触发线上研究构建。

随后处理 V3 每日入口：`run_v3_daily_entry` 与增量 writer 共用注入的 `IncrementalWriterRepository`，读取源 snapshot、复用条目和最终 snapshot 绑定仍在同一兼容流程中；该入口的完整 SQL/结果对象写入仍是 DuckDB 语义，因此继续保持 `NOT_MIGRATED`。P04-02 集成测试受同一既有 `034_v3_signal_outcomes` 版本断言影响（`2 passed / 4 failed`），失败发生在测试数据库初始化阶段，未进入本次连接边界代码。

运维备份入口随后完成连接边界收口：`BackupService` 的主库、只读审计、备份文件验证和内存 Parquet 校验统一通过 `BackupRepository`，备份复制、哈希校验、恢复演练及“必须维护窗口”门禁保持不变；当前只有 DuckDB 兼容实现，backup catalog 的 PostgreSQL 写入/恢复登记尚未接入，因此 `backup.py` 仍为 `NOT_MIGRATED`。M5/M7B 备份恢复与 P04-03 链路测试 `7 passed`。

本轮把 `backup_catalog` 元数据进一步抽成 `BackupCatalogRepository`：`BackupService` 的创建、恢复登记、链路审计和孤儿溯源不再直接执行该表 SQL；新增 `DuckDBBackupCatalogRepository` 与 `PostgresBackupCatalogRepository`，物理 DuckDB 备份文件、受管对象复制和恢复校验仍留在原有维护窗口流程。`scripts/pg_backup_catalog_repository_rehearsal.py` 在真实 PG 上验证目录 round-trip、冲突重放保持首写、列表读取、强制事务回滚和清理，结果为 `DEGRADED_PASS_BACKUP_CATALOG_REPOSITORY`，报告位于 `runtime/postgres_migration/20260922/pg_backup_catalog_repository_rehearsal_report.json`。该目录适配器尚未接入线上 BackupService 默认实例，也未改变备份文件后端，因此 `backup.py` 继续保持 `NOT_MIGRATED`。

数据库迁移准备入口随后完成路径/依赖边界收口：`DatabaseMigration` 使用统一数据库路径解析，并允许注入备份实现；目标路径、TDX 禁止写入、维护窗口、原子替换和旧库保留规则未改变。该入口仍只是 DuckDB 离线副本准备，不代表 PostgreSQL 激活，M5 migration 测试 `3 passed`，仍保持 `NOT_MIGRATED`。

存储治理入口随后完成连接边界收口：`StorageGovernance` 的 DuckDB 兼容回退路径统一通过 `StorageConnectionRepository`，已有 `StorageMetadataRepository` 注入路径、受管目录校验、租约、预览、隔离和删除前硬门均保持不变；PG 元数据路径仍需接入真实服务并完成清理生命周期 rehearsal，因此 `storage.py` 继续为 `NOT_MIGRATED`。存储治理与预览测试 `7 passed`。

主 API 入口开始收口：`Api.request_scope()` 与 `_con()` 统一通过可注入的 `ApiConnectionProvider` 获取连接，保留请求级复用和串行化锁语义；其他 legacy 路由、子进程回执读取和 DuckDB 专用查询尚未迁移，因此 `app.py` 仍为 `NOT_MIGRATED`。研究 API/UI 回归测试 `6 passed`，未注入线上 PostgreSQL。

主 API 的运维目录读取继续收口：`/api/operations/storage`、`/backups`、`/cleanup-plans` 改由 `StorageGovernance.payload_rows()` 读取，优先使用可注入的 `StorageMetadataRepository`（包括 PostgreSQL 实现），兼容路径仍是只读 DuckDB；操作路由其余直连和子进程回执读取尚未关闭，`app.py` 仍保持 `NOT_MIGRATED`。存储、运维 UI 和研究 API 回归测试合计 `11 passed`。

主 API 连接收口继续完成：Parquet 请求时查询改用 provider 的内存连接，输入回执目录读取也改走 `ApiConnectionProvider`；`app.py` 已无 `duckdb.connect` 直接调用，仅保留 DuckDB 异常类型判断和未迁移合同标记。路由 SQL、缓存和锁语义未改变，API/UI 相关测试 `10 passed`，该入口仍未接入 PostgreSQL。

已完成隔离 adapter injection harness：`BackendRepositoryProvider` 只按显式 backend 打开 DuckDB 快照或 PostgreSQL，`AdapterHttpGateway` 在 PG 连接失败时返回 `503/POSTGRES_UNAVAILABLE`，不回退 DuckDB。`scripts/pg_cutover_adapter_injection_harness.py` 对 publication heads、研究元数据和今日研究包完成 DuckDB/PG 同请求对账（股票 `5464`、板块 `498`、今日研究总数一致），并验证故障时 `fallback_used=false`，结果为 `DEGRADED_PASS_ISOLATED_ADAPTER_INJECTION_503`。报告位于 `runtime/postgres_migration/20260922/pg_cutover_adapter_injection_harness_report.json`。该 provider 尚未注入现有 `app.py` 或日常任务。

已执行 `scripts/pg_maintenance_cutover_preflight.py` 只读门禁汇总：数据表 catalog `103/103 DATA_COPIED`，ArtifactCatalog `141/141 AVAILABLE`，所有 shadow、备份恢复、写入回滚和 adapter injection 证据均有效；时间语义已为 `42 APPLIED / 0 PENDING_REVIEW`，但硬门仍为 `BLOCKED_PRECUTOVER_HARD_GATES`，阻塞项是应用直连消费者 `12 NOT_MIGRATED`，以及当前服务明确仍指向 DuckDB。报告位于 `runtime/postgres_migration/20260922/pg_maintenance_cutover_preflight.json`。该结果不是失败数据迁移，而是禁止提前切换的真实前置结论。

下一步固定为 `PGM-09 / complete application adapter migration`：继续把 12 个入口按读边界、运维元数据边界、研究写入边界和主 API 注入分批收口，并重新执行只读 preflight；在所有硬门通过并经维护窗口授权前，不执行线上切换，不开始 Focus Tracker 业务表和算法实现。

## 15. 阶段记录

| 字段 | 值 |
|---|---|
| stage | `PGM-00/01/02/03/04/05-shadow/06-shadow/07-drill/08-rehearsal/09-inventory/09-adapter-slices` |
| stage_contract | `POSTGRES_MIGRATION_EXECUTION_RECORD_V1` |
| evidence | 目标连接、冻结快照 SHA-256、103 表复制、逐表行数对账、服务恢复、API shadow、PG 备份恢复、PGM-08 隔离切换演练、当前 12 个应用直连点切换盘点、TodayResearchBundleReader/SourceFreezer/ResultObjectRepository/SliceRepository/OperationsMetadataReader/ConfigVersionStore 适配器边界、TurnoverEnrichmentService 内存 Parquet 分类证据、publication head shadow、研究元数据 shadow、研究状态/成员角色原始行 shadow、关系边 fallback shadow、适配器注入与配置回退隔离演练、统一只读 repository 合同 shadow、operations 写入边界幂等/事务回滚演练、research run 写入合同幂等/事务回滚演练、ArtifactCatalog managed-root/路径回退演练、隔离 adapter injection 双读与 PG 503 fail-closed 演练、ConfigVersionStore PG 写入/读取/清理演练、StorageMetadataRepository PG 登记/幂等/跨事务读取/租约/清理计划演练、ResultObject/SliceRepository PG 幂等与回滚演练、PostgresHistoryJobRepository job/attempt/event/回滚演练、BackupCatalogRepository 目录 round-trip/重放/回滚演练、PostgresPublicationStatusReader 状态/事件投影演练、PostgresPublicationWriter publication/批量行/head/回滚演练、PostgresRelationRepository revision/UNCHANGED/变更/回滚演练、维护状态 DuckDB/PG 元数据读边界演练、维护窗口 preflight 硬门汇总、空 membership_entries 降级证据 |
| acceptance_result | `DEGRADED_PASS / SHADOW_BACKUP_RESTORE_CUTOVER_REHEARSAL_AND_APPLICATION_INVENTORY_COMPLETE` |
| next_stage | `PGM-09 / complete application adapter migration` |
| code_changes | 新增 legacy 迁移器、PG schema builder、Artifact/consumer catalog builder、统一只读 repository 合同及 DuckDB/PG 实现、显式 backend provider 与 503 fail-closed gateway、PG 写入边界（jobs/storage_objects）、PG history job/attempt/event 写入边界、PG publication status/writer/relation 写入边界、PG research run/state/member-role 写入边界、PG research/config/storage metadata adapters、PG ArtifactCatalog managed-root 边界、ConfigVersionStore DuckDB/PG 实现、StorageMetadataRepository 注入边界、ResultObjectRepository/SliceRepository/OperationsMetadataReader/ConfigVersionStore DuckDB/PG 实现、PublicationRepositoryFactory/PublicationStatusReader publisher 边界、PostgresPublicationWriter/RelationRepository 合同演练、backend target config contract、今日研究包、publication head、研究元数据、研究状态、成员角色与关系边只读适配器、SourceFreezer publication/source-bundle repository 读取边界、TurnoverEnrichmentService 内存 Parquet 分类、数据层/API shadow-read、适配器注入与配置回退隔离演练、operations/research/ArtifactCatalog/ConfigVersion/StorageMetadata/ResultObject/SliceRepository/HistoryJobRepository/PublicationWriter/RelationRepository 合同幂等/事务回滚演练、隔离 adapter injection 双读/503 演练、维护状态读边界、维护窗口 preflight 汇总器、时间语义审计器、切换演练器、应用直连点盘点器；未修改在线主路径 |
| source_changes | 未修改 DuckDB 和 TDX 输入 |

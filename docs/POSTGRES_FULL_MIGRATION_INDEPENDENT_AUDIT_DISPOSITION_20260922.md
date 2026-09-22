# DuckDB → PostgreSQL 全库迁移独立审计处置（2026-09-22）

> 合同：`POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_V1`
> 输入：用户提供的独立审计、当前 V3 分支代码、schema 007—035、运维与备份实现、设计 V2。
> 初始审计边界：只做源码与合同审计；随后执行记录见 `POSTGRES_MIGRATION_EXECUTION_RECORD_20260922.md`。截至执行记录，已建立 PostgreSQL 18.6、冻结 DuckDB 快照并完成 `legacy` 全量复制，但尚未切换在线主库。

## 1. 总体结论

迁移方向完全成立，而且当前代码证明它是运行可靠性整改，不是单纯换数据库：

```text
PostgreSQL = 唯一在线服务主库
Parquet    = 大历史和离线事实层
DuckDB     = :memory: 或任务独立临时分析引擎
```

外部审计提出的 PG-01—PG-20 大部分正确。当前设计 V2 的迁移范围意识较完整，但在运行时 head、文件型 Forward、每表变更策略、时间语义、路径结构化和 PG 自身备份/迁移工具方面仍有实施前 P0。

阶段裁决：

```text
DEGRADED_PASS / PGM-00_REQUIRED_BEFORE_IMPLEMENTATION
```

## 2. 源码证实的迁移障碍

### 2.1 DuckDB 访问没有收口

当前至少存在这些生产直连类别：

- `app.py`：HTTP request scope、运维 API、输入恢复；
- `today_research_bundle.py`：请求时打开生产 DuckDB 补股票名称；
- `WorkbenchRepository`、publisher、research builder；
- history jobs、incremental writer、slice coordinator、analysis activation；
- backup、storage、maintenance、config、migration；
- 多个日常和验收脚本硬编码 `market_research.duckdb`。

因此 Repository 收口是切换硬门，不是代码风格优化。

### 2.2 API 还会即时扫描 Parquet

`app.py` 的 quote fallback、technical history、window sessions 会在 HTTP 请求中创建 DuckDB 内存连接并 `read_parquet()`。即使生产 `.duckdb` 文件迁走，这些路径仍违反“在线请求不启动分析引擎”的目标，需要提前物化或通过受控离线服务产生查询数据。

### 2.3 V3.3 head 仍是文件

`ACTIVE_RESEARCH_BUNDLE_V3_3.json` 当前决定活动 bundle；数据库 035 只是 registry。若页面仍读文件 pointer，PostgreSQL 就不是唯一在线权威。

### 2.4 Forward 事实不全在数据库

当前 V3.3 Forward 还依赖：

```text
data/forward_v3_3/observations/**
data/forward_v3_3/evaluation_sources/**
reports/p12_08/outcome_plan.json
reports/p12_08/outcome_results.json
```

它们必须进入 ArtifactCatalog 和迁移分类，不能因为不是 DuckDB 表而遗漏。

### 2.5 当前备份与迁移工具是 DuckDB 专用

- `BackupService` 执行 DuckDB CHECKPOINT、复制 `.duckdb`、用 DuckDB 试开；
- `DatabaseMigration` 是数据库文件路径迁移；
- `MigrationExecutor` 使用 DuckDB connection、SHOW TABLES 和 DuckDB SQL。

三者不能改个连接串就复用于 PostgreSQL。

## 3. 运行时唯一主权

切换后 PostgreSQL 必须保存并激活以下 heads：

```text
publication_heads
analysis_snapshot_heads / bindings
research_bundle_heads
focus_trade_date_heads
relation publication bindings
operations/config active revision
job current state
```

不可再使用：

```text
MAX(revision)
目录最新文件
mtime
字段最完整 observation
ACTIVE_*.json pointer
```

选择业务当前版本。

文件 bundle 的正确发布顺序：

```text
不可变 artifact 完整写入并校验
→ PostgreSQL 事务写 artifact_id 和正式 head
→ COMMIT 后对 API 可见
```

文件 pointer 可作为可重建兼容缓存，但不是权威。

## 4. PGM-00 必须生成的五份 catalog

### 4.1 `database_migration_catalog.json`

每张真实表/视图记录：

- schema、列、类型、PK、unique、check、index；
- 行数、主键 distinct、NULL 计数、日期范围；
- 读取者、写入者、变更行为；
- 迁移类别、目标表和摘要合同。

### 4.2 `database_consumer_catalog.json`

扫描并人工确认所有：

```text
duckdb.connect
read_parquet
market_research.duckdb
DatabaseOwner
WorkbenchRepository
```

每个入口标记：

```text
MIGRATE_TO_PG
OFFLINE_DUCKDB_ALLOWED
RETIRED
```

HTTP request path 中不允许 `OFFLINE_DUCKDB_ALLOWED`。

### 4.3 `artifact_pointer_catalog.json`

覆盖：

- V3.3 active bundle、bundle/results/contracts；
- V3.3 forward observations、outcome plan/result、evaluation sources；
- analysis result objects、source bundles、manifest、receipt；
- storage objects 和 DuckDB backups。

记录 content digest、物理位置、消费者、head 语义、迁移分类和可用性。

### 4.4 `timestamp_semantics_catalog.json`

每个 TIMESTAMP 列逐列记录：

```text
source_type
writer_code
semantic_timezone
sample range
target_type
transform rule
```

字段名含 `_utc` 只是线索，不是自动转换证据。事件 instant 才映射 `timestamptz`；真正的本地墙钟时间保留 `timestamp without time zone`。

### 4.5 `migration_change_capture_catalog.json`

每表必须选择：

```text
IMMUTABLE_APPEND_PK
IMMUTABLE_REVISION
MUTABLE_UPSERT_RELOAD
CURRENT_PROJECTION_REBUILD
EXTERNAL_ARTIFACT
FINAL_WINDOW_FULL_RECOPY
```

并记录 mutation key、cursor、最后写入来源和最终切换策略。

## 5. 迁移策略修订

### 5.1 不实现复杂 CDC

本项目是本地研究工作台，优先采用：

1. 多次冻结副本迁移演练；
2. 摘要和 API 双读整改；
3. 最终短维护窗口；
4. mutable/upsert 表最终重载，append 表补 delta；
5. 重建 heads/projections；
6. 完整复核后切换。

这比自行建设长期 DuckDB/PG 双写或通用 CDC 更可靠。

### 5.2 修正 publication delta

`publications` 的真实时间字段是 `imported_at_utc`，不是 V2 示例中的 `created_at`。但不应只改字段名后继续使用通用 cursor；仍按 catalog 为每张表决定策略。

### 5.3 Mutable 表

至少包括：

- `research_runs`：FAILED/BUILDING/COMPLETE 状态更新；
- `research_signal_outcomes`：upsert 到 OBSERVED；
- `storage_objects`、`leases`；
- publication/current heads、current projections；
- jobs/attempts 的运行状态。

这些表在最终窗口重新复制或重建，不假设 append-only。

## 6. PostgreSQL schema 与工具边界

### 6.1 新建 `PG_SCHEMA_V1`

- 007—035 作为 DuckDB 历史迁移证据导入 `legacy_schema_migration_evidence`；
- 不在 PostgreSQL 直接重放 DuckDB SQL；
- 使用独立 PG migration ledger、依赖和 checksum；
- 目标 schema 依据业务约束重建 FK、check、index，不机械翻译。

### 6.2 工具重命名和拆分

- 现有 `DatabaseMigration` 更名/定位为 `LegacyDuckDBFileRelocation`；
- 新建 `DuckDBToPostgresMigrator` 或版本化阶段脚本；
- 新建 PostgreSQL Backup/Restore Service；
- 旧 `backup_catalog` 记录补充 `source_engine=DUCKDB`、`restorable_to_engine=DUCKDB`、`legacy_read_only=true`；
- 旧备份不得在 PG 运维页显示为可直接恢复当前主库。

### 6.3 批量加载

`COPY FROM STDIN` 是首选候选实现，但属于需基准测试的实现选择，不是无条件硬门。小表可参数化批量 insert；大表在 PGM-00 规模确定后比较 COPY、批量 insert 和分区提交。

## 7. ArtifactCatalog 与路径

正式业务表只引用：

```text
artifact_id
managed_root_id
relative_path
sha256
size_bytes
artifact_contract
availability
```

旧绝对路径只保存为 `migration_source_path` 审计证据，不再作为运行地址。恢复或换工作区时通过 managed root 解析。

分类至少包含：

```text
V3_3_BUNDLE
V3_3_FORWARD_OBSERVATION
V3_3_FORWARD_OUTCOME_PLAN
V3_3_FORWARD_OUTCOME_RESULT
V3_3_FORWARD_EVALUATION_SOURCE
R4_FORWARD_ARTIFACT
ANALYSIS_RESULT_OBJECT
SOURCE_BUNDLE
MANIFEST
RECEIPT
LEGACY_DUCKDB_BACKUP
```

## 8. 跨引擎摘要修订

采纳 PG-13—PG-15：

- 排序在应用层按带类型和长度前缀的 canonical bytes 完成，不依赖数据库 collation；
- JSON 在应用层解析并 canonical encode，不比较 DuckDB JSON 文本与 `jsonb::text`；
- finite DOUBLE 首选 IEEE-754 binary64 big-endian bytes；Decimal 保持 scale；NaN/Inf 按表合同拒绝或独立 marker；
- NULL、空字符串、空 JSON、空数组必须区分；
- 大表按 publication/trade_date/slice 分区摘要，再形成全表 root digest。

上述编码必须先以跨 DuckDB/PostgreSQL 反例测试冻结，不能只写设计文字。

## 9. API 双读与请求一致性

### 9.1 双读比较分类

- 无序集合：canonical sort 后比较；
- 排名/队列/shortlist：逐位置比较 rank、实体、tie policy 和分页边界；
- JSON evidence：canonical object 比较；
- Decimal/float：使用业务合同精度，不用页面文本。

### 9.2 单请求版本一致性

请求开始只解析一次 immutable head，得到 publication/research/bundle/focus run identity；后续所有查询绑定该身份。不能在同一请求中多次查询 latest。需要多 SQL 严格同快照时再使用 `REPEATABLE READ`。

## 10. PostgreSQL 写入并发

保留“业务单写入器”原则，但不使用全局文件锁：

- 唯一键保证幂等；
- 同一 trade date + contract family 使用事务级 advisory lock 或等价串行化；
- page reads 继续并发；
- advisory lock 是否必要由实际写入器拓扑确认，若物理上始终只有一个 writer，可作为防御性约束而非强制依赖。

## 11. 最终切换与 smoke

最终 smoke 不向 jobs/publication/research/focus 写假业务数据。使用：

- `migration_smoke_checks` 专用表；或
- `BEGIN → INSERT probe → SELECT → ROLLBACK`；
- 其余检查均为只读 API 和 head 验证。

切换后必须证明：

```text
HTTP API:      无 duckdb.connect / read_parquet
常驻服务:      无生产 DuckDB 文件连接
后台离线计算:  仅 :memory: 或任务独立临时库
业务 head:     PostgreSQL 唯一权威
```

## 12. 外部审计逐项裁决

| 编号 | 裁决 | 本项目处理 |
|---|---|---|
| PG-01 | 接受 / P0 | 全部生产 DuckDB 直连收口 |
| PG-02 | 接受 / P0 | HTTP request-time Parquet 扫描退出 |
| PG-03 | 接受 / P0 | V3.3 bundle head 迁入 PG |
| PG-04 | 接受 / P0 | 文件型 V3.3 Forward 纳入 catalog |
| PG-05 | 接受 / P0 | 每表 change capture strategy |
| PG-06 | 接受 / P0 | 修正字段；不再使用通用 cursor |
| PG-07 | 接受 / P0 | 时间列逐列语义 catalog |
| PG-08 | 接受 / P0 | absolute path 转 ArtifactCatalog |
| PG-09 | 接受 / P0 | DuckDB backup 明确 legacy engine |
| PG-10 | 接受 / P0 | PG 独立 schema migration 系统 |
| PG-11 | 接受 / P0 | PG head 唯一权威，文件 pointer 退役为缓存 |
| PG-12 | 接受 / P1 | Focus core 与 outcome settlement 解耦 |
| PG-13 | 接受 / P1 | 应用层 byte order |
| PG-14 | 接受 / P1 | 应用层 canonical JSON |
| PG-15 | 接受候选 / P1 | IEEE binary64，以跨引擎测试最终冻结 |
| PG-16 | 条件接受 | 大表优先 COPY；以真实规模基准决定 |
| PG-17 | 接受 / P1 | 排名 API 顺序是业务结果 |
| PG-18 | 接受 / P1 | 单请求绑定 immutable head |
| PG-19 | 部分接受 | 业务锁合理；是否必须 advisory lock 待 writer 拓扑确认 |
| PG-20 | 接受 / P1 | smoke 专用表或事务回滚，不污染业务 |
| 复杂 CDC | 不需要 | 使用迁移演练 + 最终短维护收口 |
| PG 具体索引/分区 | 待真实盘点 | 不在未知行数时提前定案 |
| 连接池规模 | 待基准 | 根据本机资源和真实并发确定 |

## 13. 修订后的迁移阶段

```text
PGM-00A 代码消费者盘点
PGM-00B 真实 DuckDB 只读盘点
PGM-00C artifact / pointer 盘点
PGM-00D time semantics / mutation strategy 冻结
PGM-01  PostgreSQL 基础设施、权限、备份恢复演练
PGM-02  PG_SCHEMA_V1 与独立 migration ledger
PGM-03  Repository/ArtifactCatalog 访问层收口
PGM-04  冻结副本第一次完整迁移演练
PGM-05  绑定 immutable identity 的 API shadow read
PGM-06  最终维护窗口、mutable 重载、projection/head 重建
PGM-07  PG runtime heads 激活和服务切换
PGM-08  真实交易日观察与 PG backup restore drill
PGM-09  DuckDB 在线退役、只读归档
```

任何阶段开始前读取最新适用文档并记录 contract、evidence、acceptance 和 next stage。

## 14. 切换硬门

除 V2 原门外，新增：

1. runtime heads 均有唯一 PG authority；
2. active bundle 文件不再是业务 head；
3. HTTP 路由无 `duckdb.connect`；
4. HTTP 路由无 `read_parquet`；
5. absolute managed paths 已映射 artifact_id；
6. 所有时间列有语义决定；
7. 每个 mutable 表有最终切换策略；
8. V3.3 file Forward 全部分类；
9. ranked API 顺序 shadow check 通过；
10. 旧 DuckDB backup 标记 legacy；
11. PG backup restore drill 可恢复到可查询状态；
12. Focus Source Authority 已冻结；
13. 服务配置、任务与运维页面全部使用 PG repository；
14. 旧 DuckDB 未经单独授权不删除。

## 15. 待真实 PGM-00 决定

- 表/视图真实总数和容量；
- 每张表实际日期范围、NULL 和 orphan；
- 大表是否需要原生 partition、BRIN 或普通 BTree；
- COPY 分区大小和导入时间；
- 连接池大小、statement timeout 和 P95；
- 哪些旧辅助表已经无消费者，能否只读归档；
- 迁移维护窗口长度。

在这些数据出现前，不对具体索引数量和容量作正式承诺。

## 16. 阶段记录

| 字段 | 内容 |
|---|---|
| stage | `POSTGRES_FULL_MIGRATION_EXTERNAL_AUDIT_DISPOSITION_20260922` |
| stage_contract | `POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_V1` |
| evidence | schema.sql、research schema、007—035、app/today bundle reader、publisher、repository、ops backup/migration、P12 file Forward、DuckDB 锁修复记录与设计 V2 |
| acceptance_result | `DEGRADED_PASS / PGM_00_REQUIRED` |
| code/config/database_changed | 否 / 否 / 否；仅新增审计文档 |
| tdx_access_or_write | 未访问 / 未写入 |
| next_stage | 评审 V2.1 后执行只读 PGM-00 catalogs；catalog 未通过前不创建正式 PG schema、不迁生产数据 |

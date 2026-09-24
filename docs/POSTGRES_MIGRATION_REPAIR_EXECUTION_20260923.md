# PostgreSQL 迁移完整性修复与验收回执（2026-09-23）

| 字段 | 结果 |
|---|---|
| stage | `PGM_REPAIR_AND_REACCEPT_20260923` |
| stage_contract | `PGM_REPAIR_INTEGRITY_V1` + `PG_RUNTIME_HEADS_V1`，执行前核对 V2.1 修改说明第 6 节与全迁移独立审计第 3–4、14 节 |
| evidence | `runtime/postgres_migration/20260923/pg_integrity_repair_receipt.json`、本报告第 2–4 节、维护删除备份及回执 `runtime/manual_delete_backups/trade_date_2026-09-22_20260922T144602Z` |
| acceptance_result | **`FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`** |
| next_stage | 观察每日 PG 同步和 head 原子更新；Focus schema 尚未建立，其 head 合同在 Focus 实施阶段独立定义 |

## 数据缺失成因与恢复

2026-09-22 的手动清理回执显示，删除 publication `m4-49ce0772991047e326a03aa2d25d19b4` 时，删除范围包含 `analysis_snapshot_entries=983`、`analysis_slice_result_bindings=66`。`backup_and_delete_trade_date.py` 从当日 publication 找到 M10 snapshot，再把其历史 slice IDs 当成仅属于该 snapshot；部分 slice/result objects 仍被其他历史 snapshot 引用，所以删除把历史分析关系一起移除了。

修复前冻结源有 72 条 `analysis_slice_result_bindings` 和 1,000 条 `analysis_snapshot_entries`；workbench 分别少 18、818 个主键。`repair_postgres_migration_integrity.py` 在 serializable 事务中从冻结的只读 `legacy` 源按原列值回补，先验证 0 个孤立 slice/snapshot/result-object 引用，再提交。修复后两表的 `legacy EXCEPT workbench` 主键差均为 0。回执记录源快照 SHA-256：`525501b881c094a3f62dcb95f1d375b5d29149ddfb57b032cbdd9ae43916a96d`。

同时修正手动清理脚本：删除前检查 snapshot、slice 和 result object 是否被其他身份引用；发现共享身份就停止。存在 publication/snapshot/slice/object 身份范围时，不再把 `trade_date` 当成 OR 条件扩大删除；PG publication head 与 analysis head 在清理事务内同步处理。

## 表数据比较

- 冻结 DuckDB 以只读连接枚举 103 张源表，共 2,314,834 行；PostgreSQL `legacy` 103 张表的行数逐表一致。
- 对 103 张表逐行全列比较，键按 PostgreSQL C collation 排序；JSON 按 compact sorted canonical form 比较，IEEE NaN 按 NaN 语义比较。结果 `rows_compared=2,314,834, mismatches=0`。
- 对 103 张表逐一比较源 PK 与 workbench PK，`legacy EXCEPT workbench` 均为 0。workbench 中的后续记录属于之后已发布的增量；已变更的时间戳经语义 catalog 解释为相同 UTC instant，relation/sector interval 结束值反映新增 revision。
- 目标 `workbench` 约束已验证：PK 105、UNIQUE 10、FK 62、CHECK 26、NOT NULL 687。

## 文件引用与 runtime authority

- 原 10 条摘要失配记录保留为 `STALE_REFERENCE`，当前文件内容按新 artifact identity 注册；同时登记当前 V3.3 bundle 文件。逐文件重新核对 165 条 `AVAILABLE` 记录，缺失路径、大小差和 SHA-256 差均为 0。
- `PG_RUNTIME_HEADS_V1` 已记录于 `workbench_meta.schema_migrations`。PG `research_bundle_heads=6`、`analysis_snapshot_heads=8`；最新 head 是 2026-09-22 publication `m4-547e88ce22e6d89590876c7ea1d68ca0` 和 bundle digest `8dffed470431779f99a4fa584d8cfb1400ee2f3a7164bbebf399efa7cfa3403d`。
- PostgreSQL repository 以 PG head 选择默认 V3.3 bundle；日同步事务更新 publication、analysis snapshot、research bundle heads，并校验不可变 bundle artifact。`focus_trade_date_heads` 暂无对应数据域：当前还没有 Focus 持久化 schema，保留在 Focus 阶段合同中单独处理。
- 重启后服务状态 `READY / postgresql`；`/api/publications` 最新为 2026-09-22、11 个分析域均 `AVAILABLE`；`/api/v3/research/today` 为 `READY / 2026-09-22 / 273`，Edge 实际页面加载成功。

本阶段未运行每日生成任务，未改动 TDX 来源目录，也未覆盖用户已有未提交文件。数据库写入仅限上述回补行、artifact catalog 版本记录及版本化 PG head 表。

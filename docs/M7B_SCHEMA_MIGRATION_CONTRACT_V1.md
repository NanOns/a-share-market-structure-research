# M7B-01 Schema Migration Contract v1

版本：`workbench-schema-migration-v1.0`；本步骤落地迁移 `007_history_identity`。

## 执行顺序

`WorkbenchRepository.open()` 先建立并登记基础 `workbench-schema-v1.0`，随后由 `MigrationExecutor` 按依赖拓扑发现并执行 SQL 迁移。007 依赖基础 schema；后续迁移只能在其依赖已登记时执行。路径迁移服务仍由 M5 `DatabaseMigration` 负责，两者不共用执行入口。

## 原子性与身份

单个迁移的 DDL、`schema_migrations` 版本登记和 `schema_migration_checks` 哈希记录处于同一事务。SQL 失败时整批回滚，版本不会提前登记。每个已应用迁移保存 UTF-8 SQL SHA-256、依赖版本、前一份版本清单哈希、UTC 时间和 receipt_id。重复打开数据库会复核哈希与依赖；SQL 被修改或校验记录缺失时拒绝继续。

## 007 范围

007 只创建历史身份、分析快照、分片依赖、成员/证券元数据、统一范围、市场参考和涨跌停规则表，不填充历史计算结果。后续步骤负责输入冻结和计算。所有表均位于当前 Workbench DuckDB，TDX 源目录不被写入。

## 备份回执

真实库应用前必须先处于维护窗口，并调用 `scripts/apply_m7b_01.py`。脚本复用 M5 离线 `BackupService`：先 checkpoint、复制、校验并登记 `VERIFIED` 备份，再打开 Repository 应用 007；输出同时包含备份回执和迁移回执。Repository 的自动执行器不伪造物理备份，测试数据库可直接验证事务行为。

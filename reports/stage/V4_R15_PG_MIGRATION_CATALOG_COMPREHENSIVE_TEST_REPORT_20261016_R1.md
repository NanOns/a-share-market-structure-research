---
stage_id: V4_R15_PG_MIGRATION_CATALOG_RECONCILIATION_20261016
code_sha: 18b06d142
test_scope: v4-migration-inventory-contract-and-sql-schema-focused
conclusion: STATIC_RECONCILIATION_PASS_CATALOG_NOT_VERIFIABLE_NO_READER_DSN
approval_status: CODE_AND_STATIC_AUDIT_AUTHORIZED
---

# V4 R15 PG Ledger/Catalog 对账与授权准备阶段报告 R1

本阶段基于冻结起点 `2be2ed143b0f4e8916e7f1ccabf378f48fd92131` 与 R14 提交 `18b06d142`，静态扫描全部 43 个顶层正向迁移，逐文件记录完整名、原始 SHA-256、显式 runner 注册合同、同目录可识别依赖、预期对象、SQL 风险及实际 PG 状态。两个序号 010 分别按完整文件名呈现；runner 是显式文件名映射，不能用一个 010 ledger 项代替两个文件。新增 042 已注册，未执行。

交付：
- `docs/upgrade/V4_PG_MIGRATION_CATALOG_DIFF_R1_20261016.md`：43 条迁移清单；生产对象、字段、约束、索引、触发器、函数、grants 与 migration ledger 逐对象状态均为 `NOT_VERIFIABLE`，没有把 SQL 预期当作现场事实。
- `docs/upgrade/V4_PG_ONE_BATCH_AUTHORIZATION_REQUEST_R1_20261016.md`：独立列出 reader/writer/migration 身份边界、目标、文件 SHA 复核、重复 010、备份/恢复、锁容量、回读与撤权要求；不是写入授权。
- `tests/test_v4_r12_migration_readonly_preflight.py`：静态 migration 数由 42 更新为 43，并验证 042 清点；不访问 PG。

状态：`CODE=PASS`；`PG_STATIC=PASS_INVENTORY_AND_RUNNER_MAPPING`；`PG_ISOLATED=NOT_RUN_NO_AUTHORIZATION`；`PG_LIVE=NOT_VERIFIABLE_NO_LEAST_PRIVILEGE_READER_DSN`。没有连接 PostgreSQL，没有执行 DDL/DML，也没有创建角色、隔离数据库或变更 Head。

定向验收：`python -m pytest --confcutdir=tests -q -p no:cacheprovider tests/test_v4_r12_migration_readonly_preflight.py tests/test_v4_r7_sql_schema_compatibility.py`，`5 passed`。迁移清单由脚本对现有原始 SQL 字节重新计算 43 个 SHA；没有 PG parser，因此 SQL compile 状态仍未验证。

下一阶段 R16：持续实现 TDX/BaoStock 路径的 PIT、增量、恢复和可观测执行合同；实际交易日数据与独立签名 authority 缺失时，真实来源/PIT状态保持 BLOCKED，继续可测的代码工作。

# FOCUS-01 PostgreSQL Focus schema 阶段回执

> 阶段：`FOCUS-01`；合同：`FOCUS_PG_SCHEMA_V1`；日期：2026-09-23。

| 字段 | 结果 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 10、12、19 节；`FOCUS_00_CONTRACT_ACCEPTANCE_20260923.md` |
| prior_phase_0 | `FULL_PASS_TDX_NATIVE`；本阶段未访问 TDX 来源 |
| migration_precondition | `FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED` |
| stage_contract | `FOCUS_PG_SCHEMA_V1`，SQL SHA-256 `c680b361a262101b8ae323855ee7670ce2af5493e460c47e935140cb544f304d` |
| evidence | 安装前 rollback DDL 演练：14 表/68 约束；`--apply` 原子提交；安装后隔离 schema DDL 恢复回滚演练：14 表/68 约束；独立只读校验：14 表/68 约束/24 索引、0 run、0 head；`workbench_meta.schema_migrations` ledger 为 COMPLETE 且 checksum 相同 |
| acceptance_result | `FULL_PASS / FOCUS_01_EMPTY_SCHEMA_ACCEPTED`；结构和空表恢复演练通过，不代表真实 Focus 数据的备份恢复或发布已验收 |
| next_stage | `FOCUS-02`：从 PG 已接受来源 head 读取各族行并物化 tracking union 实际事实；不得凭文件 mtime 或缺行推断退出 |

## 写入范围与约束

仅新增 `workbench.focus_*` 表、索引和一条迁移 ledger；没有插入 Focus 业务行，没有修改既有 publication/research/analysis head。DDL 由 `scripts/apply_focus_pg_schema_v1.py` 事务化执行，默认 dry-run 回滚；`scripts/verify_focus_schema_restore.py` 在隔离 schema 中重放 DDL 并整体回滚；`scripts/verify_focus_pg_schema_v1.py` 独立只读检查实际结构。

本阶段恢复演练是**空 Focus schema 的 DDL 恢复**。首批真实 Focus 数据产生后，还须完成包含数据、head 和 artifact 引用的 PostgreSQL 备份恢复演练，作为正式上线门；此前不得把本结果称作生产数据恢复验收。跨切面迁移审计项仍按原独立记录跟踪。

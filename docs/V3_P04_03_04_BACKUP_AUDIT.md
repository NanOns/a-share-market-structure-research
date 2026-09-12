# V3 P04-03-04：backup 调用链审计

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第四个子任务：**PASS（SCOPED）**。

本轮确认并修复了每日分析调用链中的新增强制全库备份：`app.py` 的每日流程会调用 `scripts/build_m8_m9_preview.py`，该 builder 原先每次运行无条件执行 `create_history_backup()`。现已移除该调用；builder 结果保留 `backup_id: null` 和 `backup_policy: MANUAL_ONLY`。

本轮没有创建备份、恢复备份、移动对象、隔离对象或删除文件；没有写生产数据库；没有访问或修改 `D:/new_tdx`。

## 阶段合同

- 合同版本：`v3-p04-03-backup-chain-audit-v1.0`。
- 每日增量/预览构建不得无条件创建全库备份或恢复演练。
- 备份、恢复演练和迁移前备份只能从显式维护操作进入，并要求维护窗口确认、无活动任务和原子校验。
- 不因 catalog/物理对象不一致自动补备份、重写路径或清理历史副本；不把“有 manifest”冒充“数据库和外部对象均可恢复”。

## 调用链审计

| 调用方 | 结论 |
|---|---|
| `src/workbench_service/app.py::run_today` → `build_m8_m9_preview.py` | 每日仍调用分析 builder，但 builder 已不再创建备份 |
| `scripts/build_m8_m9_preview.py` | 已移除 `BackupService` / `create_history_backup`；结果声明 `MANUAL_ONLY` |
| `src/workbench_service/app.py` `/api/operations/backup/create` | 保留为显式运维操作，经 `MaintenanceService` 维护窗口确认后执行 |
| `/api/operations/backup/restore-drill` | 保留为显式运维操作，不在 daily builder 中调用 |
| `scripts/run_m7b_07_recovery.py` | 独立人工恢复检查脚本，仍显式创建 history backup，不属于每日入口 |
| `scripts/apply_m7b_01.py` / `DatabaseMigration.prepare` | 迁移前显式 offline backup，保留作为迁移安全前置 |
| `MaintenanceService` | 要求确认语、无活动任务和串行锁；不自动调度 |

## 当前备份证据（只读）

| 项目 | 结果 |
|---|---:|
| `backup_catalog` | 43 条 |
| `data/backups` 物理文件 | 82 个，22,746,509,641 B（含对象目录内文件） |
| 物理 `.duckdb` | 14 个；其中 12 个可按 catalog ID 对应，2 个无 catalog |
| 物理 `.manifest.json` | 34 个；其中 30 个可按 catalog ID 对应，4 个无 catalog |
| 物理 `.objects` 目录 | 34 个；其中 30 个可按 catalog ID 对应，4 个无 catalog |
| catalog 指向但物理数据库缺失 | 31 条；包括历史 manifest/object 存在但数据库文件缺失的记录 |
| 新增每日全库备份设计 | 已移除 |
| 新增每日恢复演练设计 | 未发现；独立脚本仍为人工入口 |

### 独立问题

`P04-03-04-A / backup catalog—物理链不完整`：30 个历史 manifest/object 对没有对应数据库文件；另有 2 个物理数据库文件和 4 个 manifest/object 对未登记在 catalog。该问题影响恢复可证明性，不能仅凭 `state=VERIFIED` 放行，也不能本轮直接删除或补登记。下一独立任务需逐 backup ID 核对 database hash、manifest hash、objects hash、来源调用和固定保留项。

## 测试证据

- `pytest -q tests/upgrade_v3/test_p04_03_04_backup_audit.py tests/upgrade_m5/test_backup_restore.py tests/upgrade_m7/test_m7b_07_recovery_cleanup.py tests/upgrade_m7/test_preview_slice_granularity.py`：**11 passed**。
- 已验证每日 builder 不再包含 `BackupService` 或 `create_history_backup`。
- 已验证人工 recovery/migration 路径仍要求显式维护窗口，并保留既有备份校验测试。
- `git diff --check`：待本轮提交前再次执行。

## 下一项

`P04-03-05`：只读核对 `backup_catalog` 与物理 database/manifest/object 的逐 ID 完整性和保留分类；不执行补登记、备份、恢复、移动或删除。

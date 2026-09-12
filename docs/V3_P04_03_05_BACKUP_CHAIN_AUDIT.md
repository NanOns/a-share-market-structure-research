# V3 P04-03-05：backup catalog 与物理链逐 ID 核对

> **当前状态（2026-09-12）**：本文保留清理前的 43 条 catalog 历史快照。旧 M0-M15 不完整链和孤立对象已按授权清理；当前真实复核为 `backup_catalog=12`、完整链 `12/12`、不完整 `0`、孤立 `0`。最终状态见 [V3_P04_03_BACKUP_CLOSURE.md](V3_P04_03_BACKUP_CLOSURE.md)。

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第五个子任务：**PASS（AUDIT）**；备份链本身仍为 **INCOMPLETE**，不因审计通过而放行回收或恢复声明。

本轮只读核对 `backup_catalog`、数据库备份文件、history manifest 和 objects 目录，实际读取并计算了现有文件 hash；未写入数据库，未补登记，未创建备份，未执行恢复、移动、隔离或删除，也未访问或修改 `D:/new_tdx`。

实际 JSON 证据：

`reports/upgrade_v3/P04-03-05_BACKUP_CHAIN_AUDIT.json`

## 阶段合同

- 合同版本：`v3-p04-03-backup-chain-audit-v1.0`。
- 每条 catalog 记录分别核对数据库文件存在性/hash、manifest 身份/hash/database hash、objects 根目录及每个对象文件的存在性/尺寸/hash。
- catalog 中存储的旧绝对路径不被直接改写；审计按文件 basename 在当前受管 backup root 定位，并同时保留 catalog 原路径和实际物理路径证据。
- 物理文件没有 catalog 记录时列为 orphan review；catalog 缺物理链时列为 incomplete；两类都不得自动删除或自动补登记。

## 实际证据

| 项目 | 结果 |
|---|---:|
| `backup_catalog` 记录 | 43 |
| 物理文件 | 82 个，22,746,509,641 B |
| 顶层数据库文件 | 14 个 |
| 顶层 manifest 文件 | 34 个 |
| 顶层 objects 目录 | 34 个 |
| 完整 catalog 链 | 12 条 |
| 不完整 catalog 链 | 31 条，均为数据库文件缺失 |
| catalog manifest | 30/30 存在且 manifest 身份/hash/database hash 通过 |
| catalog objects | 30/30 存在且对象文件 hash/尺寸通过 |
| 孤立数据库文件 | 2 个 |
| 孤立 manifest/object 对 | 4 对 |

### 不完整与孤立对象

- 不完整链：31 条 catalog 记录的 `.duckdb` 文件缺失；不能仅凭 `state=VERIFIED` 认定可恢复。
- 孤立数据库：`backup-20260910T122818Z-845f1aa24063.duckdb`、`backup-20260910T122818Z-cbeef937d124.duckdb`。
- 孤立 manifest/object：
  - `backup-20260909T025718Z-db14b8174be8`
  - `backup-20260909T025826Z-db14b8174be8`
  - `backup-20260909T032447Z-41c47923487a`
  - `backup-20260909T033314Z-6d97fc794e61`

这些 orphan 与不完整链全部保持原样，等待独立的来源、固定保留项和恢复可用性决策。

## 实现与测试

- `src/workbench_ops/backup.py`：新增只读 `audit_catalog_physical_chain()`，不复用会写表的 backup/cleanup 操作。
- `tests/upgrade_v3/test_p04_03_05_backup_chain_audit.py`：覆盖完整链、缺数据库链、孤立物理文件以及 catalog 不写入。
- 定向测试：`pytest -q tests/upgrade_v3/test_p04_03_05_backup_chain_audit.py tests/upgrade_m5/test_backup_restore.py` → **4 passed**。
- 真实审计已完成；所有 database、manifest、object hash 核对结果已写入 JSON 证据。

## 独立遗留项

**P04-03-05-A / backup chain incomplete**：31 条 catalog 缺数据库文件，4 组 manifest/object 未登记，2 个数据库文件未登记。该问题与 P04-03-04 的“取消每日强制备份”不同，不能用删除 orphan 或重新创建全库副本掩盖；必须先确定每类对象的来源、是否固定保留、是否具备可恢复证明。

## 下一项

`P04-03-06`：只读形成上述不完整/孤立对象的分类决策清单，先区分“保留证据、可人工恢复验证、待用户取舍”，不执行删除、补登记或新备份。

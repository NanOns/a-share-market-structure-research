# V3 P04-03-06：backup 链分类决策清单

> **当前状态（2026-09-12）**：本文保留清理前的分类快照。当前重新审计后 `MANUAL_RECOVERY_VALIDATION_CANDIDATE=12`、`PROTECTED_EVIDENCE=0`、`USER_DECISION_REQUIRED=0`；最终状态见 [V3_P04_03_BACKUP_CLOSURE.md](V3_P04_03_BACKUP_CLOSURE.md)。

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第六个子任务：**PASS（AUDIT ONLY）**。

本轮没有改变任何备份、catalog 或物理对象，只基于 P04-03-05 的逐 ID hash/manifest/object 审计结果生成分类决策清单：

`reports/upgrade_v3/P04-03-06_BACKUP_CHAIN_CLASSIFICATION.json`

自动动作：`NONE`；删除权限：`false`。

## 分类结果

| 分类 | 数量 | 处理边界 |
|---|---:|---|
| `PROTECTED_EVIDENCE` | 31 | catalog 链缺数据库文件；保留证据，禁止删除或伪造重建 |
| `MANUAL_RECOVERY_VALIDATION_CANDIDATE` | 12 | database/manifest/object 链完整；仅允许未来人工维护窗口验证，不自动演练 |
| `USER_DECISION_REQUIRED` | 6 | 2 个孤立数据库、4 组孤立 manifest/object；先确认归属和固定保留策略 |

## 阶段合同

- 合同版本：`v3-p04-03-backup-chain-classification-v1.0`。
- 完整链只能进入“可人工恢复验证候选”，不能直接进入可删除列表。
- 缺数据库的 catalog 记录属于受保护历史证据，即使 manifest/object hash 通过，也不能宣称可恢复。
- 无 catalog 的物理文件/目录属于待用户取舍对象；在确认归属、来源和保留项前保持原样。
- 分类器是纯只读决策函数，不调用 backup、restore、quarantine、delete，也不写 `backup_catalog`。

## 实际清单

来源为 [P04-03-05_BACKUP_CHAIN_AUDIT.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-05_BACKUP_CHAIN_AUDIT.json>)：

- 31 条 catalog 记录：`database_status=MISSING`，manifest/object 证据存在但数据库主体缺失，分类为 `PROTECTED_EVIDENCE`。
- 12 条完整 catalog 链：分类为 `MANUAL_RECOVERY_VALIDATION_CANDIDATE`，本轮没有执行恢复演练。
- 2 个孤立数据库：
  - `backup-20260910T122818Z-845f1aa24063.duckdb`
  - `backup-20260910T122818Z-cbeef937d124.duckdb`
- 4 组孤立 manifest/object：
  - `backup-20260909T025718Z-db14b8174be8`
  - `backup-20260909T025826Z-db14b8174be8`
  - `backup-20260909T032447Z-41c47923487a`
  - `backup-20260909T033314Z-6d97fc794e61`

## 测试与边界

- `pytest -q tests/upgrade_v3/test_p04_03_06_backup_chain_classification.py tests/upgrade_v3/test_p04_03_05_backup_chain_audit.py`：**3 passed**。
- 本轮未补登记、未生成新备份、未执行恢复、未移动或删除文件。
- P04-03 尚未整体完成；分类清单不等同于回收授权，也不等同于恢复可用性认证。

## 下一项

备份链已完成只读分类。下一项如继续，应先针对 `USER_DECISION_REQUIRED` 的 6 项做来源/固定保留项核对；在没有明确取舍前，不执行任何物理变更。

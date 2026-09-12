# V3 P04-03-04～08：备份链与旧产物收口

## 总结结论

**P04-03-04、P04-03-05、P04-03-06、P04-03-07、P04-03-08：PASS。**

本轮依据最新 V3 主实施文档 §17.8、§18.7，对当前工作区重新审查备份调用链，并重新执行 catalog/物理链审计、分类和孤立来源核对。此前已按用户授权清理的旧 M0-M15 残留状态同时复核通过。没有新建备份、恢复演练、移动或删除动作；V3 源包、source_files、result objects 和 publication 核心数据未被删除。

## P04-03-04：backup 调用链

合同：`v3-p04-03-backup-chain-audit-v1.0`。

- `scripts/build_m8_m9_preview.py` 不包含 `BackupService` 或 `create_history_backup`。
- daily builder 不再新增每日强制全库备份或恢复演练。
- `scripts/run_m7b_07_recovery.py` 和 `scripts/apply_m7b_01.py` 仍要求显式维护窗口参数。
- 定向调用链测试：**2 passed**。

验收：**PASS**。人工维护/恢复路径保留，自动 daily 路径不复制全库。

## P04-03-05：catalog 与物理 backup 链逐 ID 核对

合同：`v3-p04-03-backup-chain-audit-v1.0`。

当前真实审计结果：

| 项目 | 结果 |
|---|---:|
| `backup_catalog` | 12 |
| 物理文件 | 16，22,737,490,910 B |
| 顶层数据库文件 | 12 |
| 顶层 manifest | 2 |
| 顶层 objects 目录 | 2 |
| 完整链 | 12 |
| 不完整链 | 0 |
| 孤立数据库 | 0 |
| 孤立 manifest/object | 0 |

数据库 hash、存在的 manifest/object hash 和尺寸全部通过。审计为只读，不补登记、不重建、不删除。

验收：**PASS**。历史不完整链与孤立对象已由此前授权的旧 M0-M15 清理关闭，当前 V3 备份 catalog 为 12/12 完整链。

## P04-03-06：备份链分类

当前分类结果：

| 分类 | 数量 |
|---|---:|
| `MANUAL_RECOVERY_VALIDATION_CANDIDATE` | 12 |
| `PROTECTED_EVIDENCE` | 0 |
| `USER_DECISION_REQUIRED` | 0 |

自动动作 `NONE`，删除权限 `false`。12 条完整链保留为人工恢复验证候选，不自动执行恢复演练。

验收：**PASS（只读分类）**。

## P04-03-07：孤立对象来源核对

当前孤立对象数量为 **0**，来源核对产物 `items=[]`，删除权限仍为 `false`。

验收：**PASS**。没有遗留孤立数据库、manifest 或 object 组需要 owner 决策。

## P04-03-08：旧 M0-M15 残留清理复核

此前已授权清理的旧残留复核结果：

- 旧未登记 source bundle 收据已清理，当前 V3 source bundle 物理回执/catalog 为 5/5。
- 旧不完整 backup chain 与孤立对象已清理，当前为完整链 12/12、孤立 0。
- V3 `source_files=32`、V3 source packages=4；未把 V3 核心元数据当作旧产物删除。
- `cleanup_jobs=1`，没有新增清理计划。

验收：**PASS**。TDX 输入目录未访问或修改；V3 唯一源包、最近 2 个 bundle、metadata、result objects 和 publication 绑定仍受保护。

## 全局验证

- `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：**175 passed**。
- `python -m compileall -q src scripts`：通过。
- `git diff --check`：通过。
- 实际报告：
  - [P04-03-05_BACKUP_CHAIN_AUDIT.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-05_BACKUP_CHAIN_AUDIT.json>)
  - [P04-03-06_BACKUP_CHAIN_CLASSIFICATION.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-06_BACKUP_CHAIN_CLASSIFICATION.json>)
  - [P04-03-07_BACKUP_ORPHAN_PROVENANCE.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-07_BACKUP_ORPHAN_PROVENANCE.json>)

## P04-03 阶段结论

P04-03 的源包目录、真实 resolver 恢复、缓存预算预览、backup 调用链和当前物理链均已满足文档验收条件，阶段状态为 **FULL_PASS**。

该结论不代表 P05 之前的生产 daily 运维激活，也不授权未来自动删除受保护源包或自动恢复备份。下一阶段按主文档进入 **P05**。

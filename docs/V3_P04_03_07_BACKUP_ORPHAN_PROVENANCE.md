# V3 P04-03-07：孤立备份对象来源与固定保留核对

> **当前状态（2026-09-12）**：本文保留清理前 6 项孤立对象的历史核对快照。旧对象已按授权清理，当前 orphan provenance `items=[]`；最终状态见 [V3_P04_03_BACKUP_CLOSURE.md](V3_P04_03_BACKUP_CLOSURE.md)。

## 结论

依据最新 V3 主实施文档 `§17.8`、`§18.7 P04-03`，完成第七个子任务：**PASS（AUDIT ONLY）**。

本轮只读消费 P04-03-05 的物理链审计，针对 P04-03-06 标出的 6 项 `USER_DECISION_REQUIRED` 做文件 hash、manifest 身份、catalog 和 `storage_objects` 交叉核对。没有补登记、删除、移动、恢复或新建备份，也没有访问或修改 `D:/new_tdx`。

审计产物：

`reports/upgrade_v3/P04-03-07_BACKUP_ORPHAN_PROVENANCE.json`

## 阶段合同

- 合同版本：`v3-p04-03-backup-orphan-provenance-v1.0`。
- 输入只允许是 P04-03-05 的链审计及当前只读 catalog/storage 证据；不以文件名或 `state=VERIFIED` 单独推断归属。
- 对数据库孤立文件核对实际 SHA-256、文件名短 hash 自洽性和 `backup_catalog` 内容 hash；对 manifest/object 孤立组核对 manifest 自身 hash、backup identity、数据库 hash、对象文件尺寸/hash及 `storage_objects` 登记状态。
- V3 §17.8 的固定保留项必须先确认归属/保留策略；本轮不擅自设定天数，不把待决项变成清理候选。
- 固定边界：`automatic_action=NONE`、`deletion_allowed=false`，所有 6 项先 `RETAIN_UNTIL_OWNER_CONFIRMED`。

## 实际证据

| 对象 | 数量 | 交叉结果 | 建议 |
|---|---:|---|---|
| 孤立数据库文件 | 2 | 两个实际文件 hash 均与文件名最后 12 位自洽；均没有 `backup_catalog` 同 hash 归属 | `UNOWNED_PHYSICAL_DATABASE`，保留到 owner/固定保留策略确认 |
| 孤立 manifest/object 组 | 4 | 4/4 manifest identity/hash PASS；4/4 对象 hash/尺寸 PASS；均指向同一个 `storage_objects` 对象，状态 `ACTIVE`、`referenced=true` | `UNREGISTERED_MANIFEST_WITH_REGISTERED_OBJECT_EVIDENCE`，保留，禁止把它们自动补登记或删除 |

### 2 个孤立数据库

- `backup-20260910T122818Z-845f1aa24063.duckdb`：3,158,016 bytes；实际 SHA-256 `845f1aa240636c92f0e61f53b8a6e12265c6783f5676197984abf91cdae70a57`；文件名短 hash 自洽；catalog 同 hash 匹配 0。
- `backup-20260910T122818Z-cbeef937d124.duckdb`：5,517,312 bytes；实际 SHA-256 `cbeef937d12475039c3734b20d6fa75c0aaea4b83910e37b99c31a415f9c0c9b`；文件名短 hash 自洽；catalog 同 hash 匹配 0。

“文件名短 hash 自洽”只证明文件名与当前内容一致，不证明它属于当前 catalog、可恢复或应当保留多久。

### 4 个孤立 manifest/object 组

- `backup-20260909T025718Z-db14b8174be8`
- `backup-20260909T025826Z-db14b8174be8`
- `backup-20260909T032447Z-41c47923487a`
- `backup-20260909T033314Z-6d97fc794e61`

四组的 manifest 都能通过自身声明的 identity hash；对象均为 `analysis-obj-a9e40beba3799626c3a5b522f3644c480b16511ddd6b3ec76077eab5f1b1f6ce`，对象 hash/尺寸均通过，并能与当前 `storage_objects` 的 ACTIVE、referenced 对象交叉匹配。manifest 的数据库 hash 没有对应 catalog 记录，因此只能说明“对象证据仍存在”，不能升级为完整可恢复备份链。

## 验收

- 6/6 `USER_DECISION_REQUIRED` 项均被重新核对并进入产物；未遗漏数据库、manifest 或 object 组。
- catalog 只读读取 43 条；`storage_objects` 只读读取 52 条；本方法没有 INSERT/UPDATE/DELETE。
- 2 个数据库完成实际 hash；4 个 manifest identity/hash 和 4 个对象 hash/尺寸完成核对。
- 所有项目的固定保留推荐为 `RETAIN_UNTIL_OWNER_CONFIRMED`；`fixed_retention_days=null` 是刻意保留的用户决策边界，不是失败或默认清理期限。
- 定向测试：`pytest -q tests/upgrade_v3/test_p04_03_07_backup_orphan_provenance.py tests/upgrade_v3/test_p04_03_06_backup_chain_classification.py tests/upgrade_v3/test_p04_03_05_backup_chain_audit.py`：**5 passed**。
- 真实产物为原子写出；本轮没有写生产数据库、备份目录或 TDX。

## 独立遗留项

- `P04-03-05-A` 仍开放：31 条 catalog 链缺数据库主体；这与本轮 6 个孤立对象不同，不能用本轮结果合并结案。
- P04-03-03-A 的 3 份未登记 source bundle 回执、P04-03-01-B 的 `source_files=0` 仍需独立任务处理。
- 6 个孤立对象的“是否固定保留、固定多久、是否允许人工归档/删除”仍需要明确 owner 决策；在此之前本报告不授予任何物理变更权限。

## 下一项

P04-03-07 已完成来源核对。下一步只能在最新 V3 文档和独立问题项的顺序下，先处理尚未关闭的 `P04-03-05-A`/P04-03-03-A 等审计项；在用户未给出 6 个孤立对象的保留取舍前，不执行删除、补登记、移动或恢复。

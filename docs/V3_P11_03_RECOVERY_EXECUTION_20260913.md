# V3 P11-03 已授权回收执行回执（2026-09-13）

## 1. 执行结论

本阶段收到用户对明确范围的直接授权后，按固定路径清单执行回收：

- 删除 2 个可由原始 source package 重建的解包目录：20260907、20260908
- 删除 `data/backups` 下预审计的全部 16 个直接备份对象：12 个 DuckDB、2 个 manifest、2 个 `.objects` 目录
- 删除 1 个明确命名的 runtime restore-drill 备份文件
- 共删除 19 个精确对象，按执行前对象字节统计为 `25,295,015,262 B`
- `data/backups` 空目录保留，便于后续按新保留策略重新建立备份链

后置只读复核结果：`FULL_PASS`。

机器回执：[P11-03-RECOVERY-EXECUTION-20260913.json](../reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json)

## 2. 删除范围

### 2.1 解包目录

| 精确目标 | 执行前文件数 | 执行前字节 | 结果 |
|---|---:|---:|---|
| `data/input_staging/extracted/20260907` | 12,399 | 948,565,152 | 已删除 |
| `data/input_staging/extracted/20260908` | 12,399 | 948,868,320 | 已删除 |

20260909、20260910 未删除，仍保留为最近使用的解包证据。

### 2.2 物理备份

以下 `data/backups` 直接对象全部删除：

- `backup-20260910T121350Z-796244f7da16.duckdb`
- `backup-20260910T121350Z-796244f7da16.manifest.json`
- `backup-20260910T121350Z-796244f7da16.objects`
- `backup-20260910T123432Z-8a899d477b09.duckdb`
- `backup-20260910T123432Z-8a899d477b09.manifest.json`
- `backup-20260910T123432Z-8a899d477b09.objects`
- `backup-20260911T193112Z-7a931b0724e8.duckdb`
- `backup-20260911T233048Z-45d7b3c1bed2.duckdb`
- `backup-20260912T000023Z-65432baaf1ee.duckdb`
- `backup-20260912T002526Z-822de3d9b647.duckdb`
- `backup-20260912T004954Z-21dfb9a772b2.duckdb`
- `backup-20260912T010834Z-02efee63a95c.duckdb`
- `backup-20260912T012602Z-9a4b46c91b4d.duckdb`
- `backup-20260912T020156Z-638bdba5a42e.duckdb`
- `backup-20260912T023322Z-46f5b9f95f44.duckdb`
- `backup-20260912T030620Z-5f80d367e3dc.duckdb`

另删除：`runtime/restore_drills/20260908T103624951391/backup-20260908T103503Z-c8ff439c73ec.duckdb`。

## 3. 保留范围

以下对象未动：

- 生产库 `data/database/market_research.duckdb` 及其表
- 4 个原始 `hsjday.zip` source package
- 4 个 metadata snapshot
- `data/.phase1_cache`
- `data/input_staging/extracted/20260909`、`20260910`
- 六张迁移域旧表、四张关系表、七张辅助结果表
- runtime 中除上述 1 个 restore-drill 备份之外的其余文件

## 4. 安全与验收

| 项目 | 结果 |
|---|---|
| 所有授权目标已不存在 | `FULL_PASS` |
| `data/backups` 已清空 | `FULL_PASS` |
| 原始 source package 仍存在 | `FULL_PASS` |
| 生产库 size/mtime 不变 | `FULL_PASS`；`2,060,988,416 B`、mtime_ns `1789229388750638600` |
| 删除数据库表 | 未执行 |
| VACUUM | 未执行 |
| 新备份 | 未创建 |
| TDX | 未访问、未修改 |

执行脚本首轮在回执收尾阶段因空列表布尔判断产生错误码，但删除动作已完成；随后独立只读后置复核已修正该判断并生成上述 `FULL_PASS` 回执，未发生二次删除。

## 下一阶段

进入 P11-04 前置等待。备份链已清空，后续如需恢复保护，必须先制定新的备份保留策略并重新建立经验证的备份链；P11-01 存储止增长门和 P11-02 两项独立审计仍需单独处理，不能因本次回收自动关闭。

# P11-02 辅助旧写入边界审计（2026-09-13）

## 阶段结论

`P11-02-AUD-AUXILIARY-WRITES-01` 已按“有界、可解释地保留旧 writer”路径关闭，未迁移或删除任何旧表：

- `sector_membership_changes`：仅由当前增量 builder 的 `membership_changes` writer 通过一个调用点写入；按 `slice_id` 做存在检查和 immutable conflict guard，写入为 append-only。
- `stock_sector_associations_daily`：仅由手工 `build_m11_association_preview.py` 通过一个调用点写入；构建按 snapshot 去重并在事务中提交，当前 `run_today` 不调用该手工 builder。
- 两个表没有被该 writer 路径执行 `UPDATE`、`DELETE`、`DROP` 或 `TRUNCATE`。
- 旧表按用户决定继续保留，表清理不属于本审计范围。

机器回执：[P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json](../reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json)

## 证据与边界

| 域 | 表 | writer 边界 | 读取/用途 | 决定 |
|---|---|---|---|---|
| membership changes | `sector_membership_changes` | `scripts/build_m8_m9_preview.py` 的当前增量链，单一调用点 | 作为独立成员变化历史保存；不纳入六域停旧写证明 | 有界保留 |
| association | `stock_sector_associations_daily` | `scripts/build_m11_association_preview.py` 手工预览，单一调用点 | 旧 API28、linkage/insight 兼容读取仍使用 | 有界保留 |

只读当前表快照：`sector_membership_changes` 为 33,888 行，`stock_sector_associations_daily` 为 671,568 行。未执行 writer，未打开生产写连接。

## 与 V3 的关系

本审计关闭的是“两个辅助旧写点是否存在无边界增长/隐式删除”的问题，不代表辅助域已完成 V3 结果对象迁移，也不代表旧表可以删除。旧表清理仍遵循用户已确认的门：V3 全部功能开发完成、旧页面功能全部迁移、逐表引用与兼容回归完成后，再重新判断具体表。

## 验收

| 项目 | 结果 |
|---|---|
| 源码语法 | `FULL_PASS` |
| 两个 writer 调用边界 | `FULL_PASS`，各 1 个明确调用点 |
| writer 删除/更新边界 | `FULL_PASS`，未发现针对目标表的更新/删除/清空 |
| 当前 daily 入口 | `FULL_PASS`，仅接增量 builder，不接手工 M11 association builder |
| 数据库 | read-only；未修改 |
| TDX | 未访问、未修改 |
| 旧表清理 | 不在本阶段范围，继续保留 |

## 下一阶段

该独立辅助 writer 审计项可标记为 `RESOLVED_WITH_BOUNDED_LEGACY_WRITER_BOUNDARY`。下一阶段仍受 `P11-02-AUD-STORAGE-01`、P11-01 存储止增长门、P11-04 主入口交接门以及旧页面迁移门约束。

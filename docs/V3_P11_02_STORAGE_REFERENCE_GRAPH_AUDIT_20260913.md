# P11-02 存储引用图独立审计（2026-09-13）

## 阶段结论

`P11-02-AUD-STORAGE-01` 已完成逐对象只读对账，结论为
`RESOLVED_AS_CURRENT_OR_HISTORICAL_REFERENCE_NO_AUTO_ACTION`。本审计没有清除
`storage_objects.referenced`、删除对象、删除物理文件、执行 cleanup job 或修改生产库。

此前 P11-02 只将 `referenced=true` 与当前 publication head 比较，得到 17 个 stale
flag 和 1 个缺失物理路径。本次把以下关系一起纳入：

- 当前 publication → SUCCESS analysis snapshot → snapshot entry → analysis slice；
- 全部 SUCCESS snapshot 的历史 slice 关系；
- `QUEUED`/`RUNNING`/`INTERRUPTED` job 的 pending object 与 completed slice 关系；
- 有效 ACTIVE lease 的 object 关系；
- `online_payloads.storage_object_id` 直接关系；
- `storage_objects` payload 中的相对物理路径与 deleted tombstone 证据。

机器回执：[P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json](../reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json)

## 对账结果

| 项目 | 结果 |
|---|---:|
| `storage_objects` catalog rows | 52 |
| 当前 publication 引用对象 | 34 |
| 历史 analysis slice 引用对象 | 17 |
| 此前 17 个 stale flag 的历史 provenance | 17/17 |
| 活跃 job/lease 引用 | 0 |
| online payload 引用 | 0 |
| 未能解释的 `referenced=true` | 0 |
| 异常缺失物理文件 | 0 |

17 个 stale flag 全部是 DuckDB 内的 `*_RESULT_ROWS` 对象，仍有历史
`analysis_slices` 身份行指向；它们不是可以据此自动删除的“无引用对象”。本次只证明
来源与保留边界，不改变其保护标志。

唯一缺失物理路径是
`analysis-obj-a9e40beba3799626c3a5b522f3644c480b16511ddd6b3ec76077eab5f1b1f6ce`。
其 payload 明确为 `DELETED`、`physical_artifact_removed=true`，并列出两条
`legacy_slice_tombstones`；因此分类为 `TOMBSTONE_EXPECTED_ABSENT`，不执行恢复。

## 安全与验收

- DuckDB 使用 `read_only=True`；执行前后 size/mtime 不变。
- 未访问或修改 `D:/new_tdx`。
- 未修改旧表；旧表继续遵守用户确认的“V3 完成且旧页面迁移完成前保留”门槛。
- 未执行清理、VACUUM、备份、恢复或物理删除。
- 机器验收为 `FULL_PASS`，但这不等同于 P11-01 存储止增长门已完成；P11-04 仍需等待
  P11-01 存储门及主入口交接条件。

## 下一阶段

继续处理 P11-01 的存储止增长/发布保护门，满足后再进入 P11-04 主入口 handoff；旧表清理仍需等
V3 全部开发、旧页面迁移和逐表兼容回归完成后重新逐表裁决。

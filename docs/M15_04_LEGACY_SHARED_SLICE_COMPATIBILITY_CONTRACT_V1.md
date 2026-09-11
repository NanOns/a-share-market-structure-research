# M15-04 旧共享多日 slice 兼容合同 v1

合同 ID：`M15_LEGACY_SHARED_SLICE_COMPATIBILITY_V1_0`

## 语义

- `analysis_slices.trade_date` 是 slice 的物理锚点/生成日期，不是该 slice 能服务的唯一研究日期。
- `analysis_snapshot_entries.trade_date` 是快照域输出的权威研究日期；发布读取必须以 `(slice_id, entry.trade_date)` 绑定域表行。
- `covered_dates` 的解析顺序为：`basis_json.covered_dates`；其次 `basis_json.preview_window` 的闭区间；旧快照若两者均无，则使用同一 `(snapshot_id, domain, slice_id)` 下的 entry 日期集合。旧数据不回写。
- 只有当对应域表存在完全相同的 `(slice_id, trade_date)` 行时，entry 才可被读取；anchor-date 差异本身不构成数据损坏。

## 兼容约束

新建 snapshot 必须显式写入 `covered_dates` 或闭区间 `preview_window`。旧共享多日 slice 通过上述只读派生规则兼容；不得把 entry 日期改写为 anchor 日期，不得为修复审计而改写旧发布、观察或 TDX 输入。

## 验收

本合同的验收证据为生产库只读查询：269 条历史 anchor-date 差异全部存在对应域表 `(slice_id, entry.trade_date)` 行；缺失 0；当前 M13、M11 绑定快照的语义锚点差异 0，旧 M8–M9 绑定的 13 条差异均为可读的历史共享 slice 行。M15-03 浏览器冷/热证据由 `m15_03_browser_retest_receipt_20260911.json` 补齐 T22。

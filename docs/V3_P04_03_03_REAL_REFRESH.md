# V3 P04-03-03：解包保留与缓存预算真实复验

## 结论

**PASS（只读预览）**。

本任务按 V3 §17.8/§18.7 在当前工作区重新生成 input storage preview。预览只读 source bundle、publication、active job、extracted、metadata 和 `.phase1_cache`；没有执行解包回收、缓存回收、隔离、删除或 cleanup job 写入。

## 阶段合同

- 合同：`v3-p04-03-input-storage-preview-v1.0`。
- 源包是唯一原始证据，全部受保护；只在源包可恢复、无活动任务引用且满足最近 2 个已使用 bundle 规则时，将旧解包列为预览候选。
- 最近 2 个按交易日和 bundle 身份选择，不按 mtime 删除。
- `.phase1_cache` 预算为 2 GiB，90% 仅告警；超过预算但无安全访问顺序时 fail-closed，不强删受保护对象。
- 预览输出原子写出到项目受管目录；不写 `cleanup_jobs`。

## 实际证据

| 项目 | 结果 |
|---|---:|
| source bundle catalog / 物理回执 | 5 / 5 |
| 未登记物理回执 / catalog 缺失回执 | 0 / 0 |
| `source_files` | 32 |
| 最近 2 个保留日期 | 2026-09-09、2026-09-10 |
| 活动任务引用 bundle | 0 |
| 2026-09-07 解包 | `PREVIEW_RECLAIMABLE_REBUILDABLE`，12,399 文件 / 948,565,152 B |
| 2026-09-08 解包 | `PREVIEW_RECLAIMABLE_REBUILDABLE`，12,399 文件 / 948,868,320 B |
| 2026-09-09 解包 | `PROTECTED_RECENT_USED_BUNDLE`，12,402 文件 / 949,178,304 B |
| 2026-09-10 解包 | `PROTECTED_RECENT_USED_BUNDLE`，12,404 文件 / 949,487,072 B |
| `.phase1_cache` | 18,534 文件 / 954,775,668 B |
| 预算使用率 | 44.46% / 2 GiB |
| 预算决策 | `WITHIN_BUDGET`，无回收候选 |
| `cleanup_jobs` | 1 → 1，无新增计划 |
| 删除执行 | `false` |

metadata 内容 hash 复用分组仍由预览输出；未因新日期无条件复制或删除 metadata。唯一 source package、最近 bundle、活动任务引用均保持保护。

## 测试与产物

- `pytest -q tests/upgrade_v3/test_p04_03_03_storage_preview.py tests/upgrade_m5/test_storage_governance.py`：**7 passed**。
- 实际预览产物：[P04-03-03_STORAGE_PREVIEW.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-03_STORAGE_PREVIEW.json>)。
- `git diff --check`：通过。

## 验收边界

本任务关闭 P04-03-03 的预览与预算判断，不授予实际删除权限；2026-09-07/08 解包是否回收仍需另行明确执行边界。P04-03 备份链审计收口继续独立跟踪，不提前进入 P05。

## 下一任务

进入 `P04-03-04`：复核 backup 调用链及现有备份证据，确认不新增每日强制全库备份/恢复演练；仍不执行备份、恢复、移动或删除。

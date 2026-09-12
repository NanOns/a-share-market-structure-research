# V3 P04-03-03：解包保留与 `.phase1_cache` 预算预览

> **状态更新（2026-09-12）**：本文保留预览执行时的历史发现。之后 `P04-03-08` 已处理旧的未登记 source bundle 收据，`P04-03-01-B` 已完成 source_files 目录回填；最新只读复核显示物理回执与 catalog 均为 5/5、`source_files=32`。本报告中的 3 份未登记回执和 `source_files` 空表仅是回填前快照，当前不再作为开放问题；解包回收仍未执行。

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第三个子任务：**PASS（SCOPED）**。

本轮启用了“最近 2 个已使用 bundle 解包保留”和 `.phase1_cache` 2 GiB 预算的**只读预览合同**，生成实际工作区预览文件：

`reports/upgrade_v3/P04-03-03_STORAGE_PREVIEW.json`

没有删除、移动、隔离或覆盖任何源包、解包目录、metadata、缓存或数据库对象；没有调用旧 `preview_cleanup()`，没有新增 `cleanup_jobs`，没有访问或修改 `D:/new_tdx`。

## 阶段合同

- 合同版本：`v3-p04-03-input-storage-preview-v1.0`。
- 源包是唯一原始证据，始终受保护；解包目录只能在源包保留、无活动任务引用且 resolver 可重建时列为“预览可回收”，本轮不执行回收。
- 最近 2 个**已使用** bundle 按交易日和 bundle 身份选择，不按目录 mtime 选择；活动任务引用优先保护。
- `.phase1_cache` 使用 2 GiB 上限；90% 只告警，超过上限也必须先建立安全引用/访问顺序，不能按 mtime 强删；没有安全候选时 fail-closed。
- metadata 只按内容 hash 统计可复用组，不因新日期无条件复制或生成删除动作。
- 预览只读数据库和文件盘，JSON 产物通过临时文件、flush/fsync、原子 replace 写出，目标不在 TDX 根。

## 实现

- `src/workbench_ops/storage.py`
  - 新增 `preview_v3_input_storage()`，读取 source bundle 回执、数据库使用记录、活动 job、源包、解包、metadata 和 `.phase1_cache`。
  - 新增 `write_v3_input_storage_preview()`，原子写出审计 JSON。
  - 与旧分析对象 cleanup preview 分离，避免本任务误写 `cleanup_jobs`。
- `tests/upgrade_v3/test_p04_03_03_storage_preview.py`
  - 验证最近 2 个 bundle、活动任务保护、旧解包仅预览、缓存预算内状态及不写 cleanup 计划。
  - 验证超预算且缺乏安全访问顺序时 fail-closed，不删除缓存。

## 实际工作区证据

| 项目 | 结果 |
|---|---:|
| 物理 source bundle 回执 | 8 份 |
| 数据库 `source_bundles` catalog | 5 条 |
| 未登记物理回执 | 3 份：`0ef1ce20...`、`11a9329a...`、`d4f1b6de...` |
| 已使用 bundle | 5 个 |
| 保留最近 2 个 | `ba3edaf...`（2026-09-09）、`fc269487...`（2026-09-10） |
| 2026-09-07/08 解包 | `PREVIEW_RECLAIMABLE_REBUILDABLE`，仅预览未删除 |
| 唯一源包 | 4 个，全部保护 |
| `.phase1_cache` | 18,534 文件 / 954,775,668 B |
| `.phase1_cache` 预算 | 2,147,483,648 B；使用率 44.46%；`WITHIN_BUDGET` |
| 新增 cleanup job | 0；已有记录仍为 1 |
| 活动任务 bundle | 0 个 |

物理回执多于数据库 catalog 是独立审计项 `P04-03-03-A`，不能把未登记回执自动当作可回收对象；本轮全部保持保护/只读状态。

## 验收

| 条目 | 结果 |
|---|---|
| 最近 2 个已使用 bundle 保留 | PASS；按交易日选择 2026-09-09、2026-09-10 |
| 源包唯一来源保护 | PASS；4 个物理 ZIP 全部 protected |
| 活动任务文件不回收 | PASS；活动引用进入保护集合；实际无活动 job |
| 旧解包先预览、不先删除 | PASS；2026-09-07/08 只列 `PREVIEW_RECLAIMABLE_REBUILDABLE` |
| phase1 cache 预算 | PASS；44.46%，无回收候选 |
| 超预算保护 | PASS；无安全访问元数据时 `BLOCKED_NO_SAFE_CANDIDATE` |
| metadata 内容 hash 复用证据 | PASS；输出重复内容 hash 组，未复制/删除 |
| cleanup/数据库写入隔离 | PASS；测试和实际前后核对无新 cleanup job |

## 测试证据

- `pytest -q tests/upgrade_v3/test_p04_03_03_storage_preview.py tests/upgrade_m5/test_storage_governance.py`：**5 passed**。
- P04-03-02 resolver 测试与 V3/M7 回归仍保持通过；本轮未修改 resolver 或生产输入。
- `git diff --check`：待本轮提交前再次执行。

## 独立遗留项

1. **P04-03-03-A / 物理回执未登记**：3 份历史 `source_bundle.json` 不在数据库 `source_bundles` catalog 中；需独立只读对照和引用决策，不能在本阶段直接回填或删除。
2. 解包实际回收仍未执行；2026-09-07/08 要等所有历史 manifest/reader 的按需恢复调用链和活动引用核验后，另行授权回收。
3. backup catalog/物理对象对照和备份调用链尚未执行。

## 下一项

`P04-03-04`：只审查 backup 调用链和现有备份证据，确认没有新增每日强制全库备份/恢复演练设计；不执行备份、恢复、移动或删除。

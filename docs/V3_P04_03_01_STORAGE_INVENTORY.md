# V3 P04-03-01：input_staging 引用与可再生性盘点

> **状态更新（2026-09-12）**：本文保留首次只读盘点时的历史基线。随后执行的 `P04-03-08` 清理和 `P04-03-01-B` 回填已使物理源包回执与 `source_bundles` 达到 5/5 对齐，并将 `source_files` 从 0 补齐为 32。当前结果以 [V3_P04_03_01_B_SOURCE_CATALOG_RECONCILIATION.md](V3_P04_03_01_B_SOURCE_CATALOG_RECONCILIATION.md) 及其 JSON 产物为准；本文中的 `source_files=0`、未登记物理回执和对应独立遗留项属于回填前历史快照，不再表示当前状态。

## 结论

依据最新 V3 主实施文档 §17.8、§18.7 P04-03，完成第一个子任务：**PASS（AUDIT ONLY）**。

本轮只读盘点了 `input_staging` 的源包、解包目录、metadata 快照、normalized、`.phase1_cache`、backup 和现有 catalog；没有删除、移动、覆盖文件，也没有写入生产数据库。P04-03 整体仍未完成。

## 阶段合同

- 合同版本：`v3-p04-03-storage-inventory-v1.0`。
- 源包、解包、metadata 以 source bundle 的内容身份和目录 manifest 建立引用图。
- 只把“源包存在且解包/metadata 与 manifest 的数量、字节和 metadata 文件尺寸一致”记为结构性可再生证据；本轮不把它扩大为完整 hash 复验或 resolver 恢复验收。
- 任何回收候选必须继续满足：源包保留、无活动任务引用、历史 manifest 可由 resolver 通过“源包+成员路径”恢复；本轮不生成可删除清单。
- TDX 输入目录不在盘点范围内，且没有访问或修改 `D:/new_tdx`。

## 当前引用图证据

### 目录容量与文件数

| 对象 | 文件数 | 字节数 | 保护结论 |
|---|---:|---:|---|
| `data/input_staging/packages` | 4 | 2,195,026,583 | 源包原始证据，保护 |
| `data/input_staging/extracted` | 49,604 | 3,796,098,848 | 可由源包重建，但 resolver 恢复验收未完成，保护 |
| `data/input_staging/metadata` | 32 | 101,955,241 | metadata 快照证据，保护 |
| `data/normalized` | 1 | 876,179,188 | 现有单文件规范化历史，按 §17.8 保留 |
| `data/.phase1_cache` | 18,534 | 954,775,668 | 约 0.89 GiB；低于默认 2 GiB 上限，不能因此清空 |
| `data/backups` | 82 | 22,746,509,641 | 备份/manifest/object 副本，尚未完成逐项引用审计 |
| `runtime` | 74 | 1,409,431,410 | 不纳入本轮可回收结论 |

### Bundle 与物理源包

当前数据库只读查询得到：`source_bundles=5`、`source_packages=4`、`source_files=0`、`metadata_snapshots=2`。

五个 bundle 的解包和 metadata 结构结果如下：

| 交易日 | Bundle 记录 | 解包实际/声明 | metadata 实际/声明 | ZIP 引用 |
|---|---|---|---|---|
| 2026-09-07 | 2 | 12,399 文件 / 948,565,152 B，一致 | 8 文件，记录尺寸一致 | 1 个物理 ZIP；其中旧 bundle 缺 `package.staged_path` |
| 2026-09-08 | 1 | 12,399 文件 / 948,868,320 B，一致 | 8 文件，记录尺寸一致 | 1 个物理 ZIP |
| 2026-09-09 | 1 | 12,402 文件 / 949,178,304 B，一致 | 8 文件，记录尺寸一致 | 1 个物理 ZIP |
| 2026-09-10 | 1 | 12,404 文件 / 949,487,072 B，一致 | 8 文件，记录尺寸一致 | 1 个物理 ZIP |

所有 bundle 的 `read_only=true`。2026-09-07 的旧 bundle `db773f4f...` 没有显式 `staged_path`，但其日期约定路径和包尺寸仍可定位到同日 ZIP；这只能记为“可定位”，不能替代补齐 manifest 引用字段的审计项。

### 数据库与运维引用

- `publications` 当前有 2026-09-07 至 2026-09-10 的成功发布记录；one-click 发布的 `source_path` 指向对应 `data/source_bundles/<bundle_id>`，早期 daily 发布使用 release 路径，需保持兼容。
- `storage_objects=52`，其中结果行对象使用数据库内存储，唯一外部分析对象路径存在且仍被标记为 `referenced=true`；没有可直接认定为未引用的 registered object。
- `cleanup_jobs=1`，现有计划状态为 `PLANNED` 且 `eligible_object_ids=[]`；本轮没有调用会写入 `cleanup_jobs` 的新预览操作。
- `backup_catalog=43`，物理 backup 目录有 34 个 manifest 和 34 个 object 目录；catalog 与物理对象的一一对应、重复副本分类和最新有效备份选择仍属于后续独立子任务。
- `runtime/operations_config.json` 当前有效配置为 `retention_successful_days=3`、managed roots 为 `data/reports/runtime`、backup root 为 `data/backups`；本轮没有调整配置。

## 独立遗留项

1. **P04-03-01-A / bundle manifest 路径字段**：旧 2026-09-07 bundle 缺显式 `package.staged_path`，当前 resolver 依赖日期约定路径。验收要求是补充版本化兼容读取/登记证据，不是直接改历史身份或重写 bundle。
2. **P04-03-01-B / source_files catalog 空表**：`source_files=0`，现有 source package payload 虽含 SHA/URL/路径，但数据库没有逐文件登记。需要单独定义回填合同和只读对照，不能在本审计任务中直接写生产库。
3. **P04-03-01-C / backup catalog 对照**：43 条 catalog、34 个 manifest/object 对和 82 个物理文件的重复/引用关系未完成核验，暂不产生任何回收候选。

## 未执行事项

- 未验证 resolver 从保留 ZIP 恢复缺失解包文件；这是下一独立子任务。
- 未启用“最近 2 个 bundle”保留策略或 `.phase1_cache` 淘汰策略。
- 未审查/改造 backup 调用链，未执行备份、恢复演练、移动、隔离、删除。

## 下一项

`P04-03-02`：只读验证输入 resolver 能否从保留源包恢复所需文件；先用临时目录/合成故障验证，不触碰现有源包、解包目录或生产数据库。

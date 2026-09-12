# V3 P04-03-01-B：source_files 历史目录回填

## 结论

**FULL_PASS（受限于当前 V3 源包范围）**。

本任务关闭 P04-03-01 的 `source_files=0` 元数据缺口。物理源包、解包目录、metadata、TDX 输入和备份对象均未修改；仅在项目数据库内原子补登记已存在的 V3 source bundle 文件清单。

## 阶段合同

- 合同：`v3-p04-03-source-file-catalog-reconcile-v1.0`。
- 输入：`data/source_bundles/*/source_bundle.json` 中身份已封存且 `read_only=true` 的 V3 bundle。
- 写入边界：只允许写入 `source_files`；bundle/package/metadata catalog 必须已存在且身份可对照。
- 失败边界：任一 bundle 身份、文件描述或既有行发生冲突，整个事务回滚，不留下部分登记。
- 幂等边界：重复执行不新增重复行；同一物理 package 被多个 bundle 引用时，保留全部 `source_bundle_ids`。
- 禁止事项：不访问或修改 `D:/new_tdx`；不复制、移动、删除或改写源包、解包、metadata、normalized、cache、backup 文件。

## 实际执行

执行脚本：`scripts/backfill_v3_source_file_catalog.py`

结果：

| 项目 | 结果 |
|---|---:|
| 参与 bundle | 5 |
| 物理 package | 4 |
| 新增 `source_files` 行 | 32 |
| 更新行 | 0 |
| `source_bundles` | 5 |
| `source_packages` | 4 |
| `metadata_snapshots` | 2 |
| 物理回执未登记 | 0 |
| catalog 无物理回执 | 0 |
| `source_files` 空表问题 | 已关闭 |

4 个 package 每个登记 8 个 metadata 文件；同一 package 被两个 bundle 复用的关系已写入 `source_bundle_ids`，没有把重复物理 package 当成新的文件副本。

## 验收证据

- 定向测试：`pytest -q tests/upgrade_v3/test_p04_03_source_catalog.py` → **3 passed**。
- 实际审计产物：[P04-03-01-B_SOURCE_CATALOG_RECONCILIATION.json](<E:/codex work/大A交易/reports/upgrade_v3/P04-03-01-B_SOURCE_CATALOG_RECONCILIATION.json>)。
- 审计结果：`physical_receipt_catalog_mismatch=false`、`source_files_catalog_empty=false`、`mutation_executed=false`（审计阶段只读）。
- 回滚测试覆盖非法 bundle 身份，确认不会写入部分 `source_files`。

## 未扩大范围

- 没有执行解包目录回收；最近 2 个已使用 bundle 和唯一源包仍受保护。
- 没有执行备份、恢复演练、移动、隔离或删除。
- `P04-03-03` 的缓存预览仍是只读预览，不因本任务获得删除权限。

## 下一任务

继续 P04-03 的缓存/备份收口：按最新台账处理尚未关闭的独立审计项；优先保持 `P04-03-03-A`、备份链和 resolver 的证据边界，不跳入 P05。

# V3 P04-03-08 旧 M0-M15 产物清理记录

日期：2026-09-12  
适用主文档：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`  
主文档 SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`

## 范围与保护边界

本次仅处理已确认不属于 V3 核心产物的旧 M0-M15 残留。`D:/new_tdx` 及所有配置的 TDX 输入目录未触碰。所有 `result-obj-*` V3 结果对象、已登记 V3 source bundle、当前有效 publication 绑定和完整备份链均保留。

## 已删除对象

- 3 个未登记的旧 source bundle 收据目录；它们只包含重复的 `source_bundle.json`，对应的登记源包/提取物仍保留。
- 31 条 `INCOMPLETE` 旧备份链及其物理残留；这些链均缺少数据库主体，且不包含 V3 结果或 V3 source bundle。
- 6 组孤立旧备份对象（2 个数据库对象、4 组 manifest/object 对）；均无当前 catalog 归属，且不包含 V3 核心结果。
- 1 个旧 `analysis-obj-*` parquet 物理对象（`history-slice-coordination-v1.0`）；它属于历史分析切片，不属于 V3 结果发布图。

旧分析对象对应的 2 条 `analysis_slices` 身份行保留为 tombstone：历史迁移后的外键仍指向已重命名的旧表，直接删除会触发 DuckDB catalog 错误。物理文件已删除，`storage_objects` 已标记 `DELETED`、`referenced=false`，并记录删除原因及关联 tombstone；没有删除或重构 M13 表结构。

## 清理后核验

| 检查项 | 结果 |
|---|---:|
| `backup_catalog` 记录 | 12 |
| 完整备份链 | 12/12 |
| 不完整备份链 | 0 |
| 孤立数据库/manifest/object 目录 | 0/0/0 |
| source bundle catalog / 物理收据 | 5/5 |
| V3 `result-obj-*` 结果对象 | 51，全部保留 |
| V3 fallback publication binding | 0 |
| 历史 `source_files` 记录 | 0，未伪造回填 |
| 回归测试 | 170 passed |

`source_files=0` 是历史 catalog 元数据缺口，不是可删除的物理文件；本次没有把它误当作 V3 产物删除，也没有未经方案授权进行历史回填。

## 验收结论与下一步

本次旧产物清理动作通过；V3 核心产物未被删除。P04-03 的旧备份链清理子项已收口，但 P04-03 仍不能宣称整体 `FULL_PASS`：source_files 历史缺口、V3 结果待发布绑定及生产恢复/缓存集成仍需按最新 V3 文档单独验收。当前下一步仍是关闭 P04 剩余生产集成和独立审计项，未进入 P05。

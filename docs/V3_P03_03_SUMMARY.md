# V3 P03-03-summary 阶段报告

## 结论

`P03-03-summary`：**PASS**。

本阶段只处理 `stock_structure_summary_daily` summary 域，完成导入、逐行语义对照、切读和停旧写；`historical_structure_daily` structure 明细域未被本阶段改写。执行依据为工作区最新 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，SHA-256 为 `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`，对应第 17.6、18.6、18.7 节。

## 阶段合同

- 新增迁移 `032_v3_structure_summary_result_rows`。
- 新增 `structure_summary_result_rows`，物理主键为 `(result_object_id, security_id, trade_date)`；summary 的七个业务字段全部保留。
- `queues_json` 只做排序、紧凑 JSON 的规范化用于内容 hash；队列命中、层级、来源、排名、研究带、质量和计数语义不变。旧历史 `NaN` 文本在 JSON 语义对照中按原值保留。
- 新增 `structure_summary_result_daily` 兼容视图：已绑定 slice 从 V3 result object 读取，未绑定 slice 才回退旧表。
- M8/M9 preview summary writer 改为只写 V3 result rows；API 的 intersection、new-high、stock insight summary reader 全部改读兼容视图。
- `stock_structure_summary_daily` 保留为不可变兼容/审计来源；旧表没有删除或写入。

## 生产证据

- 生产维护备份：`backup-20260912T030620Z-5f80d367e3dc`，`create_offline_backup` 状态 `VERIFIED`，数据库 SHA-256：`5f80d367e3dce7b5bb8947d63aabb896957871003565075b05060e27cadd2abd`。
- 既有 history-backup 外部对象路径问题：`create_history_backup` 因 `BACKUP_OBJECT_PATH_MISSING` 拒绝执行；本阶段只写 DuckDB 内 schema/结果行，因此使用同维护窗口下通过 CHECKPOINT 和整库校验的 offline backup。该外部对象恢复能力作为独立跨域问题保留，不绕过校验。
- 迁移：`032_v3_structure_summary_result_rows`。
- 迁移 SQL SHA-256：`B8A7F6E7405ACAD562C1C1C6EE73FBB01C9C66CA929D013B14A14CE1350D3CEF`。
- 迁移回执：`migration-032_v3_structure_summary_result_rows-81d03235648b491e89114220a425c4fa`。
- `15/15` summary slice 完成 binding；`3` 个 result objects；`16,381` 行 V3 去重物理结果；`15` 个 binding。
- 旧表 `81,902` 行；新兼容视图回读 `81,902` 行；未绑定回退 `0`；旧表行数和声明行数均为 `81,902`。
- old→new、新→old 按业务字段及规范化 JSON 的多重集差集均为 `0`。原始 JSON 文本存在格式差异（旧表含空格，新结果按合同紧凑化），不属于业务值差异。
- 结果对象重复导入复用 `12` 个 slice；相同内容未新增物理结果；质量/研究带变化不会错误共享对象。
- 生产服务受控重启后 `READY/0`；`/api/stocks/{id}/insight` structures、`/api/stocks/new-highs` smoke 均成功返回。
- 数据库迁移完整性：`schema_migrations=29`（含 base），`schema_migration_checks=28`，最新迁移为 032；所有已应用迁移 SQL hash/依赖核验通过。
- 未访问或修改 `D:/new_tdx` 及配置的 TDX 输入目录。

## 测试与验收

- summary 定向测试：`2 passed`。
- P03 及相关 M7–M15 完整回归：`385 passed in 202.06s`。
- Python `compileall` 通过；6 个 v2 JavaScript `node --check` 通过；`git diff --check` 通过。
- P03-03 summary 验收：**PASS**。summary 已完成导入、逐行语义对照、切读、停旧写；旧表保留，证据和历史身份未删除。

## 下一阶段

按 V3 文档下一任务为 `P04-01`：规划每日最小失效范围。P03-03 的三个域现在全部完成，但不将 P04 及以后阶段提前标记通过。

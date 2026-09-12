# V3 P03-03-structure 阶段报告

## 结论

`P03-03-structure`：**PASS**。本阶段只处理 `historical_structure_daily` 结构明细域；`stock_structure_summary_daily` 未迁移、未切读、未改写，下一阶段单独处理 `summary`。

执行依据为工作区当时的最新 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，SHA-256 为 `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`。依据第 17.6、18.7 节，保留结构日期、队列、命中、层级、来源分类、研究带、排名、transition、basis、合同、evidence 和 quality 字段；只把 `slice_id` 从物理结果键中拆出，由 result-object binding 恢复切片身份。

## 阶段合同

- 新增 `structure_result_rows`，物理主键为 `(result_object_id, security_id, trade_date, queue_name)`。
- `evidence`、`quality_codes`、队列名、未知命中语义、研究带和队列/层级排名语义均纳入 versioned value semantics 与 `result_value_hash`。
- 对 `queue_rank`、`tier_rank` 的 pandas 浮点/ DuckDB 整数表示做 canonical normalization；非有限值按 `HASH_AS_NULL_PRESERVE_LEGACY_STORAGE` 处理，未改写旧表。
- 新增 `historical_structure_result_daily` 兼容视图：优先按 slice binding 读取 V3 result object；未绑定 slice 才允许回退旧表。
- M8/M9 结构 writer、M13 结构输入 reader、API 的结构历史/队列/evidence reader 均切换到兼容视图；旧 `historical_structure_daily` 保留为不可变兼容/审计来源。
- `stock_structure_summary_daily` 及其 reader/writer 保持原链路，不在本阶段扩大范围。

## 生产证据

- 维护备份：`backup-20260912T023322Z-46f5b9f95f44`，状态 `VERIFIED`。
- 备份 SHA-256：`46f5b9f95f44cec8b682ed140382d0519041bf2575ebd05666dc119c0de59e7e`。
- 迁移：`031_v3_structure_result_rows`。
- 迁移 SQL SHA-256：`90746B7E7B1F262CD169EB68FB9817BFFDE1E3995A5B0D36D205FCD9D9CAC0BE`。
- 迁移回执：`migration-031_v3_structure_result_rows-d8eced0d71c04d19afb21c787bbbd433`。
- 15/15 structure slice 完成 binding；3 个 result objects；V3 去重物理行 81,905。
- 旧结构表 409,510 行；新兼容视图回读 409,510 行；旧→新与新→旧逐行 `EXCEPT ALL` 差集均为 0。
- 逐 slice 声明行数、旧表行数、兼容视图行数全部一致；未绑定回退行 0；结果业务主键重复 0。
- `stock_structure_summary_daily` 保持 81,902 行，未被本阶段触碰。
- 服务恢复 `READY/0`；结构历史、队列、evidence HTTP smoke 均成功，结构能力为 `AVAILABLE`。
- `D:/new_tdx` 及配置的 TDX 输入目录未访问、未修改；主 V3 实施文档的既有工作区修改未触碰。

## 测试与验收

- structure V3 定向测试及关联迁移/旧结构测试：`23 passed`。
- 跨域回归：`380 passed`；另有 3 个既有 M12 浏览器/UI 文本断言失败，均集中在既有 UI 文案/乱码断言，涉及 `tests/upgrade_m12/test_browser_behavior.py` 1 项、`tests/upgrade_m12/test_insight_ui.py` 2 项；本阶段未修改任何 UI 文件，结构 API/M12 API 测试通过，未将其归因于结构迁移。
- `py_compile` 通过；结构 reader/writer 命中复核确认生产路径已切换，旧 writer 仅保留给兼容 fixture/迁移读取。

## 下一阶段

按 V3 文档下一任务为 `P03-03-summary`：只迁移 `stock_structure_summary_daily`，并单独完成导入、逐行对照、切读、停旧写和验收；本阶段未预先实现或执行该任务。

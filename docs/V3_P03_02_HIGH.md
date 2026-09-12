# V3 P03-02-high 阶段报告

## 结论

`P03-02-high`：**PASS**。本阶段只处理 high 域，没有开始 `P03-03`。

执行依据为工作区当时的最新 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，SHA-256 为 `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`。依据第 17.6、18.6 节，high 的物理键必须保留 `window`，结果对象必须经 slice binding 读取，旧表不得被删除或重写。

## 阶段合同

- 新增 `high_result_rows`，物理主键为 `(result_object_id, security_id, trade_date, window)`。
- `window` 仅允许 `20/30/60/100`，并进入结果值 hash 的业务键和语义合同。
- 新增 `high_result_daily` 兼容视图：优先读取绑定的 V3 result object；未绑定旧 slice 才允许回退旧表。
- high writer 切换为 `insert_high_result_rows`；API、M13 market-cycle reader 切换为 `high_result_daily`。
- 旧 `stock_high_daily` 仅保留为不可变兼容/审计来源，不再由生产 high writer 写入。

## 生产证据

- 维护备份：`backup-20260912T012602Z-9a4b46c91b4d`，状态 `VERIFIED`。
- 备份 SHA-256：`9a4b46c91b4de3c19afa6daaadbbefc903307270c97a4b5fbc8e64a604f88b0d`。
- 迁移：`029_v3_high_result_rows`。
- 迁移 SQL SHA-256：`68c0b1af6b4cdd30cd36ce8d85a93cc327f3c8c30886a3b8b291edbefc3d611a`。
- 迁移回执：`migration-029_v3_high_result_rows-306e6fa6dfad4ea1b67007ae32f48825`。
- 31/31 high slice 完成 binding；8 个 result objects；V3 物理去重行 296,544。
- 旧表 1,112,040 行；新兼容视图回读 1,112,040 行；未绑定回退行 0。
- old→new 与 new→old 逐行 `EXCEPT ALL` 差集均为 0。
- 31/31 slice 均保留四个窗口；结果对象行数与实际存储行数一致；对象值 hash mismatch 为 0。
- 旧 metadata 的历史口径已单独记录：27 个 slice 的 `row_count` 等于物理行数，4 个多日期 slice 为 `row_count × 4`；31 个均无不匹配，未改写历史 metadata。
- API smoke：`/api/stocks/new-highs` 返回 `total=6177`、`window=20`、`as_of_trade_date=2026-09-10`；`/api/market/cycle` 四窗口计数正常；服务恢复 `READY/0`。

## 测试与验收

- high/迁移链定向测试：`13 passed`；补充三次同输入重跑后 high 定向测试：`2 passed`。
- 相关完整回归：`189 passed in 95.71s`。
- `py_compile` 与 `git diff --check` 通过。
- TDX 输入目录未访问、未修改；主 V3 实施文档的既有工作区修改未触碰。

## 下一阶段

`P03-02-high` 完成后，按文档下一任务为 `P03-03`；本阶段未执行、未预先实现 `P03-03`。

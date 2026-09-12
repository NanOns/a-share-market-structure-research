# V3 P03-02 Technical 结果行迁移与切读

## 1. 阶段合同

- `task_id`：P03-02 / technical 子任务
- 依据：V3 主实施文档 §17.6、§18.6 P03-02
- 主实施文档 SHA-256：`912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`
- 前置：P03-01 PASS；生产已存在 `analysis_result_objects` 与 `analysis_slice_result_bindings`
- 本阶段范围：只迁移 `technical`，不执行 `strength`、`high` 或 P03-03

本阶段要求把旧 `stock_technical_daily` 的物理结果改为按内容寻址的
`technical_result_rows`，保留每个 `slice_id` 的独立绑定与身份依据；内容 hash
必须包含业务键、字段 schema、NULL、质量、单位/价格基准和语义合同。导入后先
逐行对照，再切换实际 reader，并停止主预览流程对旧 technical 表的写入。

## 2. 实施内容

- 新增 `027_v3_technical_result_rows.sql`：
  - `technical_result_rows(result_object_id, ...)`，物理主键为
    `(result_object_id, security_id, trade_date)`；
  - `technical_result_daily` 兼容视图，优先解析 V3 slice binding；只有未绑定的
    旧 fixture/遗留 slice 才允许回退到旧表；
  - 旧 `stock_technical_daily` 保留为不可变兼容输入，未删除、未覆盖。
- 更新 `workbench_analysis.technical`：
  - 新增 technical V3 schema/semantic contract、canonical value hash、结构/行数/hash
    回读校验、identity evidence 和 result-object 绑定；
  - `insert_technical_result_rows` 只写 V3 result rows，不双写旧表；
  - 原 `insert_technical_rows` 仅保留给未绑定旧 M8 兼容 fixture。
- 更新主预览 writer：`scripts/build_m8_m9_preview.py` 的 technical writer 改用
  `insert_technical_result_rows`。
- 更新 technical 相关的 M8C、M11、M13 预览 reader 及服务 API，全部通过
  `technical_result_daily` 解析 slice binding。
- 新增 `scripts/migrate_v3_technical.py`：默认只读审计，`--apply` 在维护窗口内
  以单事务导入全部 technical slices；异常整批回滚。

## 3. 生产执行证据

执行前服务状态为 `READY`、活动任务 0。数据库写入前创建并验证离线备份：

- backup：`backup-20260912T004954Z-21dfb9a772b2`
- 状态：`VERIFIED`
- SHA-256：`21dfb9a772b2935ce164475dd836fed6d3c7123aee06dd006f344f323dd2d7e5`
- verification：publication_heads=5、queue_memberships=7542、membership_entries=435472、outcomes=2030

应用与导入回执：

- migration：`027_v3_technical_result_rows`
- SQL SHA-256：`3baf7d554a27d3c3a830f672036f5af2b9511863d32341b5834d4b7eaeb1680c`
- receipt：`migration-027_v3_technical_result_rows-4f6afa01393d4f3a92df1b0fc972001b`
- 生产 technical slices：31
- technical bindings：31
- technical result objects：12
- 去重后的 `technical_result_rows`：111203
- 旧表行数：278009；V3 视图回读行数：278009
- `analysis_slices.storage_object_id` 已为 31/31 个 technical slice 绑定结果对象

## 4. 对照、切读与验收

生产逐行对照结果：

- `old_not_in_new=0`
- `new_not_in_old=0`
- `technical_result_daily.result_object_id IS NULL` 行数为 0
- 质量/语义内容变化在临时库中生成不同 result object；同内容不同 slice 共享一个
  result object 但保留两条 binding

服务恢复后 HTTP smoke：

- 服务状态：`READY`
- 活动任务：0
- `/api/stocks/technical`：最新 publication 返回 `total=6177`，`as_of_trade_date=2026-09-10`，正常返回分页结果

测试与静态检查：

```text
python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7 \
  tests/upgrade_m8/test_technical_contracts.py \
  tests/upgrade_m8/test_rps_windows.py \
  tests/upgrade_m13/test_m13_materializer.py \
  tests/upgrade_m2/test_api.py tests/upgrade_m4/test_one_click_publication.py \
  tests/upgrade_m1/test_owner_and_repository.py tests/upgrade_m15/test_performance.py
185 passed in 95.92s
```

另有 P03-02 定向测试 2 passed；`py_compile` 与 `git diff --check` 通过。

验收结论：`PASS`。

- technical 已完成导入、逐行对照、reader 切换和主 writer 切换。
- 生产未绑定旧表回退行数为 0，旧表仅保留兼容/审计用途。
- TDX 输入目录未访问、未修改。
- `strength`、`high` 尚未执行，不能因 technical PASS 推进跨域任务。

## 5. 下一阶段

下一步只能执行 P03-02 的 `strength` 子任务；在用户明确继续前不启动 `high` 或
P03-03。P03-02 technical 的跨域剩余项独立保留，不把本阶段 PASS 扩大解释为整步
P03-02 PASS。

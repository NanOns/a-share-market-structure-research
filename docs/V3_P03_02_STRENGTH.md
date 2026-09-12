# V3 P03-02 Strength 结果行迁移与切读

## 1. 阶段合同

- `task_id`：P03-02 / strength 子任务
- 依据：V3 主实施文档 §17.6、§18.6 P03-02
- 主实施文档 SHA-256：`912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`
- 前置：P03-01 PASS；P03-02 technical PASS
- 本阶段范围：只迁移 `strength`，不执行 `high` 或 P03-03

strength 的结果内容除业务键、值、NULL、质量、价格基准外，还明确包含 RS/RPS
语义、同日有效样本分母和排名合同；不能因为数值巧合而丢失质量或排名依据。

## 2. 实施内容

- 新增 `028_v3_strength_result_rows.sql`：
  - `strength_result_rows(result_object_id, ...)`，物理主键为
    `(result_object_id, security_id, trade_date)`；
  - `strength_result_daily` 兼容视图，优先解析 V3 slice binding；只有未绑定遗留
    slice 才回退旧表；
  - 旧 `stock_strength_daily` 保留为不可变兼容输入，未删除、未覆盖。
- 更新 `workbench_analysis.strength`：
  - 新增 strength V3 schema/semantic contract、canonical value hash、结构/行数/hash
    回读校验、identity evidence 和 result-object 绑定；
  - `insert_strength_result_rows` 只写 V3 result rows；旧 writer 仅保留未绑定兼容 fixture。
- 更新主 M8/M9 preview writer，停止 strength 写入旧表。
- 更新服务 API 的 technical、new-high、technical-history、insight、queue 等 strength
  消费路径，全部通过 `strength_result_daily` 解析 slice binding；high 物化与 high
  结果表本身未迁移。
- 新增 `scripts/migrate_v3_strength.py`：默认只读审计，`--apply` 在维护窗口内以单
  事务导入全部 strength slices；异常整批回滚。

## 3. 生产执行证据

执行前服务状态为 `READY`、活动任务 0。数据库写入前创建并验证离线备份：

- backup：`backup-20260912T010834Z-02efee63a95c`
- 状态：`VERIFIED`
- SHA-256：`02efee63a95c12de1d742f0ca508d6a770b8f035bc25fe59379d5b49c8cf910e`
- verification：publication_heads=5、queue_memberships=7542、membership_entries=435472、outcomes=2030

应用与导入回执：

- migration：`028_v3_strength_result_rows`
- SQL SHA-256：`b8442f7dc2f974281f2c51f448e78875057946ca883aba7b62cb4b9f34b59700`
- receipt：`migration-028_v3_strength_result_rows-0e14075c629f42c494ae100f6fd85600`
- 生产 strength slices：31
- strength bindings：31
- strength result objects：9
- 去重后的 `strength_result_rows`：92669
- 旧表行数：278009；V3 视图回读行数：278009

## 4. 对照、切读与验收

生产逐行对照结果：

- `old_not_in_new=0`
- `new_not_in_old=0`
- `strength_result_daily.result_object_id IS NULL` 行数为 0
- 同内容不同 slice 在临时库共享一个对象并保留两条 binding；strength quality 改变不共享对象

服务恢复后 HTTP smoke：

- 服务状态：`READY`
- 活动任务：0
- `/api/stocks/technical`：`total=6177`，RPS 正常返回
- `/api/stocks/new-highs`：`total=6177`，strength join 正常
- `/api/stocks/{security_id}/insight`：`AVAILABLE`

测试与静态检查：

```text
python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7 \
  tests/upgrade_m8/test_technical_contracts.py \
  tests/upgrade_m8/test_rps_windows.py \
  tests/upgrade_m13/test_m13_materializer.py \
  tests/upgrade_m2/test_api.py tests/upgrade_m4/test_one_click_publication.py \
  tests/upgrade_m1/test_owner_and_repository.py tests/upgrade_m15/test_performance.py
187 passed in 98.44s
```

另有 strength 定向测试 2 passed；`py_compile` 与 `git diff --check` 通过。

验收结论：`PASS`。

- strength 已完成导入、逐行对照、reader 切换和主 writer 切换。
- high 结果和 high writer 未切换，不能把本阶段 PASS 扩大为整个 P03-02 PASS。
- TDX 输入目录未访问、未修改。

## 5. 下一阶段

下一步只能执行 P03-02 的 `high` 子任务；在用户明确继续前不启动 high 之外的
P03-03。technical 与 strength 的 PASS 均独立记录。

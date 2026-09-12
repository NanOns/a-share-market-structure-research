# V3 P03-01 结果对象与切片绑定层

## 1. 阶段合同

- `task_id`：P03-01
- 依据：V3 主实施文档 §17.6、§18.6 P03-01
- 文档 SHA-256：`912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`
- 前置：P02-04 PASS；代码起点 `236ff88 feat: complete v3 p02-04 relation cutover`
- 目标：建立 `analysis_result_objects` 与 `analysis_slice_result_bindings`，将结果内容身份与切片/依赖/发布身份分离；旧域 writer 本阶段不整体切换。

本阶段严格保留每个 `slice_id`、依赖和 publication 身份，不将多个切片改成单一身份。结果对象以规范化业务值、NULL/质量、字段 schema、单位/语义、价格基准和成员依据参与内容哈希；任务时间、切片来源等只进入身份证据。

## 2. 实施内容

新增：

- `src/workbench_db/migrations/026_v3_result_objects.sql`
  - `analysis_result_objects`
  - `analysis_slice_result_bindings`
  - 结果对象唯一 `value_hash`、`row_count`、`storage_kind` 与外键/索引约束
- `src/workbench_service/result_objects.py`
  - 规范化行与主键校验
  - 内容哈希和 content-addressed `result_object_id`
  - Parquet 原子写入、结构/行数/哈希精确回读核验
  - 同内容跨 slice 复用、不同语义/质量不复用
  - 绑定时保留切片依赖、daily basis 与 identity evidence
- `scripts/apply_v3_result_objects.py`
  - 默认只读审计；`--apply` 仅用于服务停止且备份已验证的迁移
- `tests/upgrade_v3/test_p03_01_result_objects.py`
  - 同内容不同 slice 一对象两身份
  - 质量/语义或业务值变化不共享
  - 缺失绑定 fail-closed

为适配新增迁移版本，更新了两条旧迁移测试的最新版本预期：

- `tests/upgrade_m14/test_online_batches.py`
- `tests/upgrade_m7/test_migration_executor.py`

这两处只更新迁移链断言，不改变业务行为。

## 3. 生产执行证据

生产库执行前使用已验证备份：

- backup：`backup-20260912T000023Z-65432baaf1ee`
- 状态：`VERIFIED`
- SHA-256：`65432baaf1ee7d369704b6656421a7bb8df6e8a1681214da28a9e5c8197b68a4`
- 验证摘要：publication_heads=5、queue_memberships=6815、membership_entries=435472、outcomes=2030

迁移前只读基线：

- `analysis_slices`：389
- 结果对象表/绑定表：不存在
- 既有领域结果未迁移，符合本阶段边界

执行回执：

- migration：`026_v3_result_objects`
- receipt：`migration-026_v3_result_objects-672e1f8df6094901a2fb20ff7f93496f`
- SQL SHA-256：`5ce178a6d7971c1bf9bfda4722986f08a946fd179c2ae5f82338ebc076c1e38d`
- 结果：`APPLIED`
- 迁移后：`analysis_slices=389`、`analysis_result_objects=0`、`analysis_slice_result_bindings=0`

迁移后只读核对：

- 最新 schema migration：`026_v3_result_objects`
- relation_revisions=3、relation_edge_intervals=74086、relation_observations=6
- `membership_entries`=435472，未发生改写
- 服务 HTTP 状态：`READY`，活动任务 0
- 最新 publication 仍为 `m4-8a99c99719061f4f1f166d0b9184506c`
- `/api/sectors` 返回 499 个板块，旧 publication identity 与层级/关系信息可正常读取

## 4. 测试与验收

定向 P03-01 与迁移回归：`10 passed`。

完整目标回归：

```text
python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7 tests/upgrade_m2/test_api.py tests/upgrade_m4/test_one_click_publication.py tests/upgrade_m1/test_owner_and_repository.py
162 passed in 83.29s
```

验收结论：`PASS`。

- 同内容不同 slice：两个独立 slice identity，共享一个 result object。
- 质量、语义或业务值不同：生成不同 result object，不错误合并。
- hash 命中：仍验证 Parquet 结构、列、主键、行数、值哈希和 identity evidence。
- 旧域 writer：未切换，未删除旧表，未对既有分析结果做迁移或覆盖。
- TDX：未访问、未修改。

## 5. 未决项与下一阶段

- 主规格文档存在本轮之前的工作区修改，本阶段未修改、未覆盖、未回退。
- P03-01 只建立共享结果对象和绑定基础设施；尚未创建 `technical_result_rows` 等逐域结果表，也未切换旧域 reader/writer。
- 下一阶段为 P03-02：严格按文档顺序先迁移 technical，再 strength，再 high；每个域分别执行导入、对照、切读、停旧新写和独立验收，任一域失败不得标记整步通过。

# V3 P02-02 旧关系导入与逐快照对照阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P02-02 |
| 输入代码版本 | `5aa5ce2`（P02-01 完成）+ 本阶段未提交工作区变更 |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 关系迁移 | `025_v3_relations`，依赖 `024_m14_online` |
| 导入合同 | `legacy-membership-import-v3-v1` |
| source_scope | `TDX-MEMBERSHIP:direct-members-v3-v1` |
| 生产数据库 | `data/database/market_research.duckdb` |

本阶段按主实施文档 §17.4、§17.5、§17.9 MIG1 和 §18.5 P02-02 执行。旧
`membership_snapshots/entries` 保留，旧 publication 身份没有改写；没有读取或写入
`D:/new_tdx` 或其他 TDX 输入目录。

## 执行结果

### 实际旧快照

实施前以 `read_only=True` 打开生产库，按实际数量读取，而不是预设数量。实际为 6
个快照，均有 publication 绑定和完整 payload。观察时间按该旧快照关联 publication
的最早 `imported_at_utc` 登记；交易日仍单独写入 `source_effective_date`。

| 交易日 | 旧快照 ID（前 12 位） | 旧行数 | 直接边 | 派生行 | V3 revision | 属性版本 | 对照 |
|---|---:|---:|---:|---:|---:|---|---|
| 2026-09-04 | `1dcb38be541f` | 72,004 | 72,004 | 0 | 1 | `attrset-bf7d5e905dd022f02964c221` | PASS |
| 2026-09-07 | `4fdb218b7bc1` | 72,084 | 72,084 | 0 | 2 | `attrset-64e7532451af4fe1b741db5f` | PASS |
| 2026-09-07 | `8c1e65aa7687` | 72,084 | 72,084 | 0 | 2 | `attrset-64e7532451af4fe1b741db5f` | PASS |
| 2026-09-08 | `f97d0124e5ed` | 72,136 | 72,136 | 0 | 3 | `attrset-64e7532451af4fe1b741db5f` | PASS |
| 2026-09-09 | `8a36f7aaa04d` | 72,136 | 72,136 | 0 | 3 | `attrset-64e7532451af4fe1b741db5f` | PASS |
| 2026-09-10 | `f3c7f45b1e3a` | 75,028 | 72,136 | 2,892 | 3 | `attrset-20e2dbebd155c5e1ca264b8a` | PASS |

旧 payload 的 `date`、`membership_asof_date`、`membership_basis`、PIT 标记、
`historical_backtest_safe`、来源计数和完整 payload canonical hash 都写入
`relation_snapshot_bindings.legacy_payload_basis`。新关系表不重复存 75,028 行派生
成员；旧表保留，P02-03 将使用固定行业树把可解释的派生父成员重新解析。

### 直接/派生分离

- `tdxhy.cfg` 和 `infoharbor_block.dat` 的 435,472 条旧行中，均投影为关系语义
  `DIRECT`；文件来源保留在 payload/source-file evidence，不把文件名伪装成关系语义。
- 2026-09-10 的 `tdxhy.cfg:DERIVED_PARENT` 2,892 条行明确标为
  `DERIVED_PARENT`，未写入 `relation_edge_intervals`。它们的数量、来源、属性和旧
  payload hash 均保存在旧快照绑定中。
- 2026-09-10 因派生父板块属性增加，产生新的属性集合版本；关系边 hash 未改变，
  revision 仍为 3。这符合“名称/属性变化不等于成员边变化”。

### 日期、重复与兼容绑定

- 2026-09-08 与 2026-09-09 的 resolver 结果均为 72,136 条边，集合完全相同，
  但各自保留不同的 `source_effective_date`、observation 和旧快照 ID。
- 两个 2026-09-07 旧快照也共享 revision 2，但 observation 和旧 ID 绑定分别保留；
  来源 manifest/identity 仍在 source-file evidence 中区分。
- 关系区间总数为 74,086；revision 总数为 3；observation 和旧 ID binding 各为 6；
  `relation_publication_bindings` 尚未切入，这是 P02-04 的读写路径工作。
- 旧 `membership_snapshots` 仍为 6 行，旧 `membership_entries` 仍为 435,472 行。

## 生产变更证据

1. 维护前通过现有运维接口创建一致性备份：
   `backup-20260911T193112Z-7a931b0724e8`，状态 `VERIFIED`，备份前
   `membership_entries=435472`、`outcomes=2030`。
2. 确认活动任务为 0 后停止工作台服务；只应用 `025_v3_relations`，迁移 receipt 为
   `migration-025_v3_relations-ce275351de144af9bb15dfb859ad23c8`。
3. 运行 `scripts/import_v3_legacy_relations.py --apply`，随后按六个旧 ID 用
   `VersionedMembershipResolver` 对照；发现并修复了属性版本返回值缺失和兼容绑定
   字段升级，最终所有属性版本字段非 NULL。
4. 服务重新启动并健康检查为 `READY`，活动任务为 0；旧表和旧发布身份未被改写。

## 代码与回归

- 新增 `src/workbench_service/legacy_relation_import.py`：只读旧快照适配、直接/派生
  分离、PIT/日期/source evidence、旧 ID 绑定、逐快照对照和幂等回填。
- 新增 `scripts/import_v3_legacy_relations.py`：默认只读 dry-run，`--apply` 才能在
  维护窗口应用迁移和导入。
- 修正 `relation_repository.py`：属性版本复用使用冲突忽略；返回
  `attribute_version_id`；支持导入器的兼容回填。
- 修正 `membership_resolver.py`：snapshot binding 通过 observation 正确解析
  `source_scope`。
- 新增 `tests/upgrade_v3/test_p02_02_relations.py`，覆盖旧 ID、日期复用、派生证据、
  resolver 等价和重复运行。
- `python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：**123 passed**。
- 新增模块/脚本 `py_compile` 通过，`git diff --check` 通过。

## 数据异议与处理

旧表的 `membership_snapshots.snapshot_version` 与部分 payload 内的
`snapshot_version` 不同：后四个 M4 记录的表级值为 `m4-source-bundle-v1`，payload
值仍为 `sector-membership-snapshot-v1.0`。这不是被忽略的字段冲突：两者已按不同字段
保留在 `legacy_payload_basis`，对照按 payload 语义验证；没有把它们强行归并或覆盖。

## 阶段验收

**PASS。** 六个实际旧快照全部完成旧 ID 兼容绑定；direct 边集合、边计数、日期/PIT
语义和旧 payload 行数逐一通过。稳定边没有按日期重复写入，9/8 与 9/9 共享 revision
但日期独立，9/10 的派生父成员没有被错误当作新增直接股票关系。下一阶段进入
**P02-03：树语义复用与父成员去重**；在 P02-03 完成前不切旧读路径，也不关闭旧表写入。

## 独立未决项

- P02-03 需用已有 `tdx_sector_hierarchy_versions/nodes` 为 2,892 条派生父成员建立
  固定树版本解释，并验证 554 节点/父成员去重；本阶段不提前修改行业树。
- `relation_publication_bindings` 和旧 API/read path 仍未切换，按 P02-04 处理。
- 工作区原有的 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` 未提交修改仍
  保留，未被本阶段覆盖或回退。

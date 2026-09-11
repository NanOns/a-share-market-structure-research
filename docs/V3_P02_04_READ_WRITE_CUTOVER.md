# V3 P02-04 旧读路径接入与新发布增量关系写入阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P02-04 |
| 输入代码版本 | `a116d99`（P02-03 完成）+ 本阶段工作区变更 |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 适用条款 | §17.4、§17.9、§18.5 P02-04 |
| 关系 source_scope | `TDX-MEMBERSHIP:direct-members-v3-v1` |
| 关系写入合同 | `relation_revisions` + `relation_edge_intervals` + `relation_observations` + `relation_publication_bindings` |
| 旧表策略 | 历史数据保留；新发布不再写 `membership_entries` 全量明细 |

本阶段按文档顺序先接旧读路径和 publication identity，再把新发布导入改为增量观测绑定，最后
关闭两个新发布入口的旧全量成员写入。没有删除历史 `membership_snapshots/entries`，没有改写
旧 publication 身份，没有访问或修改 `D:/new_tdx` 或其他 TDX 输入。

## 读路径改造

新增 `VersionedMembershipResolver.publication_binding` 和
`edges_for_publication_compat`：

- 新 publication 优先读取 `relation_publication_bindings`；
- 历史 publication 通过 `publication_memberships` → `relation_snapshot_bindings` →
  `relation_observations` 桥接到固定 relation revision；
- relation bridge 缺失时不把旧 payload 偷换成新的关系来源。

`src/workbench_service/app.py` 的实际数据库关系消费者已切换：

- `sectors` 的成员数与报价集合；
- fallback `linkage` 的成员排序、分页和反向查询；
- fallback strength association 的成员集合；
- `identity` 的 membership/relation observation/revision/hierarchy 元数据。

`attribute_library.py`、`history_adapter.py`、`intersection.py`、`association.py` 是纯 DTO/规则
模块，本身没有直接 membership 表读；它们继续保留原合同，由 app 的绑定输入改为 resolver 结果。
`analysis_activation.py` 对有 V3 publication binding 的基础 publication 复制 relation binding；
仅历史 publication 才保留旧 ID bridge。

## 新发布增量写入

`OneClickPublisher` 和 `WorkbenchRepository.import_publication` 均在发布事务内：

1. 从发布成员输入提取 DIRECT/LEGACY_EXPLICIT 边；`DERIVED_PARENT` 不写直接边；
2. 记录属性集合和 source-file/bundle 观测证据；
3. 复用不变 relation revision，变化才写增量区间；
4. 插入 `relation_publication_bindings`，publication 直接绑定 observation/revision；
5. relation 写入失败与 publication 结果一起回滚。

发布事务使用 `RelationRepository.record_observation(..., manage_transaction=False)`，因此不会在
外层 publication 事务内开启嵌套事务。旧 `membership_entries` 只保留历史迁移/兼容查询、备份
一致性校验和旧 M1 导入证据边界，不再被新发布入口写入。

## 测试与阶段证据

新增 `tests/upgrade_v3/test_p02_04_publication_binding.py`，覆盖：

- 不同成员内容得到不同 relation revision，但两个 publication 各自有 observation/binding；
- 发布提交前崩溃时 publication、observation、binding、edge 全部为 0；
- 相同成员跨新交易日只新增 observation/binding，revision/edge 不增加，旧
  `membership_entries` 仍为 0；
- 同一 production identity 重试不会重复 relation binding。

完整目标回归：

`python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7 tests/upgrade_m2/test_api.py tests/upgrade_m4/test_one_click_publication.py tests/upgrade_m1/test_owner_and_repository.py`

结果：**159 passed**。另有 `py_compile` 和 `git diff --check` 通过。

## 生产只读/服务证据

本阶段没有向生产触发新发布任务，因此 `relation_publication_bindings=0` 是预期状态；没有用合成
发布数据污染生产库。现有生产历史关系保持：

- 6/6 旧快照对照 PASS；旧 `membership_entries=435472`；
- 9/10 绑定的 `tdx-hierarchy-v1.1-dd0b726a256dae0a`、22 个父行业、2,892 个派生父成员
  审计 PASS；
- 9/4、9/7、9/8、9/9 未被未来树回填；
- 新代码加载后的 HTTP smoke：服务 READY、active job 0；最新 publication 走
  `LEGACY_ID_BRIDGE`，relation revision 3，sector 成员 19，linkage 成员 19、排名 1/2/3，
  candidate association contract 存在。

P02-03 维护备份 `backup-20260911T233048Z-45d7b3c1bed2` 仍为 VERIFIED；本阶段无生产数据库写入，
无需新增维护备份。

## 阶段验收

**PASS。** P02-04 已完成 V3 relation resolver 接入、历史 ID 兼容、新 publication 增量 observation
绑定和新发布旧全量写关闭。旧表作为迁移前历史保留，未被删除或重写。下一阶段进入
**G02 → P03-01：建立共享结果对象与切片绑定层**；在下一阶段前不做结果表物理归并或历史回收。

## 独立未决项

- `relation_publication_bindings` 生产行将在下一次真实新发布时产生；本阶段用临时 DuckDB 原子性
  测试验证，不伪造生产发布。
- `upgrade_m1.py`、`legacy_relation_import.py`、备份校验仍保留旧表读取，这是历史迁移/恢复边界，
  不属于新研究读路径；旧 API 通过 relation bridge 读取。
- 独立的 M15 资源版本断言问题仍不纳入本阶段。
- 工作区原有 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` 未提交修改仍保留，
  本阶段未覆盖、回退或提交该文件。

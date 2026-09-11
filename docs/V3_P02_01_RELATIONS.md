# V3 P02-01 关系/属性增量结构阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P02-01 |
| 输入代码版本 | `426525b`（P01-03 证据弹窗完成） |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，当前工作区版本 |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 最新迁移基线 | `024_m14_online`；本阶段登记 `025_v3_relations` |
| 目标 | 建立慢变关系/属性增量结构、规范 hash、source_scope、版本区间查询和 ADD/REMOVE 纯函数 |
| 范围 | `relation_*` 迁移、`relation_repository.py`、`membership_resolver.py`、合成 DuckDB 测试 |
| 不在范围 | 旧 membership 导入、旧 API/读路径切换、旧表迁移、行业树复用、TDX 读取、生产数据库应用 |

本阶段严格按主实施文档 §17.4、§18.5 P02-01 执行。没有发现文档异议；新增结构与旧 `membership_snapshots/entries` 并存，尚未接入生产旧读。

## 实施结果

### 迁移与表结构

- 新增 `025_v3_relations.sql`，并在 `MigrationExecutor` 中登记依赖 `024_m14_online`。
- 新增 `relation_revisions`、`relation_edge_intervals`、`relation_observations`、`relation_snapshot_bindings`、`relation_publication_bindings`。
- 新增 `sector_attribute_versions`、`sector_attribute_revisions`、`sector_attribute_revision_bindings`，属性集合版本与单板块属性对象分离。
- 边区间使用 `[from_revision, to_revision)`；索引覆盖按板块和按证券查询。未修改或删除旧表。

### 规范化与增量写入

- `make_source_scope()`/`validate_source_scope()` 拒绝日期或 task/job 标识进入稳定命名空间。
- 边 hash 只包含 source_scope、解析合同、规范端点和 source_kind；不包含日期、观测时间、路径、名称或行情。
- 属性 hash 单独包含名称、类型、角色和语义桶；改名不会制造关系 revision，但会生成属性 revision。
- `diff_relation_edges()` 将 source_kind 改变表达为旧边 REMOVE + 新边 ADD；排序、去重稳定。
- 相同边集合只增加 observation；变化时单事务建立新 revision、关闭移除边、插入新增边。
- 空源或 `source_complete=False` 只登记 `INVALID` observation，不关闭已有区间、不创建新 revision。

### Resolver 边界

- `MembershipResolver` 批量按 revision 解析边和板块成员，不按板块/股票逐条发起 SQL。
- `VersionedMembershipResolver` 仅提供未来兼容的 snapshot/publication binding 读取门面；本阶段没有创建绑定数据，也没有切旧读路径。

## 证据与验收

### 合成与迁移回归

- `tests/upgrade_v3/test_p02_01_relations.py`：覆盖稳定 source_scope、边/属性 hash、source_kind 变化、增3删2、A→B→A 可保留旧版本、无变化只增 observation、空/不完整源 fail-closed。
- `tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：**122 passed**。
- `node` 不涉及；Python `py_compile` 覆盖新增模块和迁移执行器；`git diff --check` 通过。
- 迁移链临时 DuckDB 验证 `025_v3_relations` 原子应用、hash receipt、表和索引可用；没有对工作区生产数据库执行迁移。

### 数据和边界证据

- 所有关系测试使用临时 DuckDB 和合成行；没有读取、创建、修改、删除或重命名 `D:/new_tdx` 或其他 TDX 输入。
- 没有运行旧 membership 导入、没有修改旧 API/页面读路径、没有写入生产数据库或发布身份。
- 同一关系集合跨不同 `source_effective_date` 的第二次观察返回 `UNCHANGED`，revision 数不增加；名称变化只增加属性版本。

### 阶段验收结论

**PASS。** P02-01 完成新增关系/属性基础设施和 fail-closed 纯函数，满足“无变化日不新增边、增3删2、旧 revision 可查询、source_kind 语义变化不漏改”的合同。下一阶段进入 **P02-02：导入旧关系并逐快照对照**；执行前继续读取最新适用升级文档并先确认实际旧快照数量和输入身份。

## 独立未决项

- `025_v3_relations` 仅在临时测试库应用；正式数据库迁移和旧快照导入留给 P02-02，避免本阶段越过“尚不切生产旧读”的边界。
- P02-02 需要实际旧快照数量、观测时间、来源分类和 payload 语义核对；本阶段不预设文档中的“6 个快照”就是当前实际数量。
- 主实施文档工作区已有本轮之前的未提交修改；本阶段未修改、未覆盖、未回退该文件。

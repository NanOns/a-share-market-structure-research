# V3 P0–P3 源码与产物内部审计

## 审计结论

**FULL_PASS（审计范围：已执行的 P00-01～P03-03-summary 源码、产物、生产迁移与验收证据）**。

summary 已作为独立任务完成并通过；P04 及以后阶段不在本次审计范围内。FULL_PASS 表示本次审计范围内没有未关闭的源码、产物、迁移一致性或运行验收缺陷。

审计输入：

- 分支：`codex/v3-upgrade-analysis`
- 审计基线提交：`0298dc9 feat: complete v3 p03-03 summary result rows`
- V3 主实施文档：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`
- 主实施文档 SHA-256：`912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`
- V3 复核文档 SHA-256：`9817D513C4A1EAB3FA3A30B3B928207F19CA01FC450781F3401EE9CF8CBFFCF9`
- TDX：未访问、未写入；`D:/new_tdx` 和配置的 TDX 输入目录仍为只读边界。

## 审计项目与结果

| 项目 | 结果 | 证据 |
|---|---|---|
| P00 合同、容量、边界产物 | PASS | P00-03 合同测试通过；P00-02 容量报告与台账存在；Phase 0 前置状态未被本次改动覆盖 |
| P01 服务锁、热榜、证据 modal | PASS | P01 测试通过；6 个 v2 JS 文件 `node --check` 通过；modal 静态分组符合 V3 §12 |
| P02 关系、旧快照导入、层级复用、读写切换 | PASS | 6 个旧快照只读导入计划；2026-09-10 层级审计 `mismatch_count=0`；关系与 publication binding 计数一致 |
| P03 结果对象与六个已迁移结果域 | PASS | 五个明细域双向 `EXCEPT ALL` 均为 0；summary 按业务字段及规范化 JSON 双向差集均为 0；所有已迁移 slice 无回退；迁移 hash 完整核对 |
| Python/JS 静态质量 | PASS | `compileall -q src scripts tests/upgrade_v3 tests/upgrade_m12`；6 个 JS `node --check`；`git diff --check` |
| 相关完整回归 | PASS | `385 passed in 202.06s` |
| 服务运行状态 | PASS | `READY/0`，生产数据库路径正确 |

## 生产数据库审计

### Schema 与迁移链

- `schema_migrations=29`（base schema + 28 个迁移）。
- `schema_migration_checks=28`；迁移文件 28 个，全部已应用。
- 最新迁移：`032_v3_structure_summary_result_rows`。
- 每个已应用迁移的 SQL SHA、依赖链和 receipt 均通过 `MigrationExecutor._verify_existing` 核对。

### P02 关系与层级

- `relation_revisions=4`、`relation_edge_intervals=75,136`、`relation_observations=7`。
- `relation_snapshot_bindings=6`、`relation_publication_bindings=1`。
- `membership_entries=435,472`，未被 V3 关系切换改写。
- 2026-09-10 层级：`554` 个节点、`22` 个父行业、`2,892` 个派生父成员、`mismatch_count=0`。

### P03 已迁移结果域

| domain | 旧表行数 | 兼容视图行数 | result objects | bindings | 未绑定回退 | old→new | new→old |
|---|---:|---:|---:|---:|---:|---:|---:|
| technical | 278,009 | 278,009 | 12 | 31 | 0 | 0 | 0 |
| strength | 278,009 | 278,009 | 9 | 31 | 0 | 0 | 0 |
| high | 1,112,040 | 1,112,040 | 8 | 31 | 0 | 0 | 0 |
| member_state | 3,365,740 | 3,365,740 | 16 | 31 | 0 | 0 | 0 |
| structure | 409,510 | 409,510 | 3 | 15 | 0 | 0 | 0 |
| summary | 81,902 | 81,902 | 3 | 15 | 0 | semantic 0 | semantic 0 |

`high` 的 31 个 slice 中 27 个 exact metadata、4 个历史 x4 storage metadata，迁移脚本逐 slice 校验均无 mismatch；`member_state` 的历史 NaN 表示保留，canonical hash 语义已登记，未静默改写旧物理值。

summary 的 `queues_json` 从旧表的带空格 JSON 规范化为紧凑 JSON；解析后的队列命中、tier、source_class、queue_rank、研究带、质量和计数多重集 old→new、新→old 均为 0 差异。

### 未执行域边界

- P04 及以后阶段尚未执行，不纳入本次 P0–P3 审计。

## 源码边界审计

- 生产 M8/M9 writer 对 technical、strength、high、member_state、structure、summary 已分别指向 V3 result-row writer。
- 生产 API/M13 reader 对上述六个域已分别指向兼容 view；旧表引用仅保留在迁移审计、不可变 fixture adapter 或 legacy import。
- V3 result object identity 保留 slice binding、源合同、输入/依赖 hash、basis 与 evidence；没有用压缩删除结构/成员证据。
- M14 hot-rank 仍是 request-time direct-ephemeral，相关完整回归通过，未引入 raw payload、row、batch 或历史快照持久化。
- 所有产物写入项目托管目录；未向 TDX root 写入。

## 已发现问题与关闭记录

审计初跑发现 3 个 M12 UI 旧断言失败：它们要求 P01-03 已按 V3 §12 删除的 `<details>`、`evidenceDetails` 和“默认折叠”文案。核对主实施文档与 P01-03 阶段报告后确认是验收断言漂移，不是生产实现缺陷；已将 M12 断言更新为当前静态 `section.evidence-section` modal 合同，并通过 browser/API/UI 16 项定向测试。

该修复不修改生产 UI 行为，不修改主 V3 文档，不触碰 TDX 或生产数据库。

## 下一步

下一项只能是 `P04-01`：读取最新 V3 文档后，规划每日最小失效范围；不提前执行 P04-02 或后续任务。

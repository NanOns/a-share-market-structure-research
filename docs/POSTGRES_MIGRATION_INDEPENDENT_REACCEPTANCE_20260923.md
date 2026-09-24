# PostgreSQL 数据迁移独立复验（2026-09-23）

| 字段 | 结论 |
|---|---|
| stage | `PGM_INDEPENDENT_REACCEPTANCE_20260923` |
| stage_contract | `DAILY_FOCUS_POSTGRES_DESIGN_V2_1_CHANGE_NOTES_20260922` 第 6 节、`POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_20260922` 第 3–4、14 节，结合当前执行记录 |
| Phase 0 | `FULL_PASS_TDX_NATIVE`（既有 release seal）；本次未进入 TDX 来源目录 |
| acceptance_result | **`FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`** |
| next_stage | 观察每日 PG 同步与 head 原子更新；Focus schema 建立时再定义并验收其 authority head |

## 独立读取范围与通过项

- 使用冻结副本 `runtime/postgres_migration/20260922/market_research.source.duckdb` 的 DuckDB 只读连接，以及当前 PostgreSQL `legacy`、`workbench` 的只读事务直接查询；未运行迁移器或生成任务。
- 冻结源 103 张表、2,314,834 行。`legacy` 103 张业务表逐表行数完全一致（另有 2 张迁移 ledger 表）；当前 `workbench` 103 张业务表，共 2,528,230 行，包含后续增量。
- 修复后对 103 张表逐行全列比较，JSON canonicalization、NaN 等值规则与 PostgreSQL C collation 统一后，比较 2,314,834 行，差异为 0；对 103 张源表的主键做 `legacy EXCEPT workbench`，源键缺失数均为 0。
- 目标 `workbench` 约束均已验证：PK 105、UNIQUE 10、FK 62、CHECK 26、NOT NULL 687。
- 当前 PG `publication_heads` 最新为 `2026-09-22 / m4-547e88ce22e6d89590876c7ea1d68ca0`，与独立计算库 head 一致；该 publication 绑定的 `LOCAL_RECONSTRUCTED` snapshot 为 `m10-mainline-preview-6cf4cb562d8be09f`，两侧均有 11 个条目。PG 当日两个 V3.3 run 各 `COMPLETE / 273`，当日 candidate 行合计 546，与计算库运行身份相符。工作台运行在 PG backend，API 与 `/v3` 读取 22 号数据。
- 迁移 consumer catalog 当前为 `MIGRATED=9`、`OFFLINE_DUCKDB_ALLOWED=3`；时间语义 catalog 为 42/42 `APPLIED / timestamptz`。这些是当前 catalog 状态，不证明全部在线路径已经逐条动态覆盖。

## 审计发现及处置

### PGM-IA-02：历史绑定与快照条目缺失 — 已修复并验收

验收时发现 `legacy.analysis_slice_result_bindings` 有 72 行，`workbench` 只有 60 行，冻结源缺 18 个键；`analysis_snapshot_entries` 有 1,000 行对 193 行，缺 818 个键。随后按 `PGM_REPAIR_INTEGRITY_V1` 在单一 PostgreSQL 事务内从冻结 `legacy` 副本恢复缺失行；插入前确认所有 slice、snapshot 和 result object 引用均存在。提交后两张表 `legacy EXCEPT workbench` 均为 0。值逐列直接复制自冻结 legacy 行。

成因已由现存维护回执确认：2026-09-22 的 `backup_and_delete_trade_date.py` 删除 22 号 publication 时，备份中包含 983 条 snapshot entries 和 66 条 slice/result bindings。删除逻辑把目标 snapshot 的 slice IDs 当作仅属于当日；这些 slice IDs 实际还被历史快照引用，清理因此波及历史分析数据。现已修正该维护脚本：删除前检查共享 snapshot/slice/result-object，发现共享身份就 fail closed；有明确身份条件时不再额外使用宽泛 `trade_date` 条件扩大删除范围，并在事务中同步移除对应 PG head。

修复后该项为 `REPAIRED / ACCEPTED`。冻结源 103 张表共 2,314,834 行与 PostgreSQL `legacy` 逐列比较，差异为 0；源 PK 与 `workbench` 的差集为 0。完整内容对账按 JSON canonicalization、IEEE NaN 等值语义和 PostgreSQL C collation 处理。修复脚本只从冻结 `legacy` 源复制原始列值，不对现有行做覆盖更新。

### PGM-IA-03：ArtifactCatalog 当前文件失配 — 已修复

独立核验先发现 141 条 `AVAILABLE` 中有 10 条路径内容发生变化。修复保留旧 identity 并标为 `STALE_REFERENCE`，按当前内容新建 artifact identity；另登记 22 号 bundle 的 126 个文件。复核 165 条 `AVAILABLE` 记录，文件缺失、大小和摘要失配均为 0。同步器已加入相同的版本登记与 bundle digest 校验，避免新版本重复产生陈旧指针。

### PGM-IA-05：PG 权威 head 与新 bundle catalog — 当前数据域已修复并验收

`PG_RUNTIME_HEADS_V1` 已建立 `research_bundle_heads`（6 个日期）和 `analysis_snapshot_heads`（8 个日期/域），并在 migration ledger 登记。22 号 head 唯一指向 digest `8dffed470431779f99a4fa584d8cfb1400ee2f3a7164bbebf399efa7cfa3403d`；bundle 文件完成 catalog 登记。工作台默认研究读取已切为 PostgreSQL head，日同步器在同一事务更新 publication、analysis 与 bundle heads。Focus 子系统尚无持久化业务 schema，故 `focus_trade_date_heads` 暂不创建；这项需等 Focus schema 的版本合同形成后验收。

Focus 子系统尚无持久化业务 schema 或数据，故其 head 合同属于未来 Focus 阶段的独立门，不阻断当前已有迁移数据域。当前研究 bundle 已完成文件身份、摘要和 head 核验。

## 验收边界

修复后全量复核：冻结源 103 张表、2,314,834 行与 PostgreSQL `legacy` 全列比较，应用 JSON canonicalization 和 IEEE NaN 等值规则并统一 PostgreSQL 字符排序后，差异 0。目标 workbench 对全部 103 张源表的主键差集为 0；时间语义 catalog 中 42 列均按既定 UTC 合同落地；Publication/关系域新增行及已关闭区间对应后续有效 revision。165 条 AVAILABLE artifact 的磁盘大小和 SHA-256 差异为 0；105 个主键、10 个唯一约束、62 个外键、26 个检查约束和 687 个非空约束均已验证；22 号 PG head、研究 API 和 11 个分析域正常。Focus 业务 schema 尚未建立，故 Focus head 属未来 schema 门，不阻碍当前数据域验收。整体结果为 **`FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`**。本次未触碰 TDX 来源、未运行每日生成、未覆盖用户已有未提交工作区文件。

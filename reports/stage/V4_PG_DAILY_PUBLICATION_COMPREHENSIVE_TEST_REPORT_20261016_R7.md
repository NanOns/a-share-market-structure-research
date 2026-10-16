---
stage_id: V4_PG_DAILY_PUBLICATION_R7_20261016
code_sha: 1b51078b2e1f433152cf12c9ff0249e8ce9e206f
baseline_sha: 54959fa02af5f7aa73a931c8e610e07ed4501f6d
branch: codex/v4-workspace-cleanup
scope: R6 external-audit P0 repairs, SQL/schema compatibility review, E2E fail-closed regression, focused CI
test_scope: focused PG publication, source/core, SQL static, executor and exact-policy suites
conclusion: code repair partial; live publication remains blocked
status: R7_CODE_PARTIAL_PASS
sql_static: PASS
pg_live_read: READ_ONLY_CONFIRMED_SCHEMA_BLOCKED
pg_isolated: NOT_RUN
pg_production_write: NOT_AUTHORIZED_NOT_RUN
core_ready: BLOCKED
page_parity: BLOCKED
daily_e2e: BLOCKED_OFFICIAL_SOURCE_BINDING_DIGEST_MISMATCH
ci: PASS_PUSH_AND_PR_RUNS
production: UNCHANGED
approval_status: no authorization for production writes, Head switch, 28765 deployment or history rewrite
---

# V4 PG 日发布 R7 修复阶段报告

## 阶段范围与结果

按 R7 任务卡修复 R6 独立外审阻断。执行前确认工作区干净，当前分支 `codex/v4-workspace-cleanup`，冻结审计基线与起始 HEAD 均为 `54959fa02af5f7aa73a931c8e610e07ed4501f6d`。本轮先查阅 R7 任务卡、R6 综合报告、现役 publication/source manifest migrations 及适用的 R8 来源合同和运行时修复规范。只涉及日发布链；未启动 scanner，因此阶段 0 不适用。

- **来源写入与事务（代码修复）**：迁移 037 和 source writer 改用物理身份 `publication_id`、版本 `revision_no`，消费来源键为 `(publication_id, source_key)`。事务路径以稳定 advisory lock、防重放核对和 savepoint 冲突回滚处理并发/冲突，避免异常冲突后留下部分写入。公共入口和私有事务入口均要求独立 authority verifier；当前 verifier 未配置，伪造或自哈希 `ACCEPTED` 计划在任何 SQL 前被拒绝。Fake PG 测试只验证保存点回滚机制，不表示生产来源已获接受。
- **来源独立证明（安全关闭）**：readiness 必须使用现役 `V4_DAILY_SOURCE_READINESS_V2`，T0 与 freeze SHA 精确匹配。调用方自建回执只证明自身字节，不构成独立接受权威；没有 authority 时写入关闭。
- **Core Reader 与 Head Planner**：Reader 逐项重建 publication consumed source manifest、source revision、package/fact 绑定及 TDX 行来源，并校验 producer receipt 与 rowset digest。Reader 输出为 typed PG readback 对象；其 receipt 覆盖 planner 消费字段，`dataclasses.replace` 改写会被拒绝。数据库内 `PASS` 只作为观测状态；缺少独立审核的现役 completeness contract 时，有效状态保持 `CONTRACT_UNRESOLVED`、`publishable=false`，Planner 不生成可接受 Head 计划。
- **迁移 036/037**：修正旧 `revision` / 消费来源字段用法，改用现役 publication id 与 revision_no 语义。新增静态检查覆盖迁移和 writer 关键列。迁移仅做静态核对，未向任何数据库执行 DDL。
- **E2E / CI**：旧 policy 子集 fixture 不再绕过完整 component closure。E2E 将已签入 policy 及 66 条 accepted algorithm、604 条 component source 字节原样复制到 G 盘临时目录；在原始 bytes 下验证官方闭包，并断言失败时 Head 字节不变且 `promote` 未被调用。测试证明失败关闭，**不证明日发布成功**。CI focused suite 新增来源/core/SQL 静态和 executor regression。

## 真实数据与数据库证据

2026-10-12 已保存 source freeze 与现役 readiness 文件的 T0、SHA 绑定匹配。source adapter 实际读入 **5,212 条 TDX 日线**，结果为 `DIAGNOSTIC_ONLY / SOURCE_PIT_AUTHORITY_UNAVAILABLE`；freeze/readiness 的 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`。数据未被改写、补标或提升。该业务链没有独立接受回执，也没有接入 PG publication/core writer，因此尚未形成真实 PG core rows、Publication 或页面读回闭环。

PG 使用现有 `WORKBENCH_PG_DSN` 做事务级只读 SELECT，事务首句 `SET TRANSACTION READ ONLY`；数据库身份为 `market_research`、`127.0.0.1:5432`，连接角色 `postgres` 且为 superuser（只读事务，不是最小权限角色）。观察到：`source_packages=0`、`source_revisions=40,455`、`publication_consumed_sources=0`、`publications=0`、`publication_heads=0`、`market_calendar_sessions=0`。Live schema/迁移账本不含 034/035 及本轮 036/037 的已执行结果；无 R6 core relations。没有执行 PG DDL/DML、source ingest、core row 写入、Head CAS 或服务启动。

另核实官方 policy source closure 有已提交 stale hash：`data/v4/runtime_repair_sources_r1_1/59c29bd5ea5a591995dea12675c4191b3277d9d240d180c57eaf15bc6e690fc6/config/v4_operational_new_listing_r1.json` 实际受版本控制内容为 833 bytes、SHA256 `8dda3cba15f930c91e41e151604eab90c728f0a4c4768cb0bbc49d1364a52bae`，而 policy 声明 `59c29bd5ea5a591995dea12675c4191b3277d9d240d180c57eaf15bc6e690fc6`。这不是换行差异。本轮未改 policy、hash 或归档源；官方准入在 `CORRECTED_INPUT_DIGEST_MISMATCH` 失败关闭。

## 验证

本地 focused 命令覆盖 PG candidate、owners、contracts、source manifest、R6 source/core、R7 静态 SQL schema、operational executor、pre-next T0 chain 和 exact daily policy：**79 passed in 6.82s**。使用 `G:/codex_tmp/test_temp/r7_local_final2`。其他记录：核心/Planner 定向 **41 passed**；source/schema 定向 **6 passed**；`git diff --check` 通过；`tools/git_repository_policy.py --staged` 对首个 13 个变更 blob、随后修正的 1 个测试 blob 均通过。未执行全仓库全量测试。

- 代码提交：`b887755f6fe508779ab0c67a8851427dd400959a`（R7 核心修复）及 `1b51078b2e1f433152cf12c9ff0249e8ce9e206f`（optional capture 跨平台回归断言修正），均已推送至 `codex/v4-workspace-cleanup`。
- GitHub Actions push run [38868165122](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38868165122)：admission 与 `v4-pg-publication-candidate` 均通过。前一提交 `b887755f6fe508779ab0c67a8851427dd400959a` 的首次 CI 因两个测试错误要求 optional candidate 必须产出而失败（77 passed, 2 failed）；已修正测试以接受明确的非阻断 candidate failure，并在 `1b51078...` 上重跑通过。
- GitHub Actions PR run [38868171069](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38868171069)：admission 与 `v4-pg-publication-candidate` 均通过。

## 状态矩阵与剩余阻断

| 维度 | 状态 | 证据 / 阻断 |
|---|---|---|
| CODE | `R7_CODE_PARTIAL_PASS` | SQL 字段、来源写入防伪与回滚、Reader/Planner 防伪及 executor regression 已修复并通过 focused tests。 |
| SQL_STATIC | `PASS` | 036/037 与现役 publication 字段静态一致；没有数据库 DDL 编译或执行证据。 |
| PG_ISOLATED | `NOT_RUN` | 无获准隔离 PG 写入/迁移环境；迁移未实跑。 |
| PG_LIVE_READ | `READ_ONLY_CONFIRMED_SCHEMA_BLOCKED` | 只读事务读取；live 缺 034–037、core relations 和 publication 行。 |
| PG_PRODUCTION_WRITE | `NOT_AUTHORIZED_NOT_RUN` | 未尝试写生产 DB。 |
| CORE_READY | `BLOCKED` | 真实 freeze 非 PIT，权威接收器与完整性门槛合同均缺失；无真实 PG 行生产者接线。 |
| PAGE_PARITY | `BLOCKED` | 默认页面 handler 尚未连接 publication-bound 核心读回；无可验证 publication 数据。 |
| DAILY_E2E | `BLOCKED_OFFICIAL_SOURCE_BINDING_DIGEST_MISMATCH` | exact bytes E2E 通过的是安全拒绝路径，Head 不变且无 promote。 |
| CI | `PASS_PUSH_AND_PR_RUNS` | 最终代码提交 push 与 PR run 的 admission、focused jobs 均通过。 |
| PRODUCTION | `UNCHANGED` | 未执行 PG 写入、Head 切换、28765 部署、服务/调度切换或生产数据操作。 |

下一步需先由正式来源权威维护方修复并重新审核 stale policy source binding，再取得独立接受回执和已审计 completeness contract；随后需对 034–037 在获准隔离 PG 实际编译/迁移与事务重放验证，接通真实生产者、Publication、页面读取，并通过真实日更 E2E。生产 PG 写入、正式 Head 切换、28765 部署仍须单独授权。

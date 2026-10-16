---
stage_id: V4_R13_POST_CLOSE_PIT_UNIVERSE_GATE_20261016
code_sha: e1b42387807ea985c9fb42371cd2923c1fbf0719
test_scope: r12-v4-scoped-regression-plus-r13-clock-and-downgrade-boundaries
conclusion: DEGRADED_PASS_CODE_REPAIRS_COMPLETE_LIVE_PUBLICATION_BLOCKED
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# 大A V4 R13 盘后 PIT、R3 降级与 Universe 发布门阶段报告 R1

日期：2026-10-16。依据 Drive 任务 `V4_R12独立外审_R13盘后PIT与Universe正式发布门修复任务_R1_20261016.md`。冻结输入分支 `codex/v4-workspace-cleanup`，基线 HEAD `773cba98e900728500a888e678a3d0ea220bf0ce`。本轮保留已有 R12 修改与工作区无关文件；提交前 SHA 在最终 CI 更新中补录。

适用升级文档：`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、`docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`、`reports/stage/V4_SOURCE_UNIVERSE_PG_COMPREHENSIVE_TEST_REPORT_20261016_R12.md`。新增正式合同说明：`docs/upgrade/V4_R13_POST_CLOSE_PIT_UNIVERSE_PUBLISH_GATE_R1_20261016.md`。

## 本轮修复

- Acceptance receipt 升为 `V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R3`，新增 `V4_DAILY_PIT_DECISION_CLOCK_R1`。签名绑定 decision session、下一交易日和日历 SHA；强制观测、readiness、接受、签发、决策截止因果顺序和明确上海时区时段。15:15 首次观察、15:18 readiness、15:20 接受、15:25 签发可用于 T0 盘后；T+1 盘前必须使用签名的下一交易日和 09:30 前截止。缺字段、早于源/ready 时钟或超出会话窗口关闭准入。
- 新 T0 的 R2 降级门以 2026-10-16 为有效日期，分别在 Core、Candidate 和 PG migration 041 生效；历史 R2 兼容读取不回写。
- 新 T0 Core typed readback 显式输出 `BLOCKED_UNIVERSE_READBACK_NOT_PERSISTED`，Candidate 与 Head 要求 Universe 合同 PASS 和摘要。现有 PG schema 未持久化可重验的 snapshot 行及逐证券 reconciliation，因此所有新 T0 的正式发布仍关闭；没有把 caller 标签或 5,100 条合成样例当作真实 Universe 通过。
- 迁移 041 注册到阶段迁移 runner 与静态 preflight。没有执行该 SQL，也没有创建隔离数据库。

## 验收矩阵

| 范围 | 状态 | 证据与边界 |
|---|---|---|
| CODE | `PASS_CODE` | Core/Candidate R2 effective-date guards、041 trigger、R13 report/spec 已编写。 |
| TIME_PIT | `PASS_FIXTURES / BLOCKED_LIVE_AUTHORITY` | T0 盘后、T1 盘前、签发早于 cutoff、首见前决策和旧 T0 回写测试；实际 issuer 与官方日历数据未授权/接线。 |
| SOURCE_AUTHORITY | `BLOCKED` | `config/v4_daily_source_acceptance_authorities_r1.json` 的 `issuers` 为空；测试私钥只在 fixture 内生成。 |
| MANIFEST_R3 | `PASS_CODE / BLOCKED_LIVE_PG` | 新 T0 R2 拒绝覆盖 Core、Candidate、SQL trigger；真实数据库未编译/应用 041。 |
| UNIVERSE_RULE | `PASS_FIXTURES` | 现役独立分母模块覆盖缺失/额外证券、范围及身份分类；fixture 不代表任何真实 T0。 |
| UNIVERSE_PUBLISH_GATE | `PARTIAL_FAIL_CLOSED` | 新 T0 Core→Candidate→Head 不能越过缺失的 PG Universe snapshot/readback proof；正向可发布证明尚未实现。 |
| PG_STATIC | `PASS_INVENTORY_ONLY` | G 盘只读 preflight：42 个 SQL 文件，重复序号 `[10]`，041 纳入依赖链；证据 `G:/codex_tmp/v4_r13_preflight/V4_R12_PG_MIGRATION_READONLY_PREFLIGHT_R1.json`。这是文件清点，不是 12 条现场 ledger 逐对象对账。 |
| PG_ISOLATED | `NOT_RUN` | 未创建实例或执行 DDL/DML。 |
| PG_LIVE | `BLOCKED_NO_READER_DSN` | 环境未提供 `WORKBENCH_PG_DSN` / `V4_NATIVE_PG_READER_DSN`；不会使用 R12 已识别的 postgres superuser。只观察到一个 5432 listener；无 PG 查询、写入或迁移。 |
| OWNER | `BLOCKED_NO_AUTHORIZED_ROOT_MAPPING` | `config/v4_pg_workspace_owner_authority_r1.json` 显示映射列表为空；没有为三类可选 Owner 推测 sector membership、Forward、Focus、Cohort 或 Settlement。 |
| WORKSPACE | `BLOCKED_NO_AUTHORIZED_MAPPING` | 不创建根映射或 namespace 授权；缺少只读现场证据及批准来源。 |
| SEVEN_API | `NOT_RUN_REAL_RESULTS` | 28765、28766 均无监听服务；无 reader DSN，不能将合成 HTTP 结果冒充真实 API 结果。 |
| BROWSER | `NOT_RUN` | 未打开或模拟浏览器页面。 |
| PERFORMANCE | `NOT_RUN` | 无真实数据、实际 PG readback 或服务进程可测；未声明日增量、MA/Profile、Sector/Focus/Forward 性能达标。 |
| HEAD | `BLOCKED` | 新 T0 受 R3 与 Universe readback 门禁；未修改 Head。 |
| PRODUCTION | `UNCHANGED` | 28765 未运行/未触碰；未启动 28766、未调度、未改 PG、未部署。 |
| CI | `PASS` | code SHA `e1b42387807ea985c9fb42371cd2923c1fbf0719` 的 push run [38917838340](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38917838340) 与 PR run [38917847186](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38917847186) 均通过 `admission`、`v4-pg-publication-candidate`。stage report-only commit 的 CI 将在提交后再核对。 |

## 测试

在 `G:/codex_tmp` 设置 `TMP/TEMP/TMPDIR`，Python 使用现有 E 盘解释器；为适配运行时缺少的 cryptography、duckdb、psycopg 依赖，新增测试依赖仅安装到 `G:/codex_tmp/r13_deps`。命令：

```text
python -m pytest --confcutdir=tests -q -p no:cacheprovider \
 tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py \
 tests/test_v4_pg_publication_contract_static.py tests/test_v4_pg_source_manifest.py \
 tests/test_v4_daily_ingest_r6.py tests/test_v4_market_universe_completeness_r1.py \
 tests/test_v4_daily_core_result_r6.py tests/test_v4_r7_sql_schema_compatibility.py \
 tests/test_operational_daily_executor_v1.py tests/test_pre_next_t0_executor_chain.py \
 tests/test_v4_exact_daily_policy_v2.py tests/test_v4_r8_real_daily_executor_pg_bridge.py \
 tests/test_v4_r8_isolated_schema_runner.py tests/test_v4_native_reader_dsn.py \
 tests/test_v4_current_accepted_reader.py tests/test_v4_server_pg_candidate_mode.py \
 tests/test_v4_r12_migration_readonly_preflight.py
177 passed
```

测试全为定向 V4 代码/fixture 检查；不能证明 SQL 在 PostgreSQL 可编译、PG catalog/ledger 对账、真实 issuer、Universe 生产数据、网页结果或 Head 发布条件已满足。

## 下一阶段

在任何正向 Head 验收前，先提供非 superuser 只读 PG 身份，逐对象 reconcile 12 条 migration ledger 与 catalog/前置关系；实现 Universe snapshot 和 reconciliation 的签名来源绑定、PG 持久化及 Core 只读重算；提供被批准的实际独立 issuer 与日历；再接线真实 Workspace/Owner、同一 publication/T0/namespace 的七页结果并测真实性能。以上不授权迁移写入、Head 切换、28765 部署或调度。

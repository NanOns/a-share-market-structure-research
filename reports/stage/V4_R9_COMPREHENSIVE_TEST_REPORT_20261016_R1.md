---
stage_id: V4_R9_COMPREHENSIVE_20261016
code_sha: 3e831fd0d850787dab17866e3d51fe2584513aa7
baseline_sha: 7c837c26fbee636ec691cb02aaff974d610e8b45
branch: codex/v4-workspace-cleanup
scope: R9 daily PG publication, Workspace identity, Owner producers, seven current page consumers, reader DSN safety, runtime audit
test_scope: targeted native DSN, daily core result, PG candidate/Owner/static regression; current file-reader verification; bounded PG closeout attempt
conclusion: code partial pass; live daily publication, Owner binding, and page parity blocked
status: R9_CODE_PARTIAL_PASS
pg_live_read: READ_ONLY_SCHEMA_DRIFT_CONFIRMED
pg_isolated: NOT_RUN_NOT_AUTHORIZED
pg_production_write: NOT_AUTHORIZED_NOT_RUN
source_authority: BLOCKED_NO_INDEPENDENT_ACCEPTANCE_RECEIPT
core_ready: BLOCKED_NO_ACCEPTED_SOURCE_OR_PG_ROWS
pit: BLOCKED_SOURCE_EVIDENCE_NOT_PIT_ELIGIBLE
daily_e2e: BLOCKED_NO_PUBLICATION_OR_HEAD
page: NOT_VERIFIABLE_NO_PUBLICATION_OR_SERVICE
ci: PENDING_AFTER_PUSH
production: UNCHANGED
approval_status: no authorization for production PG writes, accepted Head switch, 28765 deployment, isolated PG writes, physical cleanup, or history rewrite
---

# V4 R9 综合推进报告 R1 — 2026-10-16

## 范围与基线

- 正式任务：`V4_R8审计及Workspace_Owner改造_R9综合任务_R1_20261016.md`（Google Drive ID `1AwMOCTsvyMwv8Z_ZW5MofxSnIi5cNeH7`）。执行前核对远端 `codex/v4-workspace-cleanup` 仍为冻结 HEAD `7c837c26fbee636ec691cb02aaff974d610e8b45`，本地与远端一致、工作区干净。
- 查阅适用升级文档 `docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、R8 阶段报告和仓库治理合同。范围限现役 V4；不启动扫描器，阶段 0 不适用。
- 分支继续使用既有治理分支 `codex/v4-workspace-cleanup`。未新建 worktree、克隆或其他源码目录。过程测试临时目录为 `G:/codex_tmp/test_temp/v4_r9`。

## 实施与验收状态

| 范围 | 状态 | 本轮证据/结果 |
|---|---|---|
| Reader DSN 回退 | **CODE PASS** | `v4_native.configured_reader_dsn()` 现仅按 `V4_NATIVE_PG_READER_DSN → WORKBENCH_PG_DSN` 选择；无 reader 配置时明确失败，不读取 `V4_NATIVE_PG_DSN`。连接策略合同升为 R2，新增 writer-only 和优先级负样本。 |
| 39 个换行绑定 | **PARTIAL** | 66 算法与 604 组件绑定中，631 项原字节匹配，37 项整文件 LF→CRLF 可复算，2 项混合换行不能从现有证据重建。当前证据只定位到归档字节表示差异，不能判断转换环节或归因于 `core.autocrlf`。未修改历史绑定、来源文件或 SHA。 |
| 日更 source→PG ingest | **BLOCKED** | 执行器实际 freeze/readiness 仍送入只诊断计划；真实历史证据 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`。独立接受权威 verifier 未配置，不能创建合法新 T0 的 accepted package/revision。 |
| 核心日线、MA/Profile→Publication | **BLOCKED** | `v4_daily_core_result_r6.py` 有真实生产者结果绑定计划和严格 PG 只读读回，但没有日更 executor 的 PG 写入者。迁移 037 未执行、live core relations 不存在；不能把 mock/plan 包装成发布。 |
| Publication / Head / 日更 E2E | **BLOCKED** | PG `source_packages=0`、`source_revisions=40,455`、`publications=0`、`publication_consumed_sources=0`、`publication_heads=0`。无合法 Publication/Head 可读回，也未执行 Head CAS。 |
| Owner 绑定 | **PARTIAL** | 3 个已有 PG Owner producer/reader 存在，均属可选能力，尚无 live publication binding：`research_priority`→radar；`operational_risk`→summary/health；`sector_lifecycle`→sector/health 补充。没有据此制造全局必需 Owner。 |
| Forward / Focus / Cohort / Settlement | **PARTIAL** | 各自有 PG 或 append-only 存储路径、T0/token/来源绑定及读回；尚未统一绑定到 publication_module_results。Cohort/Settlement 无正式 publication-bound relation；Focus/Forward 现有产物不能冒充日更 Owner。 |
| 七页 API/UI | **BLOCKED** | `PgV4CurrentAdapter` 有七路候选投影，但现役 `v4_server.py` `/api/v4/current/*` 仍使用 `CurrentAcceptedV4Reader` 文件 Head。没有 PG publication 或真实页面读回；28766 本轮未启动。 |
| Workspace/PG 身份 | **PARTIAL** | 当前主仓为唯一开发目录。root-derived schema `v4_workspace_dbe184da961f97b8` 在 PG 中不存在；历史 `v4_jobs_*`、`v4_research_*`、`v4_forward_*` 为不同 namespace，owner 为 `v4_closeout_producer_20261012`。目录迁移与旧 Owner 的稳定身份尚无映射闭环。 |
| 运行空间/端口 | **PARTIAL** | 唯一主仓与当前分支已核实；旧 C 盘 worktree `C:/Users/lps/.codex/worktrees/f46d/大A交易` 仍为 detached/prunable，本轮未触碰；归档 ZIP CRC 本轮未重新复核。5432 由 PID 8260 的一个 PostgreSQL 进程监听；28765、28766 无监听。 |

## PG catalog 只读核验

经现有 `WORKBENCH_PG_DSN` 连接，并在连接与事务上强制只读。本机身份为 `market_research`、`127.0.0.1:5432`、角色 `postgres`；事务 `transaction_read_only=on`，但角色是 superuser，不能证明具备最小权限。迁移台账缺 034–037，`source_package_facts`、`daily_core_result_snapshots`、`daily_core_result_rows` 不存在，`v4.publications` 缺 source manifest 新列。未执行任何 PG DDL/DML。

## 定向验证

- `python -m pytest -q -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/v4_r9 tests/test_v4_native_reader_dsn.py tests/test_v4_daily_core_result_r6.py tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py`：**76 passed**。
- `git diff --check`：通过。
- `tests/test_v4_current_accepted_reader.py`：**8 passed, 3 failed**。失败均为现有文件来源校验/投影：`BOUND_ARTIFACT_DIGEST_MISMATCH:data/v4/confirmation_candidates_r5/D2_2026-09-30_CANDIDATE_R5.json.gz`，导致 WAIT_NEXT 返回 409、实体无行和深链接 token 不返回。本轮未改写或重新生成该只读绑定文件。
- 曾尝试更宽的 PG closeout 回归集合：**79 passed, 9 failed**。失败项尝试创建临时 PG Owner/快照，但环境没有 `V4_NATIVE_PG_DSN`，均在取得连接前失败关闭；其中一项依赖未建立的 owner fixture。未将 `WORKBENCH_PG_DSN` 写连接回退，也未执行隔离 PG DDL/DML。该结果不是隔离 PG 验收。
- 全仓测试及 GitHub CI 的最终 SHA 结果将在推送后补录；定向测试通过不代表发布通过。

## 明确未执行 / 下阶段

未写生产 PG、未执行隔离 PG 写入、未切换正式 Head、未启动/切换 28765、未删除旧工作区、未强推历史。当前判定：`R9_CODE_PARTIAL_PASS / PG_LIVE_READ_ONLY_CONFIRMED_SCHEMA_BLOCKED / DAILY_PUBLICATION_BLOCKED / PAGE_PARITY_NOT_VERIFIABLE / PRODUCTION_UNCHANGED`。

下一阶段须先取得：独立来源接受/PIT authority；批准后的隔离 PG DDL/DML 测试范围与清理责任；034–037 生产 schema 漂移处理计划；核心 producer 的明确完整性合同；并行保留的七页 API 接入设计和正式 page readback 证据。生产 PG 写入、正式 Head、28765、物理清理和历史强推仍需各自授权。

---
stage_id: V4_R18_FINAL_DELIVERY_20261016
code_sha: b0c74302787415ac7e05b3f629b3a20fed21f5dc
test_scope: current-v4-r6-r18-targeted-publication-source-pg-owner-api-universe-regression
conclusion: FIVE_CODE_STAGES_COMPLETE_LIVE_PG_SOURCE_BROWSER_AND_PRODUCTION_ACCEPTANCE_BLOCKED
approval_status: CODE_TEST_COMMIT_PUSH_AND_GITHUB_REPORT_AUTHORIZED
---

# 大A交易 V4 R14—R18 五阶段连续交付报告 R1

日期：2026-10-16（Asia/Shanghai）。分支：`codex/v4-workspace-cleanup`。冻结起点 `2be2ed143b0f4e8916e7f1ccabf378f48fd92131`。本报告把阶段代码/测试、PG 验收、来源/PIT、页面真实结果和生产启用分开；R14—R18 是本轮执行包，不代表产品原22阶段完成。

## 五阶段代码交付

| 阶段 | 代码提交 | 交付与路径 |
|---|---|---|
| R14 | `18b06d1421fbc7ef9aa32781abf76a293537e151` | `src/workbench_db/v4_universe_pg_r1.py`: 原始事实/包签名绑定、append-only writer/readback；`042_market_universe_persistence_r1.sql` 注册；`v4_daily_core_result_r6.py`、`v4_publication_candidate.py` 把封闭 Universe readback 能力摘要绑定进 Core/Candidate/Head；R14 合同与报告。 |
| R15 | `c43d0678ddd0ee33038b8fb5c1e9e09b5dd238b6` | 完整 43 文件 migration 名称/SHA/依赖/静态对象/风险和 live `NOT_VERIFIABLE` 差异清单；reader/writer/migration 权限、一次批量迁移授权申请；更新静态清点测试适配 042。 |
| R16 | `0473cbb8486370a8cd03fa2a61bbff99f28a03b7` | `V4_DAILY_PIPELINE_PROGRESS_R1` 包装 `execute_sources`/`derive_ready_sources` 既有 checkpoint，记录耗时和计数；定向 Executor 说明及测试。该计时为 checkpoint interval，不是隔离阶段基准。 |
| R17 | `5ae62167a4722051764103c92867e2b58c3d4d8a` | `PgV4CurrentAdapter` 以 publication-bound rows 显示 `DEGRADED` partial result；新增七 API→Owner/PG relation/字段/UI 血缘矩阵与回归断言。 |
| R18 | 本报告最终提交 | 补齐 R8 isolated-schema plan runner 与测试对完整已注册 001–042 链、43 个文件和两个独立 010 的识别；添加性能/故障恢复矩阵和本总报告。未运行其 `--apply`。 |

## 测试与 CI

- R14 聚焦测试：Universe PG、market universe completeness、Core、Publication candidate，`86 passed`。
- R15 静态 migration/schema suite：migration preflight、SQL schema compatibility，`5 passed`；更新 42→43 计数并覆盖 042。
- R16 Executor/source/progress/recovery suite：`20 passed`。初次环境未加载既有 G: 临时依赖 overlay 时 collection 缺 `cryptography`；使用本项目已有 overlay 重跑通过。
- R17 Publication Candidate/Owner/page contract/server candidate suite：`73 passed`。这不是启动 HTTP 服务或浏览器证明。
- R18 现役 V4 定向回归命令（CI 当前基础清单 + R14/R16新增与迁移静态合同）：

```text
python -m pytest --confcutdir=tests -q -p no:cacheprovider \
 tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py \
 tests/test_v4_pg_publication_contract_static.py tests/test_v4_pg_source_manifest.py \
 tests/test_v4_daily_ingest_r6.py tests/test_v4_daily_core_result_r6.py \
 tests/test_v4_r7_sql_schema_compatibility.py tests/test_operational_daily_executor_v1.py \
 tests/test_pre_next_t0_executor_chain.py tests/test_v4_exact_daily_policy_v2.py \
 tests/test_v4_r8_real_daily_executor_pg_bridge.py tests/test_v4_r8_isolated_schema_runner.py \
 tests/test_v4_native_reader_dsn.py tests/test_v4_current_accepted_reader.py \
 tests/test_v4_server_pg_candidate_mode.py tests/test_v4_universe_pg_r1.py \
 tests/test_v4_market_universe_completeness_r1.py tests/test_v4_daily_pipeline_progress_r1.py \
 tests/test_v4_r12_migration_readonly_preflight.py tests/test_dd_r21_source_orchestration.py \
 tests/test_v4_r14_governance_contracts.py
```

R18 汇总：`210 passed, 3 failed`。3 个失败均在既有 `test_v4_r14_governance_contracts.py` 针对 2026-10-12 固定历史 Head 运行；受保护证据声称 `scripts/validate_v4_12_r11_chain.py` 为 9,383 bytes / SHA `ab76426fba950a58ba4a38ae144084801082d784e508c1985120f00a5c1a167d`，当前冻结仓库文件为 9,564 bytes / SHA `72a97af013b7c87e70be16c6dbdcc3741ca7acfca3a927bf52b61f34a5515a9c`。因此 exact scoped promotion、zero mutation repeat 和 full contract completeness 这3项失败均由历史证据字节绑定不一致触发；本轮没有改历史 Head/数据/校验器去掩盖它们。首轮 R18 还发现 isolated runner 把 041 写死为最后迁移；已修复为完整注册链 042，并在复跑中通过。

- R18 code/report SHA `b0c74302787415ac7e05b3f629b3a20fed21f5dc` 的 push CI [38926147348](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38926147348) 与 PR CI [38926155126](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38926155126) 均通过 `admission` 与 `v4-pg-publication-candidate`。报告证据补录形成的后续 closeout SHA 及其 CI 将记录在 Issue #2 / Draft PR #3 最终更新中。
- 测试全在 G: 临时路径保存缓存；没有运行 7,000+ 旧版测试/M14。

## 按阶段 × 任务卡验收状态

`PASS` 表示代码/静态/定向回归；`PARTIAL` 表示有限字段或 checkpoint 能力；`BLOCKED` 表示缺少实际来源/身份/PG能力；`NOT_RUN` 表示未做实际操作。

| 验收维度 | R14 | R15 | R16 | R17 | R18 |
|---|---|---|---|---|---|
| CODE | PASS | PASS | PASS | PASS | PASS_WITH_3_HISTORICAL_EVIDENCE_FAILS |
| SOURCE_REAL | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| PIT_REAL | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| UNIVERSE_PERSISTENCE | CODE_PASS_PG_NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| UNIVERSE_READBACK | CODE_PASS_PG_BLOCKED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| PG_STATIC | PASS_042_REGISTERED | PASS_43_FILE_STATIC_INVENTORY | PASS_INHERITED | PASS_INHERITED | PASS_001_TO_042_PLAN |
| PG_ISOLATED | NOT_RUN_NO_AUTHORIZATION | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| PG_LIVE | BLOCKED_NO_READER_WRITER_DSN | NOT_VERIFIABLE | NOT_RUN | NOT_RUN | NOT_RUN |
| OWNER_MAP | BLOCKED_EMPTY_AUTHORITY_REGISTRY | BLOCKED | BLOCKED | BLOCKED_NO_ROOT_MAP | BLOCKED |
| CORE_PROFILE | PARTIAL_CORE_BINDING_NO_LIVE_ROWS | NOT_RUN | PARTIAL_LOCAL_CORE_CANDIDATE | PARTIAL_ENTITY_PROFILE_FIELDS_MISSING | BLOCKED_LIVE |
| SECTOR_MEMBERSHIP | BLOCKED_NO_ACCEPTED_MEMBERSHIP | NOT_RUN | PARTIAL_LOCAL_PRODUCER_ONLY | BLOCKED_NO_PUBLICATION_BOUND_MEMBERSHIP | BLOCKED_LIVE |
| FOCUS_FORWARD | BLOCKED_NO_AUTHORITY | NOT_RUN | PARTIAL_CODE_PATH_ONLY | BLOCKED_NO_ACCEPTED_OWNER | BLOCKED_LIVE |
| COHORT_SETTLEMENT | BLOCKED_NO_PUBLICATION_RELATION | NOT_RUN | PARTIAL_CAPTURE_READINESS_ONLY | BLOCKED_NO_PUBLICATION_RELATION | BLOCKED_LIVE |
| API_SEVEN | NOT_RUN | NOT_RUN | NOT_RUN | CONTRACT_PARTIAL_NO_REAL_RESULTS | E2E_PARTIAL_NO_PG |
| BROWSER | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN_NO_SERVICE | NOT_RUN |
| PERF | NOT_RUN | NOT_RUN | CHECKPOINT_TIMING_ONLY | NOT_RUN_REAL_DATA | SYNTHETIC_MATRIX_ONLY_NO_REAL_BENCHMARK |
| HEAD | BLOCKED_UNIVERSE_PROOF_REQUIRED | NOT_CHANGED | NOT_CHANGED | NOT_CHANGED | NOT_CHANGED |
| PRODUCTION | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED | UNCHANGED |

Current least-privilege read/write DSNs and approved authority are absent; 5432 is the only observed PG listener, and 28765/28766 have no listener. No database query, DDL/DML, service start, browser E2E, accepted Head CAS, production schedule, or deployment occurred. Real performance, SQL compile in PG, data lineage through a live accepted Publication, and isolated rollback remain unverified.

The pre-existing untracked `.githooks/pre-push` hook was preserved and not staged; no other worktree changes were left by this task.

## Code readiness versus live acceptance

- **Code ready:** `PARTIAL_PASS` — R14–R18 code, contracts, static migration mapping, UI lineage, recovery/performance matrix, and focused regressions are delivered; the three immutable historical evidence failures remain visible.
- **Isolated PG ready:** `BLOCKED` — no explicit isolated target/write authorization, credentials, backup or recovery window; migrations were not applied.
- **Real daily ready:** `BLOCKED` — no independent approved issuer/calendar, accepted real T0 package, separately accepted security Universe, or production role set.
- **Production ready:** `BLOCKED` — no real PG persistence/readback, seven-page browser result evidence, measured real-day performance, accepted Head, or 28765 deployment/scheduling authorization.

## Remaining authorization bundle

A single consolidated request is in `docs/upgrade/V4_PG_ONE_BATCH_AUTHORIZATION_REQUEST_R1_20261016.md`; exact SHA for every forward migration is in `docs/upgrade/V4_PG_MIGRATION_CATALOG_DIFF_R1_20261016.md`. The request is for review only. Before any database operation, the user must authorize (1) a named isolated PG target, separate writer/reader/migration identities, exact migration SHA set, backup and restore evidence, execution window, rollback and independent verification; (2) source issuer/calendar ownership and key registration process; (3) formal Workspace root/model namespace/Owner mappings; (4) accepted Head CAS scope; and (5) separately scoped 28765 deployment/scheduling. No default permission is inferred.

## Original product 22-stage mapping

The R1 task card and repo documents available in this run do not define the original product 22 stage names/acceptance contracts. Entries 01–22 are therefore each `UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE`; R14–R18 are not substituted as product-stage PASS. The next action is to obtain the authoritative 22-stage contract together with the single authorization bundle, then re-evaluate only the dimensions those contracts require.

| Product phase entry | Mapping status |
|---|---|
| 01 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 02 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 03 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 04 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 05 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 06 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 07 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 08 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 09 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 10 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 11 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 12 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 13 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 14 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 15 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 16 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 17 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 18 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 19 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 20 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 21 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |
| 22 | UNVERIFIED_NO_FORMAL_22_PHASE_SOURCE |

## Final source SHA-256 manifest

The checksums below identify the source/test blobs in this final delivery (migration SHA also appears in the R15 full migration inventory).

| File | SHA-256 |
|---|---|
| `src/workbench_db/v4_universe_pg_r1.py` | `f952a07a5f279a08a74cb95797725321dbaf4bf7bb8acfcbe4bc073d08f45942` |
| `src/workbench_db/migrations/v4_postgres/042_market_universe_persistence_r1.sql` | `eb8e6791ed3b749537a880f725bf9d01b7d2c3681043e718dad6e9535096afa2` |
| `src/workbench_db/v4_daily_core_result_r6.py` | `25d00ab06ebe6af8e1795194dadc197f6d5b93cb4847eb533dd884a2e77e1d2d` |
| `src/workbench_db/v4_publication_candidate.py` | `0285f88e3120a4d6288808e7c2a9a00a5ad93ee43b0f450e35a9ea5ef4fe0a8f` |
| `scripts/apply_v4_phase0_schema.py` | `e45c9fac12f2ffde8ec18bbe0e76402c22fa608076959f9306cc3d627bf61e09` |
| `tests/test_v4_universe_pg_r1.py` | `315a0d07c1654013103bcc1773fde524522693d2b1192f21378f43ef3dc948f0` |
| `src/workbench_analysis/v4_daily_pipeline_progress_r1.py` | `40b8f7f66559069452e055ec332ffc88e7594df543b7f70fb7615573ba6ac279` |
| `src/workbench_analysis/operational_daily_executor_v1.py` | `6a87348b88b0842ccccc1a01c0d625c2b1d7842b0792fd15eadeae1a755e8328` |
| `tests/test_v4_daily_pipeline_progress_r1.py` | `1f9f7fd65ae5706a2fa67a889ee8f5418e0a5f3ef6574730c20e74239b4648b5` |
| `src/workbench_service/v4_pg_current_adapter.py` | `97be8ba6623f7e2fae4a0cbd78cedfb3c2d880d4daa41ede56845dd8499de65d` |
| `tests/test_v4_pg_publication_candidate.py` | `04001a7b895dba67d2fe69f020b432fa6dd3bd5c47113f9c01b327bfed320dc5` |
| `scripts/validate_v4_r8_isolated_schema.py` | `2ab2485982f61c5c5b8d8e5e2077c9b5eb2f50821ab90dd2160c6711090ca8cd` |
| `tests/test_v4_r8_isolated_schema_runner.py` | `487673ce90209785d7b4f93c68e515c98acbf65ecc69065db13e7b7a60e0ed65` |

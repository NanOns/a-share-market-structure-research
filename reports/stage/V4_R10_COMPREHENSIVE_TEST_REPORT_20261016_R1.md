---
stage_id: V4_R10_COMPREHENSIVE_20261016_R1
code_sha: e14ed450c
baseline_sha: 0eb2392f2a4a9666bd11f17b261dcfd4d98ce2e1
branch: codex/v4-workspace-cleanup
scope: R10 current Reader recovery and CI, explicit PG candidate BFF, Workspace identity, Owner/page projection states, daily Core producer bridge and controlled writer, read-only PG/schema audit
test_scope: V4 PG candidate/Owner/source/core/executor regression plus 12 current Reader cases, native PG reader guards, and fixed-port 28766 synthetic HTTP routes
conclusion: substantial code and regression pass; live PG publication, PIT authority, production role and seven-page readback remain blocked
status: R10_CODE_PASS_PG_AND_PAGE_ACCEPTANCE_BLOCKED
file_reader: PASS_390_OF_390_BOUND_ARTIFACTS_EXACT
workspace: PARTIAL_ROOT_SCOPED_IDENTITY_NO_AUTHORITY_MAPPING
owner_map: PARTIAL_THREE_OPTIONAL_FAMILIES_NO_LIVE_BINDINGS
pg_reader_role: CODE_GUARD_PASS_LIVE_ROLE_SUPERUSER_REJECTED
prod_core_wiring: PARTIAL_REAL_OWNER_PLAN_BRIDGE_AND_CONTROLLED_WRITER_NO_LIVE_PLAN
source_authority: BLOCKED_NO_ACCEPTED_SOURCE_PACKAGE_OR_PIT_RECEIPT
pg_schema_static: READ_ONLY_SCHEMA_DRIFT_CONFIRMED
pg_isolated: NOT_RUN_NOT_AUTHORIZED
pg_live: READ_ONLY_NO_PUBLICATION_OR_CORE_RESULT
e2e_neg: PASS_DIGEST_MISMATCH_FAIL_CLOSED
e2e_pos: BLOCKED_NO_ACCEPTED_SOURCE_OR_PUBLICATION
http_28766: PASS_SYNTHETIC_SEVEN_ENDPOINT_HTTP
ui_seven: PARTIAL_API_WIRED_NO_REAL_PG_OR_BROWSER_PARITY
ci: PASS_PUSH_AND_PR_38885076598_38885083695_141_PASS_1_SKIPPED
production: UNCHANGED_28765_NOT_LISTENING_NO_PG_WRITE
approval_status: no authorization for production/isolated PG writes, migration, accepted Head, 28765 deployment, physical cleanup, or history rewrite
---

# V4 R10 实质修复与验证报告 R1 — 2026-10-16

## 范围和基线

- 正式任务：Google Drive `1IUqI1XEUVLsaVgLIuhvjCKPTrB4gmnP9`，R10 当前读链、Owner/Workspace 实质修复。
- 开始前核对分支 `codex/v4-workspace-cleanup` 的本地及 origin HEAD 为冻结基线 `0eb2392f2a4a9666bd11f17b261dcfd4d98ce2e1`，无 tracked 改动；R10 主代码提交为 `26cf2e67efad4d42fa6f1f78622ce8d9e53ff6c6`，CI 精确 LFS 输入修正提交为 `f22e32ec7253f20bf187c06cfc8f854160d955be`；GitHub push/PR CI 已在 `6f60daa70b23f05e5dd57cec381b12f4c2e75e10` 成功。本报告为独立文档提交，最终报告 HEAD 以 GitHub Issue/PR 更新为准。
- 查阅适用升级合同 `docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、R9 阶段报告和仓库 `AGENTS.md`。本任务不启动扫描器，阶段 0 不适用。
- 仅在既有主仓开发；未创建 worktree、克隆、PG 实例或其他端口。过程测试临时目录均在 `G:/codex_tmp/test_temp`。

## 已完成的代码接线

1. **Accepted file Reader：** 两个坏掉的工作树 LFS pointer 用本地 Git LFS 缓存中与合同 SHA 相同的原始对象恢复，未改合同、Head、SHA 或断言。当前合同 390 个绑定全部通过路径、字节数和 SHA 核对；R10 Reader 文件现有 12 个用例全部通过。压缩原件证据：D2 为 12,539,130 bytes / `12a9aef662c540bbea47e1bb2f8a86378bf381863a3d80344fc27d259f1ace58`；STATE_EVENT 为 614,785 bytes / `7de481708462bda5073031a129bc147279dc9f2c7741c389f14a8fc6f99dcd58`。
2. **Reader 权限和 DSN：** `v4_native.connection(read_only=True)` 现在先执行 `SET TRANSACTION READ ONLY`，再核对目标 schema、超管/角色管理/建库/复制/BYPASSRLS、schema CREATE、关系写权限和 sequence 写权限。`PgPublicationReader` 同步拒绝这些高权限/可写能力。R9 reader DSN 优先级和 writer 无回退行为原样保留。
3. **七路现役 API 与工作台：** `make_v4_handler` 增加仅显式的 `source=pg_candidate` 分支；强制携带 `trade_date`、`model_namespace_id`、`context_token`，候选失败绝不回退文件 Reader。`serve_v4_candidate` 可从显式非密钥数据库身份 JSON 构造 `PgPublicationReader`，只绑定 `127.0.0.1:28766`。`v4-workbench.js` 支持 `?source=pg_candidate&trade_date=...&model_namespace_id=...&context_token=...`，七模块请求共享该 context，并展示字段缺失状态/Owner 读回；未启动服务，真实浏览器/PG readback 仍未发生。
4. **七页 Owner 消费：** 三个可选 PG Owner 映射仍为 `research_priority → radar`、`operational_risk → summary/health`、`sector_lifecycle → sector/health 补充`，且必须由同一 publication 绑定。新增 entity 真实读 `daily_core_result_snapshots/rows`：核验同一 publication/revision、T0、source revision 属于 consumed sources、每行 digest 和聚合 digest，随后投影 OHLCV、MA5/20/60、history/profile，并同 security_id 的 lifecycle 行关联；缺名称关系时显式标 `DATA_MISSING`。sector lifecycle 保留为独立补充，不再将 sector_id 误认 membership；member_count 和 algorithm_state 明确缺 relation。Cohort/Settlement 无 publication-bound relation；health 缺 replay/maturity。七页 UI 候选模式已接入，但 live PG/浏览器 parity 仍未验证。
5. **Workspace identity：** 增加不暴露路径的 `V4_PG_WORKSPACE_NAMESPACE_ID_R1`，把 root-derived schema、root identity SHA 和读写能力要求一起表达；测试确认两个不同根映射到不同 schema。PG 旧 schema 到新 G 盘主仓的授权映射未建立，不按日期或名称猜测。当前唯一主仓在 G 盘。旧 C 盘 worktree 只读状态为 detached/prunable，gitdir 指向不存在位置；未触碰或删除。
6. **日更生产者和 Core：** 现役 `operational_daily_executor_v1.derive_ready_sources` 在真实 `seal()` 后调用 Core plan bridge。该桥只从已封存的 `raw/core/profile/lifecycle` bindings 按 `(security_id, trade_date)` 读取和校验数据，并要求显式 publication/source receipt 才组装 `build_daily_core_result_plan` 输入；当前没有该权威上下文时显式返回 `BLOCKED_PG_PUBLICATION_CONTEXT_MISSING`，不生成假 source ID、Head 或 PIT 声明，也不做数据库 I/O。新增 `persist_daily_core_result` 受控 writer，要求显式 writer DSN、配置角色与当前数据库角色相同、非超管/无 DDL 能力、仅具备 Core 表 INSERT、匹配 CANDIDATE publication、PG statement-time PIT/source package 证明；不自动提交、不改 publication status、不改 Head。尚无合法 source receipt 或 live Core 表，故真实 plan 和写入均未运行。

## 测试和 HTTP 证据

- R10 初始综合定向回归为 142 passed。后续 Core→entity、sector Owner 状态和候选 UI/adapter factory 接线后，最终综合集合（15 个测试文件）为 **146 passed，0 skipped**，本地临时目录为 `G:/codex_tmp/test_temp/v4_r10_continuation_final`。
- Reader/DSN/HTTP 单独合并组：**29 passed**；收集分母分别为 Accepted Reader 12、DSN guard 15（参数化角色负例展开）、候选 HTTP 2。
- 合成 HTTP fixture 在允许的固定开发端口 `127.0.0.1:28766` 实际发起 HTTP GET：七个 endpoint 都命中候选 adapter；context 缺字段返回 400；未启用候选模式返回 404；无 accepted publication 返回 `PENDING_PG_HEAD`；文件模式仍返回 file Reader。测试关闭后服务线程退出。此为隔离 fixture，不代表真实 PG 或浏览器页面读回。
- `tools/git_repository_policy.py --staged`：通过（13 changed Git blobs）；`git diff --check`、所改 Python `compileall`、`node --check src/workbench_service/static/v4-workbench.js`：通过；续推代码 SHA 的 staged policy 通过（7 blobs）。
- 初始 SHA 的 push run [38885076598](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38885076598) 和 PR run [38885083695](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38885083695) 全部通过（141 passed、1 skip）。续推代码 SHA `ffe8723c9a48111bd23e94c7cb471fe5688ffcdb` 的 push run [38888775268](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38888775268) 和 PR run [38888782707](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38888782707) 的 admission 与 V4 scoped job 全部通过（145 passed、1 skipped）。唯一 skip 仍是 runner 缺少不入库的 2026-10-12 冻结 executor 文件；Accepted Reader、native DSN、HTTP 与新增 Core/sector tests 均在 CI 执行。
- 一次额外触碰 `tests/test_v4_embedded_owner_reader_integration.py` 的 PG 写测试未进入通过数：2 个用例在取连接前因未设置 `V4_NATIVE_PG_DSN` 失败关闭；没有连接或 PG 写入。这些需隔离数据库写入的用例未放进 CI。
- `.github/workflows/repository-policy.yml` 已给 V4 scoped job 加入 Accepted Reader、native DSN 和 synthetic HTTP 回归，并只通过 `git lfs pull --include` 拉取两个冻结 Reader 文件，避免拉取仓库全部 436 个 LFS 对象；CI 会读取真实冻结字节，而不是 133/131-byte pointer。工作流本地等价测试通过，GitHub push check 等待最新精确 SHA 实跑。

## PostgreSQL / Owner / Workspace 只读实证

- 本机 PG 身份：`market_research @ 127.0.0.1:5432`；只读事务确认 `transaction_read_only=on`。身份为 `postgres` 且 `rolsuper=true`，R10 的新 reader-role guard 会拒绝，不将事务只读误报为最小权限通过。
- 现有只读计数：`source_packages=0`、`source_revisions=40,455`、`publications=0`、`publication_consumed_sources=0`、`publication_heads=0`；`source_package_facts`、`daily_core_result_snapshots`、`daily_core_result_rows` 均不存在。
- `v4_meta.schema_migrations` 12 条。`010_security_lifecycle_history_r5` 已登记；source manifest 合同迁移和 `013–027`、`034–037` 未登记。Catalog 对照发现 source manifest 列/护栏、supplemental 表、source package fact 关系、R2 manifest/guard 及 Core result 表/约束/触发器的缺口。`028–033` 属独立 FEP 范围，本轮不并入 first-generation closeout。
- PG 一次性执行 runbook（本轮未执行）：获准后先选定唯一目标为 G 盘隔离克隆或单独获准的生产维护窗口；核验全部 SQL SHA、依赖/ledger 前置版本、数据库身份和网络边界；按完整清单串行执行 `010_source_manifest → 013 → 014 → 015–027 → 034 → 035 → 036 → 037`（FEP 028–033 单独治理）；每迁移 `statement_timeout=120s`、锁 5s、整包 30 分钟、idle-in-transaction 60s。先做 G 盘 custom-format 数据备份、schema-only 和 globals-only 备份并完成隔离恢复演练。仅 013–025 有明确配套 down SQL；其余迁移不得猜测逆向 DDL，失败时优先回滚未提交事务，必要时仅恢复经批准的隔离备份。授权文件需明确完整 SQL SHA/DDL 与 ledger DML 范围、拒绝额外业务 DML/Head CAS、操作者、执行窗口和 PG DBA 清理责任；本 runbook 本身不是授权。
- 端口检查时 `5432` 由 PID 8260 监听；`28765`、`28766` 无服务。只有 synthetic HTTP 测试短暂绑定并关闭了 28766；未启动、重启或切换 28765。

## R10 状态矩阵

| 门 | 状态 | 具体结果 |
|---|---|---|
| FILE_READER (当前文件 12 项；任务卡称 11) | PASS | 12 项通过；390/390 精确绑定；LFS 原字节恢复 |
| WORKSPACE | PARTIAL | 根哈希 namespace/capability 已编码并测；旧 schema 的权威映射缺失；C 盘 worktree 未动 |
| OWNER_MAP | PARTIAL | 三个可选 Owner 各自 producer/consumer 已列明；live PG binding 缺失，其余能力未造假 |
| PG_READER_ROLE | CODE PASS / LIVE BLOCKED | role/schema/sequence 写权限守卫通过定向负测；live `postgres` 超管被拒 |
| PROD_CORE_WIRING | PARTIAL | 真实 sealed Owner 到 Core planner 的桥和受控 writer 已接入；缺 publication/source receipt，未形成 live plan/readback |
| SOURCE_AUTHORITY | BLOCKED | 无独立 accepted package、AS_RECORDED/PIT 证明 |
| PG_SCHEMA_STATIC | FAIL / DRIFT | ledger/catalog 未包含要求的 source package、manifest、Core 结果对象 |
| PG_ISOLATED | NOT_RUN | 用户未授权隔离 PG 写入；未创建实例或数据副本 |
| PG_LIVE | READ_ONLY ONLY | 只读身份/表/计数核验完成；无 Publication/Head/Core 行 |
| E2E_NEG | PASS | reader 字节摘要不符的 fail-closed 负例通过 |
| E2E_POS | BLOCKED_NOT_EXECUTED | 无 PIT source/package 与 accepted Publication，不构造成功快照 |
| HTTP_28766 | PASS_SYNTHETIC | 七 endpoint fixture HTTP 测试完成后已停止；非真实 BFF/PG |
| UI_SEVEN | CODE_WIRED / LIVE_READBACK_BLOCKED | 工作台有显式 candidate mode，七 API 同 context；entity Core 绑定读接线完成。缺 live Head 和名称、sector membership、replay/cohort/settlement 数据，不能验证真实 parity |
| CI | PASS_WITH_ONE_EXPLICIT_SKIP | 代码 SHA `ffe8723c9a48111bd23e94c7cb471fe5688ffcdb` push `38888775268` 与 PR `38888782707` 全部通过；145 passed、1 skipped，唯一 skip 是 runner 缺本机冻结 executor 文件 |
| PRODUCTION | UNCHANGED | 28765 未监听；无 PG 写入、迁移、Head 切换、物理删除或历史强推 |

## 下一阶段与阻断

代码和测试已推送；文档将随最新 CI 结果收尾。尚未完成且有外部权限/数据门的项目：独立 source package acceptance/PIT receipt、具备最小权限的非超管 Reader/Writer 角色、获批的 PG schema migration/write 批次，以及现役页面对同一 accepted Publication/T0 的真实读回。真实日更耗时/证券数增量复测需等源数据和运行资格；不以 synthetic 数据宣称性能。

未执行生产/隔离 PG DDL/DML、Publication 或正式 Head 写入、28765 部署、旧 C 工作区清理、Git 历史改写或强推。GitHub Issue #2 和 Draft PR #3 已记录前一批 R10 状态；将在最新代码/报告 SHA 与 CI 确认后同步续推结果，PR 维持 Draft。


## R10 继续实质修复（2026-10-16，代码 SHA `e14ed450c`）

- 为 R4 publication-bound Owner mapping 增加真实事务接口 `persist_publication_module_results(pg, candidate)`：只接受经过摘要核验的 metadata candidate 和显式 `V4_NATIVE_PG_DSN` writer role；确认当前事务可写、writer 权限不含超管/DDL/更新删除、数据库身份一致，以及目标 publication 已 ACCEPTED 且尚未 Head seal。对已存在绑定做逐字段幂等核验；首次写入后逐行 readback。函数只使用调用方事务，不连接数据库、不 commit、不改 Head。迁移 `038_publication_module_results_r4.sql` 仍未执行。
- 新增事务 writer 插入/readback/重复调用回归；R10 scoped CI 同等本地命令为 **150 passed**，其中包含现役 Reader、Owner、Core、七 API/候选 server、固定 28766 synthetic HTTP 等原回归。Python 源码编译、工作台 JavaScript `node --check`、`git diff --check` 和 staged repository policy 均通过。测试使用 SQL fixture；不构成 live PG 写入证据。
- 代码已提交并推送：`e14ed450cc34e06868aa5d53b7a30fbcd984c4e0`。该 SHA 的 GitHub push run [38893245565](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38893245565) 和 Draft PR run [38893252248](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38893252248) 均成功，admission 与 V4 scoped job 全绿；runner 为 **149 passed / 1 skipped**。唯一 skip 是 CI 未提供 Git 外的 2026-10-12 冻结日更证据；本机同命令读取到该冻结证据，为 **150 passed / 0 skipped**。
- 本次进程环境未设置 `V4_NATIVE_PG_READER_DSN`/`WORKBENCH_PG_DSN`；随后仅复用既有 `config/.env` 的 `WORKBENCH_PG_DSN`，显式 `SET TRANSACTION READ ONLY` 后完成只读 catalog 检查。实测 `transaction_read_only=on`，身份为 `market_research @ 127.0.0.1:5432`、用户 `postgres`、`rolsuper=true`；`v4.publications` 与 `v4.publication_heads` 各 0 行；catalog 存在 `publication_consumed_sources`，缺少 `publication_module_results`、`daily_core_result_snapshots/rows` 和 `sector_membership_facts`。监听器核对时 `5432` 为 PID 8260，`28765/28766` 均未监听。故本角色仍被最小权限 Reader guard 拒绝，真实 Owner 绑定写入、accepted Head 和页面到 live PG 正向读回均未发生。


## R10 代码续推（2026-10-16）

- 后续代码 SHA：`ffe8723c9a48111bd23e94c7cb471fe5688ffcdb`（已推送）。
- 补入 Core result 的 publication-bound 只读查询与实体页投影；行 T0/source revision、行 SHA 和聚合 SHA 全部校验，失败关闭。候选 UI 通过显式 URL 参数选择 PG 模式，不加载文件 context、不混读；缺少候选 context 时在页面报错。
- Sector 页将 lifecycle supplement 与真实 membership 分离；成员数、名称、算法状态在无权威 PG relation 时明确 `DATA_MISSING`。
- 最终综合回归 146 passed / 0 skipped；Node JS 语法检查及 Python compileall 通过。代码 SHA push/PR workflows（38888775268 / 38888782707）均全通过，145 passed / 1 skipped；唯一 skip 是 runner 缺少本机冻结 executor 文件。
- 当前仍没有合法 AS_RECORDED/PIT accepted source/package、PG Publication/Head、daily Core 数据行或七页所需完整 Owner。代码可读路径完成不代表实际生产者写入、PG 正向 E2E、页面 parity 已验收。

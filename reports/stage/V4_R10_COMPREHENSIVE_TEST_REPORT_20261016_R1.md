---
stage_id: V4_R10_COMPREHENSIVE_20261016_R1
code_sha: 6f60daa70b23f05e5dd57cec381b12f4c2e75e10
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
3. **七路现役 API：** `make_v4_handler` 增加仅显式的 `source=pg_candidate` 分支；需要注入 reader adapter、开启候选模式，并强制携带 `trade_date`、`model_namespace_id`、`context_token`。候选读出错时返回 `PENDING_PG_HEAD / NO_READER_PRIVILEGE / NOT_PIT_ELIGIBLE / DATA_MISSING` 状态，不读文件补齐；默认文件 Reader 仍按原路径工作。`serve_v4_candidate` 只绑定 `127.0.0.1:28766`，没有被启动。
4. **七页 Owner 消费：** 候选 adapter 对 summary、radar、entity、sector、cohort、settlement、health 返回逐字段数据状态，并维持原 Owner 合同/精确字段投影，不合并 T0。现有三类 PG Owner 能力仍然是可选且无 live Publication binding：`research_priority → radar`；`operational_risk → summary/health`；`sector_lifecycle → sector/health 补充`。entity 的日线价格和身份名称关系缺失；sector membership/algorithm state 未绑定；cohort 和 settlement 没有 publication-bound 数据关系；health 缺 replay/maturity。故 API route 接入不等于 UI parity。
5. **Workspace identity：** 增加不暴露路径的 `V4_PG_WORKSPACE_NAMESPACE_ID_R1`，把 root-derived schema、root identity SHA 和读写能力要求一起表达；测试确认两个不同根映射到不同 schema。PG 旧 schema 到新 G 盘主仓的授权映射未建立，不按日期或名称猜测。当前唯一主仓在 G 盘。旧 C 盘 worktree 只读状态为 detached/prunable，gitdir 指向不存在位置；未触碰或删除。
6. **日更生产者和 Core：** 现役 `operational_daily_executor_v1.derive_ready_sources` 在真实 `seal()` 后调用 Core plan bridge。该桥只从已封存的 `raw/core/profile/lifecycle` bindings 按 `(security_id, trade_date)` 读取和校验数据，并要求显式 publication/source receipt 才组装 `build_daily_core_result_plan` 输入；当前没有该权威上下文时显式返回 `BLOCKED_PG_PUBLICATION_CONTEXT_MISSING`，不生成假 source ID、Head 或 PIT 声明，也不做数据库 I/O。新增 `persist_daily_core_result` 受控 writer，要求显式 writer DSN、配置角色与当前数据库角色相同、非超管/无 DDL 能力、仅具备 Core 表 INSERT、匹配 CANDIDATE publication、PG statement-time PIT/source package 证明；不自动提交、不改 publication status、不改 Head。尚无合法 source receipt 或 live Core 表，故真实 plan 和写入均未运行。

## 测试和 HTTP 证据

- 综合定向回归（15 个文件：PG candidate/Owners/source manifest/Core result、executor、T0、exact policy、R8 bridge/schema runner、DSN、Accepted Reader、HTTP）：**142 passed，0 skipped**，本地临时目录为 `G:/codex_tmp/test_temp/v4_r10_check`。
- Reader/DSN/HTTP 单独合并组：**29 passed**；收集分母分别为 Accepted Reader 12、DSN guard 15（参数化角色负例展开）、候选 HTTP 2。
- 合成 HTTP fixture 在允许的固定开发端口 `127.0.0.1:28766` 实际发起 HTTP GET：七个 endpoint 都命中候选 adapter；context 缺字段返回 400；未启用候选模式返回 404；无 accepted publication 返回 `PENDING_PG_HEAD`；文件模式仍返回 file Reader。测试关闭后服务线程退出。此为隔离 fixture，不代表真实 PG 或浏览器页面读回。
- `tools/git_repository_policy.py --staged`：通过（13 changed Git blobs）；`git diff --check` 与所改 Python `compileall`：通过。
- GitHub push run [38885076598](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38885076598) 和 PR run [38885083695](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38885083695) 在上述同一 SHA 全部 job 成功。V4 scoped pytest 实际结果 **141 passed, 1 skipped**；唯一 skip 为 `test_real_20261012_executor_evidence_reaches_pg_adapter_as_diagnostic_only`，原因是 GitHub runner 没有不入库的本机 2026-10-12 冻结 executor 文件。Accepted Reader、native DSN 和 synthetic HTTP 组均实际运行，非 skip。
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
| UI_SEVEN | PARTIAL / NOT_VERIFIABLE | 七 API route 已 wired；页面所需价格、身份、成员、回放/结果关系仍缺 live publication 数据 |
| CI | PASS_WITH_ONE_EXPLICIT_SKIP | Push/PR checks 在 SHA `6f60daa70b23f05e5dd57cec381b12f4c2e75e10` 成功；141 passed、1 skip，唯一 skip 是 CI 缺本机冻结日更证据 |
| PRODUCTION | UNCHANGED | 28765 未监听；无 PG 写入、迁移、Head 切换、物理删除或历史强推 |

## 下一阶段与阻断

本阶段代码、测试和 CI 修改已准备提交推送。外部发布继续等待：独立 source package acceptance/PIT receipt、具备最小权限的非超管 Reader/Writer 角色、获批的 PG schema migration/write 批次，以及现役页面对同一 accepted Publication/T0 的真实读回。真实日更耗时/证券数增量复测需等源数据和运行资格；不以 synthetic 数据宣称性能。

未执行生产/隔离 PG DDL/DML、Publication 或正式 Head 写入、28765 部署、旧 C 工作区清理、Git 历史改写或强推。GitHub Issue #2 和 Draft PR #3 将在最终推送后同步准确 HEAD、实际 CI 结果、Workspace/Owner 状态及阻断项；PR 维持 Draft。

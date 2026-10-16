---
stage_id: V4_R12_SOURCE_UNIVERSE_PG_20261016
code_sha: 1174f63512031ba63498285495e4b0dee36ba370-plus-R12-worktree
test_scope: source-acceptance-universe-source-manifest-pg-preflight-seven-api-focused
conclusion: 110-focused-tests-pass; live-authority-universe-publication-and-pg-migration-blocked
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# 大A V4 R12 来源、Universe 与 PG 闭环阶段报告 R1

日期：2026-10-16。依据 Drive 任务 `V4_R6独立审计_R12真实来源与PG发布闭环任务_R1_20261016.md`，适用设计基线为 `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、`V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md` 与 R6 已通过的 Core/Candidate 合同。本报告覆盖当前工作树代码与针对性验证；不重做 R6 Core Completeness/Candidate 修复，不把 fixture 结果视为外部验收或生产发布。

## 本轮交付

- 来源授权接口新增带版本的 Ed25519 接受回执校验：签名绑定 T0、冻结与 readiness 摘要、包描述符、来源事实绑定、AS_RECORDED/PIT 标记及同日上海截止时间；自哈希、错误签名、错误绑定、晚签和旧日后验回执拒绝。受信签发者注册表保持空白，因此真实来源接受继续关闭。
- Source package manifest 升为 R3，增加接受回执、来源事实哈希/定位/行数、AS_RECORDED/PIT 与签名证明摘要；PG Core Reader 与候选读回按 R3 验证这些字段及来源包签名，R2 读回兼容旧字段。新增迁移 `040_source_manifest_r3_fact_proof.sql` 允许 R3 合同标记。
- 新增 `V4_MARKET_UNIVERSE_COMPLETENESS_R1`：以独立且签名绑定的同 T0 security-universe fact 为分母，显式列明 SSE/SZSE/BSE 范围、普通 A 股纳入规则、B 股/ETF/指数/债券等排除项，以及停牌、新股、退市、换码和身份未知分类；逐证券列出来源归属、source_present、core_present 与差异。5100 条合成夹具用于规模和差异逻辑验证，不代表真实交易日行情统计。
- PG candidate API 要求根路径身份到 namespace/database/Owner schema 的明确有效映射；无映射或与 publication context 不符时关闭。映射授权表保持空白，未生成生产 Owner 授权。
- 新增只读迁移预检脚本，扫描迁移源码 SHA、重复序号、危险操作标签，并在只读事务中收集 catalog、ledger、relation、function、grant 与 reader-role 属性；输出只写入 G 盘临时证据目录。

## 验收矩阵

| 项目 | 状态 | 本轮证据 / 边界 |
|---|---|---|
| SOURCE_AUTHORITY | `PASS_CODE_PATH / BLOCKED_LIVE_AUTHORITY` | 独立 Ed25519 回执路径及负例通过；仓库信任注册表无签发者，不接受真实包。 |
| PIT | `PASS_FIXTURES / BLOCKED_LIVE_RECEIPT` | 新 T0 签名时间与同日 15:00 截止验证通过；旧 2026-10-12 后验不能提升为 PIT。无真实签发回执。 |
| SOURCE_MANIFEST | `PASS_R3_CODE / BLOCKED_PG_MIGRATION` | R3 字段、签名重验与 R2 兼容聚焦测试通过；迁移 040 尚未执行。 |
| UNIVERSE | `PASS_CONTRACT_FIXTURES / BLOCKED_LIVE_SOURCE` | 5100 条同日合成分母、缺失/多余、未知身份、证券类别与交易所范围测试通过；无独立签收的真实 Universe 样本，且本轮没有生产发布链路中的持久化 Universe 读回。 |
| CORE | `R6_PASS_PRESERVED` | R6 Core 完整性修复保持；本轮聚焦 Core Reader 相关测试通过。没有重新宣称真实 PG Core 发布。 |
| OWNER | `PARTIAL_CODE / BLOCKED_LIVE_BINDING` | Owner schema 必须匹配显式映射；没有现场 Owner binding，也未把 sector_lifecycle 当作板块成员关系来源。 |
| WORKSPACE | `PASS_FIXTURE / BLOCKED_PRODUCTION_MAPPING` | 根身份、日期区间、namespace、数据库及三个 Owner schema 映射校验由合成 API 夹具覆盖；正式授权注册表为空。 |
| PG_STATIC | `PASS_INVENTORY_ONLY` | 41 个 SQL 文件均记录原始字节 SHA；重复序号为 010；迁移 040 是本轮 R3 所需新增。未宣称 SQL 已编译或 catalog 差异已逐迁移闭合。 |
| PG_ISOLATED | `NOT_RUN` | 未获隔离数据库写入授权；未启动或复制 PG。 |
| PG_LIVE | `BLOCKED_PRIVILEGED_READER` | 只读事务读取 `127.0.0.1:5432/market_research`；reader 实际为 postgres，superuser、CREATEROLE、CREATEDB、BYPASSRLS、具写权限。12 ledger rows、19 relations、10 functions、133 grants。迁移决策为等待 catalog/ledger reconciliation 与批准的迁移角色。无 DDL/DML/Head 改动。原始证据按合同保存在 Git 外 G 盘临时目录 `v4_r12_preflight/final-live/`。 |
| E2E_NEG | `PASS_FIXTURES` | 错签名、错绑定/摘要、时间与旧日、Universe 缺漏/多余、映射冲突和缺少接受证明等负例通过。 |
| E2E_POS | `PASS_SYNTHETIC_FIXTURES` | 受信测试密钥签发的新 T0、R3 manifest/reader、候选 HTTP 路径与 Universe 逻辑正例通过；不等于真实签发者或 PG 发布。 |
| SEVEN_API | `PASS_SYNTHETIC_HTTP` | 28766 上对 summary、radar、entity、sector、cohort、settlement、health 七个候选 API 分别验证；本次测试结束后服务已关闭。 |
| BROWSER | `NOT_RUN` | 没有运行生产或开发浏览器页面；HTTP 夹具不代表 UI 真数据接线。 |
| CI | `PENDING_PUSH` | 本地提交前验证完成后触发；需在 Issue #2 与 Draft PR #3 记录远端精确结果。 |
| PRODUCTION | `UNCHANGED` | 未连接/修改 28765 服务；未切换生产 Head、未部署、未调度、未写入 PG。 |

## 本地验证

命令（PowerShell；`TMP`、`TEMP`、`TMPDIR` 均设为 G 盘临时目录，`PYTHONPATH` 指向 G 盘临时依赖与仓库 `src`）：

```text
$env:TMP='G-temp'; $env:TEMP=$env:TMP; $env:TMPDIR=$env:TMP; $env:PYTHONPATH='G-deps;src'
python -m pytest -q tests/test_v4_daily_ingest_r6.py tests/test_v4_market_universe_completeness_r1.py tests/test_v4_r12_migration_readonly_preflight.py tests/test_v4_pg_source_manifest.py tests/test_v4_daily_core_result_r6.py tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py
107 passed
python -m pytest -q tests/test_v4_server_pg_candidate_mode.py
3 passed
```

测试仅覆盖现役 V4 定向夹具。28765/28766 在启动 API 夹具前没有监听者；API 测试仅绑定 28766，并在 finally 中关闭。阶段范围为 `DEGRADED_PASS`：代码合同和合成正负例完成；真实授权、Universe 生产读回、迁移执行/编译、隔离 PG、Owner live binding、浏览器及发布链路仍未通过。下一阶段先取得独立数据签发主体与 workspace/Owner 映射的正式授权；数据库如需写入，另行提交精确目标、SQL hash、备份/恢复、角色和回滚范围供单独授权。

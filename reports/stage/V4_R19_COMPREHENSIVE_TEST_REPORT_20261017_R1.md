---
stage_id: V4_R19_CONTINUOUS_AUDIT_20261017
code_sha: 27ca6954461132ee78af68b34584f04d1018daf5
test_scope: R19_A_B_C_D_historical_governance_universe_reference_audit_and_focused_v4_ci
conclusion: R19_CODE_ACCEPTANCE_PASS_LIVE_PG_SOURCE_BROWSER_AND_PRODUCTION_ACCEPTANCE_BLOCKED
approval_status: CODE_TEST_COMMIT_PUSH_AND_GITHUB_REPORT_AUTHORIZED
---

# 大A交易 V4 R19 连续审计与修复报告 R1

日期：2026-10-17（Asia/Shanghai）。唯一执行入口：Drive 正式任务卡 R2 `V4_R14至R18独立审计_R19历史证据Universe与全仓非配置文件引用专项审计任务_R2_20261017.md`；R1 仅作历史记录。适用的最近升级文档：`docs/upgrade/V4_R18_INCREMENTAL_PERFORMANCE_RECOVERY_MATRIX_R1_20261016.md` 及 `reports/stage/V4_R14_R18_FIVE_STAGE_COMPREHENSIVE_TEST_REPORT_20261016_R1.md`。仓库 `NanOns/a-share-market-structure-research`，分支 `codex/v4-workspace-cleanup`。任务卡冻结起点 `601c3758b34fd3c983c6960d93f188e7fd733b64`；验收代码 SHA `27ca6954461132ee78af68b34584f04d1018daf5`，本报告在该代码验收后独立提交。

R19-A/B/C/D 连续执行。代码验收状态 `R19_CODE_ACCEPTANCE_PASS`。此状态不表示线上 PostgreSQL、真实市场数据 PIT、Owner、浏览器、正式 Head、性能、生产部署或产品原始 22 阶段整体通过。未执行 PG 写入/迁移、服务启动、Head/Publication 切换、调度或业务数据删除。

## 子项验收

| 子项 | 结论 | 证据与边界 |
|---|---|---|
| R19-A 历史冻结字节 | PASS | 保存三个原始失败堆栈，分别覆盖 `test_exact_scoped_promotion`、`test_zero_mutation_repeat`、`test_full_contract_completeness`；错误均在 `scripts/v4_12_promotion_r14.py::exact()` 检查 `scripts/validate_v4_12_r11_chain.py` 字节身份时触发。历史 Git commit `33b1949a1c05b0fe6c9068e6db9f219a9f11378b` 的原始 blob 为 9,383 bytes / SHA-256 `ab76426fba950a58ba4a38ae144084801082d784e508c1985120f00a5c1a167d`，与接受 Head 相符。现役同路径 9,564 bytes / SHA-256 `72a97af013b7c87e70be16c6dbdcc3741ca7acfca3a927bf52b61f34a5515a9c` 存在逻辑变化，不是换行差异。只增加原字节只读归档并复用现役历史 resolver；不改 Accepted Head、旧摘要或业务文件。扩展审计另归档 24 个有原始 Git blob 证据的历史 Head 文件身份。 |
| R19-B Universe 正向读回 | PASS（PG-shaped） | `VerifiedUniverseReadback` 与 canonical receipt 材料字段同构，绑定 acceptance receipt、issuer/T0/namespace/package/reconciliation 等身份。可信测试签发者→伪 PG 表行→`read_universe_snapshot`→Core→Candidate→Head planner 正向计划链通过；身份篡改负例拒绝。Fake/fixture 不等价真实 PG。SQL 042 的实际编译、约束触发器与事务顺序、角色权限、并发、实际落库/readback 未运行。 |
| R19-C 实际 PG / 来源集成 | BLOCKED | Reader 环境变量未配置，诊断为 `READER_CREDENTIAL_MISSING`。未用 writer/superuser 回退，未连接/查询/迁移/写入数据库。真实来源签发、交易日历、Workspace/Owner、七页面和性能仍待独立验收。 |
| R19-D 非配置文件引用审计 | PASS（静态审计代码验收） | 全量 Git 跟踪文件清点、语法/路径扫描、Accepted Head 历史身份复核、LFS、脚本/SQL/前端/CI及动态路径分类由可重复程序完成并纳入测试/CI。没有把正常业务文件引用本身判成缺陷。完整逐边 JSON 在 `G:\codex_tmp\R19_R2_20261017\V4_R19_NONCONFIG_EXTERNAL_FILE_REFERENCE_INVENTORY_R1.json`，46,725,780 bytes，SHA-256 `786b195db43875fcd521194d97e7a8f7e2548b7ad6c441d1f14962a23d8b07a9`。原始清单和测试日志是 G 盘证据包，不入库。 |

### D 全仓扫描指标与模块覆盖

`NONCONFIG_AUDIT_CODE_PASS`; `REFERENCE_EDGES_TOTAL=24194`; Git tracked paths `59959`; source files `4155`; independently hashed `14069`; `RUNTIME_VERIFIED_COUNT=0`; `DYNAMIC_UNRESOLVED_COUNT=8709`; `P0_OPEN=0`; `P1_OPEN=0`; `EXCLUDED_WITH_REASON_COUNT=56998`; LFS pointer-only `0`; LFS objects verified `406`。

| 模块 | 覆盖结果 | 未运行/限制 |
|---|---|---|
| Accepted Heads、历史治理、校验器 | 递归检查 path/SHA/bytes/commit；对照历史 Git 原始 blob 与现役字节身份；可追溯旧版本以归档和当前演进分离。 | 没有动态执行所有历史调用者。 |
| TDX/BaoStock、Source/PIT、Universe、Core/Profile、Sector、Owner、Focus/Forward/Cohort/Settlement | 扫描当前可达代码、manifest、源 locator、环境/动态路径和 SHA 边。 | 无生产 issuer/日历/T0/PG 来源证据；动态分支未做运行期 trace。 |
| SQL migrations 与 Reader/Writer | SQL 路径和注册顺序静态扫描；010 重复文件身份及 042 顺序有静态合同测试。 | 未查 PG catalog、未运行 SQL、未开事务。 |
| scripts、CLI、Shell/PowerShell、Git/CI | 按跟踪清单与入口扫描；CI 包含历史用例、Universe 读回/篡改测试、策略测试和只读全仓扫描。 | 依赖生产角色/外部工具的分支未执行。 |
| 七 API、导航、前端模板与 assets | 路由、静态资产、UI roots/aliases、输出路径分型；API 路由没有误判成磁盘文件。 | 未启服务或浏览器。 |
| LFS、外部行情文件、业务产物 | LFS pointer/object identity 检查；输入、外部工具与输出路径按用途分类。 | 未刷新行情或生成业务产物。 |

余项含 352 个 P2 `ACTUAL_MISMATCH`、92 `MISSING_FILE`、82 `HISTORICAL_ARCHIVE_VALID_CURRENT_CHANGED`、8,709 动态未解析边。另分类 14,858 个已知当前有效引用、34 个输出路径声明、33 个 API 路由（非本地文件）、16 个仅配置边、12 个旧绝对根、6 个外部工具查找。P0/P1 清零不等于 P2 或动态边都已运行验证；逐边记录保存在清单中。

扫描器：`scripts/audit_v4_nonconfig_file_references_r1.py`；回归：`tests/test_v4_nonconfig_external_file_references_r1.py`。从仓库根目录重复执行：

```powershell
$env:TMP='G:\codex_tmp\R19_R2_20261017'; $env:TEMP=$env:TMP; $env:TMPDIR=$env:TMP
python scripts/audit_v4_nonconfig_file_references_r1.py --output $env:TMP\V4_R19_NONCONFIG_EXTERNAL_FILE_REFERENCE_INVENTORY_R1.json
python -m pytest --confcutdir=tests -q -p no:cacheprovider tests/test_v4_nonconfig_external_file_references_r1.py
```

此扫描器提供可重复静态清单与有限安全本地检查，非完整运行期 trace。R19-D 代码验收报告建议路径为 `reports/audits/V4_R19_NONCONFIG_EXTERNAL_FILE_REFERENCE_EXTERNAL_AUDIT_R1.md`；但仓库的 `tools/git_repository_policy.py` 和 `.gitignore` 明确拒绝 `reports/audits/` 内容，本轮没有绕过准入规则或修改仓库策略，模块汇总因此并入本综合报告。

## 测试、CI 与 22 阶段口径

修复后精确 R18 聚焦集合加 R19 A/B/D 回归 `220 passed`、0 failed；三个指定历史测试单独通过且包含在最终集合中，无新增隐式 skip。另一次 R19 定向回归为 `49 passed`。首轮 push/PR CI 暴露两项扫描器平台/路径边界问题：Linux 将 `E:/python/python.exe` 误读为相对路径，以及把超过 OS 路径组件上限的文档字符串送入文件检查。均已在代码 SHA `27ca69544` 修正并加回归；同一精确本地工作流集合复跑 `220 passed`。`tools/git_repository_policy.py --staged` 与 `git diff --cached --check` 对本阶段代码及本综合报告暂存内容均通过。修复后的 push/PR GitHub CI 尚待完成，最终状态会写入 Issue #2 与 Draft PR #3。

22 阶段双口径：仓库 `data/v4/V4_STAGE_ACCEPTED_HEAD.json` 记录 `accepted_stage_range=V4_00_TO_V4_15_ACCEPTED`，内部也有 `DEGRADED` 状态；这是被接受的仓库历史范围/状态。它不是原产品 22 阶段所有功能当前通过的证明。现有材料仍无足以逐项判定的正式产品 22 阶段全量名称和适用验收合同，因此当前功能映射为 `NOT_VERIFIABLE_NO_FORMAL_PHASE_CONTRACT`，不是宣称阶段 01—22 全都没被历史接受或全都 PASS。R14—R19 工程工作包不等于产品整体验收。

## 外部验收前置项

真实只读 PG 验收需要合法 Reader 身份/DSN、精确迁移 SHA 差异、只读隔离级别与查询窗口；Source/PIT 需要正式 issuer 与交易日历及签发证据；Owner/UI 需要获准的 root→namespace/Owner 映射及可接受离线历史 T0 原始字节/可得时刻。随后才能验证真实 PG readback、七页面字段和独立性能分段。推送/CI成功也不授权这些后续数据、Head 或生产操作。

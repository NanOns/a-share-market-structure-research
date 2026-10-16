---
stage_id: V4_PG_DAILY_PUBLICATION_R6_20261016
code_sha: 4f0c56a573695665a0f3ab089f19af7cd24828bb
baseline_sha: 5875c1f79daeca0e7aec47c881bef05316b5adae
branch: codex/v4-workspace-cleanup
scope: WB1-WB7
test_scope: targeted R6 source/core, PG publication reader/adapter, contract, executor regression
conclusion: code partial pass; live daily publication blocked by source acceptance, schema, and core-result gaps
approval_status: production operations not authorized
status: R6_IMPLEMENTATION_PARTIAL_PASS
pg_live: DB_READ_ENV_AVAILABLE_SCHEMA_BLOCKED
business_publishability: BLOCKED_CORE_RESULT_AND_LIVE_SCHEMA
daily_e2e: BLOCKED_EXISTING_EXECUTOR_FIXTURE
production: UNCHANGED
---

# V4 PG 日发布 R6 综合阶段报告

## 范围与实现

按 Drive R6 任务卡连续推进 WB1–WB7。最新且适用资料已查阅：R6 任务卡、V4 R8 unified-source repair、V4 runtime performance repair、R5 阶段报告、现役日更 executor/source-freeze 与 publication contracts。未开展 scanner 工作；阶段 0 不适用于本轮范围。

- **WB1 来源链（部分）**：新增 `v4_daily_source_ingest_r6.py`。它从实际 `execute_sources` 产出的冻结文件及精确 TDX/BaoStock/runtime 文件摘要构建确定性 source package 计划；校验 T0、SHA、路径、TDX 行键、BaoStock 批次日期、readiness 对 freeze 的绑定与独立 PIT 接受回执。当前 freeze `AS_RECORDED=false / PIT_ELIGIBLE=false` 时只返回 `CAPTURED + DIAGNOSTIC_ONLY`。新增 migration 036 将 source revision 精确绑定到 package fact、记录范围、源字节 SHA、接受回执，并约束 consumed source key/digest。PG 持久化代码仅接受明确 accepted plan，未连生产执行。
- **WB2 核心结果（阻断）**：WB7 证实现役 PG 没有日行情/画像业务 relation。新增 `v4_daily_core_result_r6.py` 仅对现役 producer 已生成的行做身份、T0、行情价格基准、OHLC、换手缺失、新股历史不足和 digest 校验；不另算 MA 或画像。合同完整性阈值尚无可核准版本，因此结果保持 `BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED`。Migration 037 草拟 publication-bound core result snapshot/rows 与 append-only、T0、来源及完整性约束；无实际 PG producer/readback 数据。
- **WB3 事务/CAS（未在 PG 验证）**：source adapter 的持久化接口不查找 DSN、不提交事务、不更新 Head；要求调用者提供事务内 PG connection。candidate planner 现在验证自身 digest 并要求 PG core readback 的同版绑定；R6 没有可信 core readback，因此没有业务 CAS。Migration 037 增加已接受 publication 必须具有同版、同 T0、同 source manifest 且 PASS 的 core result 约束。`PG_TRANSACTION_NOT_TESTED`。
- **WB4 页面（部分）**：candidate adapter 现在逐字段报告 present/eligible/verified 行数、source path、缺失原因和覆盖状态，防止一行命中提升全页状态；异 T0 行不计入覆盖。七端点仍未接入默认 `/api/v4/current/*` handler：summary 事件、risk/priority/sector lifecycle 只能作为现有 publication/Owner 补充，entity 无 publication-bound 日行情/名称，sector 无 publication-bound membership，cohort/settlement 缺数据 relation，health 缺 replay/maturity 主结果。默认 UI 不变。
- **WB5 增量/恢复（部分）**：现役 TDX source freeze 本身声明 delta 文件计数及 `full_history_rehash_performed=false`；本轮未执行真实日更、未取得 Core/Profile/Sector/Focus/Forward/PG/Publication 分段耗时，也未改变生产调度或 Head。PG 成功步骤重启、失败后续跑、用户进度展示仍未端到端验证。
- **WB6 回归（部分）**：reader 新增拒绝 `source_package.page_observed_at > publication.accepted_at`；candidate planner 校验自身 digest 并要求 PG core readback 的同版绑定。测试覆盖 source freeze 伪造/错绑、core identity、价格基准、不完整样本门、package 观察晚于接受时间、改 READY 后 digest 不符、无密钥 digest 不能伪造 PG readback。完整 executor chain 的 `test_full_executor_entry[True]` 仍失败：临时 fixture 缺少 `config/operational_daily_exact_release_policy_v2.json`，在 immutable policy 读取处 FileNotFoundError；没有弱化/伪造正式策略以令测试通过。
- **WB7 PG 只读**：读取 `config/.env` 的合法 `WORKBENCH_PG_DSN`，事务首句 `SET TRANSACTION READ ONLY`，只执行 SELECT。连接身份 OID `646711`，`127.0.0.1:5432/market_research`。使用角色为 `postgres` 超级用户（非最小权限读角色），事务级只读。实际行数：source_packages 0、source_revisions 40,455、publication_consumed_sources 0、publications 0、publication_heads 0、market_calendar_sessions 0。Live schema 未包含 R5 migration 034/035 所需列，migration ledger 未登记它们；无 core market relation。10/09 file Head 仍为已发布 Head；10/13 文件 PG candidate 只是 candidate read preparation，不是 PG readback。

## 测试与限制

- 新增 source/core binding 定向测试：**5 passed**（synthetic fixtures；不执行 SQL，不证明 live provenance 或真实行情）。
- WB4 candidate adapter/owner/contract 测试：**51 passed**（synthetic PG doubles）。
- 综合定向命令覆盖 candidate、contract static、owners、source manifest、R6 source/core 与 executor chain：**63 passed, 1 failed**；唯一失败为 `tests/test_pre_next_t0_executor_chain.py::test_full_executor_entry[True]`，原因和边界见 WB6。
- 推送 SHA `4f0c56a573695665a0f3ab089f19af7cd24828bb` 的 [GitHub Actions run 38864434003](https://github.com/NanOns/a-share-market-structure-research/actions/runs/38864434003)：admission 与 `v4-pg-publication-candidate` 均通过。
- 未在真实 PG 执行 migration、DML、source-package 写入、core-result 写入或 Head CAS；未启动 28766/28765 服务；未改生产调度。28765 与 5432 生产数据保持不变。PostgreSQL DDL 未经本机 parser 编译检查，需隔离 PG 上验证。
- Migration 036/037 仅为提案；未在隔离 PG 编译/执行。CI 等提交 SHA 推送后核验。

## 下一阶段与授权包

保持 Draft PR。R6 代码已推送仍不等于真实日更或可发布；当前阶段门禁仍为 `SOURCE_AUTHORITY=BLOCKED_NO_ACCEPTANCE_RECEIPT`、`CORE_RESULT=BLOCKED_NO_LIVE_PRODUCER_OR_ROWS`、`LIVE_SCHEMA=BLOCKED_MISSING_034_035_AND_R6_RELATIONS`、`PG_TRANSACTION=NOT_TESTED`、`PAGE_DEFAULT_CONSUMER=NOT_CONNECTED`、`DAILY_E2E=FAILED_EXISTING_FIXTURE`。下一次一次性授权包应限定在隔离写 PG：逐条 review/编译 034–037；记录隔离实例来源、端口、目录、连接身份和清理责任；备份 schema；限制每表行数；执行 DDL、写入/重放/回滚演练，验证约束与只读 readback；并发测试 Head CAS；报告每步耗时。生产仍须另行授权 DDL/DML、accepted Head、28765 部署或调度切换。

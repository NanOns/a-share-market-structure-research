# V4 R21-R6 开发授权、Workspace 与 PG 实修进度 R2

- 状态：`DEGRADED_PASS`；仍在连续实修，未达到本轮全模块完成标准。
- 授权基线：2026-10-18 Drive 任务卡 R2 与长期开发授权 SOT R2。开发期可执行现役 V4 DDL/DML、迁移、Owner/Registry/Head 候选写读和可重建临时物清理；正式生产切换与最终打包仍后置。
- 当前开发分支：`codex/v4-workspace-cleanup`。唯一 PG：`127.0.0.1:5432/market_research`，OID `646711`；开发服务 `127.0.0.1:28766`。28765 未监听、未触碰。

## 本轮实际代码与数据库变更

- `src/workbench_db/v4_native.py`：新增稳定 Git-origin + 仓内相对位置 workspace ID；读取 PG alias 后解析既有物理 schema；提供只复用既有 schema 的幂等注册函数。Owner mapping 可优先按稳定 workspace ID 匹配，保留旧 root hash 兼容。开发写连接允许复用已授权共享 DSN，读路径继续显式设置只读事务。
- `src/workbench_db/migrations/v4_postgres/046_v4_workspace_namespace_alias_r1.sql` 与 `047_v4_workspace_namespace_alias_central_schema_r1.sql`：新增 append-only namespace alias registry，并允许中心 `v4` publication schema 作为 namespace 目标。`scripts/apply_v4_phase0_schema.py` 已登记两项迁移。
- 两项迁移已在唯一 PG 实际执行并读回：`v4.workspace_namespace_aliases_r1` 存在；ledger 状态为已应用；v4 表数量 35。PG 中登记 4 个 ACTIVE alias：主仓 history→`v4_history_dbe184da961f97b8`、主仓 publication→`v4`、SourceIngress→`v4_forward_213e535c50ad7135`、Owner closeout→`v4_forward_812843566da3f180`。数据未搬移、未重算。
- 在 G 盘临时模拟目录复验：移动前后 logical workspace ID 相同；history/publication alias 返回同一既有 schema；Owner mapping 按稳定 ID 解析成功。
- `configured_dsn()`、Phase 0/Focus/runtime-head 迁移入口现可复用实际已授权的共享连接；PG 现场身份为 `postgres` 超级用户，`market_research`。没有把密码写入代码或报告。相关迁移入口不再要求第二个名义 DSN。

## PG 与 28766 现场结果

- PG 有 `v4.contract_versions` 16 行、`contract_approval_events` 16 行；`dm01_data_accepted_heads` 1 行。`publications`、`publication_heads`、`operational_research_heads`、日历/universe、source package/core result 等当前关键事实域为空；没有据此伪造正式 Head 或行情 accepted 状态。
- 28766 实际服务为 `V4_PG_RESEARCH_CANDIDATE`、只读、生产权限关闭；PG 候选 T0 `2026-09-30`，股票 5,213、板块 378、Focus 469、Forward 117、事件 33。当前来源并非最新完整交易日，严格 PIT 可用日期 0。
- 通过 28766 实际请求并核验 API：home、股票搜索 `600675`（命中 1 行）、行业过滤（总计 110，返回 5）、Focus（469）、Forward 统计、market breadth、diagnostics health（5 个域）、replay、compare。请求结果均回传同一候选 T0/上下文；replay 返回 `PIT_NOT_AVAILABLE / PG_CANDIDATE_SNAPSHOT_HAS_NO_FIRST_AVAILABLE_AT_T0_PROOF`；compare 标记重建、非 PIT。日更状态 API 为 snapshot-only，worker 未启动，写任务关闭。
- Windows UI 自动化读取 Chrome URL 时被工具层策略停止，未继续绕过；因此报告只记实际 API 功能请求，浏览器逐页交互矩阵仍未完成。
- 历史 SourceIngress 的通用 JSON/base64 入库上限为 64 MiB；大型 TDX ZIP 由现有分包流程写 PG 包身份与规范化 bars，而非通过此通用 raw-byte 字段入库。当前尚缺完整、更新的全市场 T0 与真实日更运行证据。

## 验证、清理与后续

- 定向测试：`tests/test_v4_native_reader_dsn.py`、`tests/test_v4_workspace_owner_mapping_pg.py`、`tests/test_dm01_incremental_parent_pg_binding.py` 共 22 项通过。
- 先前已清理 `G:/codex_tmp` 中确认可重建的 pytest/pyc/pip 缓存 2,674,361,197 字节。大型 `r7_active_baseline_20261015` 含修改源码与独有未跟踪材料，仍保留并待逐项归属；未清理用户源、TDX 只读源或无关文件。
- 剩余重点：继续精确登记当前仓库中确有数据且可归属的 alias；完成开发阶段候选 Head/Owner 的实际 PG 写读与业务 BFF 绑定；补齐可靠 T0/真实来源和日更链；继续现役 V4 文件读取漏项与 Focus/Forward/Market/Cohort 接线；28766 浏览器逐页操作验证；核验并清理确认无活动消费者的 G 盘开发衍生物。
- 当前证据不支持全模块验收、正式生产切换或最终生产打包；两项操作仍等待全功能验收及用户后续明确指令。

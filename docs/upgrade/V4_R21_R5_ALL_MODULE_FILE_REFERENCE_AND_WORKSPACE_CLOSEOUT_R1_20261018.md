# V4_R21_R5 全模块文件引用与 Workspace 集中实修收尾报告

- 日期：2026-10-18
- 分支：`codex/v4-workspace-cleanup`
- 状态：`CODE_SCOPE_PARTIAL; BROWSER_PARTIAL; LIVE_PG_VERIFIED; FORMAL_HEAD_CLOSURE_PENDING`
- 开发服务：`127.0.0.1:28766`（候选快照、日更 worker 未启动）；生产端口 `28765` 未触碰。
- PG 身份：共享实例 `127.0.0.1:5432/market_research`，OID `646711`；当前候选 T0 为 `2026-09-30`，source mode `PG_CANDIDATE_SNAPSHOT`。

## 实际代码修复

本轮在现有分支上修改了 68 个 Python 运行模块、1 个仓库准入策略工具及 V4 日更前端资产，并更新了既有 R21 调用点矩阵和本收尾报告。真实改动包括：

- 将现役 V4 的 Head、Owner、Membership、合同 Registry、历史来源、候选 BFF 和业务消费者改为精确 PG 绑定读取；移除 Head/合同/Owner 的本地文件回退路径。
- 修正日更 successor control 的 PG payload 适配；候选预览的进度接口不再探测未启用的作业表，返回真实的 `PREVIEW_ONLY`、worker 未启动状态。
- 将 DM01 增量构建器的运行契约读取改为 Registry 的 PG 绑定物化；Forward、settlement、runtime acceptance、Profile correction ancestry 等剩余已核对消费者也按 PG 绑定读取。
- TDX 输入根与项目 Workspace 路径继续使用中央解析器；TDX 源目录保持只读，候选产物留在源目录之外。

既有矩阵 266 个稳定 P1 ID 中，当前记录为 **218 个代码级 PG 读取路径已实现、待基线/引用库存核销**，另有 **39 个 OPEN + 9 个 ACTIVE_INGRESS_ADAPTER_OPEN**；**正式 P1 核销仍为 0/266**。这 218 是代码路径改造数，不代表正式 Head/Owner 核销，也不将测试数量作为完成依据。

## 尚未关闭的调用点

48 个未核销项的精确稳定 ID、源行、分类和阻断原因保留在 [V4_R21_CALLSITE_MIGRATION_MATRIX_R1_20261017.json](/G:/codex%20work/%E5%A4%A7A%E4%BA%A4%E6%98%93/docs/upgrade/V4_R21_CALLSITE_MIGRATION_MATRIX_R1_20261017.json)。剩余源文件分布：

- TDX 官方包、最新包、TDX 本地日线补缺、只读快照及快照差分入口：`tdx_official_daily_source.py`、`tdx_latest_daily_source_v2.py`、`tdx_local_daily_fallback_v1.py`、`tdx_local_snapshot.py`、`tdx_member_retro_r43.py`、`tdx_snapshot.py`、`tdx_snapshot_delta.py`、`tdx_snapshot_delta_v2.py`。这些点承担原始来源采集/冻结/解析；仍需来源合同、PG append 和同 T0 Owner readback 才能核销。
- `v4_membership_reference_pg_v1.py`（6）、`v4_operational_owner_authority_v2.py`（1）、`v4_profile_dependent_corrections_pg_v1.py`（1）、`v4_profile_semantic_corrections_pg_v1.py`（1）：首次来源/补丁进入 PG Owner 的 ingress 尚未完成 live identity parity 与 PG append/readback。
- 其他遗留/候选边界：`operational_revision_guard_r1.py`（2）、`history_170_v3_3.py`（1，非 V4 历史消费者仅登记）、`forward_r7_store.py`（1，G 盘隔离候选 receipt）、`scripts/capture_dm01_a01_r3_tdx_package.py`（1）、`scripts/start_product_attested_r4.py`（1）。

## 内置浏览器验收（28766）

更新代码后重启候选服务并用 Codex 内置浏览器访问真实页面：

- 首页：PG 候选标记和股票 5,213、板块 378、雷达/Forward 117 数据均渲染。
- 行情/事件：市场宽度、指数、合规涨跌停及研究状态事件渲染。
- 板块：煤炭板块详情及 25 个成员可读；搜索 `600971` 留下 1 条恒源煤电结果。
- 个股：中华企业详情及实际成交行情可读；交互切换为周线成功，图表显示真实行情。
- Focus：`600675` 返回 1 条；Forward 样本 117、期限计划 585；打开来源抽屉后显示 PG 候选身份和数据质量说明。
- Compare / Replay：比较显示 2026-09-29 至 2026-09-30 同窗结果；冻结回放清晰标识为事后重建，严格 PIT 可用日期为 0。
- Diagnostics / 日更：Jobs 页显示候选快照统计且 worker 未启动；数据更新中心 Status、Progress、Releases、Logs 交互可用，Progress 返回 `PREVIEW_ONLY`，发布版本无正式 Head，日志显示暂无任务。

前端可交互链路均成功加载；任务卡最终状态仍为 `BROWSER_PARTIAL`，因为候选样本缺少正式 Head、严格 PIT 日期为 0，并存在明确的来源不完整字段。这些缺口没有被页面伪装成正式发布。

## 最小验证与交付

- 69 个已修改 Python 文件（含 68 个运行模块及准入策略工具）`py_compile`：通过。
- `git diff --check`：通过。
- 未运行 GitHub CLI 流程测试、重复全仓基线扫描或 GitHub Actions。
- 已修复后的日更 Progress 以真实页面接口验证；各现役页面按上方列表完成浏览器加载/功能操作。

实际数据库读回确认同一 `market_research` PG 实例、OID `646711`。本轮没有新增生产 Head 切换或日更任务；当前 `V4_NATIVE_PG_DSN` 未在项目安全配置中设置，且任务卡把正式合同审批/Owner append/Accepted Head CAS/Head 切换与生产部署作为单独边界。不能从 `WORKBENCH_PG_DSN` 推导写权限。正式审批、live ingress append/readback、Head CAS/切换和 28765 部署仍需按其各自合同单独执行；物理删除、强推亦未执行。

Google Drive Issue/PR 摘要连接器此前返回 HTTP 403 `Resource not accessible by integration`；未使用 GitHub CLI 绕过。

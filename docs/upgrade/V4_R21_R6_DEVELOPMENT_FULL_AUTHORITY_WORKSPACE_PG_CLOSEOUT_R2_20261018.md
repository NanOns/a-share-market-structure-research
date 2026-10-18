# V4 R21-R6 开发全权限连续实修进度 R2

- 状态：`DEGRADED_PASS`，继续实修；尚未达到全模块验收。
- 授权：2026-10-18 Drive 任务卡与长期开发授权 SOT R2。开发期 PostgreSQL DDL/DML、迁移、SourceIngress、Owner、合同和候选 Head 写读均已授权；生产切换和最终打包仍后置。
- 运行边界：开发分支 `codex/v4-workspace-cleanup`；唯一 PG `127.0.0.1:5432/market_research`（OID `646711`）；开发服务 `127.0.0.1:28766`。现场监听只有 PG 5432 与开发 28766；28765 未监听、未触碰。

## 已完成的代码与 PG 实修

- `src/workbench_db/v4_native.py`、Owner workspace mapping 与迁移 046/047：加入稳定 workspace logical ID/PG alias、保持只读读路径，并让已授权共享 PG 配置可用于开发写入。两项迁移在唯一 PG 应用并读回；4 个 ACTIVE alias 解析到原有 schema。搬动模拟确认 logical ID、history/publication namespace 与 Owner mapping 稳定。
- TDX 官方 2026-10-16 包：ZIP 校验通过，12,205 个条目，549,184,442 字节，SHA-256 `c0ea0dff…3248219`；抽取 5,567 根目标日 bars。包首见时间在 10-18，故只作诊断候选，未宣称 PIT 或 accepted。
- 将精确 TDX 目标行集作为 1,502,467 字节 SourceIngress 原始绑定写入 PG，并完成字节读回；创建 5,567 行 `core` Owner、Owner authority manifest 和 `development_head_candidate`，均从 PG 精确读回。
- 修复 `dm01_corrected_source_capture_v2.py`：临时 smoke 收据可绑定在配置的 G 盘 ingest temp root；绝对临时路径只用于内存中的 staging-only manifest，Durable runtime loader 仍只接受仓内收据。6 项路径/归一化定向测试通过。
- BaoStock 2026-10-16 同日快照实际捕获完成，幂等重跑为 `NOOP_SOURCE_ALREADY_FROZEN`：5,226 条日线、48 条归一因子；另保留 48 条 SDK 原生 `adjustFacto` 因子响应。2,599,570 字节 BaoStock 快照和 9,404 字节原生因子响应以精确绑定写入 PG SourceIngress 并读回。
- 扩展开发 Owner 候选 v1.1 到 4 域：TDX `core` 5,567 行、BaoStock 日线 5,226 行、归一因子 48 行、原生因子 48 行；Owner authority 和 `development_head_candidate` 均做 PG 全量读回。所有候选均 `DIAGNOSTIC_ONLY`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`，没有更新现行 accepted Head 或 publication。BaoStock 请求预算 ledger 记录本轮 11 次公共账本操作，修正捕获另外使用 G 临时区预算账本。
- 交叉核对：5,216 个共同证券中，close 与 volume 一致；4,883 个 amount 严格不等（最大绝对差 508.46 元、最大相对差约 `1.29e-7`）；集合差 361，其中 TDX-only 351 个全为北交所，BaoStock-only 10 个。严格合同不设容差，原值和差异均保留，未提升为业务源。
- 两项 `DRAFT_DEVELOPMENT_DIAGNOSTIC_ONLY` 合同已按精确字节 SHA 登记 PG，无审批事件。Owner 候选合同扩至 v1.1.0；PG `contract_versions` 19 条、审批事件 16 条。
- 修复 `_existing_downloader_package` 把 TDX 收据路径固定到旧目录的问题，现按配置 snapshot root 校验；定向回归测试 1 项通过。该代码修复已提交并推送：`f467f2ad6`。

## PG、28766 和功能验证

- PG 事实：`v4.contract_versions` 19 条、审批事件 16 条；`dm01_data_accepted_heads` 1 条。现有 `publications`、`publication_heads`、`operational_research_heads` 与 accepted 市场日历为空。BaoStock `query_trade_dates` 实查 10-16 为交易日，并存为 PG 诊断日历候选；补齐身份/namespace 后正式市场日历读取仍明确返回 `NO_ACCEPTED_PUBLICATION_HEAD`，不伪造 accepted 日历或源接受。
- 28766 仍服务 PG 候选 T0 `2026-09-30`：股票 5,213、板块 378、Focus 469、Forward 117、事件 33；只读、生产权限关闭、日更 worker 未启动。
- 对 28766 做了 41 个 API 请求（context、列表/详情、股票图表、Market、Events、Focus、Forward、Sources、Diagnostics、Replay/Compare）及 6 个产品页 HTTP 请求。有效数据路由为 200 且上下文 token 一致；明确返回 `SOURCE_INCOMPLETE` 的域保留该状态；Replay/Compare 因无首可用时间证明返回 `PIT_NOT_AVAILABLE`。服务返回的 8 个页面/静态资源与本仓 `static/research` 文件 SHA 全部一致。
- 28766 页面交互已有 R5 同日真实浏览器矩阵覆盖（板块、股票详情、Focus/Forward、Market、Diagnostics、Compare、Replay、数据更新页）；该矩阵标明 candidate context 和 PIT 限制。R6 本次续行再次调用 Windows UI 自动化时，工具无法可靠判定 Chrome 当前 URL，故未绕过，也未声称新增浏览器验收。

## 验证、清理与未完成项

- 已通过：此前 22 项 PG/namespace/Owner 定向测试；本轮 TDX 收据路径回归 1 项；`git diff --check`、暂存策略及提交推送正常。
- 已清理 G 盘可重建 pytest/pyc/pip 缓存 2,674,361,197 字节。大型 `G:/codex_tmp/r7_active_baseline_20261015` 含改动源码及独有材料，尚未逐项归属，保留；未动 TDX 只读源或无关文件。
- 后续继续项：恢复可用的开发 PG publication/calendar/Head 输入链，再运行正式目标日期运行接受、完整 DM-01 日更冻结与 Core/全模块业务 Head 联调；继续现役 V4 业务文件读取收口和 Focus/Forward/Market/Cohort 接线；按任务授权逐项清理已确认无消费者的开发衍生物；补完 28766 浏览器交互矩阵。
- 证据仍不支持全模块验收。生产切换和最终生产打包保持关闭，必须等全功能验收通过并由用户另行明确启动。

## 用户再次确认开发 PG 全权限后的续行实修（2026-10-18）

- 将 `focus_daily_stage` 自动执行门禁由本地 JSON 文件读取改为精确绑定的 PG SourceIngress 字节读取。代码固定合同路径、SHA-256 与 180 字节长度；PG 不可用、事实缺失或身份错误时 fail-closed，不回退读取工作区文件。当前门禁继续保持关闭，原因来自 PG 读回的原合同值：等待真实次日接受及多日 Forward/到期结果接受。
- 在唯一 `market_research` PG 中一次性登记 `config/focus_daily_pipeline_gate_v1.json` 原始字节：SHA-256 `8d398694d8df852d2f623d74538afc4e77358a5de394ee2364c43a5fba7daaa2`、180 字节；同路径/摘要精确读回，并从运行函数默认路径实测得到 `(False, REAL_NEXT_DAY_ACCEPTED; MULTI_DAY_FORWARD_AND_DUE_OUTCOME_ACCEPTANCE_PENDING)`。
- `tests/upgrade_v3/test_focus_07a_post_sync_stage.py` 定向验证 9 项通过，覆盖 PG 字节入口、不可用时关闭、既有 Focus preflight/apply 顺序和同步身份检查。`git diff --check` 通过。该修复关闭一个仍由 V4 运行时直接读取业务配置文件的调用点。
- 28766 当前 HTTP/API 服务仍为 PG 候选上下文；本次 UI 自动化工具在无法确认 Chrome 当前 URL 时拒绝继续，未绕过。既有 R5 浏览器页面操作矩阵仍是最近一次真实浏览器验收证据；本次未运行日更/采集、创建正式 publication 或切换 Head。

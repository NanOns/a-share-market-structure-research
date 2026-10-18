# V4 R21-R6 开发全权限连续实修进度 R2

- 状态：`DEGRADED_PASS`，继续实修；尚未达到全模块验收。
- 授权：2026-10-18 Drive 任务卡与长期开发授权 SOT R2。开发期 PostgreSQL DDL/DML、迁移、SourceIngress、Owner、合同和候选 Head 写读均已授权；生产切换和最终打包仍后置。
- 运行边界：开发分支 `codex/v4-workspace-cleanup`；唯一 PG `127.0.0.1:5432/market_research`（OID `646711`）；开发服务 `127.0.0.1:28766`。现场监听只有 PG 5432 与开发 28766；28765 未监听、未触碰。

## 已完成的代码与 PG 实修

- `src/workbench_db/v4_native.py`、Owner workspace mapping 与迁移 046/047：加入稳定 workspace logical ID/PG alias、保持只读读路径，并让已授权共享 PG 配置可用于开发写入。两项迁移在唯一 PG 应用并读回；4 个 ACTIVE alias 解析到原有 schema。搬动模拟确认 logical ID、history/publication namespace 与 Owner mapping 稳定。
- TDX 官方 2026-10-16 包：ZIP 校验通过，12,205 个条目，549,184,442 字节，SHA-256 `c0ea0dff…3248219`；抽取 5,567 根目标日 bars。包首见时间在 10-18，故只作诊断候选，未宣称 PIT 或 accepted。
- 将精确 TDX 目标行集作为 1,502,467 字节 SourceIngress 原始绑定写入 PG，并完成字节读回；创建 5,567 行 `core` Owner、Owner authority manifest 和 `development_head_candidate`，均从 PG 精确读回。候选标为 `DIAGNOSTIC_ONLY`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`；没有更新现行 accepted Head 或 publication。
- BaoStock 2026-10-16 实际响应经既有 SDK 0.9.3 源码哈希绑定 schema adapter 归一后，5,226 条日线与 48 条因子写入 PG 诊断交叉核对事实并读回。请求预算 ledger 记录本轮 11 次请求/会话操作。
- 交叉核对：5,216 个共同证券中，close 与 volume 一致；4,883 个 amount 严格不等（最大绝对差 508.46 元、最大相对差约 `1.29e-7`）；集合差 361，其中 TDX-only 351 个全为北交所，BaoStock-only 10 个。严格合同不设容差，原值和差异均保留，未提升为业务源。
- 现已新增两个 `DRAFT_DEVELOPMENT_DIAGNOSTIC_ONLY` 版本合同：BaoStock/TDX 交叉核对候选与开发 Owner/Head 候选；尚待提交推送并登记为 PG 未批准合同，不给予发布或 PIT 权限。
- 修复 `_existing_downloader_package` 把 TDX 收据路径固定到旧目录的问题，现按配置 snapshot root 校验；定向回归测试 1 项通过。该代码修复已提交并推送：`f467f2ad6`。

## PG、28766 和功能验证

- PG 事实：`v4.contract_versions` 与审批事件此前各 16 条；`dm01_data_accepted_heads` 1 条。现有 `publications`、`publication_heads`、`operational_research_heads` 与 accepted 市场日历为空。由于无 accepted publication Head，官方交易日日历读取返回 `PG_MARKET_CALENDAR_IDENTITY_REQUIRED`（未配置可用 Head/namespace）；不伪造日历或源接受。
- 28766 仍服务 PG 候选 T0 `2026-09-30`：股票 5,213、板块 378、Focus 469、Forward 117、事件 33；只读、生产权限关闭、日更 worker 未启动。
- 对 28766 做了 41 个 API 请求（context、列表/详情、股票图表、Market、Events、Focus、Forward、Sources、Diagnostics、Replay/Compare）及 6 个产品页 HTTP 请求。有效数据路由为 200 且上下文 token 一致；明确返回 `SOURCE_INCOMPLETE` 的域保留该状态；Replay/Compare 因无首可用时间证明返回 `PIT_NOT_AVAILABLE`。服务返回的 8 个页面/静态资源与本仓 `static/research` 文件 SHA 全部一致。
- 浏览器逐页交互未完成：Windows UI 自动化访问 Chrome URL 时被工具层停止；未绕过。HTTP/API 和静态资源校验不等同于视觉验收。

## 验证、清理与未完成项

- 已通过：此前 22 项 PG/namespace/Owner 定向测试；本轮 TDX 收据路径回归 1 项；`git diff --check`、暂存策略及提交推送正常。
- 已清理 G 盘可重建 pytest/pyc/pip 缓存 2,674,361,197 字节。大型 `G:/codex_tmp/r7_active_baseline_20261015` 含改动源码及独有材料，尚未逐项归属，保留；未动 TDX 只读源或无关文件。
- 后续继续项：将两项新合同提交推送并写入 PG DRAFT registry；恢复可用的开发 PG publication/calendar/Head 输入链，再运行 BaoStock 正式的目标日期运行接受、日更冻结、归一化、Core/Owner/Head 与完整模块读回；继续现役 V4 业务文件读取收口和模块接线；按任务授权逐项清理已确认无消费者的开发衍生物；补完 28766 浏览器交互矩阵。
- 证据仍不支持全模块验收。生产切换和最终生产打包保持关闭，必须等全功能验收通过并由用户另行明确启动。

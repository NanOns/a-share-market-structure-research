# V4_R21_R5 全模块文件引用与 Workspace 集中实修收尾报告

- 日期：2026-10-18
- 分支：`codex/v4-workspace-cleanup`
- 状态：`CODE_SCOPE_PARTIAL; BROWSER_PARTIAL; LIVE_PG_VERIFIED; FORMAL_HEAD_CLOSURE_PENDING`
- 当前开发服务：`127.0.0.1:28766`；共享 PostgreSQL：`127.0.0.1:5432/market_research`（OID 646711）。未触碰生产网页端口 28765。

## 本轮实际代码修复

本分支差异含 33 个现役 V4 Python 运行模块（32 个修改、1 个新增）、1 个迁移、配置/脚本更新及聚焦测试更新。真实实现包括：

- PG Head/Owner/Membership/合同来源读取；运行路径拒绝本地 Head 回退；Owner predecessor 固化及 PG 事实复用。
- V4 连接读取复用 `WORKBENCH_PG_DSN` 所指的现有实例，事务保持只读；写路径仍要求显式 `V4_NATIVE_PG_DSN`，未增加独立 Reader DSN/实例。
- daily、calendar、行情来源、TDX/BaoStock 路径通过 PG 绑定或中央 Workspace 路径解析；候选数据不写入 TDX 源目录。
- BFF 与 `/api/v4/*` 候选链使用 PG projection；Forward cohort、诊断、市场、股票/板块来源校验绑定 PG；新股与 sealed-resume 的 Operational Head/Owner 父级读取已改走 PG。
- 新增 Operational Research Head PG 表/读/CAS；应用迁移 044。表已存在但 Head 行数为 0，未从文件导入或切换正式 Head。

使用现有 R21 callsite matrix 做差异映射：266 个 P1 稳定 ID 中，114 个 ID 的 `source_file` 出现在当前代码差异路径（覆盖 17 个源文件）；这仅代表进入改动路径，并非逐行修复确认。矩阵仍未正式关闭任何稳定 ID，剩余 266 个都保持未核销状态；不得将行路径交集称为修复数量。

## PostgreSQL

沿用同一 `market_research` 实例。已在现有 PG history schema `v4_history_dbe184da961f97b8` 追加并读回不可变版本 `ba5ac5f7e794deba476c6354efd01a8f15db9059bb7bf8292c759af1ecb41eb2`（T0 `2026-09-30`、Head `38e7c9…`、source `9f7ee9…`）；未更新任何正式 Head。已应用 migration 043/044；043 中 7 个合同版本以 DRAFT 写入，审批事件、Accepted publication 及正式 publication Head 为 0。Operational Head 注册表存在、当前行数 0。没有导入/切换正式 Head，也没有执行生产部署、物理删除或强推。

## 28766 内置浏览器验收

使用 Codex 内置浏览器实际浏览 PG 候选前端，当前快照 T0 `2026-09-30`：

- 首页：股票 5,213、板块 378、Focus/Forward 117、事件 33；PG 候选标识可见。
- 个股：搜索 `600675` 返回中华企业，详情字段可读；先前图表因当前仓库内的历史包字节与其绑定 SHA 不一致而没有 PG 版本。已在 G 盘临时基线找到两份摘要精确匹配 `9f7ee9…` 的原始包，只读导入同一 PG，建立 Head `38e7c9…` 绑定的不可变版本（5,224 symbols、1,309,832 bars）；真实 API 返回 `READY`、253 日线/54 周线，QFQ/RAW 与周期切换均可读。
- Focus：真实搜索 `600675` 返回 1 条中华企业；Forward 117、期限计划 585、已发布期限状态 5、成熟样本 0。
- 行情/事件：2344 涨、2712 跌、155 平、13 不可判定；指数、涨跌停及 33 条研究状态事件可读。未接入的分钟级炸板和批准新闻源明确显示缺口。
- 诊断/Jobs：4 个来源健康记录；Jobs 显示快照计数并说明未运行日更 worker。
- Replay：选择 2026-09-30/中华企业显示 `PIT_NOT_AVAILABLE`、可用严格 PIT 日期 0，未展示为当时已知结果。Compare 选择“事后重建（非 PIT）”并实际运行股票 vs 市场，显示中华企业收益来源不完整、起点 Universe 同窗参考 -0.136%、共同区间 2026-09-29 至 2026-09-30；来源抽屉仍须保留为下次交互复验。
- 板块详情（前序现场）：煤炭开采详情显示 25 个成员，字段来源抽屉显示来源时间、质量和摘要；缺失字段保留 UNKNOWN。

因此浏览器结果仍为部分通过，不是全模块 PASS。市场页、Focus、Diagnostics、Replay/Compare 与个股详情可交互；严格 PIT 可用日期仍为 0，明确保持 `PIT_NOT_AVAILABLE`，没有冒充正式 Head。

## 最小验证

- 先前针对 6 个目标模块的聚焦 pytest：97 passed；本轮图表生产者/BFF及 `v4_history_pg_r1` 哈希缺陷修改通过 `py_compile`。
- `git diff --check` 通过。
- 未运行 GitHub CLI 流程测试、全仓基线扫描或 GitHub Actions。

## 尚未完成的代码范围与阻断

1. 266 个稳定 ID 尚未逐 ID 精确核销。现有矩阵源路径覆盖 114 项，仍需按矩阵继续改造并回填精确调用点；其中 Owner、业务消费者、市场来源及 ingress 都还有可继续编码的点，本报告不把它们标为完成。
2. PG Operational Head 行为空，因此任何要求当前正式 Operational Head 的日更/发布流程都会按设计失败关闭；接受源 Head 的首次导入、合同批准事件及正式 publication 尚未发生。即使表/消费者代码已完成，候选数据不能当成正式已接受 Head。
3. Replay 严格 PIT 日期仍为 0；没有首发时刻与历史成分绑定证据，不能升级 PIT。
4. 当前 Workspace 输入缺失/合同未批准导致的数值与来源缺口须在对应真实 owner/源合同链补齐；非 V4 代码只登记，不在本任务修改。

需另行授权的事项仍仅限用户原始边界：正式 Head CAS/切换、生产 28765 部署、物理删除及 Git 强推/历史重写。正常 commit/push 不涵盖这些动作。

Google Drive Issue/PR 最终摘要连接器此前返回 HTTP 403 `Resource not accessible by integration`；未用 GitHub CLI 绕过。

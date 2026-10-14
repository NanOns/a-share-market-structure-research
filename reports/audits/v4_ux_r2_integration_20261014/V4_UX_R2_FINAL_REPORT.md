# V4 六入口研究可用性专项 R2 集成报告

日期：2026-10-14（北京时间）
阶段：R2-00 / R2-01 候选工程集成；R2-02 真实环境验收部分受阻；R2-03 生产准入未执行
集成分支：`codex/v4-ux-r2-integration-20261014`
代码提交：`3bacbf12222bb6f80c1f133692d3da29c0878d54`
**唯一结论：`PARTIAL_ENGINEERING_ACCEPTED__ACTIVE_PRODUCTION_NOT_UPDATED__PRODUCT_ACCEPTANCE_BLOCKED`**

## 阶段合同

执行依据为用户提供的《V4 六入口研究可用性专项 R1 独立外部审计与现役分支回迁任务卡 R2》（2026-10-14）。另外核对最新现役升级合同 `docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md` 及 `docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`。Phase 0 正式收据为 `FULL_PASS`，SHA-256：`313304495faee8c081794ec1bf4f19803ed8a634ac98187347d9190b5ebe5b59`；它只代表 V4-00 范围已通过，不代表本专项功能验收。

本阶段只构建从现役最新 HEAD 出发的候选代码和证据。附件明确将生产包切换列为非默认执行项，并要求同版本源/PG/HTTP/UI 验收完成且另有明确部署授权后才考虑，因此没有切换服务、运行日更、改 Head、授权 Cohort/FEP 或操作 TDX。

## 基线和合并边界

- `origin/codex/v4-full-closeout-20261012` 当前 HEAD 与本次基线一致：`15876b4ef289dfe0c552a6f148e5a642c7271118`。
- 旧专项 `origin/codex/v4-fp14-r2-repair` 为 `c9e49df720da58ecb3e90eae53b9fdd8e11aab07`；共同祖先 `fbd23a6ba08d0948fe7ad421d1765fe363648522`；相对现役分支落后 142、领先 4 个提交。
- 在 G 盘新建隔离 worktree 和分支；逐项移植显示、D2 解释、Focus 行业名称、事件呈现和市场展示。没有 merge 旧专项、覆盖 BFF 整文件、改正式 R1 索引或修改原有脏工作区。
- R1 PG read-index 源文件 SHA 保持 `d15d09e111014c78568fee2265234307bdd99e2f8960722d0271df83d3df3c03`。新 Radar 使用独立的 `V4_READ_INDEX_R2`、独立 PG schema 后缀和独立 authority 文件，R1 在无 R2 authority 时仍可读取。

详情见 `MERGE_BASE_AUTHORITY_DIFF.json` 和 `UX_PG_READ_INDEX_COMPATIBILITY.json`。

## 完成与验收矩阵

| 范围 | 状态 | 证据及限制 |
|---|---|---|
| R2-00 正确基线 | `CODE_PASS` | 从现役 HEAD 建分支；未合并旧分支；R1 索引、token、Owner 和身份语义保留。 |
| Radar 分页 | `CODE_PASS / HTTP_NOT_VERIFIED` | 新 `/api/v4/radar` 从同 T0/token 物化 Focus 事件，按主体去重、先排除前十个轮动覆盖项；SQL 先过滤再计数/分页，稳定排序。首页仍用生产者物化轻量响应。没有 5225 行请求期投影。 |
| 涨跌停筛选 | `CODE_PASS / HTTP_NOT_VERIFIED` | `limit_state` 只允许 `/api/v4/market/limits`，枚举错误拒绝；先筛选后分页。UI 将“状态可分类（含停牌）”与“实际可交易且规则可评价”分开显示。 |
| 身份与 D2 | `CODE_PASS / SOURCE_NOT_VERIFIED` | 股票展示保留现役 `code_status`，另加 `identity_status`、首见日、上市日、别名状态；只在正式身份行明确为 `CONFIRMED_IPO` 时显示已确认身份。D2 区分 `scenario=NONE` 且未完整评估与真阴性。 |
| Focus 名称/事件 | `CODE_PASS / SOURCE_NOT_VERIFIED` | 活跃唯一证券分母、中文行业名联接、事件过滤、分页、有效性/路径说明、来源导航代码已接。 |
| 源层定点复核 | `PARTIAL_REFERENCE_ONLY` | 引用了附件审计与 10/13 新股既有收据；本轮没有重读当前 PG Owner bytes/digest，未重复计算历史全量。 |
| PG/HTTP | `BLOCKED_NOT_VERIFIABLE` | 附件记录的策略预检为 `EXACT_DAILY_POLICY_REQUIRED`。未关闭策略、未启动伪服务、未请求服务、未连接 PG。 |
| 六入口浏览器 | `BLOCKED_NOT_VERIFIABLE` | JavaScript 语法通过；没有同版本真实浏览器、双视口截图、交互或真实性/空状态截图。 |
| 性能 | `NOT_VERIFIABLE` | 未测同版本首页/列表/Radar 第二页 P95；不声称达到冻结基线。 |
| 生产部署 | `NOT_EXECUTED` | R2-03 非本轮默认执行；原 28765、正式 Head、自动日更状态均未修改。 |

### 代码实现

- Radar 读索引以 `V4_READ_INDEX_R2` 独立版本化，authority 原子写入 `config/v4_read_index_authority_r2.json`，候选页通过 PostgreSQL 总数查询和 `LIMIT/OFFSET` 返回。日更与 sealed-resume 在发布前先生成原 R1、再生成 R2；R2 失败时不会进入 `DERIVED_READY` 或 Head 发布。运行时有 R2 时优先读 R2；否则现有标准页继续读 R1，Radar 缺少 R2 时 fail closed。
- `limit_state` 参数按路由精确校验，合法状态为 `LIMIT_UP/LIMIT_DOWN/SUSPENDED/UNKNOWN/NOT_LIMIT`；无关路由携带该参数会被拒绝。未知筛选页的 total 基于筛选后行集。
- `current_identity_rows` 的 `code_status` 单独保留；未观察不推导为退市，不从 `list_date==T0` 推导 IPO。
- 六个 producer 缺口已独立登记在 `PRODUCER_AUDIT_ITEMS_R1.json`：Radar 优先级、Sector 生命周期、结构风险、Validation Cohort、Cohort Settlement、FEP Gate。未新增算法或授权；Forward 数量保持 null/NOT_GRANTED。

### 真实证据边界

10/13 既有新股证据显示，来源包新增稳定 ID `SEC-7C8816903D4BA9B6267531D5705888B9`，样本总数 5,225；相应阶段文件仍将日更状态记为 `DERIVING`，不是新 UI 代码的 HTTP 读回。附件独立审计报告中的 5,225 股票、400 板块、3,151 Focus、D2 unknown 分布、市场分母与 57+12 梯队，本轮作为既有审计参考，不冒称重新从 PG 核验。`SZ.301660` 当前身份 `CONFIRMED_IPO` 是附件报告引用的现役权威，本轮只有代码级合成测试，没有同 token 的 PG/API 对账。

详见 `PRODUCTION_IDENTITY_301660_RECONCILIATION.json`、`UX_R2_REAL_SOURCE_AND_HTTP.json`、`UX_R2_REAL_BROWSER_MATRIX.json` 和 `UX_R2_PERFORMANCE.json`。

## 测试和安全边界

- 新增定向测试：7 项通过，覆盖路由白名单、枚举、Radar 搜索/事件/有效性 SQL 条件、Radar 先去重和覆盖排除、证券详情链接以及 `CONFIRMED_IPO` 与 `code_status` 分离。
- 相关 Python 模块 `py_compile` 通过；`app.js`、`components.js`、`labels.js`、`stock.js` 的 `node --check` 通过；`git diff --check` 通过。
- 没有执行 7288/全仓回归、PG/HTTP 请求、浏览器实测、日更、EXE 构建或生产切换。
- 所有新工作区在 G 盘；临时路径和 Python 缓存位于 `G:\codex_tmp`。TDX 根、原工作区、正式服务、Head、auto_daily 和 Google Drive 未触碰。

## 下一阶段

`R2-02` 的剩余工作是当前被认可的只读源/PG/HTTP 同版本验证：确认 policy/role/Head/read-index 准入，核对 Radar 真第二页及筛选总数、limit UNKNOWN 正例与无关路由负例、`SZ.301660` 和常规/未观测/alias 冲突身份用例，并读回 Forward 未授权状态。随后才可做双视口实际浏览器和 P95。若仍不符合策略准入，保持 `NOT_VERIFIABLE/BLOCKED`。

只有这些同版本门全部通过，且按用户附件另有明确授权，才进入 R2-03 生产部署；本报告和分支推送均不构成部署许可。
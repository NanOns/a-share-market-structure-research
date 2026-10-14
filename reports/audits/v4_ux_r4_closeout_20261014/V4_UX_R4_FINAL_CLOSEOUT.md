# V4 UX R4 收口报告

**验收结论：`V4_PRODUCTION_CUTOVER_BLOCKED`，R5 尚未收口。** B-01/B-02 已修；本轮继续修复了隔离预览静态资源根映射，并补入 Forward 首次捕获就绪展示。最新代码已在 28768 内置浏览器预览验证，但 D2、正式三族风险、Formal Radar、Owner/截图/生产验收仍未全部通过；不得宣称 FULL_PASS 或切换完成。

## 阶段合同与环境

- 执行依据：用户指定 R5 任务卡（2026-10-14）及最新适用升级文档 [`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`](../../../../docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md)。阶段合同：修复 B-01/B-02；用 2026-10-13 已接受输入做只读验收；不得伪造 Cohort/FEP、不得启用自动日更/变更 Head；所有核心门通过后才允许切换 28765。
- R4 基线 HEAD：`d2f9dfb99221e9fe1cd78b302b5b4b135f380ecf`；R5 本轮源码与浏览器证据提交 `72bb51cfeb38df252e464d3e62c3700e844c2a9f` 已推送到同一分支。该提交只保存代码和隔离验收证据，不表示核心门通过或生产切换。
- 28765 回滚点：PID `34284`，旧包 `V4_PACKAGE_1.0.0_88cc19deae3b`，EXE `G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.0.0_88cc19deae3b\DaAV4\DaAV4.exe`。进程未停止、包未修改、未切换。内置浏览器原先读到 T0 `2026-10-13`、engine RUNNING、`auto_daily` 暂停；本轮未运行盘中日更、未改变正式 Head/token。TDX 只读输入未改。
- 受限只读 PG 的最新隔离 R2 schema：`v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5`；database `market_research` / OID `646711`，port `5432`，T0 `2026-10-13`，Head token `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`。投影计数 `{focus:3151, radar:177, sectors:400, stocks:5225}`；producer SHA `e2c47cf8e062b078edfc426ee297844462db28805f4e513ad59e87b9f22d4f5`；content digest `5ecd6dff469f70bf595fb76789e33dd0203e3c222f45199516491fd70ef3105f`。cluster `system_identifier` 未封存，PG 集群身份仍不完整。隔离 authority 仅位于 G 盘临时根；生产根没有写入 R2 authority。该 schema 使用隔离名称，不覆盖 sealed schema。
- 浏览器验收只使用 Codex 内置浏览器（28765 生产页及 28768 隔离预览）；未调用外部浏览器。28768 是源码版静态资源 + 生产数据 owner 只读读取 + 独立 PG schema 的预览服务，不是生产部署。

## 修复、测试及 HTTP 证据

1. **B-01**：新增精确 R1 legacy capability 检测。仅当响应明确标记为允许的 R1 legacy 状态时，HTTP 层跳过 R2 专用 512 KiB/字段形状检查；未标记响应和 R2 仍受 guard 约束，错误保持 fail closed。
2. **B-02**：R2 content digest 采用按 workspace + 完整 digest 派生的版本化 schema 名，旧 schema 保持只读兼容；binding 校验 producer SHA；authority 更新保留 revision history，不覆盖旧修订。
3. 定向合同测试：`tests/test_v4_ux_r2_contract.py` 11/11、`tests/test_v4_ux_r3_routes.py` 9/9 通过，`git diff --check` 通过。全仓 pytest 未成功加载，因该 checkout 缺少 `src/common/disposable_paths.py`；不计为全量回归。
4. R1 兼容复现：28766 旧 R1 `/api/v4/home` n=8 HTTP 200，5,060,827 B，P50 279.43 ms、P95 370.04 ms。修复防止旧 R1 被 R2 guard 误拒绝；5.06 MB 本身不满足 R2 首页体积目标，因此此数字仅证明降级兼容，不代表首页性能验收通过。
5. R2 隔离预览（28768，当前重跑 n=8；耗时 ms）：

| 路由 | 响应字节 | 冷请求 | P50 | P95 | 结果 |
|---|---:|---:|---:|---:|---|
| home | 116,121 | 113.87 | 114.25 | 329.23 | 8/8 HTTP 200 |
| stocks | 67,167 | 216.36 | 217.43 | 347.50 | 8/8 HTTP 200 |
| sectors | 88,043 | 111.52 | 119.01 | 226.60 | 8/8 HTTP 200 |
| focus | 82,807 | 367.13 | 258.00 | 368.74 | 8/8 HTTP 200 |
| radar p1 | 49,605 | 212.90 | 211.44 | 344.19 | 8/8 HTTP 200，总数 177 |
| radar p2 | 49,716 | 218.87 | 219.49 | 325.18 | 8/8 HTTP 200，总数 177、offset 30 |
| stock detail | 173,900 | 224.97 | 225.09 | 345.08 | 8/8 HTTP 200 |
| sector detail | 81,051 | 196.98 | 197.32 | 218.54 | 8/8 HTTP 200 |

所有数据来自同一隔离预览及 T0/token；不代表正式 28765 性能、部署或验收。

### R5 继续执行记录（2026-10-14）

- 修复板块详情每次请求都重读 rotation Owner 的慢路径：R2 producer 将 `why_now` 可审计字段放入 detail 行，HTTP 优先键查找并在一次只读 PG 连接中同时读取 Context 与详情；列表摘要排除 detail-only 数据。回归测试覆盖 detail-only 展开、主键查找、共用连接及详情不再加载 Focus/rotation 来源。
- 重新构建的隔离 R2 schema 为 `v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5`，T0/token 与生产已接受 Head 一致，计数 `{focus:3151, radar:177, sectors:400, stocks:5225}`。隔离 authority 仍只在 G 盘临时根，生产根无 R2 authority 写入。
- 修复后板块详情 HTTP 原始回应 n=8：8/8 200，81,051 B，P50 80.30ms、P95 192.09ms；此前 P95 1,198.83ms。范围仍仅为 28768 隔离预览。
- 增加 20 个分层真实 Owner 投影样本读回证据 [`OWNER_SAMPLE_AUDIT_R5.json`](OWNER_SAMPLE_AUDIT_R5.json)：股票 10（含 `SZ.301660`、`SH.688349`）、板块 5、Focus 5；隔离 PG R2 投影读回哈希 20/20 一致。此结果证明投影字节对账，不替代 D2/风险/资格算法字段的独立业务复算，也不替代 U01–U16 完整验收。
- 修复 Focus 页面状态筛选串入主列表请求的问题：`event_state` 与 `events_offset` 仍由事件子路由消费，但不再被独立 Focus 列表路由误判为未知参数。定向合同测试覆盖查询隔离；内置浏览器在 28768 选择 `INVALIDATED` 与 `EXITED` 后，Focus 主列表均继续显示 3,151 条，事件区分别以 0 条空结果正常呈现，没有 `UNKNOWN_PARAMETER`。零行属于真实接受源空结果，只证明筛选路由/空态正确，不能替代 U12 要求的失效/退出真样本或同日多事件反例；完整证据见 [`R5_BROWSER_SMOKE_20261014.json`](R5_BROWSER_SMOKE_20261014.json) 的 `focus_event_filter_reconciliation`。
- 补齐涨停梯队每条名单的所属行业展示：R2 与 R1 只读索引的身份批量查找现在尊重请求域；只在 `market/ladders` 返回已选出的涨停对象时读取证券 `primary_industry` ID 和对应板块名称，缺映射时显示未知，不推断行业。内置浏览器重新验收 2026-10-13 的 69 条：首板 57 条和前缀未绑定 12 条均可展开，名称/代码/行业/连板说明逐条可读；69 条由同一页 size=200 完整承载，没有第二页数据被截断。未知组保持“至少 N 连板（PREFIX_NOT_BOUND）”，未声称精确值；页面说明仍明确不推断分钟级首封/炸板/封单。详见 `limit_up_ladder`。该 10-13 例只证明当日读域，不代表其他交易日或生产切换。
- R4 阶段只检查了内置浏览器入口；当时未做六入口双视口。本轮 R5 已补上六入口双视口与 Radar/Forward/详情页的目视和 DOM 检查，仍缺可交付截图文件。
- 当前阶段结论不变：正式 D2 lifecycle、三族风险、Formal Radar priority、合法验证队列/settlement/FEP Owner 与生产权限仍未齐；不得据此切换 28765。

### R5 页面修复与回归（继续执行）

- 本轮源码提交 `af159a22d1a63e7b830c35dcf32b924d1045764d`：缺源原因和交易字段统一显示中文；Focus 表抑制 UNKNOWN 重复标签；Home 对 Forward/Risk 缺失 Owner 使用正式未发布状态；市场轴保留为候选证据、不再展示成正式环境；单根 K 线柱宽受限；Focus 首屏并发装载并在完成后滚动至 Forward 锚点。
- 修复属于读域呈现与路由行为，不补造业务字段，不打开 Formal D2、正式风险、Radar priority、验证队列、结算或 FEP 权限。浏览器预览 28768 运行新源码；28765 仍为旧包，无切换。
- 受影响合同回归：`python -B -m unittest -q test_v4_ux_r2_contract test_v4_ux_r3_routes`，26/26 通过；`git diff --check` 通过。仅为定向合同测试，不是全量回归。
- 下个独立工作项：继续实现/接通有版本合同的 Sector D2 生命周期与 20 个真例重算、三族独立风险事实、正式 Radar 优先级和当前首次捕获读链；同轮继续 U03/U06/U07/U08/U09/U11–U16 的真实字段抽样。外部正式 Owner/准入事实缺失时保持 unknown，不虚构。

### R5 后续复验发现与修复（2026-10-14）

- 内置浏览器对比隔离 R2 首页后发现：`/api/v4/home` 命中预物化索引时提前返回，跳过旧 R1 路径的未发布环境/风险来源状态覆盖；页面因此把候选四轴显示成正式状态，并把 Focus 风险变化显示成完整风险变化。
- 修复 `CoreProductBFFR1.get()` 的 R2 提前返回分支和在线首页分支：统一将市场四轴标记 `NOT_PUBLISHED_V4_03`；Formal risk 保持 `SOURCE_INCOMPLETE`，三类风险计数为 null；原 Focus 风险事件保留在独立 `focus_risk_events` 区域，不能占用完整风险列表；无授权 Cohort Owner 时 Forward 计数强制 null。首页新增“完整风险变化”与“Focus Owner 风险事件（部分来源）”分栏。
- 隔离 R2 真 HTTP 响应核对：`regime=NOT_PUBLISHED_V4_03`、`formalRisk=SOURCE_INCOMPLETE`、`risks=0`、`focusRiskEvents=14`、`forwardValue=null`、`radarValue=177`。内置浏览器 DOM 复验显示四轴均为“未发布”，风险完整源缺失说明及 Focus 事件分栏均可见。
- 定向合同测试更新为 `test_v4_ux_r2_contract` + `test_v4_ux_r3_routes`，28/28 通过；`git diff --check` 通过。该验证不补齐三族风险 Owner，也不等于生产切换。
- 为复用临时 G 盘隔离数据根，预览启动脚本增加显式 `--root` 参数；R2 预览只读取该临时根，读连接凭据在独立进程内从 DPAPI 装载且没有写入日志。生产 28765 与生产 Authority 未变。
### Historical Owner root propagation repair (2026-10-14)

- R5 在 10/12 跨日读取中发现：修正 Owner 的 PG descriptor 绑定生产 workspace，但 `focus/prewatch` profile-dependent corrections 与 `profile` semantic corrections 的二次查询/缓存 attest 没有继续传递 `workspace_root`，导致合法外部 Owner 被误判为缺 descriptor。修复已提交并推送：`e3e2bc5d0`（`Propagate external owner root through corrections`）。
- 定向合同回归 `test_v4_ux_r2_contract` + `test_v4_ux_r3_routes`：36/36 通过；`git diff --check` 通过。首次无 `PYTHONPATH` 的运行导入失败，补齐 `src;tests;repo-root` 后测试通过，失败仅为启动配置。
- 只读隔离预览从内置浏览器选择 2026-10-12 后，煤炭 `INDUSTRY:T0101` 详情成功读出 32/32 已映射成员、32/32 有行情；Focus API 同日返回 HTTP 200、3,025 条。详见 `R5_BROWSER_SMOKE_20261014.json` 的 `historical_date_switch`。
- U03 现为 `PASS`（限定为读域可解释性）：同一 `INDUSTRY:T0101`、同一成员快照对照 10/12 与 10/13 两日真实 Owner。两个页面均展示 NONE→NONE、Delta 字段和完整谓词；10/13 的 `diffusion=TRUE`，`early_retained/mature_retained=UNKNOWN` 且原因均为 `REQUIRED_QUALITY_UNAVAILABLE`，页面仍明确标注验证中/完整性待核。Owner 文件路径、SHA、关键指标和谓词差异已写入 JSON `rotation_cross_date`。该 PASS 不表示严格 PIT、正式全历史递归 episode 或生产接受。

## 内置浏览器验收

- 28765 生产页：旧首页读取 stocks 5,225/sectors 400、Focus 变化 177/展示 30、风险 14；Radar/Forward 首页仍显示来源未接入，直达 `/v4/research/radar` 提示“没有找到该入口”。生产包版本仍为旧 `1.0.0_88cc19deae3b`。
- 28768 源码预览：Home 加载真实摘要（stocks 5,225/sectors 400/radar 177），清楚说明 Radar 是事件雷达、正式优先级未发布，Forward 正式样本未准入且不伪造计数。Radar p1/p2 均渲染真实事件、有效性/路径/场景/资格及来源字段，第二页显示共 177 条、offset 30。**R5 续验发现并纠正：此前预览配置从隔离数据根加载了旧静态副本，因此旧版组件验收不代表当前源码；本报告最后的“最新源码复验”覆盖旧版视图结论。**
- 28768 六入口逐项检查：Home、板块研究、个股研究、关注跟踪、市场与事件、数据与诊断。板块列表展示 400 行规模、代理指标与成熟度/健康度正式来源缺失；煤炭详情展示成员数据、时间变化解释及“非严格 PIT”标记。个股列表显示 5,225 行；`SZ.301660` 详情核对代码身份、行情单位和历史不足说明。Focus 显示分母 3,151、行业未映射 0，Top5 中文名称为电气设备/化工原料/软件服务/汽车配件/专用机械；观察页标出 3 条真实状态变化、27 条来源不足观察，未把来源不足计作事件。Forward 各栏显示队列未准入、首次捕获源未验证、结算来源缺失、FEP 未准入。市场四轴显示“正式环境尚未发布”，候选轴只留在来源抽屉；诊断页提供生产源健康、来源版本、日更失败状态入口。
- R5 继续复验只使用 Codex 内置浏览器：明确设定 1440×1000 与 768×960，六个导航入口均逐页目视截图并检查 DOM；Radar 子路由、Focus `#forward-cohort`、个股 `SZ.301660` 与煤炭板块详情也检查。各入口页面 `documentElement.scrollWidth` 分别为 1425/753，与 viewport 1440/768 相符；窄屏表格在容器内滚动，无页面级横向溢出。Radar 标题/高亮已修；Focus Forward 锚点在异步完成后落入视口；市场轴正式状态保持“未发布”。截图已由内置浏览器捕获并在验收过程中逐张目视检查，但未保存为仓库文件（文件数 **0**），所以任务卡要求的可交付截图附件门仍未通过；不得把内嵌工具图误报为仓库证据文件。
- 样本验收仍未全部通过：已完成 20 个分层 Owner 投影哈希对账（20/20），但还缺 U01–U16 对应的字段语义/算法复算，不能把投影哈希一致写成业务事实正确。

## U01–U16 唯一状态

状态仅使用任务卡允许值。`PASS` 仅表示本轮已满足该项所述读域条件，不表示生产已切换；其余业务 Owner/部署门仍单独判断。

| ID | 状态 | 最新证据与未闭合项 |
|---|---|---|
| U01 | `FAIL` | 内置浏览器确认事件 Radar 177 条、第二页可读且 `NEW` 筛选 110 条；Formal Radar 全市场 priority producer 仍缺。 |
| U02 | `FAIL` | 正式 Forward 样本仍无授权 Owner；首次捕获面板显示 `NOT_DUE`、2026-10-14 候选日及四项缺失输入，计数仍为 null。 |
| U03 | `PASS` | 同一煤炭行业、同一成员快照，在已接受 Head 索引的 10/12 与 10/13 Owner 逐日对比：均为 NONE→NONE；10/12 diffusion=false/early_retained=false，10/13 diffusion=true、early_retained 与 mature_retained 因质量缺失为 UNKNOWN；逐日字段、谓词、source hash 与“验证中/待核”标记在抽屉可见。PASS 仅覆盖读域解释性，不认证严格 PIT 或正式递归 episode。证据见 JSON `rotation_cross_date`。 |
| U04 | `FAIL` | 四轴仍为正式环境未发布；个股/板块/市场三族独立风险事件与分母、四态生产证据缺失。 |
| U05 | `FAIL` | 400 板块列表明确缺正式 maturity/health Owner；独立 Sector D2 生命周期生产者和 20 个真例重算未交付。 |
| U06 | `PASS` | 28768 内置浏览器验证轮动筛选：`rotation=NONE` 共 248 条，首 30 条全为 NONE；`rotation=UNKNOWN` 共 73 条，首 30 条全为 UNKNOWN。煤炭详情显示当前/前序状态、谓词、质量原因和 Owner 来源；10/12 与 10/13 对比见 `rotation_cross_date`。仅覆盖隔离读域解释性，不代表严格 PIT 或正式生产轮动。 |
| U07 | `NOT_VERIFIABLE` | `SZ.301660` 真实详情呈现 `NONE + UNKNOWN`、检测器状态、10 项不可判定条件；跨字段 D2 Owner 复算仍不全。 |
| U08 | `NOT_VERIFIABLE` | 真实详情明确显示资格 UNKNOWN 与不可判定项；TRUE/FALSE/UNKNOWN/NOT_IMPLEMENTED 全状态及 D2 Owner 对账尚未齐。 |
| U09 | `PASS` | 28768 内置浏览器与同日正式身份来源对账：`SZ.301660` 列表/详情均为 `NEW_CODE_OBSERVED`；`SH.600703` 均为 `EXISTING_VERIFIED_IDENTITY`；搜索旧代码 `SZ.300114` 解析到当前身份 `SZ.302132`，列表/详情均为存量身份且不声称旧代码有 T0 报价。详见 `code_status_reconciliation`。仅通过隔离读域验收，不表示 28765 部署。 |
| U10 | `PASS` | 2026-10-13 同一 T0 显示 3,151 个唯一活跃对象、未映射 0、Top5 中文名/计数/占比；内置浏览器打开 Focus 详情并完成 110 个行业 5 页（25/25/25/25/10）全量翻页。证据见 `R5_BROWSER_SMOKE_20261014.json`。 |
| U11 | `NOT_VERIFIABLE` | Focus 第 1/2 页和 NEW 过滤可读；未知 membership/validity/path 被保留，但逐字段 observation/episode Owner 对账不全。 |
| U12 | `NOT_VERIFIABLE` | Focus 事件分页（offset 30）与 NEW 筛选已实测；修复 `INVALIDATED`/`EXITED` 控件污染主列表查询的问题，两个真实筛选结果均为空且页面无路由错误；缺少失效/退出真样本与同日多事件反例，未闭环。 |
| U13 | `FAIL` | 首捕就绪只读展示和隔离合同测试通过；日版全量 AS_RECORDED producer、独立队列 Owner、准入/结算/FEP 权限仍缺。 |
| U14 | `NOT_VERIFIABLE` | 内置浏览器 28768 展开五指数均显示日变动、5/20 会话收益和 2026-04-15—10-13 OHLC 图；来源将五指数 volume_unit 均标为 `SOURCE_NATIVE_UNVERIFIED`，UI 已隐藏成交量。窄视口和可交付截图未完成，故保留未验收。详见 JSON `index_chart_ui_reconciliation`。 |
| U15 | `PASS` | 真实可评价分母 5,191、UNKNOWN 21；内置浏览器展开 21 条，含参考价缺失/特殊规则期原因，错误参数合同测试有负例。 |
| U16 | `PASS` | 28768 内置浏览器同日真实接受截面完整展开 57 条精确首板与 12 条前缀未绑定对象，69/69 显示中文名、代码、所属行业及精确值或下界；size=200 单页容纳全部对象，无下一页截断。未知连板未猜测，分钟级过程未声称。仅为 2026-10-13 隔离读域验收，生产部署门另计。 |

## R5 最新源码复验（2026-10-14）

- 新发现并修复预览资源根映射错误：28768 之前从隔离数据目录的 `src/.../static` 读到旧副本，导致已修改的组件未实际送达浏览器。新增独立 `static_root` 参数并从当前源码 checkout 提供 UI 资源；默认部署路径仍使用产品数据根的现有静态资源。回归测试确认 `/v4/assets/components.js` 来自源码根，HTTP 200。
- 新增 `COHORT_FIRST_CAPTURE_READINESS_VIEW_R1` 只读状态：基于已接受 Head 和官方会话日历显示 `NOT_DUE`、下一候选日 2026-10-14、全量 AS_RECORDED 信号生产者/独立队列 Owner/完整回执/单独写授权四项缺失；写授权、正式入组、历史补算均为 false/null。无 GET 写入。
- 当前工作副本定向 unittest：31/31 通过（R2/R3 路由、Owner 只读、静态资源根和首捕状态等）；`git diff --check` 通过，只有现有 JS CRLF 提示。首次捕获隔离 pytest：56 通过；4 个实际日更执行器场景因缺少 `market_calendar.trading_calendar` 收集后失败，排除这 4 项后 56/56 通过。默认 pytest 插件另会在收集前因 checkout 缺 `src/common/disposable_paths.py` 中断；未运行全仓回归。
- 内置浏览器最新源码窄屏复验：六入口 heading 全对，页面宽度 375/scrollWidth 375；Radar 177 条、第二页 offset 30、NEW 过滤 110；Focus 事件第二页 offset 30、NEW 过滤每页 30；`SZ.301660` 显示 `NONE + UNKNOWN`、10 项不可判定条件；市场五指数、可交易规则分母 5,191、规则 UNKNOWN 21、涨停 69（精确首板 57、历史前缀未知 12）可读。所有浏览器验收均用 Codex 内置浏览器。
- 最新源码 Forward 页面确实显示“等待下一交易日正式接受”、2026-10-14 及上述四个缺项。DOM 无读源失败；证据见 [`R5_BROWSER_SMOKE_20261014.json`](R5_BROWSER_SMOKE_20261014.json)。20 个真实 Owner 读回投影证据见 [`OWNER_SAMPLE_AUDIT_R5.json`](OWNER_SAMPLE_AUDIT_R5.json)，哈希一致不替代业务算法复算。
- 日期下拉选择 2026-10-12 的真实内置浏览器复验得到 `PG_OPERATIONAL_OWNER_DESCRIPTOR_REQUIRED_NO_FALLBACK`；UI 明示未回退到其他日期。保留该失败态，未用 10-13 快照替代，也未补造历史 PG Owner。
- 静态资源修复后的实际视口仍为 375×844；该浏览器面板的 viewport 覆盖尝试未改变实际视口，桌面宽屏需重新验收。可交付截图文件仍为 0。此前记载的桌面/双视口页面证据因使用旧静态副本，不作为最新源码通过证据。
- 本次性能重跑 n=8 详见上表；最大 P95 368.74 ms、响应最大 173,900 B。范围仅 28768。

## 切换门与下一步

- 验收：`V4_PRODUCTION_CUTOVER_BLOCKED`。生产 R2 authority 保持缺失；28765 上 Radar 仍失败。源码预览成功不替代生产部署；D2、风险、Cohort/FEP、20 真样本、六入口宽/窄截图及板块详情性能门均未通过。
- 生产保护：28765 与旧 EXE 保持运行；未部署、未回滚、未更改旧包；`auto_daily` 仍暂停；正式 Head/T0/token 未变。
- 下一步继续在该已授权阶段任务内修复并验收缺口；只有任务卡核心门通过后才切换 28765。该报告不是外部接受或进入下一阶段授权。


### R5 U06 轮动筛选修复（2026-10-14）

- 修复 `app.js` 板块研究状态筛选参数：板块使用 `rotation`，其他领域继续使用 `state`；提交板块筛选时清除遗留的 `state` 参数，避免 URL/UI 状态不一致。
- Codex 内置浏览器 28768、2026-10-12：选择“未进入轮动”后 URL 为 `rotation=NONE`，返回 248 条，首屏 30/30 状态为 NONE；选择“来源能力不足”后 URL 为 `rotation=UNKNOWN`，返回 73 条，首屏 30/30 状态为 UNKNOWN。列表与详情均区分 NONE 和 UNKNOWN。
- 回归：`python -m unittest tests.test_v4_ux_r2_contract tests.test_v4_ux_r3_routes -q`，37/37 通过。pytest 的全局 hook 在本稀疏检出中导入未展开的项目模块，启动失败；不将其计为回归通过。
- 详情字段、跨日期 Owner、哈希和限制已记录在 JSON `rotation_cross_date` 与 `sector_rotation_filter_reconciliation`。本项 PASS 仅覆盖隔离的日期读域筛选及解释性；完整递归轮动/严格 PIT 仍未接受。


### R5 U14 五指数单位复核（2026-10-14）

- Codex 内置浏览器逐一展开上证、深证、创业板、沪深300、中证1000：均显示当日点数/涨跌幅、5会话与20会话收益，以及 2026-04-15 至 2026-10-13 的 OHLC 图（MA5/20/60）。
- 五指数源数据来自 `data/v4/dynamic_daily_sources/tdx/20261013/.../hsjday.zip`，SHA-256 `fe1de8b8dd28179f5da555159c03ddd1f8f60a88441694523f27d06be3ae53b5`；Owner 将每个 `volume_unit` 标为 `SOURCE_NATIVE_UNVERIFIED`。页面明确隐藏成交量并提示来源单位未核验，没有把单位猜成股或手。
- 首次窄屏尝试因该旧标签未应用 viewport override 而未形成验收。随后在 Codex 内置浏览器新标签上成功设置 1280×800 与 375×812，并完成 10 条相关路由的双视口 DOM 检查。
- 另对 `SH.688349` 个股详情执行冷启动重载，QFQ 图表 120/420 根、成交量股/成交额元、末收 13.54 正常显示；此前保留标签中的一次错误未在冷加载中复现，不记录为已确认代码缺陷。


### R5 全入口宽窄屏复验及主导航修复（2026-10-14）

- 窄屏截图发现研究主导航在 375 px 下横向滚动且出现滚动条。已将 `src/workbench_service/static/research/style.css` 的移动端导航改为自动换行；宽屏规则不变。
- 候选当前 joint 的 UI 静态资源仍绑定旧文件。尝试用既有候选刷新器生成版本资源时，其完整来源校验因 `JOINT_SOURCE_DIGEST_MISMATCH:data/v4/engineering_series_r3/series.pg.json` 失败；没有绕过校验，也未改变 Head。为验证当前 CSS，在 28769 启动了只读隔离预览，单独覆盖 style.css，其余页面与数据仍走候选源码/Owner/PG。
- 使用 Codex 内置浏览器在 1280×800 与 375×812 检查 home、stocks、sectors、focus、market、diagnostics、radar、Forward 子路由、个股详情、板块详情，共 20 个 route/viewport 组合。每个页面均完成加载且标题正确；宽屏文档 scrollWidth=1265、窄屏=360，均小于 viewport；窄屏导航 scrollWidth/clientWidth=330、flex-wrap=wrap，横向滚动消失。另在内置浏览器捕获首页宽屏和窄屏视觉画面各 1 张，但没有导出为报告目录内的截图文件，故文件数仍为 0。
- 该项通过隔离页面布局检查，不代表候选 Authority 已接受新 UI 版本；U14 仍为 `NOT_VERIFIABLE`，五指数成交量来源单位未核验。R5 总体验收仍为 `V4_PRODUCTION_CUTOVER_BLOCKED`。详细测量在 JSON `responsive_route_reconciliation`。

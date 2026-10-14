# V4 UX R4 收口报告

**验收结论：`V4_PRODUCTION_CUTOVER_BLOCKED`。** B-01/B-02 和本轮读域呈现修复已提交并推送；隔离 R2 API 与内置浏览器预览可用。六入口双视口已目视复验，但任务要求的截图文件未交付。正式 28765 未切换，R2 authority 未写入生产根；业务生产者与正式 Owner 门槛仍未闭合，禁止宣称 FULL_PASS 或完成切换。

## 阶段合同与环境

- 执行依据：用户指定 R5 任务卡（2026-10-14）及最新适用升级文档 [`V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md`](../../../../docs/upgrade/V4_FULL_CLOSEOUT_CONTINUATION_TASK_R2_20261013.md)。阶段合同：修复 B-01/B-02；用 2026-10-13 已接受输入做只读验收；不得伪造 Cohort/FEP、不得启用自动日更/变更 Head；所有核心门通过后才允许切换 28765。
- R4 基线 HEAD：`d2f9dfb99221e9fe1cd78b302b5b4b135f380ecf`；R4 代码与报告提交 `54abe9f1ef33d9d2836790c405ec7b43a5af3afa`、`664d310077ebf8912302585d0c3371396238cba5` 已推送。R5 本轮最新源码提交：`af159a22d1a63e7b830c35dcf32b924d1045764d`，已推送到同一分支。
- 28765 回滚点：PID `34284`，旧包 `V4_PACKAGE_1.0.0_88cc19deae3b`，EXE `G:\codex work\v4-production-20261012\versions\V4_PACKAGE_1.0.0_88cc19deae3b\DaAV4\DaAV4.exe`。进程未停止、包未修改、未切换。内置浏览器原先读到 T0 `2026-10-13`、engine RUNNING、`auto_daily` 暂停；本轮未运行盘中日更、未改变正式 Head/token。TDX 只读输入未改。
- 受限只读 PG 的最新隔离 R2 schema：`v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5`；database `market_research` / OID `646711`，port `5432`，T0 `2026-10-13`，Head token `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`。投影计数 `{focus:3151, radar:177, sectors:400, stocks:5225}`；producer SHA `e2c47cf8e062b078edfc426ee297844462db28805f4e513ad59e87b9f22d4f5`；content digest `5ecd6dff469f70bf595fb76789e33dd0203e3c222f45199516491fd70ef3105f`。cluster `system_identifier` 未封存，PG 集群身份仍不完整。隔离 authority 仅位于 G 盘临时根；生产根没有写入 R2 authority。该 schema 使用隔离名称，不覆盖 sealed schema。
- 浏览器验收只使用 Codex 内置浏览器（28765 生产页及 28768 隔离预览）；未调用外部浏览器。28768 是源码版静态资源 + 生产数据 owner 只读读取 + 独立 PG schema 的预览服务，不是生产部署。

## 修复、测试及 HTTP 证据

1. **B-01**：新增精确 R1 legacy capability 检测。仅当响应明确标记为允许的 R1 legacy 状态时，HTTP 层跳过 R2 专用 512 KiB/字段形状检查；未标记响应和 R2 仍受 guard 约束，错误保持 fail closed。
2. **B-02**：R2 content digest 采用按 workspace + 完整 digest 派生的版本化 schema 名，旧 schema 保持只读兼容；binding 校验 producer SHA；authority 更新保留 revision history，不覆盖旧修订。
3. 定向合同测试：`tests/test_v4_ux_r2_contract.py` 11/11、`tests/test_v4_ux_r3_routes.py` 9/9 通过，`git diff --check` 通过。全仓 pytest 未成功加载，因该 checkout 缺少 `src/common/disposable_paths.py`；不计为全量回归。
4. R1 兼容复现：28766 旧 R1 `/api/v4/home` n=8 HTTP 200，5,060,827 B，P50 279.43 ms、P95 370.04 ms。修复防止旧 R1 被 R2 guard 误拒绝；5.06 MB 本身不满足 R2 首页体积目标，因此此数字仅证明降级兼容，不代表首页性能验收通过。
5. R2 隔离预览（28768，n=8；耗时 ms）：

| 路由 | 响应字节 | 冷请求 | P50 | P95 | 结果 |
|---|---:|---:|---:|---:|---|
| home | 115,462 | 216.60 | 217.24 | 340.38 | 8/8 HTTP 200 |
| stocks | 67,167 | 112.48 | 114.95 | 225.69 | 8/8 HTTP 200 |
| sectors | 88,043 | 214.82 | 214.80 | 217.99 | 8/8 HTTP 200 |
| focus | 82,807 | 358.99 | 249.61 | 377.03 | 8/8 HTTP 200 |
| radar p1 | 49,605 | 215.45 | 211.22 | 330.77 | 8/8 HTTP 200，总数 177 |
| radar p2 | 49,716 | 347.41 | 220.01 | 347.41 | 8/8 HTTP 200，总数 177、offset 30 |
| stock detail | 158,677 | 153.74 | 214.77 | 363.32 | 8/8 HTTP 200 |
| sector detail (R5 修复后隔离版) | 81,051 | 约 192.09 | 80.30 | 192.09 | 8/8 HTTP 200 |

   表中其他路由指标沿用修复前测量；板块详情行记录本次修复后复测。详情延迟已有明显下降，但全路由复测和正式 28765 性能验收仍未完成。性能请求仅代表 28768 隔离预览，不代表现役 28765。

### R5 继续执行记录（2026-10-14）

- 修复板块详情每次请求都重读 rotation Owner 的慢路径：R2 producer 将 `why_now` 可审计字段放入 detail 行，HTTP 优先键查找并在一次只读 PG 连接中同时读取 Context 与详情；列表摘要排除 detail-only 数据。回归测试覆盖 detail-only 展开、主键查找、共用连接及详情不再加载 Focus/rotation 来源。
- 重新构建的隔离 R2 schema 为 `v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5`，T0/token 与生产已接受 Head 一致，计数 `{focus:3151, radar:177, sectors:400, stocks:5225}`。隔离 authority 仍只在 G 盘临时根，生产根无 R2 authority 写入。
- 修复后板块详情 HTTP 原始回应 n=8：8/8 200，81,051 B，P50 80.30ms、P95 192.09ms；此前 P95 1,198.83ms。范围仍仅为 28768 隔离预览。
- 增加 20 个分层真实 Owner 投影样本读回证据 [`OWNER_SAMPLE_AUDIT_R5.json`](OWNER_SAMPLE_AUDIT_R5.json)：股票 10（含 `SZ.301660`、`SH.688349`）、板块 5、Focus 5；隔离 PG R2 投影读回哈希 20/20 一致。此结果证明投影字节对账，不替代 D2/风险/资格算法字段的独立业务复算，也不替代 U01–U16 完整验收。
- R4 阶段只检查了内置浏览器入口；当时未做六入口双视口。本轮 R5 已补上六入口双视口与 Radar/Forward/详情页的目视和 DOM 检查，仍缺可交付截图文件。
- 当前阶段结论不变：正式 D2 lifecycle、三族风险、Formal Radar priority、合法验证队列/settlement/FEP Owner 与生产权限仍未齐；不得据此切换 28765。

### R5 页面修复与回归（继续执行）

- 本轮源码提交 `af159a22d1a63e7b830c35dcf32b924d1045764d`：缺源原因和交易字段统一显示中文；Focus 表抑制 UNKNOWN 重复标签；Home 对 Forward/Risk 缺失 Owner 使用正式未发布状态；市场轴保留为候选证据、不再展示成正式环境；单根 K 线柱宽受限；Focus 首屏并发装载并在完成后滚动至 Forward 锚点。
- 修复属于读域呈现与路由行为，不补造业务字段，不打开 Formal D2、正式风险、Radar priority、验证队列、结算或 FEP 权限。浏览器预览 28768 运行新源码；28765 仍为旧包，无切换。
- 受影响合同回归：`python -B -m unittest -q test_v4_ux_r2_contract test_v4_ux_r3_routes`，26/26 通过；`git diff --check` 通过。仅为定向合同测试，不是全量回归。
- 下个独立工作项：继续实现/接通有版本合同的 Sector D2 生命周期与 20 个真例重算、三族独立风险事实、正式 Radar 优先级和当前首次捕获读链；同轮继续 U03/U06/U07/U08/U09/U11–U16 的真实字段抽样。外部正式 Owner/准入事实缺失时保持 unknown，不虚构。
## 内置浏览器验收

- 28765 生产页：旧首页读取 stocks 5,225/sectors 400、Focus 变化 177/展示 30、风险 14；Radar/Forward 首页仍显示来源未接入，直达 `/v4/research/radar` 提示“没有找到该入口”。生产包版本仍为旧 `1.0.0_88cc19deae3b`。
- 28768 源码预览：Home 加载真实摘要（stocks 5,225/sectors 400/radar 177），清楚说明 Radar 是事件雷达、正式优先级未发布，Forward 正式样本未准入且不伪造计数。Radar p1/p2 均渲染真实事件、有效性/路径/场景/资格及来源字段，第二页显示共 177 条、offset 30。
- 28768 六入口逐项检查：Home、板块研究、个股研究、关注跟踪、市场与事件、数据与诊断。板块列表展示 400 行规模、代理指标与成熟度/健康度正式来源缺失；煤炭详情展示成员数据、时间变化解释及“非严格 PIT”标记。个股列表显示 5,225 行；`SZ.301660` 详情核对代码身份、行情单位和历史不足说明。Focus 显示分母 3,151、行业未映射 0，Top5 中文名称为电气设备/化工原料/软件服务/汽车配件/专用机械；观察页标出 3 条真实状态变化、27 条来源不足观察，未把来源不足计作事件。Forward 各栏显示队列未准入、首次捕获源未验证、结算来源缺失、FEP 未准入。市场四轴显示“正式环境尚未发布”，候选轴只留在来源抽屉；诊断页提供生产源健康、来源版本、日更失败状态入口。
- R5 继续复验只使用 Codex 内置浏览器：明确设定 1440×1000 与 768×960，六个导航入口均逐页目视截图并检查 DOM；Radar 子路由、Focus `#forward-cohort`、个股 `SZ.301660` 与煤炭板块详情也检查。各入口页面 `documentElement.scrollWidth` 分别为 1425/753，与 viewport 1440/768 相符；窄屏表格在容器内滚动，无页面级横向溢出。Radar 标题/高亮已修；Focus Forward 锚点在异步完成后落入视口；市场轴正式状态保持“未发布”。截图已由内置浏览器捕获并在验收过程中逐张目视检查，但未保存为仓库文件（文件数 **0**），所以任务卡要求的可交付截图附件门仍未通过；不得把内嵌工具图误报为仓库证据文件。
- 样本验收仍未全部通过：已完成 20 个分层 Owner 投影哈希对账（20/20），但还缺 U01–U16 对应的字段语义/算法复算，不能把投影哈希一致写成业务事实正确。

## U01–U16 唯一状态

状态值依任务卡限定。`FAIL` 表示有可复现的生产失败或明确缺失；`NOT_VERIFIABLE` 表示没有满足完整 owner/跨日期/样本验收证据。

| ID | 状态 | 证据摘要 |
|---|---|---|
| U01 | `FAIL` | 生产首页 Radar 源未接入且直达入口 404；隔离预览事件 Radar 真数据/第二页可读，但正式全市场优先级 producer 未发布，未部署。 |
| U02 | `FAIL` | 生产首页无 Forward 来源；预览候选未验证、无授权 Cohort Owner，正式样本数合法留空。 |
| U03 | `NOT_VERIFIABLE` | 板块页标为验证中；未按至少两个可比日重算轮动前序及 NONE/UNKNOWN 真例。 |
| U04 | `FAIL` | 市场四轴当前标记正式环境未发布；个股结构、板块生态、市场压力三族正式风险 producer、分母、改善与持平证据仍未齐。 |
| U05 | `FAIL` | 400 板块页显示成熟度/健康度 owner 未发布；D2 lifecycle producer 和 20 个样本复算缺失。 |
| U06 | `NOT_VERIFIABLE` | 煤炭详情可打开，生命周期及非严格 PIT 标示可见；历史序列的 NONE 与 UNKNOWN 不等价验收未做。 |
| U07 | `NOT_VERIFIABLE` | 三一重能详情及行情图可见；scenario/status/detector/unknown predicates 与 R2 owner 未逐字段核对。 |
| U08 | `NOT_VERIFIABLE` | Focus 真实观察显示资格、成员、有效性和 operational owner 未知；四态证据清单与 D2 owner 对账未完成。 |
| U09 | `NOT_VERIFIABLE` | R2 预览已检查 `SZ.301660` 的代码身份、列表字段和详情行情；旧股、无报价、别名及完整 R2 Owner 字段对账仍未完成。 |
| U10 | `FAIL` | 源码预览集中度已显示中文 Top5 且 unmapped=0；现役 28765 仍是旧包、未安装此修复，不能算生产通过。 |
| U11 | `NOT_VERIFIABLE` | Focus 表展示 owner-reported unknown membership/validity、operational owner unknown；observation/episode/最新观察逐字段一致性未核验。 |
| U12 | `NOT_VERIFIABLE` | 观察事件中文名/原因/来源不足可见；Focus 第 2 页、同日多事件反例及过滤证据未验。 |
| U13 | `FAIL` | 已实现缺源显式状态，但候选捕获、Cohort 准入、结算/FEP 管道缺授权 owner，超出仅等待未来样本成熟。 |
| U14 | `NOT_VERIFIABLE` | 市场四轴正式环境未发布、候选值留在来源抽屉；五指数 5/20 会话、OHLC 图与单位仍未完成两视口字段验收。 |
| U15 | `NOT_VERIFIABLE` | 本轮未核验可交易分母、规则未知证券样本与 UNKNOWN 筛选/负例。 |
| U16 | `NOT_VERIFIABLE` | 本轮未核验精确连板分类、逐类中文详情及真实分页。 |

## 切换门与下一步

- 验收：`V4_PRODUCTION_CUTOVER_BLOCKED`。生产 R2 authority 保持缺失；28765 上 Radar 仍失败。源码预览成功不替代生产部署；D2、风险、Cohort/FEP、20 真样本、六入口宽/窄截图及板块详情性能门均未通过。
- 生产保护：28765 与旧 EXE 保持运行；未部署、未回滚、未更改旧包；`auto_daily` 仍暂停；正式 Head/T0/token 未变。
- 下一步继续在该已授权阶段任务内修复并验收缺口；只有任务卡核心门通过后才切换 28765。该报告不是外部接受或进入下一阶段授权。

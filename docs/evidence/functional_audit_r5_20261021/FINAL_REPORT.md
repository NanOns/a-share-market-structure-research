# V4 R5 现役功能定点实修审计报告

日期：2026-10-21（Asia/Shanghai）

任务卡：`V4_R4外审_R5真实业务功能定点实修任务_截至1014_20261021.md`

基线：`codex/v4-unified-development` @ `90cbc653cd23559b6a970f0c472c02221a25de9a`

数据范围：截至 2026-10-14；没有读取或使用 2026-10-15 及以后行情。

## 阶段合同、适用文档与边界

执行前查阅 R5 任务卡、`AGENTS.md`、`docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`、`docs/operations/V4_R4_SOURCE_POLICY_MIGRATION_20261009.md`、R4 外审报告、日涨跌停规则合同和本次涉及的生产者/BFF/页面代码。阶段合同：只修复截至 10 月 14 日的现役功能问题；先查现行数据绑定，再以只读候选方式核实实际业务数据；实际读回 API 并用浏览器核验页面；明确区分候选与已接受结果；不重复已通过任务，不扩大行情日期范围。

本轮只读使用共享 `127.0.0.1:5432/market_research`。28766 候选预览 PID `50688`，工作目录 `G:\codex_tmp\v4_daily_candidate_chain_20261020`，状态 READY，T0 `2026-10-14`，context token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`，formal Head `2026-10-09`。当前服务 `production_accepted=false` 且 `formal_head_modified=false`。监听核对：`127.0.0.1:28766` 为 PID 50688；28765 未监听；PostgreSQL 5432 为 PID 8640。本轮未写生产 PG、未改正式 Head、未部署/重启 28765，也未运行采集器或写入工作进程。没有修改 `D:\new_tdx` 或其他 TDX 只读源目录。

## 分项验收结论

| 范围 | 状态 | 验收结论与未闭环点 |
|---|---|---|
| P0-A 日涨跌停来源错配 | **PARTIAL** | 已修正日涨跌停生产者的日期/owner 来源选择并按三个现行日期 lineage 离线重算；源覆盖从约 0.9–1.1% 回到约 99.35–99.39%。但来源捕获时间为 10/20，属 NON_PIT 候选；10/12、10/13 没有当前服务 token 绑定；仍有 60 条代表样本之外的差异/未知核验、参考价错配审计记录，且未接入市场 Owner/API。不能宣称正式风险修复完成。 |
| P0-B Priority 榜单不能读取 | **PARTIAL** | 当前候选 token 下候选 API 200、桌面浏览器显示 967 个可排序股票中的前 30 行及 0/400 板块；标题已纠正为“研究优先级”。正式 API 仍以 `RESEARCH_PRIORITY_BINDING_MISSING` 失败关闭。当前 R5 输入 SHA 与 R4 历史 payload/core SHA 不同，榜单差异尚未完成来源身份对账；仅候选预览可用。 |
| D0/D2 状态与解释 | **PARTIAL** | R4 已通过的因果分解结果不重复执行。10/14 D2 5,225 行中 TRUE 65、UNKNOWN 5,160；confirmed TRUE 145、UNKNOWN 5,080；未发现 FALSE 被强行判 TRUE。当前证据没有可复现的 detector 生产者错误，因此保留 UNKNOWN；D0/parent episode 与 Focus 页面端到端缺陷未修复。 |
| 板块生命周期与排序 | **PARTIAL** | API 读回 400/400 health/maturity `SOURCE_INCOMPLETE`，Priority 0/400 可排序；其中 266 行缺 maturity+health，134 行还缺 rotation。现存 lifecycle 文件是成员/生命周期输入快照，不是独立已验收的计算输出。没有伪造轮动或使用 RS proxy 填补，未写 PG。 |
| 市场压力风险 | **PARTIAL** | 使用修正后的日涨跌停候选输入，对既有 `market_axis_primitives` 只重算 stress 轴，三个日期均得到覆盖率约 99.35–99.39%、LOW；但 breadth/participation 仍 UNKNOWN，候选没有集成到 market Owner/home API。正式风险 API 仍 `MARKET_PRESSURE_RISK SOURCE_INCOMPLETE 0/1`，原市场 Owner 的压力值仍不可用。 |
| Focus 与首页计数 | **PARTIAL（口径已对账，数据缺口未修）** | 当前 API 全页读取 3,247 个唯一 Focus tracked-object cohort；首页变化总数 177、展示 30、净信息 191、持续项 330；首页变化页 30 行中 3 条为真实状态变化，27 条为来源不足观察。Radar 177 条事件（NEW 90/UPGRADED 57/WEAKENED 30），使用独立合同和分母。计数差异可解释，但 cohort 中仍有 2,726 条 DATA_UNAVAILABLE，前瞻数据仍 `DATA_MISSING`。 |
| 5G 概念成员关系 | **PARTIAL（页面链路 PASS）** | 浏览器实际打开 `THEME:880506`，页面显示 454 源成员、442 已映射、12 未映射、440 有行情；已映射成员表 442 行可翻页，股票链接可打开。12 项均为 TDX 快照 `UNMAPPED_QUARANTINED`、无 security_id，并且不在 10/14 core/daily 行中。源文件没有名称/上市/退市日期，不能推断其上市状态；映射缺陷仍待解决。成员采集时间 10/09，存续偏差风险。 |
| 图表 QFQ 冷/热与实际页面 | **PASS（定向样本）** | `SH.600000` 10/14 QFQ 冷读 API 200、422 根；热读 200、422 根、cache hit，规范 payload SHA 一致；浏览器个股详情页实际渲染“真实行情蜡烛图”、120/422 根 QFQ，末根 10/14 收盘 9.65；图表含 5/20/60 均线且最近 200 根 MA 全有值。来源绑定 TDX GBBQ 2026-07-16 除权样本。仅通过一个个股样本，不代表全市场图表验收。 |
| 概念关系与真实页面 | **PARTIAL** | 个股详情的“查看所属板块”链接可见；5G 概念详情页与 442 个已映射成员的可读关系表已在浏览器读回。12 个 unmapped 成员因无身份映射仍无法形成证券详情关系；除此之外未声称所有概念关系均已验收。Priority 桌面 DOM 完成验收。 |

**综合状态：PARTIAL。** 已完成日涨跌停生产者的局部修复、候选 Priority 页面和焦点计数口径验证、单只股票图表冷/热与浏览器验收。正式 Priority、市场风险集成、板块 lifecycle、D0/Focus 端到端和 5G 身份映射仍有明确缺陷。代码推送不代表外审通过或正式发布。

## 为什么其余项没有闭环

这些条目并非都“无法推进”。除正式 Owner 写入需要额外授权外，上一轮对若干只读候选工作过早停止，按当前证据逐项说明：

| 项目 | 可推进范围 | 目前确切限制 / 上轮未完成项 |
|---|---|---|
| 正式 Priority | 当前只读候选榜单、分母和页面已完成 | Formal API 的 `RESEARCH_PRIORITY_BINDING_MISSING` 表示该 token 没有 immutable Priority Owner。将它变为正式已接受结果需要共享 PG 写入/authority 变更，用户未授权；候选预览没有因此停止。 |
| 日涨跌停→市场风险 | 已完成限价候选重算和 stress primitive 离线试算 | 三份日线源记录观测时间为 10/20，超出 R5 对“各自 T0 以前合法历史输入”的要求；因此可作为“后验候选诊断”，不可当作满足 R5 时点验收的输入。stress 结果也没有进入当前候选 API。上轮应继续查找 T0 前可用源/逐项分类并做隔离 API 预览；不接入正式 Owner 是权限边界。 |
| 板块 lifecycle | 当前 400 板块可继续做离线审计 | 上轮执行的审计脚本读取的是预览根目录正式 Head `2026-10-09`，窗口为 9/28、9/29、9/30、10/08、10/09，20 个独立 oracle 样本 `FAIL`；证据 `G:\codex_tmp\r5_sector_lifecycle_audit.json` SHA256 `71a7a55b9472f58d249692af61488fa70816822701e2bc397048c863a88a315c`。这既不是 10/14 输入，也未通过独立 oracle，不能写入 10/14 Owner。R5 日期候选审计尚未运行，是上轮遗漏；应先用合法的 10/14 五会话来源重新构建/对账，而非直接写 PG。 |
| D0/D2 | 对可读取事实继续逐股追因子、parent episode | 当前 10/14 记录没有 confirmed FALSE 或 boundary_event 样本；不能伪造反例或将 UNKNOWN 改 FALSE。上轮只列了 7 个示例而任务卡要求至少 10 个真实样本，并且未完成 D0 parent episode 端到端，这属于未完成取证，不是授权阻塞。 |
| Focus | 首页/Focus 当前页面、总数与第一页 3/30、27 条来源不足已核对 | 口径问题可解释，但 cohort 仍有 2,726 `DATA_UNAVAILABLE`、3,182 validity UNKNOWN。修复这些行需要其缺失的当日证据源；上轮未按 3,247 项来源字段继续定位每类缺失具体源文件，属于未完成根因盘点。 |
| 5G 概念 | 概念页和 442 个已映射成员关系已实际读取 | 12 个代码在当前 10/14 core/daily 中均不存在，成员快照没有名称、security_id、上市/退市日期。缺少能安全映射的身份事实，无法从代码猜测或删成员；需要找到合法身份源后再修复。 |

本轮**不要求 390×844 窄屏验收**，此项不作为缺陷或后续门槛。

## P0-A 日涨跌停：生产者修复、逐日回放与代表样本

生产者原有问题是把 `core.owners` 与 source trace dates 按位置 zip，并直接选择 trace 中 BaoStock 来源；这会把旧日期查询绑定到当前 owner 行。修改后，按当日 lineage owner 的精确 RAW 路径确定候选目录，核验 `SUCCESSOR_CANDIDATE.json` RAW binding、交易日、证券代码唯一性，并读取同目录 `sources/daily.json`。缺失或绑定不一致时失败关闭。实际唯一调用点为 `src/workbench_analysis/r43_market_replay.py`。

当前 10/12、10/13、10/14 lineage owner 分别为 `54ed1b92…`、`e137824c…`、`727b8c2e…`。三份 `daily.json` 的内容 SHA 分别为 `97f750e3b3eba8f898ef905ab0c3df0cd6ef0e0f73622bb886f4698d29cc2bc9`、`c8b0a5719735a52923bd1cbcfe1e07509d61c44a88e5ee4a17bd3b18c7a052ff`、`8f949e7418355e8f60dbd859598e27ad948c4cfdf9bed69b37c5f04d65db755e`。观察时间分别为 2026-10-20 10:19:45、13:05:26、17:52:01 +08:00；这是后验候选来源，不是当时可得证据。规则合同 `config/v4_02_price_limit_rules_r3.json` SHA256 `68679333821c50ea8cbed5ff4cd001447cc6571d79b0d074a60b6bb81bdb01e0`，规则版本 `LIMIT_RULES_V1_1`。

| 日期 | 新状态计数（总行数） | UNKNOWN 拆分 | 新产物 SHA256 | 与旧链状态不同 |
|---|---|---|---|---:|
| 10/12 | NOT_LIMIT 5,122；UP 47；DOWN 23；SUSPENDED 12；UNKNOWN 20（5,224） | reference price 18；special period 2 | `518760542fffbac438b432abaebe17a0bc4d217d5b226a4fadd58353eef2f3a7` | 5,147 |
| 10/13 | NOT_LIMIT 5,112；UP 69；DOWN 10；SUSPENDED 13；UNKNOWN 21（5,225） | reference price 20；special period 1 | `3ae015150a5d16aca8e1c8da3ab36638627509cc832e77526cc10f5d9b9a7aac` | 5,151 |
| 10/14 | NOT_LIMIT 5,141；UP 37；DOWN 13；SUSPENDED 11；UNKNOWN 23（5,225） | reference price 22；special period 1 | `10038767951f38df66fa387eed47f45f38f5b501b3953f4e2590285c7e62c69b` | 5,138 |

同日对齐收盘参考价与前序 RAW close 核查仍分别有 16、17、20 条差异，必须保留为审计问题。日线只证明收盘状态，不证明盘中触板。离线回放文件位于 `G:\codex_tmp\v4_daily_candidate_chain_20261020\r5_daily_limit_materialization_8ab7eeecc0a7_54ed_e137_727b\{date}`，每个日期含压缩结果、合同和回执。20 只代表性证券/日期（共 60 组）的逐代码 old/new 状态及 OHLC、参考价、前序 close、owner、来源记录存于 `G:\codex_tmp\r5_daily_limit_current_samples.json`，SHA256 `eb061e5df2800085b964750de5be81026c3193608ac9913a77ff6935ce951335`。10/12、10/13 样本没有当前候选服务 token；10/14 使用本报告所列 token。样本核验不替代全量逐代码复核。

## 市场压力轴候选试算（未集成）

隔离试算复用 `market_axis_primitives` 与原回放分母，只替换为上表修正的日期限价候选。下表的 corrected ratio 以同一证券集合计算。没有写市场 Owner、Head 或 API。

| 日期 | 旧限价覆盖率 / 旧 DOWN | 修正覆盖率 / DOWN | 重算压力 / 变化 |
|---|---:|---:|---|
| 10/12 | 0.957% / 0 | 99.387% / 23 | LOW / RISING |
| 10/13 | 0.900% / 0 | 99.349% / 10 | LOW / DECLINING |
| 10/14 | 1.129% / 0 | 99.349% / 13 | LOW / RISING |

证据 JSON `G:\codex_tmp\r5_market_stress_replay.json` SHA256 `b94aaaf127160ab442fdf76d1f85e2cf6e40032d2f9e28b1a2a4d2d9a9842240`，其中 `accepted=false`、`PIT_ELIGIBLE=false`、`not_integrated_to_home_api=true`。breadth 与 participation quality 为 UNKNOWN，所以不能把此项试算写成已接受“市场综合环境”。

## P0-B Priority API 与浏览器读回

候选 API 使用当前 token：

- `GET /api/v4/radar/priority?view=candidate&scope=stocks&limit=10`：HTTP 200；总证券 5,225，可排序 967，排除 4,258。股票来源 core SHA `021c0e6fbcb3684d0fc8a2aa6f3f7b40353c22a2b7391264911aa2493ccdfcce`，payload SHA `c4945baac152000a39c3c330c6019f3488a635a1ce9288268d119c30254be163`。
- `scope=sectors`：HTTP 200；400 唯一板块，0 可排序，400 排除。health/maturity 均为 `SOURCE_INCOMPLETE`。组合分布为 216 个 rotation NONE、45 ROTATION_FAILED、4 ROTATION_PULSE、1 ROTATION_IN（这 266 项 rotation quality 为 KNOWN），另 134 项 rotation UNKNOWN；所有 400 项 health/maturity 均未知。
- 正式视图：HTTP 400 `RESEARCH_PRIORITY_BINDING_MISSING`；旧 token：HTTP 409 `CONTEXT_TOKEN_MISMATCH`。

候选 API 首位 `SZ.000158 常山北明`，分数 11.74123；理由可解释为核心结构未破、20 会话相对强度改善、5 会话收益为正、未显著延伸、与前 20 会话低点距离可计算。前十证券为常山北明、瑞立科密、*ST尔雅、周大生、航民股份、五矿发展、柳药集团、联发股份、上海石化、兴蓉环境。

10/21 桌面浏览器实际打开 `/v4/research/radar/priority?view=candidate&trade_date=2026-10-14`，DOM 标题为“研究优先级”，候选页状态、T0/token、板块 0/400、股票 30/967、首位证券与中文排序原因及证据按钮均已渲染。候选标题错误的旧 UI 文案已在 `app.js` 修复并通过本轮浏览器读回。R4 历史 payload SHA `2662ac3c09f7608585d9bec1c822a6ae0258fa74a663b7fe9043cfd8d7e54333`、core SHA 前缀 `2c1d4751…` 与本次当前候选来源不同，尚无独立证据认定二者应当相同；不声称榜单结果对账完成。API 分页/来源摘要 JSON `G:\codex_tmp\r5_sector_stock_api_audit.json` SHA256 `869cf59678d80b23c6e4914ef72ca8bfb92ea1e262c84b6eb4bf986f63ce4b52`。

## D0/D2、Focus、5G 概念成员

**D0/D2。** 采用已经形成的 R4 定向复核结论，避免重复运行通过任务：10/14 corrected D2 输入 5,225 行，confirmed TRUE 145、UNKNOWN 5,080；final eligibility TRUE 65、UNKNOWN 5,160；final freshness fresh 65、stale 5,160。875 行存在 prior episode，4,285 行无 prior。无 prior 的 4,249 行只因 confirmed UNKNOWN 而阻断，36 行还有其他必需未知输入；有 prior 的 795 行 confirmed UNKNOWN，80 行 confirmed TRUE 仍被 frozen invalidation UNKNOWN 阻断。最终 TRUE 65 行无 prior。当前分布没有 confirmed FALSE，也没有可用 boundary_event 样本，因此本轮不能构造“真实 false 边界样本”或据此断言 detector 错误。代码路径 `src/v4/research_state.py::reduce_state` 与 R4 定向证据说明，缺 prior 时 CONFIRMED TRUE 且唯一 frozen invalidation UNKNOWN 不应被判 stale；未发现本轮可复制的 producer 错误，UNKNOWN 保留。代表样本可按 R4 报告中的 `SZ.001965`、`SZ.002469`（confirmed true/fresh），`SH.688349`、`SH.600703`（confirmed unknown/stale），`SH.601059`（prewatch/暂停未知），`SZ.000582`、`SH.601995`（seed unknown）复核。D0 parent episode 及页面端到端验收仍未关闭。

**Focus。** API 全量分页 3,247 行、3,247 个唯一 entity；tracked-object cohort 不是 5,225 证券全市场或用户持仓。事件分布：DATA_UNAVAILABLE 2,726、NEW 96、PERSISTENT 330、UPGRADED 63、WEAKENED 32；validity UNKNOWN 3,182、VALID 65；path READY 65、PARTIAL 472、UNAVAILABLE 2,710。实际浏览器 Focus 页可见 3,247 清单，第一页 30 条观察中 3 条是真实事件、27 条是来源不足观察；首页“关注对象变化”明确显示符合 177 / 展示 30，净变化 191、持续记录 330。Radar 单独返回 177 条事件，NEW 90/UPGRADED 57/WEAKENED 30。由此解释了首页总事件与 Focus 清单首屏观察数不同的口径，但 2,726 个 DATA_UNAVAILABLE、3,182 个 UNKNOWN 及前瞻 `DATA_MISSING` 仍是未解决的数据缺口。JSON `G:\codex_tmp\r5_focus_audit.json` SHA256 `cf4c92c25d61741ceec3410a4e3f4f216f2876b0a3f1529800b1c65dd9fa235c`。浏览器首页与 Focus 读回通过不表示 cohort 全体资格正确。

**5G (`THEME:880506`)。** 10/14 当前 API 返回 454 原始成员，442 已映射，12 未映射，440 有报价。以下 12 项的 identity 均为 `UNMAPPED_QUARANTINED`、`security_id=null`、成员源 `infoharbor_block.dat`；均未匹配 10/14 core 或 daily 的 `source_security_key`，没有当日行情。原始快照没有名称、上市日期、退市日期，故这些行的身份/上市状态仍 UNKNOWN，不推断其为已退市证券。代码：`BJ.920021`、`BJ.920028`、`BJ.920186`、`BJ.920249`、`BJ.920556`、`BJ.920640`、`BJ.920720`、`BJ.920876`、`BJ.920924`、`BJ.920932`、`BJ.920961`、`SZ.301718`。成员快照 `docs/evidence/r4_3_four_session_closeout_20261009/latest_member_S.jsonl.gz` SHA256 `be1cb3b1e53bc5d104c0eda165428fae4fb03abcb7208ea8abe22ee68d3ee3be`；其采集时点 10/09，故 10/14 使用时带存续偏差风险。生命周期 API 原因为 `SECTOR_LIFECYCLE_PG_OWNER_UNAVAILABLE`。本轮未找到已计算/独立验收的 lifecycle 输出 Owner，不具备安全接入条件。

## 图表冷/热 API 与浏览器

同一 28766 context 下请求 `/api/v4/stocks/SH.600000/chart?period=D&price_basis=QFQ&limit=200&offset=0`：冷读 HTTP 200、422 根、5,780.266ms、cache miss；热读 HTTP 200、422 根、172.671ms、cache hit。规范化 payload SHA 均为 `b5c04f9bcbc51832fe2b6a2944fc6e4c4a57ec21d8b59f3b93f9be44506da9aa`；422 根逐项 transport digest `5ad270964111d41ff3341b051eea8d206999857a8544ee78e09c157da73388ba`。返回 200 根这一窗口中 MA5/20/60 各 200 个有效值；总历史从 2025-01-13 延展到 T0 2026-10-14。输入历史 cutoff 10/12，QFQ 使用 T0 绑定的 TDX GBBQ SHA `c2f07f4aa8a9e8893e5dc24c1a83ac63f2ab27198ecde444154fd591c73e2739`；上海浦发 2026-07-16 类别 1 除权记录 `c1=4.199999809265137` 是实际样本。不是外部复权服务。

浏览器从个股列表搜索 600000，打开 `SEC-62C40F6EEABB12A3B3F00D4FB0B61ED0` 的浦发银行详情；切换“价格口径”到“原生前复权”后 DOM 可见“真实行情蜡烛图；数据缺口保留交易日位置”“展示 120 / 422 根”“候选 QFQ 由逐日 RAW Owner、T0 冻结的 TDX GBBQ 和精确有理数坐标计算”及“末根 2026-10-14 收盘 9.65”。冷/热 JSON `G:\codex_tmp\r5_chart_cold_hot_audit.json` SHA256 `d73dba6e881e6145be8dd0ca08d5841674941537b28f64831a9b4a35746f1eb3`。这里完成单证券 API 与页面样本，不代表多证券图表回归覆盖。

## 代码修改、文件与校验

- `src/workbench_analysis/r43_daily_price_limits.py`：修复按现行日期 owner 的 RAW binding 选取日线来源，校验日期/行/代码，候选隔离输出。
- `src/workbench_service/core_product_bff_r1.py`：只读候选 Priority preview，限当前 token/T0；正式已接受路径仍要求 immutable Priority Owner。
- `src/workbench_service/static/core-product-r1/app.js`：候选/正式切换页签、来源与未排序说明；Priority route 标题修正为“研究优先级”。
- `tests/test_r43_daily_price_limit_source_r5.py`：精确 owner 绑定及 fail-closed 覆盖。

校验：日限价定向测试 3 passed；既有 BFF API error tests 4 passed；`node --check` 检查 `app.js` 与 `api.js` 通过；`git diff --check` 通过。校验只证明局部实现与语法，不替代上方实际 API、数据和页面验收。

## 留给下一轮独立审计的明确问题

1. 先定位 10/12–10/14 各自 T0 前可用的日涨跌停输入；10/20 采集的 `daily.json` 只能作为后验诊断。再对合法输入与 pre-close mismatch 逐代码复核，并在隔离候选 API 读回 stress 变化。
2. 查清 R4 与 R5 Priority core/payload 不同的合法来源链与当前有效基线；保持正式 Owner 缺失时 fail-closed。
3. 独立确认 400 个板块 health/maturity 与 134 个 rotation UNKNOWN 的真实来源合同和生命周期计算产物。
4. 沿 D0 parent episode、5G 12 个未映射身份和所有概念关系逐实体查原始身份凭据；缺证继续 UNKNOWN。
5. 对 Focus 3,247 cohort 与首页变化逐实体对账；页面/API只读，不把不同分母合并。
6. 扩大真实浏览器验收到市场、板块、Focus、概念关系等尚未覆盖的桌面页面。

不得把本次代码提交/推送解释为生产部署、formal Head 更新、PG 写入或发布许可。

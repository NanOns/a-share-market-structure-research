# 大A V4｜核心算法 × 六入口前端：独立验收、定点修复与产品闭环任务卡 R1


- 文档编号：V4-CORE-ALGO-UI-AUDIT-R1
- 日期：2026-10-10（中国/新加坡 UTC+08）
- 类型：Codex 可直接执行的算法+产品验收任务合同；发现实证缺陷后定点修复；**不是重建 V4、不再展开服务运维/代码热更新项目**
- 仓库：NanOns/a-share-market-structure-research
- 目标分支：codex/v4-fp14-r2-repair
- 编写时远端 HEAD：64a0e31390765027f96b6a537bbf7f044abf6c83（执行前 git fetch，重新记录 BASE_SHA，不得擅自回退）
- 目标：**真实计算结果正确、六入口研究功能完整、页面可搜可看可解释、已有数据能正常生产使用**
- 时间规则：2026-10-10 为周六，最新已核实运营日为 2026-10-09。2026-10-12 新交易日采集与发布另有 R2.2 事实门，本卡不得模拟该日完成。
- 文档权威：仓库 AGENTS.md → V4.2.2 REV2 正式页面合同 §62A–§69、§81.2 → 如影响 FEP 则补读 REV4 FEP R2 → 2026-10-08 FP01–FP14 全功能合同 → 2026-10-09 R43 R2 FP 入场缺口矩阵 → 当前这张收敛执行卡。遇不同版本，以事实来源/变更范围逐条解释，不“覆盖旧验收”。
- 用户最新覆盖指令：**单人本地使用，服务正常重启即可**。移除动态更新代码、模块加载 SHA 证明、新启动取证入口、自启/托盘/Windows 维护/额外运维工程。旧 R2.2 生产加载未验证记录保留为历史事实，但**不再作为本轮算法和前端功能研发的先决门**。
- 浏览器：按用户 2026-10-08 后续授权，**Codex 内置浏览器 IAB 是正式端到端浏览器验收工具**。不再以专门安装/调用 Edge 作为验收阻塞。至少验证 1366×768 和 1920×1080 两视口；若当前 IAB 不支持某精度能力，诚实登记，不能以仅 HTTP200 替代浏览器。
- 资料与产物：MD + 最小结构化 JSON + 有代表性的截图；不发送 4GB Owner/551MB TDX ZIP/数据库，不重跑全部旧历史数据。


---


## 0. 本次方向与“不要做什么”


### 0.1 用户要的不是一个漂亮空壳


V4 的研究工作流必须是：


```
真实已接受 T0 数据 + dated 身份 / 通达信板块成员
    → 核心因子/全市场画像/相对强弱/轮动/市场/Focus/Forward
    → 真实 Owner 字段（日期、复权、窗口、单位、质量、lineage）
    → BFF/API 规范化读取
    → 六入口页面完整可操作
    → IAB 浏览器实际看到、找到、点击、比较并解释数值
```


**一个接口返回 HTTP200 / 一个数字显示出来 / pytest 全绿 / 六个菜单可以点到，均不足以证明整条链 PASS。**


### 0.2 绝对不要消耗精力的内容


- 不建设 Python 热加载、Git 自动拉取、模块启动指纹取证、动态发布服务、自动重启守护、托盘、Windows 服务 ACL、Windows 整机重启或 Edge 专项适配。
- 不将 R2.2 上一轮“旧 PID 未加载最新版”扩展成新阶段。用户正常关闭并重新打开工作台即可；如旧进程尚在运行，测试改动前给出一句提示，不绕过任何安全限制，也不因此阻止**隔离端口/静态代码/离线数字**验收。
- 不因 10/12 尚未交易、Forward 样本未成熟、历史 strict PIT 首获数据不足，而阻塞**可基于 10/09 已接受真实快照交付的其他业务功能**。
- 不重新审计已通过的 R2.1 全量离线抽样，不重复生产 4GB Owner，只重算新修复涉及的具体字段和必要反例。
- 不为过验收伪造 Owner、回填未来信息、统一将缺数视为 0、模拟真实新闻、复制其他接口 JSON 给缺失接口、偷偷把运营重建成员标成 as-recorded PIT。
- 不强改旧 capability/Accepted Head 或不可变 receipt；研究运营展示、历史外部验收、长期统计有效性三者独立标识。
- 不写入 D:/new_tdx；所有临时/pytest/cache 只能放 G:/codex_tmp；项目根以 G:/codex work/大A交易 的仓库现状为准。


## 1. 已知基线与本轮复验范围


2026-10-09 最近一次前端外审（R43 R2 FP 入场）实际确认：**已有六入口、股票代码搜索、板块详情及成员、市场四轴、Focus 读域等可用基础**；同时记录部分页面被单个 SOURCE_INCOMPLETE 子接口整体阻断，以及多个缺失的 dated Owner。


当前需**重新核实，而非照抄旧结论**的缺口：


| 合同范围 | 之前已观察到的缺口 | 本轮处理 |
|---|---|---|
| FP03/04 | HTTP200 + SOURCE_INCOMPLETE；市场/Focus 某子接口失败使整页不可用 | P0：真实 Owner/API 绑定 + 独立区块错误隔离 |
| FP05 | 市场四轴有数据，但今日真实变化/风险/净信息未全部形成 | P0：独立字段来源与变化排序实测 |
| FP06 | 板块完整成员可读，timeline/overlap 缺或权限不一致 | P0：实际板块研究任务完整链 |
| FP07 | 搜索/画像可用，chart 与结构 timeline 部分缺失 | **最高优先级：日周月图、关键价、未入选解释** |
| FP08 | Focus 对象与事件可读，但 Episode/Anchor/Observation/Outcome 语义及自动持续跟踪有缺口 | P0：读域正确、重复日观察链；自动写入有独立安全门 |
| FP09 | 市场 breadth/indices/limits/ladders 子 Owner 不全；不可让一个错误挡住全页 | P0：真实市场统计分域对账 |
| FP10 | Forward statistics/plans/fep/settlement 部分接口缺 Owner | P1：读域真实、成熟度语义；不造已到期结果 |
| FP11/12 | dated 诊断/Replay/Compare 不全，严格历史 PIT 权限易误导 | P1：真实已存在能力可用，无法证明的范围显式保留 |
| FP13/14 | 真实全站浏览器及联合正式发布不足 | 本轮先做产品范围验收；发布全门仅在对应 FP13 满足后进入，不靠切全局开关 |


源码线索（执行前重新复核）：`src/workbench_service/research_bff.py`、`domain_views.py`、`production_v4.py`、`operational_gap_bff_v2.py`、`src/workbench_service/static/`、`src/v4/`、`src/focus_tracker/`。**这些是历史核对路径，不保证最新分支每项都存在；先检索真实代码。**


冻结数据基线：运营 accepted_trade_date=2026-10-09，原研究 Head SHA `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；严格历史 PIT Head SHA `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。这些是**旧的冻结对照值**；若执行时出现合法后继新 Head，必须记录事实并选定明确统一 T0，不能把旧值当永恒数据。


已有 2026-10-09 两板块样本：通达信 INDUSTRY:T0706 电气设备（322 成员）和通达信 GN CONCEPT/THEME:880904 智能机器（1160 成员），R2.2 已验证 ret1/ret5/median/breadth/LOO 18 项。此样本可以复用，**不要再上传重复 ZIP**。


---


## 2. 执行包 ALG-01｜当前实际运行算法到字段的“可核查”总盘点（P0）


以最新分支/HEAD、V4 主合同、此前 FP 14 卡和最近冻结 Owner 为输入，建立**算法计算事实 × 页面合同缺口表**。不可把“有代码”推断为“有真实 Owner”，也不能把“有 Owner”推断为“页面展示正确”。


每一行至少具有：


`feature_id, contract_section, producer_code, factor_or_algorithm_version, exact_input_owners, T0, member_set_asof, PIT_scope, output_owner_and_field, data_quality, field_unit, field_window, test_oracle, BFF_route, UI_route/component, browser_result, current_verdict, fix_owner`


按下列独立性质分别记账：


- **ALGO_FORMULA_VALID**：逻辑/单元/独立 numeric oracle。
- **DATA_CURRENT_VALID**：Owner 真正包含指定已接受 T0 的最新字段、证券池/板块 as-of。
- **API_BINDING_VALID**：BFF 返回正确对象、单位、质量和 context token。
- **UI_RENDER_VALID**：IAB 页面真的显示可解释的值、能操作/查看详情。
- **GO_FORWARD_VALIDATION**：真实后继结果积累/成熟度；不依附算法工程 PASS 自动成立。
- **STRICT_PIT_VALID**：真实首次可用/当时成员及 as-of；事后重建不得填 true。


结果至少列出**六入口 + 14 FP + 主要 V4-03～15 因子族 + V4-16～22/FEP 当前允许的运营读取范围**；过去已获得且输入与算法 hash 未变的正式证明可以 PASS_KEEP，不能机械全部重新验算。不得把所有旧未成熟 gate 都变成全站产品开发硬阻塞。


交付：`CORE_ALGO_UI_LINEAGE_MATRIX.json` + 8～15KB 人类可读差距摘要。所有关键 P0 失败给“现场来源/路径/输入行/字段/预期/实际”。


## 3. 执行包 ALG-02｜独立数值与交易研究语义审计（P0，优先）


**先实数后页面。** 使用真实 10/09（或实际选定并绑定的最新已接受 T0）的冻结 Owner、少量证券/板块纵向案例、以及明确分开的阴性/边界 fixture；自编一个**不 import 被测业务计算模块的简单 oracle**，禁止仅从 producer 复制最终结果作为 expected。输入均有 SHA/日期/数据源。


### A. 日/周/月技术结构与前置字段


- 价格、成交量、成交额的来源主权威（Native TDX amount vs BaoStock 差异未闭合不能偷换）；Raw/QFQ 序列/复权坐标、当月/当周 partial、停牌、除权、跨节假日。
- MA20、ATR20、ret1/5/20、放量/缩量/换手字段的**具体窗口、分母、复权状态与未知规则**；当前日值与 T-1 对照，排除前视。
- 选 20～30 只股票：覆盖趋势上涨/回落、突破未确认、无明显信号、复权事件、停牌/新上市/退市边界。选不出某类真实样本时标 NO_REAL_SAMPLE 并另测明确 FIXTURE，绝不伪装。


### B. 全市场 Daily Profile/个股状态与信号


- 全池证券画像每天都能定位该股状态，若不在 PREWATCH/关注/榜单必须解释 `NOT_ELIGIBLE / UNKNOWN / NOT_IMPLEMENTED / OUT_OF_UNIVERSE` 的真实不同原因。
- 早期关注、当前强势、结构突破/回踩/相对强弱、Waiting、Invalid、风险变化，应清楚映射原合同字段/状态 reducer/阈值、证据和“不选原因”。不能用单一大涨幅榜代替提前观察。
- 可观察 F/R 与竞争 H 假设区分：行情和结构数据只证明 F/R；`洗盘、主力吸筹、出货`等不得从日线值直接断言。页面可提供情景解释，但注明非资金账户事实。
- 信号选择与展示去重：先计算/稳定排序候选板块再确定 5–10（硬上限15）展示，独立股票变化≤30，**不可让未展示的第16+板块消耗独立股票名额**；首页不是所有库存榜单简单拼接。异常无信号仍应有合规解释型观察池，不捏造买点。


### C. 通达信行业/概念、Rotation 与相对强弱


- 行业与概念唯一来源/成员版本：TDX INDUSTRY+GN CONCEPT（内部可能存 THEME），不悄悄变成 CSRC 分类；当前重建归属与严格历史 PIT 分开。
- 原算法的 Native/LOO、ret1/5、breadth、overlap、leader、结构/轮动阶段、强度/健康/边际变化与金额类字段，**按各自合同公式**复算；不能将同一证券在跨板块综合分母中重复计数。
- 选至少 4 个板块：一强一弱、一大工业、一 GN 概念；两组已有 R2.2 独立 oracle 可复用。增加 1 个历史同形异因/阶段转变的实际冻结对照（有可靠数据才可提供）。
- 对 Rotation 递归 reducer/state transition：至少 3 个连续真实观测点，分别列“先前状态→新增 F→新状态/未知原因→失效”，缺数据只能标 SCOPED/UNKNOWN，不能仅拿 1 天评分冒充完整轮动。
- 近期强势/退潮板块仍在旧排行榜的滞后问题，要用稳定排序与生命周期状态解释验证，不能事后挑成功样本。


### D. Market 四轴/实际市场统计


- Trend、Breadth、Participation、Stress 四轴计算/归一化、eligible universe、未知/停牌剔除、权重、重复计数、RISK_ON/NEUTRAL/RISK_OFF/CAPITULATION/RECOVERY_ATTEMPT 的原状态映射（**不自行修改设计阈值**）。
- 对涨跌停、指数及梯队只使用可追踪 source；没有分钟逐笔时不得声称精确首封/炸板路径；新闻题材不能用凭空编造的叙述填。
- 对照 API 的 market 和四个子端点的数据含义；`SOURCE_INCOMPLETE` 是未完成，不是 “无涨停/无风险/四轴=0”。


### E. Focus / Forward / FEP 真实含义


- **Focus是用户研究持续跟踪对象**，Validation Cohort 是全部合格信号的独立检验样本，两者不可互相替代。Episode/Anchor/T0/Observation/事件/outcome 必须是真实分层字段，不允许 focus/episodes、/timeline、/anchors、/observations、/outcomes 返回同一数组伪装不同信息。
- 用至少 2 个实际 Episode 和 1 个边界反例检查 state transition、失效后再观察、重复增量日不重复新建 episode、同板块风险暴露。写入需遵从当前真实工程准入，**不为页面展示强开未授权的自动写权限**。
- Forward 入组、截止观察、T+1/T+3/T+5 到期、PENDING/RIGHT_CENSORED、结算基准及 benchmark、affine 复权/价格变换；FEP 仅在现有合法真实输入和模型结果已存在时读取，否则显示未具备运行条件而非伪预测。
- 不宣称真实 OOS 优势、参数最佳或统计显著性；已冻结 T0 预测不得用 T+1 结果反向修改，盈亏/胜率分母仅从到期成熟的真实样本计算。


### 审计输出与硬验收


`CORE_NUMERIC_ORACLE_MINIPACK.zip`：源输入短摘、独立脚本、expected/actual/delta、SHA、QA 模板，建议 ≤3MiB。至少覆盖上面 5 域的**已存在真实算法值**；某个域没有正式可计算 Owner，必须标 `SOURCE_NOT_PRESENT` 或 `CAPABILITY_NOT_READY`，不得用 fake fixture 使生产验收全绿。


**P0硬错误**：错 T0、前视/未来事件污染、状态机 fail-open、错股票身份/板块 taxonomy、错误复权坐标、错误分母/重复成员、旧历史值当新日、伪造真实结果、无数据却展示明确买卖结论、未 mature 就结算、页面数值与后端 Owner 不一致。发现后只定点改受影响公式/映射/消费端，保留精确的前后反例。


## 4. 执行包 BFF-03｜真实 Producer → API → 产品字段对账（P0）


基于 ALG-01/02 先审查现有 BFF，不是再凭目录名造一套平行后端。


依次验证以下真实接口族（项目实际路径优先）：


- 通用：`/api/v4/context`、`/api/operations/status`、`/api/v4/home`。
- 个股：`/api/v4/stocks`、`/api/v4/stocks/{id}`、`/profile`、`/chart`、`/timeline`；代码/中文名/别名搜索、state、不入选原因、F/R/H、周月。
- 板块：`/api/v4/sectors`、`/api/v4/sectors/{id}`、`/members`、`/timeline`、`/overlap`。
- 市场：`/api/v4/market`、`/breadth`、`/indices`、`/limits`、`/ladders`、`/api/v4/events`。
- Focus：`/api/v4/focus`、`/events`、Episode/Anchor/Observation/Outcome 子路径（按仓库真实路由）。
- Forward：`/api/v4/forward`、`/statistics`、`/plans`、`/fep`、`/settlement`。
- 诊断/历史：`/api/v4/sources`、`/api/v4/diagnostics/*`、`/api/v4/replay`、`/api/v4/compare`。


每一个 route 记录 `http_status, business_status, field_schema, coverage_count, source_binding, data_cutoff, role_in_page, context_token`，验证数据型别、单位、窗口、质量状态、对象关联、分页 token、搜索/过滤/排序稳定和旧 token 409。**HTTP200 + SOURCE_INCOMPLETE 不可计作字段覆盖 PASS**。页面无来源时局部显示可解释状态，不得返回通用假指标。


特别检查旧报告点名的候选缺陷，先确认是否已修：


1. 市场 breadth 失败后是否仍能渲染 indices/limits/ladders/原市场四轴；
2. Focus Forward 子接口失败后是否仍能浏览 Episode；
3. chart/timeline 真实 Owner 是否接通；若已有 producer/RAW/QFQ，不许因为前端字段错配就报成“算法根本不存在”；
4. Focus 子路由是否错误地重复同一 Episode；
5. homepage 变化排序与被第16+未展示板块占据去重集合的问题；
6. `source_mode=OPERATIONAL_PRODUCTION_ACTIVE` 是否被用于未获相应分域准入的字段；不能统一显示全部生产 / 全部未授权。
7. `PIT_ELIGIBLE=false` 的 corrected 历史比较必须醒目标记；严格 PIT 不得靠 as-of UI 装饰冒充。


交付 `API_FIELD_CONTRACT_AUDIT.json` + 精确“producer 有/Owner 有/adapter 缺/UI 缺”责任矩阵。修复后输出前后同输入/不同端点的期望-实际差分，不新造全量数据库。


## 5. 执行包 UI-04｜六入口核心用户体验与真实研究功能（P0）


**不是美化页面，也不是重写框架。** 复用已有六入口、导航、组件和工作台路径，按合同 §62A–69 对照实际产品功能。用户不应为了看 V4 研究而切回 V3/Shadow。默认研究页中文，底层 SHA/枚举在“诊断/字段解释”可点开查看。


| 入口 | 本轮必须实测的核心用户路径 | 可接受的缺数表达与禁止项 |
|---|---|---|
| 今日总览 FP05 | 四轴+风险环境、今天变化和净信息、轮动前后、行业/概念变化、独立个股列表、点击对应详情、风险退出 | 当天尚无新行情显示 10/09 last-good 和时间；没有变化 Owner 解释缺失，绝不全站 Unknown 或把旧日当实时 |
| 板块研究 FP06 | INDUSTRY/GN 分类、状态/成熟度/健康筛选、强度与轮动排序、成员扩散、Why Now、时间线、Overlap、成员列表完整分页、从板块跳个股 | source membership latest-reconstructed 与历史 first-available 明确；某 timeline 无证据不清空当前列表 |
| 个股研究 FP07 | 任意股票代码/中文名搜索；Daily Profile 与是否入选；日/周/月真实 K+量；F/R/H/关键价及来源；板块归属；关注/观察；Waiting/Invalid 解释 | 不在候选不等于无数据；K 线缺数不允许随机绘制；H 层不是可确认账户行为 |
| 关注跟踪 FP08 | Focus 真对象搜索/加入权限提示、Episode 列表、事件/Anchor/Observation、路径变化、退出/再次入场条件、到期 outcome 关联 | 未开合法持久化自动写入时只读或明确禁用；不得用 Cohort 代替 Focus；某子区域失败其它仍可用 |
| 市场与事件 FP09 | 四轴、真实指数/宽度、涨跌停统计及规则、梯队、题材事件来源、点击板块/股票、缺口说明 | 事件源不存在不得自动抓假新闻；一个子路由不阻塞整个市场页 |
| 数据与诊断 FP11/12 | 数据源日期/质量、TDX/BaoStock 差异、字段算法/窗口解释、观察失败原因、历史 replay/compare 明确证据类型、老工具收纳 | corrected 不能标 strict PIT；普通用户第一眼显示中文现象/原因而非 hash |


**共用完成门：**
- 搜索与筛选真正作用于全量 dataset（server/page API）而非仅过滤前六条。
- 分页/排序稳定、翻页不丢筛选、索引和对象身份不变；页面不以 `limit=6` 或固定 6 个数据卡代替完整研究功能。
- 股票/板块/事件/Focus 互相可导航；返回、刷新、上下文切换后日期不串。
- 首页只显示变化及风险的“变化对象”；不把全市场 5,000 多证券铺在首页，也不能删掉底层全量画像。
- 每个数值展示来源、T0、算法版本/质量/复权/所属板块和关键价出处；中文主标签、数据诊断抽屉展开更多技术细节。
- 页面到处 SOURCE_INCOMPLETE 且确实有真实 Owner 的，定位到 reader/adapter 错误并修；确实无 Owner 的，保留具体原因和应补 producer。
- 个别区块故障只让本区块出错，其它独立功能继续使用。
- UI 不能给交易建议当作确定结果，不用上涨后结果修饰冻结 T0 研判。


交付 `UI_FEATURE_ACCEPTANCE_MATRIX.md`（逐功能当前状态、修复记录、证据、实数抽样），不是单一“首页截图”。


## 6. 执行包 QA-05｜Codex 内置浏览器真实 E2E（P0）


**用户已取消 Edge 专属门；IAB 即正式工具。** 能用既有工作台服务就用当前真实只读快照；若代码已修改但当前运行进程仍旧，用户自行正常退出并重新启动一次以便观看新版本，Codex 不再做特殊进程控制/取证。不要在端口被占用时强行 kill，也不因为等服务重启而放弃隔离回归。


分两组独立证据：


**A. 不依赖真实服务重载即可完成**：
- Python/BFF API 契约、结构化页面组件测试、基于**明确标注的冻结 10/09 真实 Owner** 的隔离 HTTP、权限/日期负例、数字 oracle。
- 不使用 mock 服务通过后声称“用户正在访问的生产网页已经更新”。


**B. 真实工作台页面浏览器观察（用户正常重新打开服务后）**：
- IAB 1366×768 和 1920×1080；从 `/` 或真实默认入口进入；六入口逐页、每页核心详情、跨页跳转、代码与中文名查询、实际排序/分页/筛选、股票日周月图、板块时间线/成员、Focus/Forward、诊断、replay/compare。
- 每入口至少一条**真实 Owner→API→DOM** 数值对应案例，字段不全应精确列未满足合同项。
- 10/10 无新交易日时仍显示 10/09，缺数区块局部降级；同一 context token 统一，故意旧 token 返回 409 后正常刷新恢复。
- 单域故障 / 断网 / 慢请求 / 网络恢复、数据空数组、长中文名、超长 diagnostics digest、浏览器刷新/后退、日期变动期间避免串读与横向溢出。
- 有页面功能依赖 10/12 新日真实 source 时只对**该项**记录 WAIT_REAL_DAY；其余 10/09 可验能力不得一起暂停。
- 每域至少 1 张有业务含义的截图/DOM 信息（不要求高像素录像），源代码 commit、上下文日期与截图时间要同时留证，禁止旧截屏当新结果。
- 既有 FP13/FP14 真实记录可作为历史留存，但不能只复述 10/08 旧浏览器绿灯。


**硬性实测判断：** 页框能显示但算法值错、跨 T0、详情找不到、无限 UNKNOWN、搜索只搜前 6、某子接口失败导致整个页面消失、Focus 不同子路由复用同数组、未经确认的 PIT 以严格历史呈现，均 FAIL。


## 7. 执行优先顺序（不要回头重做 14 卡）


1. **Round A（P0 审计优先）**：ALG-01 总矩阵＋ALG-02 实际核心数值/股票/板块/市场/信号/Focus核验。定点暴露错误并给真实样本。**可以直接在当前周末运行，不等 10/12。**
2. **Round B（P0 用户可见修复）**：BFF-03 + UI-04 优先 FP07 个股图表与未入选解释、FP06 板块研究、FP05 首页风险变化、FP09 市场四轴/子路由隔离、FP08 Focus 读域；复用当前实现，只修实证错误。
3. **Round C（P1 补齐）**：Forward/结算成熟度、市场与事件具体指标、诊断、Replay/Compare，按真实数据与安全权限逐域完成；未有第一可用源的严格 PIT 只能保留受限，不得伪造以求全通过。
4. **Round D（P0 UI QA）**：QA-05 IAB 真实逐页/数值回读＋关键失败隔离，关闭修复项。与 ALG-02 数值证据交叉核对，产出发布候选。
5. **现有动态日更轨道**：10/12 真实 Source/发布/接口更新继续按 DD R2.2 旧事实门独立跟踪；不为等新交易日锁住 A～D。本轮**不建设任何代码热更新或工作台后台维护功能**。


如果单轮工程量过大，Codex 至少完整完成 A+P0 的 FP05/06/07/08/09 BFF+UI 与对应 IAB 验收；P1 功能按精准列表保持 OPEN_NEXT_BATCH，不能提前写 FULL_PASS。每个轮次都提供新增证据后再由外审判断，不因“做了很多”就自封通过。


## 8. 分域验收标准和产品总状态


| 领域 | 工程验收必须具备 | 不允许的替代 |
|---|---|---|
| ALG | 真 T0、真实 Owner、独立数值正确、阈值/状态合同一致 | 仅 producer 单测、复用自身输出作 expected |
| DATA | 证券池/成员/身份/截至时间/复权/PIT 标记正确 | 以 10/09 数量固定推导未来日期 |
| BFF | 每个合同 API 返回正确字段/原因/单位/时点；缺失子路由不遮蔽其它数据 | HTTP200 视作整体 API PASS |
| HOME | 变化+风险/四轴+真实去重和排序 | 用收盘价大排行榜填首页 |
| SECTOR | 通达信来源、状态、成员、因子、Timeline/Overlap，浏览器可看 | 只有板块名称+成员数 |
| STOCK | 任意搜索、全市场画像、日周月 K、候选与未入选解释、F/R/H | 只有股票代码/收盘价 |
| FOCUS | Episode / Observation / Anchor / path/outcome 语义分层及合法权限 | 同一 Episode 伪装全部子资源 |
| MARKET | 四轴、指数、breadth、涨跌停/梯队、事件来源/局部故障隔离 | 其它 API 缺失就整页错误 |
| FORWARD | 合法入组、成熟度、结算/统计样本、风险解释 | fixture 或未到期样本冒充已盈利 |
| IAB | 六入口双宽浏览、搜索排序分页、真实数值与 UI 一致、单域故障隔离 | 截图仅有导航壳、HTTP200、空态截图 |
| SAFETY | 原已接受 data/PIT/head、TDX 只读；历史 freeze 不改 | 改旧收据/放松 QA/绕过能力授权 |


**验收要区分四种事实，不得混为一谈**：
- `ALGORITHM_SCOPED_PASS`：指定算法/样本/状态机审计通过。
- `PRODUCT_DOMAIN_PASS`：指定页面真实可用、合同字段均有证据。
- `PRODUCT_CORE_RELEASE_CANDIDATE`：重要产品域完成，具备外部审核资格；需保持明确 OPEN 项和发布安全。
- `FULL_PRODUCT_PRODUCTION_RELEASE_PASS`：原 FP01–FP14 产品合同在允许真实范围内全部过门，包含 FP13/FP14 联合验收与原子发布；Codex 不得自授独立外部 FULL_PASS。


若 FP12 严格历史 PIT 现实无法得到首次可用证据，不能通过假数据获得 FULL_PASS；允许 corrected 比较作为**明确降级功能**单独通过并标记 strict PIT 待能力成熟。若无法访问真实浏览器，不可用隔离测试声称 UI_PASS。


输出必须包括：每卡是否 PASS/FAIL/NOT_VERIFIABLE/WAIT_REAL_DAY、每个 P0 缺陷的修复前后数据/页面证据、哪些过去已有功能不需要重做、下一轮最多 5 个具体工作项。失败或缺证据应分域阻塞，而不是全站降成 UNKNOWN。


## 9. 正式交付、GitHub 和 Drive 预算


本轮新增成果建议最少量：


1. **CORE_ALGO_UI_EXTERNAL_AUDIT_R1.md**：冻结输入/HEAD、六入口和算法结论、独立复算、P0 缺陷、已修/仍缺、日期/时点、研发与验证分层、唯一总状态。
2. **CORE_ALGO_UI_LINEAGE_MATRIX.json**：模块→producer→Owner→BFF→UI→验证的真实矩阵；可拆 1 个小 CSV。
3. **CORE_ALGO_UI_NUMERIC_MINIPACK.zip**：小样本必要源输入、独立 oracle、SHA、expected/actual；避免复制 10/09 R2.1/R2.2 已通过的完整样本。
4. **CORE_ALGO_UI_IAB_QA_INDEX.json** + **最多 6～8 张关键截图**：一张/域原则，索引包含界面日期、浏览器、模块、source HEAD、截图文件 SHA、明确场景。
5. **CORE_ALGO_UI_REPAIR_LEDGER.md**：改动文件、真实缺陷、修复前后反例、commit、回归命令/退出码、P0/P1 遗留和下一步；如确实无改动可只输出审计+差距。


**Drive 整轮新增证据建议 ≤5MiB，硬上限 10MiB，单文件 ≤5MiB，最多 10 个文件；以小图压缩、数值抽样和一个 ZIP 优先，不能拆卷超上限。** 巨型 Owners/raw、数据源包、数据库和完整浏览器录像必须本机 G 盘保存；Drive 只放必要 hash/小样本。正式文件放项目现有 Drive V4 任务归档目录，云端读回 byte/SHA；工程 commit+push 至目标分支，写出精确 RESULT_SHA。原用户文件、历史原始作答和验收不可覆盖。


执行结束 Codex **不能以脚本自测 PASS 代替我后续的独立外部验收**。需要能让我从 GitHub 和 Drive 拉小包重新跑 oracle，随机核查 API-UI 对应字段，再签正式裁决。


## 10. Codex 直接执行指令（本节可单独复制）


> 请以本任务卡为当前执行合同，先同步 Drive 的 V4.2.2 REV2、FP01–FP14、R43 R2 差距矩阵以及最新仓库 AGENTS.md，git fetch 后冻结真实 BASE_SHA。不要再做热更新/服务加载取证/托盘/Windows 维护；用户个人使用，代码改完正常重启工作台即可。先做 ALG-01/ALG-02 对真实已接受 10/09 数据的**核心算法+信号语义独立数值审计**，随后对 BFF/API 和六入口逐条查 Owner、查字段，优先修真实个股日周月图/画像/未入选解释、板块轮动和时间线、市场四轴及子路由失败隔离、首页变化去重排序、Focus Episode/Observation 分层与 Forward 合法读域。前端使用 Codex 内置浏览器 IAB，在 1366/1920 两尺寸做实际搜索/分页/图表/跨页/数值 E2E；没有新交易日保持 last-good，未成熟 Forward 与严格历史 PIT 按真相标注。先完成能靠现有真实数据检验的功能，不等 10/12 新数据，不复算 4GB Owner，不伪造任何业务结果。真实 bug 最小改代码+定点回归，交可独立复核的小包/截图索引/MD 报告，push GitHub、轻量 Drive 回读，给我做外部验收。没有现场证据的一律 NOT_VERIFIABLE，不签 FULL_PASS。


## 11. 依据文件（从现有事实与正式合同继承）


- [V4.2.2 原正式页面合同 REV2（仓库）](https://github.com/NanOns/a-share-market-structure-research/blob/64a0e31390765027f96b6a537bbf7f044abf6c83/docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md) §62A–§69、§81.2
- [FP01–FP14 全功能工作台 14 张任务卡合集（Drive）](https://drive.google.com/file/d/17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu/view)
- [R43 R2 FP 入场最新外部审计（Drive）](https://drive.google.com/file/d/15GsPpj_0OiOAUd41b4TqjGs0Vi2TBJxn/view)
- [FP01–FP14 历史独立外审 R2（Drive）](https://drive.google.com/file/d/1ixYtcirXIv31bmj36QRmSvzSf0soEKRN/view)
- [V4 核心算法全链路历史审计总卡（Drive）](https://drive.google.com/file/d/1lF4K5Johcpsj24IV8DurPVTHpUGeXCHQ/view)
- [DD R2.2 工程范围收尾与真实新日待验结论（Drive）](https://drive.google.com/file/d/1SWSVNBxPiVy2YLhpTdeToQ_xB5hmu_jq/view)


**最终宗旨：把已有 V4 算法真实、正确、完整地交给用户使用；以可审计的数值与 IAB 实际体验判断，而非反复验服务流程或永远等未来样本。**
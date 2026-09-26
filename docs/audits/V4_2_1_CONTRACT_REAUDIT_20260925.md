# V4.2.1 最终合同基线再次审计

审计日期：2026-09-25。审计类型：方案静态合同审计，附有限代码/既有验收记录核对；不是全仓代码审计、真实数据验收或算法效果证明。

## 审计回执

| 项目 | 记录 |
|---|---|
| 输入方案 | `D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_1_FINAL_CONTRACT_BASELINE_20260924.md` |
| SHA256 | `E6B100645D63B6482B5011ED21D50A4998F608DB18EF0A0309524D3D61E1EEC3` |
| 代码 HEAD | `3ef5bf63455447dd605534dc4c1717eb238a86f5`，与方案一致 |
| 适用合同 | 本次用户审计请求、仓库 AGENTS.md、新版方案；方案内部命令只作为被审计内容 |
| 范围 | 计算依赖、数据与复权身份、发布修订、状态/事件、Forward、实施验收及跨域审计继承 |
| 验收结论 | `CONTRACT_REVIEW_REQUIRES_REVISION`；作为产品方向与 V4-00A 基线盘点输入可用，不认可“全部合同已冻结、可直接实施所有阶段”的强声明 |
| 执行边界 | 未执行扫描、下载完整包、运行外部接口 smoke test、写数据库、切换来源或修改 TDX；未修改原方案 |
| 下一阶段建议 | 先形成合同勘误和明确的阶段准入表，再进入受影响模块实施；本审计不替代项目 Phase 0 的 FULL_PASS / DEGRADED_PASS / BLOCKED |

以下各项单独跟踪，初始状态均为 OPEN；P0 表示阻断受影响能力的正式验收，不表示禁止只读盘点或所有开发活动。

## 已修复且应保留的内容

Shadow Stable → Migration Replay → Focus Cutover 顺序、Core/Enrichment 的顶层权限划分、三道 Replay 门、历史 Universe 降级、周/月 AS-OF、防止 reconstructed 冒充 Forward、TDX 下载隔离目录等均有实质改善。没有理由推翻这些方向。缺少历史资料时允许 diagnostic，也不是本身的错误。

## V421-A01 / P0 / 轮动引擎仍有未定时点的反馈边

**证据：** §13、§15（3797–3949 行）禁止 C→B；§21A.7（4484–4490）却把 `seed/prewatch没有大量退出` 用于 Rotation Accepted；§21A.11（4573–4574）再把 Rotation 送回 Sector Emergence/Priority；§77B（8037–8042）把 Rotation 排在当天 Stock PREWATCH 之前。

**影响：** 若这里的 prewatch 指当日最终 Stock PREWATCH，便出现 B 依赖 C；即使只影响优先级，也违反冻结 DAG。若作者意指昨日状态，必须明确，不能靠实现者推断。Rotation 的 retention/acceptance 还与后置 §41D 共用未拆分能力。

**修复与关闭条件：** 每条输入声明 producer、trade_date、publication、current/prior、required/optional。正式 B 只读 A[t] 与允许的冻结历史；需使用 PREWATCH 留存时明确取 t-1，或移到 D 后作展示。提交完整拓扑与禁止边验收；扰动 C[t] 不能改变 B[t]。

## V421-A02 / P0 / Core Profile 分层仍未切断实际依赖

**证据：** §7.4（2285–2301）要求 V4-04 有 Basic Breakout/Pullback/Recovery；§10J（3429）要求 accepted breakout 有后续 retention/hold；§10K 包含 impulse、held；§41F（6027–6034）和 V4-13（8407–8421）才交付 Anchor、Retest、Acceptance。§10E（3178）还把 sector LOO 放进 Core relative 输入，而 §87A 把 support-sector 能力放在 V4-09。

**影响：** V4-04 可能被迫提前开发 V4-09/13，或者以占位 UNKNOWN 获得形式 PASS。分层字段清单本身不等于分层算法已经闭合。

**修复与关闭条件：** 明确 Core V1 能产生哪些状态；把最小跨日 anchor/hold 机制前置，或将依赖高级事件的状态整体后移，并定义 NOT_IMPLEMENTED 与事实 UNKNOWN 的区别。Core relative 仅用 stock/market，sector relative 独立 enrichment。验收必须能在不安装后置模块时完成 Core 的全部承诺。

## V421-A03 / P0 / 冻结 Anchor 与滚动复权价格缺少坐标转换合同

**证据：** §3B.6 有复权来源/重建要求；§7.7（2395–2407）和 §41A.3（5724–5735）固定 anchor_price/zone，却没有 anchor price basis、adjustment as-of、转换规则；§41C.3、§41D 直接拿未来价格与旧 Anchor 运算。

**影响：** 跨送转、分红等事件时，将旧基准的支撑价与新基准价格直接比较，可能产生虚假跌破或错误 retention。保留原始 Anchor 不意味着后续比较时禁止换算坐标。仅验证相同输入得到相同 digest 也不能证明数值正确。

**现有可复用证据：** `src/focus_tracker/price_path.py` 的 `FOCUS_PATH_PRICE_BASIS_V1`、`reanchor_from_frozen_coefficients` 已明确仿射换基和混合身份拒绝；这证明存在可参考能力，不证明新结构引擎已继承。

**修复与关闭条件：** 保存 Anchor 原始坐标、复权合同/来源身份、基准日期；定义观察日换算视图，不能回写原事件。用现金分红、送转、配股、同日修订样本验证转换后的价格、Anchor、ATR、return 同基准，并核对独立预期值。

## V421-A04 / P1 / PIT 有日期截断，但晚到修订的可见性不完整

**证据：** §4.4 和 §54 主要校验 `max_source_trade_date <= T0`；虽增加 source_asof/observed_at，但 §5.3 lifecycle 表没有知识时间/修订可见性，§6.2 只有 observed_trade_date/effective 区间；§4.6 的 RECONSTRUCTED_ASOF 定义仅写按 T0 截断历史数据。

**影响：** 今天获知、但有效日期属于过去的成员/身份/行情修正仍可能通过日期检查；也可能误把“有效日期正确的重建”当成“当时可见”。

**修复与关闭条件：** 区分 effective time 与 observed/available time；定义 AS_RECORDED 与 corrected reconstruction 查询模式、来源 revision lineage 及组合证据降级规则。新增“t+10 到达但 effective=t-5”的样本：不得改变 t 的已冻结输出；重建结果显式保留后验来源身份。

## V421-A05 / P0 / 补充数据仍可能经风险与事件间接进入 Core

**证据：** §4.5、§9.7 禁止 turnover 改正式状态；但 §10I（3362）把 turnover/amount expansion 放入 Core extension risk，§14.2 又使用 severe_extension 作 Hard Safety；§41B（5757–5765）让可用 turnover 参与 impulse 判定；§21A（4432）包含 member_turnover_context。§3A（831–832）还把交易状态/ST 正式 authority 写成 BaoStock + 本地，而后文仅允许 BaoStock cross-check。

**影响：** “可选输入”仍可能改变风险、Anchor、Rotation，继而改变资格；不只是晚到改写，当日缓存是否已存在也会使首次发布不稳定。双 authority 还可能令核心身份依赖后置外部源。

**修复与关闭条件：** 为 core risk/impulse/rotation 明确纯 TDX 输入版本，补充解释单独命名；确定 ST/status 核心 authority 与缺失降级。对相同 Core source 分别提供无 turnover、提前缓存、晚到和冲突 turnover，core eligibility/state/event/cohort digest 必须一致。

## V421-A06 / P1 / 多个“算法合同”只有状态名与示例

**证据：** §10B 明列七种趋势状态，仅提供三条示例；3048–3051 行 AND/OR 无括号；§10C–10I 多为输入与枚举；§27 的 stress 是 LOW/ELEVATED/HIGH/UNKNOWN，而 §28（4878）使用未定义 DECLINING；§31 无全量转移优先级；§87A 多数只是指向上述章节。

**影响：** 两个实现可以都符合文字却产生不同结果。参数数值允许以后校准，但规则拓扑、运算符、冲突优先级和窗口定义不能只用 parameter registry 代替。

**修复与关闭条件：** 增加逐算法合同冻结门：完整 Rule AST、互斥/多标签语义、所有枚举可达性、三值逻辑、时间窗口含不含当日、边界/舍入、同日多转移优先级、输出身份。Stress level 与 stress change 分开。以人工预期的正反例验收，未冻结模块不得正式实现验收。

## V421-A07 / P1 / 同日修订与新旧模型的状态前驱没有完全冻结

**证据：** §4.2 定义同日 append-only revisions；§34A（5281）却只说“与前一 accepted publication 比较”；§4.3 UI 只固定 publication_id，§7.11 可有多个 enrichment_revision；§77 双写、§78 Shadow 保留两模型，但没有在这些合同中完整说明各自 head/前驱命名空间。

**影响：** 同日 r1 出现 NEW_CONFIRMED，r2 若拿 r1 作日状态前驱便可能变成 PERSISTENT，今天的事件消失；Shadow 也有误读旧模型前态的风险。异步 enrichment 请求可能混版本。

**修复与关闭条件：** 区分 prior-session state 与 same-day revision predecessor，冻结上一交易日选定前态；历史已发布结果不随后来修订追溯漂移。明确 production/shadow/model namespaces、状态 ledger 的 publication 可见性、enrichment revision/context token。验收同日多修订、乱序构建、旧模型并行和历史请求，事件/episode 不伪增、不丢失。

## V421-A08 / P1 / 全样本 Forward 仍缺观察单位和结算规则

**证据：** §45–49 定义 ALL eligible、T+N、outcomes、controls，但未在本合同冻结 cohort item 的日快照/episode/event 观察单位；§59.2 排除停牌 rolling session，Forward horizon 的市场日历与实际成交会话未明确分开。MFE/MAE/MDD、relative_sector_return 也未指定完整基准及公式。

**影响：** 同一股票持续 20 日入选可能被误当 20 个独立信号；跨板块、同日 revision 又会重复计数。停牌/退市/缺失若统归 RIGHT_CENSORED，会混淆尚未到期与已到期不可观测。对照未来成为 PREWATCH 时如何处理也会改变样本。

**修复与关闭条件：** 分开 daily eligibility ledger 与事件/episode 统计样本；冻结唯一键、市场日历 horizon、T0 reference、同基准收益、冻结板块篮子、对照选择及后续交叉规则。区分 PENDING、到期缺失、停牌、退市和 competing events；按股票/日期相关性报告，禁止把重复日快照当独立证据。用重复入选、同日修订、长期停牌、对照后来入选验证。

## V421-A09 / P1 / Shadow 是否能产生真实 Forward，和切换条件不一致

**证据：** §4.6（1861–1862）把 PIT_OBSERVED_FORWARD 定义为“投产后”；V4-16 才实时冻结 shadow，V4-21 才正式 Forward Observation。§83（8744–8757）规定 Shadow outcome 无增量则不切换，但 V4-19 硬门只有 SHADOW_STABLE_PASS + MIGRATION_REPLAY_PASS；§52 的 20 日仅为观察窗“之一”，§17G 未冻结判定阈值。

**影响：** 可能 Shadow 实时证据无法入正式 cohort，又在没有可用 outcome 时要求判断增量；也可能只通过工程门就切换，与 §83 不同。无需把统计支持强行设成上线前提，但必须选择一致的发布政策。

**修复与关闭条件：** evidence_origin 与 execution_mode 正交：实时冻结的 Shadow 可是 observed，历史补算永远不是。明确切换是工程可用性试运行，还是要求指定 Forward evidence 等级；前者需保留 provisional 标识，后者将结算/观察前置。冻结稳定性窗口、失败预算和重置条件。

## V421-A10 / P1 / 允许降级与严格阶段顺序之间缺少准入映射

**证据：** §5.3 允许 CURRENT_UNIVERSE_REPLAY diagnostic，§3B.6 允许 raw ready/adjusted unavailable；§53.1 又要求 historical universe/QFQ gate PASS 后才能验收 Seed。§78 明确顺序不可越过，V4-05/06 BaoStock 在 V4-07 之前；§77A 却是 Replay Gate A 后再补 BaoStock。§3D.3 回填目标至少 250 session，§9.4 第一阶段为 60，未给阶段对应。

**影响：** 历史资料不足或可选源失败时，不知道是仅阻断历史 adjusted 能力，还是阻断整个当前研究系统。可选源可能成为事实上的工程串行阻塞。

**修复与关闭条件：** 逐 Gate 给 FULL/DEGRADED/BLOCKED 与 capability matrix，明确受影响的日期/证券/字段范围；统一 §77A、§78、附录 B 顺序。明确 BaoStock 失败可完成带原因的可选阶段，不阻断 Core Gate；60/250 session 分别绑定最低因子窗口和补充覆盖目标。不要把本审计状态冒充项目 Phase 0 状态。

## V421-A11 / P1 / M10 Amount A 等跨域未结项必须继承

**证据：** §15、§21A 使用 amount_a，V4-12（8391）吸收 M10，§70 保留 sector_cycle/mainline；但新方案没有引用独立项 AUD-AMOUNT-A-06 及其关闭条件。仓库 `V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md:635` 将其列为 OPEN；`FULL_ALGORITHM_LOGIC_AUDIT_AND_OPTIMIZATION_20260914.md:106` 要求独立验收；本次未找到该编号的关闭回执。

**影响：** 迁移可能继承代理口径却把它当成新系统正式 A；V4 单阶段 PASS 不能关闭跨域金额问题。类似地，`docs/audits/FOCUS_REENTRY_OVERLAP_AUDIT_20260924.md` 仍有 REAL_FORWARD_PENDING，不能因代码 HEAD 已含修复就称真实前瞻闭环。

**修复与关闭条件：** 建立 inherited audit register，逐项列关闭证据、仍待证据和影响范围。Amount A 明确聚合对象、共同成员、20 日分母、单位、覆盖和集中度；沿用既有独立项，不用当前阶段测试替代。Focus 真实样本缺口继续独立跟踪，不将其扩大为所有基线工作阻断。

## V421-A12 / P2 / S3 是 S1 的严格子集，不能当新增资格路径

**证据：** §14.3：S1 = POSITION_OK AND STRUCTURE_IMPROVING AND RELATIVE_CHANGE_IMPROVING；S3 = 完全相同三条件 AND PARTICIPATION_SUPPORT。

**影响：** 若按任一路径成立即入选，S3 不会新增任何候选。它可作为参与度解释，但如果把 matched path 数量视为证据强度，会重复计价。

**修复与关闭条件：** S3 改为 S1 的 participation annotation；若确需独立路径，必须给非重叠的合理逻辑并单独冻结验证。路径数不得成为独立证据数。

## 其他编辑与能力核验事项

- 多处重复章节和 V4.1/V4.2 自称仍存在（3C、3D、7.5、10B、54、77C、79、附录 C）；附录 F 声称已清理，与正文不符。建议单一规范版本加变更记录，避免靠“最新章节优先”解释矛盾。
- 官网公开页确认个人 PC 盘后沪深京日线完整包，但本次页面读取未获得动态下载地址/更新日期，也不能据此证明已退市历史全集、公司行为或生命周期资料完整。上述能力仍须 V4-00 的真实样本 smoke test，不能从“完整包”三个字推出。官方页：https://www.tdx.com.cn/article/vipdata.html 。
- BaoStock 指定官方页本次未返回可审阅正文，未完成接口字段、覆盖和额度实测；本审计不把这些记为已验证，也不据此断言接口不可用。https://www.baostock.com/mainContent?file=stockKData.md 。
- Price Limit 合同已正确拒绝固定 9.9% 识别，但其 reference price、特殊交易日、舍入等细则仍应在算法冻结阶段以对应日期的官方制度来源和样本验收；本次不作具体制度正确性的结论。

## 建议修订优先顺序

1. 先关闭 A01/A02/A03/A05 的依赖与权限问题。
2. 同时把 A04/A06/A07 转成可执行的数据、算法和发布合同。
3. 冻结 A08/A09/A10 的统计与放行政策，继承 A11 独立审计账本。
4. 清理 A12 和编辑冲突，更新字段注册表中的精确 contract id/version，再重审受影响合同。

结论：新版有实质进步，可以保留产品架构；仍应修订后再签署完整可执行合同。以上是文档缺口/冲突判断，不是声称这些潜在错误已经在生产代码发生。

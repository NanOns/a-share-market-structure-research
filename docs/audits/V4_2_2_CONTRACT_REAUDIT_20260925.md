# V4.2.2 最新合同再次审计

## 范围与回执

| 字段 | 记录 |
|---|---|
| 日期 | 2026-09-25 |
| 输入 | `D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925.md` |
| SHA256 | `AC86F92F9CFAA3547A0BA99959E749DA02F0FA7F9C0A1568AD95627DB0200B97` |
| 仓库 HEAD | `3ef5bf63455447dd605534dc4c1717eb238a86f5`，与文档一致 |
| 适用约束 | 用户最新审计请求、AGENTS.md、新版方案及上一轮独立审计报告 |
| 审计内容 | 上轮处置核对、新增规范与旧正文一致性、阶段依赖、公式反例、发布/前瞻身份 |
| 验收结果 | `CONTRACT_REVIEW_REQUIRES_REVISION`；按方案 §81.4 自身要求，仍为 `CONTRACT_INCOMPLETE` |
| 执行内容 | 只读文档/仓库身份，运行纯数值公式反例，写独立审计记录；没有运行扫描、行情下载、数据库写入或切换 |
| 下一阶段 | 先完成规范统一与下列受影响合同修订，再复核；基线盘点可继续，但本审计不替代项目 Phase 0 状态 |

这是合同审计，不是对全部算法实现或收益效果的认证。P0 指阻断受影响正式流程的合同冲突，P1 指必须在对应模块验收前修复的问题。所有新项均 OPEN，独立于实施阶段 PASS 跟踪。

## 上轮问题处置核对

| 上轮项 | 本轮判断 |
|---|---|
| A01 同日反馈 | §13A/21A.4A 已明确 t-1 PREWATCH、纯 Core retention，原特定反馈问题在新增条款中得到修复；其他日内依赖见本轮 B05 |
| A02 Core 依赖 | §10A.3 已修复分层意图，但 §7.4/10J/41F 仍保留旧义务，未全文闭合 |
| A03 Anchor 换基 | 原坐标冻结、观察日换基、同基准、失败降级和真实样本要求已补齐；具体转换仍明确留给 V4-00E，不视为已经数值验收 |
| A04 双时间 PIT | 已补齐框架；实际已消费来源与版本选择规则仍见 B07 |
| A05 Supplemental 污染 | §9A 防污染条款和扰动验收正确，但旧 authority/输入表仍冲突 |
| A06 算法合同 | 新增冻结门是进步；并不等于现有所有 Rule AST 已完成，见 B04 |
| A07 修订前驱 | NEW/PERSISTENT 的同日前驱误用已修复；迟到前驱与统计事件修订仍见 B06 |
| A08 Forward | 已区分日账本和事件、市场日历和停牌；新增公式有确定错误，其他结算规则仍未闭合 |
| A09 Shadow Forward | 正交身份和临时切换政策已新增；旧枚举、结算交付阶段和旧切换政策未同步 |
| A10 降级门 | 能力矩阵方向正确；旧任务表仍在，Gate 的降级回执仍需精确映射 |
| A11 独立审计 | 已继承 OPEN 状态；Amount A 如何限制正式计算仍需明确 |
| A12 冗余 S3 | 原资格路径冗余已修复；现在是 annotation，不再重复计路径数 |

因此不能照抄 §0E 的 CLOSED 声明作为独立审计结论。

## V422-B01 / P0 / 同一份合同仍有两套相互冲突的规范

**证据与具体冲突：**

- §78：V4-05 是 Replay Gate A，V4-07 是 Seed，V4-08 是 Sector，V4-12 是 Structure；附录 B（10121–10157 行）仍是 V4.2.1 顺序：V4-05 BaoStock、V4-07 Replay、V4-08 Seed、V4-13 Structure。
- §87A（9943–9956）仍大量引用旧阶段号。按这张表 Seed/Sector/State 的交付日期与 §78 不一致。
- §10A.3（3489–3545）要求 Core 不依赖 Anchor；§7.4（2500–2516）仍要求 V4-04 交付 basic_breakout/pullback/recovery；§10J（4026）仍写第一阶段做基础突破。
- §9A 将 BaoStock ST/status 限制为 cross-check；§3A（858–859）仍列为正式联合 authority；§10I（3997）仍把 turnover 放在 extension risk 输入中。
- §51A 的 observed 枚举是 `PIT_OBSERVED`，允许 SHADOW；§4.6（1884–1903）仍限定投产后 `PIT_OBSERVED_FORWARD` 且正式 cohort 只接受该值。
- §10A0 的 Position 是 HIGH/MID/LOW，§10C 是 HIGH_ZONE/MID_ZONE/LOW_ZONE；Compression 是 COMPRESSED/EXPANDING_STRONG，§10F 是 COMPRESSING/EXPANDING_EXTREME；Relative 也有两套枚举。未说明它们是不同字段或显式版本映射。

**影响：** 实施者遵守一个章节就违反另一个；按旧附录拆卡可能错过 Gate，按旧 schema 可能拒绝新值。不能仅把这些当错别字。新增条款虽然明确方向，但没有将被替代的规范删除、标成历史或给出完整字段映射。

**关闭条件：** 只保留一套当前阶段、枚举、Core 字段和 authority；旧规范移到明确非规范的历史附录。自动检查任务引用、枚举、字段注册表与 producer 一致。页首日期仍为 09-24 可一并修正，但日期错误不是本项 P0 的原因。

## V422-B02 / P1 / MDD 公式对单调上涨路径返回正回撤

**证据：** §46A（7284–7285）定义 `PATH_MDD_CLOSE_N = min_{i<j<=N}(Close_j / Close_i - 1)`。

**已运行纯数值反例：** 收盘路径 `[100,110,120]`，该式返回 `+9.0909%`；实际没有任何峰值回撤，应为 0。N=1 且未明确定义 i=0 时还可能出现空集合。

**修复：** 如使用负号表示回撤，明确：

```text
P_j = 同一已验证观察基准下的收盘价，j=0..N
D_j = P_j / max(P_0..P_j) - 1
PATH_MDD_CLOSE_N = min(D_0..D_N)
```

也可使用正值幅度，但须整体反号并改写命名/解释。T0 必须参与峰值基准。MFE/MAE 也需明确只取 T+1..T+N；信号盘后形成，不能把 T0 日内高低点算进未来路径，并明确是否用 0 截断。

**关闭条件：** 单调上涨、单调下跌、先涨后跌、平盘、N=1、缺失会话和跨公司行为路径有独立预期值。本次 `[100,80,90]` 算例为 -20%，平盘为 0；单调上涨反例足以证明原公式缺陷。

## V422-B03 / P0 / 切换前需要结算结果，但结算仍被安排到切换后

**证据：** §52A（7595–7615）要求至少五个信号日、30 个股票事件的 T+5 成熟结果才能切换；§78 的 V4-15（9506–9508）只写 ledger/events/controls/Why Now，没有 outcome settlement；§87A（9966）把 `forward_outcome` 放在 V4-21，后者在 Focus/UI Cutover 之后。

**影响：** 按 Field Registry 和阶段顺序执行，会在 V4-17G 等待尚未交付的结算器。运行 20 天本身不能产生成熟 outcome。

**另一个政策冲突：** §52A 只要求最低观察充分性，不要求已证明长期优势；§83（9745–9752）仍规定“outcome 无增量”不得切换，未定义无增量与尚未证明的区别。

**关闭条件：** 将结算器、冻结基准、重试、修订、controls/outcome readback 在 V4-15 或更早交付，在 V4-16 每日运行；V4-21 只做继续观察。统一切换政策，明确样本不足时是等待而不是降低候选资格；明确严重退化的判定合同。

## V422-B04 / P1 / 冻结门本身会拦住当前文档，而且缺的不只是数值阈值

**证据：** §10A0 明确“状态名/示例不等于算法冻结”；§81.4（9701–9719）要求正式任务拆分前所有状态都有 Rule AST，缺项即 CONTRACT_INCOMPLETE 且不得自行补语义。但趋势仍写“示意拓扑”，SIDEWAYS 系列留给“剩余可评估空间和 relative state 映射”（3333）；Position/Relative/Compression 没有完整规则。新 Core 的 near_high20/60、drawdown20/60（3519–3522）未在 §87A 登记。

**影响：** 当前文档可以作为算法合同设计输入，不能同时宣称所有合同已完成、可以直接拆全部实现任务。注册表加字段名或一个 contract id 不等于填完规则。

**还需冻结：** UNKNOWN 的 required input 范围、已知 FALSE 与其他 UNKNOWN 的归约、状态可达性、阈值边界、窗口是否含当日、AST 括号、全量冲突决策。不能让每个实现自行解释。

**关闭条件：** 逐模块交付可执行规则和正反测试向量；将“全局框架盘点”与“对应算法正式实现准入”区分。基线/合同设计工作不必被一刀切禁止，但对应规则未冻结就不能实现验收。

## V422-B05 / P1 / 同日结构失效和新确认在最终状态之后才计算

**证据：** §77B（9330–9334）顺序为 PREWATCH → Multi-Axis State → Confirmation Event Engine → Structure/Support/Acceptance → Radar。§31.3（5847 起）又要求 STRUCTURE_DAMAGE / INVALIDATION_AST TRUE 当日立即 health=DAMAGED、validity=INVALIDATED；§10A0（3426–3433）也把 HARD_INVALIDATION 放在最高优先级。

**影响：** 若当日跌破旧 Anchor 的失效事实直到 Structure 步骤才生成，前面的状态已经算完；同日新确认也在 maturity 计算后产生。可能延迟一天失效，或暗中回跑形成未声明依赖。这里只能确认 producer/consumer 未闭合，不能断言生产代码已经出错。

**修复：** 把价格/结构/确认 detector facts 与最终状态/event projection 分开；对 t-1 冻结 Anchor 评估 t 的结构事实，在最终状态 reducer 之前提供；最终事件压缩在 reducer 之后。若 Base Seed 需要 structure_damage，须定义可前置的纯价格检测器或声明其输入时点。

**关闭条件：** 完整字段级 DAG；同日“满足确认且触发结构失效”与“跌破旧 Anchor”样例，最终状态遵守合同优先级且不依赖隐式二次执行。

## V422-B06 / P1 / 同日事件去重键没有解决修订撤销与前驱漂移

**证据：** §4.7 定义 prior_session_state_head 为“上一交易日最终 accepted”，未明确当日首次构建后如何冻结该前驱 revision；§45A 的统计事件键（7194–7198）没有 publication/revision，虽然日账本有 publication。§4.2 仍要求 revisions append-only。

**反例：** T r1 是 NEW_CONFIRMED，r2 数据修正后已不满足确认。相同 episode/event/date 的统计记录应保留原始 observed、在当前研究投影撤销，还是由 r2 覆盖？单一唯一键没有给出答案。另一个反例：T 已发布后，T-1 出现修订，T 的重放若读取后来“最终 accepted”会改变事件分类。

**关闭条件：** 逻辑 event id 与 event observation revision 分开；固定每个 publication 实际消费的前驱 id/digest；声明首次实时 enrollment、事后修正、撤销事件和 current head 的投影规则。既不重复计样本，也不删除/重写原始 Forward。Shadow→Production 的状态继承也应冻结切换前态，避免新 namespace 首日全部 FIRST_OBSERVED。

## V422-B07 / P1 / AS_RECORDED 查询条件不能单独证明系统当时实际读到了该版本

**证据：** §6A 保存 observed_at/available_at/ingested_at，但 AS_RECORDED 谓词（2283–2285）只有 effective 区间和 available_at<=cutoff，未定义 available_at 是供应商公开时间还是本系统可消费时间，也未给出同 key 多 revisions 在 cutoff 内的唯一选择和 publication 精确消费集合。

**影响：** 供应商在 T0 前发布、系统 T+10 才抓到的数据，若 available_at 用供应商时间，会被误纳入“当时系统实际知道”。两个 cutoff 内版本还可能重复参与聚合。

**关闭条件：** 分开 provider available time 与本系统 observed/ingested time；AS_RECORDED 以实际冻结 source snapshot/consumed revisions 为权威，并明确 tie-break/替代规则。允许历史 knowledge-time reconstruction，但不得称实际观察。分别验证迟到抓取、迟到更正、相同 effective range 多版本。

## V422-B08 / P1 / Forward 收益基准和板块样本身份仍没有闭合

**证据：** §46A 的 R_N 仅写 `Close_adj(T+N)/Close_adj(T0)-1`，没有规定必须将两端按统一 evaluation basis 重估并保存 identity；§41A0 同基准原则方向正确，但不能默认两个 daily snapshot 的 QFQ 值已相同坐标。§49A 只有 MARKET_BENCHMARK_V1 名字，没有具体序列、聚合/权重/再平衡/缺失规则。§45A 的键全部为 security_id，而 §45 明确纳入全部 WARM/CONFIRMED，系统也包含板块研究信号。

**影响：** 不同日快照的 QFQ 基准直接相除可能错误；板块收益可被不同聚合方式改变；板块 cohort 不知道用什么身份与价格路径结算。

**关闭条件：** Outcome 显式保存 evaluation adjustment basis、source revisions、T0 原值和比较用换基值；冻结真实 market benchmark contract，冻结板块成员、权重、目标股 LOO 是否适用及缺失成员政策。cohort 使用 entity_type/entity_id 或独立 stock/sector schema；若第一版仅做股票 Forward，明确缩小范围，不能称全对象闭环。

## V422-B09 / P1 / CLEAN_CONTROL 没有定义，可能重新引入未来选择偏差

**证据：** §49B（7342–7355）保留后来入选的原 assignment，这一步正确；但同时要求 ITT_CONTROL/CLEAN_CONTROL，未定义 CLEAN_CONTROL 的构造方式。

**影响：** 如果 CLEAN_CONTROL 表示事后剔除“未来变成 PREWATCH”的对照，就依据未来信息选择对照，可能夸大增量。冻结原 assignment 不能自动消除此报告层偏差。

**关闭条件：** ITT 作为主比较；CLEAN 明确是诊断敏感性分析还是预注册的时间依赖/截尾方法，披露后验选择与样本流失，不能替代 ITT 或直接用于通过效果门。为对照 T+3 入选的样例固定 T+5 的归属及处理。

## V422-B10 / P1 / Amount A 的 PROVISIONAL 标签尚未绑定正式消费权限

**证据：** §70A 继承 AUD-AMOUNT-A-06 OPEN，声明不得成为“正式强证据”，并写 `amount_a = PROVISIONAL_EVIDENCE`；§15/21A 仍把 amount_a 用于 Sector/Rotation，§52B 将其依赖能力标成 PROVISIONAL。

**影响：** “不是强证据”没有规定能否满足正式 Rule AST、参与 ranking、生成 Focus source。若只是换一个质量标签继续用于正式决策，独立审计保护没有落实。数值与质量状态也不应共用 amount_a 字段。

**关闭条件：** 拆为 amount_a_value/quality/contract_id；列出 OPEN 期间允许的诊断消费者及禁止的正式消费者，或明确批准的临时合同与独立样本身份。相关范围阻断不能扩散成所有 Stock Core 停止，但也不能靠 PROVISIONAL 标签绕过其正式资格门。

## 本次不作为新阻断的事项

- 不再把 BaoStock 当前接口可用性当作已证实失败；本次不重复接口 smoke test。方案中“用户已确认”属于文档记载，本轮没有独立验证吞吐、覆盖或全部字段，也不据此删除既有 bounded request、source contract 和降级要求。
- 20 日加最低 T5 样本数属于可选择的上线观察政策，不能当成算法正确性证明；样本不足则延期本身是设计选择，不是必然算法错误。
- 历史成员不可还原、历史复权不齐全可以按能力范围降级，不需要强求所有历史能力完整才能盘点基线。
- Anchor 换基与 S3 annotation 的新增条款不应推翻；需要的是全篇同步和后续数值验收。

## 推荐修订顺序

1. 先统一 §78、附录 B、§87A、§7.4、§4.6 与新增规范；删除过期规范而不是再加一层补丁。
2. 修正 MDD，前置 Forward settlement，并统一切换政策。
3. 补齐 detector→state→event 的 DAG、事件修订与前驱冻结。
4. 冻结完整算法 AST、AS_RECORDED 消费身份、benchmark/control 和 Amount A 权限后，再验收对应模块。

最终判断：V4.2.2 的修复方向是正确的，但仍存在确定公式错误、执行顺序矛盾和未填完的合同。可以继续合同设计和基线盘点，不应按当前文本直接签署全部算法与流程已可执行。

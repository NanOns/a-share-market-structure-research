# 全系统算法与业务逻辑复核及优化方案（2026-09-14）

**阶段合同**：`ALGO_LOGIC_REAUDIT_V1_0`。输入为 [原审计登记册](FULL_ALGORITHM_LOGIC_EXTERNAL_AUDIT_REGISTER_20260913.md)、[V3 当前主规格](WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md)（特别是 §4–8、§14、§18、§20–22）、[最新页面/数据整改记录](V3_UI_DATA_INTEGRATION_REMEDIATION_20260913.md)、当前工作区代码/配置及生产 DuckDB 的只读查询。本文是审计后的**新建议文档**，不改动原登记册、不执行重建或交易操作。TDX 源始终只读；本阶段仅在项目内写文档。项目当前工作区有未提交修改，以下“实现”均指 2026-09-14 审阅时的工作区状态，不预设其已发布。

**结论**：原登记册正确抓住了 V3 双轨缺历史、缺值三态和效果尚未验证的问题，但漏掉一个更直接的硬错误：板块“站上 MA20 宽度”比较了不同量纲，当前 553 个板块全部算成 0。原册也不完整且有过时计数。当前实现不能称为“最优”。已经可以直接确认的实现/合同偏差，应优先修复；阈值是否更好只能在冻结版本、真实跨日样本和同日基线下判断，不能凭一个下跌日的 3/531 或 0/531 调参。**本次文档审计接受结果：`DEGRADED_PASS`（静态代码和生产库只读事实核查完成，未做所有因子的独立逐笔复算）；V3 提前轨道的有效性及效果放行：`BLOCKED`。**

## 1. 审计证据、口径与原册修订

只读查询目标：`data/database/market_research.duckdb`、`data/normalized/adjusted_daily.parquet`，没有读写 TDX 根目录。以下是截至审计时的库内事实，不能替代新发布日的运行验收。

| 项目 | 本次只读结果 | 对原册的修订 |
|---|---:|---|
| 调整日线 | 19,641,332 行、8,785 日期，1990-12-19～2026-09-11 | 长历史是原始价格窗口，不等于历史板块结果或 PIT 成员存在。 |
| 成功 publication / COMPLETE research run | 各 1 个，均为 2026-09-11 | 只能证明单日当前运行。 |
| `sector_cycle_daily` / `mainline_daily` | 各仅 1 日期；前者 553 行，`breadth_ma20` **553/553 为 0** | 不能产出真实 3/5/10/20 日状态；MA20 宽度还存在独立量纲错误。553 与研究正常板块 531 为不同范围，不可混写。 |
| `research_sector_states` | 531 行；CURRENT 3、POTENTIAL 0；三项 `dq5_3/b_delta3/ma20_delta3` 均 531/531 为 IEEE NaN | `potential_eligible` 531 行目前全是 SQL `false`，**不是** SQL `NULL`；上游 MA20 宽度恒 0 是已证实的独立否决因素，另有历史缺失。不能把“0 个”归因于行情或仅归因于历史。 |
| `research_sector_signal_state` / `research_signal_outcomes` | 531 行 `NO_EPISODE`、`history_complete=false`；outcome 0 | 生命周期和效果均未获得真实跨日证据。 |
| V3 短名单 | CURRENT_FOCUS 9；EARLY_FOCUS 0 | 两轨不得用 V1 候选补位。 |
| V1 `candidate_daily` | **1,072 行、1,072 只股票，全部 `IN_CANDIDATE_POOL`** | 原册及页面整改记录的 1,071 已与当前库不符；应按 publication、合同、查询时点重算页面 total。 |
| `market_cycle_daily` | 物化行 0；`/api/market/cycle` 代码有技术切片即时聚合分支 | 原册“M13 有同日数据”可指 API 结果，不能据此声称 M13 表已物化。市场摘要和即时聚合须分开标来源。 |

原册“所有在用及兼容模块”仍漏列 V2 shadow 五条队列、V2.1 强回撤、`forward/live.py` 的前瞻状态机、Phase 0 调整/归一化、关系/发布身份、数据能力门等。下文按用户实际目标把它们纳入核查范围。代码存在不等于正在 V3 主界面使用；`FULL_PASS` 工程回执不等于科学效果通过。

## 2. 当前实现与算法合同的关键差异（按优先级）

| ID/级别 | 核对结果与证据 | 建议修改及原因 | 验收标准 |
|---|---|---|---|
| ALG-00 / P0 | [sector_cycle.py:371–375,413](../src/workbench_analysis/sector_cycle.py#L371) 把 `member_ret1`（收益率）与 `member_ma20`（价格）比较，形成 `breadth_ma20`。只读库 553/553 板块均为 0；同日 `technical_result_daily` 6,182 行中有 1,477 行 `adj_close>ma20`。V3 POTENTIAL 共用门要求宽度≥0.45，因而当前 0/531 有确定的上游硬错误。 | 在相同 `TDX_NATIVE_QFQ` 基准上比较成员 `adj_close>ma20`，只以收盘与 MA20 均有效且实际观察的成员为分母，记录有效数/总成员数/价格基准；重新物化新版本板块周期和其依赖结果。原因：收益率与价格量纲不同，当前宽度不代表任何市场事实。 | 人工 5 股样本手算宽度；真实 2026-09-11 重算后宽度不再全 0，逐板块与技术行聚合一致；依赖的 POTENTIAL/M10 旧结果不得原地改写，须新合同和新 run。 |
| ALG-01 / P0 | [research_builder.py:82](../src/workbench_service/research_builder.py#L82) 读 110 个日线会话，却只从 `sector_cycle_daily` 取至多 11 个已物化日期；[184–205 行](../src/workbench_service/research_builder.py#L184) 对物化序列做 `diff(3)`、将 `prior_current_within10=None` 固定写入、每板块只给 episode 一行。当前库恰只有一日周期。 | 建立**请求日 t 的受控历史依赖窗口**：按主日历取 t-10 及必要预热窗口，逐日重算 q5/q20、共同成员宽度与金额、CURRENT/W，再形成 t 的 dq5_3、ma20_delta3、曾 CURRENT、episode。只发布 t 的最终研究行及可审计的依赖摘要；用户要求单日保留时不擅自永久保存历史最终行。原因：这是提前轨道的输入缺口，不是阈值问题。历史成员若无时点证据，标 `RECONSTRUCTED_CURRENT_MEMBERSHIP` 作诊断；不得伪称 PIT 或正式效果样本。 | t-3 和前 10 日按交易日精确对齐；任一历史成员/报价缺失显式 UNKNOWN；同一 t 重算幂等；截断 t 后输入不能改变 t 结果；至少 5 个连续真实运行日验证跨日状态。 |
| ALG-02 / P0 | [research_builder.py:199–205](../src/workbench_service/research_builder.py#L199) 用布尔值 `.eq(True).rank(method='first')` 给**所有**板块排名。只读库 528 个未通过 CURRENT 的板块有 `current_rank`，真正 3 个合格板块为 529–531；POTENTIAL 全为 false 仍得到 1–531。 | 先过滤 `current is True` / `potential_eligible is True`，按规格 §5.1/§5.2 的特征排序及 `sector_id` 稳定兜底，再仅给合格者连续 1..N；非合格者排名 NULL。原因：布尔排名不表示强度，误导 API、页面及主关联排序。 | 生产 2026-09-11 的 3 个 CURRENT 排名恰为 1、2、3；528 个其余 NULL；全无 POTENTIAL 时所有 potential_rank NULL；并列与缺值顺序复算一致。 |
| ALG-03 / P0 | [research_builder.py:162–178](../src/workbench_service/research_builder.py#L162) 在统计覆盖率计算前已把未观察股票从 `current_quotes` 删除；[sector_attention.py:105–109](../src/workbench_analysis/sector_attention.py#L105) 的 `market_coverage` 只以传入行作分母。 | 在冻结的当日统计 A 股 universe 上保留每个成员一行，未知报价用 NULL；分母是应观察对象总数，分子是实际有效 ret1。板块成员覆盖率同理另列；输出两个 denominator、universe hash、排除规则。原因：先删缺行会把“数据少”误算为“覆盖高”，破坏全市场 90% 门。 | 注入 20% 缺报样本时全市场覆盖率为 80%，CURRENT 全榜不发布；BJ/科创等配置变更同步改变分母并生成新身份。 |
| ALG-04 / P0 | [research_builder.py:88–91,157](../src/workbench_service/research_builder.py#L88) 读 parquet 时未取已有 `price_basis`/`adjustment_status`，反而给所有 raw 行赋 `TDX_NATIVE_QFQ`；[research_features.py:126–134](../src/workbench_analysis/research_features.py#L126) 因而只校验这个人工常量。 | 从调整日线原字段读取并逐行核对复权身份、状态、实际 bar 与 cutoff；基准不符时信号 UNKNOWN，不能改写标签通过。原因：价格身份是 MA、RPS、新高及前瞻收益的共同硬前提，代码现可掩盖混基准输入。 | 注入 RAW/错误版本/缺少身份行均 fail closed；与 [正式调整合同](ADJUSTMENT_CONTRACT_V0_3.md) 的 `TDX_NATIVE_AFFINE_QFQ` 和原始金额口径一致。 |
| ALG-05 / P0 | [research_builder.py:218–219](../src/workbench_service/research_builder.py#L218) 对 `current is not None` 的板块标 `quality=READY`，当前 531/531 为 READY，但 3 日指标全 NaN、`history_complete=false`。`ResearchRunStore.complete` [104 行](../src/workbench_service/research_runs.py#L104) 将 NaN 直写数值列。 | 将“CURRENT 当日质量”“POTENTIAL 历史质量”“生命周期质量”分栏；进入 DB 前统一非有限数→SQL NULL，JSON `allow_nan=False`，API 展示 UNKNOWN/缺失原因，独立保留已知 false 的失败谓词。原因：不能让 READY 遮盖另一条轨道的未知，也不能混用 NaN/NULL。 | DB 数值列无 NaN/Inf；531 行中历史质量不再 READY；三值真值表、DB→API→UI 往返一致；已知 false 与证据不足可分别统计。 |
| ALG-06 / P0 | [research_builder.py:161–163](../src/workbench_service/research_builder.py#L161) 手工 `rank(pct=True)` 对所有日线行求 RPS；[strength.py:34–64](../src/workbench_analysis/strength.py#L34) 的正式强度合同只对 `IN_NORMAL_UNIVERSE` 且样本数≥100 排名。 | P05 直接复用已封存的同日 strength 结果，或复用相同可执行函数、相同 universe/缺失门，并绑定其 slice/合同/样本数。原因：同名 RPS 不同分母会改变 SETUP、RECOVERY、趋势背景和潜在板块。 | 抽取多个边界日期/股票逐项比对 P05 的 RPS5/20 与 strength 输出完全一致；停牌/新股/非正常 universe/样本不足为 UNKNOWN。 |
| ALG-07 / P0 | 配置中 `max_rank_universe_change`、`min_rank_intersection_union`、`min_common_member_coverage`、`liquidity20_amount_gte`、`prior_current_lookback_sessions`、`monitoring_max_sessions` 在 `src/` 无引用；[research_builder.py:28–56](../src/workbench_service/research_builder.py#L28) 将 0.70 写死，[research_features.py:209](../src/workbench_analysis/research_features.py#L209) 将 2,000 万写死。构建器读取配置后未调用 [validate_contract_bundle](../src/workbench_service/research_v3_contracts.py#L275)。 | 把所有决定资格的参数接到实际执行路径，逐项测试“改参数会改结果/身份”；未实现的参数从生效合同移到“预留”并禁止误读；运行前验证 canonical `parameter_hash`。原因：当前版本化配置并未完整控制算法，审计无法重放参数含义。 | 配置字段使用覆盖表 100%；任一生效字段变化产生新 hash/run；手改值但不改 hash 被拒绝；固定阈值只存在于版本化函数合同内。 |
| ALG-08 / P1 | [sector_attention.py:477–482](../src/workbench_analysis/sector_attention.py#L477) 在返回角色前将每板块 CURRENT_RESEARCH/EARLY_WATCH 截为 5；[research_builder.py:210–214](../src/workbench_service/research_builder.py#L210) 再把截断结果送全局关联/短名单。 | 资格计算保留**全部**合格成员；只在板块卡/API 预览层取前 5。先全量去重、LOO 与每板块 3/每清单 20 限额，再分页。原因：展示上限不应改变研究资格，多个板块共享股票时可能漏掉后续合格者。 | 单板块有 8 合格者、前 5 关联重复时，全局清单能考虑第 6–8 人；板块角色总数与预览数分别正确。 |
| ALG-09 / P1 | [research_association.py:112–140](../src/workbench_service/research_association.py#L112) 生成 `waiting_for` 的规则可让已进入 CURRENT 的股票仍显示“等待 BREAKOUT 或 RECOVERY”；`setup` 局部变量未参与决策，`previous_state=None`、`NEW_SELECTION` 恒定。`research_shortlist` 无封存的 `signal_date` 列。 | 以真实当前信号和轨道状态生成等待/失效条件；跨日关联 previous_state、首次日期、PAUSED/移出原因；信号日随 run 封存，API 不用当前上下文伪造旧信号日。原因：清单必须解释“为什么今天在、下一步等什么”，不能给已满足条件的等待语。 | BREAKOUT/RECOVERY/SETUP 各有正反例；连续两日状态可追溯；同一个旧 run 的说明在未来构建后字节不变。 |
| ALG-10 / P1 | `research_runs` 的 [input_key](../src/workbench_service/research_runs.py#L28) 绑定 publication/snapshot/membership/算法版本/参数 hash，却未绑定调整日线内容 digest、实际历史窗口、成员 as-of 证据；[research_builder.py:73–78](../src/workbench_service/research_builder.py#L73) 从项目 parquet 直接读取。 | run 依赖声明加入调整日线工件 hash、日期范围、strength/sector amount 切片、历史成员来源、代码合同版本及质量摘要；相同输入才复用 COMPLETE。原因：同名文件被重建后不能静默复用旧结果。 | 变更任一实质依赖会生成新 run 或被明确拒绝；相同依赖重放结果和行 hash 一致；快照身份本身不被改写。 |
| ALG-11 / P1 | 现有直接热榜 API [online_hot_rank.py:326–378](../src/workbench_service/online_hot_rank.py#L326) 为请求时直读；但 [collector.py:64–169](../src/workbench_online/collector.py#L64) 和 `scripts/run_m14_02_*capture.py` 仍可将热榜原始 payload 与 batch 写盘。 | 将旧采集入口关闭、删除可达命令入口或增加一律拒绝的显式门，并登记历史遗留文件的只读清点/隔离决策。原因：AGENTS.md 的 M14 热榜合同禁止 raw/row/batch/history 持久化；“当前 API 不写”不等于仓库所有可执行路径均安全。清理历史文件需另立范围与验收，不在本次文档审计中执行。 | 对所有热榜入口做调用图与写路径检查；直接模式请求前后目录/DB 无热榜持久化增量；旧脚本调用返回明确禁用状态。 |
| ALG-12 / P1 | `b_delta3` 依赖 t-3 `publication_memberships`，[research_builder.py:120–133](../src/workbench_service/research_builder.py#L120) 在缺此前 publication 时给空成员；`ma20_delta3` 对历史 `sector_cycle_daily` 直接 `diff(3)`，未按合同固定共同成员集；q5 变化未执行配置中的横截面稳定性门。 | 历史比较统一为日期对齐的“同一可比较成员”与可审计覆盖；q5 分母/交并比不足时 UNKNOWN；MA20 宽度 t/t-3 在同一成员交集与两日有效窗口上计算；仅有当前成员时标重构诊断。原因：成员变化和股票池变化可伪造“扩散/改善”。 | 人工构造大规模成员替换、缺 t-3 publication、停牌缺值、横截面变化>10% 样本均不产生正式改善；金额 A 保持独立正式合同。 |
| ALG-13 / P0 | [sector_cycle.py:382–387](../src/workbench_analysis/sector_cycle.py#L382) 在成员 `rs5` 缺失时回退 `ret5`，随后生成 q5；但 V3 主规格 §4 明确“RS5 缺失但 RET5 有值时，q5 必要输入未知”，并禁止 RS 缺失回退 RET。 | 删除同名 q5 的回退；若要研究“5 日收益分位”，另设字段和版本合同，不能冒名 RS5。原因：RS 是相对市场的量，RET 是绝对收益，二者在普涨/普跌日排序含义不同。 | 缺 RS5、有 RET5 的样本 q5 为 UNKNOWN；RS5 完整时 q5 与正式 strength 及同类板块平均秩/N 一致。 |

**审计解释**：当前宽度 0 使 MA20 门已知失败，足以令三分支 false；另有历史字段未知。`potential_eligible=false` 在三值硬门下可以由已知不合格条件决定。因此修复 ALG-00/01/05 后，应提供每个板块“已知失败谓词 / 未知谓词 / 可评估分支”分布，不能机械地把全部 531 行改成 UNKNOWN，也不能在证据不足时发布“全市场没有潜在对象”。

## 2A. 修改后的 V3 核心算法合同（建议稿，尚未实施）

建议新合同标识 `RESEARCH_V3_CORRECTNESS_DRAFT_20260914`。此节替代**计算路径和解释语义**，暂不改动 [现行阈值表](../config/research_attention_v3.yaml) 的数值。它在 R1/R2 验收并形成正式版本号前不能用于正式发布或覆盖既有 `RESEARCH_V3_PREVIEW_3` 结果。

| 步骤 | 修订后的明确规则 | 缺证据/边界 |
|---|---|---|
| 0. 身份冻结 | 以 `(publication_id, trade_date, snapshot_id, membership_asof_id, adjusted_daily_digest, strength_slice_id, sector_amount_slice_id, config_hash, code_contract)` 定义 run 输入身份；`source_date<=trade_date`。价格 `C`、MA 均为同一 TDX-native QFQ，成交额和报价涨幅按 RAW 合同。 | 任一价格/成员/日期身份冲突拒绝构建；旧快照身份不改写。 |
| 1. 市场报价 | 冻结当日统计 A 股全集 `U_t`；`market_quote_coverage = 有效、实际观察 ret1 数 / |U_t|`，`market_m1 = median(有效 ret1)`。不先丢缺报行；每板块成员集单独记录 `n` 和报价有效数。 | 覆盖<0.90 时 CURRENT 全榜 UNKNOWN；板块覆盖<0.70 或 n<5 时其资格不得为 true。 |
| 2. 股票基础 | 在主交易日历上计算 QFQ MA、前 20 日最高收盘、20 日原始金额中位/均值、波动、RPS5/20；RS/RPS只在正式正常 universe 内产生，样本<100 为 UNKNOWN。BREAKOUT/SETUP/RECOVERY/风险沿现行阈值逐谓词三态判定。 | 停牌/合成填充不当真实 bar；`ret1` 的 RAW 前收与 QFQ 趋势价格分开标；关键字段 UNKNOWN 不补零。 |
| 3. 板块当日特征 | 对 as-of 成员计算 `m1=median(ret1)`、`b1=#(ret1>0)/#有效ret1`、`rel1=m1-market_m1`。**`ma20_width=#(C_adj>MA20_adj)/#(C_adj 与 MA20_adj 同时有效)`**；记 `ma20_valid_count/n`。`q5/q20` 是同类型正常板块的成员 RS 中位的平均秩/N，不以 RET 替代 RS。 | 成员有效数/覆盖不足为 UNKNOWN；`top1_positive_share=max(ret1_i^+)/sum(ret1_i^+)` 只说明上涨贡献集中，不叫资金集中。 |
| 4. 跨日特征 | `dq5_3=q5[t]-q5[t-3]`，同时校验同类有效排名总体数量变化≤10%、交并比≥0.90。`J=U_t∩U_{t-3}`，且只取两日 ret1、QFQ C/MA20 同时有效的成员；`b_delta3=mean_J(ret1_t>0)-mean_J(ret1_t-3>0)`；`ma20_delta3=mean_J(C_t>MA20_t)-mean_J(C_t-3>MA20_t-3)`。`|J有效|>=5` 且相对两日目标成员最大数覆盖≥0.70。 | t-3 必须是主日历第三个先前交易日，不能拿第三条现有记录替代；成员 as-of 不可证时仅输出重构诊断；`prior_current_within10` 只从此前已封存、同合同、日期相连的 CURRENT 事实导出。 |
| 5. CURRENT 与 W | CURRENT 保持现行 n≥5、报价覆盖≥0.70、全市场覆盖≥0.90、同类型横截面覆盖≥0.70，以及 `m1>0,b1≥0.60,rel1≥0.003,p1≥0.80,positive_count≥3,top1_positive_share≤0.50` 全部成立。W 仍为 `(m1<0 且 b1<0.35)` 或 `(m1<0 且 b_delta3≤-0.20)`，独立于 CURRENT。 | 三值逻辑：任一已知必要 false→false；无 false 且有未知→UNKNOWN；全 true→true。CURRENT 排名只对 true 板块按 `(p1↓,b1↓,rel1↓,amount_A↓,sector_id↑)` 连续编号。 |
| 6. POTENTIAL | 在非 CURRENT、非 W、正常板块、n≥5、`m1≥-0.01,ma20_width≥0.45,risk_coverage≥0.70,extended_share≤0.50` 的共同门之后，保持现行扩散/蓄势/回暖三分支数值阈值；金额只接受 `SECTOR_AMOUNT_COMMON_AGG_V1` 的正式 A。同日多分支均保留，主分支优先级回暖→扩散→蓄势。 | 历史比较、金额或风险证据缺失分别显示未知谓词；POTENTIAL 排名只对 true 板块按 `(命中分支数↓,dq5_3↓,ma20_delta3↓,early_width↓,amount_A↓,sector_id↑)` 编号；非 true 排名 NULL。 |
| 7. 生命周期/成员/清单 | 对每板块连续交易日序列推进 episode，首次潜在日冻结 first_seen/branch/成员证据；CURRENT 才确认，W/结构失效作无效，缺日作 DATA_GAP。对**全量**合格角色做 LOO、主备关联和双清单，每板块 3/每清单 20 的限额在资格后执行；板块卡预览最后取 5。 | 旧日期信号说明不可被未来改写。`waiting_for` 从实际未满足条件生成；`previous_state`、PAUSED/移出原因和 `signal_date` 真实封存。当前缺历史时生命周期为 PARTIAL，不伪造首次或确认。 |

该修订的目标是恢复**可计算、可解释、可复现**，并不预设修复后 POTENTIAL 一定不为 0；只有重算后的门槛失败分布和后续真实效果才能判断规则是否值得进一步优化。

## 3. 算法域全量核对与建议

状态标记：`A`=代码路径和主要合同对齐（未证明效果最优）；`D`=已确认偏差；`H`=历史/数据缺口；`E`=仅有工程能力、效果待证；`R`=旧兼容/影子路径，须隔离语义。表中“保留”表示不建议在本轮无证据地改阈值。

| 域与代码 / 版本 | 本次判定 | 修改或优化理由与方向 |
|---|---|---|
| Phase 0 只读接入、交易日历、QFQ：`tdx/*`、`market_calendar/*`、`adjustment/*`；`adjustment-contract-v0.3` | A | Phase 0 `FULL_PASS` 是既有放行前提，不在此重新证明。保持本地 TDX+GBBQ、原始额/量、未来除权排除；新增 V3 输入行身份核对（ALG-04），避免下游绕过。 |
| 归一化/正常 universe：`normalize/*`、`universe.py` | A/D | 显示范围与统计范围分开正确；V3 全市场覆盖分母、RPS 分母必须复用此合同（ALG-03/06）。 |
| 快照/发布/关系：`production/*`、`source_freezer.py`、`membership_resolver.py`、`relation_repository.py` | A/H | 保留只读 TDX、原子输出、revision 身份；加入 run 对内容和 as-of 关系的完整依赖；历史成员缺时不得拿当前关系当 PIT。 |
| Phase 1 因子：`factors/registry.py`、`engine.py`，`factor-contract-v1.0` | A/E | 保留 RET/MA/RS/量额/波动等明确公式；单独抽样复算调整价、窗口完整性、停牌/零分母。不要将 V1 因子分位自动解释为 V3 RPS。 |
| Phase 2 市场/合成板块：`sector/phase2.py`，`sector-factor-contract-v1.1-correctness` | A/H | 当前成员快照可解释今日结构；历史效果仍需 PIT/重构标签。成员去重、同类排名和质量分母列为回归样本。 |
| Phase 3/4 扫描：`scanner/sector_scanner.py`、`stock_scanner.py`，各自 v1 合同 | A/E | 旧结构硬规则继续独立运行；只作研究候选，不把 V1 扫描命中当 V3 CURRENT/POTENTIAL。对小板块、单股贡献、风格偏置做失败原因分布。 |
| Phase 5 V1 候选/优先级：`candidates/research_priority.py`，v1.1 | A/E | 1,072 当前库候选与 V3 9/0 分轨显示；分数仅排序。建立按 publication 的 total 对账，避免页面/文档旧计数。 |
| M8 技术/RPS/新高/图表/结构：`technical.py`、`strength.py`、`highs.py`、`chart.py`、`structures.py` | A/D | 技术报价收益用 RAW 前收、趋势用 QFQ 价本身合理，但页面必须标价格基准。V3 手算 RPS 和正式 strength 不同（ALG-06）；高点明确是收盘还是最高价，结构类别重叠给出证据。 |
| 历史适配与板块周期：`history_adapter.py`、`sector_cycle.py`、`member_state.py`、`representative_state.py` | D/H | `history_adapter.py` 明确拒绝当前成员的历史回填，这是正确安全门；但板块周期 MA20 宽度比较收益率与价格，RS5 缺失回退 RET5，且当前库仅 1 日。先修 ALG-00/13，再以真正 as-of 成员逐日构建；没有时点关系则只给 RECONSTRUCTED 诊断。历史代表股不能冒充当日领涨。 |
| M10 成交额 A / 中期主线：`sector_amount.py`、`mainline.py` | H/E | A 必须按正式共同成员金额合同，不能用成员量比中位代替；只一日时主线状态 DATA_INSUFFICIENT。金额单位、同成员交集、20 日窗口、覆盖与真实日延续分别作为独立审计项。 |
| M13 市场周期：`market_cycle.py`、`app.py::market_cycle` | A/H | 当前 API 有技术切片即时聚合支路，而表无物化行。市场总览的 API30 缺值和 M13 动态结果应按同 publication/snapshot 显式绑定，并标“即时聚合”来源，避免跨快照混搭。 |
| V3 个股特征/信号：`research_features.py`、`stock_attention.py` | D/E | 三值谓词结构和价格/金额窗口大体符合主规格；修复价基准、RPS、配置生效性后逐谓词手算。`BREAKOUT/SETUP/RECOVERY` 是研究标签，不是收益预测。 |
| V3 CURRENT/W/POTENTIAL：`sector_attention.py` | D/H | CURRENT 当日门与规格接近，但全市场覆盖分母需修；POTENTIAL 三分支的上游 MA20 宽度全错且历史缺失。先修算子、再补历史证据、最后做阈值敏感性；3/531 不能单独说明门过严。 |
| V3 生命周期/角色/关联/短名单：`sector_attention.py`、`research_association.py`、`research_builder.py` | D/H | 单行 episode、角色前置截断、错误布尔排名、状态/等待语恒定均需修复（ALG-01/02/08/09）。LOO 为支持强弱证据，不是板块上涨原因。 |
| V2 影子五队列及 V2.1 强回撤：`shadow_v2/*`、`shadow_v21/pullback.py`、`queue_ranking.py` | R/E | 原册漏项。维持 shadow/研究对比身份，分别冻结版本与 V1 baseline；不得把旧队列回填 V3 提前轨道。若页面继续展示，显式标“兼容/影子”，并审计重复候选、同股多队列与优先级稳定性。 |
| 旧本地涨停/梯队/晋级：`limit_rules.py`、`limit_ladder.py`、`limit_promotion.py` | R | 只在旧兼容域保留；V3 在线涨停使用来源自身事件字段，不可静默回退本地估算。按用户 V3 去留裁决核对 API/页面引用。 |
| 在线事件/热榜/报价/龙虎榜：`workbench_online/*`、`online_*`、`p09_products.py` | A/D/E | P09 工程验收可保留；当前可用性按来源/数据集单独判。热榜旧可写 collector 是边界缺口（ALG-11）。在线金额“流通市值×换手率”标估算，不当正式成交额 A，也不进入本地信号。 |
| 前瞻观察与评估：`forward/live.py`、`forward/observation.py`、`forward/evaluation.py`、`research_signal_evaluation.py` | E/H | 原册漏了前瞻状态/到期绑定。V3 当前 outcome=0，P10-03 仍是 `EFFECT_OBSERVATION_PENDING`；按信号日冻结成员和原因，t+3/t+5 与三组同日基线比较，按日期/重叠板块聚类报告不确定性，不许概率或收益保证。 |

## 4. 参数“最优”如何判断：先修正确性，再做有限对照

1. **第一层，正确性门**：ALG-00～07、10、12、13 完成前不讨论最佳阈值；每个因子/扫描器写出版本、输入、公式、缺值逻辑、排序、反例、run 绑定和人工手算样本。CURRENT、POTENTIAL、V1 结构分开验收。
2. **第二层，分布与敏感性**：对 CURRENT 的 m1/b1/rel1/p1/贡献集中门，对 POTENTIAL 的 dq5_3/b_delta3/MA 宽度/金额 A/风险门，逐门记录 2026-09-11 失败和 UNKNOWN 计数；按行业、概念、风格、成员数与市场涨跌分层。一次只变一个阈值并比较名单重合、日换手、成员宽度、数据缺失，不以“凑够 6 个板块/20 只股票”为目标。
3. **第三层，真实前瞻**：冻结候选版本，在后续真实交易日与规格 §14 的三个简单基线比较。至少 20 个不同信号日、50 个独立 episode 是**最低报告门**，仍要给重叠板块/同日相关性和覆盖缺口；样本不足保持 `EFFECT_OBSERVATION_PENDING`。比较 t+3/t+5 CURRENT 确认、固定 t 成员复权收益中位、失效率、提前天数、名单稳定性；这不是可交易收益或概率。
4. **第四层，参数更改**：只有当对照显示稳定改进且未明显恶化缺失率/解释性时，才发布新算法与参数版本，保留旧版 run、失败样本和回滚路径。未知参数不从 9 月 11 日单日“经验优化”。

可探索但**暂不作为已验证改法**：小板块采用更严格的共同成员/单股集中门；POTENTIAL 的行业/概念/风格分别校准分位；排名优先采用可比宽度改善而非单日上涨；对高重叠概念在 UI 归组，算法仍保留原始真实关系。每项都需上述对照与新合同版本，不能直接替换当前阈值。

## 5. 独立审计项、阶段顺序与验收

| 独立项 | 范围、证据与不并入当前门的原因 | 关闭条件 |
|---|---|---|
| `AUD-MA20-00` | 板块 MA20 宽度量纲错误、受影响的 POTENTIAL/M10/页面历史；对应 ALG-00。比历史缺口更前置的确定性阻断项。 | 源技术行手算一致、同日 553 板块重算不再全 0、所有依赖对象新版本构建且旧 run 保留。 |
| `AUD-HIST-01` | P05–P07 历史派生、PIT 成员、CURRENT 10 日回看和 episode；对应 ALG-01/12。影响提前轨道有效性，是阻断项。 | 真实连续日、日期切断、三值、状态转移、重构/PIT 标识和单日保存边界全部对账。 |
| `AUD-COV-02` | 全市场/成员报价分母、RPS 分母、横截面变化与 RS5 回退；对应 ALG-03/06/07/13。 | 分母和排除数入证据，缺报注入不产生虚假 READY，P05 与 strength 同值，RS 缺值不回退 RET。 |
| `AUD-RANK-03` | 布尔排名及全量资格与展示限额；对应 ALG-02/08/09。 | 当前 3 个排名 1–3、非资格 NULL；多板块重复/第 6 候选反例通过。 |
| `AUD-PRICE-04` | 调整价身份、版本、真实 bar、配置 hash；对应 ALG-04/07/10。 | 修改输入身份或参数时 fail closed/新 run；旧 run 保持不可变。 |
| `AUD-NULL-05` | NaN→NULL、三态、轨道分别质量；对应 ALG-05。 | DB/API/UI/理由表一致，补历史前不把 POTENTIAL 的缺证据显示为完整结论。 |
| `AUD-AMOUNT-A-06` | 跨域金额 A 专项（V3、M10、V1/V2 及在线估算均涉及）。与阶段门独立，不能只靠测试通过关闭。 | 独立金额单位/共同成员/20 日分母/覆盖/单股支配样本与跨域引用表，保留审计回执。 |
| `AUD-HOT-07` | 直接模式与旧 collector 的全仓可写路径；对应 ALG-11。 | 旧持久化入口不可达，直接模式无 raw/row/batch/history 新写；历史文件处理另行单独裁决。 |
| `AUD-MKT-08` | API30 摘要 vs M13 技术切片动态市场周期与首页来源标注。 | 同 publication/snapshot/date 绑定、缺表/缺切片显式降级，UI 不混称物化。 |
| `AUD-EFFECT-09` | P10-03 与 V1/V2 前瞻观察分别评价。 | 达最小样本门并提供同日基线、覆盖、相关性与失败样本；不能由工程 `FULL_PASS` 自动关闭。 |

**建议实施顺序**：`R0` 先冻结现库及规格/原册 hash、逐项复算当前只读事实；`R1` **先修 MA20 宽度与 RS5 回退**，再修输入身份、分母、RPS、配置 hash、NaN 和排名，生成新版本合同；`R2` 建受控历史依赖窗口与成员证据、修 episode/短名单，并验证 5 个连续真实日；`R3` 独立关闭金额 A、热榜旧入口、市场摘要等跨域项；`R4` 冻结参数开展真实前瞻效果观察。每阶段执行前重读当时最新适用升级文档，记录**阶段合同→输入/代码/运行证据→接受结果（FULL_PASS/DEGRADED_PASS/BLOCKED）→下一阶段**。测试只是证据之一，不自动代表发布就绪。

**本阶段证据与接受**：只读 SQL 核对了上述库行数、日期、NaN、排名、状态与 outcome；逐源核对了关键 V3、V1/V2、在线、前瞻的函数及配置引用。未运行新的生产构建、未写数据库、未改 TDX，也未对全部历史日线及每个因子做独立手算。因此本文件可作为整改合同和外部复核底稿，不能称“所有算法已证明最优”。**下一阶段**：优先立项 `R1-FACTOR_AND_INPUT_CORRECTNESS`，同时保持 `AUD-MA20-00`、`AUD-HIST-01`、`AUD-AMOUNT-A-06` 等独立跟踪；在 R1/R2 通过前，V3 提前轨道维持 `BLOCKED`，CURRENT 只能按当日规则作为预览事实使用。

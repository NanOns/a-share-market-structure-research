# 全系统算法与业务逻辑外部审计清单（2026-09-13）

状态：**待外部审计；不是效果验收报告**。本文件按当前仓库代码、配置和 2026-09-11 发布快照登记决策逻辑；旧版兼容算法也列入，不能因为 V3 不展示就视为不存在。外部审计应以代码、版本合同、输入快照和重算结果为准，不以页面截图或单元测试代替。TDX 源目录只读。

## 1. 输入与快照事实

| 对象 | 观察结果 | 审计含义 |
|---|---|---|
| 本地调整日线 `data/normalized/adjusted_daily.parquet` | 8,785 个日期，1990-12-19～2026-09-11 | 通达信源确有较长日线历史；这不是所有派生域已按历史逐日生成的证据。 |
| `sector_cycle_daily` | 仅 2026-09-11 一个交易日 | V3 板块 3 日变化、历史状态、10 日曾为强势无法直接从该派生表取得。 |
| `research_runs` | 完整运行 1 次，交易日 2026-09-11 | V3 信号生命周期仅保存一天，不能验证持续/转强。 |
| `research_sector_states` | 531 板块，CURRENT=3，POTENTIAL=0 | 空的提前观察不是“TDX 没历史”，而是当前构建链缺少必需的板块历史派生证据。 |
| `research_shortlist` | CURRENT_FOCUS=9，EARLY_FOCUS=0 | 个股清单是板块资格、成员角色与关联筛选后的派生结果，不是全市场直接筛选。 |
| `dq5_3/b_delta3/ma20_delta3` | 531 行均写入 NaN，而非 SQL NULL | 必须审计数值缺失的存储/JSON/判定一致性；不得把 NaN 当有效数。 |
| V1 `candidate_daily` | 1,071 个结构候选 | 与 V3 两个短名单不同合同；首页已恢复其前 20 名独立展示。 |

## 2. V3 双轨：准确算法链与当前缺口

1. `research_builder.py::build_latest_research_run` 从调整日线读取最近 **110** 个交易日，供个股技术和 P05 信号计算；不是只读取一天。它却从当前 `sector_cycle_daily` 读取板块周期，并在该表上做 `q5.diff(3)`、`ma20_width.diff(3)`。该表只有一天，所以两个变化量均为 NaN。
2. 同一构建器需要上一个对比日成员快照；若没有，则 `prior_members` 为空，`b_delta3` 无法形成。当前 531 个板块均是 NaN。构建器还把 `prior_current_within10=None` 固定写入，令“回暖”分支缺失历史资格；`progress_potential_episode` 每个板块只传入一行，无法形成真实多日生命周期。这是**实现缺口**，不是仅仅“生成一天”的自然现象。
3. CURRENT（`sector_attention.py::build_sector_current`，`SECTOR_CURRENT_PREVIEW_1`）：板块须为正常属性、成员≥5、报价覆盖≥70%、全市场报价覆盖≥90%、同类型有效横截面覆盖≥70%；当日成员涨幅中位数 M1>0、上涨宽度 B1≥60%、相对全市场中位数 REL1≥0.3%、同类型相对强度百分位 P1≥80%、上涨成员≥3、最大单股正收益贡献≤50%。任一硬门不通过或必需证据未知，不能成为 CURRENT。9 月 11 日全市场下跌 4,856、上涨 639，只有 3 个板块通过，**单就 CURRENT 数量而言并不能证明算法错误**；仍须做阈值敏感性和行业/概念/风格分层审计。
4. POTENTIAL（`build_sector_potential`，`SECTOR_POTENTIAL_PREVIEW_1`）：须非 CURRENT、非弱势、M1≥-1%、站上 MA20 成员宽度≥45%、风险覆盖≥70%、过度延伸成员≤50%；再满足“扩散、蓄势、回暖”三个分支任一个。扩散要求 `dq5_3≥0.10`、`b_delta3≥0.10`、`ma20_delta3≥0.05`、早期宽度≥10%、早期成员≥2、板块共同成员额比≥1.05；蓄势要求 Q20≥40%、MA20 宽度≥55%、3 日宽度变化非负、足够 SETUP、额比 0.8～1.3、`b_delta3≥0`；回暖要求 10 日内曾 CURRENT、REL1>0、`b_delta3≥0.10`、MA20 宽度不下降、额比≥1.05、SETUP/RECOVERY≥2。当前关键变化量全部 NaN，回暖历史资格恒为未知，0 个 POTENTIAL **不能解释为全市场无提前机会**。
5. 个股信号（`stock_attention.py` + `research_features.py`，`STOCK_ATTENTION_PREVIEW_1`）：BREAKOUT、SETUP、RECOVERY、趋势背景、结构破坏和过度延伸风险按 `config/research_attention_v3.yaml` 硬阈值计算。缺值为未知，不得视为假或补零；算法依赖 20 日流动性、位置、RPS 变化与日线完整性。
6. 成员角色（`build_sector_member_roles`，`SECTOR_MEMBER_ROLES_PREVIEW_1`）：TODAY_LEADER 为板块内当日正收益且分位≥80%；CURRENT_RESEARCH 仅来自 CURRENT 且 BREAKOUT/RECOVERY 为真；EARLY_WATCH 仅来自 POTENTIAL 且 SETUP/RECOVERY 为真。后二者还需无结构破坏、位置字段齐全、不过度延伸。每板块角色预览上限 5，不代表全部成员。
7. 个股关联与短名单（`research_association.py`，`RESEARCH_ASSOCIATION_PREVIEW_1`/`RESEARCH_SHORTLIST_PREVIEW_1`）：每股主板块 1、备选 2，按轨道、剔除该股后的共同支持、角色排名和板块排名排序。CURRENT_FOCUS 只能来自 CURRENT_RESEARCH，EARLY_FOCUS 只能来自 EARLY_WATCH；每板块最多 3 股、每清单最多 20、首页默认 10，同股优先列入 CURRENT。缺潜在板块必然导致 EARLY_FOCUS=0；V1 候选 1,071 股不会自动回填。

## 3. 所有在用及兼容的计算/判定模块

下表“审计重点”是应验证的问题，不表示已证实错误。每项均须记录输入范围、合同版本、公式/阈值、缺失值语义、输出样本、跨日复算和反例。

| 领域 | 模块 / 版本或合同 | 决策逻辑与输入 | 外部审计重点 |
|---|---|---|---|
| 源接入 | `production/daily.py`、`production/workbench.py`、`source_freezer.py` | TDX 文件、代码/板块关系、日期与发布身份归一化 | 源文件只读、未来数据、同日重复与失败原子性 |
| 范围 | `universe.py`、`semantic.py`、`membership_resolver.py` | A 股统计/展示范围、板块正常属性/风格/市场标签、版本化成员 | BJ/科创板、父子板块重复、语义分类 |
| 层级 | `hierarchy.py` / `TDX_SECTOR_HIERARCHY_V1_1` | 本地板块父子节点与有效关系 | 父子循环、成员继承/重复、版本日期 |
| 历史板块基础 | `history_adapter.py` / `HISTORICAL_SECTOR_ADAPTER_V1_0` | 历史行情与当前/历史成员适配 | 现存历史成员能否做时点回测，禁止以当前成员冒充历史成员 |
| 因子 | `factors/registry.py`、`engine.py` / `factor-contract-v1.0` | RET、RS、MA、量额、波动、趋势、区间位置等滚动因子 | 复权、窗口完整性、零分母、停牌填充 |
| 股票技术 | `technical.py` / `TECHNICAL_HISTORY_V2_1_PREVIEW` | MA5/10/20/60、RET、量额比、均线排列与质量码 | 容错与窗口口径、技术诊断缩窄门槛 |
| RPS | `strength.py` / 横截面强度合同 | 同日有效股票分位与样本量 | 历史可比股票池、缺失/停牌、分母变化 |
| 新高 | `highs.py` / `TECHNICAL_HISTORY_V2_1_PREVIEW` | 20/30/60/100 日高点 | 复权序列、收盘/最高价口径、停牌 |
| K 线 | `chart.py` / `TECHNICAL_CHART_V2_1_PREVIEW` | 技术展示点列 | 展示/计算价格基准一致性 |
| 五类结构 | `structures.py` / `HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED` | 历史结构分类与摘要 | 重叠类别、时点有效性、证据可读性 |
| 股票扫描 | `scanner/stock_scanner.py` / `stock-scanner-ruleset-v1.0` | 多种结构硬规则与质量门 | 规则漏报/误报、阈值稳健性、V1 优先名单 |
| 板块扫描 | `scanner/sector_scanner.py` / `sector-scanner-ruleset-v1.2-evidence-binding` | 板块强度/统计有效性/证据绑定 | 小板块、单股驱动、父子重复 |
| V1 候选排序 | `candidates/research_priority.py` / `research-priority-ruleset-v1.1-correctness` | 结构候选排序分数、A+/A/B/C | 分数仅研究排序，非概率/收益；多风格偏置 |
| 板块成交额 | `sector_amount.py` / `SECTOR_AMOUNT_COMMON_AGG_V1` | 共同成员总额比、覆盖度 | 金额单位、成员集合变化、单股支配 |
| 板块周期 | `sector_cycle.py` / `SECTOR_CYCLE_V1_3_M9_STATE_METRICS` | RS5/20、宽度、额比、扩散/收缩和历史排名 | 当前仅 1 个派生日期；需重建时间序列后复核 |
| 强成员留存 | `member_state.py` / `SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC` | 板块强成员进出及留存 | “诊断参考”不得当强成员、基期成员变化 |
| 历史代表股 | `representative_state.py` / `SECTOR_REPRESENTATIVE_STATE_V1_0` | 候选/确认/更替状态 | 不能当今日领涨，时序不得前视 |
| 中期主线 | `mainline.py` / `MAINLINE_STATE_V2_4_PREVIEW` | 3/5/10/20 日状态：新晋、持续、再加速、高位收缩、退潮等 | 仅 1 日应 DATA_INSUFFICIENT；阈值、宽度/成交额跨日稳定性 |
| 市场周期 | `market_cycle.py` / `M13_MARKET_CYCLE_V1` | 全市场涨跌、均线覆盖、新高、额与队列 | 统计范围、有效报价分母、API30 摘要缺失 |
| V3 个股特征 | `research_features.py` / `RESEARCH_FEATURES_PREVIEW_1` | 本地 110 日形成 P05 输入 | 源日历、复权、日线可用与派生缺口分离 |
| V3 个股信号 | `stock_attention.py` / `STOCK_ATTENTION_PREVIEW_1` | BREAKOUT/SETUP/RECOVERY/风险 | 每个谓词手算和缺值三态 |
| V3 当前板块 | `sector_attention.py::build_sector_current` / `SECTOR_CURRENT_PREVIEW_1` | 当日 M1/B1/REL1/P1/覆盖/正收益贡献 | 9 月 11 日下跌市 3/531；阈值敏感性、风格标签 |
| V3 提前板块 | `sector_attention.py::build_sector_potential` / `SECTOR_POTENTIAL_PREVIEW_1` | 三分支硬条件 | 派生历史缺失导致 0；不能当负结论 |
| V3 生命周期 | `progress_potential_episode` / `SECTOR_SIGNAL_LIFECYCLE_PREVIEW_1` | QUALIFIED→MONITORING/CONFIRMED/失效 | 构建器当前仅传一日；须重建连续交易日 |
| V3 成员/短名单 | `build_sector_member_roles`、`research_association.py` | 角色、LOO 支持、主备板块、20 股上限 | 预览上限、同股去重、短名单因果链 |
| 本地板块/个股关联 | `association.py`、`strength_association.py`、`intersection.py` | 板块属性、交并差、强势关联证据 | 保留数据但 V3 菜单隐藏；时点/成员准确性 |
| 旧本地涨停 | `limit_rules.py`、`limit_ladder.py`、`limit_promotion.py` | 旧 V2 兼容的涨停/梯队/晋级推断 | V3 不应调用或回退；确认后台不会影响 V3 结论 |
| 在线事件 | `online_events.py`、`event_batch.py`、`p09_products.py` | 涨停池、七池、最强题材/成员和速览 | 来源时点/交易日、分页全量、断源降级 |
| 在线热榜 | `ths_hot_rank.py`、`eastmoney_hot_rank.py`、`hot_rank_view.py` | 四榜请求时读取 | 不落盘原始行/批次/历史，平台排名不当本地信号 |
| 在线附加 | `quotes_capability.py`、`lh_list_capability.py`、`external_evidence.py` | 报价、龙虎榜、外部证据能力门 | 来源不可用时失败关闭，不污染本地快照 |
| 效果评估 | `research_signal_evaluation.py`、`forward/evaluation.py` | 后续表现/信号结果绑定 | 当前效果仍待观察，不得称盈利验证或预测概率 |

## 4. 独立审计项与验收

| ID | 范围与证据 | 需要的验收 |
|---|---|---|
| AUD-HIST-01（阻断潜在轨道结论） | 8,785 日原始序列但 `sector_cycle_daily` 只有 1 日；3 个板块变化字段 531/531 NaN；`prior_current_within10=None` 常量；episode 单行 | 在不写 TDX 源的前提下，受控构建至少满足配置窗口的历史派生板块数据，并核验 P05/P06/P07 同日、前视隔离、缺值三态和跨日生命周期；完成前 POTENTIAL/EARLY 不可用，不应表述为“市场没有符合对象”。 |
| AUD-CUR-02 | CURRENT=3/531，9 月 11 日上涨 639、下跌 4,856 | 每板块门槛失败分布、边界样本手算、行业/概念/风格分层和阈值敏感性；判断“3”是行情事实还是参数过紧。 |
| AUD-NAN-03 | 三个数值字段 531/531 储存 NaN | DB/API/UI 均显式 UNKNOWN，不计作有值；重建后 NaN/NULL 语义一致。 |
| AUD-V1-04 | V1 候选 1,071 股，V3 短名单 9/0 | 保持独立标签和合同，避免把 V1 优先排序当 V3 双轨资格。 |
| AUD-MKT-05 | API30 市场摘要 UNAVAILABLE，M13 市场周期有同日数据 | 修复摘要数据绑定或明确独立降级，不得跨快照静默拼接。 |
| AUD-ALL-06 | 本清单所有模块 | 为每模块建立输入/公式/版本/反例/回归/运行证据矩阵；对有交易解释含义的结论进行人工样本核对和效果观察。 |

## 5. 当前接受结论

**DEGRADED_PASS（页面修复）/ BLOCKED（V3 潜在轨道有效性）**。弹窗页大小错误和 V1 优先名单遗漏已修复；CURRENT 只有 3 个在下跌日有算法上的可解释性，但未证明参数最佳。POTENTIAL/EARLY 为 0 的解释不能归结为“本地只生成一天”，因为本地日线有长历史；真正缺的是派生板块历史与先前状态绑定。不得把本文件视为外部审计已完成。

与用户此前“仅保留最近一次 9 月 11 日发布数据”的要求兼容的实现方向是：将更早日线作为**只读计算窗口**，在构建任务内临时形成所需的前序板块特征和状态，只发布 9 月 11 日的最终研究行及必要的可审计依赖摘要；是否保留额外历史派生表应另行明确，不因修复算法而擅自扩大发布数据范围。

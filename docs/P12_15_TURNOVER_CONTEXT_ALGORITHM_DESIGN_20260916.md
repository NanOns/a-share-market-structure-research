# V3.3 候选后置换手率算法升级与个股应用设计

> 合同：`TURNOVER_CONTEXT_V3_3_V1_DRAFT`；参数：`TURNOVER_CONTEXT_PARAMS_V1_DRAFT`  
> 编制日期：2026-09-16（Asia/Shanghai）  
> 状态：`DESIGN_COMPLETE / IMPLEMENTATION_PENDING / EFFECT_OBSERVATION_PENDING`  
> 本轮交付仅为设计文档。未修改业务代码、配置、数据库、活动研究包；未发起在线行情请求或来源测试。

## 1. 范围与结论

换手率在本项目中的定位是：**V3.3 完成初筛后，对已入选个股补充“参与程度与收盘结果是否匹配”的证据**。它不要求全市场覆盖，不是新的入选条件，不补齐核心缺失分数，不替代原有结构、板块和 LOO 判断。

本次采用“可信换手事实 → 同组参与程度 → 场景价格接受度 → 个股解释与研究提示 → 独立增强顺序”的算法。优先解决个股详情中的实际应用，不能只增加一列百分位。

用户提供的《V3_3_TURNOVER_CONTEXT_AND_ONLINE_SOURCE_PLAN_20260916.md》是参考方案。其来源探测、Source Router、12源测试矩阵、五份交付物等任务不属于本轮请求，不执行。本方案也不以完成来源测试作为编写算法的前置条件；来源身份无法证明时，算法明确降级。

本版不修改：候选集合、primary_category、matched_categories、selection_mode、sector_support_status、核心 risk_codes、category_score、category_rank、rank_status、原始显示顺序、研究包摘要和历史快照。新增风险仅写入 turnover_risk_codes。`QUALIFIED_UNRANKED` 即使获得正向换手证据，也仍然是未完整评分。

## 2. 本地核查依据与当前状态

### 2.1 适用文档及证据

本阶段按 AGENTS.md 先查阅以下文档及代码，再制定合同：

- `docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md`：V3.3 主算法与时间身份边界。
- `docs/P12_14_FULL_CANDIDATE_TURNOVER_ENHANCEMENT_ACCEPTANCE_20260916.md`：候选全集关联和旧二级顺序。
- `docs/P12_14_GENERATION_TIME_TURNOVER_INTEGRATION_ACCEPTANCE_20260916.md`：生成期获取、腾讯备用和页面只读物化结果，优先于旧页面主动请求描述。
- `src/workbench_analysis/turnover_enrichment_v3_3.py`、`turnover_shadow_v3_3.py`。
- `src/workbench_analysis/today_research_factors_v3_3.py`、`today_research_scanner_v3_3.py`、`today_research_rank_loo_v3_3.py`、`pullback_episode_v1.py`。
- `src/workbench_service/turnover_enrichment_service.py`、`src/workbench_service/static/v2/v3-unified.js`。
- 两份 `config/p12_14_*turnover*_v1.json` 来源合同，以及本地活动研究包、已封存换手观察。

这里的文件路径均相对于项目根目录 `E:/codex work/大A交易`。本轮只读既有产物，没有重跑 scanner、日常流水线或历史回测，没有访问 TDX 根目录。不能据此声明新的 Phase 0 或生产发布验收通过。

### 2.2 当前冻结样本（本次直接读取本地产物）

- 研究交易日：2026-09-15；活动摘要：`45ae278c97d7a4fdec844fe52158ad0f85a39a76ac72adde69092588161fa4d7`。
- 观察摘要：`598bbc633bdf18bddd680a9915d0763cb5c1466baf7f484f5e8ba8564a408bae`。
- 候选56只，支持请求的沪深候选54只，BOUND 47只；全部候选覆盖率47/56=83.93%，受支持范围绑定率47/54=87.04%。两者均不是全市场覆盖率。
- 47条绑定记录均标记 `TENCENT_QUOTES_LATEST / TENCENT_FLOAT_SHARE_BASIS`。这证明当前记录的身份标签，不等于本次核实了真实分母定义。

| 主类别 / 模式 / 评分状态 | 候选数 | 已绑定数 | 设计含义 |
|---|---:|---:|---|
| LAUNCH_CONFIRM / INDEPENDENT / QUALIFIED_UNRANKED | 47 | 41 | 数量和覆盖具备相对比较的必要条件，仍需口径及身份门 |
| LAUNCH_CONFIRM / SUPPORTED / QUALIFIED_UNRANKED | 6 | 5 | 位于最小样本边界，标签需标注小样本 |
| TREND_CONTINUE / SUPPORTED / SCORED | 3 | 1 | 禁止相对参与分层，不得借其他类别凑样本 |

本样本没有 RECOVERY_TURN、STRONG_PULLBACK 候选。后文这两类规则是待实现设计，不冒充当前实证。

### 2.3 现有算法的具体不足

1. `apply_turnover_enhancement` 先对传入的全部 BOUND evidence 计算百分位，之后才按类别、模式划分未评分排序组。比较总体与使用总体不一致，且没有最小样本/覆盖门；函数边界未先排除池外证据。
2. 旧百分位是平均秩除以 n；单样本会得到1，可能显示 HIGH；全部同值也不固定为0.5。
3. 未评分组以“有值优先、百分位降序”产生增强序号，缺失行序号为空。前端目前只是显示序号，并未据此整体重排；后续若直接采用这些序号，会引入缺失惩罚。
4. 已评分行的增强序号默认复用 category_rank，容易混淆核心排名与换手评价。
5. 算法合同名称绑定 Eastmoney，缺省 basis 也是 Eastmoney；腾讯已有单独标签，但没有充分表达分母可信度。前端详情固定显示“浮动股本口径”。
6. 当前换手详情只列数值、百分位、序号，未利用 clv、break_margin_close20 和 scanner_evidence 判断个股。
7. 现有物化读取只要有 evidence 就返回 AVAILABLE，不代表相对比较或语义判断已经满足条件。

## 3. 输入、身份与数据契约

### 3.1 输入范围

`C` 为同一个冻结研究包的完整候选列表，去重键 security_id；分页、搜索过滤、页面 TopN 不能改变 C。关联只接受 `security_id ∈ C` 且交易日、bundle_digest 匹配的记录。非候选输入丢弃并统计 `OUT_OF_SCOPE_EVIDENCE`。

没有进入 C 的股票不会被换手层扫描或请求。已经进入 C 但未请求、市场不支持、源失败等，均保留候选并明确缺失原因。

### 3.2 标准化事实

每行至少携带：security_id、trade_date、bundle_digest、turnover_rate、turnover_unit、turnover_basis、basis_verification、source_id、source_contract_id、field_map_version、observed_at、source_quote_time、binding_status、source_identity_sha256。

- turnover_rate 统一为比例：0.052=5.2%；展示时乘100。不能依据数值大小猜单位。
- turnover_basis：FLOAT_SHARE / FREE_FLOAT_SHARE / TOTAL_SHARE / SOURCE_DEFINED / UNKNOWN。
- basis_verification：VERIFIED / DECLARED_ONLY / UNKNOWN。仅代码里存在 `*_FLOAT_SHARE_BASIS` 字符串，最高只能视为 DECLARED_ONLY，除非引用已核实的版本化口径证据。
- UNKNOWN 或 DECLARED_ONLY：保留可信绑定数值用于展示，但不生成 LOW/HIGH、Tier正负或增强排序；显示“来源报送换手率，口径待核实”。
- TOTAL_SHARE 不解释为“流通筹码参与”；本版仅已核实 FLOAT_SHARE / FREE_FLOAT_SHARE 可进入参与语义，各自单独分组。SOURCE_DEFINED 需要后续明确分母和比较许可后升版，当前只展示。
- 有限数、非负是基础要求；兼容现行入口的 `0<=rate<=1` 门。大于1暂记 `OUT_OF_CONTRACT_RANGE`，不得截成1、不得宣称经济上不可能；放宽须独立更新合同。
- 0不能当 NULL。若本地 volume>0 而来源 rate=0，保留报送值和 `ZERO_PRECISION_AMBIGUOUS`，本版只展示、不分层，避免来源舍入/占位歧义。
- 同证券同身份重复且完全一致可去重；值、口径、时间冲突则该证券 `EVIDENCE_CONFLICT`，不使用最后一条静默覆盖。

### 3.3 日期绑定

保留现行 RAW 收盘价、成交额、成交量三重匹配：

```text
abs(x-y) <= max(abs_tol, rel_tol * max(abs(x), abs(y)))
close:  abs_tol=0.011, rel_tol=0.0005
amount: abs_tol=100元, rel_tol=0.002
volume: abs_tol=100股, rel_tol=0.002
```

本地指纹也必须有限且为合法实际交易记录；价格使用 RAW，不能拿复权 close 匹配线上价。额量单位先标准化，再比对。

未来实现必须同时检查可用的源日期/时间：源日期与目标日冲突、源时间在目标收盘前、时间晚于记录的接收时间且无法解释，均不可用；源时间缺失只能标记 `FINGERPRINT_ONLY`，不能写成已获得明确日期证明。三字段匹配是近似会话佐证，不是数学上的唯一日期证明。本版 FINGERPRINT_ONLY 可显示事实，正负语义和排序要求 `SESSION_VERIFIED`（日期与收盘时间可信且指纹通过）。不能用 observed_at 替代源交易日。

当前旧物化记录未保存 source_quote_time/source_contract_id 等完整字段。不得倒填时间或臆造历史身份；保留旧记录，由新契约给出 `LEGACY_EVIDENCE_INCOMPLETE`，必要时只展示。后续在既有正常生成链封存更多元数据即可，本轮不请求重采。

## 4. 覆盖率与比较总体

### 4.1 三层能力要分开

1. FACT_AVAILABLE：这条报送值合法且指纹绑定，可展示。
2. COMPARABLE：身份、单位、basis、会话均通过，允许组内比较。
3. CONTEXT_READY：比较组有效，且个股所需场景价格事实完整，可给语义。

因此“47条 BOUND”不能直接等于“47条可增强排序”。

### 4.2 分组及公式

先定义业务组 `G=(primary_category, selection_mode, rank_status)`。组内不跨模式、不跨评分状态。再按 `K=(source_id, source_contract_id, field_map_version, turnover_basis)` 划分可比集合。版本兼容没有独立证据时不合并。

```text
N = |C|
B = C中 FACT_AVAILABLE 的数量
M = C中 COMPARABLE 的数量
global_fact_coverage = B/N
global_semantic_coverage = M/N
n_gk = G内符合K且COMPARABLE的数量
group_coverage = n_gk / |G|
```

分母 |G| 包括未获取、不支持、错误及另一来源记录，不能在请求失败后缩小分母。另报 supported_binding_rate 供来源运维观察，不用于算法门。

门限（均是待验证工程参数）：

- N=0：EMPTY，返回空增强列表，不除零。
- 全局 semantic coverage≥0.80：允许检查各组；不是自动给所有组放行。
- 0.60≤coverage<0.80：DEGRADED，保留事实及本地价格说明，不生成相对参与标签或换手正负 Tier。
- coverage<0.60：BYPASSED；主流程和核心顺序原样返回，有值可在证据抽屉展示，不做语义排序。
- 单个 G/K 必须同时 `n_gk>=5`、`group_coverage>=0.70` 才有效；5～9条附 `SMALL_COMPARISON_GROUP`。
- 不足时不回退到全候选百分位、不跨类别合并，不临时使用固定5%/10%阈值补位。

这比参考方案更明确地区分“来源有值”和“可用于算法”。当前旧物化可能因身份字段不完整暂不能通过语义门，这是正确降级，不是算法失败。

### 4.3 百分位及参与程度

仅在通过门的 G/K 内，以标准化值精度比较，使用中点经验分布：

```text
p_i = (count(rate_j < rate_i) + 0.5 * count(rate_j == rate_i)) / n_gk
LOW:    p_i <= 0.20
NORMAL: 0.20 < p_i <= 0.80
HIGH:   p_i > 0.80
```

并列不按证券代码人为分开；全部同值 p=0.5，全部 NORMAL；5条互异样本 p=0.1/0.3/0.5/0.7/0.9。百分位仅表示“当前同类候选中的相对参与”，不表示全市场排名，也不表示该股票相对自身历史放量。

本版不需要历史换手率，不计算换手率/20日均值，不用今日股本重建历史换手，不把某一天缺失插值补齐。未来若增加自身历史口径，另立合同。

## 5. 场景价格接受算法

### 5.1 事实复用与读取优先级

读取同 bundle 的 factor_evidence、scanner_evidence 和已经封存的 episode 证据。top-level 字段只在与 factor_evidence 一致时复用；冲突记 `LOCAL_FACT_CONFLICT`，不选更有利的值。没有字段不另查“最新行情”补历史。

复用公式：`clv=(C-L)/(H-L)`，H=L时未知；`break_margin_close20=C/PHC20-1`，PHC20为此前20日最高收盘价；`bias20=C/MA20-1`；`amr20_mean_prior=A_t/mean(A_(t-20:t-1))`。价格均沿原因子价格基准及锚点，金额沿原因子额量口径。

回踩字段来自 `pullback_episode_v1.py` 的已确认事件：pullback_contraction为回调阶段平均成交额/峰值截至日的前5日平均成交额；confirm_amount_ratio为确认日额/回调阶段平均额。不能用单日AMR假装回调阶段收缩。当前产物没有这些字段时标记缺失，不假定已封存。

### 5.2 确定性判定顺序

先检查主类别对应的已封存 eligible 必须为 true；false 或必要核心检查明确与候选身份冲突，则 `CORE_EVIDENCE_CONFLICT`、T2、不排序，并另开审计。不能把不可能出现的主场景失败包装为正常T3。

然后检查下表该场景所需字段：任一未知、非有限或域不合法 → `PRICE_CONTEXT_UNKNOWN`；已知完整才判定 STRONG，否则 MARGINAL。允许在字段不足时展示已知事实，但不推断完整价格接受状态。所有布尔采用 true/false/unknown，不能 bool(null)。

| 场景 | 本版必需证据 | STRONG 的精确条件（全部满足） |
|---|---|---|
| LAUNCH_CONFIRM | launch.eligible、clv、break_margin_close20、intraday_reject_high20、amr20_mean_prior | clv≥0.75；break_margin_close20≥0.01；intraday_reject_high20=false；AMR≥1.20 |
| RECOVERY_TURN | recovery_turn.eligible、r5/r20分支、clv、bias20、amr20_mean_prior | clv≥0.70；bias20≥0；AMR≥1.05；r5或r20至少一个true |
| STRONG_PULLBACK | pullback.eligible、当日CONFIRMED事件、clv、pullback_contraction、confirm_amount_ratio、intraday_reject_high20 | clv≥0.70；contraction≤0.85；confirm_ratio≥1；intraday_reject_high20=false |
| TREND_CONTINUE | trend_continue.eligible、clv、bias20、scanner检查CLOSE_ABOVE_PRIOR_HIGH、amr20_mean_prior | clv≥0.70；CLOSE_ABOVE_PRIOR_HIGH=true；0.80≤AMR≤2.50 |

RECOVERY的分支用三值OR：一支true即可成立；不能要求两支都存在。其余表列字段依上述规则处理。TREND的bias20用于下一节位置风险，仍要求已知。

MARGINAL 是“原资格仍成立，但不满足本增强层更强的收盘接受条件”，不是主算法失败。明确记录哪些增强条件未达到。例如启动 clv=0.77、突破幅度0.26%，因突破幅度未达1%而为MARGINAL。

上述0.75/0.70/1%是新增强层首轮工程参数，不改原 scanner 的0.60/0.55准入门，不声称经过收益优化。AMR仅复核已有额量语境，不再加一次成交额分数。

本版不常规输出参考方案的 HIGH_CHURN_REJECTION：已通过当前主场景的候选若出现直接否定其资格的同日事实，应优先排查身份或事实冲突。未来若扩展跨日跟踪再单立“确认后失败”状态。

## 6. 换手与价格组合：实际进入个股判断

先得到参与分层及STRONG/MARGINAL，再按下表生成基础状态。无合法参与分层时无论价格多强，都不得生成换手确认。

| 参与程度 | 价格接受 | turnover_context | Tier / 判断 |
|---|---|---|---|
| HIGH | STRONG | HIGH_PARTICIPATION_ACCEPTED | T1，参与与价格结果相互支持 |
| NORMAL | STRONG | NORMAL_PARTICIPATION_ACCEPTED | T1，正常参与下形成较好收盘结果 |
| LOW | STRONG | LOW_CHURN_EFFICIENT_ADVANCE | T2，低相对周转下仍保留较好价格结果 |
| HIGH | MARGINAL | HIGH_CHURN_MARGINAL_ACCEPTANCE | T3，相对高周转但收盘接受有限 |
| NORMAL | MARGINAL | NORMAL_NEUTRAL | T2，没有额外确认或风险结论 |
| LOW | MARGINAL | LOW_PARTICIPATION_WEAK_CONFIRMATION | T2，额外确认有限，不以低换手处罚 |
| 任意 | UNKNOWN | PRICE_CONTEXT_UNKNOWN | T2，事实不足 |
| UNKNOWN | 任意 | TURNOVER_UNKNOWN | T2，换手证据不足 |

与参考方案的明确差异：LOW+MARGINAL不设T3。低换手可能有多种原因，仅凭低相对参与和边缘接受尚不足以降级；T3必须有可信的高参与与价格结果不匹配组合。

场景解释覆盖基础名称，但保留 `base_context`：

- 启动：直接用基础状态；T1解释“同类候选相对参与较高/正常，且突破幅度与收盘位置均满足增强确认”。T3指出具体未达条件，不说“出货”。
- 回踩：NORMAL/HIGH+STRONG → `PULLBACK_CONFIRM_WITH_PARTICIPATION`、T1；HIGH+MARGINAL → `PULLBACK_HIGH_CHURN_WEAK_ACCEPTANCE`、T3。解释中区分回调阶段成交额收缩和今天换手，不能说已观察到回调期换手收缩。
- 修复：NORMAL/HIGH+STRONG → `RECOVERY_WITH_PARTICIPATION`、T1；HIGH+MARGINAL → `RECOVERY_HIGH_CHURN_CAUTION`、T3。指出MA5或MA20分支；只知道r5不能写“已收复MA20”。
- 延续：HIGH+MARGINAL且bias20≥0.08 → `HIGH_CHURN_TREND_RISK`、T3；其余HIGH+MARGINAL保留普通T3。0.08只为风险语境工程初值，不是核心过热否决。其余按基础状态；不得称“换手较昨日放大”，因为没有昨日换手。

Tier优先级：身份/事实异常或缺失先T2旁路；合法场景组合才进入T1/T3。所有解释输出为“已知事实、规则匹配、解释边界、后续观察”，不输出主力方向、上涨概率、买卖指令。

示例（合成，不是实盘评价）：

```text
启动候选：rate=6.2%，组内p=0.90，CLV=0.82，突破幅度=1.6%，AMR=1.4。
结论：T1 / HIGH_PARTICIPATION_ACCEPTED。
理由：同组相对参与较高，收盘靠近日内高位且保持1.6%的平台突破。
观察：后续是否保持原突破结构；此处没有预测后续价格。

启动候选：p=0.90，CLV=0.62，突破幅度=0.3%，AMR=1.4。
结论：T3 / HIGH_CHURN_MARGINAL_ACCEPTANCE。
理由：高相对参与，但CLV和突破幅度均未达到增强确认线。
候选资格、核心分数与风险事实不变。

同样价格事实但换手缺失：T2 / TURNOVER_UNKNOWN。
显示本地启动判断，同时提示换手不可判断；不能沿用上例T3。
```

## 7. 缺失中性与独立排序

### 7.1 先有个股证据，再考虑顺序

SCORED：展示context、Tier、理由，category_rank保持不变；新 `turnover_enhanced_rank=null`，不复制核心排名。原始列表默认顺序不变。

QUALIFIED_UNRANKED：在同G内生成可选增强视图；不能跨类别、模式、评分状态，也不能将换手证据解释为补全核心评分。

### 7.2 缺失锁位算法

参考方案“所有T1→T2→T3”仍可能让缺失股相对降位。本版使用固定空位方式：

1. 保存冻结候选原始数组位置 `core_display_rank`，不依赖security_id重新排序。
2. 在一个通过比较门的 G/K 中，取同时满足 CONTEXT_READY 的未评分行作为可移动集合 S。
3. S以 `(tier_order(T1=1,T2=2,T3=3), core_display_rank)` 稳定排序，不再以原始rate或百分位打破并列。
4. 仅把排序后的S放回S原本占据的槽位。其他来源、不支持、缺失、组失效、价格不足及SCORED行位置全部锁住。
5. 输出独立 `enhanced_display_order`；`turnover_enhanced_rank` 是移动行最终在业务组G中的一基位置，可以有空号；不可比较行该字段null，并有 `position_policy=LOCKED`。
6. 没有有效移动集合或层关闭时，增强顺序与原顺序完全一致。

例：原顺序 `[A(T3), X(缺失), B(T1), C(T2)]`，增强顺序 `[B, X, C, A]`。X始终第2，不被自动放尾。此机制保证缺失自身的绝对位置不变；它不是全组按Tier排序，因此页面必须标明“同组可比较证据增强顺序”，不可冒充完整优劣榜。

默认主表继续原顺序；可提供显式“查看增强顺序”选项及前后位置。即使只做证据展示、不打开排序，所有SCORED和未评分个股都应使用本章之前的解释，不能让新算法只影响少数序号。

### 7.3 降级表

| 情形 | 事实展示 | 语义/Tier | 排序处理 |
|---|---|---|---|
| 源超时、失败、未请求、无记录 | —及具体原因 | UNKNOWN/T2 | 锁位 |
| 市场不支持（当前BJ） | 不支持 | UNKNOWN/T2 | 锁位，候选保留 |
| 日期、证券、bundle或三指纹不符 | 不作为目标日换手展示 | UNKNOWN/T2 | 锁位 |
| 单位未知、NaN/Inf/负数、超合同范围 | 无有效值 | UNKNOWN/T2 | 锁位 |
| basis未核实、旧元数据缺失、仅指纹日期证据 | 可显示已绑定报送值及限制 | UNKNOWN/T2 | 锁位 |
| 可信0但精度含义未确认 | 显示来源报送0及限制 | UNKNOWN/T2 | 锁位 |
| 组少于5条或覆盖不足 | 可显示值，无有效p | UNKNOWN/T2 | 整个比较集合不动 |
| 全局覆盖降级 | 已绑定值可展示 | UNKNOWN/T2 | 全局原序 |
| 换手可信但价格事实不足 | 值及缺失字段 | PRICE_CONTEXT_UNKNOWN/T2 | 锁位 |
| 同股重复冲突/本地证据冲突 | 显示异常原因 | T2旁路 | 锁位并登记审计 |
| 全部NULL或增强开关OFF | 本地研究照常 | UNKNOWN/T2或不展示 | 原序完全一致 |

禁止0填充、均值填充、前日沿用、用成交额倒推换手、以失败代替低参与。整层异常在可选增强边界捕获并返回基线，不吞掉真正的本地核心错误。

## 8. 输出与集成设计

建议新增独立纯函数模块 `src/workbench_analysis/turnover_context_v3_3.py`。它无网络、不写数据库，消费冻结候选与标准化证据，输出同长度的sidecar。未来实现触点：

| 位置 | 计划修改 |
|---|---|
| turnover_enrichment_v3_3.py | 保留指纹绑定，按新契约标准化身份，旧百分位排序由新纯函数替代 |
| turnover_enrichment_service.py | 读取物化证据后执行或读取新context sidecar，分别报告事实/语义能力，不以非空即完整AVAILABLE |
| turnover_shadow_v3_3.py | 新版本封存完整失败原因、身份、比较组、参数hash和规则输入；不复写旧观察 |
| v3-unified.js | 列表增加简短换手判断；详情显示事实、接受条件、组合结论、降级原因；口径动态显示 |
| 既有生成流水线 | 保持初筛完成后获取；本地核心成功独立于增强失败；不新增页面在线请求 |

建议sidecar结构：

```yaml
algorithm_contract_id: TURNOVER_CONTEXT_V3_3_V1
parameter_hash: ...
bundle_digest: ...
observation_digest: ...
as_of: ...
layer_status: AVAILABLE|DEGRADED|BYPASSED|EMPTY
coverage: {candidate_n: 56, fact_n: 47, comparable_n: 0}
# comparable_n=0仅示意旧身份未通过新门，不能把它当本次执行的统计结果
items:
  - security_id: SH.xxxxxx
    turnover_rate: null
    turnover_basis: UNKNOWN
    basis_verification: UNKNOWN
    binding_status: SOURCE_FAILED
    semantic_status: UNAVAILABLE
    turnover_activity_percentile: null
    turnover_activity_band: null
    comparison_group_id: null
    comparison_n: 0
    comparison_coverage: null
    price_acceptance: UNKNOWN
    base_context: TURNOVER_UNKNOWN
    turnover_context: TURNOVER_UNKNOWN
    turnover_priority_tier: T2
    turnover_reason_codes: [SOURCE_ROW_MISSING]
    turnover_risk_codes: []
    rule_evidence: []
    core_display_rank: 1
    turnover_enhanced_rank: null
    position_policy: LOCKED
    effect_status: EFFECT_OBSERVATION_PENDING
```

rule_evidence每条保存字段路径、实际值、比较符、阈值、三值结果，能从结论回溯原研究包。source_error与单股原因分开保存。旧记录没有逐股失败原因时输出 `LEGACY_REASON_NOT_RECORDED`，不猜测7只未绑定的具体原因。

冻结身份至少包括bundle_digest、observation_digest、algorithm_contract、parameter_hash、组成员摘要。原子写入项目目录内新的版本化产物（临时文件+同目录replace），不修改TDX及原研究包；读回校验摘要后才更新增强索引。

同一研究包有多次观察时：线上显示可采用明确版本的新观察；后验评价必须锁定当时已选的observation，不按未来“绑定数量最多”重新选择历史数据。今天重新读取旧行情不能成为昨天已知的增强信号。

## 9. 算法伪代码

```python
baseline = freeze_core_rows(candidates)
C = validate_unique_candidates(baseline)
E = normalize_and_validate(evidence, C, bundle_identity)
facts = attach_without_mutating_core(C, E)

if not C:
    return empty_sidecar()

for row in facts:
    row.price_context = evaluate_frozen_category_facts(row)
    row.context, row.tier = 'TURNOVER_UNKNOWN', 'T2'
    row.position_policy = 'LOCKED'

global_gate = comparable_count(facts) / len(C) >= 0.80
if global_gate:
    for G in group_by_category_mode_rank_status(facts):
        for K in group_by_source_contract_basis(G):
            S = comparable_rows(K)
            if len(S) < 5 or len(S) / len(G) < 0.70:
                record_group_bypass(K)
                continue
            compute_mid_distribution_percentiles(S)
            for row in S:
                if row.price_context.complete_and_consistent:
                    row.context, row.tier = category_context(row)
                    row.semantic_status = 'CONTEXT_READY'
            stable_sort_ready_unranked_rows_into_original_slots(G, K)

assert core_projection(facts) == baseline
return immutable_versioned_sidecar(facts, coverage, identity)
```

实现中coverage、N=0、身份失败、冲突和OFF分支需先处理。此伪代码只定义算法流，不是本轮已经运行的新实现。

## 10. 验收与效果观察（未来实施使用，本轮未执行）

### 10.1 必须通过的工程与数据反例

1. 池外行不改变百分位；证券、日期、bundle不符不关联。
2. 单样本、3条、4条均禁止相对标签；5条互异为0.1/0.3/0.5/0.7/0.9；同值全部0.5。
3. 全局足够而某组不足仍旁路；另一来源同值也不能混池。
4. 全局0.60、0.80及组0.70边界按本文精确定义；N=0无除零。
5. 启动强接受HIGH为T1；边缘HIGH为T3；强接受LOW为T2；边缘LOW仍T2。
6. 核心eligible冲突、CLV缺失、H=L、回踩事件缺失均不产生正负换手结论。
7. 当前3只趋势、1条换手的组合不得输出HIGH；没有历史换手不得输出“较昨日放大”。
8. source时间与目标日冲突即使指纹碰巧匹配仍不可用；旧记录不凭空补元数据。
9. `[T3,缺失,T1,T2]`按锁位规则变为`[T1,缺失,T2,T3]`；SCORED始终原位。
10. OFF、全部NULL、接口失败时，候选集合、所有核心字段及显示顺序与基线一致；相同输入/参数产生相同摘要。
11. 页面请求只读本地，证据失效不能导致候选列表空白；解释文本与rule_evidence一致。
12. 参数变化创建新sidecar，不覆盖历史观察；对旧产物回放时显示“重解释”，不当作当日真实运行。

每阶段还需：版本化合同、输入/输出摘要、真实本地样例、降级说明、页面证据和验收回执。测试全绿仅能证明工程行为，不能证明排序有效。

### 10.2 消融和后验

未来比较A原始顺序、B旧换手降序（仅作旧算法对照）、C本方案锁位语义顺序。候选及核心分数相同，分别披露覆盖率、锁位数量、实际移动数量；B的缺失处理差异单独说明，不能全归因于context。

后验复用项目既有forward评价合同的FRET/MFE/MAE及1/3/5/10会话口径，不另发明成交假设。仅在持有期数据成熟后计算，按日期、类别、模式、rank_status、Tier、source/basis分层。额外分析相同CLV/AMR语境下的差异，检查换手是否只是重复价格/成交额证据。

当前代码20个绑定日、50行的SHADOW门只表示覆盖准备度，不表示效果通过。同股重复观察、同日多bundle不能充当独立交易日。稀疏组和源覆盖缺失需单独报告，不将“未取得换手”并入低换手对照。

本版不进入核心综合分。效果未证明时可使用明确标注的研究解释；增强顺序保留可选/观察状态，不宣称提高收益。

## 11. 分阶段落地与独立审计登记

| 阶段 | 合同/范围 | 验收证据与结果要求 | 下一步 |
|---|---|---|---|
| 本轮设计 | 本文DRAFT；本地只读核查+算法设计 | 文档自检完整；DESIGN_COMPLETE，实施/效果均PENDING | 后续按用户实施安排进入纯函数阶段 |
| A 纯算法 | 新context/参数合同；离线固定输入 | 三值、组门、矩阵、锁位、核心不变的反例和回执 | B |
| B 关联与解释 | 身份元数据及sidecar/API/UI | 真实本地样例、未知口径降级、页面只读证据；不足可DEGRADED_PASS | C |
| C 观察 | 冻结as-of的消融合同 | 工程通过与效果待观察分别记录 | 独立后验评审 |
| 来源测试 | 用户后续独立任务 | 不属于A/B/C本次设计交付，不在这里认定来源可用 | 另案制定矩阵 |

以下跨层问题在本文作为独立审计项开启跟踪，不能随换手算法阶段通过自动结项，也不在本轮擅自修复：

| 审计ID / 状态 | 独立范围与现有证据 | 独立验收条件 |
|---|---|---|
| TC-AUD-01 / OPEN | 来源分母及身份契约：算法Eastmoney命名、腾讯basis声明、前端固定口径文案 | 来源证据可追溯、未知不假定、算法与来源版本分离；未来来源测试另行完成 |
| TC-AUD-02 / OPEN | 时间与观察选择：旧物化未保留source_quote_time，读取按bound_count/时间选择观察 | 时间元数据传递、反例验证、as-of观察冻结及独立审计回执 |
| TC-AUD-03 / OPEN | 核心评分完备性：本样本53只QUALIFIED_UNRANKED；样例rps5_delta3为空 | 单独归因各必需字段缺失，确认评分合同与生产字段链；不能用换手补分掩盖 |

已有M10 Amount A等综合审计继续按各自登记跟踪，不纳入本文的换手门验收，也不推断其已解决。

## 12. 本轮交付验收记录

- 阶段合同：只编写基于当前项目的换手率升级设计。
- 证据：源码、当前活动研究包、47条本地绑定观察、最新生成期接入回执；未进行网络验证。
- 设计接受结果：`DESIGN_COMPLETE`，规则、计算总体、参数、缺失、排序、集成、独立审计及后续验收已明确。
- 发布接受结果：`NOT_APPLICABLE`；未实施、未执行新算法测试，不标记FULL_PASS或算法效果已验证。
- 下一阶段：按本文实现纯函数与解释层，保留来源和时间身份不足时的中性降级；在线来源测试由用户后续另案开展。

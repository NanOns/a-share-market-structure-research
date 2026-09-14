# V3「今日重点研究」与研究工作台详细升级方案

> 文档版本：`V3-TODAY-RESEARCH-UPGRADE-PLAN-v2.1-AUDITED`  
> 状态：`AUDITED_DESIGN / IMPLEMENTATION_PENDING`；设计审计接受结果 `DEGRADED_PASS`，不代表算法效果或生产发布通过。  
> 编制/审计日期：2026-09-14，Asia/Shanghai。原设计：SOL；本次：结合当前工作区源码、配置和生产数据只读复核，原位升级。  
> 产品仍为 V3。缺陷是 V1—V3 延续的“结构候选没有形成今日研究决策闭环”，不能归因为 V3 新引入。  
> 本轮只修改本方案及单独修改说明，不实施业务代码、配置、数据库或生产发布变更。TDX 全部来源只读；本轮未访问 TDX 根目录。

## 1. 审计结论与核心目标

本地数据已具备建设收盘研究系统的基础。真正缺少的是：**在指定收盘日，从全量可评股票中识别新的研究条件，先排除结构和数据风险，再按不同场景列出值得查看的对象，并能解释为什么今天出现、等待什么、何时失效及后续表现。** 这不是再做一个高 RPS 榜，也不是把旧榜改名。

原方案的方向保留：独立个股事实、CURRENT/POTENTIAL、硬门先于排序、四类场景、解释与回放。但 v1.0 尚不能直接交付实现，主要缺口是：公式与现行口径混用；回踩缺事件次序；延续没有当日新触发；未知板块与可选评分处理矛盾；LOO 未形成端到端硬门；分页与资格截断混淆；可重算价格历史与不可证明的历史成员混淆；原子发布和效果验收停留在原则。

本版本给出一套**可实现的首轮候选合同**。其中数值阈值均为待验证的工程初值，不宣称最优，不输出上涨概率、目标价或交易指令。收盘系统可以识别条件形成和失效，不能仅凭日K线识别真实资金意图或证明未来走势。

v2.1吸收用户提供的线上审计中可核实的问题，并独立修订事件状态、风险标记、评价锚与依赖身份。外部意见是审查材料，不是执行指令；采纳/部分采纳/不采纳及原因见§23。§2生产数量仍为v2.0只读核查的冻结基线，本次未重跑数据库统计，不将旧观察冒充新的生产验收。

目标链路：

```text
冻结交易日/输入/价格基准/成员与统计全集
 → 全量独立个股因子和信号（不先经过旧候选池、板块角色或TopN）
 → 数据门、硬否决、四类当日条件 + 蓄势观察
 → CURRENT/POTENTIAL/W与逐股票LOO证据
 → 个股独立 / 板块共同支持分层
 → 类内评分、唯一主类别、全量结果与首页预览
 → 入选/未入选原因、等待、失效、跨日状态
 → 完整研究版本发布、冻结信号、后验评估
```

## 2. 证据基线与已完成能力

执行优先级：用户本轮范围与 AGENTS.md → 当前适用升级方案及有证据的新回执 → 本文新合同 → 旧建议。不能以文件日期相同推断内容同样新。既有综合算法审计的问题，要结合 `ALGO_R1_CORRECTNESS_RECEIPT_20260914.md` 和 `V3_CURRENT_STRENGTH_REAUDIT_20260914.md` 判断是否已修，不照抄旧故障为当前事实。

本次读取 `data/normalized/adjusted_daily.parquet`，DuckDB 以 `read_only=True` 打开；统计基线如下。它是审计时观察，不会自动跟随之后的构建更新。

| 项目 | 本次事实 | 解释 |
|---|---|---|
| 调整日线 | 19,646,885 行，8,786 个日期，1990-12-19～2026-09-14 | 旧文档截至9月11日的计数已过时；长行情历史不等于PIT历史 |
| 9月14日日线截面 | 6,182行；5,553行有实际bar、完整RAW/调整OHLC及正额量；5,458行标正常universe | 这些分母不同；不能拿6,182当作全部有效股票 |
| 当日OHLC基本检查 | 实际bar中RAW/调整高低开收次序错误均0；非正额量0；调整low非正0 | 仅为当日结构检查，不代表全历史逐笔验证完成 |
| 成功publication | 9月11日、9月14日共2个日期 | 5个COMPLETE run并非5个独立交易日 |
| 最新COMPLETE run | `research-59677a66206c4314b0b2b4b9e88046d0` | 9月14日，版本 `RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE` |
| publication / snapshot | `m4-f787bac7863fa3409d45f75a8b7b5c30` / `m10-mainline-preview-4067dec5315150dc` | 所有当日研究比较必须绑定此组或另一个明确冻结版本 |
| 该run股票信号 | 6,182行；BREAKOUT 163、SETUP 405、RECOVERY 87、TREND_BACKGROUND 1,113、STRUCTURE_BREAK 2,622 | 标签重叠，不把计数相加当独立股票数 |
| 该run板块 | 531行；CURRENT 72、POTENTIAL 0；三项3日变化各531行NULL | 不能解释为市场没有潜在板块；既有必要条件false仍可使部分分支已知失败 |
| 历史身份 | dependency明确 `historical_membership=UNAVAILABLE` | 当前关系可用于今日研究；尚不足以证明历史时点成员 |
| 既有研究清单 | CURRENT_FOCUS 20，EARLY_FOCUS 0；这20行均记录LOO_COMMON_SUPPORT | 当日样本没有证明LOO失败泄漏；源码仍存在未硬过滤的路径缺口 |
| 旧候选 | 9月14日1,045只；A+/A且行业/概念主板块52只 | 是旧合同结果，不是四类今日清单 |
| 关系与板块周期 | 关系区间72,537条；周期仅2日期，9月14日有2个slice | 多slice不是新增历史日；跨run不能混合或重复聚合 |

保留已有工作：V3默认入口、七池默认强势股/去重涨停、在线首次涨停时间排序、唯一在线涨停明细入口、北向卡移除、题材弹窗表格及宽度修复、长说明完整展示、表格内滚动、两位小数/中文均线、一键本地构建。以对应在线修复文档及实际验收为准，本轮不重复开发这些功能。

## 3. 根因与当前实现映射

1. `static/v2/v3-unified.js` 的首页精选仍取 `/api/candidates?...&basis=RECONSTRUCTED&final=1`；`app.py::candidates` 按A+/A、行业/概念主板块筛选并沿用旧优先级。这是历史结构高分被赋予“今天优先”语义的直接证据。
2. `research_features.py` 的 `prior_high20` 是**此前20个收盘价的最大值**；`range5/range20` 也是收盘极差；`amount_vs_prior20` 分母为此前20日**均值**；`liquidity20` 分母为此前20日**中位数**。不能原样复用字段名却换成最高价、中位数或当天窗口。
3. V1 `VOLATILITY20` 是20个对数收益样本标准差 `ddof=1`；V3 `sigma20` 用 `ddof=0`，且用于现有extension公式。不得视为同一个因子。
4. `stock_attention.py` 中 EXTENDED 是 `BIAS20>=0.15 AND extension_z20>=1.5`，不是OR；STRUCTURE_BREAK是连续两个主日历会话低于0.98×MA20。需新增单日重挫/破位门，不能称已有两日门能挡住所有首日破位。
5. 现有RECOVERY已经要求上穿MA5、MA20三日不下降；在它外面增加 `MA5 OR MA20` 并不能扩展为真正的MA20收复分支。新场景必须明确独立分支，而非冗余套用旧RECOVERY。
6. `research_association.py` 的 `_loo_early` 对成员计数剔除了目标股，但改善值取全板块，且择首个非空字段而非三值OR；`shortlist()`最终过滤没有强制 `track_ok is True AND loo_support is True`。因此“现有LOO完整可信”需要纠正。
7. 旧角色只覆盖BREAKOUT/RECOVERY/SETUP；若从这些角色或已截断CURRENT_FOCUS反推四类候选，会漏掉新增回踩、延续及独立触发。必须先从全量股票算资格，再关联。
8. `app.py`先等待M4发布成功，再执行M8/M9、M10和研究构建。基础发布成功不等于完整研究包READY；本期新增研究发布指针门，不能宣称已有全链单事务。

## 4. 范围与产品输出

本期只做 `LOCAL_CLOSE_ONLY`。无分时需求，不开发盘中成交额进度校正、分钟因子或新增在线必需依赖。换手率不作为任何准入、必需评分或发布时间门。TDX允许按既有只读链消费，禁止写入；修正原文“不读取TDX”的不必要限制。

首页显示“今日重点研究 · 本地收盘 YYYY-MM-DD”。若日期落后于可证明的最新本地交易日，显示“最近一次完整研究：YYYY-MM-DD / 当前待构建”；不得用系统今天覆盖旧数据日期。在线日期与本地日期分别显示。

| 场景 | 研究问题 | 新要求 |
|---|---|---|
| LAUNCH_CONFIRM 启动确认 | 今天是否出现收盘越过此前平台的触发？ | 明确突破价基准、额量确认、当日位置 |
| STRONG_PULLBACK 强势回踩 | 前期强势之后的回调，今天是否出现收回/止跌条件？ | 先强势、后回踩、再当日确认；不是高RPS且下跌 |
| RECOVERY_TURN 修复转强 | 调整后是否重新收复关键均线并改善强度？ | MA5收复与MA20收复两条明确分支 |
| TREND_CONTINUE 强势延续 | 已有趋势今天是否有新的延续条件？ | 趋势背景之外必须有当日触发，且CURRENT+LOO通过 |

保留独立的**蓄势观察 SETUP_WATCH**，消费有效SETUP及新增等待条件，不占四类已确认名额。它回答“尚未触发、接下来观察什么”，否则四类全部等确认后才显示仍会遗漏核心的提前研究用途。它不改名成启动确认，也不创建第三套板块榜。

其他观察原因允许多选：`HIGH_POSITION_WATCH`、`PULLBACK_UNCONFIRMED`、`SECTOR_WEAK_NOW`、`SECTOR_FADING`、`STRUCTURE_DAMAGED`、`DATA_INSUFFICIENT`。状态、风险原因和数据质量分别保存，不能把大跌一概命名为高位。

## 5. 时间、价格、额量与统计全集合同

新合同族：`TODAY_RESEARCH_FACTOR_V3_3`、`TODAY_RESEARCH_SCANNER_V3_3`、`TODAY_RESEARCH_RANK_V3_3`、`TODAY_RESEARCH_OUTPUT_V3_3`。v2.1修改了候选逻辑，故替代v2.0草拟的V3_2合同及参数集，不只改文档版本号。本文件定义DRAFT，实施时正式登记版本，不复写既有PREVIEW合同。

### 5.0 依赖锁定与重现范围

所有引用信号均须由 `dependency_lock` 精确指定：contract_id、规范化参数子树hash、可执行实现及其传递依赖源码hash、因子公式hash、日历/universe/调整合同、运行时及数值库锁定版本。BREAKOUT_V3、RECOVERY_V3、SETUP、TREND_BACKGROUND、STRUCTURE_BREAK、EXTENDED均解析到该锁，不允许解释为调用时“最新stock_attention”。板块轨道及评分同样受锁约束。

锁随run和研究bundle封存，构建前对摘要；任一不符拒绝复用，产生新合同/参数版本并新建run。保存hash还不够：必须有可恢复的源码/依赖包或可定位的仓库对象及参数快照，受现有存储合同管理。首版复用锁定实现，不复制一份易漂移的信号代码。P12-02须把实际执行谓词逐项导出至合同，对照§3和stock_attention的checks；配置里声明但代码未消费的字段不能假称已生效。

历史日k的信号使用k时点冻结输入及价格锚；t日的事件峰值/回撤比较统一转换至t锚，不能把不同日锚的数值混算。冻结布尔信号不因换锚重新解释。没有k的可恢复输入时按重构诊断模式计算并标注，不能称PIT。完全相同锁定运行环境要求逻辑结果相同；跨数值平台仅在事先登记的容差内复核，不承诺任意环境浮点逐bit一致。

### 5.1 价格与日历

- `t-k`一律表示主交易日历向前k个会话；`[a,b]`含两端。`mean(C[t-19:t])`恰20个值，`RET20`需21个收盘。缺日不能压缩为“前一条现有记录”。
- 趋势价 `O,H,L,C` 均为同一cutoff、同一调整版本的 `adj_*`。原始报价单列 `O_raw/H_raw/L_raw/C_raw`。公式须标 `price_basis`，禁混RAW高点与调整MA。
- 项目基准是本地TDX .day+GBBQ的仿射前复权 `A×RAW+B`，身份 `TDX_NATIVE_AFFINE_QFQ`；并非外部复权服务，也不承诺与所有客户端显示逐点相同。
- **历史t回放必须以t为调整截止日重建A/B，只纳入当时可用且生效日≤t的事件。** 当前最新QFQ整表不能直接切到t冒充PIT；仿射含加项，收益率和百分比阈值不保证对换锚不变。还应检查源事件的可获知时间，事后补录只能为重构诊断。
- 当日形态使用真实bar。V1允许已证明停牌的aligned填充，V3本合同窗口不把填充当真实交易；复用数值须同时复用窗口质量，否则重算并标新合同。
- `tradable=true`目前只表示有本地bar，不证明交易所交易状态或可成交。上市首条bar也不等于已验证上市日期；ST/停复牌/涨跌停规则依赖M8C的独立能力，未验证不编造。

### 5.2 额量与换手率

- 成交额 `A=raw_amount`，单位元；成交量 `V=raw_volume`，单位按本地解码验收锁定为股。展示“万元/亿元”只能转换显示；量比不是换手率。
- `A/V`仅作RAW日成交均价与日内价格范围的容差诊断，不充当分钟VWAP、资金净流入或主力成本。原始额为浮点来源，须声明容差，不能直接做分毫无差的断言。
- 换手率若未来开放，须注明总股本/流通/自由流通分母、股数单位、生效日期与来源。项目当前目标口径可定义 `V/流通股数`，但不得无标签混用总股本换手率；当前不启用，也不推断“本地一定永远无法计算”。上交所统计本身区分不同股本口径，故分母必须显式。[上交所指标说明](https://www.sse.com.cn/aboutus/publication/monthly/explain/)
- 日线足以计算金额比、收盘位置、趋势和回撤；不需要为这些能力等分时或在线换手率。

### 5.3 统计全集与时间可得性

今日沿用正式正常universe及其样本最小数100，不为了捕捉低位股偷偷修改股票全集。当前正常门包含至少120个原始bar、当日实际bar和20日覆盖要求；新股/复牌观察作为明确的范围外信息，不混正式排名。

`RPS_N=同日有效收益升序平均秩/N`，单位(0,1]；`RS_N=RET_N-同日正常全集有效RET_N中位数`。减去同一中位数不改变排名。UI的99是0.99的百分制展示，不能与0.75阈值混算。

跨日RPS比较必须记录两日统计全集、各N有效数；数量变化≤0.10、交并比≥0.90才比较；不满足时变化字段UNKNOWN。现有股票变化值并未完整证明这些门已生效，本期须接入。历史parquet的 `universe_asof_date` 为当前cutoff，不能拿当前标签当历史股票全集。

## 6. 数据可得性与能力分层

| 输入/能力 | 当前证据 | 本期处理 |
|---|---|---|
| RAW/调整OHLC、额量、实际bar | parquet字段及9月14日覆盖已核查 | 接入P05，补齐OHLC，做逐场景窗口质量 |
| MA/收益/OLS/波动/RPS | 因子库、M8与P05已有 | 复用可执行公式与绑定，禁止同名异义 |
| 今日行业/概念/层级关系 | 当前关系及publication绑定存在 | 用于今日共同支持；STYLE仅作为背景 |
| 个股历史价格状态 | 长日线可以受控重算 | 不必等积累20个研究run才计算MA/回踩事件 |
| 历史成员、历史universe、源事件可得性 | 最新依赖声明历史成员不可用 | 只能诊断重构；真实PIT能力逐项开启 |
| 历史派生run | 2个交易日，不足t与t-3 | 可从合格输入重算；不能伪造当时发布过 |
| 当日行情涨幅/精确涨停 | RAW前收/除权参考需独立确认 | 技术收益与报价涨幅分列；规则未知不贴精确涨停标签 |
| 流通股本/换手率 | 本轮未验证可靠时点分母 | OFF，不阻断收盘研究 |
| M10板块金额A | 字段和合同存在，但专项未独立关闭 | 受影响POTENTIAL分支按能力降级；股票金额比不依赖M10 |

每个能力输出 `capability_status, missing_inputs, available_sessions, required_sessions, history_basis`。不要用单一READY掩盖POTENTIAL历史缺口。零候选也可完整READY；有候选也可只有局部能力。

## 7. 因子字典与精确公式

所有比值要求有限数及正分母；log要求正价；任何必要观察缺失返回NULL。NaN/Inf入库转SQL NULL，JSON禁止非有限数。公式比较使用原精度；源QFQ已有分位舍入不另行补精度。全部参数含闭开区间与单位进入canonical参数哈希。

### 7.1 已有因子对齐

| 字段 | 新合同中的精确定义 | 复用边界 |
|---|---|---|
| RET_N_ADJ | `C[t]/C[t-N]-1` | N+1连续真实bar；用于技术变化 |
| MA_N | `mean(C[t-N+1:t])` | N真实bar；新增MA10可由同一算子计算 |
| BIAS20 | `C/MA20-1` | 与既有同义 |
| SLOPE20 / R2_20 | x=0..19、y=ln(C)；β=Σ(x-x̄)(y-ȳ)/Σ(x-x̄)²；R²=1-SSE/SST | SST=0→NULL；回踩用截至t-1趋势，不用回踩日抬趋势 |
| POS_N_HL | `(C-min(L[t-N+1:t]))/(max(H[t-N+1:t])-min(L[t-N+1:t]))` | 不能与收盘极差混称 |
| DIST_HIGH_N_HL | `C/max(H[t-N+1:t])-1` | 含t；新breakout用不含t版本 |
| MDD_N_CLOSE | `min_j(C[j]/running_max(C)[j]-1)` | 非正，绝非当前回撤幅度的同名替代 |
| SIGMA20_V3 | `std(log(C[j]/C[j-1]), j=t-19..t, ddof=0)` | 保留现有extension风险语义 |
| EXTENSION_Z20 | `ln(C/MA20)/(SIGMA20_V3*sqrt(20))` | sigma=0→NULL；不能解释成正态概率 |
| VOL20_SAMPLE | 同20收益、`ddof=1` | V1字段；不代替SIGMA20_V3 |
| RANGE_N_CLOSE | `max(C[t-N+1:t])/min(C[t-N+1:t])-1` | 现有range5/range20是这个口径 |
| RETURN_CONCENTRATION20 | `max(max(RET1_ADJ,0))/sum(max(RET1_ADJ,0))`，20收益 | 无正收益→NULL；仅诊断，不阻断全部评分 |

`ddof`不同会改变标准差分母，需显式指定，不能依赖库默认值。[pandas标准差文档](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.core.window.rolling.Rolling.std.html)

### 7.2 新增价格与额量事实

```text
PHC20 = max(C[t-20:t-1])                 # 既有收盘平台
PHH20 = max(H[t-20:t-1])                 # 新增最高价平台
BREAK_MARGIN_CLOSE20 = C[t]/PHC20 - 1
BREAK_MARGIN_HIGH20  = C[t]/PHH20 - 1
BREAK_HIGH20 = C[t] > PHH20
INTRADAY_REJECT_HIGH20 = H[t] > PHH20 AND C[t] <= PHH20
CLV = (C[t]-L[t])/(H[t]-L[t])            # H=L -> NULL，不能补成1
BODY_RET_RAW = C_raw[t]/O_raw[t]-1       # 当日实体百分比，独立标RAW
RECLAIM_MAk = C[t-1]<=MAk[t-1] AND C[t]>MAk[t], k=5,20
TOUCH_RECLAIM10 = L[t]<=1.01*MA10[t-1] AND C[t]>=MA10[t-1]

AMR5_MEAN_PRIOR = A[t]/mean(A[t-5:t-1])
AMR20_MEAN_PRIOR = A[t]/mean(A[t-20:t-1]) # 既有amount_vs_prior20
AMR20_MEDIAN_PRIOR = A[t]/median(A[t-20:t-1]) # 另名诊断，不替换均值
PB_AMR3_5_DIAGNOSTIC = mean(A[t-2:t])/mean(A[t-7:t-3]) # 仅旧口径对照
LIQ20_AMOUNT = median(A[t-20:t-1])
LIQ20 = LIQ20_AMOUNT >= 20_000_000
VR20_MEAN_PRIOR = V[t]/mean(V[t-20:t-1]) # 辅助；股本变化会影响跨日量比

RET3_ADJ = C[t]/C[t-3]-1
ACCEL_LOG5_20 = ln(C[t]/C[t-5])/5 - ln(C[t]/C[t-20])/20
```

PB_AMR3_5_DIAGNOSTIC含确认日t，不再用于回踩资格或评分。回踩收缩和确认日成交额分开，按§9.2的真实事件区间计算。ACCEL替代原简单收益线性年段缩放；仅诊断。旧AMOUNT_RATIO20的分母包含t，保持旧合同，四类触发统一用prior均值。

不将同日摸过前高但收回称为“已证明假突破”；命名为日内越高回落事实。后续失败必须对**信号日冻结的平台价**判断，不能每日滚动平台使原信号永远不失效。纯日K线不能证明同一天先摸低再拉高的时序。

### 7.3 单日风险标准化

```text
LOGRET1 = ln(C[t]/C[t-1])
SIGMA20_PRIOR = std(ln(C[j]/C[j-1]), j=t-20..t-1, ddof=0) # 需22个收盘
DROP_FLOOR_PCT = 0.04                  # 首轮候选，不是交易所制度
DROP_CAP_PCT = 0.08                    # 绝对跌幅保护上限，首轮候选
DROP_Z = 2.0
RELATIVE_DROP_LIMIT_LOG = max(-ln(1-DROP_FLOOR_PCT), DROP_Z*SIGMA20_PRIOR)
ABSOLUTE_SEVERE_DROP = RET1_ADJ <= -DROP_CAP_PCT
RELATIVE_SEVERE_DROP = LOGRET1 <= -RELATIVE_DROP_LIMIT_LOG
SEVERE_DROP = ABSOLUTE_SEVERE_DROP OR RELATIVE_SEVERE_DROP # 三值OR
FIRST_DAY_DAMAGE = C[t]/MA20[t] < 0.97
WEAK_CLOSE = CLV < 0.30
HEAVY_WEAK = WEAK_CLOSE AND AMR20_MEAN_PRIOR>=1.50 AND RET1_ADJ<0
```

保留prior波动、不让当日冲击抬自身分母；新增绝对保护，避免高历史波动无限提高风险标记门槛。当全部输入已知时等价于 `LOGRET1<=-min(-ln(1-DROP_CAP_PCT), RELATIVE_DROP_LIMIT_LOG)`。参数约束 `0<floor<=cap<1, Z>0`。sigma=0使用4%底线；sigma未知仍为UNKNOWN，但绝对跌幅已过8%时OR可明确TRUE，不因未知波动隐藏风险。4%/8%/2倍仅为本次冻结候选，P12-02按预登记分组检查分布，不宣称已校准。

线上审计指出风险函数存在无上界问题成立，但“因此大跌进入四类”不成立：v2.0启动/修复/延续要求正收益，回踩要求C[t]>=C[t-1]。本次修正保护的是公共风险语义、观察状态与未来复用，而不是声称已发现真实大跌入选事故。非正收益和异常跌幅标签仍是不同事实。不同市场/波动组分别报告，不把8%解释成10/20/30涨跌停制度。

报价 `quote_ret1` 仅展示项目正式RAW前收/除权参考口径；不得拿RAW除权缺口当结构暴跌。上述技术收益标明ADJ，不冒充行情软件涨幅。

## 8. 三值准入、否决与板块支持矩阵

三值AND：有已知false→false；无false且有未知→UNKNOWN；全部true→true。OR：有true→true；无true且有未知→UNKNOWN；其余false。NOT UNKNOWN仍UNKNOWN。不能用SQL `!=TRUE` 或Python真假值代替三值逻辑。

按股票×场景计算必需字段，记录 `known_failed_checks` 与 `unknown_checks`；两者可以同时存在。有已知失败时资格false，但仍说明缺哪些证据。数据可评质量与资格结果分开，不能“任何NULL都改整个结果UNKNOWN”。

```text
COMMON_GATE = 正常universe AND 当日完整实际bar AND 该场景窗口有效
              AND LIQ20 is TRUE AND 全部输入身份相容
SAFETY_PASS = STRUCTURE_BREAK is FALSE AND EXTENDED is FALSE
              AND FIRST_DAY_DAMAGE is FALSE AND SEVERE_DROP is FALSE
```

EXTENDED继承既有AND定义。四类一律要求SAFETY_PASS；严重大跌不再给回踩例外。高RPS、板块龙头或额量分不得抵消以上失败。结构风险/过热证据未知，不准入今日重点，但可显示数据不足。

板块不是四类共同的数据门。先独立计算场景，再对该股所有真实行业/概念关联计算支持，避免“只要存在一个弱概念就否决全部”或“随便找一个热门标签就加分”。

| 场景 | 至少一条有效CURRENT/POTENTIAL且LOO通过 | 支持均未确认/历史未知/无关系 | 关系数据完整且所有可用关联均明确W |
|---|---|---|---|
| 启动/回踩/修复 | `SUPPORTED`分组，显示具体轨道 | `INDEPENDENT`分组，板块支持状态如实为UNKNOWN或NOT_CONFIRMED | 个股触发保存，转风险观察，不进今日重点 |
| 强势延续 | 只接受CURRENT+LOO TRUE | 不入重点；保留趋势观察 | 风险观察 |

“个股独立”是输出模式，不是把UNKNOWN改成已确认“不弱”。支持分组不靠“缺历史例外OR”进入资格公式。某一明确弱板块与其它支持板块并存时，保留风险说明及支持来源，不一票否决全部。

W当日已知弱与FADING从强转弱分开。`CURRENT=false`仅表示未过严格当前门，不自动表示退潮。INDEPENDENT与SUPPORTED分组各有数量和质量，不重分配缺失板块评分权重。

## 9. 四类场景与蓄势观察的首轮执行合同

本节阈值均纳入 `parameters-v3_3-candidate-01`；没有通过历史/真实日验证前不得称正式最优值。所有场景公共要求第8节COMMON_GATE、SAFETY_PASS，以及对应板块矩阵。公式中的趋势/rps窗口均从第5–7节获取，禁止从页面推断。

### 9.1 启动确认

```text
LAUNCH = BREAKOUT_V3 is TRUE            # 明确消费现有收盘平台突破事实
         AND C[t]>PHC20
         AND RET1_ADJ>0
         AND CLV>=0.60
         AND AMR20_MEAN_PRIOR>=1.20
         AND INTRADAY_REJECT_HIGH20 is FALSE
```

类型标签：若 `C>PHH20` 为 `HIGH_PLATFORM_BREAK`，否则为 `CLOSE_PLATFORM_BREAK`，不能把后者叫最高价突破。`BREAKOUT_V3`的数值合同须固定为当前stock_attention版本，未来调整时同步新版本。

不要求历史RPS≥70，不要求所属板块必为CURRENT，避免“低位相对转强必须先涨成历史强股”的循环。RPS变化仅在本场景评分，不可评分时保留QUALIFIED_UNRANKED。

新触发标志必须比较t-1同合同是否命中；未知则 `FIRST_OBSERVED`，不能写“首次突破”。连续突破仍属该类但新鲜度递减。H=L时CLV未知，转 `ONE_PRICE_BAR_WATCH`，不伪造日内承接或精确涨停。

### 9.2 强势回踩：先强势事件，再冻结峰值与回调

采用逐主日历日推进的 `PULLBACK_EPISODE_V1`，不在看到t的收复后遍历多个锚点挑选最容易通过者。每股同版本同时最多1个活动事件；事件上限20个会话、回调上限10个会话，为有界候选参数。

1. `IDLE`：日a的 `STRONG_SEED = TREND_BACKGROUND OR (RPS20>=0.75 AND C>=MA20)` 明确TRUE且STRUCTURE_BREAK明确FALSE，建立事件，保存seed证据；峰值暂为H[a]，h=a。无需事后最高价日也满足强势。若从历史窗口左边开始就强势、无法恢复前态，标LEFT_CENSORED，仅观察，不捏造事件起点。
2. `ADVANCING`：从a+1逐日处理。若H[d]>=暂存峰值，更新峰值并列取最近h=d；该日即使长上影回落也不同时认定峰后回调，避免日K线臆断时序。否则，首次C[d]<C[d-1]且C[d]<峰值日收盘时，转`PULLING_BACK`，冻结h、H_peak、峰值日收盘，p=h+1为回调区间起点。H_peak可能来自seed之后不再满足强势标签的上影日，允许保留，只要未触发结构终止。
3. `PULLING_BACK`：从h+1累计真实bar；已知STRUCTURE_BREAK或C/MA20<0.97即`INVALIDATED`，当日不重建事件。缺必要bar/状态则`DATA_GAP`，不越过未知恢复确认。若再次H>=H_peak则旧回调`RESET_NEW_HIGH`，次日以后才可凭新seed建新事件，不能静默抬峰值。达到事件20/回调10会话上限后为`EXPIRED`。所有状态按日保存/受控重算，窗口起始必须是已知IDLE或可恢复状态；否则降级。
4. 对仍活动的事件，t必须在h之后至少两会话，且此前已检测到回调；回调期 `[p,t-1]` 不含确认日，至少1条实际bar。首个完整满足下式的t才将事件置为`CONFIRMED`。同一事件以后不反复产生新的回踩确认；观察后续失效，只有新的seed事件才能再确认。

同一日处理优先级固定：缺必要数据→DATA_GAP；已知结构损坏→INVALIDATED；峰值重置→RESET_NEW_HIGH；超窗口→EXPIRED；最后评估确认。缺数据时仍保留已知损坏原因；所有情况均不准入。a/h/p的日期和源价身份封存；跨日比较将参考值转换至当前锚，原证据不覆写。

事件长度为a至当前日含首尾的会话数，回调长度为p至当前日含首尾的会话数；>20或>10才超限。CONFIRMED/INVALIDATED/RESET_NEW_HIGH/EXPIRED为终态，下个会话回到IDLE，允许新seed但不在终止当日重开。DATA_GAP/LEFT_CENSORED不可直接用新强势续上旧事件：须恢复足够历史重算，或观察到一个完整可判定的STRONG_SEED=FALSE日后进入IDLE，再等待之后的新seed。这个定义是有界研究事件，不声称已识别全部经济趋势起点。

```text
PRE_PULLBACK_AMOUNT = mean(A[h-4:h])     # 冻结的峰值前5会话，含峰值日
PULLBACK_AMOUNT = mean(A[p:t-1])         # 峰后至确认前，全部会话，不挑下跌日
PULLBACK_CONTRACTION = PULLBACK_AMOUNT/PRE_PULLBACK_AMOUNT
CONFIRM_AMOUNT_RATIO = A[t]/PULLBACK_AMOUNT
DEPTH = 1 - C[t]/H_peak
CONTROLLED = 0.03<=DEPTH<=0.12
             AND min(C[j]/MA20[j], j=p..t)>=0.97
             AND SLOPE20[t-1]>0 AND R2_20[t-1]>=0.40
CONFIRM_TODAY = C[t]>=C[t-1] AND CLV>=0.55
                AND (RECLAIM_MA5 is TRUE OR TOUCH_RECLAIM10 is TRUE)
PULLBACK = active_episode is PULLING_BACK AND C[t-1]<C[h]
           AND CONTROLLED AND PULLBACK_CONTRACTION<=0.85
           AND CONFIRM_AMOUNT_RATIO>=1.00
           AND CONFIRM_TODAY AND INTRADAY_REJECT_HIGH20 is FALSE
```

确认日成交额至少达到回调期均值，是显式新候选门；金额极端放大只记录AMR/风险事实，不凭空假设越大越好。回调期和参考期任何必要数据缺失不压缩窗口。峰前5日可能包含seed之前日期，准确称峰前金额基准，不冒称全部是强势期；记录两窗口及数量。回调1日可计算但标SHORT_PULLBACK_SAMPLE，必须独立报告此类分布。例如峰前均额100、两日回调各60、确认额120，收缩比0.60、确认比2.00，不能因确认日放量否决缩量证据。

如同时存在更早已失效事件和近期有效事件，仅顺序状态机定义的活动事件可用于确认，不回退挑旧事件。历史锚选择、窗口超时、左截断、同日重跑和跨日换锚都须人工事件轨迹验收。缺PIT时可对当前源作诊断重构，但必须保留重构标志。

门较严格是可审计的第一版，不保证最优。单日回落后未收回、只有缩量没有止跌、持续沿低点下行，均 `PULLBACK_UNCONFIRMED`。同日高低价不证明时序；说明应写“最低价触及此前MA10附近、收盘收复”，不能写盘中先回踩再拉升。

### 9.3 修复转强：拆开MA5与MA20分支

```text
R5 = RECOVERY_V3 is TRUE AND RECLAIM_MA5 is TRUE
R20 = RECLAIM_MA20 is TRUE
       AND count(C[j]<MA20[j], j=t-5..t-1)>=2
       AND MA20[t]>=MA20[t-3]
RECOVERY_TURN = (R5 OR R20)
                AND RET1_ADJ>0 AND CLV>=0.55
                AND RPS5_DELTA3>0
                AND AMR20_MEAN_PRIOR>=1.05
                AND C[t]>=0.98*MA20[t]
```

R20是真正新增分支，不被旧RECOVERY的MA5上穿前置门否决。两分支命中均保留；收复位置分别记录。MA20仍下行的上穿只进 `RECOVERY_UNCONFIRMED`，避免单一MA5动作被称为趋势修复。板块RECOVERY_BUILD是支持说明，不是股票修复成立的必要条件。

### 9.4 强势延续：背景必须加当天事件

```text
CONTINUE_BACKGROUND = TREND_BACKGROUND is TRUE
                       AND C[t]>=MA5[t]>=MA20[t]
                       AND SLOPE20[t]>0 AND RPS20[t]>=0.70
CONTINUE_EVENT = RET1_ADJ>0 AND C[t]>H[t-1]
                 AND CLV>=0.55 AND 0.80<=AMR20_MEAN_PRIOR<=2.50
TREND_CONTINUE_STOCK_ONLY = COMMON_GATE AND SAFETY_PASS
                            AND CONTINUE_BACKGROUND AND CONTINUE_EVENT
TREND_CONTINUE_SUPPORTED = TREND_CONTINUE_STOCK_ONLY
                           AND CURRENT_WITH_LOO_BREADTH_SUPPORT is TRUE
TREND_CONTINUE = TREND_CONTINUE_SUPPORTED
```

没有当日事件只保留TREND_BACKGROUND观察，不因为每天仍站MA20就常驻今日重点。高位扩张依然否决；不同类别可重叠，唯一主类别在第12节处理。价格突破昨日高点不要求突破20日平台，故不与启动完全重复。

保留STOCK_ONLY的全量真假/未知及后续描述性结果，作为SUPPORTED的同日影子对照，不新增首页重点类别，也不因未过板块门删掉对照样本。板块硬门是待验证的研究取舍，不是已证明必要条件；首次上线仍保持，是否取消需独立消融和新版本，不在本次凭讨论放松。按原股票事件跟踪，不能因唯一主类别变成启动而遗漏延续对照。

### 9.5 蓄势观察与失效条件

SETUP成立且COMMON_GATE/SAFETY_PASS成立、尚未命中确认场景→SETUP_WATCH，展示 `waiting_for=[C>冻结PHC20, AMR20_MEAN_PRIOR>=1.20, CLV>=0.60]` 的未满足项。RPS上升、MA收敛不能自行变为启动确认。

失效分两层：当日eligibility每天重算；已封存episode按冻结参考追踪。启动跌回信号日平台、回踩跌破事件期间0.97×MA20规则、修复再次跌回被收复均线、延续丢失CURRENT/LOO都记原因。均线规则需声明后续使用同日MA还是信号日固定MA；本版修复使用后续同日对应MA，平台固定。参考价在后续调整锚变化时必须转换至同基准或用信号锚重算，不能混价。

## 10. 板块轨道与剔除目标股后的成员支持

复用CURRENT/POTENTIAL/W事实合同及正常行业/概念类型，不新造板块总榜。当前CURRENT阈值继承配置：成员≥5、板块报价覆盖≥0.70、市场报价覆盖≥0.90、同类横截面覆盖≥0.70；M1>0、B1≥0.60、REL1≥0.003、P1≥0.80、上涨成员≥3、最大正收益贡献占比≤0.50。此处列出供对账，不重新调参。

### 10.1 今日LOO

对每个股s、真实板块g，先去重成员，`O=members(g)\{s}`，分母包括应观察的其他成员；V为其中有效实际bar且RET1已知者。

```text
coverage_LOO = |V|/|O|
B1_LOO = count(RET1_i>0, i∈V)/|V|
M1_LOO = median(RET1_i, i∈V)
CURRENT_WITH_LOO_BREADTH_g_s = CURRENT_g is TRUE
              AND |V|>=5 AND coverage_LOO>=0.70
              AND B1_LOO>=0.55 AND M1_LOO>0
```

样本不足和覆盖不足记录数据原因，不补false后写“明确无支持”。真实充分数据且宽度不达门才为false。板块5个成员即使CURRENT过门，剔除后最多4个，不可获本版LOO支持，须展示这一明确限制。

### 10.2 EARLY及跨日LOO

早期计数要求其他成员SETUP/RECOVERY两字段可评，用三值OR；记录信号可评覆盖≥0.70、有效其他成员≥5、已知命中≥2。还需POTENTIAL成立以及 `B_DELTA3_LOO>=0.05 OR MA20_WIDTH_DELTA3_LOO>=0.05`，使用三值OR，不能择首个非空字段。

两日共同成员 `J=(members_t ∩ members_t-3)\{s}`；在各指标的两日都有效的成员交集上做差。有效数≥5，覆盖分母取两日剔除s后成员总数的较大值，覆盖≥0.70。`B_DELTA3_LOO`是同一J的上涨比例之差；MA宽度用同基准 `C_adj>MA20_adj`，不拿收益比价格。每个指标记录实际J哈希。未知历史成员则UNKNOWN，不能拿全板块变化冒充LOO。

LOO证明“其他成员也支持”的统计事实，不证明因果。CURRENT/POTENTIAL背景本身仍包含目标股，输出应清楚写“板块轨道成立且其他成员共同支持”，不声称整个轨道是在去掉目标股后重新全市场排名得出。若要更严格的全轨道LOO，须另立合同和成本预算。

### 10.3 弱与退潮

`W_NOW=(M1<0 AND B1<0.35)`；`W_HISTORY=(M1<0 AND B_DELTA3<=-0.20)`，总W按既有三值OR。历史退潮定义为前一会话CURRENT TRUE、当前CURRENT FALSE、且 `(B_DELTA3<=-0.20 OR MA20_WIDTH_DELTA3<=-0.15)`；缺证据UNKNOWN。非CURRENT不等于W，W_NOW不需要等20天历史。

`CURRENT_WITH_LOO_BREADTH_SUPPORT`为§10.4预先冻结关系集合上 `CURRENT_WITH_LOO_BREADTH_g_s` 的三值OR；早期对应 `POTENTIAL_WITH_LOO_MEMBER_IMPROVEMENT_SUPPORT`。只有某条关联明确TRUE才进入SUPPORTED。不存在关系时为NOT_CONFIRMED，不伪造一个板块；存在关系但所有支持状态未知时为UNKNOWN。DTO、原因码、UI和合同统一用这些名字；旧LOO字段只能由带版本适配层读取，不能升级含义。

首版明确 `support_method=TRACK_PLUS_LOO_MEMBERS_V1`，`full_track_recomputed_without_target=false`。不新增Full LOO必要门，包括延续场景；这不是因为断言本地算不起，而是Full LOO改变研究假设且涉及目标股从重叠板块、市场参照与同类P1排名中如何剔除的新合同，当前未证实有必要。保留全轨道重算作为后续消融候选；本版绝不显示“剔除该股后整个CURRENT仍成立”或“完整反循环证明”。

按支持成立、支持轨道（CURRENT优先，其后POTENTIAL）、固定类型次序INDUSTRY/THEME、相应有效板块rank、sector_id稳定选择1主+2备；行业与概念rank不当作同一排名直接比较，类型次序仅作关联兜底，不作为资格优先。保存全量支持关系，详情可查看，不能用备选板块绕过首页分散约束。

### 10.4 多关系机会数与支持偏差

在读取板块当日强弱前冻结 `eligible_relationship_set`：publication绑定的真实有效行业/概念边、按(security_id,sector_id)去重、类型和属性可用、剔除STYLE/已失效边；成员样本/数据覆盖在之后的评估中标UNKNOWN，不能因为没过门从tested分母里删除。不能根据结果只保留热点关系或推造“主概念”。历史重构的关系模式继承§14，不变成历史事实。

每股保存 `relationship_set_hash, sector_relations_tested, evaluable_relations_count, unknown_relations_count, supported_relations_count, industry_relations_count, theme_relations_count, industry_support, theme_support`；支持分别列 `INDUSTRY_ONLY/THEME_ONLY/BOTH/NONE/UNKNOWN` 的实际组合证据。计数为唯一sector_id数，无重复边奖励。无关系、全部失败、部分未知按三值语义区分。

首版保留ANY真实关联确认支持，不直接实施“行业优于主概念优于普通概念”的新资格门：当前没有独立可靠的主概念归属合同，类型偏好也无效果证据。支持数量不加股票分，也不逐概念额外占名额，但这**不能消除**多关系获得SUPPORTED及预览优先的机会偏差。必须按关系数1–2/3–5/6以上分层，比较可评覆盖、支持占比和前瞻分布，并在同日期、相近关系数/流动性/股票触发的样本内对照；同时比较行业only、概念only与ANY。样本不足保持偏差待验，不将ANY称为统计显著共振。

## 11. 评分：所有子项可复算，缺项不奖励

评分只排序，不授予资格。第一版只对股票事实评分，板块支持另作显式分组和证据；取消原“未知不加分但同时重分配权重”的矛盾。SUPPORTED与INDEPENDENT内分别展示类内名次，不能把两者分数解释成机会大小差异。

定义 `u(x;a,b)=clip((x-a)/(b-a),0,1)`、`c(x;m,w)=max(0,1-|x-m|/w)`；要求b>a、w>0。子项范围[0,1]。下表权重均和为1，最终 `score=100×Σw_i*x_i`。必需评分字段未知→`score=NULL, rank=NULL, QUALIFIED_UNRANKED`，该股保留全量合格结果和独立未评分区，不补0、不按剩余项重分配。

| 场景 | 子项/精确公式 | 权重 |
|---|---|---:|
| 启动 | `c(BREAK_MARGIN_CLOSE20;0.02,0.06)` | .25 |
| 启动 | `u(CLV;0.60,0.90)` | .25 |
| 启动 | `c(AMR20_MEAN_PRIOR;1.80,1.20)` | .20 |
| 启动 | `u(RPS5_DELTA3;0,0.15)` | .20 |
| 启动 | Freshness | .10 |
| 回踩 | `u(SLOPE20[t-1];0,0.015)*u(R2_20[t-1];0.40,0.80)` | .20 |
| 回踩 | `c(DEPTH;0.06,0.06)` | .20 |
| 回踩 | `c(PULLBACK_CONTRACTION;0.65,0.35)` | .20 |
| 回踩 | `u(CLV;0.55,0.90)` | .20 |
| 回踩 | `c(C[t]/MA10[t-1]-1;0.01,0.06)` | .10 |
| 回踩 | Freshness | .10 |
| 修复 | `u(CLV;0.55,0.90)` | .30 |
| 修复 | `u(RPS5_DELTA3;0,0.15)` | .25 |
| 修复 | `c(AMR20_MEAN_PRIOR;1.50,1.00)` | .20 |
| 修复 | `c(C[t]/MA20[t]-1;0.01,0.06)` | .15 |
| 修复 | Freshness | .10 |
| 延续 | `u(SLOPE20[t];0,0.015)*u(R2_20[t];0.40,0.80)` | .25 |
| 延续 | `u(CLV;0.55,0.90)` | .25 |
| 延续 | `c(AMR20_MEAN_PRIOR;1.20,1.30)` | .20 |
| 延续 | `u(RPS20;0.70,0.95)` | .10 |
| 延续 | `c(BIAS20;0.04,0.10)` | .10 |
| 延续 | Freshness | .10 |

Freshness：同合同、同模式、连续可判定场景命中年龄为age时，`max(0.20,1-0.15*(age-1))`；已知前日未命中方可age=1。窗口左侧截断或历史未知时，Freshness采用显式保守值0.20并标 `AGE_LEFT_CENSORED`，age保持NULL/下界，不伪称首日；这一固定惩罚是公开合同规则，不是通用缺值补零。

取消原“扣20～30、15～25”的不可执行风险区间。已知硬风险只否决；额量过热等通过有界center反映；其他未标定诊断风险只展示、无暗中扣分。本版不将ACCEL、集中度、量比叠成重复加分，避免把同一涨幅/成交额重复计权。后续新增风险扣分须新参数版本与消融证据。

### 11.1 首版参数冻结与简单排序对照

本轮不再微调既有CLV、RPS、center/width及权重；上表作为唯一固定候选排序，不并行搜索所有组合。参数分为已继承合同、风险/事件新增候选、评分候选三组，逐项登记来源和改变影响。P12-02先验证事实、事件与风险，评分不得掩盖资格错误。

新增唯一简单影子排序基线：在相同主类别/支持模式内，`CLV降序 → LIQ20_AMOUNT降序 → security_id升序`，资格、样本和预览数量完全相同，不改变首页正式排序。P12-04对照名单稳定性和解释完整性，P12-05/08再检验复杂评分增量；没有证据不宣称复杂分数更有效。

首轮开发阶段最多登记3套完整候选参数（含本基线配置），每套相对前套只改变一个参数组；只在开发段比较，保留所有尝试和拒绝原因。到上限后冻结，不通过新命名绕过试验预算。锁定评估段失败不得继续用同段调参后重称独立验收；新版本需新的预登记观察。Full LOO、流动性分位和主概念优先均不加入首轮网格搜索。

## 12. 排名、去重、完整性与展示分散

1. 先计算全量股票×场景资格，保存所有命中；不得从V1候选、CURRENT_FOCUS/EARLY_FOCUS、每板块预览5只开始扫描。
2. 股票主类别固定 `LAUNCH_CONFIRM > RECOVERY_TURN > STRONG_PULLBACK > TREND_CONTINUE`，其余为次级标签。不是哪类分数最高就归哪类；各分数不跨类可比。接口保留 `matched_categories`，分类筛选可检索次级命中但总计数按唯一股票去重。
3. 每个主类别×支持模式内：有分者按score降序、可用age升序（未知最后）、LIQ20_AMOUNT降序、security_id升序稳定排序。质量缺口单列，不以通用READY标记掩盖特定轨道缺失。
4. **全量合格结果不设20只或每板块3只的资格上限。** 首页预览每类默认5只，展开每类20行分页，所有合格对象可检索；页面数量等于全量结果，不等于预览名额。
5. 首页合并预览采用四类轮询，各类内SUPPORTED有分→INDEPENDENT有分→未评分观察入口；每轮每类最多1只，总计20只。显示这是展示顺序，不是全市场统一机会排名；某类为空不放松门槛凑数。
6. 主板块展示上限沿用现配置10，单独存preview参数；不可把刚修复的3只硬限引入资格层。同一板块6只合格必须全量可见。需要分散时仅影响预览，排除原因标 `PREVIEW_DIVERSITY_LIMIT`，不写成失效或落选。
7. 对高重叠概念先展示集中度与共同成员比例，本版不暗中聚类改排名；若后续引入Jaccard聚类须独立合同。所有支持板块真实保存，不更换主板块规避上限。

## 13. 研究状态、解释与输出合同

状态变化需要同publication修订策略、前一交易日同算法/参数结果和同历史模式。年龄按各场景本身是否命中计算，先于唯一主类别选择；主类别变化不自动把连续次级命中重置为首日。算法/参数变更标 `VERSION_RESET`，首次接入标 `FIRST_OBSERVED`，缺日标 `HISTORY_GAP`，都不能计为自然NEW。重复构建同一天不增加age。

`NEW`仅指前日该类可判定且false、今日true；`RETAINED`为连续true；`UPGRADED/DOWNGRADED`须指定从观察/独立到确认支持的迁移，不把类别编号大小当等级；`REMOVED`须原因是资格失效，展示额度排除另标。市场假日不算缺日；在途尚未完成的run不作为前态。

输出最小结构：

```yaml
security_id: string
trade_date: date
mode: LOCAL_CLOSE_ONLY
primary_category: LAUNCH_CONFIRM|STRONG_PULLBACK|RECOVERY_TURN|TREND_CONTINUE|null
matched_categories: array
eligibility_by_category: object # TRUE/FALSE/UNKNOWN
known_failed_checks: array
unknown_checks: array
selection_mode: SUPPORTED|INDEPENDENT|OBSERVATION
sector_support_status: CONFIRMED|NOT_CONFIRMED|WEAK|UNKNOWN
quality_by_capability: object
category_score: number|null
category_rank: integer|null
score_components: array
primary_sector_id: string|null
alternative_sector_ids: array
signal_date: date|null
first_observed_date: date
signal_age: integer|null
age_lower_bound: integer|null
history_basis: PIT_CAPTURED|PIT_RECOMPUTED|RECONSTRUCTED_CURRENT_MEMBERSHIP
previous_state: string|null
change_reason: string
reason_codes: array
risk_codes: array
waiting_for: array
invalid_if: array
checks: array # factor/version/observed/operator/threshold/unit/window/price_basis/as_of/source_ref
episode_reference: object # 平台/回踩h/收复均线/价格锚
pullback_episode: object # a/h/p/state/H_peak/参考额窗口/回调额窗口/左截断/前态
stock_only_eligibility: object # 含延续影子对照，先于主类别去重
relationship_support_audit: object # tested/evaluable/unknown/supported/industry/theme/hash
support_method: TRACK_PLUS_LOO_MEMBERS_V1
full_track_recomputed_without_target: false
dependency_lock_hash: string
publication_id: string
snapshot_id: string
membership_snapshot_id: string
research_run_id: string
calendar_id: string
universe_hash: string
input_digests: object
algorithm_version: string
parameter_hash: string
generated_at: timestamp
```

前台解释必须从checks生成，不能再维护一套不同的中文阈值。示例：“前期强势后回撤6%；峰后至昨日的平均金额为峰前5日的0.72倍；今天成交额为回调均额1.3倍，收盘不低于昨日并收复MA5；板块历史支持未知，因此列为个股独立回踩。”等待条件列尚未满足的确认项；入选对象可等待板块确认，但不能等待它已必须满足的股票准入项。

总览分别列：输入股票数、可评数、合格唯一股票数、各类命中数、已评分数、未评分数、观察数、未知数、预览数；同股多个未知原因不反复加计。空态区分 `EMPTY_EVALUATED / PARTIAL_EVALUATION / NOT_BUILT / BUILD_FAILED / STALE`。

## 14. 历史重算与能力开放

不能机械规定“3个run允许3日变化、5个run允许启动、20个run才能退潮”。t与t-3需要至少4个对应日状态，且每个状态还要技术预热；先前10日CURRENT加今天需11日状态。真实日期必须来自主日历，缺日不以第3条记录替代。

依赖规划器从因子DAG推导最早日期：LAUNCH的prior20至少21个bar；单日风险需22个；RPS5_DELTA3需覆盖t-8至t且两日横截面有效；回踩事件必须有可恢复前态或已知IDLE，最长20会话事件叠加seed时RPS20至少需向前约40会话的价格，并额外加载峰前5日金额与均线预热，再叠加正常universe120原始bar条件。具体最早日由DAG计算，约40日不代替精确规划。禁止只取[t-10,t-2]最高价作为事件历史；左截断保持观察。既有high100诊断不应无意阻断只用20日的场景，除非明确列为必需。

三种历史模式严格隔离：

| 模式 | 用途 | 可否作为当时已发布事实 |
|---|---|---|
| PIT_CAPTURED | 真正封存的当日输入、成员、参数与信号 | 可以，须可验证发布时间与身份 |
| PIT_RECOMPUTED | 使用当时可得原始源、事件/成员/universe，在t截止重算 | 是时点重算，不能宣称当时实际发布过 |
| RECONSTRUCTED_CURRENT_MEMBERSHIP | 以当前关系/当前可见源诊断历史形态 | 不可用于正式PIT效果结论；单独统计 |

个股MA、回踩和日线触发可在受控内存窗口重算，当前成员诊断也可帮助研究；缺历史成员不能伪造POTENTIAL生命周期确认。采用现有单日保留/止增长政策：依赖窗口按需构建并缓存有界；保存输入摘要和必要冻结信号，不自行长期复制全历史派生表。要增长长期前瞻记录须纳入明确保留预算。

## 15. 信息架构与现有功能关系

- 首页精选改为本文唯一输出；旧 `/api/candidates` 保留兼容和结构复盘，禁止成为失败回退数据源。新增接口建议 `/api/research/today` 与详情 `/api/research/today/{security_id}`，由冻结run解析，不让前端二次算资格。
- CURRENT_FOCUS/EARLY_FOCUS继续解释板块轨道；四类是股票研究场景，二者不是一对一重命名。EARLY_FOCUS中的SETUP可出现在蓄势观察；新回踩不要求先成为旧CURRENT_RESEARCH角色。
- 保留新高、RPS、MA、量额筛选、五类旧结构、交并集和中期主线，说明用途。旧A/A+标“旧结构研究等级”，而非误称所有记录都是历史日期。
- 首页市场摘要只提示当前市场广度和覆盖，第一版不把未经标定的市场总状态做统一硬门，避免普跌时自动错过独立强势股。
- 个股弹窗展示RAW最新价/行情涨幅与ADJ技术指标的差别；可看未入选的逐谓词原因。日期、来源、单位、关键风险应在主行可见。
- 表格固定高度、分页、窄屏横向滚动及既有在线题材弹窗修复均保持回归验收。历史复盘/数据能力独立入口显示具体缺什么，而不只有“2个交易日”。

## 16. 构建、存储与完整研究发布

Phase0须先有终态：`FULL_PASS`或允许相应数据能力的`DEGRADED_PASS`才可执行扫描；`BLOCKED`只是终态，不是许可继续。必须复核降级项是否影响必需字段。不能把“取得任一终态”写成扫描放行。

构建链：冻结输入→基础publication→M8/M9必要技术与关系→个股事实/四类→板块轨道与LOO→类内评分/解释→全量结果→完整性验收→封存research run→**原子切换active research bundle**。M10历史增强缺失属于受控降级，不得因其非必需历史字段为空阻断独立股票研究；格式/身份损坏仍必须fail closed。

现有M4可能已成功，后续失败不回滚删除该publication。本期增加一个完整研究包指针，绑定 `(publication,snapshot,membership,run,contracts,parameter_hash,output_digest)`。只有所有必需对象COMPLETE且校验通过才切换；否则保留上一完整研究包并显示其真实日期、当前失败阶段。页面不能把新行情与旧研究混成同一份最新清单。

对象先在TDX外临时位置写入、flush/fsync后原子replace；DB行在事务内写入并最终COMPLETE。文件+DB跨资源不假定一个原子事务：先登记不可变结果摘要，再切换唯一可见指针；断电留下的未引用对象按已有回收合同处理，不在此自动删除。相同输入/合同/参数的重跑须同内容哈希；run审计时间或运行ID可不同，逻辑结果必须一致。

现有 `build_latest_research_run`需新增显式目标publication/snapshot参数或可靠lease绑定。并发构建时不能执行到后半程再取“最新”而跳到另一任务。原版本/参数结果保留，禁止原地改历史标签。

资源门：窗口按日、按列批量读取；同日技术与RPS只算一次，不能每股重扫1,964万行。LOO计数用总量减目标贡献，中位数用排序/秩或等价可验证算法；不得以降低精度换性能。P12-01记录现链耗时、峰值内存、产物增量，P12-07须报告新旧对照和既有预算是否通过。

## 17. 回放、后验评估与参数校准

三个门分开：**实现正确性、研究功能可用性、效果有效性**。测试通过不证明有效；真实效果尚未完成也不要求把所有已正确的收盘功能禁用。首期可作为明确标注的研究预览上线，效果标 `EFFECT_OBSERVATION_PENDING`。

1. 先冻结公式/参数/窗口/分组，建立人工手算、单元反例和当前真实日逐谓词分布。所有零入选场景都分析已知失败与缺证据，不凑人数。
2. 历史诊断按时间顺序切成开发/验证/锁定评估区间，边界、起止、样本数在看结果前登记。没有合格PIT成员/universe/事件则只能股票事实或重构诊断，不能写“无未来函数回测通过”。
3. 调参只能看开发段；验证段选择有限候选后冻结，锁定段只验一次。前瞻窗口10日时，时间分割需排除跨边界未到期的标签（至少覆盖最长10会话的隔离），不随机打乱股票日；保留全部参数尝试和失败结果。
4. 基线必须同日、同正常全集/流动性/数据门、同展示数量，至少含旧priority_score、仅RPS、股票触发不含板块、完整方案。消融LOO、位置门、新鲜度分别解释名单变化，不只追求收益最高。

### 17.1 后验评价锚与不可变结果

信号在t收盘后才可用。本版选择 `evaluation_basis=HORIZON_END_TDX_AFFINE_QFQ_V1`：每个h=1/3/5/10会话的到期日e=t+h，使用**以e为截止日和锚点**的本地仿射调整引擎，统一计算整个[t,e]窗口的O/H/L/C。记该价为C^(e)、H^(e)、L^(e)：

```text
FRET_h = C^(e)[e]/C^(e)[t]-1
MFE_h  = max(H^(e)[t+1:e])/C^(e)[t]-1
MAE_h  = min(L^(e)[t+1:e])/C^(e)[t]-1
```

引擎只纳入其支持的本地事件类型、生效日≤e且属于冻结评价源的事件；RAW数据、GBBQ源/解析事件、调整实现/参数、日历、e、采集时间及原始摘要一同冻结。调用`build_affine_factors`必须确保传入日期锚为e；缺e必要报价时输出缺失，不能让引擎悄悄以最后一条可用bar为锚。无e时点可获知源证据的历史评价标RECONSTRUCTED，不能宣传PIT。

采用e锚允许t之后至e的公司行为进入**后验评价**，它们绝不反馈给t的资格/分数/episode。e之后的事件不进入；事后补录/修订e之前数据须建立新 `evaluation_revision`，保留原结果，禁止用最新整表覆盖。不同h可有不同锚，因此跨h数字不是同一固定基准价格路径；每行携带anchor和hash，不将它们强行拼成可加总收益曲线。

唯一评价身份至少含 `(signal_run_id, security_id, episode_id, horizon, end_date, evaluation_contract, evaluation_source_hash, adjustment_version, evaluation_revision)`。冻结信号与冻结评价是两份对象，评价不得更新信号身份。FRET为项目调整价变化，不等同含现金分红再投资总收益或可交易收益；MFE/MAE是相对信号收盘的窗口极值，可为负/正，并非买入后最高收益/最大回撤策略。

缺日、未到期、非正调整价、停牌及退市分别保留状态和总体分母，不填0、不择有利终点、不悄悄删样本。同日基准成员集合在t冻结，每只股票同样以e锚评价；主基准采用有效成员FRET中位数，报告有效数/目标数及覆盖，覆盖低于预登记门则相对结果UNKNOWN，不动态更换存活成员集合。若研究模拟成交，须另立t+1进入、涨跌停/成本合同，本期不做。

### 17.2 流动性门的时代适用范围

当前2000万元流动性门保持不变，首版不额外叠横截面金额分位：后者会改变今日资格，当前没有证据支持。数据库始于1990年不等于本方案承诺从1990年统一回测。正式效果样本以版本冻结后的真实前瞻为主；历史PIT验证仅限P12-05预登记的、靠近当前且制度/数据覆盖可比的样本段，登记精确起止、选择理由和分层，未预登记不得发布历史效果结论。

早期年代仅用于解析/数据质量/结构诊断，不能与现代固定金额门结果混池评价。即使现代段也报告当日LIQ20金额分布及候选在该分布的位置，监控固定门随市场变化的覆盖漂移；分位只作诊断。需要扩展长年代时另立流动性时期合同，比较绝对门与分位方案，不能事后按效果划分年代。

报告按场景、市场强弱、行业/概念、流动性和波动分层；同时给数量、覆盖、分布中位/分位、回撤、入选持续天数、重叠程度与失败案例。重复股票episode和同日相关性需按日期/episode分组分析，不能把相关股票当独立样本夸大置信度。

沿既有AUD-EFFECT-09最低报告门：至少20个独立信号日、50个独立episode；各场景另报自身样本数，不能拿总数替代不足场景。该门只足以启动描述性报告，不能自动证明统计有效或参数最优。需预登记可接受覆盖与退化边界，样本不足保持PENDING。

## 18. 验收矩阵与固定反例

| 验收面 | 必须提供的证据与通过条件 |
|---|---|
| 公式正确性 | 平台最高收盘/最高价区分；mean/median区分；ddof区分；精确窗口与人工样本逐值相符；容差写入合同 |
| 风险不被加分抵消 | STRUCTURE_BREAK、EXTENDED、SEVERE_DROP、FIRST_DAY_DAMAGE已知true时四类入选数各为0 |
| 触发真实性 | 仅RPS99/旧A+/TREND_BACKGROUND不能入重点；回踩有顺序；延续有当天事件；R20不被MA5旧分支锁死 |
| 关系共同性 | SUPPORTED行LOO通过率100%；覆盖分母、成员哈希完整；未知/失败不得进入支持组 |
| 数据完整性 | 输出身份冲突0；未知与false分开；窗口不压缩；DB/JSON无NaN/Inf；报价/技术收益不混名 |
| 数量与排序 | 全量资格不被预览限额删除；无重复主股票；相同逻辑输入结果一致；代码稳定兜底；跨类别不按分数混排 |
| 解释 | 所有入选行checks、来源/日期/单位、场景、风险、失效规则完整率100%；未入选对象能查询原因 |
| 发布 | 基础发布成功而研究失败、并发日期切换、重试、断电模拟均不暴露混合完整包；旧日期明确 |
| 行为与效果 | 实测每门漏斗、名单覆盖/集中/持续分布；工程验收与EFFECT_PENDING分开 |
| UI | 源码接口依赖及桌面/窄屏实际检查；已有七池/涨停/题材表格修复不回归 |

固定反例至少包括：

1. RPS99且首日放量破MA20：不得靠“尚未连续两日破位”通过。
2. 缩量但连续走低未收回：回踩未确认；有历史强势+事件回调+当日收复时方可通过。
3. 前20日最高收盘10、最高价11、今日收盘10.5：只能收盘平台突破，不能称最高价突破。
4. MA20收复但昨日MA5已经站上：R20可独立评估；不能被旧RECOVERY否决。
5. 高RPS、MA多头、今日无延续事件：只趋势观察。
6. 目标股单独拉升；LOO剩余成员平弱/缺报：不能SUPPORTED；条件充分的股票可独立研究。
7. EARLY全板块改善只由目标股贡献；剔除后无改善：不能早期共同支持。
8. 一项必要false、另一项NULL：资格false，同时列未知；全部已知true但必要一项NULL：UNKNOWN。
9. H=L、零分母、停牌填充、缺主日历会话、新股不足120bar、RPS样本99：正确降级，不用默认0。
10. RAW除权缺口而同截止ADJ连续：不误报技术暴跌；换锚后的冻结平台仍同基准。
11. 同板块6只全部合格：全部结果可查，不复发3只截断；首屏限额不改资格。
12. 同日2个run、次日缺run、算法换版、左截断：age不虚增，NEW不伪造。
13. t后追加价格/成员/除权事件：冻结t结果不变；无法恢复当时源时明确诊断限制。
14. 基础publication已发布而研究失败：显示上一完整研究日期或失败，不回退旧候选冒充新清单。
15. 无板块历史但个股触发完整：独立组可用；当前W已知true可风险观察，不等20个run。
16. 评分字段缺失：保留资格/未评分状态，不补权重升到榜首。
17. prior sigma=0.06、ADJ跌9%且仍在MA20以上：绝对跌幅标记TRUE；sigma未知也不能隐藏已知绝对大跌。非跌日不触发严重跌。
18. 强势seed之后长上影创峰而峰值日已不强、后续无结构破坏并回调收复：不因峰值日强势FALSE否决；峰后破结构则不能回踩。
19. 峰前均额100、两日回调各60、确认日120：收缩0.60、确认2.00；确认额不污染收缩比。1日回调与10日边界单列。
20. 同一事件窗口每天向前移动、同日重跑、峰值被突破、过期、缺日、已确认后二次收复：不漂移旧锚、不挑更早有利事件、不重复NEW。
21. 完整CURRENT成立但去目标股后只通过成员宽度而完整轨道不成立：本方法仍按自身合同评估，元数据必须明确full_track=false，禁止误标Full LOO。
22. 一股有12个概念、一股2个；重复边、未知边和未支持边全部计数可对账；支持数不加股票分，效果按关系数分层。
23. 同contract_id/参数但传递依赖源码或运行库改变：旧锁不可复用；hash存在但源码丢失也不声称可重现。
24. t到e间发生支持的公司行为：只影响e锚评价，不改t信号；e之后再发生事件，原h评价hash和值不变；e前事件事后修订产生新revision。
25. 延续股票门TRUE而板块未知/不支持：保存STOCK_ONLY影子样本，首页不伪称SUPPORTED；缺PIT关系的比较只能诊断。

## 19. 分阶段实施与放行

每阶段执行前读取最新适用方案/专项回执，保存 `stage_contract, consulted_versions/hashes, input_identity, evidence, acceptance_result, next_stage`。接受状态使用FULL_PASS/DEGRADED_PASS/BLOCKED并写适用范围。以下均为未来实施安排，本次未执行。

| 阶段/合同 | 工作与产物 | 通过/降级条件 | 下一步 |
|---|---|---|---|
| P12-01 BASELINE_V2 | 冻结目标日及旧榜/全量P05/LOO漏斗、字段覆盖、反例和资源基线，查Phase0 | 输入身份清楚、缺口按能力列明；Phase0 BLOCKED不能进入扫描 | P12-02 |
| P12-02 FACTOR_V3_3 | OHLC输入、窗口/价格基准、prior量额、风险、回踩事件与RPS变化可比性 | 人工公式复算、边界和当前真实分布；未验证历史标模式 | P12-03 |
| P12-03 SCANNER_V3_3 | 四类独立资格及SETUP_WATCH，逐谓词和风险解释 | 固定反例、全量漏斗；仅旧等级不能准入 | P12-04 |
| P12-04 RANK_AND_LOO_V3_3 | 修复最终LOO硬过滤、变化LOO、评分/支持模式/完整全量结果 | 分组真实、未评分不丢失、6股案例、不跨类混分 | P12-05 |
| P12-05 REPLAY_V3_3 | 冻结参数、时序诊断/合格PIT回放、基线、消融、校准记录 | 算法和诊断可验收；缺PIT仅DEGRADED_PASS，效果PENDING | P12-06 |
| P12-06 BUNDLE_V3_3 | **先**接完整研究发布指针、目标日绑定、事务/文件提交、预算与失败恢复 | 真实链输出可读；原子可见性与幂等通过，不把M4成功当研究READY | P12-07 |
| P12-07 UI_V3_3 | **后**切首页数据源、详情、全量分页、空态/日期、旧UI回归 | 桌面与窄屏实查、新接口对账；可发布研究预览并明示效果待验 | P12-08 |
| P12-08 FORWARD_V3_3 | 连续真实日封存、状态迁移与后验观察 | 达既有最低报告门后独立评估，不自动关闭效果专项 | V3内新版本校准 |

历史增强/效果与本地收盘可用性分别放行。修改参数必须产生新hash、新run，不覆盖旧证据。设计完成不是执行完毕，本次不把P12-01正式生产基线或任一实现阶段标FULL_PASS。

## 20. 独立专项审计登记

以下条目独立于P12阶段门保留范围、证据和关闭条件；不能因本方案修订或单个测试通过自动关闭。影响本阶段的阻断依赖同时列入阶段回执，不因“独立跟踪”而忽略。

| ID / 状态 | 范围与证据 | 独立关闭条件 |
|---|---|---|
| AUD-AMOUNT-A-06 / OPEN | M10、POTENTIAL、旧域金额A及单位/共同成员；既有审计仍未闭合 | 正式A与股票AMR、成员比中位严格分开；21日成员/金额/覆盖/身份实算和引用审计 |
| AUD-HIST-01 / OPEN | 最新run历史成员UNAVAILABLE，3日变化NULL | PIT成员/universe/事件可得性、精确会话、重构标签、连续实跑与存储预算 |
| AUD-EFFECT-09 / OPEN | 阈值未验证，效果独立于工程 | 同日基线、冻结样本/参数、足量分场景结果与失败分析 |
| TR-AUD-LOO-01 / OPEN | 当前shortlist未硬过滤track/loo；EARLY变化未真正剔除目标 | 源码门、缺报/小板块/单股贡献反例、真实全量对账；本次20行通过不能代替关闭 |
| TR-AUD-PRICE-TIME-02 / OPEN | RAW/ADJ、ddof、高点定义、仿射换锚和历史可得性跨域 | 多除权日期人工复算；t后输入不改t；窗口和基准契约一致 |
| TR-AUD-PUBLISH-03 / OPEN | M4先发布、M8/M9/M10/research后构建；latest并发目标风险 | 完整研究指针、并发/失败/恢复实证及旧结果保留 |
| TR-AUD-UNIVERSE-04 / OPEN | 当前universe历史标签复用、股票RPS跨日分母 | 历史可得全集/状态，跨日交并与样本门，缺报分母与新股范围对账 |
| TR-AUD-TURNOVER-05 / DEFERRED | 流通股本、股本变更与不同换手率分母尚未验证 | 本地源清点、生效日和股数口径验证；关闭前保持OFF |
| TR-AUD-LEGACY-06 / OPEN | 首页旧候选语义，旧结构/新场景/预览截断相互污染 | 接口引用表、页面真实来源、全量不截断回归，失败无旧榜补位 |
| TR-AUD-ONLINE-07 / DEFERRED | 在线事件完整分页、M8C证券状态/制度来源 | 按数据集版本门独立验收；不成为本地日线必需依赖 |
| TR-AUD-RELATION-MULTIPLICITY-08 / OPEN | 多关系股票ANY支持机会偏差，含预览优先效应 | 预冻结关系集合、全分母计数、类型/数量分层与同日对照；统计字段完成不等于偏差已消除 |
| TR-AUD-EPISODE-09 / OPEN | 回踩seed/峰/回调/确认、金额区间及换锚的跨日一致性 | 人工逐日轨迹、左截断、终止/重置与重复信号反例，真实事件对账 |
| TR-AUD-EVALUATION-ANCHOR-10 / OPEN | 不同h评价锚、事件源修订与跨域复权收益 | e锚手算/公司行为样本、e后事件不漂移、revision保留、信号与评价隔离 |
| AUD-MKT-08 / OPEN | 市场摘要/动态周期/物化结果来源身份 | 同publication/snapshot一致，质量分开，不由本次四类门自动关闭 |

已修代码的AUD-MA20-00、AUD-COV-02、AUD-RANK-03、AUD-PRICE-04、AUD-NULL-05、AUD-HOT-07，沿R1回执记录其当时关闭范围；本版新增跨日/跨发布问题不得伪称这些旧项从未修复，也不得借旧关闭覆盖新缺口。

## 21. 在线边界与保留决定

在线涨停、题材、事件、龙虎榜及热榜仅作为独立证据展示，不进入本地四类打分，不改变snapshot identity。来源不可用应显式降级，不阻断本地必需链。热榜request-time only，禁止保存raw payload、行、批次、历史快照；不可因为想做前瞻评估而偷偷保存热榜历史。

保留V1/V2结构研究、V3双轨板块、唯一在线涨停、现有行情可视化和一键生成。新增核心是全量、当日、分场景、带风险与失效的研究流程，仍在V3，不创建V4或第二套生成入口。

## 22. 本文档审计阶段记录

| 字段 | 内容 |
|---|---|
| stage | `V3-TODAY-RESEARCH-DESIGN-AUDIT-20260914` |
| stage_contract | `V3_TODAY_RESEARCH_DESIGN_AUDIT_V2` |
| consulted | 原v1.0、AGENTS、V3主规格/台账、全算法审计及R1整改回执、当前强势复核、最终清单复核、调整/日历/因子/强度/关联合同、当前代码配置 |
| evidence | 第2–3节当日只读数据及源码映射；详细问题映射、文件hash、只读查询方法见单独修改说明 |
| acceptance_result | `DEGRADED_PASS`：设计冲突已修订，当前数据能力核查完成；未执行新扫描器、完整历史/PIT回放、生产发布与效果验收 |
| code/config/database_changed | 否/否/否 |
| tdx_access_or_write | 否/否；未来构建按既有只读输入契约 |
| artifact_write | 仅本方案与修改说明，项目docs内临时文件完成后原子替换 |
| next_stage | 实施时进入P12-01，重读最新适用文档并冻结当时输入；本次交付为已修订设计及修改说明 |

配套修改说明：`V3_TODAY_RESEARCH_PRIORITY_AUDIT_CHANGELOG_20260914.md`。本文是设计实施依据；任何候选阈值的实际有效性仍需独立证据，不因审计文档写完而自动成立。

## 23. v2.1线上审计逐项裁决与阶段记录

输入为用户提供的 `D:/Users/lps/Desktop/V3_TODAY_RESEARCH_DESIGN_AUDIT_20260914.md`，只读审阅。其评分、P0/P1级别和“必须”建议不自动成为项目授权或事实。本次只做设计订正，不启动P12实现。原§22保留为v2.0审计历史，本节为当前设计订正回执。

| 外部审计项 | 裁决与实际修订 | 未采纳部分/原因 |
|---|---|---|
| §3 严重跌幅无上限 | 部分采纳，§7.3增加绝对/相对双门、三值和参数约束 | 不接受“必然泄漏大跌到四类”的推断；四类本身已有非负/正收益条件。8%是候选保护初值，未称已校准 |
| §4 非Full LOO | 采纳命名订正，§10统一TRACK_PLUS_LOO_MEMBERS与字段；明确full_track=false | 原文已限定并非全轨道LOO，故不是首次发现隐瞒。首版不强制Full LOO，也不凭空声称性能不足；全轨道含P1/市场/重叠关系重算需独立合同及增量证据 |
| §5 回踩锚顺序 | 采纳并扩展，§9.2逐日seed→推进峰→回调→确认状态机 | 不只写Episode First口号，补重置/超时/左截断/重复确认与同日高低未知时序 |
| §6 回踩金额混确认日 | 采纳，§7/9/11分离实际回调收缩和确认日金额，并同步评分 | 不采用任意挑选下跌日的分母，实际区间包括中间反弹；窗口/样本数可审计 |
| §7 多概念机会偏差 | 部分采纳，§10.4关系集合在结果前冻结、数量/类型/未知统计及分层验证 | 不新增无来源的主概念，不直接让行业资格高于题材，不用任意前K关系截断；ANY仍有选择偏差，独立挂账 |
| §8 旧信号依赖漂移 | 采纳，§5.0锁定传递源码/参数/环境并要求源码可恢复 | 不复制独立一份旧信号实现，防止两套逻辑再漂移；不能只存不可恢复的hash |
| §9 金额门年代漂移 | 采纳验证范围约束，§17.2正式前瞻/预登记现代PIT段、早期历史诊断分开 | 2000万元当日门保留，不无证据叠加分位门；历史数据多不代表必须全年代混池 |
| §10 评价锚缺失 | 采纳，§17.1选择每h的到期日e共同本地仿射锚，冻结评价源/revision | 不新增外部调整服务，也不把该价变化叫总收益；t信号与e评价隔离 |
| §11 延续板块门过严假设 | 采纳影子验证，§9.4保留全量STOCK_ONLY/SUPPORTED | 本次不直接取消首页板块门，不增加新的重点类别；待消融验证 |
| §12 参数自由度 | 部分采纳，§11.1固定现有评分、增加唯一简单排序对照和3套候选预算 | 不凭无样本的主观判断删掉所有评分项或重新调大量权重，先事实/事件/风险，后验证增量 |
| §13 保留的设计 | 保留三值、全量资格、RPS背景、非CURRENT不等弱、研究价变化非交易收益 | 不恢复TopN资格截断，不新增分时或换手率必需项 |
| §14–17 推进顺序/评级 | 采纳先订正设计再实施；P12顺序保持，详见下方新增验收 | 8.5/10不是工程或效果证据，外部“有条件通过”不代替项目阶段门 |

实施阶段新增约束：P12-01冻结dependency_lock草案、源证据、现代样本预登记要求；P12-02验收风险双门、事件状态机和分离量额；P12-03保存延续STOCK_ONLY对照；P12-04验收支持命名、关系机会统计及简单排序对照；P12-05必须先通过e锚/revision与时序样本隔离再出评价；P12-06把dependency_lock_hash纳入bundle；P12-07检查部分LOO说明和影子不冒充首页；P12-08按关系数量与场景报告真实前瞻。单独审计项仍不能由某阶段测试自动关闭。

阶段合同：`V3_TODAY_RESEARCH_EXTERNAL_REVIEW_DISPOSITION_V2_1`。证据：外部审计全文、当前源方案、AGENTS、V3最新台账、research_association/stock_attention/research_attention配置、TDX仿射实现与合同。接受结果 `DEGRADED_PASS`（设计意见已核实并订正；本轮没有重跑生产统计、实现新扫描器或证明阈值效果）。下一阶段仍P12-01；代码/配置/数据库/TDX修改均为否。改动通过项目docs内临时文件原子替换，单独修改说明追加v2.1记录，保留v2.0历史指纹。

# TDX Market Structure Scanner
## V0.3 基线继承、生产实现全链与设计审计说明
### — Astra 外部设计审计专用补充文档

**文档性质**：独立审计说明 / V0.3 Implementation Supplement  
**项目**：通达信A股市场结构扫描器 / TDX Market Structure Scanner  
**当前最高设计与业务基线**：`TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md`  
**当前生产实现版本**：`daily-production-v1.1`  
**当前生产状态**：`TDX_MARKET_STRUCTURE_SCANNER_V1_PRODUCTION_READY`  
**主线开发状态**：`CLOSED`  
**审计目的**：让首次接触本项目的外部模型能够完整理解“原始TDX数据如何变成最终板块、个股、Candidate Pool、A+/A/B/C”的全过程，并重点审计 V0.3 原始方案与最终生产实现之间的继承、细化和实际差异。

---

# 0. 结论先行

## 0.1 当前仍然遵循 V0.3 FINAL 吗？

**是。**

当前项目没有发布新的 V0.4 / V1.0 业务设计文档去取代 V0.3 FINAL。

截至 Phase 6.1 最终封板：

```text
baseline_version
=
V0.3_FINAL_IMPLEMENTATION_BASELINE
```

仍然是所有正式 Phase Receipt 的基线身份。

当前生产版本：

```text
daily-production-v1.1
```

只是：

> V0.3 设计基线之上的正式生产实现版本。

它不是新的业务基线，也没有修改项目身份。

因此当前权威关系应理解为：

```text
V0.3 FINAL IMPLEMENTATION BASELINE
= 最高项目设计 / 业务语义 / 数据边界基线

↓

后续 Versioned Contracts
= 对 V0.3 中未完全冻结、仍属“建议 / 待公式化 / 可选”的部分进行正式实现收敛

↓

daily-production-v1.1
= 把已经冻结的 Phase1—5 模型合同组织成正式每日生产闭环
```

---

# 0.2 但是不是“V0.3 每一句建议都原样实现”？

**不是。**

V0.3 中有三种内容：

```text
A. 硬业务原则
B. 已明确公式
C. 初始建议 / 候选权重 / 待合同化设计
```

最终生产系统：

- **完整保留 A 类原则；**
- **基本继承 B 类公式；**
- **对 C 类内容通过 Phase1—5 Contract 做了进一步收敛。**

因此外部审计不能只问：

> “代码是不是和 V0.3 每一行完全相同？”

而应该问：

> “后续合同的收敛是否仍忠于 V0.3 的项目目标、数据边界、解释性原则和结构发现目标？其中哪些实现收敛值得重新审计？”

这正是本文档要解决的问题。

---

# 1. 当前权威层级

当前建议按以下顺序审计。

## Level 1 — 项目设计权威

```text
TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md
```

负责定义：

- 项目是什么；
- 项目不是什么；
- 数据边界；
- TDX 只读；
- Universe；
- Factor / Sector / Stock / Candidate 的总体架构；
- Research Priority 的业务语义；
- Current Membership Bias；
- 输出目标；
- 不允许概率化、自动交易和未经验证的数据。

---

## Level 2 — 复权与数据口径

```text
Adjustment Contract V0.3
Adjusted Dataset Contract V1
```

当前正式价格体系：

```text
RAW SOURCE
=
LOCAL TDX .day

CORPORATE ACTION SOURCE
=
LOCAL TDX gbbq

ADJUSTMENT
=
TDX_NATIVE_AFFINE_QFQ

PROJECT_PRICE_BASIS
=
FORWARD_ADJUSTED

AMOUNT
=
RAW

VOLUME
=
RAW
```

正式前复权为仿射：

```text
AdjustedPrice
=
A * RawPrice + B
```

而不是简单乘法比例。

---

## Level 3 — 原子 Factor

```text
FACTOR_CONTRACT_V1
factor-contract-v1.0
```

定义正式生产股票原子因子。

---

## Level 4 — Market / Synthetic Sector

```text
MARKET_REGIME_FACTOR_CONTRACT_V1
SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1
```

把个股因子聚合成：

```text
Market Factor Vector
+
Synthetic Sector Factors
```

---

## Level 5 — Sector Scanner

```text
SECTOR_SCANNER_CONTRACT_V1
sector-scanner-ruleset-v1.0
```

输出：

```text
CURRENT_STRENGTH
STABILIZATION
REACCELERATION
```

---

## Level 6 — Stock Scanner

```text
STOCK_SCANNER_CONTRACT_V1
stock-scanner-ruleset-v1.0
```

输出：

```text
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
SECTOR_LEADER
EARLY_MOVER
```

---

## Level 7 — Candidate / Research Priority

```text
CANDIDATE_POOL_CONTRACT_V1
RESEARCH_PRIORITY_CONTRACT_V1
research-priority-ruleset-v1.0
```

输出：

```text
Candidate Pool
+
Priority Score
+
A+ / A / B / C
```

---

## Level 8 — Production

```text
DAILY_PRODUCTION_CONTRACT_V1
daily-production-v1.1
```

负责：

```text
latest解析
source fingerprint
阶段编排
generation/hash binding
原子发布
日报
same-cutoff revision
no-new-data
```

不修改模型。

---

# 2. 项目的真实生产链

最终每日流程：

```text
LOCAL TDX
│
├─ .day
├─ gbbq / gbbq.map
├─ tdxhy.cfg
├─ tdxzs.cfg
├─ infoharbor_block.dat
├─ SH/SZ/BJ TNF
└─ MASTER_TRADING_CALENDAR
       ↓
[1] Source / Readiness / Fingerprint
       ↓
[2] TDX_NATIVE_AFFINE_QFQ
       ↓
[3] Calendar-aligned Normalized Daily
       ↓
[4] NORMAL_UNIVERSE
       ↓
[5] 29 Stock Atomic Factors
       ↓
[6] Market Factor Vector
       ↓
[7] CURRENT_TDX_MEMBERSHIP
       ↓
[8] Synthetic Sector Factors
       ↓
[9] Sector Scanner
       ↓
[10] Stock Scanner
       ↓
[11] Candidate Pool
       ↓
[12] Research Priority
       ↓
[13] A+ / A / B / C
       ↓
[14] market_summary.html / sectors.csv / stocks.csv / candidates.csv
```

核心命令：

```bash
python run_daily.py --date latest
```

---

# 3. 数据边界

V0.3 的核心数据原则仍然完全生效。

正式生产数据只来自：

```text
本地 TDX
```

当前没有进入生产计算的：

```text
东方财富
同花顺
AkShare
84x
新闻
财务
研报
资金流
指数OHLC
分钟
Tick
Level2
LLM
AI预测
机器学习
```

当前：

```text
external_data_used = FALSE
index_ohlc_used = FALSE
```

---

# 4. Membership 的正式限制

正式板块成员口径：

```text
CURRENT_TDX_MEMBERSHIP
```

因此：

```text
pit_membership = FALSE
historical_backtest_safe = FALSE
```

这意味着：

## 当前每日扫描

合法。

## 用今天成员回填过去做正式历史回测

不合法。

所以当前 production：

```text
不支持任意历史 --date
```

这是比 V0.3 原始“允许近20日 approximate replay”更加保守的最终生产策略。

---

# 5. Universe

正式股票扫描基础：

```text
NORMAL_UNIVERSE
```

核心语义：

```text
A_STOCK
+
history >= 120 market sessions
+
近期数据质量满足要求
+
非长期无效证券
```

当前生产快照：

```text
NORMAL_UNIVERSE = 5461
```

创业板、科创板、北交所并不是因为板块类型被永久删除。

---

# 6. Phase 1 — 当前正式 29 个股票原子因子

当前真正进入生产 Factor Engine 的不是 V0.3 中所有可能 Factor，而是已经冻结的 **29 个正式字段**。

下面按类别列出。

---

## 6.1 Return — 4

```text
RET5
RET10
RET20
RET60
```

公式：

```text
RET_N(t)
=
adj_close(t) / adj_close(t-N) - 1
```

用途：

- 短中期强度；
- Relative Strength；
- Sector Return；
- Stock Scanner；
- Pattern Rank。

若分母非正或输入非法：

```text
NULL
```

禁止 epsilon / abs / clip 伪修复。

---

## 6.2 Moving Average — 4

```text
MA5
MA10
MA20
MA60
```

公式：

```text
MA_N(t)
=
mean(adj_close[t-N+1:t])
```

用途：

- 趋势基础；
- MA above breadth；
- Strong Pullback 的结构保持；
- Market Breadth。

---

## 6.3 Trend Regression — 4

```text
TREND_SLOPE_20
TREND_R2_20
TREND_SLOPE_60
TREND_R2_60
```

模型：

```text
y = log(adj_close)
x = 0 ... N-1
```

输出：

```text
Slope
R²
```

解释：

```text
Slope > 0
= 方向向上

R² 高
= 价格路径与线性趋势吻合度更高
= 趋势更连续/更规则
```

如果窗口中存在不能做 log 的非正 QFQ 价格：

```text
NULL
```

禁止人为 clip。

---

## 6.4 Position — 3

```text
POS20
POS60
POS120
```

公式：

```text
POS_N
=
(adj_close - rolling_low_N)
/
(rolling_high_N - rolling_low_N)
```

范围通常：

```text
0 → 窗口低位附近
1 → 窗口高位附近
```

分母为0：

```text
NULL
```

用途：

- 强趋势位置；
- 回踩后是否仍处中高位；
- Breakout Prep；
- Sector Leader。

---

## 6.5 Distance From High — 2

```text
DIST_HIGH20
DIST_HIGH60
```

公式：

```text
DIST_HIGH_N
=
adj_close / HighestHigh_N - 1
```

典型：

```text
0
= 当前接近窗口最高点

-0.05
= 距高点约5%
```

用途：

- Pullback 深度；
- Breakout Prep；
- Near-high 结构。

---

## 6.6 Max Drawdown — 2

```text
MDD20
MDD60
```

公式：

```text
MDD_N
=
min_j(
  Close(j) / running_max(Close <= j) - 1
)
```

结果：

```text
<= 0
```

用途：

- 趋势破坏程度；
- Strong Pullback；
- Steady Trend；
- Sector quality。

---

## 6.7 Volatility — 1

```text
VOLATILITY20
```

公式：

```text
std(log_return_1d)
```

正式：

```text
ddof = 1
```

当前生产中：

```text
STEADY_TREND 仅要求 finite
```

`volatility20_pct` 主要作为上下文，并没有进入固定 absolute threshold。

---

## 6.8 Relative Strength — 4

```text
RS5
RS10
RS20
RS60
```

公式：

```text
RS_N(stock,t)
=
RET_N(stock,t)
-
Median(
  RET_N of valid NORMAL_UNIVERSE at same t
)
```

重要：

```text
不是相对上证指数
不是相对沪深300
不是外部Benchmark
```

原因：

```text
Index Data Contract 尚未进入正式生产
```

RS 是整个系统的重要横截面相对强弱基准。

---

## 6.9 Amount Moving Average — 3

```text
AMOUNT_MA5
AMOUNT_MA10
AMOUNT_MA20
```

输入：

```text
RAW_AMOUNT
```

不是复权成交额。

---

## 6.10 Today / 20D Amount Ratio — 1

```text
AMOUNT_RATIO20
=
Amount(t) / AMOUNT_MA20(t)
```

注意：

这个字段容易和后面 Scanner 使用的：

```text
AMOUNT_RATIO_5_20
```

混淆。

两者不是一个东西。

---

## 6.11 Return Concentration — 1

```text
RETURN_CONCENTRATION_20
```

先：

```text
positive_return_i
=
max(ret_1d_i, 0)
```

然后：

```text
RETURN_CONCENTRATION_20
=
max(positive_return_i)
/
sum(positive_return_i)
```

若：

```text
sum positive return = 0
```

则：

```text
NULL
```

解释：

> 20日正收益是否高度集中在某一个单日脉冲。

---

# 7. 29个正式 Factor 汇总

```text
4  Return
4  MA
4  Trend Regression
3  Position
2  Distance High
2  MDD
1  Volatility
4  RS
3  Amount MA
1  Amount Ratio20
1  Return Concentration
----------------------
29
```

---

# 8. Phase 1 之后额外派生但不属于 29 Factor 的关键量

有几个后续计算非常重要，但不能和 Phase1 的29因子混为一谈。

---

## 8.1 AMOUNT_RATIO_5_20

正式：

```text
AMOUNT_RATIO_5_20
=
AMOUNT_MA5 / AMOUNT_MA20
```

解释：

```text
>1
= 最近5日平均成交额高于20日平均
```

主要用于：

- Market activity；
- Sector activity；
- Breakout Prep；
- Early Mover。

---

## 8.2 Stock Cross-Section Percentile

例如：

```text
stock_rs5_pct
stock_rs20_pct
stock_rs60_pct
volatility20_pct
amount_ratio_pct
```

按：

```text
同一交易日
NORMAL_UNIVERSE
finite values
average-rank percentile
```

计算。

---

## 8.3 Sector Internal Percentile

例如：

```text
member_ret20_pct
member_rs20_pct
member_pos60_pct
```

分母不是全市场。

而是：

```text
同一个 sector_id 当前有效成员
```

这是 SECTOR_LEADER 的核心。

---

# 9. Market Regime — 最终不是离散状态，而是 Context Vector

V0.3 原文规划：

```text
STRONG
NORMAL
WEAK
```

但最终 Phase2 **没有发布这个离散状态**。

生产实现为：

```text
Market Factor Vector / CONTEXT_ONLY
```

原因：

> 没有冻结足够可靠的状态阈值之前，不让一个主观的 STRONG / WEAK 标签反过来影响所有 Scanner。

当前典型字段：

```text
breadth_ret5_pos
breadth_ret20_pos
breadth_ret60_pos

breadth_above_ma20
breadth_above_ma60

market_ret5_median
market_ret10_median
market_ret20_median
market_ret60_median

trend_r2_20_median
trend_r2_60_median

mdd20_median
mdd60_median

pos60_median

amount_ratio_5_20_median
active_amount_expansion_ratio
```

当前 Market Vector：

```text
只作为环境解释
不改变 Scanner threshold
不改变 Priority score
```

---

# 10. Synthetic Sector — 板块不是用板块指数K线算的

核心设计继承 V0.3：

```text
CURRENT_TDX_MEMBERSHIP
+
股票原子 Factor
↓
Synthetic Sector
```

而不是：

```text
读取一个板块指数Close
↓
当成整个板块
```

这能直接观察：

```text
板块内部中位收益
Breadth
位置
回撤
RS
成交活跃
集中度
```

---

# 11. Sector Validity Gate

任何板块在进入正式 Scanner 前必须先有效。

当前基本门槛：

```text
INDUSTRY total members >= 5
THEME    total members >= 8
STYLE    total members >= 8

valid_member_count >= 5
coverage >= 0.70
```

其中：

```text
coverage
=
valid_member_count / total_member_count
```

不是：

```text
tradable_member_count / total_member_count
```

低于门槛：

```text
sector_valid = FALSE
```

不得进入正式排名。

---

# 12. Sector Type 必须分域

正式：

```text
INDUSTRY vs INDUSTRY
THEME    vs THEME
STYLE    vs STYLE
```

禁止：

```text
银行
AI概念
昨日涨停
```

放进同一 percentile 排名。

---

# 13. Synthetic Sector 的核心原子字段

生产实际使用/保留的主要结构包括：

## Return

```text
sector_ret5_median
sector_ret10_median
sector_ret20_median
sector_ret60_median
```

## Relative Strength

```text
sector_rs5
sector_rs10
sector_rs20
sector_rs60
```

及同 sector_type percentile：

```text
sector_rs5_pct
sector_rs20_pct
sector_rs60_pct
```

## Breadth

```text
sector_breadth_ret5_pos
sector_breadth_ret20_pos
sector_breadth_ret60_pos

sector_breadth_above_ma20
sector_breadth_above_ma60
```

## Trend

```text
sector_trend_slope20_median
sector_trend_r2_20_median

sector_trend_slope60_median
sector_trend_r2_60_median
```

## Position

```text
sector_pos20_median
sector_pos60_median
sector_pos120_median
```

## Near High

```text
sector_dist_high20_median
sector_dist_high60_median
```

## Drawdown

```text
sector_mdd20_median
sector_mdd60_median
```

## Activity

```text
sector_amount_ratio_median
sector_amount_expansion_breadth
```

## Concentration

```text
TOP3_CONCENTRATION
```

---

# 14. TOP3_CONCENTRATION

最终遵循 V0.3：

```text
POS_RETURN_i
=
max(RET1_i, 0)
```

```text
TOP3_CONCENTRATION
=
sum(top3 POS_RETURN)
/
sum(all POS_RETURN)
```

要求：

```text
至少8个 finite RET1
```

无正收益：

```text
NULL
```

这里不是：

```text
成交额Top3占比
```

也不是：

```text
市值Top3占比
```

---

# 15. Sector Scanner — CURRENT_STRENGTH

正式生产规则：

全部满足：

```text
sector_valid = TRUE

sector_ret20_median > 0

sector_rs20_pct >= 0.80

sector_breadth_ret20_pos >= 0.60

sector_pos60_median >= 0.60

sector_mdd20_median > -0.15
```

业务解释：

> 20日整体收益为正、同类RS靠前、大多数成员参与、中期价格位置较高、近期回撤受控。

---

# 16. Sector Scanner — STABILIZATION

全部满足：

```text
0.35 <= sector_rs20_pct < 0.75

sector_ret5_median > 0

sector_rs5_pct >= 0.60

sector_breadth_ret5_pos >= 0.55

sector_breadth_ret5_pos
-
sector_breadth_ret20_pos
>= 0.10

sector_amount_ratio_median >= 0.90
```

并至少满足一个此前受损条件：

```text
sector_ret20_median <= 0

OR sector_mdd20_median <= -0.08

OR sector_pos60_median < 0.50
```

正式语义：

```text
Cross-horizon stabilization evidence
```

不是：

```text
确认反转
```

---

# 17. Sector Scanner — REACCELERATION

全部满足：

```text
sector_rs60_pct >= 0.65
sector_rs20_pct >= 0.70

sector_ret20_median > 0
sector_ret5_median > 0

sector_rs5_pct >= 0.75

sector_breadth_ret5_pos >= 0.60

sector_breadth_ret5_pos
-
sector_breadth_ret20_pos
>= 0.08

sector_amount_ratio_median >= 1.00
```

并至少：

```text
sector_mdd20_median <= -0.03
OR
sector_dist_high20_median <= -0.03
```

正式名称语义：

```text
CROSS_HORIZON_REACCELERATION_PATTERN
```

不是历史 PIT 状态切换证明。

---

# 18. Sector Tags

## BREADTH_EXPANSION

```text
breadth5 >= breadth20 + 0.10
AND
breadth5 >= 0.55
```

## HIGH_CONCENTRATION

```text
TOP3_CONCENTRATION >= 0.60
```

## LOW_COVERAGE

```text
0.70 <= coverage < 0.85
```

这些是：

```text
结构 / 风险上下文
```

不是自动否决。

---

# 19. Sector Primary Pattern

如果一个板块多标签：

```text
REACCELERATION
>
STABILIZATION
>
CURRENT_STRENGTH
```

但：

```text
scanner_hits
```

保留全部真实命中。

---

# 20. Stock Scanner 的通用 Hard Gate

正式命中要求：

```text
security_id valid
IN_NORMAL_UNIVERSE
factor row exists
tradable = TRUE
no fatal factor-quality error
```

任一 Scanner 所需值非 finite：

```text
该 Scanner = FALSE
```

不做：

```text
NULL → 0
```

---

# 21. STEADY_TREND

生产 V1 全部满足：

```text
RET20 > 0
RET60 > 0

TREND_SLOPE_20 > 0
TREND_SLOPE_60 > 0

TREND_R2_20 >= 0.55
TREND_R2_60 >= 0.45

POS60 >= 0.55

MDD20 > -0.15
MDD60 > -0.25

DIST_HIGH20 >= -0.15

RS20 >= 0

VOLATILITY20 finite
```

业务解释：

> 中短期收益为正、趋势向上、趋势拟合质量较好、中期位置健康、回撤受控，并至少不弱于全市场中位数。

---

# 22. STRONG_PULLBACK

全部满足：

```text
RET60 > 0

TREND_SLOPE_60 > 0
TREND_R2_60 >= 0.40

RS60 >= 0

POS60 >= 0.55

-0.18 < MDD20 <= -0.03

-0.18 <= DIST_HIGH20 <= -0.03

RET5 <= RET20

POS20 < 0.85

MA20 finite
MA60 finite

adj_close > MA60
```

业务解释：

> 中期仍然强，但20日窗口出现真实回撤，仍在中高位并保持长一点的均线结构。

---

# 23. BREAKOUT_PREP

全部满足：

```text
DIST_HIGH20 >= -0.05
DIST_HIGH60 >= -0.10

POS20 >= 0.75
POS60 >= 0.65

TREND_SLOPE_20 > 0
TREND_R2_20 >= 0.40

RS20 >= 0

RET20 > 0

AMOUNT_RATIO_5_20 >= 0.90
```

若：

```text
POS20 >= 0.95
AND
RET5 > 0.10
```

增加：

```text
LATE_EXTENSION_WARNING
```

但不取消命中。

正式语义：

```text
BREAKOUT_PREP
!= BREAKOUT_CONFIRMED
```

---

# 24. SECTOR_LEADER

先要求股票自身：

```text
RET20 > 0
RS20 > 0
TREND_SLOPE_20 > 0
POS60 >= 0.60
MDD20 > -0.18
```

然后必须至少属于一个：

```text
CURRENT_STRENGTH
OR
REACCELERATION
```

的有效板块。

在该板块内部：

```text
member_rs20_pct >= 0.80
```

且：

```text
member_ret20_pct >= 0.70
OR
member_pos60_pct >= 0.75
```

则成为：

```text
SECTOR_LEADER
```

---

# 25. Primary Leader Sector

如果一个股票在多个板块都成为 Leader：

选择主 Leader 时：

```text
1. REACCELERATION 优先
2. sector_rs20_pct 高优先
3. member_rs20_pct 高优先
4. sector_id deterministic tie-break
```

所有 Leader sector 仍然保留。

---

# 26. EARLY_MOVER

这是 Tag，不是 primary pattern。

全部满足：

```text
RET5 > 0
RS5 > 0
RET5 >= RET20

TREND_SLOPE_20 > 0

AMOUNT_RATIO_5_20 >= 1.00

stock_rs5_pct >= 0.80

has_current_strength_sector = FALSE
has_reacceleration_sector = FALSE
```

正式解释：

> 个股短周期结构已经领先，但所属板块还没有进入正式 CURRENT_STRENGTH / REACCELERATION。

不是：

```text
板块一定会跟随
```

---

# 27. Stock Primary Pattern

多 Scanner 命中时：

```text
SECTOR_LEADER
>
BREAKOUT_PREP
>
STRONG_PULLBACK
>
STEADY_TREND
```

EARLY_MOVER：

```text
只作为Tag
```

不会覆盖正式 primary pattern。

---

# 28. Candidate Pool 是怎么来的？

不是“把全市场打一个分然后选Top N”。

正式 Gate：

```text
IN_NORMAL_UNIVERSE
AND
tradable
AND
quality OK
AND
(
 STEADY_TREND
 OR STRONG_PULLBACK
 OR BREAKOUT_PREP
 OR SECTOR_LEADER
 OR EARLY_MOVER
)
```

进入：

```text
Candidate Pool
```

没有任何命中：

```text
OUTSIDE_POOL
```

池外没有 C 等级。

---

# 29. Candidate Pool 与 A+/A/B/C 的区别

Candidate Pool 回答：

> 这只股票是否值得进入下一层人工研究？

Research Priority 回答：

> 已经进入研究池以后，今天先研究谁？

所以：

```text
Candidate
!= Recommendation
```

---

# 30. Anti-Double-Counting

Phase5 专门冻结：

```text
NO_LINEAR_HIT_COUNT_SCORING = TRUE
NO_MEMBERSHIP_COUNT_SCORING = TRUE
NO_LEADER_SECTOR_COUNT_SCORING = TRUE
```

也就是说：

```text
命中3个Scanner
```

不等于：

```text
自动比命中1个Scanner高分
```

属于10个概念：

```text
也不自动多加10份板块分
```

这是最终 Research Priority 相对 V0.3 初始设想的重要收敛。

---

# 31. Research Priority Score

生产正式：

```text
PRIORITY_SCORE
=
PRIMARY_PATTERN_BASE
+
PATTERN_RANK_POINTS
+
SECTOR_CONTEXT_POINTS
+
QUALITY_CONTEXT_POINTS
```

最大：

```text
100
```

四维：

```text
A. Primary Pattern Base    max 40
B. Within Pattern Rank     max 30
C. Sector Context          max 20
D. Quality Context         max 10
```

---

# 32. Primary Pattern Base

```text
SECTOR_LEADER    = 40
BREAKOUT_PREP    = 34
STRONG_PULLBACK  = 32
STEADY_TREND     = 28
EARLY_MOVER_ONLY = 22
```

只使用一个 primary pattern。

Supporting hits 不线性加分。

---

# 33. Within-Pattern Rank

不同类型股票不强行按一个通用因子混排。

---

## SECTOR_LEADER

```text
best_sector_rs20_pct DESC
primary_member_rs20_pct DESC
stock_rs20_pct DESC
security_id ASC
```

---

## BREAKOUT_PREP

```text
stock_rs20_pct DESC
DIST_HIGH20 DESC
TREND_R2_20 DESC
security_id ASC
```

---

## STRONG_PULLBACK

```text
stock_rs60_pct DESC
MDD20 DESC
RS20 DESC
security_id ASC
```

---

## STEADY_TREND

```text
stock_rs20_pct DESC
TREND_R2_20 DESC
MDD20 DESC
security_id ASC
```

---

## EARLY_MOVER_ONLY

```text
stock_rs5_pct DESC
AMOUNT_RATIO_5_20 DESC
RET5 DESC
security_id ASC
```

得到：

```text
within_pattern_rank_pct
```

然后：

```text
PATTERN_RANK_POINTS
=
30 * within_pattern_rank_pct
```

---

# 34. Sector Context Points

只取最高一档，不叠加。

```text
primary Leader sector = REACCELERATION
→ 20

primary Leader sector = CURRENT_STRENGTH
→ 18

非Leader，但存在 REACCELERATION
→ 14

非Leader，但存在 CURRENT_STRENGTH
→ 12

只有 STABILIZATION
→ 6

无正式强板块
→ 0
```

---

# 35. Quality Context

初始：

```text
10
```

扣分：

```text
LATE_EXTENSION_WARNING
-3

HIGH_CONCENTRATION_SECTOR_CONTEXT
-2

LOW_SECTOR_COVERAGE_CONTEXT
-3

MULTIPLE_LEADER_SECTORS
0
```

最低：

```text
0
```

---

# 36. Priority Percentile

Priority Score 完成后，在：

```text
当日 Candidate Pool
```

内部：

```text
rank(
 pct=True,
 method="average",
 ascending=True
)
```

得到：

```text
research_priority_pct
```

---

# 37. A+/A/B/C

完全继承 V0.3 的横截面等级边界：

```text
A+ : pct >= 0.95

A  : 0.85 <= pct < 0.95

B  : 0.65 <= pct < 0.85

C  : pct < 0.65
```

正式语义：

```text
DAILY CROSS-SECTIONAL
CANDIDATE-POOL-RELATIVE
RESEARCH PRIORITY
```

绝不是：

```text
上涨概率
胜率
目标收益
买入评级
```

---

# 38. 当前生产截面 — 2026-09-04

以下用于帮助审计者理解实际行为，不代表历史稳定性。

---

## 38.1 Market

```text
NORMAL_UNIVERSE = 5461

breadth RET5 positive  = 44.44%
breadth RET20 positive = 55.28%
breadth RET60 positive = 46.26%

above MA20 = 50.81%
above MA60 = 57.94%

market median RET5  = -0.42%
market median RET20 = +1.20%
market median RET60 = -1.06%

median MDD20 = -8.69%

median AMOUNT_RATIO_5_20
= 0.9874
```

---

## 38.2 Sector

有效板块：

```text
503
```

当前：

```text
CURRENT_STRENGTH = 76
STABILIZATION    = 25
REACCELERATION   = 16
NONE             = 386
```

---

## 38.3 Stock Scanner

```text
STEADY_TREND    = 198
STRONG_PULLBACK = 345
BREAKOUT_PREP   = 304
SECTOR_LEADER   = 502
EARLY_MOVER     = 86
```

注意：

这些 Scanner 可以重叠。

---

## 38.4 Candidate

```text
Candidate Pool = 1013
Outside Pool   = 4448
```

---

## 38.5 Research Priority

```text
A+ = 51
A  = 101
B  = 203
C  = 658
```

当前：

```text
A+ 和 A
全部来自 SECTOR_LEADER primary pattern
```

这是生产规则当前截面的真实结果。

没有人工配额。

---

# 39. Production Freshness

当前正式生产版本：

```text
daily-production-v1.1
```

每次 PRECHECK 计算：

```text
production-source-fingerprint-v1.0
```

覆盖：

```text
cutoff
.day source state
gbbq
gbbq.map
tdxhy
tdxzs
infoharbor_block
SH/SZ/BJ TNF
master calendar
```

---

# 40. Same Cutoff Revision

正式：

```text
same cutoff
+
same fingerprint
=
VERIFIED_NO_NEW_DATA
```

但：

```text
same cutoff
+
changed fingerprint
=
SAME_CUTOFF_SOURCE_REVISION
```

此时：

```text
重新运行正式链
+
same-date atomic replace
```

这是为了处理：

```text
同一天TDX membership修订
gbbq修订
TNF修订
尾bar修订
```

---

# 41. V0.3 与最终生产实现：哪些保持完全一致？

以下核心没有改变：

```text
本地TDX为唯一正式生产源
TDX只读
MARKET.CODE身份
NORMAL_UNIVERSE
前复权后做趋势结构
CURRENT_TDX_MEMBERSHIP
非PIT限制
Synthetic Sector由成员股票聚合
行业/主题/风格分域
Sector validity / coverage
CURRENT_STRENGTH
STABILIZATION
REACCELERATION
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
SECTOR_LEADER
EARLY_MOVER
Candidate Pool
A+/A/B/C只表示研究优先级
可解释输出
不做上涨概率
不做自动交易
不做外部数据
```

---

# 42. V0.3 原文中“缺失 / 未冻结”，后来被正式补齐的部分

这部分是本文最重要的补充。

---

## 42.1 Adjustment 从概念要求变成 TDX_NATIVE_AFFINE_QFQ

V0.3 只要求必须建立可靠 Adjustment Contract。

后来实际确定：

```text
TDX .day
+
TDX gbbq
+
Affine QFQ
```

并处理：

```text
现金
送转
配股
停牌跨事件
future ex-day
ROUND_HALF_UP
```

这是正式补齐，不改变 V0.3 原则。

---

## 42.2 Factor 范围从“大候选集合”收敛到正式29个

V0.3 原文还包含：

```text
RET1/3/120
MA120/250
多种MA Slope
UP_DAY_RATIO
VOLATILITY60
POS250
DIST_HIGH120/250
```

生产第一版没有把所有这些都放进正式 Factor Snapshot。

而是冻结 29 个当前真正需要的原子字段。

这是工程范围收敛。

---

## 42.3 Market Regime 没有采用 STRONG/NORMAL/WEAK

V0.3 设想：

```text
STRONG
NORMAL
WEAK
```

生产版：

```text
Market Factor Vector / Context Only
```

这是有意更保守。

---

## 42.4 Sector Composite Score 没有生产化

V0.3 曾给出：

```text
RS
Breadth
Trend
Volume
New High
Penalty
```

以及建议权重。

生产 Phase3 最终没有实现：

```text
Sector Score 0~100
```

而是：

```text
Hard Gates
+
Deterministic Conditions
+
Reason Codes
```

因此正式 Sector Scanner 更接近规则分类器，而不是加权评分器。

---

## 42.5 Stock Scanner 的正式规则与 V0.3 初始建议不同

例如 V0.3 STEADY_TREND 曾建议：

```text
RET20 > Universe 70 percentile
UP_DAY_RATIO20 >= .60
TREND_R2 >= .70
MA5 > MA10 > MA20
MA20 slope positive
Return Concentration不过高
```

生产 V1 则使用：

```text
RET20/60 positive
Slope20/60 positive
R²20/60门槛
POS60
MDD20/60
DIST_HIGH20
RS20
```

并没有直接使用：

```text
UP_DAY_RATIO
MA5>MA10>MA20
RETURN_CONCENTRATION
```

作为 hit gate。

这是正式实现变化。

---

## 42.6 BREAKOUT_PREP 没有显式“区间收窄/波动收敛”条件

V0.3 明确强调：

```text
横盘
收敛
RANGE ratio / ATR ratio / VOL ratio
```

生产 V1 实际条件主要是：

```text
Near High
Position
Trend
RS
RET20
AMOUNT_RATIO
```

没有一个正式：

```text
RANGE_10/RANGE_20
ATR_10/ATR_20
VOLATILITY_10/VOLATILITY_20
```

Gate。

这是非常值得外部审计的一点。

---

## 42.7 SECTOR_LEADER 比 V0.3 初始设计更简单

V0.3 建议综合：

```text
RS5 rank
RS20 rank
Trend R² rank
Near High rank
Return rank
Drawdown rank
```

生产 V1 核心：

```text
股票基础结构
+
member_rs20_pct top20%
+
member_ret20_pct / member_pos60_pct
+
强板块背景
```

这是明显的实现收敛。

---

## 42.8 EARLY_MOVER 也发生了收敛

V0.3 设想：

```text
板块中性
RS领先
Near High
Trend quality高
```

生产版：

```text
RET5
RS5
RET5 >= RET20
Slope20 > 0
Amount expansion
stock_rs5_pct >= .80
无 CURRENT_STRENGTH / REACCELERATION 板块
```

没有显式 Near High / R² Gate。

---

## 42.9 Research Priority 的正式架构与 V0.3 初始权重不同

V0.3 建议：

```text
40% Stock Structure
25% Sector Structure
20% Relative Strength
15% Multi-Scanner Confirmation
```

生产 V1：

```text
40 Primary Pattern Base
30 Within-Pattern Rank
20 Sector Context
10 Quality
```

并且明确：

```text
Multi-Scanner hit count不加分
Membership数量不加分
Leader sector数量不加分
```

原因是防止重复计价。

这是 Phase5 最重要的设计收敛之一。

---

# 43. 建议 Astra 重点审计的问题

以下不是已经确认的 Bug。

它们是：

```text
DESIGN REVIEW QUESTIONS
```

---

## Q1. V0.3 仍作为最高基线是否合理？

当前后续 Contract 已经非常详细。

应审计：

> V0.3 是否应继续作为最高项目设计基线，同时让 Phase1—6.1 Contracts 作为子合同；还是应该在不修改当前行为的前提下，整理一份新的“V0.3 IMPLEMENTED AS-BUILT SPEC”？

---

## Q2. Market Regime 完全 Context-Only 是否太保守？

当前市场环境不改变 Scanner。

优点：

```text
不引入未经验证的动态阈值
```

风险：

```text
弱市场和强市场使用完全相同的结构门槛
```

Astra 应判断：

> 是否继续维持 Context-Only，直到 Forward evidence 足够；还是需要未来设计一个非常弱的 regime-aware modifier？

当前不应直接修改 V1。

---

## Q3. STYLE Sector 是否导致重复表达 / 循环强化？

当前 Sector Type：

```text
INDUSTRY
THEME
STYLE
```

STYLE 中存在类似：

```text
近期强势
昨日连板
昨日涨停
昨日上榜
最近异动
近期新高
```

这些 STYLE membership 本身就可能由价格行为生成。

而系统又用股票价格 Factor 聚合这些 STYLE：

```text
股票涨得强
→ 被TDX归入“近期强势”
→ “近期强势”STYLE聚合很强
→ 股票成为强STYLE中的SECTOR_LEADER
→ Priority Base提高
```

这可能形成：

```text
PRICE SIGNAL
→ STYLE MEMBERSHIP
→ SECTOR STRENGTH
→ LEADER
→ PRIORITY
```

的重复表达。

这并不是未来函数，但可能是：

```text
semantic double counting
```

这是目前最值得 Astra 审计的结构风险之一。

建议 Astra 特别比较：

```text
INDUSTRY Leader
THEME Leader
STYLE Leader
```

是否应该拥有完全相同的 Sector Context 权重。

---

## Q4. A+/A 全部是 SECTOR_LEADER 是否说明 Priority 架构过度偏向 Leader？

当前截面：

```text
A+ 51/51 = SECTOR_LEADER
A 101/101 = SECTOR_LEADER
```

这是固定规则结果，不是实现Bug。

但需要审计：

```text
SECTOR_LEADER base = 40

+
Leader sector context = 18 / 20

+
Within-pattern rank
```

是否让其它结构：

```text
BREAKOUT_PREP
STRONG_PULLBACK
STEADY_TREND
EARLY_MOVER
```

几乎没有进入高研究等级的数学空间。

特别需要判断：

> Research Priority 的目标究竟是“统一跨结构排序”，还是“每种结构内部先选最值得研究的，再进行跨模式排序”？

当前系统选择后者的一部分，但 Primary Base 差异仍然强。

---

## Q5. Candidate Pool = 1013 是否仍满足“显著减少复盘范围”？

```text
1013 / 5461
≈ 18.55%
```

如果用户需要人工逐一看 1013 只，显然仍然太多。

但：

```text
A+ + A = 152
```

约占全市场：

```text
2.78%
```

所以可能实际使用语义应为：

```text
Candidate Pool = broad structural universe
A+/A = primary manual review pool
```

Astra 应审计这种分层是否合理。

---

## Q6. BREAKOUT_PREP 是否缺少其名字中最关键的“收敛”？

当前规则能找：

```text
接近高点
中短期强
趋势向上
成交不弱
```

但不一定能区分：

```text
强势横盘收敛
```

与：

```text
已经快速拉升接近高点
```

虽然有：

```text
LATE_EXTENSION_WARNING
```

但这不是 range contraction。

Astra 应审计是否未来需要：

```text
RANGE contraction
ATR contraction
Volatility contraction
```

之一。

---

## Q7. STEADY_TREND 是否缺少“上涨持续性”直接因子？

V0.3 原意强调：

```text
不涨停但是涨不停
```

生产规则主要使用：

```text
return
slope
R²
drawdown
position
```

没有直接使用：

```text
UP_DAY_RATIO20
RETURN_CONCENTRATION20
```

这些实际上很贴近：

```text
持续上涨
vs
单日脉冲
```

Astra 应判断：

> R² + MDD 是否已经足够表达“稳态”，还是应在未来 V2 引入 Up-Day / Return-Concentration？

---

## Q8. STRONG_PULLBACK 是否足够区分“正常回踩”和“趋势转坏早期”？

当前使用：

```text
RET60
Slope60
R²60
RS60
POS60
MDD20
DIST_HIGH20
adj_close > MA60
```

但没有：

```text
pullback期间量能收缩
```

V0.3 原始目标有：

```text
调整成交下降
```

生产 V1 没有把它作为必需 Gate。

值得审计。

---

## Q9. SECTOR_LEADER 是否过度依赖 RS20？

当前板块内：

```text
member_rs20_pct >= .80
```

是硬条件。

再加：

```text
member_ret20_pct
或
member_pos60_pct
```

但没有：

```text
member trend R² percentile
member drawdown percentile
member RS5 percentile
```

V0.3 原设计更丰富。

Astra 应判断：

> 当前 Leader 是“板块内20日强股”还是“真正结构核心”？

---

## Q10. SECTOR_LEADER Pattern Rank 混用了 best-sector context 和 primary-Leader context

Phase5 的 SECTOR_LEADER pattern rank：

```text
best_sector_rs20_pct
primary_member_rs20_pct
stock_rs20_pct
```

但是 Phase6.1 已明确：

```text
best_sector
```

与：

```text
primary_leader_sector
```

在 502 个 Leader 中：

```text
254 相同
248 不同
```

这意味着排序第一键可能来自：

```text
一个“最佳上下文板块”
```

而第二键来自：

```text
另一个“主Leader板块”
```

这可能是合理的：

```text
综合最优环境 + 主Leader身份
```

也可能存在语义混用。

这是一个很值得外部审计的问题。

---

## Q11. Sector Context 是否应该区分 INDUSTRY / THEME / STYLE？

当前：

```text
REACCELERATION = 20
CURRENT_STRENGTH = 18
```

主要看 pattern。

并不因为：

```text
INDUSTRY
THEME
STYLE
```

而拥有不同权重。

考虑 STYLE 的价格行为属性，Astra 应重点审计：

> STYLE context 与 INDUSTRY/THEME context 是否应该完全等价。

---

## Q12. 当前没有 Forward Performance Evidence 时，是否应该修改任何阈值？

建议审计原则：

```text
NO
```

当前 V1 已工程闭环。

在没有积累真实 Forward Snapshot / Future Outcome 前：

```text
不要因为单日结果“看起来奇怪”
就改规则
```

Astra 最好把建议分成：

```text
P0 correctness bug
P1 structural design issue
P2 future V2 experiment
```

而不是把所有意见直接变成改代码任务。

---

# 44. 当前设计的优点

供 Astra 审计时避免只看缺点。

---

## 44.1 数据边界极清晰

```text
本地TDX
只读
无外部补数
```

---

## 44.2 价格口径已经解决

不再是：

```text
raw price混合除权断层
```

正式：

```text
TDX_NATIVE_AFFINE_QFQ
```

---

## 44.3 Factor 是原子层

Phase1 不提前“选股”。

---

## 44.4 Sector 不依赖黑箱指数

Synthetic Sector 直接看内部成员。

---

## 44.5 NULL 不等于0

数据质量不会静默伪造。

---

## 44.6 行业/主题/风格分域

避免三种完全不同的板块横截面混排。

---

## 44.7 Scanner 是解释性规则

每个命中可以追溯：

```text
factor
threshold
reason code
```

---

## 44.8 Priority 防多标签累加

避免：

```text
概念多
=
天然高分
```

---

## 44.9 Research Priority 明确不是概率

没有把研究排序包装成预测能力。

---

## 44.10 Production 已有完整 freshness / hash / atomic publication

生产正确性与模型规则分开治理。

---

# 45. 当前设计的主要限制

```text
1. CURRENT membership 非PIT
2. 无正式历史回测能力
3. Market Regime 不参与决策
4. STYLE可能存在信号重复表达
5. Sector Leader权重较强
6. Candidate Pool仍较宽
7. Breakout Prep缺显式收敛Factor
8. Steady Trend未直接使用up-day / return concentration
9. Pullback未直接使用缩量Gate
10. Index Contract未建立
11. 无外部基本面 / 新闻 / 资金信息
12. 无分钟 / Tick / L2
13. 无Forward统计晋级证据
```

其中 1 是正式限制。

3～9 属于设计审计问题。

10～12 属于未来扩展。

13 是任何 V2 参数调整前最重要的证据缺口。

---

# 46. Astra 审计时建议采用的判定格式

建议不要只输出：

```text
好 / 不好
```

而采用：

```text
BASELINE_ALIGNMENT
= PASS / PARTIAL / FAIL

DATA_MODEL
= PASS / ...

FACTOR_DESIGN
= PASS / ...

SECTOR_AGGREGATION
= PASS / ...

SECTOR_SCANNER
= PASS / ...

STOCK_SCANNER
= PASS / ...

CANDIDATE_POOL
= PASS / ...

RESEARCH_PRIORITY
= PASS / ...

PRODUCTION_GOVERNANCE
= PASS / ...

CRITICAL_DESIGN_RISKS
= [...]

NON_BLOCKING_DESIGN_RISKS
= [...]

V2_EXPERIMENTS
= [...]

DO_NOT_CHANGE_BEFORE_FORWARD_EVIDENCE
= [...]
```

---

# 47. 希望 Astra 明确回答的最终问题

请 Astra 对以下问题给出明确判断：

1. `V0.3 FINAL IMPLEMENTATION BASELINE` 是否仍然足以作为当前最高业务设计基线？
2. Phase1—6.1 的实际实现是否仍忠于 V0.3 核心目标？
3. 上述实现收敛中，哪些属于合理工程冻结，哪些已经构成设计偏离？
4. 29 个正式 Factor 是否足够支撑当前五类 Stock Scanner？
5. Market Context-Only 是否合理？
6. Synthetic Sector 的聚合方案是否存在明显统计或语义问题？
7. Sector Scanner 三类规则是否具有良好可分性？
8. STYLE sector 是否造成循环/重复信号？
9. Stock Scanner 的四类 + EARLY_MOVER 是否真正覆盖 V0.3 原始目标？
10. BREAKOUT_PREP 是否必须补 contraction factor？
11. STEADY_TREND 是否应恢复 Up-Day Ratio / Return Concentration？
12. STRONG_PULLBACK 是否应增加 pullback volume contraction？
13. SECTOR_LEADER 是否过度依赖 RS20？
14. Phase5 Anti-Double-Counting 是否设计正确？
15. A+/A 全为 SECTOR_LEADER 是合理结构结果还是架构性偏置？
16. `best_sector_rs20_pct + primary_member_rs20_pct` 的混合排序是否合理？
17. INDUSTRY / THEME / STYLE 是否应该使用相同 Sector Context 权重？
18. Candidate Pool 1013 是否过宽？
19. A+/A 152 只作为主要复盘池是否足够完成“压缩人工复盘范围”的目标？
20. 在没有 Forward Evidence 前，哪些参数绝对不应该修改？

---

# 48. 审计材料建议组合

如果 Astra 能同时读取多份文件，建议至少提供：

```text
1. TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md
2. 本文档
3. PHASE6_1_FINAL_RECEIPT.json
4. DAILY_PRODUCTION_CONTRACT_V1.md
5. market_summary.html（可选，用于看当前真实输出）
```

如果只能提供两份：

```text
V0.3 FINAL
+
本文档
```

本文已经补齐正式生产实现链。

---

# 49. 本文档与 V0.3 的关系

本文：

```text
不是 V0.4
不是 V1.0 新方案
不是模型升级任务
```

它的身份是：

```text
V0.3 IMPLEMENTATION / AS-BUILT AUDIT SUPPLEMENT
```

作用：

> 把 V0.3 设计之后，通过 Phase0—6.1 实际冻结的公式、阈值、规则、优先级、生产行为和设计差异集中写清楚，让外部审计者不必从几十份阶段任务卡和 Receipt 中反向拼接真实系统。

---

# 50. 当前最终项目身份

```text
PROJECT
=
TDX Market Structure Scanner

DESIGN BASELINE
=
V0.3 FINAL IMPLEMENTATION BASELINE

PRODUCTION
=
daily-production-v1.1

PRICE BASIS
=
TDX_NATIVE_QFQ / FORWARD_ADJUSTED

MEMBERSHIP
=
CURRENT_TDX_MEMBERSHIP

HISTORICAL PIT
=
FALSE

EXTERNAL DATA
=
FALSE

INDEX OHLC
=
FALSE

PRODUCTION READY
=
TRUE

MAINLINE DEVELOPMENT
=
CLOSED
```

---

# END

**建议 Astra 将当前系统视为：**

> 一个已经完成工程闭环、但尚未经过长期 Forward Statistical Promotion 的“可解释市场结构发现引擎”。

审计重点应该从：

```text
能不能运行？
数据有没有明显错误？
```

转向：

```text
这些结构定义是否最能表达我们的真实研究目标？
是否存在信号重复计价？
哪些V0.3原始思想在生产收敛中被削弱？
哪些应保持到Forward证据出现后再调整？
```

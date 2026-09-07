# 通达信A股市场结构扫描器
## TDX Market Structure Scanner — V0.3 FINAL IMPLEMENTATION BASELINE

**文档状态**：当前最高项目设计与实施基线  
**版本**：V0.3 FINAL  
**日期**：2026-09-04  
**目标阶段**：Weekend MVP  
**项目定位**：本地、盘后、只读通达信数据的A股市场结构发现工具  
**核心原则**：先保证数据口径可靠，再讨论Scanner有效性；先交付真实可运行结果，再扩展分时、AI和外部数据

---

# 1. 项目目标

每日收盘后，在用户完成通达信本地行情更新后，通过一条命令完成全市场结构扫描：

```bash
python run_daily.py --date latest
```

系统自动执行：

```text
通达信本地行情
↓
只读审计
↓
标准化行情
↓
复权/价格口径处理
↓
Universe
↓
Factor Engine
↓
Market Regime
↓
Synthetic Sector
↓
Sector Scanner
↓
Stock Scanner
↓
Candidate Pool
↓
Research Priority
↓
HTML / CSV / Audit
```

目标是将：

```text
5000+ 股票
+
大量行业/概念/风格板块
```

压缩成：

```text
少量重点板块
+
少量结构候选股
+
每个候选明确的结构原因
+
明确的数据质量与限制说明
```

---

# 2. V0.3 Weekend MVP 要回答的问题

## 2.1 板块

1. 当前真正强势的板块有哪些；
2. 哪些板块属于前期较强、目前调整企稳；
3. 哪些板块正在从调整进入二次上攻；
4. 哪些板块内部Breadth正在扩散；
5. 哪些板块只是少数龙头独舞；
6. 哪些板块因成员不足或有效覆盖不足，不应该参与正式排名。

## 2.2 个股

1. 哪些股票不涨停但持续稳定上涨；
2. 哪些股票属于强趋势中的正常回踩；
3. 哪些股票处于横盘收敛、接近突破；
4. 哪些股票是所属板块内部核心；
5. 哪些股票已经提前强于所属板块；
6. 哪些股票因为复权、样本不足或数据质量问题只能标记为实验性结果。

---

# 3. 数据边界

## 3.1 唯一正式数据源

V0.3 只允许使用用户本地通达信数据。

允许读取：

```text
个股日K .day
指数日K .day
行业映射
概念板块
风格板块
权息/复权相关本地数据（若真实存在且可可靠解析）
其他经Phase 0审计确认稳定可用的通达信本地文件
```

典型目录仅作为参考：

```text
TDX_ROOT/
├─ vipdoc/
│  ├─ sh/
│  │  └─ lday/
│  ├─ sz/
│  │  └─ lday/
│  └─ ...
└─ T0002/
   └─ hq_cache/
      ├─ block_gn.dat
      ├─ block_fg.dat
      ├─ block_zs.dat
      ├─ tdxhy.cfg
      └─ ...
```

**禁止根据网上示例假设本机一定存在任何文件。**

---

## 3.2 V0.3 明确禁止

未经用户批准，不得引入：

```text
分时
Tick
Level2
新闻
财务数据
东方财富
同花顺
AkShare
84x
网络爬虫
外部API
LLM预测
AI自动选股
XGBoost
神经网络
强化学习
自动交易
自动下单
上涨概率
胜率承诺
数据库集群
微服务
Docker
Redis
Kafka
历史PIT板块数据库
外部复权服务
```

---

# 4. 核心架构原则

## 4.1 通达信数据只读

严禁修改：

```text
*.day
*.cfg
*.dat
vipdoc/
T0002/
```

项目数据流：

```text
TDX原始数据
↓
只读解析
↓
项目自有标准化数据
↓
项目派生数据
```

---

## 4.2 通达信根目录必须可配置

```yaml
tdx:
  root: "D:/TDX/new_tdx"
```

优先级：

```text
1. config
2. 环境变量 TDX_ROOT
3. 自动探测
```

不得在业务代码中写死盘符。

---

## 4.3 数据分层

推荐：

```text
tdx-market-scanner/
├─ config/
├─ data/
│  ├─ normalized/
│  ├─ adjusted/
│  ├─ factors/
│  ├─ sectors/
│  ├─ candidates/
│  └─ cache/
├─ reports/
├─ src/
├─ tests/
├─ docs/
├─ PROJECT_SPEC.md
├─ AGENTS.md
└─ run_daily.py
```

---

# 5. Phase 0 总目标

正式名称：

```text
PHASE 0 — DATA, ADJUSTMENT & FACTOR CONTRACT PREFLIGHT
```

Phase 0 不允许直接开发完整Scanner。

必须完成：

```text
真实TDX目录审计
↓
.day二进制契约
↓
证券身份与类型识别
↓
文件稳定性检查
↓
复权能力审计
↓
板块成员能力审计
↓
Universe契约
↓
Factor Contract
↓
GO / DEGRADED / BLOCKED 判定
```

---

# 6. Phase 0 最终三级状态

## 6.1 FULL_PASS

满足：

```text
.day解析可靠
证券类型识别可靠
交易日对齐可靠
复权数据可靠且可复算
板块成员可解析
Factor Contract完整
```

允许：

```text
全部V0.3正式Scanner
```

---

## 6.2 DEGRADED_PASS

满足：

```text
.day解析可靠
证券类型识别可靠
交易日对齐可靠
数据管线可运行
板块成员可用
```

但：

```text
复权数据缺失 / 不可靠 / 无法完整复算
```

此时允许：

```text
数据标准化
Universe
报告框架
板块成员分析
不依赖复权的有限统计
实验性Factor
实验性Trend Scanner
```

所有依赖复权的结果必须标记：

```text
EXPERIMENTAL
PRICE_ADJUSTMENT_LIMITATION = TRUE
```

不得宣布：

```text
Trend Scanner正式PASS
```

---

## 6.3 BLOCKED

以下任意发生：

```text
.day解析无法验证
价格/成交量单位无法确定
股票与非股票证券无法区分
日期对齐存在原则性错误
读取到半条/损坏记录无法安全治理
TDX原始数据发生写入冲突
```

则：

```text
BLOCKED
```

禁止进入正式Scanner开发。

---

# 7. `.day` 二进制契约

必须真实验证：

```text
record_length
endianness
date_encoding
open unit
high unit
low unit
close unit
amount unit
volume unit
保留字段
尾记录完整性
重复日期
异常日期
零成交
停牌表现
```

至少对：

```text
上海主板
深圳主板
创业板
科创板
北交所（如本机存在）
```

人工与通达信界面最后若干根K线交叉验证。

---

# 8. 文件稳定性检查

为避免通达信正在写入文件时读取半条记录，Phase 0必须定义：

```text
FILE_STABILITY_CHECK
```

建议流程：

```text
读取 size / mtime
↓
等待短暂稳定窗口
↓
再次读取 size / mtime
↓
确认未变化
↓
检查 file_size % record_length == 0
↓
允许读取
```

如果：

```text
size变化
mtime变化
尾记录不完整
```

则：

```text
FILE_UNSTABLE
```

本次运行不得消费该文件。

---

# 9. 证券唯一标识

内部唯一键：

```text
MARKET.CODE
```

示例：

```text
SH.600000
SZ.000001
SZ.300750
SH.688XXX
BJ.XXXXXX
```

禁止仅使用六位代码作为长期唯一键。

---

# 10. 证券类型契约

至少识别：

```text
A_STOCK
INDEX
ETF
FUND
CONVERTIBLE_BOND
OTHER
```

NORMAL_UNIVERSE只能纳入：

```text
security_type = A_STOCK
```

如果：

```text
历史ST
历史证券名称
历史退市状态
```

本地无法可靠获取，则：

```text
SECURITY_MASTER_CAPABILITY = LIMITED
```

并在Audit中披露。

---

# 11. expected_a_stock_count 定义

不得循环定义。

Phase 0必须冻结：

```text
市场目录范围
代码段规则
security_type判定规则
排除规则
有效日K存在条件
```

最终：

```text
expected_a_stock_count
=
根据冻结后的市场+代码+证券类型规则
识别出的“理论应参与解析的A股证券数”
```

解析率：

```text
parse_success_ratio
=
parsed_a_stock_count
/
expected_a_stock_count
```

---

# 12. 复权契约

`PRICE_BASIS`不能只是字符串标签。

Phase 0必须建立：

```text
ADJUSTMENT_CONTRACT
```

---

## 12.1 必须记录调整因子来源

例如：

```text
adjustment_source
adjustment_file
adjustment_version
adjustment_fingerprint
```

实际来源必须来自用户本地TDX。

禁止联网补齐。

---

## 12.2 必须定义调整因子日期语义

必须回答：

```text
factor在除权日前生效还是当日生效
factor对应哪个交易日
累计因子方向
前复权/后复权基准日
```

---

## 12.3 OHLC调整

必须统一：

```text
AdjustedOpen
AdjustedHigh
AdjustedLow
AdjustedClose
```

使用同一价格调整比例。

不得只调整Close而不调整OHLC。

---

## 12.4 Volume调整

必须显式定义：

```text
VOLUME_ADJUSTMENT_RULE
```

若采用价格按比例调整，则必须明确：

```text
成交量是否反向调整
```

不得默认猜测。

---

## 12.5 Amount

必须明确：

```text
AMOUNT_BASIS
```

V0.3原则上优先保留通达信原始成交额：

```text
amount = RAW_AMOUNT
```

除非真实数据契约证明必须调整。

---

## 12.6 Corporate Action类型

至少审计：

```text
现金分红
送股
转增
配股
拆并股
其他TDX可识别公司行为
```

必须说明本地数据能覆盖哪些。

---

## 12.7 缺失因子

若某证券复权因子：

```text
缺失
异常
不连续
```

则：

```text
ADJUSTMENT_STATUS = INVALID
```

该证券不得进入正式Trend类Scanner。

---

## 12.8 复权历史修订

必须记录：

```text
adjustment_fingerprint
```

若调整因子历史发生变化：

```text
ADJUSTMENT_HISTORY_REVISED
```

则重新计算：

```text
受影响历史价格
↓
Factor
↓
Sector
↓
Scanner
```

---

# 13. Price Basis

正式值：

```text
RAW
FORWARD_ADJUSTED
BACKWARD_ADJUSTED
LOCAL_DYNAMIC_ADJUSTED
```

项目统一：

```text
PROJECT_PRICE_BASIS
```

所有正式Trend因子必须共享同一口径。

---

# 14. 标准化数据

## 14.1 stock_daily.parquet

```text
security_id
market
code
date
open
high
low
close
amount
volume
source
raw_fingerprint
```

---

## 14.2 adjusted_daily.parquet

如果复权可靠：

```text
security_id
date
adj_open
adj_high
adj_low
adj_close
adj_volume_if_applicable
raw_amount
adjustment_factor
price_basis
adjustment_status
```

---

## 14.3 stock_master.parquet

```text
security_id
market
code
security_type
board
history_days
is_active
is_st_if_available
name_if_available
source
```

---

## 14.4 sector_membership.parquet

```text
sector_type
sector_code
sector_name
security_id
membership_basis
source
```

统一：

```text
membership_basis = CURRENT_TDX_MEMBERSHIP
```

---

# 15. Universe

## 15.1 FULL_UNIVERSE

全部可成功识别证券。

用于：

```text
审计
数据质量
留档
```

---

## 15.2 NORMAL_UNIVERSE

正式股票扫描池。

统一初始条件：

```text
security_type = A_STOCK
history_days >= 120
最近20个交易日数据有效
非长期无成交
非明显已失效证券
```

---

## 15.3 60日与120日冲突修正

V0.3统一：

```text
NORMAL_UNIVERSE min_history = 120
```

因此：

```text
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
```

正式扫描均要求：

```text
history_days >= 120
```

不再使用60日作为正式Universe最低门槛。

---

## 15.4 MA250样本不足

如果：

```text
history_days < 250
```

则：

```text
MA250 = NULL
POS250 = NULL
DIST_HIGH250 = NULL
```

不得填充、外推。

任何Scanner若依赖MA250：

```text
必须声明 requires_250d = true
```

V0.3核心Scanner不强制依赖MA250。

---

# 16. 交易日对齐

所有横截面必须：

```text
按交易日T
↓
使用T日有效NORMAL_UNIVERSE
```

不得跨日期混算。

RS：

```text
Market Median RET_N
```

只能使用：

```text
T日可用且满足相应Factor样本要求的证券
```

---

# 17. Factor Contract

每个Factor必须定义：

```text
name
formula
window
min_samples
include_t
null_rule
universe
price_basis
version
```

---

# 18. Return

```text
RET_N(t)
=
Close(t) / Close(t-N) - 1
```

N：

```text
1
3
5
10
20
60
120
```

正式Trend环境下：

```text
Close = adjusted_close
```

---

# 19. Moving Average

```text
MA_N(t)
=
mean(Close[t-N+1:t])
```

N：

```text
5
10
20
60
120
250
```

样本不足：

```text
NULL
```

---

# 20. MA Slope

正式避免歧义：

```text
MA20_SLOPE_5D
=
MA20(t) / MA20(t-5) - 1
```

同理：

```text
MA5_SLOPE_3D
MA10_SLOPE_5D
MA20_SLOPE_5D
MA60_SLOPE_10D
```

---

# 21. Position

```text
POS_N(t)
=
(Close(t) - LowestLow_N(t))
/
(HighestHigh_N(t) - LowestLow_N(t))
```

包含当日。

分母0：

```text
NULL
```

---

# 22. Distance From High

```text
DIST_HIGH_N(t)
=
Close(t) / HighestHigh_N(t) - 1
```

其中：

```text
HighestHigh_N(t)
=
MAX(High[t-N+1:t])
```

包含当日。

---

# 23. Max Drawdown

```text
MAX_DRAWDOWN_N(t)
=
min_j
(
Close(j) / max_{i<=j} Close(i) - 1
)
```

结果：

```text
<= 0
```

---

# 24. Up Day Ratio

```text
UP_DAY_RATIO_N
=
Count(Close(t) > Close(t-1))
/
有效比较日数量
```

---

# 25. Volatility

```text
VOLATILITY_N
=
std(log_return_1d)
```

V0.3统一使用：

```text
sample standard deviation
ddof = 1
```

---

# 26. Trend Regression

```text
y = log(adjusted_close)
x = 0...N-1
```

输出：

```text
TREND_SLOPE_N
TREND_R2_N
```

核心：

```text
20
60
```

Slope采用：

```text
每交易日log-price斜率
```

不受价格绝对值影响。

---

# 27. Amount

```text
AMOUNT_MA5
AMOUNT_MA10
AMOUNT_MA20
```

```text
AMOUNT_RATIO20
=
Amount(t) / AMOUNT_MA20(t)
```

Amount默认使用原始成交额。

---

# 28. Relative Strength

```text
RS_N(t)
=
Stock_RET_N(t)
-
Median_RET_N(t, valid NORMAL_UNIVERSE)
```

并生成：

```text
RS_PERCENTILE5
RS_PERCENTILE20
RS_PERCENTILE60
```

---

# 29. Return Concentration

```text
POSITIVE_RETURN_SUM_20
=
sum(max(ret_1d,0))
```

```text
MAX_POSITIVE_DAY_20
=
max(max(ret_1d,0))
```

```text
RETURN_CONCENTRATION_20
=
MAX_POSITIVE_DAY_20
/
POSITIVE_RETURN_SUM_20
```

如果分母为0：

```text
NULL
```

---

# 30. 增量更新

## 30.1 Raw

允许：

```text
append新交易日
```

---

## 30.2 Derived

新增T日必须重新计算：

```text
受影响Rolling窗口
T日横截面
T日RS Percentile
T日Sector Breadth
T日Scanner
```

---

## 30.3 历史修订检测

记录：

```text
file_size
mtime
hash/fingerprint
```

状态：

```text
NO_CHANGE
RAW_APPEND
RAW_HISTORY_REVISED
```

---

# 31. 原子写入

所有：

```text
Parquet
CSV
JSON
HTML
```

必须：

```text
先写 temporary file
↓
完整校验
↓
atomic replace
```

运行失败时不得留下半成品正式文件。

---

# 32. Market Regime

V0.3状态：

```text
STRONG
NORMAL
WEAK
```

指标：

```text
上涨股票比例
PCT_ABOVE_MA20
PCT_ABOVE_MA60
20D新高比例
20D新低比例
市场RET5中位数
市场RET20中位数
```

仅作环境标签。

---

# 33. Synthetic Sector

核心：

```text
CURRENT_TDX_MEMBERSHIP
+
成员个股Factor
↓
Synthetic Sector
```

通达信板块指数若存在，仅用于辅助校验。

---

# 34. 历史板块成员限制

历史Replay统一：

```text
REPLAY_MODE = APPROXIMATE_CURRENT_MEMBERSHIP
CURRENT_MEMBERSHIP_BIAS = TRUE
```

禁止宣称：

```text
POINT_IN_TIME
STRICT_NO_FUTURE_MEMBERSHIP
```

此问题不阻断：

```text
CURRENT DAILY SCAN
```

---

# 35. 板块有效性契约

必须新增：

```text
SECTOR_VALIDITY_CONTRACT
```

---

## 35.1 最小成员数

配置：

```text
MIN_SECTOR_MEMBERS
```

建议初始：

```text
industry = 5
concept = 8
style = 8
```

最终由Phase 0根据真实数据分布确认。

成员过少：

```text
SECTOR_TOO_SMALL
```

不得进入正式排名。

---

## 35.2 当日最小有效成员

配置：

```text
MIN_VALID_MEMBERS_ON_DATE
```

例如：

```text
>= 5
```

不足：

```text
INVALID_ON_DATE
```

---

## 35.3 有效覆盖率

```text
member_coverage_ratio
=
valid_member_count
/
total_member_count
```

配置：

```text
MIN_MEMBER_COVERAGE_RATIO
```

建议初始：

```text
0.70
```

低于阈值：

```text
LOW_MEMBER_COVERAGE
```

不得进入正式Sector Score排名。

---

## 35.4 停牌成员Breadth分母

V0.3统一：

> Breadth分母只使用当日具有有效价格状态且满足该Breadth因子输入要求的成员。

同时必须输出：

```text
total_member_count
valid_member_count
suspended_or_invalid_count
member_coverage_ratio
```

不得只显示百分比。

---

# 36. Sector Type分组

板块类型至少区分：

```text
industry
concept
style
```

任何：

```text
Sector percentile
Sector rank
Sector score percentile
```

必须：

```text
在相同 sector_type 内计算
```

禁止：

```text
industry
vs
concept
vs
style
```

直接混在同一横截面排名。

---

# 37. Sector Return

每个板块：

```text
MEDIAN_RET1
MEDIAN_RET3
MEDIAN_RET5
MEDIAN_RET10
MEDIAN_RET20
```

辅助：

```text
EQUAL_WEIGHT_RET
```

优先使用Median。

---

# 38. Sector Breadth

至少：

```text
PCT_UP
PCT_ABOVE_MA5
PCT_ABOVE_MA10
PCT_ABOVE_MA20
PCT_ABOVE_MA60
PCT_NEAR_HIGH20
PCT_NEAR_HIGH60
PCT_RS_TOP20
```

每个Breadth结果同时保存：

```text
valid_member_count
member_coverage_ratio
```

---

# 39. Sector Concentration

定义：

```text
POS_RETURN_i = max(RET1_i,0)
```

```text
TOP3_CONCENTRATION
=
sum(top3 POS_RETURN)
/
sum(all POS_RETURN)
```

无正收益：

```text
NULL
```

但只在：

```text
valid_member_count >= MIN_CONCENTRATION_MEMBERS
```

时计算。

建议初始：

```text
MIN_CONCENTRATION_MEMBERS = 8
```

---

# 40. Score Mapping

优先使用：

```text
cross-sectional percentile
```

并且：

```text
sector percentile
=
同sector_type内部百分位
```

综合Score：

```text
component raw value
↓
percentile / bounded score
↓
weighted aggregation
↓
0~100
```

必须保存：

```text
raw_components
normalized_components
weights
final_score
mapping_version
```

---

# 41. Sector Scanner

正式只做：

```text
CURRENT_STRENGTH
STABILIZATION
REACCELERATION
```

附加标签：

```text
BREADTH_EXPANSION
HIGH_CONCENTRATION
LOW_MEMBER_COVERAGE
```

---

# 42. CURRENT_STRENGTH

组件：

```text
RS20
RS5
Breadth
Trend
Volume Activity
New High Participation
Concentration Penalty
Volatility Penalty
```

初始权重允许：

```text
25% RS20
20% RS5
20% Breadth
15% Trend
10% Volume
10% New High
-
Penalty
```

但必须先标准化。

---

# 43. STABILIZATION

目标：

```text
前期较强
近期调整
结构未破坏
Breadth停止恶化
成交收缩
前排仍强
```

“停止恶化”等全部在Scanner Contract公式化。

---

# 44. REACCELERATION

目标：

```text
强势
↓
调整
↓
再次转强
```

关注：

```text
RS20仍强
过去5~10日调整
最近1~3日RS改善
Breadth回升
PCT_ABOVE_MA5改善
成交由收缩转扩张
前排重新逼近高点
```

输出：

```text
EARLY
CONFIRMED
OVERHEATED
```

---

# 45. Sector State

V0.3：

```text
WEAK
STRONG
PULLBACK
STABILIZING
REACCELERATING
```

采用：

```text
deterministic daily classification
```

暂不强制：

```text
minimum dwell time
hysteresis
confirmation days
```

如果Forward确认存在严重抖动，再升级。

---

# 46. Stock Scanner

正式：

```text
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
SECTOR_LEADER
```

标签：

```text
EARLY_MOVER
```

---

# 47. STEADY_TREND

统一要求：

```text
history_days >= 120
```

建议：

```text
RET20 > Universe 70 percentile
UP_DAY_RATIO20 >= 0.60
TREND_R2_20 >= 0.70
MA5 > MA10 > MA20
MA20_SLOPE_5D > 0
MAX_DRAWDOWN20受控
接近20/60日高位
RETURN_CONCENTRATION不过高
```

输出：

```text
GRINDER_SCORE
```

---

# 48. STRONG_PULLBACK

核心：

```text
RET60强
RS60强
MA20上行
近3~10日回撤
中期结构未破坏
调整成交下降
仍处于60日相对高位
```

---

# 49. BREAKOUT_PREP

关注：

```text
60日趋势良好
近20日横盘/整理
波动率下降
区间收窄
接近20/60日高点
RS未恶化
成交未失控
```

收窄必须从以下之一正式冻结：

```text
RANGE_10 / RANGE_20
ATR_10 / ATR_20
VOLATILITY_10 / VOLATILITY_20
```

禁止只写“横盘收敛”。

---

# 50. SECTOR_LEADER

同板块内部：

```text
RS5 rank
RS20 rank
Trend R² rank
Near High rank
Return rank
Drawdown rank
```

板块必须通过：

```text
SECTOR_VALIDITY_CONTRACT
```

后才能生成正式Leader。

---

# 51. EARLY_MOVER

定义：

```text
板块尚未明显强势
+
个股RS明显领先
+
接近阶段高点
+
趋势质量高
```

只作标签。

---

# 52. Candidate Pool

## Sector

```text
CURRENT_STRONG
STABILIZING
REACCELERATING
```

## Stock

```text
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
SECTOR_LEADER
EARLY_MOVER
```

允许多标签。

---

# 53. Research Priority

只表示：

```text
人工研究优先级
```

建议：

```text
40% Stock Structure
25% Sector Structure
20% Relative Strength
15% Multi-Scanner Confirmation
```

---

# 54. A+/A/B/C 评级契约

V0.3明确：

```text
A+/A/B/C
=
当日横截面相对研究优先级
```

不是跨日期绝对评级。

初始边界：

```text
A+ : >= 95 percentile
A  : >= 85 and <95
B  : >= 65 and <85
C  : <65
```

如果使用综合0~100 Score，则最终仍根据：

```text
当日Research Priority横截面百分位
```

生成等级。

必须记录：

```text
rating_basis = DAILY_CROSS_SECTIONAL
rating_version
```

---

# 55. Explainability

每个候选：

```text
score
percentile
rating
components
reasons
risk_flags
sector_context
data_quality_flags
```

示例：

```text
reasons:
- TREND_R2_HIGH
- RS20_TOP10
- MA_ALIGNMENT
- LOW_DRAWDOWN
- NEAR_60D_HIGH
- SECTOR_REACCELERATING
```

---

# 56. 输出文件

```text
reports/YYYYMMDD/
├─ market_summary.html
├─ sectors.csv
├─ stocks.csv
├─ candidates.csv
└─ run_audit.json
```

CSV：

```text
UTF-8 BOM
```

---

# 57. HTML报告

必须包含：

## 市场

```text
交易日
Market Regime
FULL / DEGRADED状态
有效股票数量
MA20以上比例
MA60以上比例
20D新高比例
20D新低比例
市场RET5中位数
市场RET20中位数
```

## 板块

必须显示：

```text
sector_type
sector_name
score
percentile
valid_member_count
member_coverage_ratio
top3_concentration
stage
data_quality_flags
```

## 个股

至少显示：

```text
20D Return
Up Days
Max Drawdown
Trend R²
RS Percentile
Return Concentration
Sector
Scanner Tags
Research Rating
```

---

# 58. Run Audit

每次运行必须记录：

```text
run_id
run_time
trade_date
run_status

tdx_root
tdx_latest_date

price_basis
adjustment_source
adjustment_version
adjustment_fingerprint

security_master_capability
membership_basis
replay_mode

stock_file_count
expected_a_stock_count
parsed_a_stock_count
parse_success_ratio

sector_count
sector_validity_version

raw_source_fingerprint
factor_contract_version
scanner_version
score_mapping_version
rating_version
universe_version
config_hash
code_version

runtime_seconds
warnings
errors
```

---

# 59. 历史回放

允许：

```text
近20个交易日
```

要求：

```text
行情严格截断到T日
```

但：

```text
CURRENT_MEMBERSHIP_BIAS = TRUE
```

用途：

```text
检查明显未来行情泄漏
检查Scanner基本识别能力
```

禁止用途：

```text
正式策略收益证明
严格PIT证明
历史最优参数搜索
```

---

# 60. Weekend MVP 时间安排

## 周五

完成：

```text
Phase 0
DATA, ADJUSTMENT & FACTOR CONTRACT PREFLIGHT
```

必须给出：

```text
FULL_PASS
DEGRADED_PASS
BLOCKED
```

之一。

---

## 周六上午

若：

```text
FULL_PASS
```

则：

```text
正式Factor Engine
```

若：

```text
DEGRADED_PASS
```

则：

```text
数据管线 + 实验性Factor
```

并标记限制。

---

## 周六下午

完成：

```text
Market Regime
Synthetic Sector
Sector Validity
Sector Factor
```

---

## 周六晚上

完成：

```text
CURRENT_STRENGTH
STABILIZATION
REACCELERATION
```

---

## 周日上午

完成：

```text
STEADY_TREND
STRONG_PULLBACK
BREAKOUT_PREP
SECTOR_LEADER
EARLY_MOVER
```

若处于DEGRADED_PASS：

```text
Trend类Scanner必须标记EXPERIMENTAL
```

---

## 周日下午

完成：

```text
Candidate Pool
Research Priority
HTML
CSV
Audit
```

---

## 周日晚上

只允许：

```text
Bug修复
P0/P1明确错误修正
小范围阈值调整
垃圾候选排查
报告完善
文档补充
```

禁止扩范围。

---

# 61. V0.3 最终验收

## FULL_PASS

要求：

```text
真实TDX行情成功读取
A股Universe建立
最新交易日一致
复权契约完整可复算
Factor正式可运行
Sector Validity生效
Sector Scanner正式运行
Stock Scanner正式运行
HTML/CSV/Audit生成
```

---

## DEGRADED_PASS

要求：

```text
数据管线完成
Universe完成
板块成员完成
报告完成
Audit完成
复权限制显式披露
Trend类Scanner标记EXPERIMENTAL
```

允许周末MVP交付：

> 可运行的降级版本。

不得宣称：

```text
Trend Scanner正式有效
```

---

## BLOCKED

基础数据契约失败。

必须停止。

---

# 62. Codex硬约束

Codex必须：

1. 先读本文件；
2. 先审计真实TDX；
3. 不得假设目录；
4. 不得修改TDX；
5. 不得联网；
6. 不得擅自补外部复权；
7. 不得引入数据库/微服务；
8. 不得在BLOCKED状态继续开发Scanner；
9. DEGRADED状态必须显式标记；
10. 所有Factor必须公式化；
11. 所有Sector percentile必须同type内部计算；
12. 所有Breadth必须输出有效成员数量；
13. 所有Score必须可解释；
14. 不得为了必须有候选而自动降阈值；
15. 不得使用未来行情调参；
16. 所有正式文件采用原子写入；
17. 周末MVP优先于架构完美。

---

# 63. 推荐文档层级

```text
PROJECT_SPEC.md
docs/
├─ DATA_FACTOR_SPEC.md
├─ SCANNER_SPEC.md
├─ CURRENT_STATUS.md
└─ decisions/
```

当前V0.3可暂时作为：

```text
PROJECT_SPEC + DATA CONTRACT + IMPLEMENTATION BASELINE
```

Phase 0结束后再拆分细化。

---

# 64. Codex首个正式任务

正式任务：

```text
PHASE 0 — DATA, ADJUSTMENT & FACTOR CONTRACT PREFLIGHT
```

必须完成：

```text
真实TDX_ROOT审计
.day契约验证
文件稳定性检查
MARKET.CODE唯一键
证券类型识别
expected_a_stock_count冻结
复权本地来源审计
Adjustment Contract
Sector Membership审计
Sector Validity初始参数统计
Factor Contract
TDX_DATA_AUDIT.json
FULL / DEGRADED / BLOCKED判定
```

禁止：

```text
提前完成Scanner
联网
修改TDX
外部补数
大型回测
机器学习
扩展技术栈
```

---

# 65. 后续路线

只有V0.3稳定后：

```text
V0.4
Forward快照与候选跟踪

V0.5
板块生命周期完善

V0.6
个股生命周期完善

V0.7
分时确认层

V0.8
外部复盘交叉

V0.9
AI Review

V1.0+
严格PIT数据与统计晋级
```

---

# 66. 项目最终定义

**中文**：

> 通达信A股市场结构扫描器

**英文**：

> TDX Market Structure Scanner

正式身份：

> 基于本地通达信行情、复权口径和当前板块成员关系，对A股全市场进行盘后结构识别、分类、解释和研究优先级压缩的本地研究工具。

成功标准不是：

```text
预测未来牛股
获得高胜率
回测收益漂亮
```

而是：

> 数据口径明确、结果可复算、结构可解释、每天可稳定运行，并能够显著减少人工复盘范围。

---

**END OF V0.3 FINAL IMPLEMENTATION BASELINE**

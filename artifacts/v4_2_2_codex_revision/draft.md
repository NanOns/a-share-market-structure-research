# 大A市场结构研究系统 V4.2.2 codex修改版

> 文档编号：DA-MSR-V4.2.2-CODEX-REV1  
> 日期：2026-09-25  
> 状态：DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK / IMPLEMENTATION_NOT_VERIFIED  
> 原件：A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925.md；本文件由原件副本逐章修改，原件不变。  
> 代码基线：codex/algorithm-v3-incremental-upgrade @ 3ef5bf63455447dd605534dc4c1717eb238a86f5。  
> 最高任务：全市场每日状态理解、变化发现、可解释研究、持续跟踪和前瞻验证。

本版统一当前规范，保留原产品目标及无冲突章节，不把文档修改等同代码验收、真实数据验证或长期统计支持。§78 是唯一阶段表；§87A 是字段登记；§72 是参数治理。历史附录只解释沿革，不发出实施指令。遇到未预期冲突，登记 CONTRACT_CONFLICT 并只暂停受影响能力。

允许先做基线盘点、源能力验证和算法合同设计；对应模块实现前须具有其 Rule AST、参数实例、独立测试向量及数据合同。新增阈值均是 ENGINEERING_CANDIDATE，不是市场规律。

所有 TDX 根目录只读；下载、staging、归档、备份和临时文件均在项目管理目录，原子写入。原项目 Phase 0 必须有 FULL_PASS / DEGRADED_PASS / BLOCKED 回执，BLOCKED 范围不得进入 scanner。各阶段记录合同、证据、接受结果和下一阶段。M14 仅按已批准 dataset source contracts、能力门、有界请求运行，hot-rank direct mode 禁止持久化原始/行/批次/历史快照。跨域审计独立跟踪。

---

# 0. 升级背景与产品问题

V4.0 的战略方向是正确的：

```text
Canonical Facts
→ Factors
→ State
→ Radar
→ Focus
→ Forward
```

也正确识别了旧系统最重要的产品错位：

```text
RS20 背景排行
被长期当成今日研究优先级；

POTENTIAL / EARLY
实际上已经偏向共振确认；

个股 EARLY 与板块 POTENTIAL
形成循环依赖；

V3.3 正式候选偏确认，
真正偏早期的 SETUP_WATCH 没有产品化；

Focus Tracker 已经具备成熟的生命周期审计能力，
但上游来源语言仍然碎片化。
```

多份外部审计进一步指出，V4.0 虽然“发现什么”的方向已经正确，但还缺少一组决定算法能否可信落地的硬合同：

1. Stock PREWATCH 与 Sector PREWATCH 仍可能形成**同日软反馈环**。
2. Evidence Family 虽然分了名字，但大量指标都来自同一价格序列，存在**重复计价**。
3. PREWATCH 的“相对抗跌”可能把系统从“老强势霸榜”带到“低 Beta 防御股霸榜”。
4. Sector seed/breadth 在小板块上有明显**小样本比例偏差**。
5. 历史板块成员若不是 Point-in-Time，历史 replay 可能存在 `CURRENT_MEMBERSHIP_BIAS`。
6. “主板块”如果没有确定性规则，会产生 sector cherry-picking。
7. Market Regime 只有状态名，没有轴、滞后和转移合同。
8. `SEED / PREWATCH / WARM / CONFIRMED / CONTRACTION / FADING / FOLLOWUP` 混合了不同维度，缺正式 FSM。
9. 如果只验证 `PREWATCH → CONFIRMED`，会出现“算法用自己后面的规则证明自己前面的规则”的自证问题。
10. 如果只有 Focus Top-K 才产生完整结果，会形成**选择偏差**。
11. 20 个交易日只能证明工程稳定，不能证明算法得到真实 Forward 支持。
12. 工程 PIT replay、时序泄漏测试、deterministic replay 应提前，而不是放到 P2。
13. 数据质量不能只用一个粗粒度 `READY/PARTIAL/UNAVAILABLE` 而不说明原因和传播。
14. BaoStock 换手率需要历史窗口、绑定、预算、缺失降级和口径治理。
15. Near-Miss 应按规则路径计算“差什么”，而不是生成神秘总分。

这些意见中，大部分成立；也有部分建议如果直接采用，会反而违背本项目目标或制造前视偏差。本版首先完成审计裁决，再给出新的正式架构。

---


# 0A. V4.2 本轮新增的最高级约束

V4.2 相比 本版 不是“小版本补丁”，而是把系统从：

```text
候选筛选器 + Focus
```

进一步扩展为：

```text
全市场每日状态理解
        ↓
变化事件发现
        ↓
少量研究优先级
        ↓
持续跟踪与 Forward 验证
```

新增六个正式模块：

1. `TDX_OFFLINE_HISTORY_BOOTSTRAP`：只依赖通达信官网个人行情完整日线包与本地 TDX 文件，不依赖 TDX 量化平台/TQ/付费 API。
2. `FULL_MARKET_DAILY_STOCK_PROFILE`：每日对研究 Universe 中所有股票生成统一状态画像。
3. `ROTATION_STATE_ENGINE`：识别板块轮动脉冲、进入、接受、扩散、轮出和再加速。
4. `STRUCTURE_EVENT_ENGINE`：管理突破、中阳、平台、前高、均线等结构事件与冻结 Anchor。
5. `SUPPORT_ACCEPTANCE_ENGINE`：把“支撑有效”拆为 Test → Reclaim → Hold → Retest → Confirm/Break。
6. `CONFIRMATION_EVENT_COMPRESSION`：把 V3.3 从“所有仍满足确认条件的股票列表”改造成“今日新确认/确认变化事件引擎”。

本轮同时冻结用户侧产品约束：

```text
首页板块：正常 5–10 个，硬上限 15 个
首页行业 + 概念统一排序
通达信风格板块：排除出研究 Radar
首页：只显示今天发生变化的对象
独立个股变化/优先研究对象：首页硬上限 30 个
底层 eligible / seed / confirmed：允许远大于页面显示量
板块内个股：按实际板块结构展示；首页卡片只预览重点成员，详情页展示完整结果
```

这些是产品合同，不反向改变底层算法资格。

---

# 0B. 现实数据源约束：TDX 量化接口正式出局

V4.2.2 明确：

```text
OUT OF SCOPE / FORBIDDEN DEPENDENCY
- 通达信 TQ 量化接口
- 通达信量化平台付费行情 API
- 依赖专业版量化权限的 get_market_data / get_exday_data 等接口
```

正式允许的数据入口：

```text
A. 通达信官网个人行情数据页：
   https://www.tdx.com.cn/article/vipdata.html

B. 用户本地通达信 vipdoc / 已下载日线文件

C. BaoStock 免费接口：
   https://www.baostock.com/mainContent?file=stockKData.md
   仅承担补充事实，不成为价格权威
```

通达信官网个人行情页公开说明该页面适用于个人版 PC 盘后数据下载，并提供沪深京日线数据完整包。V4.2 因此把该完整包定义为历史价格 Bootstrap 的正式入口。

**禁止把任何需要 TQ/量化平台权限的能力写进 V4.2 的 Required Dependency。**


# 0C. 本版合同状态

产品目标保留；数据/算法按本文统一。实现、外部源覆盖、历史公司行为与真实 Forward 仍需阶段证据。所有页面字段必须进入 §87A 字段族及逐字段机器注册表。

# 0D. 依赖顺序

Source/Identity → Facts/Factors → Core Profile → Replay A → Seed → Sector/Rotation → PREWATCH 原始资格 → Confirmation/Structure detector facts → Final State → Events/Radar/Cohorts/Settlement → Replay B、实时 Shadow → 工程稳定与最低 Forward → Migration Replay → Focus/UI 切换。

开发阶段与每日拓扑不同：§78 约束交付，§13A/77B 约束运行。Settlement 在 Shadow 前交付；历史 replay 不计真实观察天数。

# 0E. 审计处置

上一轮 A01–A12、本轮 B01–B10 和全文新增修订见配套修改说明。状态为 DOCUMENT_REVISED，不自动 CLOSED；代码、真实数据、独立审计、Forward 分别验收。

BaoStock 可复用已有有效调用回执，但能调用不等于全市场覆盖、无限额度或全部历史字段可信。缺能力证据只限制该补充 dataset，不阻断 TDX 主链。

---

# 1. 审计意见裁决

## 1.1 直接吸收为 P0 的意见

以下意见成立，并继续作为 V4.2 P0：

| 审计意见 | V4.2 裁决 | 原因 |
|---|---|---|
| Stock ↔ Sector PREWATCH 存在同日软反馈风险 | **直接吸收** | 必须固定 DAG，禁止同日回馈 |
| Evidence Family 不独立、存在重复计价 | **直接吸收** | 不能把同一价格变化重复算成多条独立证据 |
| PIT Universe / Sector Membership 缺正式合同 | **直接吸收** | 历史 replay、LOO、sector breadth 都受影响 |
| 生命周期缺正式状态机与 hysteresis | **直接吸收** | 否则 PREWATCH/WARM 会日间抖动 |
| Forward Cohort 必须独立于 Focus Top-K | **直接吸收** | 避免展示/人工 pin 造成样本选择偏差 |
| Forward 不能只看 PREWATCH→CONFIRMED | **直接吸收** | 必须加入外部价格结果 |
| Right Censoring | **直接吸收** | 未到 T+N 不能算失败 |
| Engineering PIT Replay 提前 | **直接吸收** | 上线前先查时序、状态、PIT、幂等 |
| 多板块股票 sector context 去重 | **直接吸收** | 一个股票不能因属于多个概念获得多份 Context 证据 |
| Relative resilience 区分 passive / active | **直接吸收** | 防止弱市低波动防御股霸榜 |
| Position 使用波动标准化 | **直接吸收** | 固定 6%/8% 对不同波动股票意义不同 |
| 小板块 seed density 需要样本置信约束 | **直接吸收** | 2/5 与 15/80 不能简单只比 raw ratio |
| Why Now / Conflict / Timeline / PIT Replay | **直接吸收** | 与“变化发现器”产品目标高度一致 |
| Temporal Leakage / Replay / Flapping / Cohort completeness 测试 | **直接吸收** | 属于基础正确性测试 |
| BaoStock 缺失不能改变价格主资格 | **直接吸收** | 外部补充源不能控制核心研究资格 |

---

## 1.2 修改后吸收的意见

### A. “至少 3 个 Evidence Family”

**原建议问题：**

即使改叫 Domain，简单做：

```text
Domain count >= 3
```

仍然存在：

```text
三个刚过线的弱证据
机械压过
两个很强的一致证据。
```

**V4.2 延续并强化：**

不再把 `domain_count` 作为第一排序键，也不把它作为唯一资格逻辑。

改为：

```text
Hard Safety
+
Rule Path Eligibility
+
独立 Priority Axes
```

Domain count 只作为：

```text
evidence_completeness
```

---

### B. “相对韧性最好做 beta60 residual”

这个方向在纯量化因子研究中合理，但**不直接作为 V4.2 P0**。

原因：

1. beta60 估计本身不稳定；
2. 需要额外处理停牌、涨跌停、regime；
3. 很容易把项目带向横截面因子中性化；
4. 用户当前目标是主观研究辅助，而不是建立市场中性 Alpha 模型。

本版 采用：

```text
raw relative return
+
volatility-adjusted resilience
+
RS acceleration
+
structure change
```

作为主体。

`beta residual` 保留为未来诊断项，不进入第一版 qualification。

---

### C. “行业、市值、波动率全面中性化”

**部分成立。**

波动率标准化非常有用，纳入正式因子。

行业/市值全面中性化不纳入 本版 P0，原因：

- 系统本来就要研究行业/概念变化；
- 过度中性化会把真实板块效应主动剥离；
- 市值数据口径必须先有可靠 source contract；
- 容易滑向黑箱因子模型。

---

### D. “概念板块成员按 1/N 衰减”

**不采用。**

一只股票同时属于多个真实概念是正常事实。

如果按：

```text
1 / 所属概念数
```

稀释，会人为改变每个板块内部真实成员含义。

本版 采用：

- 每个板块内部：一只成员就是一只成员；
- 跨板块 Radar：做重叠诊断、相似板块聚类和展示去重；
- Stock Context：多个支持板块只能形成 **1 个 CONTEXT Domain**。

---

### E. “板块 RS 必须增加自由流通市值加权”

**待后续验证，不作为第一版硬要求。**

现有中位数聚合的优势是鲁棒、可解释。

若未来有可靠、PIT-safe 的流通市值数据，可并行增加：

```text
cap_weighted_rs
```

作为诊断，不立即取代 median。

第一版优先增加：

```text
top1_concentration
top3_concentration
effective_member_count
```

判断板块是否被少数股票支配。

---

### F. “BaoStock BOUND_SOFT 也可以进入正式换手因子”

本版 只部分接受。

定义：

```text
BOUND_STRICT
BOUND_SOFT
UNAVAILABLE
```

但是第一版：

```text
BOUND_STRICT
→ 正式 turnover factor

BOUND_SOFT
→ diagnostic only

UNAVAILABLE
→ no turnover factor
```

避免容差绑定反过来污染正式资格。

---

### G. “NEW > PERSISTENT 必须成为 PREWATCH 第一排序”

**不作为核心 eligibility rank。**

原因：

新出现值得在“今日变化”首页优先展示，但一个持续 PREWATCH 且今天继续显著改善的对象，研究优先级未必低于新出现对象。

因此分开：

```text
Event Priority
和
Radar Priority
```

首页变化流：

```text
NEW / UPGRADED
优先
```

正式 Radar 排名：

```text
emergence
structure
risk
staleness
```

---

### H. “H 层必须机械生成至少两个解释”

不采用机械文本生成。

正式研究仍坚持：

> 至少保留竞争解释。

但系统只能从**有证据支撑的假设模板**中生成。

每个 Hypothesis 必须带：

```text
hypothesis
evidence_for
evidence_against
next_discriminator
expiry_condition
```

若系统当前没有足够证据构造第二个真正竞争解释：

```text
HYPOTHESIS_SET_INCOMPLETE
```

并禁止把不完整 H 层升级成强结论。

这比为了“凑两个”制造资金故事更符合本项目 F/R/H/A 纪律。

---

# 1.3 明确不采纳 / 不成立的意见

## A. “PREWATCH 在 T0 准入时必须保证比 WARM/CONFIRMED 早 N 天”

**不成立。**

在 T0 不可能知道：

```text
未来第几天会 CONFIRMED。
```

把这个条件写进资格算法本身就是未来信息泄漏。

正确做法：

```text
T0：
按当时可知事实产生 PREWATCH。

T+N：
统计 actual lead_sessions。
```

“领先 2–3 天”可以成为：

```text
Forward evaluation target
```

不能成为：

```text
T0 eligibility predicate。
```

---

## B. “T+5 后恶化，就把 T0 标成 PREWATCH_FALSE_POSITIVE 并改写原判断”

不允许改写 T0。

可以新增 outcome：

```text
FORWARD_OUTCOME = FAILED_TO_DEVELOP
```

或：

```text
INVALIDATED_WITHIN_5
```

但：

```text
T0 PREWATCH
永远保持 AS_RECORDED。
```

---

## C. “stock_fact_daily / sector_fact_daily 主键不含 trade_date 就意味着一只股票只能存一行”

这个判断**技术上不成立**。

如果：

```text
publication_id
```

本身每天不同，并且每个 publication 唯一绑定一个 trade_date，那么：

```text
PK(publication_id, security_id)
```

完全可以存每日多行。

不过审计暴露了一个真实问题：

> publication 与 trade_date 的一致性合同需要更明确。

本版 因此采用：

```text
publications:
UNIQUE(publication_id, trade_date)

stock_fact_daily:
PK(publication_id, security_id)
trade_date NOT NULL
FK(publication_id, trade_date)
  → publications(publication_id, trade_date)

sector_fact_daily:
同理
```

这样既不增加没有意义的主键冗余，又从数据库层保证 trade_date 一致。

---

## D. “publication_id 必须等于 trade_date + contracts 的 hash”

**不采用。**

现有系统已经有：

- publication id；
- revision；
- source identity digest；
- computation identity；
- head。

把全部合同 hash 强行塞进 publication_id：

- 增加耦合；
- 降低可读性；
- 不会自动提升审计质量；
- 与现有 publication/revision 体系不兼容。

本版 保留：

```text
opaque publication_id
+
explicit identity digests
+
revision
+
accepted head
```

---

## E. “弱市 PREWATCH 非空率必须达到某阈值”

**明确禁止。**

这会诱导系统：

> 为了不空白而制造候选。

本版 的目标是：

> 弱市允许发现相对变化，但没有合格 PREWATCH 时仍然允许 0。

页面在这种情况下应展示：

```text
无正式 PREWATCH
+
Near-Miss / Passive Resilience / Market Context
```

而不是降低资格。

---

## F. “换手率应该进入 PREWATCH hard eligibility”

第一版不采用。

原因：

- BaoStock 是补充在线源；
- 免费外部源没有核心行情同等级别的稳定性；
- 换手缺失不应让本来有效的价格结构资格消失。

换手第一版用于：

```text
PARTICIPATION supplemental context
diagnostic-only priority view
diagnostic risk note
hypothesis discriminator
```

而不是核心硬门。

---

## G. “V4 第一版按 Market Regime 切换不同参数集”

第一版不采用。

Regime 初期用于：

```text
解释
优先级
统计分层
```

不直接改变硬资格阈值。

否则很容易变成：

```text
行情一变
→ 换一套最适合当前行情的参数
→ 过拟合。
```

只有未来 Forward 样本支持后，才允许新 contract 引入 regime-conditioned parameter set。

---

## H. “事实表现在就必须 range partition”

不作为设计硬门。

V4-00 先建立性能 baseline。

如果实际：

```text
query latency
write amplification
index size
vacuum
backup time
```

触发门槛，再引入分区。

不能在没有性能证据时提前增加 schema 运维复杂度。

---

# 2. V4.2 最终目标

本版 不是做一个更复杂的选股器。

最终系统应该回答：

```text
市场现在是什么环境？
什么板块今天真正发生了变化？
什么板块虽然仍强，但正在衰减？
什么股票尚未确认，却已经出现值得提前跟踪的结构变化？
什么股票今天完成了确认？
为什么今天值得看，而不是昨天？
它还有什么反证？
还差什么确认？
什么条件失效？
后来到底发生了什么？
```

系统不直接替用户回答：

```text
该不该买？
买多少？
目标价多少？
明天上涨概率多少？
```

---

# 3. V4.2 唯一主链

```text
Local Source / Identity / Calendar / Adjustment
    -> F0 Core Facts / Atomic Factors
    -> A Stock Seed -> B Sector / LOO / Rotation -> C Stock PREWATCH
    -> D0 Confirmation -> D1 Structure -> D2 State -> D3 Events
    -> E Accepted Publication / Radar
        -> Focus (用户跟踪)
        -> Complete Validation Cohort -> Due Planner / Forward / Statistics

BaoStock / approved optional sources -> independent Enrichment Revision
Accepted Core + selected Enrichment -> context-bound UI / diagnostics
```

每条实际输入边和并行分支按§13A。上图为分层摘要，不允许从Supplemental、Focus、Forward或UI反馈修改Core资格。Focus和Validation Cohort从Accepted Radar分叉，用户筛选不限制完整验证样本。行业成员仅对消费它的能力必需，缺失不全局阻断stock Core。

---

---

# 3A. V4.2 数据源权威矩阵

## 3A.1 核心原则

不同数据源可以共存，但**每个字段必须只有一个正式 authority**。

| 数据/能力 | 正式 Authority | Supplemental / Validation | 禁止行为 |
|---|---|---|---|
| 日线 OHLC | TDX 本地/官网日线 | BaoStock 仅 fingerprint | 不用 BaoStock 覆盖 TDX |
| Volume | TDX | BaoStock fingerprint | 不混单位后拼接 |
| Amount | TDX | BaoStock fingerprint | 不用不同口径静默覆盖 |
| 前复权价格 | 现有仓库已验收的本地 TDX QFQ 链 | 其他源仅诊断 | 不引入 TQ API 依赖 |
| 周K/月K | Canonical TDX 日线重采样 | 不读取 BaoStock 周/月价格 | 禁止多价格源周期混用 |
| Turnover | BaoStock `turn`（BOUND_STRICT） | TDX金额/量用于绑定 | 缺失不阻断价格主链 |
| Trade Status | accepted local security master + TDX/calendar facts | BaoStock 独立 cross-check | 缺失不是停牌，冲突只标补充告警 |
| ST | accepted local security master 日期有效身份 | BaoStock 仅 cross-check | 未知则对应规则 UNKNOWN |
| 股票代码/证券类型 | 本地 TDX 元数据 | BaoStock basic | 证券 identity 必须统一 |
| 行业/概念/风格 | 本地 TDX 板块元数据 | 手工类型映射配置 | 风格板块不进入主 Radar |
| Sector PIT Membership | 从 V4 启动日起每日冻结 TDX 成分快照 | 历史无法还原时标 CURRENT_MEMBERSHIP_REPLAY | 不伪造两年前 PIT 成员 |

---

## 3A.2 Source Family

```text
TDX_VIPDATA_PACKAGE
TDX_LOCAL_VIPDOC
BAOSTOCK_SUPPLEMENT
```

`TDX_VIPDATA_PACKAGE` 与 `TDX_LOCAL_VIPDOC` 都属于：

```text
TDX_PRICE_FAMILY
```

但必须保存独立 source identity，便于判断某条历史记录来自完整包还是本地日常更新。

---

## 3A.3 不允许的数据融合

禁止：

```text
2025-01 ~ 2026-01 BaoStock QFQ
2026-02 ~ 当前 TDX QFQ
```

拼成同一价格序列。

也禁止：

```text
TDX 日线
+ BaoStock 周线
+ BaoStock 月线
```

形成多口径多周期数据。

正式链只能是：

```text
TDX Canonical Daily
    ├─→ Daily
    ├─→ Derived Weekly
    └─→ Derived Monthly
```

---

# 3B. 两年历史初始化：TDX Offline Bootstrap

## 3B.1 目标不是“只保存两年”

用户需要至少两年可研究历史。

但如果只从两年前第一天开始读取数据，则最早一段无法完整计算：

```text
MA60
ATR20
RPS20
250日位置
长期波动基准
周/月趋势
```

因此正式采用三层：

```text
RAW ARCHIVE
= 官网完整日线包原样归档，可长于两年

ACTIVE WARMUP WINDOW
= 两年正式研究窗口之前再保留至少 300 个实际交易 session 的算法 warm-up

FORMAL RESEARCH WINDOW
= 最近约两年交易历史
```

页面默认研究最近两年，但底层可以读取更早数据用于 warm-up。

---

## 3B.2 Bootstrap 输入

正式流程：

```text
1. TDX_VIPDATA_ADAPTER_V1 读取通达信个人行情数据页
2. 验证页面标示的更新日期与目标日期关系
3. 取得“沪深京日线数据完整包”下载对象
4. 保存原始 ZIP 到 immutable raw archive
5. 记录 SHA256 / size / source page / observed_at
6. 在 project-managed staging 安全解压
7. 解析全部可识别证券日线，不在 Raw Ingest 阶段按“今天的股票池”删除历史证券
8. 构建 Historical Security Lifecycle / Historical Evaluable Universe
9. 再按每个 trade_date 的历史资格产生研究视图
10. 与当前本地 TDX 的重叠窗口做全市场一致性核验
11. 核验通过后写入 Canonical Daily History
```

关键修订：

> Raw History 不允许先按“当前 V4_RESEARCH_UNIVERSE”裁掉已退市、已更名、今天已不在研究池的历史股票。

原因：

```text
current-universe filtering
→ survivorship bias
→ historical RPS / breadth / percentile 污染
```

研究 Universe 必须是日期函数：

```text
RESEARCH_UNIVERSE(security_id, trade_date, universe_contract_id)
```

官网 ZIP 永远不自动覆盖用户本地通达信目录。项目只读外部源，正式库由项目自己的 staging / canonical pipeline 管理。

---

## 3B.3 Source Package Identity

每次下载完整包都保存：

```text
package_id
source_url
page_observed_update_date
local_download_time
file_name
file_size
sha256
unpack_manifest_digest
parser_version
```

同一文件 SHA 相同：

```text
idempotent / skip duplicate import
```

---

## 3B.4 重叠核验

完整包与当前本地 TDX 至少抽取最近：

```text
60–120 个实际交易 session
```

做全市场级核验。

输出：

```text
exact_match_rows
normalized_tolerance_match_rows
mismatch_rows
package_only_rows
local_only_rows
identity_mismatch_count
```

核验字段：

```text
trade_date
security_id
open/high/low/close
volume
amount
```

如果 mismatch 超过合同阈值：

```text
BOOTSTRAP_BLOCKED
```

而不是静默拼接。

---

## 3B.5 Canonical 历史优先级

对于重叠日期：

```text
accepted local TDX current chain
```

优先于同 family 的旧 complete package。

对于 local 缺失的较早历史：

```text
TDX_VIPDATA_PACKAGE
```

填补。

所有选择都写 provenance。

---

## 3B.6 历史复权与公司行为合同

本版 **禁止把“日线完整包可读取”直接等同于“历史 QFQ 可重建”。**

正式拆成两个事实层：

```text
RAW_CANONICAL_PRICE
= TDX .day 原始日线
= 只要日线解析、身份、日期和重叠校验通过即可 READY

ADJUSTED_CANONICAL_PRICE
= 只有 TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1 通过后才可 READY
```

### 必须冻结 `TDX_HISTORICAL_ADJUSTMENT_CONTRACT_V1`

至少写明：

```text
adjustment_source_files
corporate_action_inputs
factor_build_algorithm
factor_effective_date
raw_to_qfq_formula_or_library
rounding_policy
new_listing_policy
suspension_policy
rights_issue_policy
cash_dividend_policy
split_bonus_policy
missing_action_policy
rebuild_determinism
```

### 实证验收

至少选择发生过以下公司行为的真实样本：

```text
现金分红
送股/转增
配股
除权
长期停牌后复牌
上市不久股票
```

在多个历史日期验证：

```text
same raw source
+
same adjustment source
+
same adjustment contract
→ same QFQ series digest
```

### 调整数学与历史截断

已验证同一artifact的affine系数A[j],B[j]满足Q[j]=A[j]*raw[j]+B[j]。以观察日t为坐标时P[j|t]=(A[j]*raw[j]+B[j]-B[t])/A[t]，A[t]>0；多artifact系数不可混算。差值/ATR只乘正尺度，不加beta；价格水平变换才加beta，收益必须在统一坐标重新算而非直接“转换百分比”。Anchor先确定其原始基准，再用对应线性坐标映射，不把系数用于不匹配的raw基准。
公司行为仅使用effective<=t且在所选消费manifest内可见的事件；即使full-series系数能消去未来行动，也必须单独证明重锚等价、来源可见性及没有后来更正泄漏。现金分红的加法项使简单“价格比总会消因子”不成立。
独立预期值来自可核验本地源样本/数学向量，不仅比较digest。真实事件源缺证据仍按下面scope降级，不能用在线adjustment补作Core。

### 复权失败降级

如果某段历史：

```text
RAW price READY
但
adjustment evidence incomplete
```

则：

```text
raw_quality = READY
adjusted_quality = UNAVAILABLE
adjustment_reason = ...
```

以下因子不得静默退回 raw 继续算：

```text
MA / slope
RPS / relative return
历史高低点
breakout / pullback
ATR-normalized anchor
support event
weekly/monthly adjusted trend
```

这些输出应：

```text
BLOCKED_BY_ADJUSTMENT
```

禁止：

```text
TDX adjustment 失败
→ 自动换 BaoStock QFQ 补正式主价格
```

BaoStock adjusted OHLC 永远不是 本版 正式价格 fallback。

---

# 3C. 周K / 月K：全部由 Daily 派生

## 3C.1 周K算法

对每个证券、每个交易周：

```text
open   = first(actual daily open)
high   = max(actual daily high)
low    = min(actual daily low)
close  = last(actual daily close)
volume = sum(actual daily volume)
amount = sum(actual daily amount)
```

分别对：

```text
RAW Daily
QFQ Daily
```

派生。

禁止：

```text
用 BaoStock weekly bar 作为主周K。
```

---

## 3C.2 月K算法

同理：

```text
open   = 月内首个实际交易日 open
high   = 月内 high 最大值
low    = 月内 low 最小值
close  = 月内最后实际交易日 close
volume = sum(volume)
amount = sum(amount)
```

---

## 3C.3 周/月 AS-OF

contract_id=PERIOD_ASOF_V1。使用冻结exchange calendar确定周期最后市场交易日，不用自然周五/月末猜测。CLOSED_ONLY只纳入period_last_session<=T0且当期所需日线/确认停牌证据完整、source在cutoff可见的周期；T0恰为周期最后交易日且数据已接受时可纳入，不能无端滞后一周期。
AS_OF_PARTIAL由period首会话至T0实际bar聚合，保存max_source_trade_date、period_view、asof_trade_date和IN_PROGRESS/CLOSED。所有必需日线价格先换到同一观察坐标再聚合，amount/volume保持原始单位，不调整成交量后混加。
整周期停牌没有actual OHLC则UNKNOWN/NO_ACTUAL_BAR，不制造零K线；部分停牌可按actual bar聚合但保存calendar_count/actual_count/suspended_count，未知缺口则该bar PARTIAL且不进正式closed trend。
同一因子必须声明固定period_view，不能按结果好坏挑选。趋势V1只用CLOSED_ONLY，图表可以并列partial。历史删掉T0之后日线/公司行为与知识时间晚到行，T0输出应不变。

---

## 3C.4 周/月因子的 PIT 测试

必须至少测试：

```text
周一 / 周三 / 周五
月初 / 月中 / 月末
跨节假日周
月末非交易日
```

并证明：

```text
T0 周/月输出
与删除 T0 之后所有 Daily 后重新聚合
完全一致
```

否则：

```text
TEMPORAL_LEAKAGE_BLOCKED
```

---

# 3D. BaoStock 历史补充数据方案

## 3D.1 BaoStock 的角色

BaoStock `query_history_k_data_plus()` 可用于历史 A 股日线查询，并可返回如：

```text
date
code
open/high/low/close
preclose
volume
amount
turn
tradestatus
pctChg
isST
```

V4.2.2 只正式消费：

```text
turn
tradestatus
isST
```

OHLC/volume/amount 只用于 source fingerprint 和质量诊断。

用于 fingerprint 的 BaoStock K 线必须优先请求：

```text
adjustflag = 3  # 不复权
```

再与 TDX raw daily 比较；禁止拿 BaoStock 前复权价格与 TDX raw 做身份绑定。

---

## 3D.2 不冻结未经验证的请求额度

V4.2.2 不把“每天 X 万次”等未经当前正式文档/实测确认的数字写成事实。

Adapter 第一次 smoke test 必须测量：

```text
login stability
requests / minute
rows / request
server errors
session timeout
full-market one-day elapsed time
one-security two-year elapsed time
```

然后生成：

```text
BAOSTOCK_RUNTIME_CONTRACT_V1
```

---

## 3D.3 历史初始化策略

由于历史接口按股票代码 + 日期范围获取，历史初始化优先：

```text
one security
×
two-year range
```

而不是：

```text
security × trading day
```

下载器必须：

```text
checkpointable
retryable
idempotent
adaptive throttle
```

正式目标：

```text
优选 250 个此前有效 session turnover history；最低运行窗口按 §9.4
```

如果两年历史一次拉取成本可接受，则直接保存两年 supplement；否则先完成 §9.4 的最低60个此前有效样本，再后台扩展；不阻断Core。

---

## 3D.4 每日增量与主发布解耦

TDX 主价格 publication：

```text
不等待 BaoStock 全市场完成
```

流程：

```text
TDX primary publication
→ 全市场 price-based profile
→ BaoStock enrichment job
→ turnover BOUND_STRICT
→ same-day enrichment revision
```

因此如果全市场 BaoStock 当日抓取慢：

```text
turnover_state = PENDING / UNAVAILABLE
```

但：

```text
Trend / Position / Structure / RPS / PREWATCH price path
```

仍可完成。

### 当日 Enrichment 优先队列

为避免全市场串行抓取影响用户体验，BaoStock enrichment 采用：

```text
Priority A:
- 首页变化对象
- Focus active
- 用户 pinned
- 当日搜索股票

Priority B:
- 其余 Research Universe
```

最终目标仍是全市场补齐，不是只补候选。

如果用户搜索某只 `turnover_state=PENDING` 的股票，可触发：

```text
on-demand single-security enrichment
```

成功后写入同一 supplement cache；不得只在页面内临时返回而不落库。

---

## 3D.5 BaoStock 绑定

正式绑定至少检查：

```text
security identity
trade_date
tradestatus
normalized close
normalized volume
normalized amount
```

状态：

```text
BOUND_STRICT
BOUND_SOFT
UNBOUND
MISSING
```

第一版只有：

```text
BOUND_STRICT
```

可进入正式 turnover factors。

`BOUND_SOFT` 只做诊断。


# 3E. TDX VIPDATA 免费数据适配器合同

正式适配器：

```text
TDX_VIPDATA_ADAPTER_V1
```

唯一公开入口：

```text
https://www.tdx.com.cn/article/vipdata.html
```

本版 不依赖：

```text
通达信量化平台
TQ / 专业量化 API
付费行情 API
```

## 3E.1 页面发现

Adapter 必须解析或可靠取得：

```text
source_page_url
page_observed_at
page_declared_update_date
download_url_or_resolved_object
```

当用户要求当日数据时：

```text
page_declared_update_date < target_trade_date
→ SOURCE_NOT_READY
```

不能把上一交易日完整包当今天。

## 3E.2 下载安全

必须：

```text
download to temp name
fsync / close
file_size > minimum
sha256
ZIP CRC check
safe extraction
manifest generation
atomic promotion
```

禁止：

```text
直接下载到正式目录
半个 ZIP 被 parser 读取
路径穿越解压
自动覆盖用户 D:/new_tdx
```

## 3E.3 Package Manifest

至少：

```text
package_id
source_page_url
download_url
page_declared_update_date
observed_at
download_started_at
download_finished_at
file_name
size_bytes
sha256
zip_entry_count
unpack_manifest_digest
parser_version
status
failure_reason
```

## 3E.4 重试

只允许对：

```text
network failure
5xx
timeout
partial download
CRC failure
```

做有上限重试。

以下不重试伪装成功：

```text
page update date not ready
identity mismatch
unexpected file family
overlap validation failed
```

## 3E.5 Source Acceptance Gate

```text
DOWNLOADED
≠ ACCEPTED_SOURCE
```

只有：

```text
download integrity
+
parser integrity
+
market/date identity
+
overlap validation
```

全部通过才：

```text
ACCEPTED_SOURCE_PACKAGE
```

---

# 3F. Source 接受与交易制度边界

source package、local snapshot、parser版本共同确定输入身份；相同zip hash但parser版本变化必须新parse artifact，不能因hash相同直接跳过重算。source manifest要绑定目标trade_date和冻结来源cutoff，较新包可用于重建历史但不能伪称过去实际观察。
TDX官网页面只证明提供日线包，不证明历史退市全集/公司行为全集。历史身份不能从文件第一/最后bar推断上市/退市日；板块/PIT成员未知按scope降级。TDX本地在用户更新时可能变化，读取前后size/mtime/hash核验，不稳定重试有界次数或SOURCE_MUTATING，正式分析只读项目快照。
ZIP处理拒绝绝对路径、..逃逸、符号链接/reparse point逃逸、异常压缩比/总解压大小；临时和最终路径必须都在项目目录，fsync/close后原子promote。URL只能来自获准public source contract及允许重定向host，不把官网“覆盖vipdoc”的客户端说明当本项目写权限。
有界请求的timeout/最大bytes/重试/并发/每日预算在V4-00D/F能力回执中冻结；已有实测可复用，缺失预算拒绝该网络作业，不运行无界探测。上游429按Retry-After/退避，不无限重试。

PRICE_LIMIT_RULE_V1必须基于目标日期官方制度版本表及本地可验证身份，保存board/security_type/ST/listing_phase、规则生效区间、参考价来源、tick、rounding、无涨跌幅限制例外。previous_close字段区分上次成交收盘与交易所当日涨跌幅参考价，除权等日期不能直接把昨日raw close代入。无权威参考价/规则则limit_status UNKNOWN；不是用BaoStock补作Core authority。制度表的当前或历史事实不能由本方案臆造，V4-02提交官方来源与独立样本后才启用对应规则，其他Pure-Core能力依赖scope运行。

---

# 4. Source / Publication / Revision 合同

## 4.1 Publication 继续沿用现有成熟语义

本版 不重造一套 publication 世界。

正式 publication 继续保留：

```text
publication_id
trade_date
revision
status
source_identity
computation_identity
accepted head
```

V4 数据输出全部绑定：

```text
publication_id
```

---

## 4.2 同日修订

同一个 trade_date：

```text
revision 1
revision 2
...
```

旧 revision：

```text
append-only
不可覆盖
```

唯一 current head 指向：

```text
accepted revision
```

---

## 4.3 UI Request Context

页面切换交易日后：

```text
先固定 publication_id
```

同一次页面加载的所有 API：

```text
必须携带同一 publication_id
```

前端收到旧异步请求：

```text
publication_id != current context
```

直接丢弃。

---


## 4.4 Data Cutoff / As-Of Contract

每个正式 publication 必须冻结：

```text
target_trade_date

tdx_source_package_id
tdx_page_declared_update_date
tdx_source_observed_at

local_tdx_snapshot_id
membership_snapshot_id
universe_snapshot_id

mandatory_source_cutoff_at
optional_enrichment_cutoff_at

computation_started_at
computation_finished_at
accepted_at
```

任何正式因子：

```text
max_source_trade_date <= target_trade_date
```

任何同日来源修订必须产生：

```text
new revision
```

而不是静默覆盖旧结果。

---

## 4.5 Core Publication 与 Supplemental Enrichment 权限

第一版正式冻结：

### Core Research Publication

只使用：

```text
mandatory TDX price/factor facts
mandatory universe facts；membership只对sector/context能力必需，stock Core不以membership缺失全局阻断
已明确属于核心资格的 deterministic factors
```

决定：

```text
Base Seed eligibility
Sector state
Rotation state
Stock PREWATCH eligibility
Maturity / Health / Validity
Confirmation event
Canonical Radar algorithmic eligibility
Focus transition
Validation signal enrollment
```

一旦：

```text
CORE_PUBLICATION = ACCEPTED
```

BaoStock 后置补充**不得**反向修改上述正式状态。

### Supplemental Enrichment Revision

BaoStock 可以更新：

```text
turnover_rate
turnover_context
participation_context
tradestatus cross-check
isST cross-check
hypothesis evidence
UI supplemental badges
diagnostic risk note
```

但第一版：

```text
cannot mutate core eligibility/state/focus transition
```

这样才能同时满足：

```text
BaoStock 不阻塞主链
AND
同一 publication 语义稳定
```

未来只有在真实运行证明 BaoStock 足够稳定，并发布新的：

```text
CORE_SOURCE_CONTRACT_V2
```

后，换手才可以升级成 pre-publication mandatory input。

---

## 4.6 Historical Reconstruction Identity

唯一枚举：evidence_origin=PIT_OBSERVED / RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED / DIAGNOSTIC_NON_PIT；execution_mode=PRODUCTION / SHADOW / REPLAY。

PIT_OBSERVED 是运行时真实冻结的源消费集合与结果，生产和 Shadow 均可；事后按 T0 有效/知识时间重建为 RECONSTRUCTED_ASOF；用后来更正为 RECONSTRUCTED_CORRECTED；任何必要时序条件无法证明为 DIAGNOSTIC_NON_PIT。

分别保存 universe_basis、membership_basis、price_basis、quality；不要把 CURRENT_MEMBERSHIP/PRICE_ONLY 混进 origin。每个输出按实际依赖的最弱证据降级。正式观察 cohort 只接受 PIT_OBSERVED，按 Shadow/Production 分层；历史重建只能作工程 replay、案例、参数初检，不合并真实 Forward。

---

## 4.7 Prior-Session State 与 Same-Day Revision Parent

t 首次创建计算 lineage 时，冻结同模型上一市场交易日 accepted publication id、revision、logical digest 为 prior_session_state_head。t 的所有同日 revision 使用相同前驱；same_day_revision_parent 只用于修订差异。

T-1 未确认、T r1/r2/r3 均确认，则三者都是 NEW_CONFIRMED。若 r2 撤销资格，追加事件 observation RETRACTED；当前投影按 r2，原实时 enrollment 保留并标 SOURCE_CORRECTION，不伪造市场失效。

T-1 后来更正不改变已冻结 T；要传播则新建 CORRECTED_RECONSTRUCTION lineage 有序重算。上一市场日未发布时记录 gap，不能跨多日称“昨日”；纯事实可发布，状态暂停升级/退出，补齐有序状态或显式初始化边界后恢复。

---

## 4.8 Model / Execution Namespace

所有状态账本携带：

```text
model_contract_id
execution_mode
namespace
publication_id
core_revision
```

至少区分：

```text
PRODUCTION_LEGACY
SHADOW_V4
PRODUCTION_V4
```

Shadow 必须读取 Shadow 自己的 prior-session state，不能把 Legacy 前态当 V4 前态。

model_contract_id 绑定代码/AST/参数/源语义摘要；参数变更必须新模型身份。state_lineage_id 与执行 namespace 分开：同模型 Shadow→Production 经 migration manifest 显式继承最后 Shadow 前态与 episode mapping，不制造 FIRST/REENTRY。不同模型产生 MODEL_BOUNDARY 和新 cohort。旧 episode follow-up、pending outcome 独立保留结算。

---

## 4.9 UI Context Token

一次页面上下文固定：

```text
trade_date
publication_id
core_revision
model_namespace
optional_enrichment_revision
```

异步响应 token 不一致：

```text
DISCARD
```

Supplemental revision 只能刷新允许的 supplemental 区域，不重新定义 Core event。

---

# 5. Universe 合同

## 5.1 Data Universe 与 Research Universe 分离

### Data Universe

尽可能覆盖 TDX 当前可识别 A 股证券。

### Research Universe

由版本化合同定义。

本版 不在设计文档里擅自重新决定：

- ST 是否排除；
- 北交所是否排除；
- 上市 N 日以内是否排除；
- 长期停牌如何处理。

V4-00 必须审计当前：

```text
normal_universe
```

真实代码行为后，冻结：

```text
V4_RESEARCH_UNIVERSE_V1
```

---

## 5.2 Canonical Trading Status

trading_status=ACTUAL_TRADED / SUSPENDED / DATA_GAP / UNKNOWN。RESUMED 是事件，DELISTING 是 lifecycle 字段；涨跌停独立为 limit_status。确认停牌需日期有效证据；无 bar 不等于停牌，换手/金额不填零。

收益窗口、状态计数和 Forward horizon 分别按 §10A0/31/46A，不能用一个“有效会话”代替不同时间尺度。

---

## 5.3 Historical Security Lifecycle / Survivorship Contract

新增：

```text
security_lifecycle_history
```

至少字段：

```text
security_id
symbol
security_type
board
list_date
delist_date
effective_from
effective_to
status
source_contract_id
quality
```

每个历史 trade_date 构建：

```text
historical_evaluable_universe(t)
```

不能：

```text
today_active_security_list
→ 回算过去 RPS 横截面
```

### 历史横截面必须绑定 Universe

以下全部保存：

```text
universe_contract_id
universe_digest
evaluable_count
```

包括：

```text
market median return
RPS percentile
sector member percentile
breadth
new high / new low count
matched controls
```

### 无法重建历史证券生命周期时

必须降级：

```text
universe_basis = CURRENT_UNIVERSE_REPLAY
```

此时：

```text
historical RPS percentile
historical breadth
historical control cohort
```

只能：

```text
DIAGNOSTIC
```

不能作为正式历史效果证据。

---

# 6. Point-in-Time Membership 合同

## 6.1 为什么是 P0

Sector RS、breadth、seed density、LOO、历史 replay 全部依赖成员关系。

如果历史只有今天的成员名单：

```text
用 2026 成员
回算 2025 板块
```

会形成：

```text
CURRENT_MEMBERSHIP_BIAS
```

---

## 6.2 新成员表

建议：

```text
sector_membership_observations
```

字段：

```text
sector_id
security_id
observed_trade_date
effective_from
effective_to
observed_at
available_at
source_revision_id
supersedes_revision_id
source_contract_id
source_identity
membership_basis
membership_quality
```

其中：

```text
membership_basis =
  PIT_OBSERVED
  SOURCE_EFFECTIVE_RANGE
  CURRENT_SNAPSHOT_REPLAY
  UNKNOWN
```

---

## 6.3 历史重构标记

如果无法证明历史真实成员：

```text
history_basis =
CURRENT_MEMBERSHIP_REPLAY
```

不得写：

```text
PIT_HISTORICAL_REPLAY
```

这种 replay：

- 可以用于工程状态机测试；
- 可以用于界面历史演示；
- 不能用来证明历史板块 PREWATCH 效果。

---


# 6A. 双时间 PIT 与实际消费版本

可修订事实保存 effective_from/to、provider_available_at（可未知）、observed_at、ingested_at、source_revision_id、supersedes_revision_id、source_identity。available_at 旧别名只指 system_available_at=max(observed_at,ingested_at)，不能填供应商公开时间。

AS_RECORDED 读取 publication_consumed_sources 冻结的 key/revision/digest，不扫描最新事实。构建要求 effective_from<=T0<effective_to（空结束为无穷）、system_available_at<=cutoff；同 key 选 cutoff 内更正链唯一末端。分叉、内容冲突或无确定顺序为 SOURCE_REVISION_CONFLICT，不随意取最大时间。

原始行、tombstone、版本关系 append-only；消费 manifest 与 accepted head 原子提交。供应商早已公开但系统迟到的数据不属于过去 AS_RECORDED。知识时间重建与实际观察分开。

验收：T+10 才到的 effective=T-5 行、多版本、删除、乱序、分叉。旧 publication 与原 Forward enrollment digest 不变，当前修订显式变化。

---

# 7. Canonical Fact Layer

## 7.1 `market_fact_daily`

```text
publication_id
trade_date

median_ret1
breadth_ret1
breadth_ma20
breadth_ma60
new_high20_count
new_low20_count
up_limit_count
down_limit_count

amount_total
amount_ratio20

quality_status
quality_codes
fact_digest
```

---

## 7.2 `stock_fact_daily`

主键：

```text
(publication_id, security_id)
```

同时：

```text
trade_date NOT NULL
```

并通过：

```text
FK(publication_id, trade_date)
```

保证与 publication 日期一致。

核心：

```text
raw_close
adj_close
adj_high
adj_low

ret1
ret5
ret20

ma5
ma10
ma20
ma60

rps5
rps20

amount
volume

trading_status

fact_digest
quality_status
quality_codes
```

---

## 7.3 `sector_fact_daily`

```text
publication_id
trade_date
sector_id
sector_type

member_count
evaluable_member_count
quote_coverage

ret1_median
relative_to_market_1

breadth_ret1
breadth_common
breadth_delta1
breadth_delta3

ma20_width
ma20_delta1
ma20_delta3

sector_rs5
sector_rs20
sector_rs5_pct
sector_rs20_pct

rank_rs5
rank_rs20
rank_velocity3
rank_velocity5

strong_count
entered_count
exited_count
retention

amount_a_value / amount_a_quality（独立审计diagnostic）
sector_participation_proxy / proxy_delta3

base_seed aggregates 存 PASS B sector_seed_aggregates，不属于预计算 native facts

extended_share

top1_concentration
top3_concentration

quality_status
quality_codes
fact_digest
```

---


## 7.4 `stock_daily_profile`

主键(publication_id,security_id)，trade_date 复合 FK。Core 字段仅为 §10A.3 Core Profile V1；不含 basic_breakout/pullback/recovery 或 sector relative。

Participation 在 V4-06，Context/Structure 在 V4-13，Why Now 在 V4-15。组件状态独立为 NOT_IMPLEMENTED/PENDING_SOURCE/READY/PARTIAL/UNKNOWN_DATA/DEGRADED/NOT_APPLICABLE。全产品目标不要求 V4-04 完成后续能力。

Core digest 只绑定 Core；combined view digest 绑定完整 context token。异步 turnover 仅存 stock_profile_enrichments，不能改变 stock_fact_daily。

---

## 7.5 `stock_bar_weekly` / `stock_bar_monthly`

由 Canonical TDX Daily 派生。

字段：

```text
security_id
period_start_date
period_end_date
asof_trade_date
open/high/low/close
volume/amount
price_basis
bar_status
period_view
max_source_trade_date
source_daily_digest
```

---

## 7.6 `stock_structure_events`

```text
event_id
security_id
origin_trade_date
event_type
anchor_id
state
state_since
validity
quality
```

---

## 7.7 `stock_structure_anchors`

```text
anchor_id
security_id
anchor_type
anchor_date
anchor_raw_lower
anchor_raw_upper
anchor_price_basis
adjustment_contract_id
adjustment_source_identity
adjustment_asof
anchor_basis_trade_date
frozen_transform_coefficients
is_dynamic
source_event_id
validity
```

---

## 7.8 `sector_rotation_core_state_daily`

```text
publication_id
sector_id
rotation_core_state
relative_acceleration
breadth_state
retention_state
acceptance_state
participation_state
risk_state
```

Why Now 单独存 D 阶段 state_events/Radar，不进入 B 的摘要。

---

## 7.9 `source_packages`

用于 TDX vipdata 完整包与未来外部原始包：

```text
package_id
provider
source_url
observed_source_date
sha256
file_size
parser_version
import_status
```


## 7.10 `security_lifecycle_history`

用于 Historical Universe / survivorship-safe cross-section。

```text
security_id
symbol
security_type
board
list_date
delist_date
effective_from
effective_to
status
quality
source_contract_id
```

---

## 7.11 `stock_profile_enrichments`

Supplemental 数据与 Core Profile 解耦：

```text
publication_id
security_id
enrichment_revision
provider
turnover_rate
turnover_state
participation_context
provider_asof
binding_quality
quality_codes
created_at
```

不得通过此表直接改写 Core maturity / eligibility。

Core、sector aggregates、structure observations、state transitions、Radar/enrollment 均绑定 publication_id 与模型。Anchor 原值不可变，validity 存 observation。enrichment_revision 为每个 publication 全局 manifest revision，包含各证券/provider 的具体 revision；唯一键(publication_id,enrichment_revision,security_id,provider)。周期 bar 唯一键(publication_id,security_id,period_start_date,period_view,price_basis)，保存 adjustment identity，不覆盖旧周期版本。

---

## 7.12 `publication_source_cutoffs`

```text
publication_id
source_family
source_package_id
source_observed_at
provider_asof
max_source_trade_date
mandatory_flag
quality
```

用于证明每个结果当时读到了什么。

---

## 7.13 公共字段和实体完整性

PUBLICATION_V1：每个revision有不同opaque publication_id；UNIQUE(namespace,trade_date,core_revision)，trade_date复合FK防串日；parent/predecessor引用都按id冻结。currency=CNY、price/amount/volume单位分别存source contract，OHLC有限且positive，low<=open/close<=high，volume/amount非负；违例不静默修正。
QUALITY_V1：value、quality、reason、source_digest分开，不把UNKNOWN字符串存入数值列。事实族保留raw字段；派生字段保存contract/parameter/input digest。只有最终visibility由accepted head决定，事务失败的staging不被读API/统计消费。
security_id不是单纯symbol：带exchange与lifecycle identity，改名不改实体，代码复用另建实体；日期有效identity不足则UNKNOWN。Core actual_bar=(trading_status=ACTUAL_TRADED且OHLC/身份/日期通过)。
sector_seed_aggregates等B产物单独schema，不放进F0 native表假装已有；structure_health按关联事件优先级BROKEN→DAMAGED、HELD_CONFIRMED→STABLE、RECLAIMED→IMPROVING、其余有效→STABLE、缺数据→UNKNOWN，未交付组件NOT_IMPLEMENTED。

---

# 8. Data Quality & Degradation Contract

V4.0 的：

```text
READY / PARTIAL / UNAVAILABLE
```

保留，但必须增加原因。

## 8.1 Quality Reason Codes

```text
SOURCE_MISSING
SOURCE_STALE
INSUFFICIENT_HISTORY
LOW_COVERAGE
IDENTITY_MISMATCH
PARTIAL_MEMBERSHIP
CURRENT_MEMBERSHIP_REPLAY
CALENDAR_GAP
TRADING_STATUS_UNKNOWN
TURNOVER_UNBOUND
DERIVED_FROM_PARTIAL
DEPENDENCY_UNKNOWN
TDX_PACKAGE_MISMATCH
ADJUSTMENT_UNAVAILABLE
TURNOVER_PENDING
BAOSTOCK_UNBOUND
WEEKLY_BAR_IN_PROGRESS
MONTHLY_BAR_IN_PROGRESS
```

---

## 8.2 Quality Propagation

每个因子定义：

```text
required_inputs
optional_inputs
```

例如 Stock PREWATCH：

```text
price / RPS / position
= required

turnover
= supplemental-only，非 Core qualification input
```

如果 BaoStock 缺失：

```text
turnover_quality = UNAVAILABLE
```

但：

```text
stock_price_factor_quality
仍然可以 READY
```

禁止：

```text
一个 optional provider 缺失
→ 整只股票 UNAVAILABLE
```

---

# 9. BaoStock 换手率正式设计

## 9.1 权威边界

TDX：

```text
正式价格
正式复权
MA
high
return
RPS
Focus reference price
```

BaoStock：

```text
turnover supplementary fact
```

BaoStock 永远不能静默替代 TDX 正式价格。

---

## 9.2 Source Contract

实现前冻结：

```text
provider
endpoint
fields
unit
turnover_denominator
adjustment_mode
request_semantics
provider_limit
error_codes
```

如果官方规则变化：

```text
new source_contract_id
```

---

## 9.3 请求策略

优先级：

```text
P0 Daily Incremental
P1 Missing Recent Window
P2 Historical Backfill
P3 Manual Diagnostic
```

日常增量绝不能被历史回填耗尽额度。

---

## 9.4 历史回填

最低覆盖：目标日前60个实际成交且 strict-bound 样本，加目标日；优选此前250样本。基准排除当日，确认停牌才能跳过，未知网络缺失不能跳过。最大回看250市场会话，不足窗口只降级该指标。

任务 checkpointable/idempotent/budget-aware；每请求 timeout、并发、重试预算、熔断写入 source contract。已有回执可复用，不做无界测速，不阻断 Core。

---

## 9.5 绑定状态

```text
BOUND_STRICT
BOUND_SOFT
UNAVAILABLE
```

### `BOUND_STRICT`

满足：

```text
security identity
exact trade_date
tradestatus
unit normalized fingerprint
```

并通过版本化容差。

### `BOUND_SOFT`

大部分事实一致，但某个辅助 fingerprint 只在宽松容差内。

第一版：

```text
diagnostic only
```

### `UNAVAILABLE`

不进入正式 turnover factor。

---

## 9.6 Turnover Factor

contract_id=TURNOVER_CONTEXT_V1。priorN 为 t 前最近 N 个确认实际成交且严格绑定样本；未知缺失不能跳过，N=5/20/60，最大回看250市场日。ma5=prior5均值，median20=prior20中位数，ratio20=turn[t]/median20（分母<=0为UNAVAILABLE）；pctN=100*(count(prior<turn[t])+0.5*count(prior=turn[t]))/N。delta3=turn[t]-turn[t-3]，市场日期端点缺失为UNKNOWN。

全部为 supplemental，不进入 Core eligibility、正式排序或 Focus activation。单位由 source contract 冻结。

---

## 9.7 Turnover 第一版权限边界

第一版换手率可以：

```text
展示
Participation context
Conflict Panel
Hypothesis discriminator
辅助 priority 的非正式诊断视图
```

第一版换手率不可以：

```text
改变 PREWATCH hard eligibility
改变 maturity stage
改变当天 Focus transition
改变当天 Validation enrollment
```

原因不是认为换手没有价值，而是：

```text
external free provider
+
后置异步 enrichment
+
无同等级 SLA
```

还不足以成为正式 Publication 的强依赖。

等未来升级到 mandatory pre-publication source 后，再发布新合同，不允许在实现中偷偷扩大权限。

---


# 9A. Pure-Core 与 Supplemental Variant 合同

V4.2.2 禁止 supplemental turnover 通过风险、Impulse 或 Rotation 间接进入 Core。

## 9A.1 Core Extension Risk

正式字段：

```text
core_extension_risk
```

只能使用：

```text
price distance
ATR / realized volatility
recent price impulse
MA / high distance
TDX amount / volume + price result
```

不得使用：

```text
turnover
BaoStock isST
BaoStock tradestatus
```

可另算：

```text
supplemental_extension_note
```

但不进入 Hard Safety。

## 9A.2 Core Bullish Impulse

正式 Anchor 创建资格：

```text
core_bullish_impulse
```

只使用：

```text
body / ATR
range / ATR
CLV
TDX amount / volume
relative_market_result
```

turnover 只能形成：

```text
turnover_enriched_impulse_context
```

不能决定 Anchor 是否存在。

## 9A.3 Core Rotation

正式：

```text
rotation_core_state
```

不得使用：

```text
turnover
member_turnover_context
supplemental_participation
```

这些只能形成：

```text
rotation_participation_enrichment
```

## 9A.4 ST / Trading Status Core Authority

Core 使用：

```text
canonical_security_master
accepted local TDX metadata
canonical price/calendar observation
```

作为正式身份/交易状态来源。

BaoStock：

```text
tradestatus
isST
```

只作为 cross-check / supplemental evidence。

如果 Core ST 身份不足：

```text
ST_STATE = UNKNOWN
price_limit_rule = DEGRADED / UNKNOWN
```

不能因 BaoStock 晚到改写已 accepted Core。

## 9A.5 一致性验收

同一 Core source 分别运行：

```text
A. no turnover
B. turnover cached before run
C. turnover arrives after publication
D. turnover conflicts with local metadata
```

必须证明：

```text
core_eligibility_digest
core_state_digest
core_event_digest
validation_enrollment_digest
```

完全一致。

---

# 10. Factor Layer

## 10.1 Position

UI 保留百分比：

```text
bias20
dist_high20
```

算法同时新增：

```text
ATR20
BIAS20_ATR
DIST_HIGH20_ATR
```

定义：

```text
BIAS20_ATR
= (close - ma20) / ATR20

DIST_HIGH20_ATR
= (prior_high20 - close) / ATR20
```

如果 ATR 数据质量不足：

```text
fallback = NONE；ATR不足时该归一化字段UNKNOWN（CORE_FACTOR_V1）
```

但必须带：

```text
normalization_method
```

---

## 10.2 Structure

```text
range5 / range20
realized_vol5 / realized_vol20
ATR contraction
amount quietness
```

---

## 10.3 Relative Change

把原本高度相关的：

```text
RPS acceleration
relative market
relative sector
```

放进同一个：

```text
RELATIVE_CHANGE Domain
```

不允许各自贡献一份“独立证据”。

核心事实：

```text
rps5_delta1
rps5_delta3
rps20_delta3

rel_market_1
rel_market_3
rel_market_5

rel_sector_1
rel_sector_3

short_long_divergence
= rps5 - rps20
```

---


# 10A0. 原子因子、三值逻辑与冻结门

每个算法 contract id + §72 parameter_set_id 必须可序列化为 input/producer/time/quality、AST、窗口、舍入、互斥、输出身份和测试向量。V4-00G 建框架，对应阶段先生成机器合同再实现；不要求未来模块完成才准基线盘点。

Kleene 三值逻辑：FALSE AND UNKNOWN=FALSE；TRUE AND UNKNOWN=UNKNOWN；TRUE OR UNKNOWN=TRUE；FALSE OR UNKNOWN=UNKNOWN；NOT UNKNOWN=UNKNOWN。Hard Safety 先归约：已知FALSE拒绝，否则含UNKNOWN则UNKNOWN；禁止 None!=True 通过。分类按 first-true；高优先级未知分支可能改变结果则UNKNOWN，optional diagnostics不污染资格。

## CORE_FACTOR_V1

t 是冻结市场日历索引。O/H/L/C 在观察日同一已验证仿射坐标，a/v 是原始金额/量。全精度计算和比较，仅显示舍入。零分母为UNKNOWN，不用epsilon造巨大有效数。

- MA_N=最近N市场会话收盘均值；本版要求连续实际bar，确认停牌也不填0/不跳日凑数，缺失为INSUFFICIENT_CONTIGUOUS_HISTORY。
- retN=C[t]/C[t-N]-1；volN=std(log(C[j]/C[j-1]),ddof=0)，j=t-N+1..t，未年化，均需N+1实际bar。
- TR[j]=max(H[j]-L[j],abs(H[j]-C[j-1]),abs(L[j]-C[j-1]))；ATR_N=SMA(TR,N)。ATR<=0时归一化UNKNOWN，本版不自动换volatility fallback。
- prior_highN=max(H[t-N:t-1])；HHV_N=max(H[t-N+1:t])；低点同理。pos60=(C-LLV60)/(HHV60-LLV60)，零振幅UNKNOWN。
- slope20=(MA20[t]-MA20[t-5])/ATR20；slope60=(MA60[t]-MA60[t-10])/ATR20。
- HH_PROGRESS=max(H[t-4:t])>max(H[t-9:t-5])；LL_PROGRESS=min(L[t-4:t])<min(L[t-9:t-5])。
- RPS_N=100*(less+0.5*(equal-1))/(n-1)，N=5/20；对同日historical evaluable Universe retN排名，n<2 UNKNOWN，同值同分。delta使用百分点。
- rel_market_N=retN-market_reference_return_N（§49A）；delta3=rps5[t]-rps5[t-3]。
- range_ratio=(HHV5-LLV5)/(HHV20-LLV20)；atr_ratio=ATR5/ATR20；vol_ratio=vol5/vol20。
- amount_ratioN=a[t]/mean(a[t-N:t-1])；volume_ratioN同理，N=5/20。percentile60按prior60 midrank，排除当日。
- CLV=(C-L)/(H-L)；H=L时UNKNOWN，不凭一字板虚构收盘强度。
- core_price_damage=(C<prior_low20-0.5*ATR20 AND ret1<0)，只读价格，不读Anchor/Final State。

严格连续窗口是保守工程基线，不代表停牌的经济收益为0。Forward另有路径规则。300市场日warm-up只是规划目标，各字段实际首个可用日独立报告。

本文章节规则实例化为RULE_AST_FROZEN，经schema及独立正反向向量验收才TEST_VECTOR_PASS。旧V3/V3.3通过§34精确extraction manifest冻结，不能仅说沿用思想。

---

# 10A. 全市场 Daily Stock Profile

## 10A.1 定位

V4.2 的关键升级是：

> 先理解全市场，再从中筛少量优先研究对象。

每天对 `V4_RESEARCH_UNIVERSE` 中所有股票生成：

```text
stock_daily_profile
```

即使股票没有进入 Seed / PREWATCH / Confirmed / Focus，用户搜索它时仍有完整基础研究信息。

---

## 10A.2 Daily Profile 与筛选器彻底分离

```text
Canonical Facts
      ↓
Canonical Factors
      ↓
Daily Stock Profile  ← 全市场
      ↓
Seed / PREWATCH / Confirmation ← 优先级筛选
```

禁止：

> 只有进入候选的股票才计算结构状态。

---

## 10A.3 Daily Profile 分层交付合同

V4.2.2 的 **Core Profile V1** 必须在没有 Sector、Rotation、Anchor、Support、BaoStock 的情况下独立完成。

### Core Profile V1

只允许输入：

```text
Canonical TDX Daily
PIT-safe Weekly/Monthly
Market Canonical Facts
Historical Security Universe
Pure price/amount factors
```

必须完成：

```text
trend_state
weekly_trend_state
monthly_trend_state
position_state
ma_structure_state

relative_market_state
compression_state
amount_state
volume_state
core_extension_risk
trading_status

near_high20_state
near_high60_state
drawdown20_state
drawdown60_state
```

明确不属于 Core V1：

```text
sector_relative_market_state
algorithmic_support_sector
rotation_context

accepted_breakout
pullback_to_anchor
support_state
recovery_from_anchor
retest / retention

turnover_state
turnover_enriched_participation

why_now
hypothesis_set
```

因此 V4-04 不需要后置模块才能 PASS。

### Participation Enrichment

增加：

```text
turnover_state
turnover_context
supplemental_participation_context
```

### Sector Context Enrichment

增加：

```text
relative_sector_state
primary_industry
supporting_concepts
algorithmic_support_sector
sector_context_state
rotation_context_state
```

### Advanced Structure Enrichment

增加：

```text
active_anchor
breakout_event
pullback_event
support_state
reclaim
retest
acceptance_state
recovery_from_anchor
```

### Research Projection

增加：

```text
Why Now
Waiting For
Invalid If
Conflict
Hypothesis Set
```

这些都不是基础 Profile 的物理事实。

## 10A.4 `NOT_IMPLEMENTED` 与 `UNKNOWN`

组件状态：

```text
NOT_IMPLEMENTED
PENDING_SOURCE
READY
PARTIAL
UNKNOWN_DATA
DEGRADED
NOT_APPLICABLE
```

例如 Support Engine 尚未安装：

```text
support_component_status = NOT_IMPLEMENTED
```

不能伪装成：

```text
support_state = UNKNOWN
```

然后声称“完整画像已完成”。

---

# 10B. Trend State 算法

contract_id=TREND_STATE_V1。required：MA20/60、slope20/60、HH/LL_PROGRESS、core_price_damage、C、ATR20。UP20=slope20>0.1，DOWN20=slope20<−0.1；UP60/DOWN60同理。依次first-true：

| 状态 | Rule AST |
|---|---|
| DOWNTREND_STRONG | C<MA20 AND DOWN20 AND DOWN60 AND LL_PROGRESS |
| UPTREND_STRONG | C>MA20 AND UP20 AND (C>MA60 OR UP60) AND HH_PROGRESS AND NOT core_price_damage |
| DOWNTREND | C<MA20 AND DOWN20 |
| UPTREND | C>MA20 AND UP20 AND NOT core_price_damage |
| SIDEWAYS_WEAK | C<MA20 |
| SIDEWAYS_STRONG | C>MA20 |
| SIDEWAYS | 其余可评估情况 |

周趋势仅用CLOSED_ONLY：WEEKLY_UP=Cw>MA5w AND MA5w>MA5w[-1]，DOWN反向，其余FLAT。月线用MA3m同规则。未知为UNKNOWN；进行中bar仅在图表另标，不影响正式趋势。

# 10C. Position State

contract_id=POSITION_STATE_V1。bias20_atr=(C-MA20)/ATR20，dist_high20_atr=(prior_high20-C)/ATR20。依次EXTENDED（bias>=3）、HIGH_ZONE（pos60>=0.8）、MID_HIGH（>=0.6）、MID_ZONE（>=0.4）、MID_LOW（>=0.2）、LOW_ZONE。required未知则UNKNOWN；pos250仅诊断。
near_highN_state(N=20/60)：d=(prior_highN-C)/ATR20；d<0 ABOVE_PRIOR_HIGH，0<=d<=0.5 NEAR，其余BELOW。drawdownN=C/HHV_N-1；>=−0.05 SHALLOW，>=−0.15 MODERATE，其余DEEP。这些是描述，不是接受突破或统一风险。

# 10D. MA Structure State

contract_id=MA_STRUCTURE_V1。依次BULL_ALIGNED（MA5>MA10>MA20 AND slope20>0）、BEAR_ALIGNED（反向）、BULL_TRANSITION（MA5>MA20 AND slope20>=0）、BEAR_TRANSITION（反向）、MIXED。required未知为UNKNOWN。

# 10E. Relative Market State

contract_id=RELATIVE_STATE_V1。required：rps5/20、delta3、rel_market_1/5、compression_state、ma_structure_state；不读trend_state或sector。
active=(delta3>=10 AND (compression_state in {COMPRESSING,COMPRESSING_STRONG} OR ma_structure_state in {BULL_TRANSITION,BULL_ALIGNED}))。
依次ACTIVE_EMERGENCE（active）；PASSIVE_RESILIENCE（rel_market_1>0 AND NOT active AND delta3<=0）；LEADING_ACCELERATING（rps20>=80 AND delta3>0）；LEADING_STABLE（rps20>=80 AND delta3>=−3）；IMPROVING（delta3>3）；WEAKENING（delta3<−3）；LAGGING（rps20<20）；NEUTRAL。required未知为UNKNOWN。
relative_sector_state在V4-13使用同拓扑，以LOO rel_sector替换market relative，不进入Core/Seed。

# 10F. Compression State

contract_id=COMPRESSION_STATE_V1。required：range_ratio/atr_ratio/vol_ratio/amount_ratio20/minimum_liquidity。
依次EXPANDING_EXTREME（atr_ratio>=1.5 OR vol_ratio>=1.5）；EXPANDING（任一>=1.1）；COMPRESSING_STRONG（range_ratio<=0.35 AND atr_ratio<=0.7 AND vol_ratio<=0.7 AND amount_ratio20<=0.8 AND minimum_liquidity）；COMPRESSING（range_ratio<=0.6 AND atr_ratio<=0.9 AND vol_ratio<=0.9 AND minimum_liquidity）；NORMAL。未知则UNKNOWN，扩张优先。

# 10G. 成交额/量及价格结果

contract_id=AMOUNT_VOLUME_STATE_V1。amount_state/volume_state各自ratio20：<0.5 VERY_DRY、<0.8 CONTRACTED、<1.2 NORMAL、<2 EXPANDED、其余VERY_EXPANDED，缺失UNKNOWN。
core_participation_result依次：HIGH_PARTICIPATION_REVERSAL（amount_ratio20>=1.2 AND ret1<0）；HIGH_PARTICIPATION_EFFECTIVE_ADVANCE（ratio>=1.2 AND ret1>0 AND CLV>=0.7）；HIGH_PARTICIPATION_LOW_EFFICIENCY（ratio>=1.2）；LOW_PARTICIPATION_ADVANCE（ratio<0.8 AND ret1>0）；LOW_PARTICIPATION_DECLINE（ratio<0.8 AND ret1<0）；NORMAL_PARTICIPATION。依赖CLV的更高分支未知时不得直接落入低效分类。
supplemental_participation_context只把turnover_state与Core结果并列，不改Core。

# 10H. Turnover State

contract_id=TURNOVER_CONTEXT_V1。pct60：<20 LOW、<70 NORMAL、<90 ELEVATED、<97 HIGH、其余EXTREME。尚未绑定PENDING，不支持/绑定失败UNAVAILABLE，窗口不足组件UNKNOWN_DATA。只作补充，非收益概率。

# 10I. Core Extension Risk

contract_id=EXTENSION_RISK_V1。依次EXTREME（bias20_atr>=4）；HIGH（bias>=3 OR (ret5>=3*ATR20/C AND amount_ratio20>=2 AND ret1<=0)）；MEDIUM（bias>=2）；LOW。只检查分支required输入，未知依三值逻辑；severe_extension=(risk=EXTREME)。turnover只进supplemental_extension_note。

# 10J. Basic Breakout State（V4-12）

contract_id=STRUCTURE_EVENT_V1。无活动breakout事件：C>prior_high20+0.1*ATR20 AND CLV>=0.7产生BREAKOUT_TENTATIVE和PRIOR_HIGH Anchor；否则near_high20=NEAR为APPROACHING，其余NO_BREAKOUT。
已有事件：BROKEN/INVALIDATED→FAILED_BREAKOUT；HELD_CONFIRMED或创建后至少2连续可评估日C>=anchor_upper→BREAKOUT_ACCEPTED；当日触碰→TESTING；其余保留BREAKOUT_TENTATIVE。未知不制造状态；创建日不能接受。

# 10K. Basic Pullback State（V4-12）

contract_id=STRUCTURE_EVENT_V1。无此前有效上涨/突破/impulse事件为NOT_PULLBACK。已有Anchor依次：BROKEN/INVALIDATED→PULLBACK_FAILED；HELD_CONFIRMED→PULLBACK_HELD；RECLAIMED/HELD_TENTATIVE→PULLBACK_RECLAIMED；触碰按类型PULLBACK_TO_MA/BREAKOUT/IMPULSE；未触碰且从事件后峰值回落→PULLBACK_IN_PROGRESS；其余NOT_PULLBACK。只用t-1冻结事件，未知为UNKNOWN。

# 10L. Recovery State（V4-12）

contract_id=STRUCTURE_EVENT_V1。依次RECOVERY_FAILED（已有恢复事件失效）；RECOVERY_CONFIRMED（事件后至少2连续可评估日守住冻结恢复线）；ANCHOR_RECLAIM（旧Anchor当日EOD reclaim）；MA20_RECLAIM（C[t-1]<=MA20[t-1] AND C[t]>MA20[t]）；RELATIVE_RECOVERY（delta3从<=0转>3 AND rel_market_1>0）；BOUNCE_ONLY（ret1>0）；NONE。创建恢复事件保存原线，不同日追认，未知按三值逻辑。

# 10M. 页面解释

Core先回答趋势、位置、压缩、量额、相对市场与风险；高级组件交付后回答突破/回踩/支撑/恢复。NOT_IMPLEMENTED/UNKNOWN/NOT_APPLICABLE不得写成资格FALSE。全产品目标保留，V4-04不承担后置验收。

---

# 10N. A股 Price Limit / Trading Constraint Rule Engine

新增正式模块：

```text
price_limit_rule_engine.py
```

目的：

> 不允许用 `ret >= 9.9%` 这种简化规则识别涨停。

## 10N.1 输入

```text
security_id
trade_date
board
security_type
isST_status
listing_age
previous_close
open/high/low/close
trading_status
price_tick
rule_contract_id
```

## 10N.2 Rule Contract

规则必须按：

```text
trade_date
board / security type
ST status
listing stage
```

选择制度版本。

不能假设所有历史日期制度相同。

## 10N.3 输出

```text
theoretical_limit_up
theoretical_limit_down

limit_status =
  NONE
  UP_LIMIT
  DOWN_LIMIT
  ONE_WAY_UP_LIMIT
  ONE_WAY_DOWN_LIMIT
  TOUCHED_UP_LIMIT
  TOUCHED_DOWN_LIMIT
  RULE_NOT_APPLICABLE
  UNKNOWN

limit_rule_quality
```

## 10N.4 一字板

如果：

```text
open == high == low == close == theoretical_limit_up
```

在容差内：

```text
ONE_WAY_UP_LIMIT
```

跌停同理。

## 10N.5 数据不足

如果：

```text
ST 身份未知
制度版本未知
previous_close 无法确认
```

必须：

```text
limit_status = UNKNOWN
```

禁止猜测。

## 10N.6 因子影响

涨跌停价格仍是 OF，可参与事实记录；但下游必须知道：

```text
return is price-limit censored
turnover/amount may be liquidity constrained
RPS tie may increase
```

不能把封板导致的低成交直接解释为“供应枯竭”。

---

# 11. Passive Resilience 与 Active Emergence

ACTIVE_EMERGENCE、PASSIVE_RESILIENCE唯一算法为§10E；本节解释其含义，不另设第二套资格规则。相对市场上涨不等于个股上涨；低Beta防御和主动改善不能仅凭单日跌得少区分。系统同时列ret1/relative_market/delta3/结构事实，不能用模板推断资金意图。
rel_market_vol_adj=rel_market_1/vol20，vol20<=0/未知为UNKNOWN，作为诊断而非单独硬资格。Beta residual与全面中性化不进入V1。价格衍生证据相关性必须披露，不重复算独立支持。

---

# 12. Evidence Domain 体系

V4.0 的 family 改成：

```text
Domain
```

## 12.1 Domains

### POSITION

```text
bias20
bias20_atr
dist_high20
dist_high20_atr
position60
```

### STRUCTURE

```text
range contraction
volatility contraction
compression duration
```

### RELATIVE_CHANGE

```text
RPS acceleration
short-long divergence
market relative
sector relative
```

### TREND_TRANSITION

```text
MA structure
slope transition
reclaim
recovery
```

### PARTICIPATION

```text
amount ratio
turnover ratio（supplemental-only）
turnover percentile（supplemental-only）
```

### CONTEXT

```text
sector emergence
market regime
```

### RISK

```text
extension
damage
liquidity
trading status
data quality
```

---

## 12.2 不再使用简单 Domain Count 做资格

正式资格用：

```text
Rule Path
```

而不是：

```text
COUNT(domain_true) >= 3
```

---

# 13. 防反馈计算 DAG

正式计算分层如下；“当日 detector事实”与“最终状态/事件”不同。依赖边以字段及时间为单位，而不是仅按模块文件名。

# 13A. 当日拓扑 DAG_V1

| 层 | 产物 | 允许输入 |
|---|---|---|
| F0 | Native facts、Core factors/Profile | frozen source、日历、Universe |
| A | Base Seed | F0纯价格/量额，不读Anchor/sector/final state |
| B0 | Sector aggregates/emergence原始谓词 | Native sector facts、A[t]、冻结历史 |
| B1 | Rotation | B0、A历史、PREWATCH[t-1]成员当日Core结果；不读当日最终成熟度 |
| B2 | Sector raw qualification | B0规则，Rotation只供D排序解释；不反写B0 |
| C | Stock PREWATCH raw qualification | A、Core quality、core_price_damage |
| D0 | Confirmation detector事实 | F0、B2/LOO事实及已冻结legacy纯函数，不读最终状态 |
| D1 | Structure detector/旧Anchor失效事实 | F0、t-1冻结Anchor/event；不读D2 |
| D2 | Final state reducer | C/B2/D0/D1、冻结前态、合规迁移manifest |
| D3 | Event diff、Radar、Cohort enrollment | D2及冻结前态；Context LOO使用独立排除目标结果 |
| E | publication accept、Focus outbox、settlement | 已验证staging与accepted来源 |

同日禁止D→A/B/C、C→B、Focus/UI/Supplemental→资格。D1新建Anchor只能作为今日新事件，最早次日参加路径测试，不能同日自证支撑。

原始C资格是算法证据；D2可因该研究episode旧Anchor硬失效禁止最终PREWATCH/Confirmation，不能把D2结果回灌今日B的Seed宽度。保存raw_qualification与final_eligibility解释差异。

每条边登记producer、contract/version、字段、t或t-1、namespace、required/optional。验收扰动C[t]不得改变B；扰动Supplemental不得改变A–D；同日确认与旧Anchor硬失效冲突时，D2正确失效，无隐式重跑。

---

# 14. PASS A：Stock Base Seed

## 14.1 输入限制

只能使用：

```text
stock canonical facts
market canonical facts
historical stock factors
```

禁止：

```text
final sector PREWATCH
final stock PREWATCH
today radar
Focus state
```

---

## 14.2 Hard Safety

contract_id=BASE_SEED_V1。safety=research_universe AND actual_bar AND price_identity_READY AND minimum_liquidity AND NOT core_price_damage AND NOT severe_extension。三值归约后FALSE拒绝，UNKNOWN待评估，TRUE才检查路径。minimum_liquidity=prior20 mean amount>=20,000,000 CNY；金额单位先通过source contract。本版为工程候选，不冒充已验证最佳阈值。

## 14.3 Seed Rule Paths

POSITION_OK=(bias20_atr<3)；STRUCTURE_IMPROVING=(compression_state in {COMPRESSING,COMPRESSING_STRONG})；RELATIVE_CHANGE_IMPROVING=(delta3>=3)；RELATIVE_CHANGE_STRONG=(delta3>=10)；TREND_TRANSITION_EARLY=(ma_structure_state=BULL_TRANSITION OR (C[t-1]<=MA20[t-1] AND C[t]>MA20[t]))。

S1=POSITION_OK AND STRUCTURE_IMPROVING AND RELATIVE_CHANGE_IMPROVING。
S2=POSITION_OK AND RELATIVE_CHANGE_STRONG AND TREND_TRANSITION_EARLY。
base_seed_state=safety AND (S1 OR S2)。这些谓词只读Core，严格三值逻辑，不读高级Anchor。

seed_participation_annotation按core_participation_result：有效推进SUPPORTED，反转/低效CONFLICTING，其余NEUTRAL，未知UNKNOWN。不计新路径、不影响资格；turnover只另作补充说明，不进入正式排序。

---

## 14.4 输出

```text
base_seed_state
matched_seed_paths
domain_states
waiting_for
invalid_if
quality
fact_digest
```

---

# 15. Sector Native 与聚合合同

contract_id=SECTOR_FACTORS_V1。对日期t的真实成员M_t构建可评估集合E_t，quote_coverage=|E_t|/|M_t|；未知成员来源为UNKNOWN。Core sector最低成员5、coverage>=0.8，低于门限不产生正式sector资格。

sector_rsN=成员retN中位数，sector_rsN_pct按同日source/type/member/coverage合格的全体板块（非算法已入选集合）midrank（§10A0公式），rank_velocityK=percentile[t]-percentile[t-K]，dq5=rs5_pct[t]-rs5_pct[t-3]。排名跨日Universe变化要保存两个snapshot；同分同分位，展示tie-break用sector_id。

breadth_ret1=count(ret1>0)/count(ret1 known)；ma20_width=count(C>MA20)/count(MA20 known)。deltaK只在M_t∩M_(t-K)且两端该指标均可评估的共同成员上分别重算再相减；保存common_count与coverage。成员新增/删除单独记录membership_entered/exited，不算市场强弱进出。

strong成员=RPS20>=80且可评估；retention=|strong_prev∩strong_now|/|strong_prev|，分母0为NOT_APPLICABLE。未知当前结果标unknown_retention_count，不当退出；Core需要全部该分母成员可观察，否则该retention UNKNOWN。Seed留存同理；PREWATCH仅用t-1成员在t日Core谓词是否仍满足，不读取C[t]最终集合。

sector_participation_proxy=median(成员amount_ratio20)，与Amount A明确不同；top1/top3_concentration为金额份额，分母是同日可评估成员金额总和，零分母UNKNOWN。正式Core本版不用未关闭的Amount A，也不用turnover。

# 16. 小板块调整

contract_id=SEED_WIDTH_V1。n=BaseSeed可评估成员数，k=TRUE数；n=0 UNKNOWN。raw=k/n；adjusted=(p+z²/(2n)-z*sqrt(p*(1-p)/n+z²/(4n²)))/(1+z²/n)，z=1.96。

Wilson式只作为样本量惩罚的排序启发式，不声称成员独立、统计置信覆盖或上涨概率；板块成员相关，不能据此作概率结论。保存k/n/unknown_count/raw/adjusted，coverage门先于排序。

---

# 17. Sector PREWATCH / WARM / CONFIRMED

contract_id=SECTOR_QUALIFICATION_V1。sector_safety=membership_READY AND member_count>=5 AND quote_coverage>=0.8。
prewatch_raw=sector_safety AND dq5>=3 AND (breadth_delta3>0 OR ma20_delta3>0) AND adjusted_seed_width>=0.05。不要求市场上涨；UNKNOWN不当FALSE。此原始谓词不排除更高阶段，最终D2按最高已确认资格选成熟度。
warm_raw、confirmed_raw来自§34已提取验收的纯Core legacy合同；未就绪时该能力NOT_IMPLEMENTED，不从POTENTIAL/CURRENT标签猜测规则。若legacy资格依赖未关闭Amount A，则该路径不能作为正式资格，保留diagnostic；其他独立路径不受影响。

# 18. Sector 三轴

contract_id=SECTOR_AXES_V1。emergence：HIGH（dq5>=10 AND breadth_delta3>=0.05 AND adjusted_seed_width>=0.1）；MEDIUM（dq5>=3 AND (breadth_delta3>0 OR ma20_delta3>0)）；LOW（其余可评估）。confirmation_axis保存confirmed_raw/warm_raw/coverage，不读D2。
exhaustion：HIGH（rs20_pct>=80 AND dq5<=−5 AND breadth_delta3<=−0.05）；MEDIUM（rs20_pct>=80 AND dq5<0）；LOW。extension share作为并列事实，不重复计价。required未知则对应轴UNKNOWN，不用其他轴掩盖。

---

# 19. 板块重叠与概念去重

## 19.1 不做 1/N 成员稀释

每个板块仍按自己的成员集合计算。

---

## 19.2 新增 Overlap Diagnostics

```text
sector_overlap_jaccard
overlap_cluster_id
unique_member_share
top_member_concentration
```

高重叠概念可以在 UI 合并展示：

```text
主题簇
```

但底层板块事实保持独立。

---

# 20. Stock Sector Context 合同

一个股票可以有：

```text
PRIMARY_INDUSTRY
SUPPORTING_CONCEPTS[]
ALGORITHMIC_SUPPORT_SECTOR
```

---

## 20.1 PRIMARY_INDUSTRY

来自确定性的行业分类关系。

不能因当天强弱变化。

---

## 20.2 SUPPORTING_CONCEPTS

保存全部符合关系合同的概念。

---

## 20.3 ALGORITHMIC_SUPPORT_SECTOR

contract_id=LOO_CONTEXT_V1。在真实membership内，对目标股排除后重算sector native、seed aggregates、B0/B2原始资格以及其所需的历史比较。不得只减计数而保留原rank/median/状态。历史状态若用于context也从排除目标的独立lineage重算；无法重算时不使用该项。
按LOO confirmed_raw、warm_raw、emergence(HIGH>MEDIUM>LOW)、adjusted_seed_width降序，再sector_id升序选择。过滤quality非READY。保存全部候选及选择理由；没有合格者NULL/NOT_APPLICABLE，数据不足UNKNOWN。Context最多一份，不能提升stock hard eligibility。

---

## 20.4 Historical Sector Context Quality

投产前历史若只能：

```text
CURRENT_MEMBERSHIP_REPLAY
```

则 Stock Profile 中：

```text
algorithmic_support_sector
sector_context_state
rotation_context_state
```

必须同步写：

```text
sector_context_quality = CURRENT_MEMBERSHIP_REPLAY
```

页面规则：

```text
普通历史研究：
可显示，但必须标“当前成员回放，仅供诊断”

严格 PIT Replay：
默认隐藏 / 降级为 UNKNOWN
```

不能把后来知道的概念成员关系包装成当时系统已知的 Sector Context。

---

# 21. Full LOO 泛化

现有 `full_loo_v3_3.py` 的思想保留，但 本版 要从：

```text
CURRENT support
```

泛化成：

```text
all stock-level sector context facts
```

对个股研究使用：

```text
sector_breadth_ex_target
sector_seed_width_ex_target
sector_rs_ex_target
sector_emergence_ex_target
```

不能：

```text
目标股票自己让板块变强
→ 板块再证明目标股票强。
```

---


# 21A. Rotation State Engine

## 21A.1 目标

A 股板块轮动频繁，不能把：

```text
今天涨幅第一
```

直接当成：

```text
新主线 / 新确认。
```

Rotation Engine 研究的是：

> 相对市场资源是否正在向某板块转移，以及这种转移之后的价格结果是否被保留和接受。

---

## 21A.2 研究对象类型

首页 Radar 统一处理：

```text
INDUSTRY
THEME / CONCEPT
```

不分两个大榜。

明确排除：

```text
STYLE
通达信风格板块
```

如果某板块类型无法识别：

```text
sector_type = UNKNOWN
```

不得进入正式首页，直到完成类型映射。

---

## 21A.3 Rotation State

```text
NONE
ROTATION_PULSE
ROTATION_IN
ROTATION_ACCEPTED
ROTATION_EXPANDING
ROTATION_REACCELERATING
ROTATION_OUT
ROTATION_FAILED
UNKNOWN
```

---

## 21A.4 Rotation Core Rules

contract_id=ROTATION_CORE_V1。使用§15/16/18的纯Core事实与冻结历史。历史PREWATCH仅作t-1成员参考；当日PREWATCH、Final Confirmation、Support/turnover均禁止输入。

保存rotation_episode_id、pulse_date、冻结成员篮子和pulse前基准；sector_price_retention_core由该篮子等权路径计算（§49A），而不是每日中位收益拼成价格。pulse收益分母<=0时retention_ratio为NOT_APPLICABLE，不能用epsilon强行作除法。

候选规则：pulse=(dq5>=10 AND breadth_delta1>=0.05)；retained=(冻结篮子累计收益>0 AND strong_member_retention_1>=0.5)；failed=(pulse后1..5市场会话内篮子累计收益<=0 AND breadth_delta1<=−0.05)。扩散=(entered_count>exited_count AND breadth_delta1>0 AND top1_concentration<=0.5)，成员变更不计入entered/exited。

有序状态：
1. 必要输入未知→UNKNOWN，暂停该episode计数不伪造退出。
2. 已有episode且failed→ROTATION_FAILED。
3. t-1已WARM/CONFIRMED且dq5<0、breadth_delta1<0连续2可评估市场会话→ROTATION_OUT。
4. t-1已成熟、昨日dq5<=0、今日pulse且retained→ROTATION_REACCELERATING。
5. 已有至少2个后续会话且retained、昨日已ACCEPTED/EXPANDING且扩散→ROTATION_EXPANDING。
6. pulse后至少2会话且retained且breadth_delta1>=−0.05→ROTATION_ACCEPTED。
7. pulse后至少1会话且retained→ROTATION_IN。
8. 无活动episode且pulse→ROTATION_PULSE并冻结episode。
9. 未终止活动episode在创建后5会话内无新规则→保持前态；超过5会话未accepted→ROTATION_FAILED；无活动episode→NONE。

接受后episode不再使用“5日未接受”到期；OUT/FAILED为终止事件，次日可新pulse，旧历史保留。发生同日冲突按上述优先级。Rotation只进入D的解释/排序，不回写B0资格。

## 21A.4A 输入时点

B1读取B0[t]、A[t]、frozen history[t-1]；使用t-1成熟度而不是本日最终状态。高级Structure在V4-12完成后可于D3增加rotation_structure_enrichment，不改B1。扰动测试证明当日C/D/Supplemental改变不影响B。

---

## 21A.12 页面展示

今日总览显示：

```text
轮动脉冲
轮动进入
已被接受
正在扩散
再次加速
轮出/失败
```

并显示：

```text
Why Now
成员留存
宽度
相对强度变化
参与度
反证
```

而不是只显示板块涨幅。


# 22. PASS C：Stock PREWATCH

## 22.1 PREWATCH Eligibility

contract_id=STOCK_PREWATCH_V1。raw_qualification=base_seed_state AND mandatory_core_quality_READY。C只输出原始资格，不读D2 validity。D2在§31结合已冻结研究episode的当日硬失效，产生final_eligibility。Sector Context只在D3影响解释和独立context排序键，不能成为硬门。

---

# 23. PREWATCH Priority Axes

禁止一个神秘：

```text
total_score = 87.34
```

采用三轴：

```text
EMERGENCE
STRUCTURE_QUALITY
RISK
```

再加：

```text
CONTEXT
STALENESS
```

---

## 23.1 Emergence

来源：

```text
relative_change
rps acceleration
trend transition
change velocity
```

---

## 23.2 Structure Quality

来源：

```text
position
compression
ATR-normalized distance
```

---

## 23.3 Risk

来源：

```text
extension
structure damage
limit/suspension anomalies
data quality
```

---

# 24. Priority Bucket

contract_id=PRIORITY_V1。stock emergence=HIGH(delta3>=10)、MEDIUM(delta3>=3)、LOW；structure=HIGH(COMPRESSING_STRONG)、MEDIUM(COMPRESSING或BULL_TRANSITION)、LOW。risk使用core_extension_risk。
顺序A：emergence HIGH AND structure HIGH AND risk LOW；B：emergence HIGH AND structure>=MEDIUM AND risk<=MEDIUM；C：emergence MEDIUM AND structure HIGH AND risk LOW；D：其余eligible。排序键缺失放该桶末尾并显示UNKNOWN，不改变资格。
确认股票的桶：A=confirmed_raw且risk LOW且structure HIGH；B=confirmed_raw且risk<=MEDIUM；C=confirmed_raw且risk HIGH；D=其他可展示已确认对象。risk EXTREME/hard damage 是否final eligible由§31决定，不允许用桶覆盖硬门。

---

排序枚举显式序：risk LOW<MEDIUM<HIGH<EXTREME；emergence/structure LOW<MEDIUM<HIGH；bucket A<B<C<D。排序方向按§60，不按字符串字典序。UNKNOWN单列末位，不等于最低风险。

# 25. Staleness

保存prewatch_age_sessions、last_positive_change_date、days_since_emergence_improvement、waiting_condition_progress，市场日龄与可评估会话龄分开。PRIORITY_V1排序在同等emergence/structure等键后把staleness较低者前置，不另行暗改资格或桶。到期只按§32，原始T0结果永不删除。

---

# 26. Event Priority 与 Radar Priority 分离

首页：

```text
NEW
UPGRADED
DOWNGRADED
INVALIDATED
```

优先。

Radar：

```text
A/B/C/D priority
```

优先。

因此：

```text
NEW != automatic rank #1
```

---

# 27. Market Regime 四轴

contract_id=MARKET_REGIME_V1。趋势使用§49A市场参考日路径，trend_axis=STRONG(指数C>MA20且MA20比5日前上升)、WEAK(反向)、NEUTRAL；不足UNKNOWN。
breadth_axis按全市场共同成员breadth_delta3：>0.05 IMPROVING、<−0.05 DETERIORATING、其余STABLE。participation_axis按全市场成员amount_ratio20中位数：>=1.2 EXPANDING、<0.8 THIN、其余NORMAL。
stress_level以有效limit规则覆盖>=0.8为前提，down_limit_count/evaluable_count>=0.05 HIGH、>=0.01 ELEVATED、否则LOW；不可用UNKNOWN。stress_change按同成员比率日差：>0 RISING、<0 DECLINING、=0 STABLE，未知UNKNOWN。

# 28. Regime UI Mapping

first-true：必需轴UNKNOWN→UNKNOWN；trend WEAK且stress HIGH→CAPITULATION；trend WEAK且breadth IMPROVING且stress_change DECLINING→RECOVERY_ATTEMPT；trend STRONG且breadth非DETERIORATING且stress LOW→RISK_ON；trend WEAK或stress HIGH→RISK_OFF；其余NEUTRAL。
映射候选连续2个可评估市场会话才切标签，CAPITULATION立即；数据缺失显示UNKNOWN及last_known，不把旧标签说成当日判断。该映射只解释，不切换资格参数。

---

# 29. Regime 不改变第一版硬资格

第一版 Market Regime 只影响：

```text
priority
context
statistics stratification
```

不切换不同 eligibility 参数。

---

# 30. 多轴状态机

V4.0 把太多不同概念塞进一条生命周期。

本版 改为五轴。

---

## 30.1 Maturity Stage

```text
NONE
SEED
PREWATCH
WARM
CONFIRMED
```

---

## 30.2 Health State

```text
IMPROVING
STABLE
WEAKENING
DAMAGED
EXHAUSTED
UNKNOWN
```

`CONTRACTION / FADING`：

```text
作为板块 health subtype/tag
```

不再做成熟度阶段。

---

## 30.3 Validity State

```text
VALID
INVALIDATED
UNKNOWN
```

---

## 30.4 Tracking State

```text
ACTIVE
FOLLOWUP
CLOSED
```

---

## 30.5 Scenario

股票：

```text
SETUP
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
NONE
```

板块：

```text
BASE_BUILD
BREADTH_BUILD
RECOVERY_BUILD
BROADENING
REACCELERATING
SUSTAINED
NONE
```

---

# 31. Final State Reducer

contract_id=RESEARCH_STATE_V1。每轴单值，D0/D1 detector先完成，D2才执行。保留raw资格、最终资格、transition reasons及known/unknown predicates。

1. 模型边界先选择合法前态/lineage，边界事件独立记录，不和健康竞争。
2. 旧研究episode冻结invalidation_AST或core_price_damage为TRUE：health=DAMAGED、validity=INVALIDATED、final_eligibility=FALSE、maturity=NONE、tracking=FOLLOWUP；同日其他确认不能覆盖。
3. 无硬失效，必需事实UNKNOWN：保留last_known maturity并标state_freshness=STALE，validity=UNKNOWN、health=UNKNOWN、final_eligibility=UNKNOWN；不新增enrollment/退出，不将旧值算今日eligible。
4. 都可评估：validity=VALID；按CONFIRMED>WARM>PREWATCH>SEED>NONE选raw最高阶段。确认用D0，WARM用已冻结legacy，PREWATCH用C；股票V1不额外发明WARM检测器，无对应股票WARM合同则该分支NOT_APPLICABLE，板块仍有WARM。
5. 升级当日生效；下降候选需连续2个可评估市场会话（中间缺失/停牌打断连续计数，不当FALSE），期间保留阶段但final_eligibility按今天是否仍满足至少一条合法资格。第二日降到候选阶段；NONE则退出到FOLLOWUP。
6. health按DAMAGED已优先处理；否则risk=EXTREME→EXHAUSTED；delta3<−3→WEAKENING；delta3>3→IMPROVING；其余STABLE（sector使用dq5）。没有必要历史为UNKNOWN。
7. 无episode且NONE→tracking=CLOSED；有活动资格→ACTIVE；退出→FOLLOWUP；所有冻结outcome/follow-up到期工作完成后CLOSED。

hard invalidation只作用其关联研究episode的冻结invalid_if，不把任意旧Anchor broken当整股永久失效。invalidation_AST来自创建时证据合同，不能随之后挑Anchor改变。一个坏Anchor和另一个有效Anchor分别展示，不能自动清除反证。

# 32. Expiry

SEED/PREWATCH连续10个可评估会话未有阶段升级且delta3/dq5未提高>=3个百分点则EXPIRED，maturity=NONE、tracking=FOLLOWUP。改善计时以最后一次达到门槛的冻结值为参照，不能每日重置掩盖停滞。UNKNOWN/停牌不增expiry计数；额外显示market_age避免僵尸隐藏。支持/确认episode不适用此expiry。

# 33. Reentry

正式退出后次一市场会话及以后重新满足资格才new episode，parent_episode_id指旧episode。退出当天不新建，stage间升级/下降不新建；MODEL_BOUNDARY不是REENTERED。旧episode继续独立follow-up和outcome，实体投影显示活动episode优先。唯一键包含episode_id，不以实体合并旧工作。

---

# 34. V3 POTENTIAL / CURRENT / V3.3 迁移

## 34.1 V3 POTENTIAL

改语义：

```text
WARM
```

不是 PREWATCH。

---

## 34.2 V3 CURRENT

改语义：

```text
CONFIRMED_SECTOR
```

---

## 34.3 V3.3

保留：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

作为 Confirmation detector facts，输入时点依 §13A，最终事件在D2之后生成。

LEGACY_ADAPTER_V1：V4-00A提取基线每条保留函数的路径/符号/源码hash、调用图、参数、输入单位/时间、输出与UNKNOWN语义，按首次消费者阶段（sector V4-08、stock confirmation V4-11）生成精确AST与黄金向量。当前源码不是未来变量；一经提取绑定model_contract_id。若发现内部读取Final State、Focus或在线补充，拆成纯函数或保持diagnostic，不能直接入正式D0。未提取模块只阻断其场景，不阻断F0/Core。

---

## 34.4 SETUP_WATCH

不进入确认候选。

转为：

```text
Seed / PREWATCH evidence provider
```

但不能直接把几百个 SETUP_WATCH 全量展示。

---


# 34A. V3.3 Confirmation Event Compression

## 34A.1 原问题

V3.3 可以每天产生大量仍然满足确认条件的对象。

如果页面直接显示：

```text
所有 V3.3 eligible
```

就会重新变成：

> 已经确认的强势股排行榜。

因此 V4.2 将 V3.3 产品语义从：

```text
TODAY CANDIDATE LIST
```

改为：

```text
CONFIRMATION EVENT ENGINE
```

---

## 34A.2 底层结果不丢

所有符合：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

的股票仍完整写入底层结果。

但页面压缩。

---

## 34A.3 Security-Level Dedup

每个 (publication_id,security_id) 只能有一个 canonical result row；同日不同revision分别保留。

字段：

```text
primary_scenario
matched_scenarios[]
scenario_evidence[]
```

如果多场景同时命中，第一版 primary scenario 使用 §34 extraction manifest 冻结的V3.3场景优先级；所有次场景保留，不重复显示股票。

---

## 34A.4 Multi-Sector Dedup

同一股票属于多个概念：

```text
首页只出现一次
```

展示：

```text
algorithmic_support_sector
also_in_sectors[]
```

---

## 34A.5 Event Classification

contract_id=STATE_EVENT_V1。仅对D2和冻结prior_session_state_head做diff；first-true：有效前态缺失→FIRST_OBSERVED；关联旧episode本日硬失效→CONFIRMATION_INVALIDATED；本日确认且该episode或其明确关联的parent_episode曾确认、上一可见状态已弱化/退出→RECONFIRMED；本日确认且前态未确认→NEW_CONFIRMED；持续确认且primary_scenario按冻结优先表更高→SCENARIO_UPGRADED；旧确认而health/资格变弱→CONFIRMATION_WEAKENED；均确认且无变化→PERSISTENT_CONFIRMED；其余NONE。

scenario变化非升级时单独SCENARIO_CHANGED，不伪称更强。成熟度与health不得互相比较枚举。多事件分别保留，primary_event按上述序，仅用于展示，不能删除其他轴的反证。每(publication_id,entity_type,entity_id,event_type)唯一。

---

## 34A.6 首页展示规则

“今日新确认 / 确认变化”改名：

> **今日新确认 / 确认变化**

首页只展示：

```text
NEW_CONFIRMED
SCENARIO_UPGRADED
RECONFIRMED
重要 CONFIRMATION_WEAKENED / INVALIDATED
```

`PERSISTENT_CONFIRMED` 折叠到完整 Confirmed 列表和 Focus。

---

## 34A.7 SETUP_WATCH 压缩

几百个 `SETUP_WATCH`：

```text
不进入今日确认
```

路径：

```text
SETUP_WATCH evidence
→ Stock Base Seed
→ Stock PREWATCH Rule Path
→ Priority Bucket
→ 少量用户可见 PREWATCH
```

---

## 34A.8 Display Cap

独立股票首页：

```text
hard cap = 30
```

正常目标：

```text
10–20
```

如果底层：

```text
eligible = 73
```

页面必须显示：

```text
底层符合 73 / 首页展示 20
```

而不是假装算法只产生 20。

---

## 34A.9 板块内股票

不设置“每板块必须固定 3 只”这种算法规则。

板块详情页：

```text
展示所有属于该板块、达到对应 Research State 的成员
```

板块首页卡片为了信息密度可以只预览：

```text
3–5 个重点成员
```

但应有：

```text
查看全部成员
```

---

## 34A.10 Priority

确认对象复用唯一PRIORITY_V1的确认分桶和稳定排序。不得在此重新维护另一套优先级或参数。

---

## 34A.2A Confirmation Event 的状态前驱

事件比较固定使用：

```text
prior_session_state_head
```

不是：

```text
same_day_revision_parent
```

同日 r1/r2/r3 只要相对上一交易日仍是首次确认，都保持：

```text
NEW_CONFIRMED
```

Revision diff 可以记录证据变化，但不得把当天事件从 NEW 变成 PERSISTENT。

---

# 35. Shadow V2 迁移

保留 detector：

```text
STEADY
PULLBACK
BREAKOUT_PREP
LEADER
EARLY_MOVER
```

转为：

```text
Evidence Provider
```

退役：

```text
CORE_RESEARCH
SUPPORTED_RESEARCH
```

作为一级产品资格。

---

# 36. Canonical Research Radar

新增：

```text
research_radar_daily
```

类型：

```text
SECTOR_PREWATCH
SECTOR_WARM
SECTOR_CONFIRMED
STOCK_PREWATCH
STOCK_CONFIRMED
RISK_CHANGE
NEAR_MISS
```

---

## 36.1 必须同时保存

```text
eligibility_state
eligibility_rank

priority_bucket
priority_rank

display_rank

focus_activation_state
focus_activation_reason
```

资格、排序、展示、Focus 激活彻底分离。

---

# 37. Near-Miss：AST 失败谓词

contract_id=NEAR_MISS_V1。先按正常Hard Safety求值，硬失败对象只展示风险解释，不排入“差一点可入选”。对S1/S2完全可评估路径，distance=(FALSE叶谓词个数, 按固定predicate_id顺序的单位归一化shortfall向量)，词典序比较，不把不同单位相加。
连续谓词shortfall=max(0,threshold−value)/scale（方向相反则反向），scale由参数合同冻结且>0；离散FALSE为1，TRUE为0。取路径最小词典序距离；所有路径含UNKNOWN则distance=NULL、UNRESOLVED，不把未知当0。页面列具体未满足/未知谓词，不能将Near-Miss当收益分数。

---

# 38. Near-Miss 产品边界

```text
radar_type = NEAR_MISS
```

默认：

```text
折叠
```

不进入：

```text
Focus
首页第一屏
正式 PREWATCH 数量
```

---

# 39. “Why Now” 成为核心字段

每个 Radar 对象必须有：

```text
why_now
```

它不是自然语言随便总结。

数据结构：

```text
previous_stage
current_stage
changed_facts[]
changed_domains[]
newly_satisfied_rules[]
new_risk_flags[]
```

UI 示例：

```text
昨日：SEED
今日：PREWATCH

今天变化：
RPS5 Δ3 +11pct
压缩进入有效区
板块 emergence 从 LOW → MEDIUM
extension 仍低
```

---

# 40. Conflict Panel

每个对象同时显示：

```text
supporting_evidence[]
opposing_evidence[]
unknown_evidence[]
```

禁止页面只解释：

> 为什么它好。

---

# 41. Hypothesis Contract

Hypothesis 不是资格算法。

结构：

```text
hypothesis_id
statement
evidence_for[]
evidence_against[]
next_discriminator[]
expiry_condition[]
quality
```

例：

```text
H1:
主动相对需求正在增强

For:
RPS加速
板块种子扩散

Against:
成交参与度尚未增加

Discriminator:
未来2日突破位是否被接受
```

竞争 H：

```text
H2:
当前主要体现防御性抗跌，
尚未形成持续方向需求
```

必须由 facts 支撑。

---


# 41A. Structure Event Engine


# 41A0. Anchor Price Coordinate / Re-Anchor Contract

冻结 Anchor 是冻结历史事实和原始坐标，不是把旧复权价格数字永远直接拿来与未来价格比较。

Anchor 必须保存：

```text
anchor_id
security_id
anchor_trade_date

anchor_raw_lower
anchor_raw_upper
anchor_price_basis

adjustment_contract_id
adjustment_source_identity
adjustment_asof
anchor_basis_trade_date

frozen_transform_coefficients
source_event_id
source_fact_digest
```

原始 Anchor 永不回写。

观察日 `t` 比较时生成：

```text
anchor_view_asof_t
```

抽象：

```text
P_view(t)
=
alpha(anchor_basis → observation_basis, t) * P_anchor
+
beta(anchor_basis → observation_basis, t)
```

具体 QFQ 转换由 Historical Adjustment Contract 冻结。

以下必须同一 price basis：

```text
anchor
current price
ATR
return
breach depth
support zone
```

禁止：

```text
旧 QFQ anchor number
直接比较
新复权基准 current price
```

公司行为后只生成新观察坐标视图，不回写旧 Anchor。

如果无法建立确定转换：

```text
support_state = UNKNOWN
reason = PRICE_BASIS_MISMATCH
```

验收必须覆盖：

```text
现金分红
送转
配股
同日 revision
跨公司行为 support test
```

并核对独立预期值。

现有 Focus `price_path` / re-anchor 只能作为可复用参考，不能自动视为 V4 Structure Engine 已继承完成。

---

## 41A.1 为什么 Daily Profile 还不够

“今天靠近 MA20”不是完整结构。

要判断：

```text
突破
回踩
中阳支撑
平台支撑
恢复
```

必须保存跨日事件与 Anchor。

因此高级阶段新增：

```text
stock_structure_events
stock_structure_anchors
stock_structure_event_transitions
```

---

## 41A.2 Anchor Type 与选择

contract_id=STRUCTURE_EVENT_V1。V1支持PRIOR_HIGH/BREAKOUT_LEVEL、RANGE_UPPER、BULLISH_IMPULSE_BODY/LOW、MA20_DYNAMIC/MA60_DYNAMIC、PIVOT_LOW、GAP_ZONE；每类须有明确来源事件，不能看图事后随意画线。
PRIOR_HIGH=此前20日最高价；RANGE_UPPER仅当此前20日range/ATR<=4且slope20绝对值<=0.1，取此前20日高；impulse按§41B；dynamic MA来源于此前注册的上涨事件，其公式冻结，每观察日生成新值不改旧值。
PIVOT_LOW采用左右各2日低点确认，最早在pivot_date+2实际可评估会话才能注册，available_date为确认日不能倒填；GAP_ZONE需L[t]>H[t-1]，区间[H[t-1],L[t]]，注册日不能参与回测支撑。

## 41A.3 Anchor 冻结

固定Anchor原坐标及事件不回写；每日换基视图按§41A0。动态MA不得伪称固定支撑价。每个Anchor分别跟踪；active_anchor按是否未失效、与C距离/ATR升序、anchor_date降序、anchor_id升序选择供页面展示；研究episode invalid_if使用创建时绑定的Anchor，不能随active_anchor切换。
平台/前高基于历史复权坐标建立时，使用逆仿射变换存anchor_basis_trade_date raw坐标，并保存原变换摘要；不是把历史最高raw直接用于当前坐标。

---

# 41B. Bullish Impulse

contract_id=STRUCTURE_EVENT_V1。body=C-O，body_atr=body/ATR20[t-1]，range_atr=(H-L)/ATR20[t-1]；昨日ATR换到当前价格坐标后计算，避免今日大振幅抬高自身阈值。CLV按§10A0。
core_bullish_impulse=(body_atr>=1 AND range_atr>=1 AND CLV>=0.7 AND amount_ratio20>=1.2 AND rel_market_1>0)。数据不足UNKNOWN，一字板CLV未知不能靠该分支确认。turnover只能生成独立补充说明。
记录open/body_mid/close/low/high；BODY区间[O,(O+C)/2]，LOW区间[L,L]，最早次日开始测试。价格区间只是研究Anchor，不映射买点。所有新增阈值写入§72候选参数实例。

---

# 41C. Support / Acceptance 状态机

contract_id=SUPPORT_STATE_V1。只评估t-1已存在Anchor；新Anchor今日IDLE。缺失actual bar/换基/ATR为UNKNOWN观察，保留旧状态与stale标记，不虚构退出。

定义zone=[lo,hi]（观察日同基准）、atr=ATR20[t-1]换基值>0；touch=(L<=hi+0.25*atr AND H>=lo−0.25*atr)；close_breach=C<lo−0.5*atr；deep_breach=C<lo−1.5*atr；eod_reclaim=touch AND C>=hi AND CLV>=0.5。只用日线，不推断日内先后/速度。

状态与计数按序：
1. 已终止INVALIDATED/BROKEN不复活，恢复须新事件。
2. deep_breach或close_breach连续2可评估市场日→BROKEN，关联invalidation AST可当日使研究episode INVALIDATED；不等待未来回收来回写今天。
3. close_breach首次→BREACHED_SHALLOW（描述待确认，名称不保证盘中浅穿）。
4. eod_reclaim且之前已完成首次测试、至少隔1个完全离开测试带的实际会话后再次touch→HELD_CONFIRMED，test_count+1。
5. eod_reclaim且此前TESTING/BREACHED_SHALLOW→RECLAIMED；首次touch并eod_reclaim→RECLAIMED（仅EOD事实，test_count=1）。
6. 之前RECLAIMED且后续至少1实际会话C>=hi、无close_breach→HELD_TENTATIVE。
7. 之前HELD_TENTATIVE/HELD_CONFIRMED再次touch但未reclaim→RETESTING。
8. touch→TESTING；否则距离区间<=1*atr→APPROACHING；其余保持有效前态或IDLE。

每个分支保存触发事实；缺失会话打断连续close_breach计数，不当作恢复。冻结的硬invalid_if可严于该支撑状态，需显式记录两者含义。输出INVALIDATED是终止行政状态，BROKEN是价格路径状态，不能任意互换。

# 41D. Acceptance / Retention

contract_id=RETENTION_V1。impulse_retention_k=(C[t0+k]-base)/(C[t0]-base)，k=1/3，全部换到同一观察基准；分母<=0或未知则NOT_APPLICABLE/UNKNOWN，禁止epsilon伪造。仅在目标市场日到来且证据可用时新增observation，不能更新t0事实。数值可>1或<0，展示原值不伪装概率。
acceptance_state=UNKNOWN(必需数据缺失)、BROKEN(已硬失效)、PENDING(事件后尚无2个可评估会话)、ACCEPTED(后2个连续会话C>=anchor_upper)、NOT_ACCEPTED(其余可评估)。support retest与breakout acceptance不同，不能用一次上涨等价支撑确认。
板块retention按§15固定集合，Rotation价格路径按§21A，不能调用当日stock最终状态回灌B。

---

# 41E. Structure Event 与 Rotation 的联动

案例：

```text
股票支撑初步守住
+ 所属板块 ROTATION_ACCEPTED / EXPANDING
```

Context 增强。

但：

```text
板块强
≠ 股票自身结构有效。
```

反过来：

```text
股票 HELD_CONFIRMED
但板块 ROTATION_OUT
```

页面必须同时显示个股结构与不利 Context，而不是隐藏冲突。

---

# 41F. Profile 分阶段

Core字段在V4-04，Turnover在V4-06，Structure/Anchor/Support在V4-12，Context/Structure投影在V4-13，Why Now在V4-15。API在Core阶段允许组件NOT_IMPLEMENTED；完整产品验收才要求已承诺的后置组件就绪。字段登记只用§87A，禁止另列“第一阶段必须全部高级状态”。

---

# 41G. 解释、展示和独立证据

HYPOTHESIS_V1：模板必须绑定可验证predicate_id、支持/反对/UNKNOWN证据及下一判别/过期AST。证据不足不强造第二个解释，标HYPOTHESIS_SET_INCOMPLETE。价格衍生的多个Domain不是统计独立观测；不能按Domain数或解释数量累加“把握”。Supplemental解释包含自身revision，不混入Core why_now。

DISPLAY_V1：先从完整qualified ledger生成全部事件，事件改变检测以冻结前態为准。首页只展示非PERSISTENT有实质事件的对象；市场卡与数据等待说明不受“仅变化对象”限制。先按风险失效、确认/升级、新PREWATCH、其他变化排序，再各自PRIORITY_V1 tuple、stable entity_id。跨行业/概念合并板块池，最多15；独立股票最多30，允许0，正常5–10/10–20只是预期负荷而非下限。
股票全首页去重，已在板块卡展示者独立列表不重复计入负荷；板块卡最多5个变化成员，详情完整分页。风险退出即使final_eligibility=FALSE仍进入RISK_CHANGE事件流，不能被eligible-only排序删除。eligible_count、changed_count、displayed_count分别显示。
sector_overlap_jaccard=|M_a∩M_b|/|M_a∪M_b|，空并集NA；J>=0.8建立边，按稳定id连通分量生成展示cluster_id，明确传递聚类不保证所有两两J>=0.8。聚类仅去重展示，不合并计算资格；各板块统计仍独立。

---

# 42. Focus Tracker：不重写成熟底座

必须保留：

- Episode；
- Segment；
- Anchor；
- Transition；
- Observation；
- Outcome；
- revision；
- ordered replay；
- accepted head；
- PIT RPS；
- invalidation frozen facts；
- Path State V2；
- fail closed。

本版 只改变：

> 上游 canonical source。

---

# 43. 新 Focus Source Family

建议：

```text
V4_STOCK_RESEARCH
V4_SECTOR_RESEARCH
```

同一个股票（未正式退出、无模型边界时）：

```text
maturity: PREWATCH → CONFIRMED（有独立股票WARM合同后才有WARM）
health: STABLE → WEAKENING
```

仍是：

```text
同一个 episode
```

---

# 44. Focus 不再承担模型完整验证样本

Focus 的用途：

```text
用户要持续看的对象
```

可以有：

```text
display cap
manual pin
user priority
```

因此：

> 不能拿 Focus 样本代表全算法样本。

---

# 45. 独立 Validation Cohort

contract_id=COHORT_V1。对STOCK/SECTOR全部final eligible PREWATCH/WARM/CONFIRMED写daily ledger，与展示/Focus/pin无关。股票无WARM检测器时NOT_APPLICABLE，不能造样本；SEED仅诊断。Near-Miss按§49选作对照。

# 45A. 日账本、统计事件和修订

daily ledger唯一键(model_contract_id,state_lineage_id,publication_id,entity_type,entity_id,signal_type)。统计逻辑事件键(model_contract_id,state_lineage_id,entity_type,entity_id,episode_id,event_type,event_trade_date)，只对FIRST_PREWATCH、REENTRY_PREWATCH、UPGRADE_TO_WARM、NEW_CONFIRMED、REACCELERATION_EVENT、INVALIDATION产生事件；Persistent不新建。
事件observation唯一键(logical_event_id,publication_id)，含ASSERTED/RETRACTED/CORRECTED。enrollment_id第一次实时ASSERTED冻结T0、reference、source、parameters、benchmark、controls和publication。后续修订只追加并标source_correction，不能重抽原对照、删原样本或重置T0；重算样本独立CORRECTED cohort。原始观察和当前修订投影分别展示。
报告分列daily rows、logical events、episodes、unique entities、unique dates，股票和板块分开，重叠episode/日期相关性不得当独立样本。

# 46. Forward Outcomes

V4-15必须交付enrollment、日历due planner、价格path、benchmarks、control settlement、outcome revisions与readback。V4-16开始每日结算；V4-21只是继续累计。任何Focus/UI筛选不限制结算。
唯一键(enrollment_id,horizon,outcome_contract_id,evaluation_source_digest)。同源重复执行幂等；更正源追加evaluation revision，first_observed和latest_corrected分开，不写回信号。

# 46A. Horizon 与公式

contract_id=FORWARD_PRICE_PATH_V1。N=1/3/5/10/20，按冻结市场日历推进。T0为盘后信号收盘，不是可成交策略回报。evaluation_basis_date=T+N；将T0和后续OHLC全部用同一已验证local affine adjustment source换到该日坐标。冻结signal的原始reference不变，另存comparison_reference、换基系数/digest/asof。不能拿不同daily QFQ快照直接相除。

P_j为同基准收盘，j=0..N；未来高低点只取1..N：

```text
R_N = P_N/P_0 - 1
MFE_N = max(0, max_{1<=j<=N}(High_j/P_0-1))
MAE_N = min(0, min_{1<=j<=N}(Low_j/P_0-1))
D_j = P_j/max(P_0,...,P_j)-1
PATH_MDD_CLOSE_N = min(D_0,...,D_N)
```

MFE>=0、MAE/MDD<=0；不把T0日内高低点算作未来。缺失实际会话不合成bar；确认停牌可从极值路径省略但披露actual_count，未确认缺口使路径指标MATURED_DATA_MISSING。终点停牌R_N不可用，不挪到复牌日。另存tradable-session诊断，不替代N日结果。
反例验收：[100,110,120] MDD=0；[100,80,90] MDD=−0.2；[100,120,90] MDD=−0.25；N=1、平盘、除权、缺口都必须有独立预期。

# 47. 到期与截尾

未到期存PENDING；报告截止日未完成的time-to-event观察标RIGHT_CENSORED。已到期按OBSERVED/SUSPENDED_AT_HORIZON/MATURED_DATA_MISSING/DELISTED_BEFORE_HORIZON分开，禁止全当右截尾或失败。退市无可验证终值不填−100%或0；披露不可观察比例，不从完整案例结果推出全样本效果。confirmed suspension的中间缺口与未知缺口分列。

# 48. Competing Outcomes

对每个PREWATCH episode记录首个CONFIRMED/INVALIDATED/EXPIRED的market-date时间；同日按state reducer的硬失效优先级。RIGHT_CENSORED是观察状态，不是竞争事件。转化后仍继续N日外部价格路径；不能因失败/确认而停止结算选择样本。完整报告分事件类型、日期和source quality，不只报conversion%。

# 49. Controls

Control A=冻结同日Legacy模型全部符合对象；无真实Legacy当日输出不能事后冒充observed control。Control B=同Hard Safety下delta3 Top-N，N为同日该股票signal类型事件数；稳定id打破展示同分，资格同分保留原值。Control C见§49B。三个对照分别报告，不合成最佳对照。

# 49A. Benchmark Contract

contract_id=MARKET_BENCHMARK_V1。Core历史市场参考retN：在起点t-N已符合Universe、按各因子窗口可评估股票的等权endpoint return均值，保存起点Universe/可观察集合/coverage；缺失超过20% UNKNOWN，不能只凭现在存活证券补池。市场趋势路径为连续这些ret1链乘，标daily-rebalanced research index，非交易所指数，不与单一股票收益混名。

Forward市场基准：T0冻结可评估Research Universe，等权固定份额，每股收益按同基准换算，B_j=sum(w_i*(P_i,j/P_i,0))。不因后来变强/退市重选或再归一化剩余成员。完整endpoints才正式OBSERVED；成员终点缺失则benchmark UNKNOWN并披露范围，不能使股票absolute_return失效。
Sector基准同式，T0按§20确定sector，冻结成员和等权份额；对stock relative_sector排除目标股票，n<2不提供；SECTOR signal直接使用自身冻结篮子。identity含member/weight/source/adjustment digest。
relative_market_return=stock_R−market_B_return；relative_sector_return同理。sector endpoint/path以同一固定篮子计算；日线无法知道成员盘中极值是否同步，故SECTOR的MFE/MAE采用close-only并独立命名MFE_CLOSE/MAE_CLOSE，不能把成员high求和冒充板块intraday高点。板块和股票outcome分开统计。

# 49B. Matched Controls 与分析

contract_id=CONTROL_ASSIGNMENT_V1。T0符合相同Hard Safety、非当日PREWATCH final eligible且非本事件实体为池；优先同primary industry（必须T0可知），缺行业允许全市场并标MATCH_SCOPE_MARKET。距离为prior20 mean amount的log值、vol20、RPS20各自同日百分位差绝对值之和，固定顺序tie-break security_id。每signal最多3个最近对照，允许不同signal复用；不足保存实际数量，不用未来补选。冻结features/assignment digest。
后来对照入选只追加crossed_signal_at，ITT主分析保留。CLEAN_CONTROL只作为明确标识的事后敏感性子集，禁止用于主要增量结论或切换门；不得因“剔除了未来入选者”宣称因果优势。按security、signal_date、sector重叠分层披露；无预注册相关性处理时只提供描述统计，不给概率/显著性保证。

---

# 50. Forward 不是“收益优化器”

本项目不转向：

```text
不断挖因子
不断看 p-value
自动调参
```

统计只用于：

```text
发现明显无效
发现样本偏差
判断增量信息
约束过拟合
```

若同时测试很多参数版本：

```text
必须冻结 cohort
不得 cherry-pick 最好看的那个
```

必要时再使用：

```text
block bootstrap
clustered intervals
multiple-comparison adjustment
```

作为 PRO 级验证，而不是把系统变成量化竞赛。

---

# 51. 验收状态分层

不能再把：

```text
代码完成
```

和：

```text
算法有效
```

放一个 PASS。

## Stage A

```text
ENGINEERING_COMPLETE
```

表示：

- schema；
- DAG；
- replay；
- state；
- API；
- deterministic；
- no temporal leakage。

## Stage B

```text
SHADOW_STABLE
```

表示：

- 连续真实运行；
- no duplicate episode；
- no state flapping anomaly；
- no publication mixing；
- runtime acceptable。

## Stage C

```text
PROVISIONAL_FORWARD_EVIDENCE
```

表示：

- 已有完整 outcome；
- controls 可比较；
- 多 signal dates；
- 数据质量足够。

## Stage D

```text
FORWARD_SUPPORTED
```

表示：

- 不同市场环境都有样本；
- 结果不是一个板块/一个行情阶段驱动；
- PREWATCH 相对基线显示稳定增量研究价值。

不使用：

```text
FINAL_PROVEN_ALPHA
```

这样的表述。

---

# 52. 20–60 交易日的正确定位

```text
20 日
```

可作为：

```text
SHADOW_STABLE
```

的最低工程观察窗之一。

不能作为：

```text
算法有效证明。
```

最终 Forward Supported 不只看日期数量，还看：

```text
complete cohort count
signal date diversity
sector diversity
regime diversity
right censoring
control comparability
```

---


# 51A. Evidence 与执行方式

统一使用§4.6枚举：PIT_OBSERVED+SHADOW可进入真实Shadow cohort；RECONSTRUCTED_ASOF+REPLAY不可冒充观察。

## 51A.1 观察起点与防事后重跑选样

V4-00C冻结每日scheduled cutoff和观察发布deadline（Asia/Shanghai且存UTC时间），daily_observation_slot=(model_contract_id,state_lineage_id,trade_date)。只有该slot的第一次合规accepted可创建真实enrollment；deadline之后补跑或更换参数属于reconstruction，不允许择优标PIT_OBSERVED。延期/源不可得则记录MISSED_OBSERVATION_SLOT，不悄悄重置日期。已有实时结果的同日修订仍存observations，但不能新增第二套原始样本。
source/provider_available、system_available、computed_at、accepted_at、observation_deadline分别记录；“同一trade_date”不等于“当时已知”。切换门使用完整slot日志、P0日志和model identity，禁止只挑通过的20天。

# 52A. 切换政策 CUTOVER_V1

只要求工程稳定加最低真实观察，不要求已证明长期优势：
SHADOW_STABLE_PASS=同一model_contract_id连续20个市场会话按期accepted，0时序泄漏/duplicate episode corruption/Core identity/P0 state violation，rollback drill通过。漏日/不可评估核心会话不计连续；P0或模型/参数变更重置窗口。
PROVISIONAL_FORWARD_GATE=至少5个不同signal_date、30个不同股票正向入选事件（FIRST/REENTRY_PREWATCH/NEW_CONFIRMED）的T5 OBSERVED结果，同一模型，settlement无P0、controls/benchmark覆盖回执已披露。不能用INVALIDATION或同日revision凑30；样本不足延长观察，不降低资格。
Focus/UI切换=上述两门 AND MIGRATION_REPLAY_PASS；切换后证据标PROVISIONAL。无明确优势不等于严重退化，不自动阻断。严重退化定义为合同/数据正确性失败、未解释的系统性状态异常或超出事前冻结运行预算，不以后验收益挑阈值。

# 52B. Gate Capability Matrix

每道Gate回执=(status FULL_PASS/DEGRADED_PASS/BLOCKED, capability_scope, affected_dates/entities/fields, reasons, evidence)。兼容DATA_FACTOR_REPLAY_PASS等别名只表示FULL或明确scope内DEGRADED成功，不能丢scope。

| 条件 | 允许能力 | 禁止能力 |
|---|---|---|
| 当前TDX/adjustment通过，历史不全 | 当前Core、完整窗口内算法、当日起Forward | 缺证据历史adjusted输出 |
| 历史Universe只有current replay | 诊断历史、独立通过的当前链 | 正式历史横截面效果 |
| 历史membership非PIT | 历史price-only、当日起真实成员 | 正式历史sector效果 |
| turnover失败/不足 | 全部Pure-Core | 对应turnover结果 |
| AS-OF周期失败 | 无周期依赖的独立能力 | affected周期/信号 |
| adjustment identity mismatch | verified raw事实 | affected adjusted指标/Forward |
| Amount A审计OPEN | stock Core、采用命名明确proxy的独立sector路径 | 依赖未验收Amount A的正式路径 |
| actual temporal leakage | 保留旧accepted | affected新publication |

多个问题取能力集合交集而不是后行覆盖前行。DEGRADED不是允许UNKNOWN硬门通过。BaoStock可选任务失败或等待，调度器可继续Core；历史补齐不作为当前独立能力的全局门。核心必需字段未知即该信号UNKNOWN；不能用capability矩阵静默降低规则。

---

# 53. 三道 Replay Gate

## Replay Gate A — Data / Factor

位置：

```text
Canonical Facts
+ Factors
+ Core Daily Profile
完成后
```

验证：

```text
TDX source identity
historical universe
adjustment reproducibility
Daily deterministic
Weekly/Monthly AS-OF
factor max_source_trade_date
Core Profile deterministic
revision idempotency
```

通过：

```text
DATA_FACTOR_REPLAY_PASS
```

## Replay Gate B — Algorithm / State

位置：

```text
Seed
Sector Emergence
Rotation
PREWATCH
State
Confirmation Compression
Support / Acceptance
完成后
```

验证：

```text
same-day feedback forbidden
state transition legality
hysteresis
expiry
direct PREWATCH→CONFIRMED
rotation pulse→accepted/failed
support test→reclaim→retest/break
confirmation persistent suppression
multi-sector dedup
unknown propagation
no duplicate event/episode
```

通过：

```text
ALGORITHM_STATE_REPLAY_PASS
```

## Replay Gate C — Migration

位置：

```text
Shadow Stable + Provisional Forward Gate
之后
Focus Cutover 之前
```

验证：

```text
SOURCE_MODEL_BOUNDARY
old source → V4 mapping
episode continuity
no fake reentry
read API projection
rollback
same-day revision behavior
namespace isolation
```

通过：

```text
MIGRATION_REPLAY_PASS
```

历史效果 replay 只有在 price/universe/membership/source identity 均能证明 PIT 时才可提高证据等级；否则只能 diagnostic。

---

# 54. Temporal Leakage Test

必须自动证明：

T0 输出中：

```text
不存在：
T+1 price
未来 membership
未来 Focus outcome
未来 state
future publication
```

所有 factor/provider 都带：

```text
max_source_trade_date
```

并要求：

```text
max_source_trade_date <= target_trade_date
```

---


进一步强制测试：

```text
A. Weekly/Monthly AS-OF
   T0 Monday cannot read Friday
   T0 mid-month cannot read month-end

B. Historical Universe
   delisted/later-listed security cannot be included/excluded using future knowledge

C. Sector Membership
   target-date membership basis must be explicit

D. Corporate Action
   adjustment factor effective date cannot leak future action data

E. Supplemental Enrichment
   provider_asof > core cutoff cannot alter accepted core state
```

所有 factor/provider 增加：

```text
max_source_trade_date
source_asof
evidence_origin
```

---


额外必须覆盖：

```text
A. Weekly/Monthly AS-OF
   Monday cannot read Friday
   mid-month cannot read month-end

B. Historical Universe
   later delisting/listing knowledge cannot silently alter old cross-section

C. Sector Membership
   effective time 与 available time 同时满足

D. Corporate Action
   adjustment source revision 不能泄露到 AS_RECORDED

E. Supplemental Enrichment
   provider_asof > Core cutoff 不得改变 accepted Core state

F. Same-Day Revision
   r2/r3 不得把同日 NEW event 变成 PERSISTENT
```

所有相关 provider/factor 保存：

```text
max_source_trade_date
source_asof
available_at
evidence_origin
model_namespace
```

---

# 55. Deterministic Replay

同：

```text
source identity
code commit
contract
parameter set
trade_date
```

重复运行必须得到：

```text
same logical digest
```

否则：

```text
NON_DETERMINISTIC_OUTPUT
```

阻断正式发布。

---

# 56. State Flapping Test

构造临界数据：

```text
threshold ± epsilon
```

连续多日验证：

```text
hysteresis
exit hysteresis连续计数（无强制升级等待）
unknown
hard invalidation
```

确保不会：

```text
PREWATCH
WARM
PREWATCH
WARM
```

无意义频繁跳动。

---

# 57. Multi-Sector Test

一只股票属于：

```text
1 行业 + N 概念
```

必须验证：

```text
Context Domain = max 1
```

即使：

```text
5 个概念 PREWATCH
```

也不获得 5 份资格证据。

---

# 58. Cohort Completeness Test

必须证明：

```text
eligible but not displayed
```

仍进入：

```text
Validation Cohort
```

否则阻断 Forward 统计。

---

# 59. A股制度状态处理

## 59.1 涨跌停

涨停/跌停 return 是真实 OF。

不尝试“还原如果没有价格限制会涨多少”。

增加：

```text
limit_status
```

用于解释：

- RPS 同值堆积；
- 换手受交易状态影响；
- intraday acceptance 分析边界。

---

## 59.2 停牌

确认停牌不填ret=0/turnover=0，不当数据缺失；Core连续市场会话窗口遇停牌按CORE_FACTOR_V1返回不足，不跳过日期；Turnover自身历史按TURNOVER_CONTEXT_V1允许跳过确认停牌；Forward按FORWARD_PRICE_PATH_V1固定市场horizon。三者明确分开，不能共享一个无语义的rolling工具。

---

## 59.3 ST / 特殊证券

不在总方案里直接拍脑袋剔除。

由：

```text
V4_RESEARCH_UNIVERSE_V1
```

冻结。

---

# 60. Research Radar 排名

contract_id=PRIORITY_V1。完整eligible集合按STOCK_PREWATCH/STOCK_CONFIRMED/SECTOR_PREWATCH/SECTOR_WARM/SECTOR_CONFIRMED分别rank；RISK_CHANGE与NEAR_MISS独立，不要求当前eligible。
Stock键：bucket(A到D)、emergence(HIGH到LOW)、structure(HIGH到LOW)、delta3降序、risk(LOW到EXTREME)、days_since_improvement升序、prior20_amount降序、stable_id升序。Sector键：emergence、rank_velocity3降序、breadth_delta3降序、ma20_delta3降序、adjusted_seed_width降序、exhaustion升序、stable_id升序。每个键missing排该层末位且显示UNKNOWN，不改变已成立资格。
eligibility_rank即完整资格集合内此序，priority_rank同义alias不另算分；display_rank按DISPLAY_V1事件过滤/cap计算。turnover、未关闭Amount A、未来outcome与manual pin均不进这些正式键。

---

# 61. Display Diversification

Display cap 只影响 UI。

例如：

```text
per_sector_display_cap
```

不会改变：

```text
eligibility_rank
```

同一股票若关联多个板块：

```text
首页只显示一次
also_in_sectors[]
```

---

# 62. 用户负荷

本版 不追求固定“每天必须多少只”。

目标是：

```text
Net New Information Load
```

统计：

```text
new objects
upgraded objects
downgraded objects
invalidated objects
duplicates removed
```

而不是简单把：

```text
4 个页面条目数
```

全部相加。

---


# 62A. V4.2.2 页面一级导航最终合同

用户日常只看页面，因此页面是正式产品，不是算法附属。

一级导航固定为：

```text
1. 今日总览
2. 板块研究
3. 个股研究
4. 关注跟踪
5. 市场与事件
6. 数据与诊断
```

后台术语如：

```text
PASS A/B/C
BOUND_STRICT
ACTIVE_EMERGENCE
```

默认不占主页面，详情/诊断再展开。

---

# 62B. 今日总览算法与展示

## 第一屏只回答三个问题

```text
市场今天是什么环境？
今天真正出现了什么新变化？
哪些风险发生了重要变化？
```

---

## 62B.1 Market Card

数据：

```text
Trend Axis
Breadth Axis
Participation Axis
Stress Axis
```

映射：

```text
RISK_ON
NEUTRAL
RISK_OFF
CAPITULATION
RECOVERY_ATTEMPT
```

页面必须显示四轴，不只显示综合标签。

---

## 62B.2 今日轮动

只展示变化事件：

```text
ROTATION_PULSE
ROTATION_IN
ROTATION_ACCEPTED
ROTATION_EXPANDING
ROTATION_REACCELERATING
ROTATION_OUT / FAILED
```

---

## 62B.3 板块变化

候选池：

```text
INDUSTRY + THEME
```

排除：

```text
STYLE
```

正常显示：

```text
5–10
```

硬上限：

```text
15
```

如果 eligible > 15：

```text
底层符合 N / 首页展示 15
```

---

## 62B.4 独立个股变化

首页硬上限：

```text
30
```

只展示：

```text
NEW PREWATCH
UPGRADED
NEW CONFIRMED
SCENARIO UPGRADE
RECONFIRMED
IMPORTANT WEAKENED
INVALIDATED
```

不展示无变化的 PERSISTENT。

---

## 62B.5 板块内重点股票

板块卡片只预览：

```text
3–5 个高优先级变化成员
```

不是算法 cap。

进入板块详情后展示完整 eligible/member state。

---

# 62C. 板块研究页

统一行业和概念，不再分两个榜。

筛选：

```text
全部 / 行业 / 概念
PREWATCH / WARM / CONFIRMED
改善 / 稳定 / 转弱 / 高位衰减
轮动状态
```

默认字段：

```text
板块
类型
Maturity
Health
Rotation State
Why Now
RS20背景
RS5变化
宽度变化
Seed变化
Participation
Exhaustion Risk
Quality
```

点击后展示：

```text
Why Now
Factor Timeline
成员扩散
Rotation Timeline
支持证据 / 反证
Overlap
完整成员分层
PIT Replay
```

---

# 62D. 个股研究页

入口：

```text
任何股票代码 / 名称搜索
```

Research Universe中即使不在候选池也必须有Daily Profile；搜索池外证券仍显示身份/排除理由和可用Raw事实，不伪称全套研究算法已评估。

第一屏：

```text
Trend
Weekly/Monthly Context
Position
MA Structure
Relative State
Compression
Amount
Turnover
Breakout/Pullback/Recovery
Support State
Risk
Market Regime
Primary Industry
Algorithmic Support Sector
```

第二屏：

```text
Why Now
F / R / H
Waiting For
Invalid If
```

第三屏：

```text
Price Chart
关键 Anchor / Event
Daily/Weekly/Monthly structure
Factor Timeline
Sector Context
Focus Timeline
PIT Replay
```

---

# 62E. 搜索任意股票时“未入选”的解释

如果股票未进入 PREWATCH，先区分NOT_ELIGIBLE、UNKNOWN、NOT_IMPLEMENTED和NOT_IN_RESEARCH_UNIVERSE；下面只说明已完成评估且为FALSE的示例：

页面不能写：

> 不值得关注。

而要显示：

```text
PREWATCH = NOT_ELIGIBLE

已满足：
- POSITION
- STRUCTURE

未满足：
- RELATIVE_CHANGE

风险：
- extension medium
```

这样筛选器不会被误解为股票好坏判决器。

---

# 62F. 关注跟踪

首页按变化事件：

```text
NEW
UPGRADED
WEAKENED
INVALIDATED
EXITED
REENTERED
```

无变化 PERSISTENT：

```text
折叠计数
```

详情展示：

```text
完整 Episode Timeline
Anchor
Observation
Path State
Outcome
```

---

# 62G. 市场与事件

保留：

```text
指数
涨停/跌停
涨停梯队
题材/事件
市场即时统计
```

但必须明确：

```text
市场事实 / 临时事件
≠
正式 Research State
```

---

# 62H. 数据与诊断

下沉：

```text
RPS20矩阵
创新高/RPS
全市场技术扫描
V3 legacy
Shadow V2
LOO证据
Data Quality
Source Contract
Parameter Contract
```

日常不要求用户进入。


# 63. 首页 V4.2.2

第一屏只回答三个问题：

```text
1. 市场今天处于什么环境？
2. 今天最重要的新变化是什么？
3. 今天有哪些明显风险变化？
```

---

## 63.1 市场卡

```text
Trend
Breadth
Participation
Stress
```

下方显示 UI 映射：

```text
RISK_OFF / RECOVERY_ATTEMPT ...
```

---

## 63.2 今日变化

最多：

```text
Top change events
```

例如：

```text
新进入 PREWATCH
WARM → CONFIRMED
maturity=CONFIRMED，health→WEAKENING
VALID → INVALIDATED
```

---

## 63.3 第二屏

再放：

```text
Sector Radar
Stock PREWATCH
Stock Confirmed
```

---

# 64. 板块研究页

第一入口：

```text
Lifecycle + Why Now
```

不是 RPS20 矩阵。

---

## 64.1 顶部

```text
板块
Maturity
Health
Emergence
Confirmation
Exhaustion
Data Quality
```

---

## 64.2 Why Now

显示：

```text
相较昨日变了什么
```

---

## 64.3 Factor Timeline

至少：

```text
RS5
RS20
rank velocity
breadth
MA20 width
seed width
amount
```

5/10/20 日趋势。

---

## 64.4 成员扩散

```text
base seeds
PREWATCH
confirmed
entered
exited
retention
```

---

## 64.5 Overlap

显示：

```text
高重叠概念
overlap cluster
unique member share
```

---

# 65. 个股研究页

第一入口必须是：

```text
股票代码 / 名称搜索
```

不是新高榜。

---

## 65.1 第一屏

```text
Maturity
Health
Validity
Tracking
Scenario
Risk
Quality
Market Regime
Primary Industry
Algorithmic Support Sector
```

---

## 65.2 Why Now

昨天 vs 今天：

```text
stage
domain
waiting
risk
```

---

## 65.3 F 层

```text
price
MA
ATR-normalized position
RPS
relative
compression
amount
turnover
sector facts
```

---

## 65.4 R 层

只能使用观察结果语言：

```text
推进效率改善
相对抗跌
突破后接受
高参与但推进不足
回调后恢复
```

---

## 65.5 H 层

显示：

```text
竞争解释
支持证据
反证
下一判别条件
```

不输出：

```text
主力吸筹
庄家洗盘
```

这类不可验证故事。

---

# 66. PIT Replay 功能

用户可选择：

```text
2026-09-18
```

页面只显示：

> 截止那一天系统能知道什么。

禁止泄露：

```text
后续 stage
后续 outcome
后续 membership
```

这是用户训练和模型审计都非常重要的功能。

---

# 67. Compare 功能

股票研究页支持比较：

```text
今天 vs 昨天
股票 vs 市场
股票 vs T0冻结研究板块（收益基准）/ 当前LOO支持板块（当日解释），两者分开
```

板块支持：

```text
板块 vs 市场
今天 vs 3日前
PREWATCH vs WARM 历史阶段
```

---

# 68. 旧页面最终定位

```text
领先行业 / 概念
→ 中期背景

当前强势
→ Sector Confirmed

早期启动 / 结构突破观察
→ Legacy WARM diagnostic

提前观察板块
→ V4 Sector PREWATCH

当前关注个股
→ V4 Active / Confirmed Focus

提前观察个股
→ V4 Stock PREWATCH

V3.3今日算法候选
→ 今日新确认 / 确认变化

板块周期矩阵
→ Diagnostics

创新高/RPS
→ Stock Scanner Diagnostics

Shadow V2
→ Evidence Provider / Diagnostics

Focus Tracker
→ Canonical lifecycle history
```

---

# 69. API 重构

建议：

```text
/api/v4/context
/api/v4/home

/api/v4/radar/sectors
/api/v4/radar/stocks
/api/v4/radar/events

/api/v4/sectors/{id}
/api/v4/sectors/{id}/timeline
/api/v4/sectors/{id}/members

/api/v4/stocks/{id}
/api/v4/stocks/{id}/timeline
/api/v4/stocks/{id}/evidence

/api/v4/replay

/api/v4/focus/...

/api/v4/diagnostics/...
```


```text
/api/v4/stocks/{id}/profile
/api/v4/stocks/{id}/structure-events
/api/v4/stocks/{id}/anchors
/api/v4/stocks/{id}/why-not-prewatch

/api/v4/sectors/{id}/rotation
/api/v4/sectors/{id}/rotation-timeline

/api/v4/data-sources/status
/api/v4/data-sources/tdx-package
/api/v4/data-sources/baostock
```

所有V4研究响应携带§4.9完整context token和以下来源信息：

```text
publication_id
trade_date
core_revision
model_namespace
optional_enrichment_revision
data_as_of
turnover_as_of

source_contract_id
factor_contract_id
state_contract_id
parameter_set_id
quality
```

---

# 70. 代码级改造边界

## 70.1 重点保留

```text
technical.py
strength.py
sector_cycle.py
mainline.py
full_loo_v3_3.py
focus_tracker/*
```

---

## 70.2 重构

```text
sector_attention.py
→ sector_current.py
→ sector_warm.py
→ sector_emergence.py

stock_attention.py
→ stock_detectors.py
→ stock_base_seed.py
→ stock_confirmation.py
```

---

## 70.3 新增

```text
canonical_facts.py
data_quality.py
market_regime.py
relative_change.py
volatility_normalization.py
stock_base_seed.py
sector_emergence.py
stock_prewatch.py
research_state_machine.py
research_radar.py
rule_path_distance.py
validation_cohort.py
baostock_turnover.py
state_events.py
full_market_profile.py
trend_state.py
position_state.py
compression_state.py
participation_state.py
rotation_core_state.py
structure_events.py
support_acceptance.py
confirmation_event_compression.py
tdx_vipdata_bootstrap.py
tdx_period_resampler.py
source_overlap_validator.py
```

---


# 70A. Inherited Audit Register

| 项目 | 状态 | 权限与关闭条件 |
|---|---|---|
| AUD-AMOUNT-A-06 | OPEN/EVIDENCE_REQUIRED | amount_a_value/quality/contract_id分开；OPEN时只diagnostic，不进正式资格/排序/Focus。独立单位/共同成员/20日分母/覆盖/集中度实算及跨域引用验收后新合同启用 |
| Focus真实Forward缺口 | OPEN/FORWARD_REQUIRED | 保留原专项的精确范围和证据；旧新episode并存等真实样本继续跟踪，文档/合成通过不自动关闭 |
| 历史Universe/membership | CAPABILITY_SCOPED | current replay只diagnostic；按source证据升级 |
| 本轮全文修订 | DOCUMENT_REVISED | 代码和真实样本按模块独立验收，不能以文档自检关闭生产审计 |

sector_participation_proxy=median(member amount_ratio20)可依SECTOR_FACTORS_V1使用，必须另名，不称Amount A。若legacy M10路径需要Amount A而未通过，则该路径diagnostic，不暗换代理以维持正式资格。其他独立Core路径仍可运行。

---

# 71. 当前关键函数迁移清单

## `research_builder.build_latest_research_run`

当前核心问题：

> 历史 lifecycle 接线必须真正读取 accepted previous history。

V4-00A盘点，V4-14集成时必须证明：

```text
跨 separate daily builds
episode state 连续
```

---

## `sector_attention.build_sector_potential`

定位：

```text
Legacy WARM Provider
```

不再承担 PREWATCH。

---

## `sector_attention.progress_potential_episode`

保留思想。

迁移到正式：

```text
multi-day accepted state engine
```

---

## `stock_attention.classify_stock_attention`

定位：

```text
detector provider
```

不直接定义最终 Research Stage。

---

## `today_research_scanner_v3_3.scan_today_research`

迁移：

```text
four confirmation scenarios
+
SETUP_WATCH seed evidence
```

---

## `today_research_rank_loo_v3_3.rank`

只保留：

```text
confirmation ranking
```

不复用于 PREWATCH。

---

## `full_loo_v3_3.recompute_full_current_loo`

泛化为：

```text
Target-Excluded Sector Context
```

---

## `today_research_bundle`

长期：

```text
bundle = audit artifact
```

产品 authority：

```text
PostgreSQL canonical radar head
```

---

# 72. 参数注册表

contract_id=PARAMETER_REGISTRY_V1，初始parameter_set_id=V422_CODEX_ENGINEERING_01。本文新增规则中的数值均为候选默认值，包含窗口、阈值、计数、coverage、分桶边界、显示cap及排序scale；实现时提取到对应algorithm contract的命名参数，不散落代码。符号阈值没有赋值的模块不得静默选值。

每个参数保存id、contract_scope、value、unit、min/max与边界是否含等号、status、reason、introduced_version、approved_at、supersedes。通用epsilon用于浮点比较仅1e-12（单位随比较字段），金额/价格制度舍入单独按源/制度contract，不用此epsilon识别涨跌停。

初始关键参数：MA窗口5/10/20/60；slope deadband 0.1 ATR；minimum_liquidity 20,000,000 CNY prior20均额；RPS改善3/强改善10百分点；sector最少5成员/coverage0.8；Wilson z1.96；exit连续2会话；seed expiry10可评估会话；support浅收盘破0.5ATR/硬破1.5ATR/触碰带0.25ATR；Shadow20连续市场日/5个信号日/30个股票事件T5。

状态ENGINEERING_CANDIDATE→SHADOW_FROZEN→PROVISIONAL→SUPPORTED或RETIRED。值变更必须新parameter_set_id和model_contract_id，重新冻结cohort；旧值与旧outcome不改。候选默认值不因本文件存在而成为最佳或有效算法。现有Legacy阈值从基线源码提取保留，不用新增默认值覆盖Legacy。

Legacy contract提取、source units/历史制度表与性能预算属于测量型参数，须有真实回执再冻结；不是让实施者发明事实。未就绪只限制其模块，基础盘点和纯Core合同工作可继续。

# 73. 禁止实现硬编码与参数偷换

代码从参数实例读取；正文数值是可审阅候选参数说明。构建验收生成参数使用清单，每个AST literal必须有parameter_id或明确数学常数/枚举说明。所有尺度scale>0，整型窗口/计数必须正整数，coverage在[0,1]，排序边界有序。无该实例或digest不匹配拒绝affected计算，不回退到某个全局默认。

---

# 74. 性能 baseline

V4-00 先测：

```text
daily pipeline wall time
peak RAM
CPU utilization
factor compute time
sector stage time
radar build time
Focus time
PostgreSQL write time
API P50 / P95
homepage payload
DB size growth
```

之后才能决定：

```text
是否分区
是否物化视图
是否缓存
```

---

# 75. 运维

必须新增：

```text
source freshness alert
BaoStock budget alert
candidate count anomaly
state transition anomaly
publication failure
Focus replay backlog
validation settlement backlog
```

---

# 76. BaoStock 不可用降级

如果 BaoStock 当天失败：

```text
TDX analysis continues
```

换手：

```text
UNAVAILABLE
```

页面提示：

```text
换手数据源未完成绑定
```

不阻断主 publication，除非未来另有明确 contract。

---

# 77. 双写迁移

本版 不允许 Big Bang Cutover。

阶段：

```text
旧链继续生产
+
V4 shadow write
```

在影子期：

- 不改旧页面主结果；
- 不改 Focus source；
- 不覆盖 accepted history。

---


# 77A. 历史初始化

按§78先完成源/身份/调整合同；TDX package仅解压到项目staging，解析全部可识别历史证券，构建历史Universe，重叠核验，形成不可变Raw/Adjusted Daily及PIT周期，再计算Core、Replay A。
下载完整包不证明已退市全集/公司行为齐全；缺失按能力scope标注，不伪造PIT。若本地无可对照重叠范围，显式BOOTSTRAP_NO_OVERLAP，先进行独立格式/身份/样本核验而非假称overlap pass，待基线源验收后再提升。
历史按日期顺序运行§77B的纯计算路径，mode=REPLAY、origin=RECONSTRUCTED_*，不登记observed enrollment。BaoStock独立可选，失败不回滚Core。历史DAG无前態时FIRST_OBSERVED及warmup，不把首次可用日期伪称市场首次事件。

# 77B. 每日增量、接受与副作用

1. 冻结calendar、Universe/membership/source revisions、model/parameters、cutoff、prior_session_state_head；有每namespace/date单写锁。
2. 校验source freshness/completeness，生成不可见staging F0、Core Profile。
3. A Seed；B0/B1/B2 Sector/Rotation；C stock raw qualification，全部绑定该staging publication。
4. D0 confirmation detector；D1旧Anchor path/失效及新Anchor事件；D2 final state；D3 event diff/LOO context/Radar/eligibility ledger。
5. 运行质量、无反馈、身份、row coverage和一致性校验。事务内写结果、consumed source manifest、enrollment、outbox，并CAS更新accepted head。失败整批不可见；不能先写可见cohort再发布失败。
6. accepted后独立worker消费Focus outbox和settlement due items；每项publication/episode/enrollment幂等。可重试/补偿，不与Core transaction或BaoStock串行等待。
7. BaoStock独立抓取/绑定/enrichment manifest revision，仅刷新补充UI。Source correction产生Core新revision需重新走1–5，不能由enrichment触发隐式改写。

结算器只能用accepted且对应日期可见的来源，结果追加revision；交易日终点未可得保持due backlog并显示具体原因。原始price、Anchor、episode观察和accepted历史不回写。失败回滚不是删除所有V4数据，而是切换读取namespace/配置并保留审计线。

---

# 77C. Sector Membership 从现在开始建立真正 PIT

由于历史 TDX complete package 不提供可证明的“每个历史交易日板块成分关系”，V4.2.2 明确：

```text
价格历史可以回溯两年+
但板块 PIT membership 不能凭当前成员倒推两年前
```

因此从 V4.2 投产日开始，每天冻结：

```text
industry_membership_snapshot
concept_membership_snapshot
sector_type_snapshot
```

append-only。

投产日前的 sector replay：

```text
CURRENT_MEMBERSHIP_REPLAY
```

只能 diagnostic。

投产日后的 Forward：

```text
PIT_OBSERVED
```

才可作为正式板块验证证据。


# 78. 唯一实施阶段表

阶段按下面顺序交付，V4-06可选分支不是V4-07前置。算法实现前先完成该模块AST/参数/向量；纯基础盘点不受全局算法冻结阻断。V4-10可实现reducer接口和独立向量，但完整运行必须等V4-11/12，再于V4-14验收，不能把接口测试当完整DAG通过。

| 阶段 | 唯一名称 | 交付与准入 |
|---|---|---|
| V4-00A | Baseline Freeze | 当前HEAD、DB备份/恢复回执、accepted/Focus head、旧输出及继承审计；只读盘点不依赖未来AST |
| V4-00B | Security Lifecycle / Universe / PIT | 日期有效身份、知识时间、历史覆盖与不支持范围 |
| V4-00C | Publication / Revision / Namespace | 冻结前驱、消费manifest、修订事件与原子接受、namespace迁移 |
| V4-00D | TDX VIPDATA Source Contract | 有界下载、隔离staging、manifest、校验、archive与overlap |
| V4-00E | Historical Adjustment / Coordinates | 仿射调整、公司行为、历史可见性、Anchor与outcome比较坐标 |
| V4-00F | BaoStock Supplemental Contract | 字段单位/strict binding/有界请求；可复用有效回执，不阻断Core |
| V4-00G | Algorithm Contract Framework | AST/schema/参数实例、字段producer注册、纯函数Legacy提取规范 |
| V4-00H | Capability / Performance / Rollback | 能力scope、预算、失败回执、恢复演练；Phase 0最终回执 |
| V4-01 | TDX History Bootstrap | Raw archive、历史Universe和重叠核验；历史不足可scope降级 |
| V4-02 | Canonical Daily / PIT Periods | Raw/Adjusted、closed/asof周期、Price Limit规则表和覆盖 |
| V4-03 | Pure-Core Factors | CORE_FACTOR_V1、市场/sector native primitives、benchmark基础价格路径 |
| V4-04 | Full-Market Core Profile | §10B–10I全部Core字段，不依赖高级Anchor/Sector Context/BaoStock |
| V4-05 | Replay Gate A | DATA_FACTOR_REPLAY_PASS及能力scope，失败只阻断affected后继 |
| V4-06 | Supplemental Enrichment | Turnover历史/绑定/补充组件；与Core后继无硬依赖 |
| V4-07 | Stock Base Seed | BASE_SEED_V1与原始资格 |
| V4-08 | Sector / Rotation Core | 共同成员、B0/B1/B2、纯Core legacy sector资格adapter |
| V4-09 | Stock PREWATCH | STOCK_PREWATCH_V1原始资格与priority primitives |
| V4-10 | State Reducer | RESEARCH_STATE_V1接口与独立向量；最终集成须等D0/D1交付 |
| V4-11 | Confirmation / Events | Legacy精确AST提取/黄金样例、D0 facts与D2后event diff，隔离Amount A路径 |
| V4-12 | Structure / Anchor / Support | D1算法、换基、breakout/pullback/recovery、支持/接受 |
| V4-13 | Profile Advanced Projection | Context/LOO/Structure投影与完整DAG集成 |
| V4-14 | Replay Gate B | ALGORITHM_STATE_REPLAY_PASS：完整D0/D1/D2时序与修订 |
| V4-15 | Radar / Cohorts / Settlement | 字段全量登记、事件样本、控制分配、市场/板块benchmark、due planner、价格结算、结果修订、Why Now及readback |
| V4-16 | Realtime Shadow Dual-Run | PIT_OBSERVED+SHADOW，真实冻结日账本并每日运行settlement，旧系统继续production |
| V4-17 | Shadow UI | 同context token，展示完整已实现组件，不写production Focus |
| V4-17G | Shadow Stable / Provisional Forward Gate | §52A两门，样本不足延长观察；禁止以historical replay凑天数 |
| V4-18 | Migration Replay Gate | MIGRATION_REPLAY_PASS：前態继承、旧episode/未结算工作、namespace和rollback |
| V4-19 | Focus Source Cutover | 仅§52A三门通过后，accepted V4 source进入生产Focus |
| V4-20 | Default UI Cutover | 默认V4，Legacy下沉diagnostic，明确PROVISIONAL |
| V4-21 | Continued Forward Observation | 继续累计Shadow/Production各自分层证据；不在此首次开发结算器 |
| V4-22 | Independent Audit | 数据/算法/发布/迁移/UI/Forward/rollback独立验收；开放项不自动关闭 |

每张卡记录input commit、适用合同、source/capability、allowed/forbidden files、schema migration、fields/producer/time、UNKNOWN行为、旧行为保护、独立test vectors、集成/E2E/replay、rollback、evidence receipt、acceptance scope及next stage。卡模板允许CONTRACT_DESIGN任务，不允许假称DRAFT算法已验收。

---

# 79. Phase 与 Priority

P0表示受影响正式能力不可越过，不表示全项目一次实现。以§78的稳定阶段ID引用，不再保留另一套阶段名称；V4-05 Replay A在Core之后，V4-14在完整算法集成之后，V4-18在真实Shadow门之后。所有DEGRADED必须携带scope，BLOCKED scope不可进入其scanner/consumer。

---

# 80. 测试矩阵 V4.2.2

## 数据

- 交易日错位；
- publication/date mismatch；
- stale source；
- missing membership；
- BaoStock budget exhausted；
- turnover soft binding；
- partial history。

## A股制度

- ST；
- 主板涨停；
- 创业板涨停；
- 停牌；
- 复牌；
- 新股；
- 退市整理；
- 除权/复权身份切换。

## PREWATCH

- weak market active emergence；
- passive defense only；
- sector absent but stock seed；
- multi-sector；
- high RPS old leader decelerating；
- low volatility defensive bias。

## Sector

- 5-member small concept；
- 80-member broad sector；
- one-stock-driven；
- overlapping concepts；
- PIT membership change。

## State

- threshold epsilon；
- flapping；
- data gap；
- hard damage；
- expiry；
- direct PREWATCH→CONFIRMED；
- reentry；
- model boundary。

## Forward

- right censor；
- control assignment；
- all eligible captured；
- hidden/display excluded but still settled；
- historical reconstructed vs REAL_FORWARD separated。

---

# 81. Definition of Done V4.2.2

## 81.1 Engineering Complete

必须：

- no temporal leakage；
- deterministic replay；
- no same-day feedback loop；
- PIT basis explicit；
- quality propagates；
- no duplicate episode；
- revision idempotent；
- rollback works。

---

## 81.2 Product Complete

用户能快速回答：

```text
今天发生了什么变化？
为什么今天而不是昨天？
它处在哪个阶段？
支持证据是什么？
反证是什么？
等什么确认？
什么会失效？
```

---

## 81.3 Algorithm Evidence

不能靠：

```text
“页面看起来更合理”
```

必须：

- validation cohort 完整；
- controls 完整；
- outcome 可观察；
- right censor 正确；
- 按 market/sector 分层；
- 不只看 self-confirmation；
- 旧系统 head-to-head 可比较。

---


## 81.4 Contract Completeness DoD

允许先拆基线与合同设计卡；对应实现卡开工前必须有该模块字段注册、AST/参数实例、producer/time semantics、source能力/UNKNOWN及独立向量。没有则该模块CONTRACT_INCOMPLETE，不能由实现者悄悄补语义。
整体上线前所有承诺组件与用户可见字段须覆盖§87A机器注册表，且通过完整DAG、发布一致性、source degradation、真实Shadow/Forward与迁移门。文档检查不替代代码测试、实测性能或统计证据。

---

# 82. V4.2 不使用的验收指标

明确不使用：

```text
每天必须非空
每天必须 N 只
上涨率必须 > X%
20天就宣布有效
某一个市场阶段好看就宣布通过
```

---

# 83. 风险与失败回滚

§52A是唯一切换政策。“样本不足/尚未证明增量”不能当作已失败或改候选阈值的理由。Shadow P0、无法解释的系统异常、超事前冻结运行预算则NO_CUTOVER并登记独立审计；修订算法/参数要新模型和cohort。
切换后保留legacy可恢复运行能力；失败时切读/写source namespace，保留V4不可变历史、outbox和未完成outcome。停止不合法新副作用，已接受的事件不删除；恢复旧系统时按预演manifest处理切换期间空档，不能只恢复一个数据库备份而丢失用户pin/后续观察。

---

# 84. 术语表

## PREWATCH

未形成正式确认，但已经出现值得跟踪的变化。

## WARM

已有早期共振；主要继承旧 POTENTIAL。

## CONFIRMED

已有明确确认；主要继承 CURRENT/V3.3。

## Seed

内部最早变化对象；默认不直接进 Focus。

## Radar

每日研究优先级读模型。

## Focus

产品持续跟踪系统。

## Validation Cohort

完整算法效果验证样本，不受 UI/人工选择影响。

## Why Now

今天相较前一 accepted 日发生了什么变化。

## PIT

只能使用当时能够知道的事实。

---

# 85. 关键治理原则最终版

1. 先事实，再因子，再状态。
2. Stock Base Seed 不读 Sector PREWATCH。
3. Sector Emergence 只读冻结的 Base Seed。
4. Final Stock PREWATCH 不反向修改当天 Sector。
5. Context 不作为第一版 Stock PREWATCH hard gate。
6. 相关价格信息不能重复计价成多个独立证据。
7. 弱市允许 0 正式 PREWATCH。
8. Passive Resilience 不等于 Active Emergence。
9. 旧强势不等于今日优先。
10. 任何历史 replay 都必须标 membership basis。
11. Focus 是产品跟踪，不是完整模型样本。
12. Validation Cohort 必须包含所有 eligible 对象。
13. T0 不允许使用未来 lead time 做准入。
14. Forward 结果只能追加，不能改写 T0。
15. BaoStock turnover 是辅助，不控制主资格。
16. 模型版本边界不是市场退出/重入。
17. 参数变更创建新 cohort。
18. 代码 PASS 不等于算法有效。
19. 页面展示 cap 不等于算法资格 cap。
20. 不为“页面不空”制造候选。

---

# 86. 最终架构判断

V4.0 最大的正确方向是：

> 从“排名结果”转向“变化发现”。

本版 把它补全成：

> **变化发现 + 无反馈计算 + PIT + 多轴状态 + 完整样本验证。**

最终系统的核心不再是：

```text
谁排第一？
```

而是：

```text
今天什么变了？
变化来自什么可观察事实？
它是被动抗跌还是主动改善？
它处于 Seed、PREWATCH、WARM 还是 Confirmed？
板块支持是否在剔除目标股后仍成立？
这个状态是新的，还是已经停滞很多天？
有什么反证？
什么条件会确认？
什么会失效？
后续真实结果相对市场、板块和对照组怎么样？
```

只有这样，这套系统才真正服务于用户长期培养目标：

> **帮助用户更早地发现值得研究的市场变化，同时保持可解释、可证伪、可跟踪、可复盘，而不是替用户制造更多“看起来很聪明”的候选。**

---


# 87. Feature → Data → Algorithm → UI 全链路追踪矩阵

这是 V4.2 的强制可追踪合同：**页面存在的功能必须在本文找到算法来源；算法输出必须知道落在哪张表和哪个页面。**

| 页面功能 | 数据输入 | 核心算法/思想 | 主要结果 | 页面 |
|---|---|---|---|---|
| 市场环境 | market facts | Trend/Breadth/Participation/Stress 四轴 + hysteresis | regime axes + UI regime | 今日总览 |
| 今日轮动 | sector facts + seed + retention | Rotation State Engine | PULSE/IN/ACCEPTED/EXPANDING/OUT | 今日总览/板块 |
| 板块 PREWATCH | sector native + frozen base seed | PASS B + emergence + small-sample adjustment | Sector PREWATCH | 今日总览/板块 |
| 板块 WARM | legacy POTENTIAL | BREADTH/BASE/RECOVERY build | WARM | 板块 |
| 板块 Confirmed | legacy CURRENT | strict confirmation | CONFIRMED | 板块 |
| 高位衰减 | RS20 + dq5 + breadth + retention + extension | Exhaustion Axis | WEAKENING/EXHAUSTED | 首页风险/板块 |
| 全市场趋势 | TDX daily/weekly/monthly | Trend State rules | trend_state | 个股搜索 |
| 全市场位置 | TDX daily + ATR | Position State | position_state | 个股搜索 |
| 放量/缩量 | amount/volume history | self-relative ratios | amount_state | 个股搜索 |
| 换手异常 | BaoStock turn | ratio/percentile valid sessions | turnover_state | 个股搜索 |
| 相对强弱 | RPS + market/sector relative | Relative State + passive/active distinction | relative_market_state | 个股搜索 |
| 压缩/扩张 | range/ATR/vol | Compression | compression_state | 个股搜索 |
| 基础突破 | prior anchors | Basic Breakout | breakout_state | 个股搜索 |
| 回踩 | prior trend/anchor | Pullback state machine | pullback_state | 个股搜索 |
| 恢复 | reclaim/relative recovery | Recovery Engine | recovery_state | 个股搜索 |
| 中阳支撑 | impulse body/ATR/CLV | Bullish Impulse + Anchor | impulse event | 个股详情 |
| 支撑有效 | anchor + future facts | Test→Reclaim→Hold→Retest | support_state | 个股详情 |
| 价格接受 | impulse + retention | Acceptance/Retention | retention facts | 个股/板块 |
| Stock PREWATCH | Daily Profile + PASS A | Rule Path + Priority Axes | PREWATCH | 首页/个股 |
| 今日新确认 | V3.3 scenes | Confirmation Event Compression | NEW/UPGRADE/RECONFIRM | 首页 |
| Persistent Confirmed | prior/current confirmation | state diff | PERSISTENT | 完整列表/Focus |
| Why Now | previous/current accepted state | State/Event Diff | changed facts/domains | 所有研究详情 |
| Conflict | evidence graph | support/opposition/unknown split | conflict panel | 板块/个股 |
| Focus | Radar selected + user pin | existing Episode/Segment/PathState | lifecycle history | 关注跟踪 |
| Forward 验证 | all eligible cohort | T+1/3/5/10/20 + controls + censoring | outcomes | 诊断/审计 |
| PIT Replay | historical publication | no-future read | frozen historical view | 板块/个股 |

如果后续新增页面功能而此表没有对应算法章节：

```text
DESIGN_INCOMPLETE
```

不得直接开发。

---


# 87A. Field → Algorithm Contract Registry

以下字段族是规范登记；实现前展开为逐字段schema，包含data type、unit、producer、required/optional、time、output digest和显示标签。不得由页面发明未注册资格字段。算法contract+参数实例唯一；表中多个contract代表派生链，不代表任选。

| 字段/字段族 | 权威输入 | Algorithm Contract | 阶段 | 缺失/降级 |
|---|---|---|---|---|
| trend_state; weekly_trend_state; monthly_trend_state | TDX adjusted/closed periods | TREND_STATE_V1 | V4-04 | required缺失UNKNOWN |
| position_state; near_high20_state; near_high60_state; drawdown20_state; drawdown60_state; pos60/250; bias20_atr; dist_high20_atr | Core price/ATR | POSITION_STATE_V1 | V4-04 | 分母0/历史不足UNKNOWN；pos250独立 |
| ma_structure_state | Core MA | MA_STRUCTURE_V1 | V4-04 | UNKNOWN |
| relative_market_state; RPS5/20; delta1/3; rel_market_1/3/5 | historical Universe/market | RELATIVE_STATE_V1 + CORE_FACTOR_V1 | V4-03 / V4-04 | non-PIT只diagnostic |
| compression_state | range/ATR/vol/liquidity | COMPRESSION_STATE_V1 | V4-04 | UNKNOWN |
| amount_state; volume_state; core_participation_result | TDX amount/volume/OHLC | AMOUNT_VOLUME_STATE_V1 | V4-04 | UNKNOWN |
| core_extension_risk; core_price_damage | Pure-Core price/amount | EXTENSION_RISK_V1 + CORE_FACTOR_V1 | V4-03 / V4-04 | UNKNOWN |
| trading_status; limit_status; resumed_event; lifecycle_status | local identity/calendar/制度表 | TRADING_STATUS_V1 / PRICE_LIMIT_RULE_V1 | V4-02 | UNKNOWN；补充不得覆盖 |
| turnover_state; turnover_ratio20; turnover_pct20/60; turnover_ma5; turnover_delta3; supplemental_participation_context; supplemental_extension_note | BaoStock strict binding | TURNOVER_CONTEXT_V1 | V4-06 | PENDING/UNAVAILABLE/UNKNOWN_DATA |
| base_seed_state; matched_seed_paths; seed_participation_annotation | Core | BASE_SEED_V1 | V4-07 | Kleene三值 |
| sector_emergence; sector_rs5/20; rank_velocity; dq5; breadth_delta; ma20_width; seed_width; retention; entered/exited; top1/top3_concentration; sector_participation_proxy | PIT common member/Core Seed | SECTOR_FACTORS_V1 / SEED_WIDTH_V1 / SECTOR_AXES_V1 | V4-08 | 覆盖低UNKNOWN，0分母NA |
| amount_a_value; amount_a_quality; amount_a_contract_id | 独立Amount A审计 | AUD-AMOUNT-A-06 | V4-08 | OPEN只diagnostic，禁止正式consumer |
| rotation_core_state; sector_price_retention_core; rotation_episode_id; rotation_structure_enrichment | B0/历史/固定篮子；structure仅D3 | ROTATION_CORE_V1 | V4-08 / V4-13 | UNKNOWN保留last_known |
| primary_industry; supporting_concepts; algorithmic_support_sector; relative_sector_state; sector_context_state; sector_context_quality | PIT membership/完整LOO | LOO_CONTEXT_V1 | V4-13 | 无合格NA，数据不足UNKNOWN |
| stock_prewatch; raw_qualification; final_eligibility | A/C/D2 | STOCK_PREWATCH_V1 / RESEARCH_STATE_V1 | V4-09 / V4-10 | UNKNOWN不计eligible |
| maturity_stage; health_state; validity_state; tracking_state; scenario; state_freshness; expiry; reentry | raw资格/D0/D1/冻结前態 | RESEARCH_STATE_V1 | V4-10 | STALE/UNKNOWN不制造退出 |
| confirmation_event_type; primary_scenario; matched_scenarios; source_model_boundary | Legacy manifest/D2 diff | LEGACY_ADAPTER_V1 / STATE_EVENT_V1 | V4-11 | FIRST_OBSERVED或NA |
| active_anchor_id; anchor_view_asof_t; basic_breakout_state; basic_pullback_state; basic_recovery_state; structure_health; structure_events | frozen Anchor/price detector | STRUCTURE_EVENT_V1 | V4-12 | NOT_IMPLEMENTED/NA/UNKNOWN分开 |
| support_state; acceptance_state; impulse_retention_1/3; retest_count | D1路径 | SUPPORT_STATE_V1 / RETENTION_V1 | V4-12 | PENDING/UNKNOWN/NA分开 |
| market_regime_axes; stress_level; stress_change; regime_ui | Core market/制度coverage | MARKET_REGIME_V1 | V4-03 / V4-04 | UNKNOWN及last_known |
| waiting_for; invalid_if; why_now; conflict_panel; hypothesis_set | frozen AST/事件/证据模板 | NEAR_MISS_V1 / STATE_EVENT_V1 / HYPOTHESIS_V1 | V4-15 | UNRESOLVED/INCOMPLETE，不强造文本 |
| eligibility_rank; priority_bucket; priority_rank; display_rank; overlap_cluster_id; also_in_sectors | 完整eligible + event filter | PRIORITY_V1 / DISPLAY_V1 | V4-15 | unknown排序末尾，cap不改资格 |
| daily_eligibility_ledger; statistical_signal_event; enrollment_id; controls; forward_outcome; benchmark; MFE; MAE; MDD | frozen T0/未来事实隔离结算 | COHORT_V1 / CONTROL_ASSIGNMENT_V1 / FORWARD_PRICE_PATH_V1 / MARKET_BENCHMARK_V1 | V4-15 | 按到期/缺失/停牌/退市分开 |
| focus_activation; Focus timeline/path/outcome | accepted Core/原Focus契约 | 现有Focus版本清单 + migration manifest | V4-19 | Shadow不写production |
| profile component statuses; quality; source_asof; context token; diagnostic counters | 冻结manifest/组件能力 | PUBLICATION_V1 / QUALITY_V1 | V4-00C / V4-04 / V4-15 | unknown和NOT_IMPLEMENTED分开 |

只读投影允许同义UI标签，但API枚举/字段不得另起一套；旧relative_market_state→relative_market_state、core_extension_risk→core_extension_risk、rotation_core_state→rotation_core_state为显式schema迁移映射，旧publication原样保留。

---

# 88. 外部数据接入故障矩阵

| 故障 | 主流程处理 | UI | 是否阻断 |
|---|---|---|---|
| TDX完整包无法下载 | 保留旧 accepted source；不做新 bootstrap | 数据源异常 | 初始化/补历史阻断 |
| 当日 TDX 必需覆盖未通过 | 不发布该scope的新 accepted trading day | 显示等待数据 | **阻断当日主发布** |
| TDX local/package mismatch | `SOURCE_MISMATCH` | 诊断可见 | **阻断冲突范围** |
| 本地 QFQ 生成失败 | raw可保留，adj factors UNKNOWN | 复权指标不可用 | 阻断需要QFQ的正式算法 |
| BaoStock login失败 | TDX 主链继续 | 换手暂不可用 | 不阻断价格主链 |
| BaoStock部分股票失败 | 个股 turnover PENDING/UNAVAILABLE | 明示 | 不阻断其他字段 |
| BaoStock fingerprint冲突 | UNAVAILABLE / BINDING_MISMATCH | 数据质量告警 | turnover factor 阻断 |
| Sector membership未知 | context quality降级 | 明示 | 不允许伪造PIT |

---


本版 额外规定：

```text
TDX core source failure
→ can block Core Publication

BaoStock supplemental failure
→ cannot invalidate accepted Core Publication

historical membership/universe uncertainty
→ downgrade historical evidence origin

adjustment uncertainty
→ block adjusted-dependent factors only
```

---

# 89. V4.2.2 最终产品原则

系统最终不是：

```text
先筛掉99%
→ 只理解剩下1%
```

而是：

```text
全市场每日状态理解
→ 找出今天真正发生变化的对象
→ 将少量对象推到用户首页
→ 用户可搜索任何一只股票查看完整基础画像
→ 对重点对象再做结构事件、F/R/H、确认/失效和持续跟踪
```

这也是 V4.2 相对于 本版 最重要的升级。

---

# 历史附录 D：V4.1 → V4.2 迁移说明

新增：

1. 通达信付费量化接口/TQ 从 Required Dependency 中彻底移除；
2. TDX 官网 vipdata 完整日线包成为正式历史 Bootstrap；
3. 两年 Formal Research Window + 更早 warm-up；
4. 日线统一派生周/月线；
5. BaoStock 只做 turnover/tradestatus/isST supplement；
6. 全市场 Daily Stock Profile；
7. Rotation State Engine；
8. Structure Event Engine；
9. Support/Acceptance Engine；
10. V3.3 Confirmation Event Compression；
11. 首页板块 5–10 常态、15硬上限；
12. 首页独立个股 30 硬上限；
13. 首页只显示变化对象；
14. 行业与概念合并 Radar，风格板块排除；
15. 页面功能与算法强制 Traceability Matrix。

本历史附录不构成当前规范；当前合同仅按本修改版正文。


# 附录 A：审计意见最终处置摘要

## 已采纳

- 四阶段无反馈 DAG；
- PIT membership；
- evidence domain / rule path；
- volatility normalization；
- passive vs active resilience；
- small-sector confidence adjustment；
- multi-axis state machine；
- hysteresis / expiry；
- Validation Cohort；
- controls；
- right censor；
- independent forward outcomes；
- early engineering replay；
- quality propagation；
- AST Near-Miss；
- Why Now；
- Conflict Panel；
- PIT Replay；
- performance baseline；
- temporal leakage tests。

## 修改后采纳

- Market Regime；
- turnover soft binding；
- NEW priority；
- H competitive hypotheses；
- sector overlap；
- statistical validation；
- weighted sector context。

## 明确不采纳

- T0 准入要求未来至少领先 N 日；
- 用未来 T+5 改写 T0；
- “主键没 trade_date 就只能存一日”的错误判断；
- publication_id 强制 hash 化；
- 弱市候选非空率 KPI；
- concept 成员按 1/N 稀释；
- 第一版 mandatory cap-weighted sector RS；
- turnover 作为 hard PREWATCH gate；
- 第一版 regime-specific eligibility 参数；
- 无性能证据就强制 PostgreSQL range partition；
- 全面 market-cap / industry neutralization。

---

# 附录 B：任务卡索引

阶段与依赖只引用§78，不再复制第二套阶段表。任务卡必须带stage_id、contract ids/digests、input commit、source/capability scope、allowed/forbidden files、migration、required tests、独立证据、rollback、acceptance result和next_stage。

---

# 历史附录 C：V4.0 → V4.1 迁移说明

V4.1 保留 V4.0 的主方向，不推翻：

```text
Canonical Facts
Factors
PREWATCH
Confirmed
Radar
Focus
Forward
```

主要新增：

1. 无反馈计算 DAG；
2. PIT membership；
3. Evidence Domain / Rule Path；
4. Passive vs Active Resilience；
5. volatility-normalized position；
6. small-sector confidence；
7. multi-axis state；
8. independent validation cohort；
9. controls / right censor；
10. publication/date一致性；
11. Why Now / Conflict / PIT Replay；
12. detailed quality propagation。

主要删除/纠正：

1. 简单 `>=3 evidence family`；
2. Context 作为 PREWATCH hard gate；
3. 单轴大生命周期；
4. 20天等同算法验证；
5. Focus 样本等同模型完整样本；
6. 弱市必须有候选的隐性产品压力；
7. PREWATCH 全局总分思路。

---


# 历史附录 F：V4.2 → V4.2.1 迁移说明

V4.2 的产品目标、全市场画像、PREWATCH、Rotation、Support/Acceptance、Confirmation Compression、页面上限和 Focus/Validation 分离全部保留。

V4.2.1 主要修正的是“实施合同”：

1. Focus Cutover 移至 Shadow Stable + Migration Replay 之后。
2. Daily Profile 改成分层组件交付。
3. Replay 从单门拆成三道门。
4. 增加 Historical Security Lifecycle / survivorship-safe Universe。
5. 增加 Historical Adjustment Contract。
6. 增加 Weekly/Monthly AS-OF。
7. 增加 Core Publication / Supplemental Enrichment 权限边界。
8. 增加 Data Cutoff。
9. 增加 TDX VIPDATA Adapter。
10. 增加 Historical Reconstruction Identity。
11. 增加 Price Limit Rule Engine。
12. 增加 Field → Algorithm Registry。
13. 清理过期任务编号、字面转义换行和不再准确的 V4.1 自称。

因此：

```text
V4.2
= Product & Algorithm Architecture Baseline

V4.2.1
= Final Executable Contract Baseline
```

---

# 附录 E：正式外部数据源清单

## TDX Personal Market Data

```text
https://www.tdx.com.cn/article/vipdata.html
```

用途：

```text
沪深京日线完整包
历史价格 Bootstrap
盘后离线数据
```

V4.2 不要求任何 TDX Quant/TQ 权限。

## BaoStock Historical K Data

```text
https://www.baostock.com/mainContent?file=stockKData.md
```

用途：

```text
turn
tradestatus
isST
```

并使用 OHLC/volume/amount 作为绑定 fingerprint，不作为正式价格权威。

任何字段、频率、限流、稳定性只有在本地 adapter smoke test 通过后才能进入正式 Source Contract。

---


# 附录 G：codex修改版变更追踪

本版在原件副本直接替换冲突章节，保留产品目标与未冲突说明；详细逐章变更、审计项映射、原件/输出SHA256和自检结果见同目录《codex修改版_修改说明》。DOCUMENT_REVISED不代表IMPLEMENTATION_PASS，也不关闭Amount A/Focus真实Forward等独立审计。

---

# 本次修订签署状态

DOCUMENT = DA-MSR-V4.2.2-CODEX-REV1
STATUS = DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK
IMPLEMENTATION / REAL_DATA / FORWARD = NOT_VERIFIED_BY_THIS_DOCUMENT_EDIT
TDX = READ_ONLY_INPUT
BAOSTOCK = SUPPLEMENTAL_ONLY
STAGES = SECTION_78_ONLY
SETTLEMENT = V4-15_BEFORE_SHADOW
INHERITED_AUDITS = OPEN_UNTIL_INDEPENDENT_EVIDENCE

**文档结束**

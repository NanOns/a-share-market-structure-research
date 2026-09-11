# M10 金额 A 设计裁定与实施对齐

日期：2026-09-10。状态：IMPLEMENTED_PENDING_INDEPENDENT_ACCEPTANCE。

本文件依据当前工作区源码与 M10_AMOUNT_A_AUDIT_BRIEF.md 进行定义审查；未运行新公式或验收预览，不是 EXTERNAL_AUDIT_PASS。用户本次要求修改方案，简报中“暂不修改方案”的说明是该简报编写时的工作范围，不限制本次修改。

## 1. 裁定与证据

问题是统计层级发生替代，同时文档缺少精确定义。不能用“公式都可解释”证明实现符合设计，也不能断言整套实施都错误。

- technical.py 的 shift(1).rolling(20) 计算个股排除当日的金额比；若输入日期有缺口，滚动行数不自动等于主交易日窗口，因此仍须验证上游日历补齐，不无条件认定全部窗口实现正确。
- sector_cycle.py 对 member_amount_vs_prior20 取中位数，window_stats 标记 MEMBER_MEDIAN_STOCK_AMOUNT_VS_PRIOR20；member_amount_sum 未参与该比值计算。
- mainline.py 直接读取上述字段，按板块行位置取比较日；NEW/REACCELERATING/FADING 因此消费代理值。
- 示例：三股历史日均各100，当日300、100、100，中位数为1，聚合比为500/300。两者会导致金额谓词不同。

正式 A 选择“可比成员聚合金额扩张”；典型成员中位数单列诊断。成交额代表成交活跃度，不能叫净资金流入。该选择是设计决策，不是收益有效性的证明。

## 2. 可执行公式

主交易日历为 C，t 的基准 W20(t) 为 C 中严格前20个位置。H21(t)=W20(t)∪{t}；不跳过缺日向前补足。raw_amount 单位元，不使用复权金额。

### 2.1 成员口径

OBSERVED：每个 H21 日期都有封存成员依据，候选集合为这些日期成员集合的交集。

RECONSTRUCTED：固定一个已声明的成员快照 K，按 K 的成员回算 H21。不能把缺失的历史成员集合伪造为 K 当时存在。快照观察时间、回算锚、证券范围偏差必须随字段/API/页面提供。新概念可显示回算活动，但不是“当时已存在的概念”。

两种模式均再取在 H21 所有日期金额状态已知且合格的完整成员，得到 U。U 在分子分母中必须完全相同。每日相加不同成员总额再滚动，不作为正式 A。

S(U,u)=Σ raw_amount(i,u), i∈U

D(U,t)=Σ[S(U,u), u∈W20(t)] / 20

A(s,t)=S(U,t)/D(U,t)

历史股票短于窗口不进入 U，但必须计入目标成员分母，不能通过缩小分母掩盖缺失。新股可展示报价及缺失原因。

### 2.2 金额质量门

建议冻结为首版预览质量参数：min_comparable_members=5，min_comparable_coverage=0.80；它们是工程质量门，不是已证实最佳经济参数。不得根据状态命中数量调整。

目标分母 N 为当前目标成员数；OBSERVED 另要求 |U|/max(H21 各日目标成员数)≥0.80，避免大量删除成员后覆盖看似满额。保存两项覆盖以及分母来源。

有限正数有效；有来源确认的无成交/停牌零额有效并计入均额，不等于未知。无来源的零值、负数、非有限值、缺行、质量失败视为未知；不得补零。D≤0 则 A=NULL；分子确认为0且 D>0 时 A=0，是有效的低活跃状态，不能被 gt(0) 过滤。

任一门未通过时 A=NULL，质量码给出 NO_CALENDAR、INSUFFICIENT_HISTORY、MEMBERSHIP_HISTORY_MISSING、LOW_MEMBER_COUNT、LOW_COVERAGE、INVALID_AMOUNT 或 NONPOSITIVE_BASELINE；可保存多个原因。

member_amount_sum 单独表示当前成员已知金额部分总和，保留覆盖与 partial 标识；不能被界面无条件叫完整板块总额。它不必等于 A 的可比分子。

### 2.3 三交易日变化

比较日期 c=C[t_index-3]，不能使用板块已有行的倒数第四行。

用于金额下降谓词的共同集合 V 在 H21(t)∪H21(c) 的24个主交易日上固定，按上面模式和质量门构造。分别计算 A(V,t) 与 A(V,c)：

sector_amount_ratio_delta_3sessions_common=A(V,t)-A(V,c)

单位是比值差，不是涨跌百分比或3日均额比。保存两端值、比较日、V 哈希、分子/分母、覆盖。它可能不同于页面两个各自使用 U 的 A 值之差；页面必须明确“固定共同成员比较”。

FADING 使用共同集合差值严格小于负的既有精度容忍值；持平不算下降。NEW/REACCELERATING 使用当日 A(U,t)。差值不可用时为 UNKNOWN，不退回独立成员 A 值相减。若未来需要3日均额比，另开字段和合同。

## 3. 字段与消费约束

| 字段 | 层级与用途 |
|---|---|
| stock_technical_daily.amount_ratio20 | 保留旧含当日个股公式 |
| stock_technical_daily.amount_vs_prior20 | 保留排除当日个股公式 |
| member_amount_ratio_median_vs_prior20 | 旧板块代理新明确名称，只诊断 |
| member_amount_sum / amount_valid_count | 当日已知金额规模及样本数 |
| sector_amount_vs_prior20 | 正式板块 A |
| sector_amount_comparable_sum / sector_amount_prior20_mean | A 分子与分母，单位元 |
| amount_comparable_member_count / amount_target_member_count | 可比集合与目标数量 |
| amount_comparable_coverage / amount_window_coverage | 当前及窗口覆盖 |
| amount_basis / amount_quality_codes / amount_contract_id | 模式、质量、合同 |
| amount_member_set_hash / amount_window_start/end | 复算依据 |
| sector_amount_ratio_delta_3sessions_common | 同一24日成员集合下的比值差 |
| amount_comparison_evidence | 比较日、两端A、分子分母、V哈希、覆盖及缺失 |

旧 sector_cycle_daily.amount_vs_prior20 与 mainline_daily.current_amount_vs_prior20 不原地改义；旧 slice 原样保留并标明 LEGACY_PROXY。新消费者按显式合同字段读取，不允许 coalesce(new_A,old_proxy)。字段目录必须记录生产者、公式、层级、单位、窗口、成员口径、质量门、消费者和测试 ID。

金额 predicate 采用三态逻辑。金额未知不自动把全板块判弱：只有依赖它的条件为 UNKNOWN；保持既有状态优先级和 UNKNOWN_HIGHER_PRIORITY 规则。不依赖金额的状态是否可输出由完整三态树决定，不能把所有未知统一转 False。

## 4. 阈值、历史视图与版本

1.10/1.20 暂保留作预览起点，不能因公式改变而宣称阈值已验收。新旧公式需要差异报告和人工复算；不以增加/减少 NEW 数量优化阈值。

新增 SECTOR_AMOUNT_COMMON_AGG_V1 和 MAINLINE_STATE_V2_4_PREVIEW 已作为运行合同，生成新配置、依赖哈希及新 slice/snapshot；旧合同和旧代理列未改义。

公式/质量门变化标 MODEL_CHANGE；成员快照、OBSERVED/RECONSTRUCTED 切换标 BASIS_CHANGE；不得当成市场退潮。回算页允许明确展示回算分类，正式 OBSERVED 消费者不得混入回算条件；Forward 不补造历史观察。

历史计划器必须增加依赖：单日 A 需21个主交易日，3日差需24个。若主线输出依赖 L 日 A 序列，原始窗口至少 L+20；同时涉及差值需再覆盖3日边界，最终取完整依赖图最大值，不沿用硬编码预热天数。

## 5. 实施顺序与对齐矩阵

| 顺序 | 交付 | 验收证据 |
|---|---|---|
| A 定义冻结 | 本裁定、主方案、字段目录与正式新合同一致 | 每个符号都有日期/集合/质量定义 |
| B 独立计算 | sector_amount 聚合函数及窗口计划器 | 手算与边界测试，不先嵌进分类函数 |
| C 数据迁移 | 新增列/表、新 slice 依赖；不复用已部署迁移编号 | 临时库迁移、旧数据未改义 |
| D 主线消费 | 三态金额门、显式合同、API/UI证据 | 禁用代理兜底，旧页面标注代理 |
| E 差异预览 | 新旧并排，按 OBSERVED/RECONSTRUCTED 分组 | 公式差/成员差/质量差分别报告 |
| F 独立验收 | 实际代码与输入哈希、样例和剩余阻断 | 外审通过才允许新正式消费 |

中位数与聚合比、规模与广度是互补维度；文档不应为适配已写代码而把它们混成一个指标。后续所有经济字段要求“定义卡 → 数据能力 → 实现 → 证据”闭环。实现困难只能显式缺失或提出新合同，不能悄悄采用代理。

## 6. 必测场景

- 个股100×20、今日300：新3、旧300/110；保持个股合同。
- 三股300/100/100：算术核对聚合5/3、中位1；因少于5股正式门返回 LOW_MEMBER_COUNT。正式门样例用五股500/100/100/100/100，聚合1.8、中位1。
- 新增成员仅改变原始规模，OBSERVED 公共集合排除新增；回算模式固定 K 全窗口验证；成员变动不会在同一分子分母中混入。
- 中间缺一个主交易日，不按第21个更早观察补齐；重复日期必须拒绝。
- 4股完整/5股目标满足80%但仍未达5股数量门；5/6有效通过、5/7不通过。
- 已知零分子输出0；未知不能补零；全零分母返回NULL。
- 去掉大金额成员需同时显示可比覆盖和剔除清单，不能暗示剩余聚合代表全部成员。
- 3日前缺日或共同集合不足，差值UNKNOWN；同一24日集合手算两端与差值。
- 模型/输入/模式改变生成新身份；旧发布及旧代理不覆盖。
- A未知沿三态优先树传播；禁止把 proxy 注入 NEW 或 REACCELERATING。
- 阈值边界1.10/1.20及持平下降判定、输入顺序变化确定性、金额单位一致。

测试通过仅证明定义实现一致；主线经济有效性不能由测试数量证明。

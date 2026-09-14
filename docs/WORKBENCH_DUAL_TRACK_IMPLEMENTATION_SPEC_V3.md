# 工作台双线改造 V3：功能去留、双轨板块与个股联动实施规格

> **执行权威说明（2026-09-13）**：V3新功能、新界面、新存储和新执行顺序以本文件为主，M0–M15旧合同不得否决V3已明确的变更。P09在线执行先读§22龙字诀优先及解阻裁决，再读§21伏羲补位，其他冲突读§20、§19及§18。旧合同仅约束仍需解释的旧结果和兼容接口；采用版本/适配/迁移解决冲突，不为了旧测试保留错误新行为。进度以实施台账为准，勿从P00重做；已完成阶段的范围缺口按§20.4补验。

日期：2026-09-11。状态：设计内部复审稿，可按任务开发预览版；未实施、未完成算法效果验收。

2026-09-11追加：第17章为数据膨胀专项审计与增量存储实施合同，优先于前文“旧库清理后置”和“全部旧物理表保持不动”的笼统约定。先阻止新增重复，再无损归并已有重复；清理仅在实施阶段完成核验后执行，本轮不修改或删除数据库/数据文件。

实施入口：**先读第18章，严格按P00→P11执行其中的小任务**。第18章统一替代第13章、第17.11节零散U/O/S编号的执行顺序；第3–17章仍是字段、算法和存储的技术规范。没有前置验收证据，不得仅凭“代码已写”跳到下一个模块。所有任务当前均为计划，本文追加不代表实现已经开始。

**2026-09-12续审更正：实施已推进至P04-02（以实时台账为准），不要从P00重做。先执行第19章R19补漏清单。已复现P04-01规划器的遗漏，P04-02可继续单元开发，但正式绑定/激活前必须关闭R19-02～04；在线接口使用第19章完整清单。前文“所有任务未开始”是原编写时状态，不再用于判断现状。**

## 0. 使用方法与不可漂移边界

本文件完整替代《Astra双线审计与升级方案V2》的实施约定。V2和Sol V1原文保留供追溯，不要求实现者自行拼接三份规则。发生冲突采用本文件；已发布业务合同不原地改义。新增合同统一后缀`PREVIEW_1`，通过效果验收后再版本化。本文写“新增”的文件/表/接口均是计划，不是已有事实。

目标：同时回答“当前谁在强”“谁正在改善、值得提前跟踪”“这些板块分别该看哪些股票”。潜在转强不是低涨幅榜，也不是把旧强势榜前移一名；必须有多成员改善证据、明确等待的确认条件、失效条件和随后结果记录。规则分析是首版实现方式，不冒称已训练的AI预测模型，不输出未经验证的上涨概率。

范围：仅文档审计。本轮不修改业务代码、配置、数据库，不执行扫描。项目正常联网；只使用用户认可的A/B类公开来源，登录/动态签名/会员私有源不纳入核心。所有阶段由执行助手内部审计，不存在外部独立审计角色。不新增灾备工程。TDX输入只读，保留正常事务和原子写入。

实现者不得自行做以下替换：

1. 不得把CURRENT、POTENTIAL和全部板块合成一个“综合分”榜。
2. 不得以RET20/RPS20排序替代本文当日成员榜或潜在成员榜。
3. 不得只在旧candidate_daily内召回；不得把1200条分页后仍叫“优先研究”。
4. 不得把潜在板块直接标为“未来强势已确认”，或用随后上涨修改过去信号。
5. 不得用成员量比中位数替代共同成员总成交额比；不得用20日因子覆盖率当报价覆盖率。
6. 不得删除旧五类结构、矩阵、主线、RPS能力；移除的是错误入口/标签，不是用户数据。
7. 参数、公式、枚举、响应字段、单位、路由、分页语义变更须先在本文件登记变更号、理由和相应验收用例，不能在代码中“自行优化”。

## 1. 本轮重新核查的证据与V2缺口

源码根为`src/`；数据库为`data/database/market_research.duckdb`，本轮只读DESCRIBE。

| ID | 已核查位置 | 事实/影响 | 本规格处理 |
|---|---|---|---|
| F01 | workbench_service/app.py::_overview_strong_sectors | 依据sector_cycle的长期rank取行业/主题各10，不验证当日增强 | §5 CURRENT重算，旧榜移入历史 |
| F02 | workbench_service/association.py::evaluate_relation | ALLOWED_PATTERNS只接受CURRENT_STRENGTH/REACCELERATION；核心门多为RET20 | 潜在关联另建合同，不篡改旧表 |
| F03 | workbench_analysis/sector_cycle.py::calculate相关聚合 | coverage来自有效RET20/成员数，不是有效ret1；RS5缺失时回落RET5；3期比较基于出现日期序列 | 新特征明确报价/历史覆盖和主交易日历，禁止静默混用 |
| F04 | sector_cycle_daily实际模式 | 正式sector_amount_vs_prior20和旧amount_vs_prior20并存；有共同成员差值列 | 明确列映射和质量条件 |
| F05 | stock_technical_daily/stock_strength_daily | 已有MA/量额/RPS；没有潜在信号、板块角色、提前观察状态 | 复用基础，新加紧凑研究表 |
| F06 | stock_sector_associations_daily；019迁移 | 旧关联按slice/stock/sector/date存，包含拒绝关系 | 不再新存全市场全部拒绝关系；按需解释 |
| F07 | static/v2/router.js、app.js、api.js | 已有6个主路由、请求取消、详情modal；热榜cache:false已有 | 保留壳，不推倒重造；新路由复用取消机制 |
| F08 | app.py::request_scope/do_GET；online_hot_rank.py | 网络等待与全局DB锁耦合；分页/补行情存在问题 | U01先处理，不让在线拖住本地 |
| F09 | 024_m14_online.sql和m14_runtime_capabilities_v1.json | source/batch表已有；行情正式能力NOT_VERIFIED，热榜DIRECT | 不把报价“存在代码”说成全市场实时可用 |
| F10 | forward/evaluation.py | 现有五类结构描述性前瞻统计，非板块预测模型 | 借鉴绑定结果方法，新增独立板块评估，不改原合同 |

V2最大缺口：只细化了“当前”，没有独立POTENTIAL资格/状态/成果验证；没规定各板块的两类成员；泛称coverage、RPS改善易直接读错列；未冻结每个API所绑定的日期和角色。本文件优先解决这些问题。

本轮未复算所有股票、未测试新策略盈利、未跑浏览器验收。V2中的2026-09-10发布数量仅为前轮证据，不当作此刻数据库最新统计。

## 2. 现有功能逐项去留（不得自行删减）

| 功能 | 决定 | 现有实现/数据 | 精确变化与最终入口 |
|---|---|---|---|
| 首页市场概况 | 保留并拆源 | dashboard、market_cycle_daily | 本地收盘概况+独立在线事件概况；缺在线不影响本地 |
| 首页“强势板块” | 替换算法和组件 | _overview_strong_sectors、sector_cycle_daily | 改双栏CURRENT/POTENTIAL，分别最多6张卡，每卡直接列3只对应股票 |
| 首页“优先研究” | 替换，不删旧池 | candidates、candidate_daily | 两个独立标签：当前触发最多20、提前观察最多20；默认各显示10；旧池入口“全部结构候选” |
| 全板块 | 保留 | sectors、sector_library | 板块研究子页“全部板块”，名称搜索/类型过滤/分页；不默认展示 |
| 板块周期矩阵 | 保留并扩列 | sector_cycle/timeline | 原5/10/20/30日指标不改义，新增双轨信号和失效标记；缺日期留空 |
| 主线周期 | 保留历史合同 | mainline_daily、mainlines | 改标签“中期主线背景”；不得作为CURRENT/POTENTIAL必需资格 |
| 成员留存/龙头更替 | 保留历史视图 | member_state、representative_state | 标签“原结构强成员/历史代表”；新当日领涨成员另列，禁止混用计数 |
| 板块—个股联动 | 重做操作，不删能力 | linkage/history、association | 板块列表→右侧成员；默认角色取决于轨道；关联按钮不要求手填ID |
| 板块属性库/交集并集排除 | 保留并合并操作入口 | sector-library、sector-intersection/query | 名称选择2–4板块，已有集合服务复用；加角色过滤由服务端完成 |
| 五类结构 | 保留算法、改描述 | queues/evidence、structures | “核心观察”在该页改“结构核心”；原等级不映射为今日优先 |
| 新高/RPS/MA/量额 | 保留 | technical、highs、strength | 常用筛选放个股研究工具；被动新高不自动FOCUS也不自动剔除 |
| 个股证据 | 保留内容、改组织 | evidence、stock_insight、modal | 始终弹窗，不展开表格；分入选/风险/板块/技术/在线，X遮罩Esc关闭 |
| 本地涨停/连板/晋级 | V3 移除，V2 历史兼容 | V3 无本地梯队/晋级入口 | 用户裁决 §2.1：仅在线事件，断源明确不可用，不回退本地估算 |
| 最强题材/涨停分布/简图/速览 | 新增/改造在线主视图 | 新事件adapter，已有online基础 | §11逐项定义，来源事件榜与本地研究双轨不混榜 |
| 人气热榜 | 保留并扩榜 | online_hot_rank、THS/EM adapter | 单平台单榜按需；实时无历史，不参与持久化研究选择 |
| 板块精选 | 重定义 | 原排名/在线题材 | 不是第3套榜：即CURRENT/POTENTIAL双轨，可叠在线证据徽标 |
| 数据状态/操作维护 | 保留、不扩建 | data-info/operations | 普通入口靠后；不安排灾备演练、不因维护页未升级阻塞研究页 |
| 每日导出/登录会员/投资日历/外部软件跳转 | 本版不做 | 原采纳取舍 | 不生成任务或依赖 |
| 龙虎榜/新闻原因 | 后置可选 | lh_list/external_evidence能力 | 首版不阻塞；已有源题材说明按源展示，不生成伪造原因 |

### 2.1 用户裁决 V3-UC-20260913-01：V3 移除本地收盘梯队与晋级

用户于 2026-09-13 明确要求 V3 不再展示或调用本地计算的收盘梯队、连板和晋级，统一使用在线涨停事件数据。本裁决优先于上表“保留为本地估算”的旧约定：

- V3 `/v3` 页面移除“收盘梯队与晋级”模块，不再调用本地 `limit_ladder`、`limit_promotion` API。
- V3 市场页以在线涨停事实、来源题材、事件池和在线历史晋级（仅在同源完整事件数据满足合同时）作为唯一涨停入口。
- 旧 `/v2`、旧 API 和历史数据暂时保留兼容，不得在 V3 页面回填或冒充在线事实。
- 在线来源不可用时显示 `UNAVAILABLE`，不得回退到本地估算。

本版不DROP任何既有表，不删除旧API；新首页不再调用candidate_daily作优先清单，也不再调用旧20日代表榜作当日成员榜。旧接口兼容保留，只有新增接口使用新枚举。

## 3. 数据来源与字段绑定

### 3.1 时间和身份

本地正式计算以交易日t收盘为截面，所有窗口含义按主交易日历，不用“上一条记录”补缺日。输入由publication→analysis snapshot→domain slice绑定，不用`MAX(trade_date)`跨切片拼接。持久化研究run只用本地输入；在线数据不改变其身份。

LIVE页面允许在线t + 本地最近收盘d，d通常为t-1；所有本地信号标“截至d收盘”。在线CURRENT当日榜与本地CURRENT收盘榜分开，禁止拿昨天名单配今天价格仍称今天排名。未有足够在线报价时明确“盘中成员榜未覆盖”，仍可看收盘榜。

每个返回字段组含`as_of,source_id,basis,status`；基础类型：收益/宽度/分位DOUBLE比例，价格元，金额元DECIMAL(28,2)，时间ISO8601含时区，日期YYYY-MM-DD，缺失NULL。交易日不得从采集电脑日期猜测。

### 3.2 复用映射和禁止替代

| 新字段/用途 | 实际来源 | 必要校验/禁止替代 |
|---|---|---|
| price_close/ret1/amount | stock_technical_daily.raw_close/quote_ret1/raw_amount；当天显示优先现有已绑定quotes服务同语义值 | 日期一致；复权价不充当交易现价 |
| C、MA、ret5/20 | adj_close、ma5/10/20/60、ret5/20 | 同复权锚；原始日线经过既有adjustment/history_adapter |
| rps5/rps20 | stock_strength_daily.rps5/rps20 | 保留现有全A基准，不在研究池重排 |
| sector中期排名 | sector_cycle_daily.sector_rs20_pct/rank | 仅背景，不能当当日强 |
| quote_coverage | quote_valid_count/total_member_count；须验证同当天A股成员集 | 不读旧coverage（RET20覆盖） |
| amount_sum | 同日有效成员原始amount求和 | 单列amount_coverage，不声称完整金额 |
| amount_A | sector_cycle_daily.sector_amount_vs_prior20 | amount_contract_id匹配正式共同成员合同且质量通过；绝不读旧amount_vs_prior20 |
| amount_delta3 | sector_amount_ratio_delta_3sessions_common | 3交易日共同集合质量通过；不直接减两个不同成员集A |
| b_delta3 | 从t与t-3共同有效成员重算，旧列仅合同/日历一致才复用 | 共同集合覆盖>=.70且>=5只 |
| 正常板块成员 | 发布绑定成员快照+semantic.py/config/sector_semantics.yaml | NORMAL_ATTRIBUTE；近期强势/昨日首板等为标签，只放附加属性 |
| 连续新高 | 既有highs.py close-based窗口 | 严格前N日，不含今天；窗口20/30/60/100保持原义 |
| 外部事件/题材 | §11 adapter，独立source batch | 真实事件与本地推断分列 |
| 实时价格/涨幅/金额 | quotes_capability与eastmoney_quotes的公开来源，开发需实际验证范围 | 当前正式能力NOT_VERIFIED；未验证不得写成已上线 |

A股展示沿用配置沪深北A股，保留ST但标风险；确认退市/B股/新三板/基金等排除。停牌可在全部成员查到，但不进入新成员角色榜。未知上市状态不能当退市。

## 4. 新特征字典与默认参数（工程初值，不是经验定律）

新增`src/workbench_analysis/research_features.py`，合同`RESEARCH_FEATURES_PREVIEW_1`。只做纯计算，不读网络、不写DB。调用方负责绑定输入。

设U_s,t为正常板块当日A股成员，V为所需字段有效子集，n=|U|。未满足所需覆盖的该特征为NULL；不把缺失当false。预测观察严格门要求n>=5，成员报价覆盖>=.70；金额正式门沿用既有>=.80，不降低为.70。

| 字段 | 公式/窗口/边界 |
|---|---|
| m1,b1 | median(ret1_i)；count(ret1_i>0)/有效ret1人数；平盘留在分母 |
| market_m1 | 同日全A有效ret1中位，非板块等权均值 |
| rel1 | m1-market_m1；若全A行情不完整则NULL |
| p1 | 正常板块按同sector_type的rel1升序平均秩/N，N<5为NULL；独立于旧rank |
| q5,q20 | 成员有效rs5/rs20中位后，在同类型正常板块平均秩/N；禁止RS缺失回退RET。历史比较使用同合同且给rank_universe_hash |
| dq5_3 | q5[t]-q5[t-3]；总体变化>10%（交集/并集<.90）时NULL并提示排名总体变化 |
| b_delta3 | 在U_t∩U_t-3且两日ret1都有效的相同股票集合计算b_t-b_t-3；共同集/两个目标成员数最大值>=.70 |
| ma20_width,ma20_delta3 | C>=MA20人数/有效人数；变化同上共同集合、两日MA有效 |
| early_width | 满足§6股票SETUP或RECOVERY条件的成员数/所需字段完整成员数；禁止先截股票20只再算 |
| amount_A | 正式共同成员sum(A_t)/mean(sum(A_u),u=t-20..t-1)，复用sector_amount.py |
| top1_positive_share | max(max(ret1_i,0))/sum(max(ret1_i,0))；分母0为NULL。仅表示上涨贡献集中，非资金集中 |
| positive_count | ret1>0的有效成员数 |
| bias20 | C/MA20-1，MA20>0 |
| sigma20 | 最近20个有效日对数收益总体标准差ddof=0，需要21收盘；缺日NULL |
| extension_z20 | log(C/MA20)/(sigma20*sqrt(20))；sigma=0为NULL |
| EXTENDED | bias20>=.15且extension_z20>=1.5；不是新高或RET20高即命中 |
| dist_high20 | C/max(C[t-20..t-1])-1，严格排除今天 |
| range5,range20 | max(C)/min(C)-1，分别含今天的5/20收盘；非振幅OHLC |
| liquidity20 | median(raw_amount[t-20..t-1])>=2000万元；缺窗UNKNOWN |
| rps5_delta3 | 同股票rps5[t]-rps5[t-3]；总体变化标记同dq5 |

所有阈值存计划新配置`config/research_attention_v3.yaml`，带合同ID；本轮不创建配置。必须冻结浮点比較为未舍入原数值，页面舍入不影响资格；排序降序NULL最后，security_id/sector_id升序兜底。

补充机器判定约定：quality只取READY/PARTIAL/UNAVAILABLE；每个分支用三值逻辑，已知必要条件false即false，没有false但有NULL为UNKNOWN，全部true才true。板块potential_eligible在任一分支true且共用基础通过时true，全部false才false，其余NULL。W已知true具有风险显示优先级，不能被质量未知掩盖。风险过热成员占比=count(EXTENDED=true)/EXTENDED有效人数，risk_coverage=该有效人数/n；feature_coverage按各分支必要字段交集人数/n计算，不能用所有字段取并集。BASE_BUILD的有效SETUP人数指SETUP可判true或false的人数；early_width的分母是SETUP与RECOVERY都可判的人数。分母0均NULL。

日内排名分母包含同板块所有有效报价A股，非仅上涨者。today_rank为ret1降序`RANK`（并列同名次）；TODAY_LEADER资格分位为升序平均秩/N；展示顺序再以金额、ID打破并列，role_rank是连续序号。current_rank/potential_rank也是稳定排序后的连续序号，不能与p1/q5分位混用。

## 5. 板块双轨：当前强势与潜在转强

### 5.1 当前强势 CURRENT

合同`SECTOR_CURRENT_PREVIEW_2_TYPE_SCOPED`，事实判断而非次日预测。CURRENT 的发布范围只包含 `INDUSTRY` 与 `THEME`；`STYLE`、地域及其他工具型集合可以用于背景观察，但不得进入“当前强势”或由其派生的当前关注清单。

基础：NORMAL_ATTRIBUTE、n>=5、quote_coverage>=.70、m1/b1/rel1/p1有效。资格同时满足：m1>0、b1>=.60、rel1>=.003、p1>=.80。必须至少3只上涨，top1_positive_share<=.50；极小样本或单股拉动只进入全部板块并提示，不能凑卡片。

CURRENT不要求连续2天，也不要求RPS20高；`confirmed_days`只是附加标签。q20>=.80标“中期仍强”，不改变当日资格。排序固定为(p1↓,b1↓,rel1↓,amount_A↓,sector_id↑)。行业与概念分别计算p1；综合展示按各类分位排序并标类型，禁止混原始名次。

CURRENT 与今日总览的板块成员详情使用当前发布绑定的 technical/strength 结果，按 `ret1↓, raw_amount↓, security_id↑` 排序。有效报价成员的前20%（向上取整）标“今日领涨”，后20%标“低涨幅”，其余标“中位军”；标签只描述板块内当日位置，不替代 `CURRENT_RESEARCH` 等研究角色。页面至少展示最新价、当日涨幅、成交额、20日涨幅和研究角色，行情缺失行排在末尾并显式标记。

CURRENT_FOCUS 只接收 CURRENT 板块中满足 BREAKOUT 或 RECOVERY 且结构、位置、过热门均通过的 `CURRENT_RESEARCH` 成员。清单总上限和单板块上限必须读取 `display_limits.focus_max` 与 `display_limits.focus_per_sector_max`，禁止在代码中另设更小的隐藏截断；达到显示上限时接口必须返回完整 eligible total。

confirmed_days从已绑定的逐交易日CURRENT=true向前连续计数，遇缺日停止并标censored；首次值1只表示本日成立，不声称前面一定未强。CURRENT全市场资格需要同日全A报价参考有效覆盖>=.90，板块类型横截面正常可评板块覆盖>=.70；未达只显示板块表现，不发布强势全榜。p1/q5/q20的当日分母与被排除数量必须记录。

“今日转弱”独立W：(m1<0且b1<.35)或(m1<0且b_delta3<=-.20)。昨天CURRENT今天非CURRENT不一定W，可能只是“强度回落”；两者标签不得混淆。W进入风险，放量不能豁免。

### 5.2 潜在转强 POTENTIAL：不是今日榜的尾部

合同`SECTOR_POTENTIAL_PREVIEW_1`，默认观察未来3/5个交易日。CURRENT与POTENTIAL同日互斥，已确认强势移入CURRENT并保留“来自提前观察”标记。

共用基础：正常板块、n>=5；当日/比较成员覆盖通过；不为W；m1>=-.01、ma20_width>=.45；不能有超过半数有效成员同时满足EXTENDED（风险特征有效覆盖>=.70）。未有风险覆盖不判安全，该日潜在资格UNKNOWN。下列分支使用的每个必要输入必须有效，缺一个不算命中。

| 分支 | 必须全部满足 | 含义/等待确认 |
|---|---|---|
| BREADTH_BUILD 扩散改善 | 非CURRENT；dq5_3>=.10；b_delta3>=.10；ma20_delta3>=.05；early_width>=.10且提前观察成员>=2；amount_A>=1.05 | 相对强度、参与面、均线位置同步改善；等待CURRENT或成员触发扩散 |
| BASE_BUILD 蓄势观察 | 非CURRENT；q20>=.40；ma20_width>=.55；ma20_delta3>=0；SETUP成员>=max(2,ceil(.15*有效SETUP人数))；amount_A在[.80,1.30]；b_delta3>=0 | 结构收敛但尚未普遍启动；不是预测资金流入 |
| RECOVERY_BUILD 回暖观察 | 非CURRENT；前10日存在CURRENT且日期已知；之后发生至少1日非CURRENT；今天rel1>0、b_delta3>=.10、ma20_delta3>=0、amount_A>=1.05；RECOVERY或SETUP成员>=2 | 前期强板块改善但未重新达到当前强门 |

分支可多命中，按RECOVERY_BUILD、BREADTH_BUILD、BASE_BUILD优先给主标签，其余附加，不重复列同板块。不输出总“成功率”。排序固定：(命中分支数↓,dq5_3↓,ma20_delta3↓,early_width↓,amount_A↓,sector_id↑)。q20只作分支背景，不作为全局主排序。

首次条件成立立即进入潜在预览列表；连续2日命中标“持续改善”，不能等到已大涨才出现。首页默认最多6，完整潜在列表最多20；不足可0。对行业父子/高度重叠概念仅UI归组，不在算法删掉，保留“同时命中X板块”。

### 5.3 信号生命周期与撤销

每个潜在episode记录first_seen_date、last_qualified_date、branch、age_sessions、end_reason。最长跟踪5交易日：

- CURRENT成立→CONFIRMED，记录确认日；不再出现在潜在主列表。
- W成立、ma20_width<.35、或风险覆盖完整且过热成员>一半→INVALIDATED，当日移出并给理由。
- 条件不再满足且无硬失效→MONITORING（最多1个有效交易日），显示“改善暂停”，排序末尾；第二日仍不满足→CONDITION_LOST。
- 第5日结束仍未CURRENT→EXPIRED；不能每天重置期限。至少连续2个有效日完全不命中后再从false→true建立新episode。
- 数据缺失→DATA_GAP，不当失效、不虚增连续天数；交易日年龄仍推进。评估结果不可据缺失记失败。

完整CURRENT资格评估先于潜在分支；第一次出现便已CURRENT的对象不是“成功提前发现”。RECOVERY_BUILD历史不足时为UNKNOWN，但其他分支输入完整仍可执行。

### 5.4 LIVE的边界和正向用途

在线全板块成员报价覆盖足够时，依§5.1重算`live_current`，加入未复权真实当日ret1即可，不需改本地RPS。在线只抓用户点击的板块，可生成该板块当日成员榜；不足以生成全市场p1时只能叫“该板块盘中表现”，不能冒充全市场强势排名。

潜在轨道首版以收盘模型为主，盘中叠“今天已增强/暂未确认/今日转弱”。在线事件只作观察证据，不为了盘中可用而混算昨日均线和不同基准现价。用户仍能看到提前观察名单今天的实际表现；不需要等待第二天收盘才看价格。

## 6. 股票角色：板块中的当日领涨与提前观察必须分开

新增`stock_attention.py`纯函数。输入全A必要基础，不依赖旧candidate池；板块计算需要这些特征，因此先计算股票基础信号，后聚合板块，最后分配成员角色。禁止“股票需要板块信号、板块又需要筛后股票”循环。

### 6.1 基础股票信号（与板块无关）

| 信号 | 固定条件 | 用途 |
|---|---|---|
| BREAKOUT | liquidity通过；C>前20日最高收盘；C>=MA20；amount_vs_prior20>=1.20；位置字段完整且非EXTENDED | 当前可研究触发 |
| SETUP | liquidity通过；.98<=C/MA20<=1.08；MA20[t]>=MA20[t-3]；dist_high20在[-.06,0]；range5<=.6*range20且range20>0；rps5_delta3>=.05；位置完整非EXTENDED | 未突破的收敛/改善观察，不要求今天涨 |
| RECOVERY | liquidity通过；MA20[t]>=MA20[t-3]；C[t-1]<=MA5[t-1]且C[t]>MA5[t]；C>=.98MA20；rps5_delta3>0；amount_vs_prior20>=1.05；非EXTENDED | 短期恢复，不宣称首次回撤 |
| TREND_BACKGROUND | C>=MA20、MA20[t]>MA20[t-5]、RPS20>=.70 | 仅趋势背景，不独立进入重点 |
| STRUCTURE_BREAK | C<.98MA20连续2个有效交易日 | 触发失效，单日只警示 |

风险缺失只影响“研究资格”，不妨碍事实领涨榜。跳空/冲高回落需要实际同基准OHLC；首版不输出未定义的“量价背离/脉冲/出货”风险名称。

### 6.2 板块成员角色

| role | 资格 | 排序 | 数量及风险 |
|---|---|---|---|
| TODAY_LEADER 当日领涨 | 当天真实有效报价、ret1>0、ret1在本板块有效报价平均秩分位>=.80；不要求RPS20 | ret1↓,amount↓,security_id↑ | 默认前5、分页全部；高位/涨停照列并标风险，这是事实榜 |
| CURRENT_RESEARCH 当前触发 | CURRENT板块内BREAKOUT或RECOVERY，非STRUCTURE_BREAK；位置完整不过热 | BREAKOUT优先,amount_vs_prior20↓,rps5_delta3↓,id↑ | 每板块前5预览；不拿最涨替代 |
| EARLY_WATCH 提前观察 | POTENTIAL板块内SETUP或RECOVERY；非STRUCTURE_BREAK；位置完整不过热 | SETUP优先,rps5_delta3↓,abs(bias20)↑,liquidity20金额↓,id↑ | 每板块前5预览；允许0且解释 |
| ALL_MEMBERS 全部成员 | 发布绑定A股成员 | ret1↓缺失末尾,id↑，允许明确选择旧20日排序 | 分页50，保留停牌/未知价格行 |

CURRENT板块卡：直接显示TODAY_LEADER前3，并给“研究触发N只”按钮。进入板块默认当日领涨tab。POTENTIAL卡：直接显示EARLY_WATCH前3，进入默认提前观察tab，旁边始终有当日领涨tab。不能只有板块名看不到股票。

一只股票可在多个真实所属板块出现，这是合法多对多；全局清单只去重一次。每行返回板块A股总数、角色合格数、quote_valid_count、当天涨幅名次和旧20日名次（后者折叠），严禁名次空白却不给不可用原因。

### 6.3 全局两条研究清单

CURRENT_FOCUS：所有CURRENT_RESEARCH候选，最多20；EARLY_FOCUS：所有EARLY_WATCH候选，最多20；默认各10展示。不能共用20个名额让当前涨幅挤掉提前观察。个股可来自多个板块但同一清单一行；若两条都合格，主入口列CURRENT_FOCUS，提前轨道保留“已触发”历史而不占当前提前名额。

先按对应板块轨道排序，再按角色排序，全局去重；每主板块最多3只；剩余全部进入对应页“更多候选”，不凑满。无板块但BREAKOUT/RECOVERY有效的股票进入独立“个体触发”tab最多10，不伪造所属板块。

个股每行必须包含`selection_reason`（最多3条）、`waiting_for`、`invalid_if`和`signal_date`。SETUP默认等待BREAKOUT或RECOVERY；STRUCTURE_BREAK/EXTENDED/所属潜在episode硬失效时退出；条件暂停最多1个有效日，再不满足移出。价格阈值以信号时基准保存说明，后续新日期新证据不能覆盖旧说明。

转入CURRENT_FOCUS仍要求所属板块成为CURRENT并满足CURRENT_RESEARCH；潜在板块内股票已RECOVERY时，waiting_for写“板块当前强势确认”，不得等待一个当天已经满足的RECOVERY条件。MONITORING板块仍在潜在页末尾显示“改善暂停”，不新增EARLY_FOCUS；既有观察股票最多保留该1个暂停日，使用previous_state=PAUSED明确标记，下一日未恢复即退出。股票角色事实按当天重新计算，不把昨日角色保存为今日命中。

## 7. 板块关联算法的新旧边界

新增`workbench_service/research_association.py`供新页面使用，旧association.py和strength_association.py的旧合同保留兼容，不把新POTENTIAL枚举塞进旧表。

成员关系是硬前提：发布快照确认为成员才关联。默认主关联排序：对应轨道合格、对应股票角色合格、剔除目标股票后仍有共同改善支持、板块轨道排序、sector_id。取1主+最多2备选。CURRENT与EARLY分别计算主关联，不预设“一级行业最重要”。

共同支持LOO：CURRENT研究要求其他有效成员>=5、其他成员b1>=.55且中位ret1>0；EARLY要求其他有效成员>=5、其他SETUP/RECOVERY成员>=2，并满足b_delta3>=.05或ma20_delta3>=.05。LOO不通过不取消真实成员关系，标“单股/小样本关联”，不得称共振主关联；角色榜仍可显示股票。全局限额无合格主关联时按各股票独立处理，不能全挤成“未知板块”。

不能从共同改善推断“这就是上涨原因”。关联分三栏：真实属性、共同强势/改善依据、来源题材说明。近期强势/昨日首板保留在“行情标签”，不占主/备选关联。

在线映射EXACT需要身份及成员范围依据，不仅是同名；RELATED只展示关联链接，不把来源精选成员与本地全成员混分母。未映射题材保留来源ID，用户无需每日人工映射才能看在线榜。

## 8. 数据库详细改造（只新增，不覆盖旧切片）

迁移目录`src/workbench_db/migrations/`；本轮看到编号024，实施时读取实际清单再分配，不固定冲突编号。注册到既有migrations.py。以下同名V2规划表按本章替代；若实施者发现已建V2表须先做字段差异表，不假定空库。

### 8.1 本地结果表

公用约定：ID/VARCHAR非空，交易日DATE，数值DOUBLE可NULL，金额DECIMAL(28,2)，计数INTEGER，数组JSON非空默认[]。JSON只放短证据/质量码，不塞全历史OHLC。每个表除另注字段外主键均非空。run内日期统一，不重复每行存trade_date。

| 表 | 主键/唯一约束 | 完整必需字段（除PK） |
|---|---|---|
| research_runs | run_id PK；input_key UNIQUE | trade_date DATE、publication_id、snapshot_id、membership_snapshot_id、algorithm_version、parameter_hash、dependency_bindings JSON、history_basis、status、created_at TIMESTAMP；input_key=输入依赖+日期+参数+合同SHA256 |
| research_stock_states | (run_id,security_id) | setup/breakout/recovery/trend_background/structure_break BOOLEAN可空；quality、bias20、sigma20、extension_z20、dist_high20、range5、range20、rps5_delta3、liquidity_median20金额、risk_codes JSON、reason_codes JSON、evidence JSON |
| research_sector_states | (run_id,sector_id) | current_eligible/potential_eligible BOOLEAN可空、potential_branch可空、potential_branches JSON、current_rank/potential_rank INTEGER可空、m1/b1/rel1/p1/q5/q20/dq5_3/b_delta3/ma20_width/ma20_delta3/early_width/amount_A/top1_positive_share DOUBLE、member_count/quote_valid_count/feature_valid_count/early_count/positive_count INTEGER、quote_coverage、feature_coverage、risk_coverage、quality、reason_codes JSON、evidence JSON、input_members_hash、rank_universe_hash |
| research_sector_signal_state | (run_id,sector_id) | episode_id可空、first_seen_date/last_qualified_date/end_date DATE可空、age_sessions/miss_sessions/reset_sessions INTEGER、lifecycle、end_reason可空、prior_run_id可空、history_complete BOOLEAN；保存当前状态小行 |
| research_sector_member_roles | (run_id,sector_id,security_id,role) | role_rank INTEGER、today_rank INTEGER可空、role_reason_codes JSON、evidence JSON；只存前三类合格角色，不复制ALL_MEMBERS或每个拒绝关系 |
| research_shortlist | (run_id,list_type,security_id)；UNIQUE(run_id,list_type,rank) | rank INTEGER、primary_sector_id可空、alternative_sector_ids JSON、selection_reason/waiting_for/invalid_if JSON、previous_state、change_reason；list_type=CURRENT_FOCUS/EARLY_FOCUS/INDIVIDUAL |

索引：sector_states(run_id,current_rank)、(run_id,potential_rank)；roles(run_id,sector_id,role,role_rank)及(run_id,security_id)；shortlist(run_id,list_type,rank)。不为JSON任意创建索引。所有run_id引用有效research_runs；应用层/事务同时校验引用，禁止孤儿行。

股票价格/MA/RPS不再重复存进roles和shortlist；按run绑定的技术切片批量JOIN。source_refs放run依赖和短证据，复用已有价格库。ALL_MEMBERS查询原成员表，不为每个run复制全成员全历史。

sector_states.evidence须包含`valid_counts_by_feature`（SETUP/RECOVERY/风险/q5等有效人数）、`extended_count`、`setup_count`、`recovery_count`、`rank_universe_counts`、`confirmed_days/censored`、`amount_source_column/contract/coverage`、`comparison_dates`及`source_slice_ids`；SQL过滤和排序用显式数值列，不每行解析大JSON。derived amount_sum等显示字段从绑定旧表读取。潜在MONITORING在状态表记录，sector_states.potential_eligible仍表示“当日规则命中”，API02 POTENTIAL展示active episode（QUALIFIED/MONITORING）并分开标识，不能把暂停日篡改为规则通过。

research_stock_states.evidence固定保存信号日C/MA5/MA20/前高/前日MA5、所用比较日期和阈值，用于waiting_for/invalid_if解释；否则后续改动复权锚会让旧说明漂移。research_runs.status只取BUILDING/COMPLETE/FAILED。所有JSON与数组字段写入前按固定schema校验，多余未知业务键拒绝，避免实现者任意塞新指标。

### 8.2 评估结果表（先观察后评估，不污染信号）

新增`research_signal_outcomes`：PK(signal_run_id,sector_id,horizon,eval_version)；字段episode_id、due_date DATE、evaluated_at TIMESTAMP、status(PENDING/OBSERVED/DATA_GAP)、confirmed_date DATE可空、confirmed_within_h BOOLEAN可空、lead_sessions INTEGER可空、member_forward_median DOUBLE可空、member_forward_coverage DOUBLE、evaluation_basis、evidence JSON。horizon仅3/5；历史重建与真实前瞻分开统计。

评估任务只写outcomes，不能UPDATE研究信号。只观察潜在episode的首次记录，重复5天列表不是5个独立成功样本。不把此前信号在未来榜单中“消失”当失败或退市。

### 8.3 在线事件表

复用data_sources/online_fetch_runs/online_batches/online_payloads，热榜禁止进入这些持久化路径。新增：

| 表 | PK | 字段 |
|---|---|---|
| online_event_bundles | bundle_id | trade_date、source_batch_bindings JSON、source_statuses JSON、observed_at TIMESTAMP、coverage JSON；只绑定允许持久化的收盘事件批次 |
| online_pool_entries | (batch_id,pool_type,source_code) | security_id可空、event_state、consecutive_limit_days INTEGER可空、m_days/n_boards INTEGER可空、first_limit_time/last_limit_time TIMESTAMP可空、price/amount/seal_amount金额可空、ret1/turnover DOUBLE可空、quality_codes JSON |
| online_topic_entries | (batch_id,source_topic_id) | name、description可空、source_order INTEGER可空、source_url可空 |
| online_topic_members | (batch_id,source_topic_id,source_code) | security_id可空、is_limit_up BOOLEAN可空、m_days/n_boards可空、reason可空 |
| source_sector_mappings | (mapping_version,source_id,source_sector_id,local_sector_id) | relation_type(EXACT/RELATED)、status、evidence、valid_from DATE、valid_to DATE可空 |

source_code必须带来源市场命名空间防同代码冲突；批次引用来源/版本/日期。UNKNOWN不得自动变0/false。同一日期修订新增batch，不覆盖旧batch；无需设计多级灾备。

盘中事件仅有界内存bundle：TTL120秒、16个/32MiB上限，过期409要求整组刷新；热榜不享受跨请求缓存。收盘事件采集每个来源按日期一次逻辑结果、可显式刷新修订，不要求每分钟永久落库。

## 9. 计算与存储执行顺序

新增`research_builder.py`（协调、写入）和`research_context.py`（读取）分离；GET不得启动全市场构建。

1. 解析已完成Phase0和已发布本地输入；Phase0非FULL_PASS/DEGRADED_PASS不得发起新的scanner，BLOCKED停止相关任务。
2. 从现有technical/strength复用有效切片；缺的基础窗口只补目标日所需，不再把全年所有成员全证据重新物化。
3. 股票基础特征与SETUP/RECOVERY/BREAKOUT→板块特征→CURRENT→POTENTIAL→episode→成员角色→全局清单。此顺序不可倒置。
4. 首次特征温启动至多85个交易日原始输入覆盖MA60、RPS比较及潜在10日观察；按输入需求实际裁减。更长episode/模型另行任务，不能无止境向前补。
5. 事务写当天紧凑结果，最后status=COMPLETE；同input_key已COMPLETE直接复用。失败不切换首页run。修正输入生成新run，不原地改旧输出。
6. 在线页面独立取公开事件/报价，补充字段但不重写本地run；在线断开本地照常。
7. 每日只增量写当天；历史评估补算按用户选择的小窗口执行，不成为每日强制依赖。

上限是研究结果，不是市场参考总体：全A日收益/RPS和板块宽度仍需要全市场低成本计算；不能为了减少量把宽度分母缩成20只。记录read_rows/write_rows/reused_rows/wall_ms，专项排查重复；本版不清旧库。

## 10. 接口合同（API版本与算法版本分开）

新增路径统一`/api/v3`，继续由现有app.py路由接入，但SQL/算法放新服务模块。旧API返回字段不改义。

### 10.1 公共请求/响应

`GET /api/v3/research/context?publication_id=...&trade_date=...&mode=CLOSE|LIVE`：选择已有COMPLETE run；返回`context_id,run_id,mode,local_date,online_date,publication_id,snapshot_id,algorithm_version,capabilities`。找不到返回200 capabilities.research=NOT_BUILT，items为空；不自动启动计算。context_id为这些字段规范化摘要，不是任意UUID可跨日期复用。

其余研究GET必须带context_id；本地分页page>=1，page_size默认20最大50；非法值400，未知ID404，已过期/模式冲突409，单数据源失败由子结果status表达。所有列表包含`total_eligible,returned_count,total,page,page_size,has_more,items,context`；total为该查询完整合格数（非当前页长度），首页cap另外返回display_limit。没有资格和未有数据用EMPTY/UNAVAILABLE区分。

### 10.2 逐接口定义

| ID/方法 | 参数（均含context_id，除另注） | 返回数据/服务读取 | 页面 |
|---|---|---|---|
| API01 GET /api/v3/home/local | 无额外参数 | market本地摘要、current_sectors<=6、potential_sectors<=6、current_focus<=10、early_focus<=10；卡片嵌3只股票 | 首页，不含在线等待 |
| API02 GET /api/v3/research/sectors | track=CURRENT/POTENTIAL/WEAK/ALL，type、q、page/page_size | sector_states JOIN名称，默认各轨道固定排序；ALL保留全部正常板块 | 板块左列 |
| API03 GET /api/v3/research/sectors/{id} | 无 | SectorDetail：所有轨道状态、基础、理由、失效、member_counts、前5只对应角色 | 板块右侧摘要 |
| API04 GET /api/v3/research/sectors/{id}/members | role四枚举、page、page_size、q；ALL允许sort=RET1/RET20/AMOUNT | roles或原成员JOIN技术；返回所有统计分母和角色排名 | 右侧成员表 |
| API05 GET /api/v3/research/shortlist | list_type三枚举、page/page_size | shortlist JOIN技术+状态+主备选板块 | 个股双轨 |
| API06 GET /api/v3/research/stocks/{id} | origin_sector_id可空 | 基础信号、所属每板块状态、主备选、选入/未入原因 | 个股modal概览 |
| API07 GET /api/v3/research/stocks/{id}/evidence | section=selection/risk/sectors/technical | 只取该节；技术深历史复用原stock_insight/technical_history的绑定能力 | modal证据 |
| API08 GET /api/v3/research/sectors/{id}/signals | days=5/10/20/30 | 日期、两轨资格、episode、结果状态；缺日占位NULL | 矩阵/详情信号历史 |
| API09 GET /api/v3/events/context | 不需本地context；date、mode | event_bundle_id、来源状态、过期时间 | 事件页首请求 |
| API10 GET /api/v3/events/{overview,topics,ladder,pools} | event_bundle_id、pool_type、page/page_size | 固定bundle标准化事件，不混批 | 在线4子页 |
| API11 GET /api/v3/events/topics/{id}/members | event_bundle_id、height可空、page/page_size | 来源题材成员及事件，不用本地全板块假装来源成员 | 分布下钻 |
| API12 GET /api/v3/hot-rankings | 独立source、list_type、page/page_size；无历史日期 | source_rank/rank_change、quote组、status、upstream_total可NULL | 热度观察 |
| API13 GET /api/v3/search/suggest | context_id、q长度2..40、entity_type | <=10名称/代码候选；服务端限制 | 属性/交集选择 |
| API14 POST /api/sector-intersection/query | 旧参数兼容；新增可选research_context_id/member_role | 先原集合计算，再新角色筛选，再总数和分页；不传新参数保持原语义 | 板块交集 |
| API15 GET /api/v3/live/sectors/{id}/members | context_id、quote_bundle_id可选、page/page_size | 仅验证后启用；拉本板块完整有效报价排序后分页、覆盖不足提示；非全市场榜 | 盘中成员 |

API15预算最大一次一个板块，服务端并发<=4、成员批量查询，不能一股票一HTTP。来源不支持完整成员批量时该能力UNAVAILABLE，不“只抓前50就算榜”。quote_bundle仅短时内存，分页固定一次采样；日期和时间范围返回。

API15报价缓存沿用事件预算规则（TTL120秒、16个/32MiB）但使用独立命名空间，不与热榜缓存混用；返`quote_bundle_id,expires_at,quote_coverage,oldest_quote_at,newest_quote_at`。quote_coverage<.70或来源时间无法判断则排名不可用；时间跨度超过120秒的样本显示ASYNC_QUOTES，不称同一时刻完整排名。返回本板块TODAY_LEADER事实榜不等于通过全市场CURRENT资格。

### 10.3 必需DTO字段

SectorCard=`sector_id,name,type,track,branch,lifecycle,signal_date,m1,b1,rel1,amount_sum,amount_coverage,amount_A,quote_coverage,member_count,today_leader_count,early_watch_count,reasons,waiting_for,invalid_if,preview_members,quote_as_of,local_as_of`。

MemberRow=`security_id,name,price,ret1,amount,quote_as_of,quote_source,role,role_rank,today_rank,rank_denominator,total_member_count,rps20,bias20,risk_codes,selection_reason,waiting_for,invalid_if,primary_sector,other_sector_count`。

Reasons每项=`code,label,observed,operator,threshold,unit,as_of`；未用到的值NULL。例如`BREADTH_IMPROVING,上涨占比改善,0.12,>=,0.10,RATIO,t`。前端不解析英文字符串拼业务规则，中文label由catalog.py版本映射。

排序字段直接列枚举白名单，SQL参数化；取名等源文本textContent。API06/07不得查询未来结果表来解释当时选入原因。

### 10.4 构建入口与模块函数边界

复用现有POST /api/jobs鉴权/任务状态机制，新job_type=`BUILD_RESEARCH_V3`，body=`publication_id,trade_date,algorithm_version`；参数版本从已冻结配置解析，不接受前端随意传公式。返回202及job_id；运行中相同input_key返回同job_id，不重复任务；完成后通过context读取。离线开发CLI可以调用同builder，不另造算法实现。历史回放另用`EVALUATE_RESEARCH_V3`，指定from/to且默认最多30输出日，禁止点击首页触发。

固定模块职责：`research_features.calculate(stock_inputs,membership,calendar,contracts)`→股票/板块基础特征；`stock_attention.classify(features,params)`→基础信号；`sector_attention.classify(sector_features,stock_signals,prior_states,params)`→轨道资格；`sector_signal_state.advance(previous,current,calendar)`→episode；`research_members.assign(sector_states,stock_signals,membership)`→roles；`research_association.select(roles,features)`→主备选；`research_builder.build(bound_context)`→完整run。这些为计划函数签名，允许容器类型实现细节不同，但输入依赖方向不得改变。特征函数内不能调用研究角色函数；提前宽度使用原始股票信号，不使用筛后EARLY_FOCUS。

GET所有读取只消费COMPLETE run；按需解释可运行单对象纯函数，不能暗中触发全量构建。U06负责接入job_type和已有状态/错误格式，U08负责读取，不新建另一套任务系统。

`research_features.calculate`中的板块基础不含early_width；early_width由sector_attention接收全部stock_signals后聚合，随后才判POTENTIAL。这样不产生循环依赖。

### 10.5 响应样例（合成数据，仅校验协议）

```json
{
  "context": {"context_id":"fixture-context","run_id":"fixture-run","mode":"CLOSE","local_date":"2026-09-10"},
  "status":"READY",
  "total_eligible":2,"total":2,"returned_count":1,"page":1,"page_size":1,"has_more":true,
  "items":[{
    "sector_id":"FIXTURE.SECTOR.A","name":"演示板块A","track":"POTENTIAL",
    "branch":"BREADTH_BUILD","lifecycle":"QUALIFIED","signal_date":"2026-09-10",
    "m1":0.002,"b1":0.54,"rel1":0.003,"amount_A":1.1,"quote_coverage":1.0,
    "member_count":20,"today_leader_count":4,"early_watch_count":3,
    "reasons":[{"code":"BREADTH_IMPROVING","label":"上涨占比改善","observed":0.12,"operator":">=","threshold":0.10,"unit":"RATIO","as_of":"2026-09-10"}],
    "waiting_for":["达到当前强势门槛或观察成员触发扩散"],
    "invalid_if":["成员上涨占比低于35%且整体下跌"],
    "preview_members":[{"security_id":"FIXTURE.STOCK.A","name":"演示股票A","role":"EARLY_WATCH","role_rank":1,"price":10.0,"ret1":-0.001,"amount":50000000,"risk_codes":[]}]
  }]
}
```

示例省略的DTO字段生产仍需按§10.3补齐或NULL；fixture代码不得进入生产证券表。潜在股票今天可微跌，不能因ret1不是正数前端自行隐藏；当日领涨股则必须ret1>0。

## 11. 在线功能逐模块规格及来源验证边界

项目联网是正常功能，不是例外许可。免费公开网页接口不等于永久稳定授权；开发只验证用户认可的A/B类，不接私有会员接口。

本轮查阅[同花顺热榜页面](https://eq.10jqka.com.cn/webpage/ths-hot-list/index.html?showStatusBar=true)只返回需JavaScript的页面提示；[东方财富人气榜页面](https://guba.eastmoney.com/rank/)可读且说明排名有更新间隔及完整性限制。这只证明公开页面入口存在，不证明以下全部数据端点当前可用。其余路径来源于本地adapter/龙字诀静态证据；未验证项必须在O01封样后启用，不得猜字段直接上线。

### 11.1 来源注册与适配器

| 数据集 | 现有/计划来源 | 映射规则及任务 |
|---|---|---|
| THS_HOT_STOCK | 现有ths_hot_rank.py：dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock | type=hour/day × list_type=normal/skyrocket，stock_type=a；code/name/order→代码名称平台名次，market明确映射，不凭6位数字推市场 |
| EM_HOT_STOCK | 现有eastmoney_hot_rank.py：gbcdn.dfcfw.com/rank/popularityList.js | 复用既有公开页面解码，不增加鉴权绕过；平台排名独立，解码失效仅此源不可用 |
| SOURCE_TOPICS | 新xuangubao_events.py：flash-api.xuangubao.cn/api/surge_stock/plates 与 stocks | plates日期北京时间零点Unix秒，stocks日期YYYYMMDD；fields按名字对齐数组，题材ID多对多；精确字段/日期历史支持在O01实际验证 |
| LIMIT_POOL | 新ths_events.py：data.10jqka.com.cn/dataapi/limit_up/limit_up_pool | date/page/limit/field/filter/order真实参数经样本确认；不自动获取签名；涨停/跌停/炸板分池能力分别注册 |
 | ADDITIONAL_POOL | `https://flash-api.xuangubao.cn/api/pool/detail` | 七池及请求模板已恢复至§19.3；已有静态和旧探测记录，P09-01负责当前复测，不从零猜测 |
| LIVE_QUOTES | 现有eastmoney_quotes.py/quotes_capability.py | 开发明确price/ret1/amount单位、批量上限、SH/SZ/BJ覆盖、时间，验证后打开对应capability，不全局开启一切源 |
| THS板块/话题榜 | hot_list/v1/plate 与 topic静态候选 | 与股票榜分开DTO；同样O01逐数据集确认，不因股票榜可用推定全可用 |

O01产物每数据集一份字段映射表：完整URL模板、方法、query默认值、请求头必要性、公开页面出处、响应成功码、记录路径、源字段→DTO、单位、时区、市场范围、分页结束、空列表含义、最大页数。非热榜可保存少量测试样本；热榜只保存人工编造fixture和字段schema，不能保存真实raw/行/batch/历史。

字段映射不明时只阻塞该数据集，不阻塞双轨本地开发。JSON业务失败虽HTTP200仍为SOURCE_ERROR；禁止返回空数组伪装成功。单源预算8秒、总12秒、最大并发4；缺页TRUNCATED而非总量完整。

### 11.2 最强题材

数据SOURCE_TOPICS；来源自有顺序→source_order，不逆向宣称服务端选择算法已知。页面两个tab“来源题材榜”“本地双轨关联”；前者保持原榜，后者EXACT/RELATED映射后展示对应本地状态，禁止把本地分数改写源排名。

题材行：名称、源排名、涨停成员数、来源成员数、最高明确连续板、来源更新时间、关联本地板块；点击进入API11。成员计数按规范security_id或带市场source_code去重；映射未知仍可看源数据。

### 11.3 涨停分布

在同bundle中按来源题材→连续板高度分桶。一个股属于多题材可多处显示，但全市场总数去重。必须同时显示“唯一证券数”和“题材归属次数”，不能把后者叫涨停家数。9天5板单独M天N板标签，连续字段未知进入“高度未明”，不塞5连板。

来源题材成员可能包括非涨停；只有明确is_limit_up=true才进入涨停分布，其他进入相关成员。数据不全时只称“来源覆盖分布”，不称全市场。

### 11.4 涨停简图

以明确LIMIT_UP成员为基础，按consecutive_limit_days降序、first_limit_time升序NULL最后、security_id升序。每个高度显示卡片前10，展开分页，不一次几百股全DOM。卡片字段：名称代码、价格、ret1、amount、连续板或M天N板、首次/末次封板、题材、seal_amount（若有）。成交额与封单额绝不混列。

同日源数据冲突保留两个source状态，主源优先级由O01版本表决定；不通过“字段哪个非空用哪个”合成无来源股票。源缺失允许切本地估算页，必须有明显估算标记。

### 11.5 情绪速览

显示涨停家数、跌停家数、明确炸板家数、明确最高连续板、来源封板率；市场涨跌家数/成交额来自完整行情参考总体，不由涨停池推算。封板率仅当涨停池与炸板池口径相同、去重且互斥、覆盖完整时计算N_limit/(N_limit+N_broken)，分母0=NULL。`up_limit=false`不等于炸板。

一次采样没有封板全过程，不做实时炸板时间线。7池未验证可只上已验证卡片，缺项标不可用。历史情绪沿用本地market_cycle；在线只补有真实归档日期，不给本地估算换在线标签。

### 11.6 热榜及在线板块精选

热榜平台分tab，THS四榜分子tab，默认只请求当前一榜；保留平台原名次，过滤非A股后不改平台排名，另给展示序号。总数未知返回NULL，先分页再补本页行情；源upstream分页先依其规则取页，不二次误切导致空页。

不跨HTTP缓存热榜，不落raw/行/batch/候选历史，前端api.js继续cache:false；日志不得带响应正文。热度徽标只在当前页面短暂显示，不参加持久化CURRENT/POTENTIAL资格和评估。板块精选就是§5双轨+在线题材证据，不再生成第三个不明含义综合分。

## 12. 页面布局与操作合同

保留现有6个一级路由：overview首页、sectors板块研究、stocks个股研究、linkage集合筛选、market市场事件、data-info数据状态。不要再新增十个一级菜单；主线/矩阵放板块子页，热榜放market子页。

首页从上到下：市场概况一行→板块双栏→个股双tab。当前板块和潜在板块各默认6张卡，每卡3只股票可点；1440宽双栏，<1100改轨道tab（数据/选择不重置）。首屏本地不等在线，在线概况独立刷新；不得加自动滚动跑马灯。

板块研究子页：当前强势 / 潜在转强 / 周期矩阵 / 中期主线 / 全部板块。当前/潜在采用左侧32%列表+右侧68%成员，左侧不超过20行分页，右侧不套第二个纵向滚动容器；屏幕<1100用列表→详情返回。

右侧固定头：板块名+轨道+截止日期、当日成员表现/上涨占比/金额、3条理由、等待条件/失效条件；下方当日领涨/研究触发/提前观察/全部成员tabs。每次切板块重置成员page=1但保留role偏好；切轨道采用对应默认role，不能沿用无意义空筛选。

表格首屏列：名称代码（同格）、最新或收盘价、当日涨幅、成交额、对应角色名次、留意原因、风险、证据按钮。20日涨幅/RPS/原队列放可展开列设置，不默认挤出姓名/按钮。table布局限定容器宽度；横向滚动只在表内，禁止撑大整页。

金额单位只用元/万/亿/万亿，按绝对值边界1e4/1e8/1e12，默认最多2小数去尾0；舍入跨单位边界需晋升。示例：1.62e9→16.2亿，8.09e9→80.9亿，8.9e7→8900万。tooltip保留原始元值。涨幅默认1小数，宽度显示60%而非0.6。

有真实板块指数行情显示“板块涨幅”；否则列名“成员表现”，解释为“成员涨幅排序后的中间值，代表典型成员，不是板块指数”。旁列上涨占比。不得仅删“成员中位”变成伪造板块指数涨幅。

证据使用现有modal.js居中弹窗，宽min(960px,视口-32px)，高不超85vh，内容内部滚动；X、遮罩、Esc关闭，点击内容不关闭；焦点回按钮，禁止表内展开、href跳转或抽屉叠抽屉。板块选择是页面布局，不与证据弹窗混淆。

路由新增query：track、sector_id、member_role、list_type、list_page、member_page、mode、context_id；现有page/subpage/publication_id/basis兼容。现有security_id专用于股票modal。退回恢复轨道/板块/滚动；修改发布日期清掉run/context、在线bundle和跨日选择。

请求竞态：沿用beginViewRequest/cancelHiddenViewRequests；每次切板块取消旧请求并校验epoch+context_id，迟到响应不得覆盖新板块。空态必须分别展示“没有符合规则”“输入不足”“来源暂不可用”，不能统一“无数据”。

## 13. 文件级改造任务与测试落点

以下是允许的实现落点，不代表本轮修改。新增测试目录`tests/research_v3/`；旧测试继续运行，不为通过测试篡改旧合同。

| 任务 | 文件/操作 | 必须完成的小任务 | 通过标准 |
|---|---|---|---|
| U00 基线冻结 | 本文+config/research_attention_v3.yaml新增 | 冻结参数、DTO、去留表；记录实际最新迁移/输入 | 不存在“综合分待定”“前端随便排序” |
| U01 服务隔离 | app.py request_scope/do_GET；online_hot_rank.py修改 | 在线前释放DB锁；分页后补行情；源分别成功失败；热榜total修复 | 慢源8秒期间publications本地无8秒阻塞 |
| U02 字段适配 | 新research_features.py；history_adapter复用 | 日期网格、quote覆盖、正式A、RS5无RET回退、均线/收敛特征 | 人工公式对照、缺日/换成员/零波动 |
| U03 股票基础 | 新stock_attention.py | §6.1五信号与原因；不看板块结果、不依旧candidate | SETUP、突破、恢复正反各例 |
| U04 板块双轨 | 新sector_attention.py | §5.1/5.2、互斥、单股效应、稳定排序 | 牛市普涨不全强、潜在非尾部榜 |
| U05 序列 | 新sector_signal_state.py | 初见/暂停/确认/失效/过期/重置、日期截断 | 5日未确认过期、不每天重置 |
| U06 存储 | 新迁移+research_builder.py | §8紧凑表、同input_key复用、依赖绑定、事务 | 同输入重跑0新增，旧slice不变 |
| U07 成员关联 | 新research_association.py、research_members.py | 四role、LOO主备选、全局双清单、统计分母 | 当日赢家非RET20赢家；潜在有提前成员 |
| U08 API | 新research_context.py/research_queries.py，app.py加路由 | API01–08/13/14，参数白名单，schema及错误语义 | ID日期错配拒绝；总数先筛再分页 |
| U09 UI第一切片 | v2/index.html/app.js/styles.css/router.js/api.js修改 | 首页双栏→点卡成员→股票modal→返回；人工样例先接 | 页面能早看效果，不能等全部模块结束 |
| O01 公共源验证 | workbench_online源adapter/config registry | §11.1每源映射/权限类别/分页/单位/空态；热榜仅合成fixture | 有实际来源证据才启该capability |
| O02 事件标准化 | 新events.py/ths_events.py/xuangubao_events.py+事件迁移 | batch/bundle、池/题材映射去重、连续板区分 | 9天5板不算5连板、源冲突可见 |
| O03 在线UI | market子页+API09–12 | 最强题材/分布/简图/速览、单榜热度、失败部分显示 | 在线正常使用且不阻塞本地 |
| O04 盘中联动 | quotes_capability、live_sector_members.py新增、API15 | 按板块完整批量报价、覆盖、固定采样分页、当日赢家 | 只抓前50不得声称完整榜；昨日名单有日期 |
| U10 信号评估 | 新sector_signal_evaluation.py及outcomes迁移 | §14标签/基线/窗口/缺失/历史成员偏差 | 未来信息不进入输入，能审阅失败样本 |
| U11 旧入口整合 | dashboard/overview、mainlines/technical/linkage前端 | 逐项执行§2；保留旧API/原结构历史 | 去留矩阵逐项截图验收，不只单测 |
| U12 内部终验 | 本文验收记录+缺陷表 | §15全用例、性能、实际清单、参数敏感性 | 不满足效果则仍PREVIEW，不伪称预测完成 |

依赖：U00→U01；U00→U02→U03→U04→U05；U06的表迁移可在U02后先做，正式builder需U05/U07；U04→U07→U08→U09；O01可与U02并行，O02→O03必须已过U01；O04依赖O01报价验证和U07；U06→U10；全部可用模块→U11/U12。

U09先用明确标“演示数据”的合成fixture验证布局，随后接真实run验收，不能把演示图当真实算法通过。在线主功能不等本地潜在评估完成才可用，潜在预览不等全部外部源可用才展示。

## 14. “提前发现”的验证方式，不能只证明代码能跑

### 14.1 目标与结果

信号日t收盘冻结POTENTIAL。目标一：t+1..t+3或t+5首次满足同合同CURRENT，分别记确认日期与lead_sessions；信号日已CURRENT的对象不进入提前样本。目标二：独立记录t时成员在t+3/t+5的复权收盘收益中位（固定t成员集，覆盖>=.70），避免只用自定义CURRENT证明自身有效。此收益是诊断，不是交易回测，不计为可成交盈利。

同episode只计首次信号；按到期日入统计。缺未来日期/停牌/成员依据不明标DATA_GAP，披露数量而非全删。历史成员用当前归属回看为RECONSTRUCTED，只能调试，不冒充真实当时可知效果。

### 14.2 基线与验证门

至少比较：同日同类型非CURRENT合格总体；旧q20排名靠前但非CURRENT的等量名单；非CURRENT中按单一dq5_3排名的等量名单。候选和基线使用同一天、同成员口径、相同展示数量。记录3/5日确认比例、提前天数中位、覆盖率、失效比例、名单日换手、固定成员后续收益分布。

先冻结一组参数再用后续日期验证；不能看完整未来再挑“最合适阈值”。预览功能验收需30个合成/真实正反例及至少5个连续实际运行日；这只证明可用。效果升级至少20个不同信号日、50个独立episode且公开数据覆盖不足情况；仅为最低报告门，不保证统计可靠。记录按日期成组的不确定性区间，不把同日几十个高度重叠概念当几十个独立证据。

若尚无足够真实前瞻数据，页面明确“规则观察·效果验证中”，仍允许用户使用，但不得写“AI已证实优于涨幅榜”。若未优于简单基线，保留原结果和失败样例，修改规则版本后继续观察，不能删掉失败样本再称通过。

### 14.3 AI在后续的作用

第一版价值来自明确的提前信号和追踪，不来自调用大模型改写涨幅排名。AI可先辅助解释证据和发现失效模式；任何生成文字不得增加不存在事实。后续若用户选择训练模型，应另定时间外验证/特征合同/版本和数据许可，不把训练任务暗塞本版，也不使联网LLM成为打开页面的前置条件。

## 15. 内部验收清单与防漂移检查

| 用例 | 必须结果 |
|---|---|
| 板块RET20排名第1，今天m=-2%、b=.2、放量 | 不在CURRENT/POTENTIAL，显示今日转弱 |
| 市场全体涨，某板块m>0但rel1不足 | 不因普涨自动称最强 |
| q20低但dq5、宽度、MA改善和SETUP成员齐备 | 可进入BREADTH_BUILD，不被长期榜否决 |
| 只有一只涨停，其余弱 | 单股效应，不强行推潜在板块 |
| 非CURRENT、稳定均线和收敛股票增加 | BASE_BUILD可命中，不要求已经突破 |
| 股票连续涨15天且今天跌，另一股票今天领涨 | 当日榜优先今日领涨；旧RET20名次另列 |
| 当日最高涨股票EXTENDED | TODAY_LEADER保留风险，CURRENT_RESEARCH不入 |
| 潜在板块没有任何EARLY_WATCH | 卡片0并说明；不能拿RET20第一补位 |
| 同股多个板块，一个弱一个改善 | 逐关系解释，主关联不固定一级行业 |
| quote有效90%、RET20有效50% | 当日报价质量不误判50%；历史特征另判断 |
| RS5缺失但RET5有值 | q5必要输入未知，不假RS5 |
| t-3缺日但有更早记录 | 不拿前三条记录冒充3交易日前 |
| A正式字段缺失，旧量比中位2.0 | 不以2.0冒充正式A |
| 潜在第2日CURRENT | 确认并移轨，保留首次信号；不回填t已强 |
| 潜在连续5日未确认 | EXPIRED，不第6天自动变全新候选 |
| t信号看完t+5结果 | 信号表/名单/解释哈希不变 |
| 收盘名单d，盘中行情t | 日期分组可见，t当日成员排序独立 |
| 点击A板块后立刻B，A请求迟到 | 仍显示B；返回保留列表位置 |
| 证据点开/关闭 | 表格行高不变，X/遮罩/Esc都关闭 |
| 合格板块2个、股票7只 | 展示2/7，不凑6/20 |
| 五类结构/新高/交集老入口 | 功能仍可达，旧API语义不变 |
| 单源超时、热榜翻页 | 本地可用；另一源可用；真实热榜零持久化 |
| 总数100，页长20 | total=100、returned_count=20，不误报20 |

性能测量：记录实际硬件/DB大小，暖态本地API P95<=1.5秒（每类至少30次）；首屏本地JSON<=200KiB；普通表页<=50行；在线总预算12秒；UI切轨不触发全市场新构建。冷启动单列报告，不通过只测缓存命中隐藏慢查询。

每阶段执行助手内部记录：任务ID→改动文件→输入/合同→自动测试→实际界面或查询证据→遗留问题→下一依赖。跨域AUD-LOCAL/PERF/DATA/STORAGE仍分别跟踪，不要求外部签字，不扩建灾备。

## 16. 本次复审结论与后续实施起点

V2保留历史参考，但不能再仅按其宽泛任务实现。本版新增可独立执行的潜在板块三分支、当日/提前两类成员、固定成员角色排名、生命周期和效果观察；逐项冻结功能去留、字段、表、接口、文件和验收。

尚不能诚实承诺的两件事：潜在算法已经优于简单基线、所有外部数据接口目前均免费可用。前者由U10/U12验证，后者由O01逐源验证；都不能由实现者自行假设。其余已明确部分可从U00/U01开始实施，不必重新等待总体方案讨论。

本次文档新增，不表示任何代码或数据库已经变更。原V2 SHA256：78056C1553D3F4E2945F33B544B3F1F930F8416AE83337C8B6DB1ED668AD857C。

### 阶段起步的最小确定性验算包

以下均为合成特征夹具，非真实行情或效果证据；未列出的共用质量门默认满足。U02另需从原始逐股输入推导这些聚合值，不能只测试分类函数。

| 夹具 | 指定值 | 预期 |
|---|---|---|
| S_CURRENT | m1=.02,b1=.75,rel1=.01,p1=.90,positive_count=15,n=20,top1=.12 | CURRENT；POTENTIAL=false |
| S_BUILD | m1=.002,b1=.54,ma20_width=.60,dq5_3=.12,b_delta3=.12,ma20_delta3=.08,early_width=.20,early_count=4,amount_A=1.10；非CURRENT | BREADTH_BUILD命中 |
| S_BASE | m1=0,b1=.50,q20=.50,ma20_width=.60,ma20_delta3=.01,setup_count=4,setup_valid_count=20,A=1.00,b_delta3=.02；dq5_3=0；非CURRENT | BASE_BUILD命中，非BREADTH_BUILD |
| S_FALSE | S_BUILD但b_delta3=-.05,ma20_delta3=-.02且无历史CURRENT | 所有分支false，不因dq5改善单独入潜在 |
| S_NULL | S_BUILD但正式amount_A=NULL且其余分支不成立 | 潜在UNKNOWN，不能把旧量比代入 |
| STOCK_SETUP | C=10,MA20=10,MA20[t-3]=9.95,prior_high20=10.30,range5=.02,range20=.10,rps5_delta3=.08,liquidity=5000万元,风险完整非过热 | SETUP=true；ret1=-.001仍可EARLY_WATCH |
| STOCK_HIGH | 当日ret1=.10、板内分位1.0、bias=.20、z=1.8 | TODAY_LEADER=true，研究角色false |

验收严格比较未舍入值；每个数值阈值增加阈值本身、阈值上下最小差、NULL三类边界用例。快照切换、并列排序、缺日和成员变更再用服务集成测试验证，不由单个分类单测代替。

## 17. 数据膨胀专项审计与增量存储实施合同

### 17.1 专项结论：关系不应每日全量存，但不止关系表一个问题

专项ID=`AUD-STORAGE-02`，合同建议`INCREMENTAL_STORAGE_V3_PREVIEW_1`。本章是V3必做组成部分，不再全部后置。当前量化结论来自本轮只读DuckDB查询和目录字节统计，不是估算一年的增长曲线。

用户的判断成立：行业父子、行业/概念成员关系应按实际变化保存，不应每交易日完整复制。需要保留的是“当时观察到了哪个关系版本”，而非每天再复制七万条边。但当日股价、板块强度、当日成员名次等确实每日变化，不能全部改成一张覆盖写的静态表。

当前同时存在四类问题：关系快照重复、分析结果随切片重复物化、输入解包/历史归档占用、完整库备份占用。不能仅给成员表加增量就宣称解决全部膨胀；也不能只删历史来掩盖每天仍在重复生成。

### 17.2 实测清单与证据边界

| 对象 | 本轮实测 | 结论 |
|---|---|---|
| 主库 | PRAGMA database_size约1.6GiB；6594个256KiB块，5759使用、835空闲 | 有约208.75MiB库内空闲块；物理文件大小不等于有效数据大小 |
| membership_entries | 435472行，6快照、5交易日 | 按日期及完整payload摘要生成快照，包含每日日期等非关系内容 |
| 9月7日成员 | 两个快照均72084条，排序后(sector_id,security_id)SHA256相同 | 关系边重复；名称/来源/payload未证明完全相同，不能整行盲删 |
| 9月8日/9日成员 | 两天各72136条，关系边SHA256相同 | 同一关系集重复存；日期应该移到观测绑定，而非边payload |
| tdx_sector_hierarchy_nodes | 1662行，3版本，各554节点 | 已经版本化，不是当前最大来源；优化摘要依赖即可，不能说它每天全量新增 |
| sector_member_state_daily | 3365740行、5交易日、31切片；去slice后的日期/板块/股票键374014个 | 约9倍键级重复；不同算法/依据可能合法，不能把差额直接算可删行 |
| stock_technical_daily | 278009行、5交易日、31切片；日期/股票键30890个 | 同样约9倍，需检查合同/值/质量及依赖 |
| stock_high_daily | 1112040行；日期/股票/window键123560个 | 约9倍；必须包含4个window维度，不能误报36倍重复 |
| stock_sector_associations_daily | 671568行；日期/股票/板块键298467个 | 旧方案每候选关系存拒绝依据，乘切片后变大；V3新结果应稀疏保存 |
| analysis_slices | 389条，387 DUCKDB、2 PARQUET | 主库分析重复不是简单删除analysis_objects目录可解决 |
| slice内容分组 | technical 31条/12种(date,contract,logical_hash)；high31/8；member_state31/16；structure15/3 | 存在“相同结果摘要、不同切片身份”的归并候选；仍需核实schema/口径，保留不同来源身份 |
| data/input_staging | 5823.6MiB、49642文件 | extracted3620.2MiB/49604文件；packages2093.3MiB/4文件；metadata97.2MiB |
| data/backups | 3305.6MiB/72文件 | 大于主库；本轮未证明都是无用或自动生成，需按catalog查引用和用途 |
| data/.phase1_cache | 910.5MiB/18534文件 | 作为可再生缓存单独限额，不当永久历史 |
| data/normalized | 835.6MiB/1文件 | 全历史规范化资产本身不等于重复；要排查每日全重写成本 |

可复查源码：

- `src/workbench_db/repository.py::_import_market_and_membership`：对当日筛出的完整membership行做logical_digest，并把每行完整payload_json导入membership_entries；payload含date/membership_asof_date及重复板块名称。
- `src/workbench_analysis/hierarchy.py::ensure_hierarchy/_source_digest`：已复用相同version，但摘要包含source_hashes；源文件变动而树未变时可能新建相同语义树。
- `src/workbench_service/slice_coordinator.py::_input_hash/_slice_identity`：identity包含source_bundle/manifest/basis；用于溯源是合理的，但不应强迫相同结果物理复制。
- `src/workbench_analysis/immutable.py::immutable_slice_state`：验证同slice内容，不是跨slice去重器。
- `src/workbench_input/pipeline.py::safe_extract_zip`：完整解包生成文件；`seal_source_bundle`绑定提取路径，不能直接移除所有旧路径。
- `src/workbench_ops/backup.py::create_offline_backup`：每次明确创建会复制完整库；需查调用链，不能由存在方法推断每日任务自动备份。

统计不含TDX原始目录，不对其执行任何写入。目录大小不等于可立即回收大小；本轮没有逐文件内容去重、没有运行压缩迁移，也没有给出未经验证的节省百分比。

### 17.3 数据分类与保存策略：明确什么静态、什么按日

| 数据类别 | 最终物理保存 | 更新时机 | 明确取消 |
|---|---|---|---|
| 板块ID、名称、类型、语义标签 | 维度属性版本 | 属性变化才新版本 | 每条成员每天复制名称/标签 |
| 行业父子关系 | 独立树内容版本 | 父边/节点语义或解释合同变化 | 仅因采集日期/无关文件hash改变重存树 |
| 行业/概念/风格/地域直接成员 | 一份基线+关系有效版本区间 | 新增/移除边写增量 | 每天全量membership_entries |
| 父行业汇总成员 | 固定树版本下对子孙直接成员去重求并集，允许内容缓存 | 子边或树版本变化 | 每天再存一份父行业股票边 |
| 日期/发布→关系 | 小绑定表 | 每次真实观测/发布绑定一条或少量来源绑定 | 为日期复制整张关系表 |
| 原始日行情 | 股票/交易日事实；修订另有版本 | 新日追加，历史修订仅改动受影响分区 | 每日复制全历史作为新的权威资产 |
| 股票MA/RPS/新高、板块宽度 | 每日实际结果，可跨发布复用 | 所依赖输入改变才新结果 | 为不同任务ID重复相同结果 |
| 当日成员名次/角色 | 动态计算或共享当天紧凑块；V3仅存合格角色 | 当日计算/按需查询 | 用静态成员关系替代动态名次；全成员每天复制长证据JSON |
| 快照、发布、合同、依赖 | 小身份记录，引用共享内容 | 身份/依赖变化 | 删身份证明后直接按日期取最新 |
| 归档源包和提取文件 | 一个可复现权威源+可再生解包缓存 | 内容变化/需要读取 | 同时永久保存每个日包及完整解包副本而不设策略 |
| 在线数据 | 事件收盘批次有限频率；热榜请求时 | 按既有在线合同 | 热榜落盘、每次刷新长期存一个行情全量包 |

“静态”含义是慢变，不是永远不变。今天观察到公司加入概念，不证明过去一直在该概念；不能为了省空间把所有历史快照指向最新关系。

### 17.4 关系增量表结构与解析规则

本节替代每日新建全量membership快照的新增路径。旧ID保留映射，不修改已发布身份。新增表统一命名`relation_*`，不要再实现一套日全量表。

| 表 | 主键 | 必要字段和规则 |
|---|---|---|
| relation_revisions | (source_scope,revision_no) | revision_id UNIQUE、previous_revision_no可空、edge_content_hash、parser_contract、created_at；仅边或解析语义改变创建revision，日期不进入edge_content_hash |
| relation_edge_intervals | (source_scope,sector_id,security_id,from_revision) | to_revision可空；区间[from,to)，from<to；边来源source_kind/直接归属语义；仅存直接成员，不存动态行情 |
| relation_observations | observation_id | source_scope、observed_at、source_effective_date可空、source_file_hashes JSON、revision_no、attribute_version_id、hierarchy_version、quality；内容未变只增观测小行 |
| relation_snapshot_bindings | legacy_membership_snapshot_id | observation_id、revision_no、attribute_version_id、hierarchy_version、legacy_payload_basis JSON；旧快照ID到新解析器的兼容映射 |
| relation_publication_bindings | (publication_id,source_scope) | observation_id、revision_no、attribute_version_id、hierarchy_version；新发布不再生成全量旧snapshot |
| sector_attribute_versions | (source_scope,sector_id,attribute_version_id) | name、type、role、semantic_bucket、content_hash；同属性复用，名字变不等于股票成员变 |

属性集合绑定补充：新增`sector_attribute_revision_bindings(source_scope,sector_id,from_attribute_revision,to_attribute_revision,attribute_version_id)`，PK为前三列，区间规则同成员边；属性观测版本由`sector_attribute_revisions(source_scope,attribute_revision,attribute_set_hash)`登记小行。relation_observations中的attribute_version_id表示这一集合版本的规范ID，查询先解析attribute_revision，再取区间内的对象版本。仅改名的板块闭合旧属性绑定、插入新绑定，不每日复制全部板块属性；不能用单个板块属性对象ID充当整套属性版本。

source_scope是数据源及直接成员定义的稳定命名空间，不包含日期/任务ID；若混合多个TDX文件，先按现有合同解析出规范直接成员再比较。一个revision包含该scope的完整逻辑成员集，但物理仅通过区间表达增量。索引：intervals(source_scope,sector_id,from_revision,to_revision)、(source_scope,security_id,from_revision,to_revision)。

处理步骤固定：

1. 读取TDX只读源或已冻结源，对文件内容hash比较；时间戳只能作为扫描优化，不能作为内容不变的唯一证明。文件未变复用解析；变动时解析一次规范关系和属性。
2. 规范化股票市场/代码、稳定板块ID、直接/派生来源；集合排序去重。关系hash仅包含source_scope、解析语义版本、直接边及影响边含义的source_kind，不含trade_date/observed_at、文件路径、名称、行情。source_kind改变但端点相同也属于关系语义修订，需闭旧区间再开新区间，不因端点hash相同漏改。
3. 与当前该scope完整集合比较。ADD=new-old，REMOVE=old-new；不变则不增revision、不写任何edge行，只记录观测及必要绑定。
4. 有变化时事务建立r+1：REMOVE更新对应开放区间to_revision=r+1；ADD插入from_revision=r+1/to=NULL。老revision查询仍返回原集合，闭合有效区间并非改变旧发布解释。
5. 查询版本r的成员：from_revision<=r且(to_revision IS NULL或r<to_revision)，按security去重；新增/移除数量及按板块分布记简短差异报告。
6. 源解析不完整、编码失败、截断、标的数量异常时该观测INVALID，不关闭原关系。移除只有完整源集合验证通过才可执行；明确空板块与全文件读空分开判。
7. 关系A→B→A按时间生成三个版本，不为了hash相同把第三次观测时间倒回第一次；基础边只按出现区间保存。首次导入没有此前证据，不反推历史生效日期。

不做每日全量“静态快照checkpoint”。区间查询无递归增量链，新增成本约O(新增边+移除边)，无需每32天再复制七万行。批量向量化JOIN后聚合，禁止一个板块一个小SQL/一只股票一个小SQL。

板块名称和关系解耦：同一边集不同名称编码/修正时，边版本复用而属性版本更新；必须校验Unicode实际值，不依据终端显示乱码判数据库坏。ID变更不能仅按同名合并，需明确映射证据。

### 17.5 行业树和父板块派生成员

复用tdx_sector_hierarchy_versions/nodes与analysis_snapshot_hierarchy，不新造第二套行业树表。新增树语义摘要版本：H(contract,排序后的节点ID/parent_ID/level/relation_basis)。名称属性独立绑定；source hashes和observed_at作为观测证据保留，不驱动树内容复制。若现有父关系推导合同改变，应生成新树版本，不悄悄改老树。

行业父成员=`该版本树下全部直接叶成员的UNION DISTINCT`，同股票多叶只计一次。若源提供直接父成员，按合同与派生集求并集并记录DIRECT/DERIVED依据；不能一概抹掉源直接父关系。概念没有可靠父树时保持平面，不能凭代码前缀虚构概念父子。

派生缓存key=(relation_revision,hierarchy_version,semantic_version,display_universe_version)，只在四者之一改变时失效，不包含trade_date；当天退市/ST过滤变化由display_universe_version体现。缓存仅保存必要查询结果，默认内存，不每天落一个父成员全量文件。

迁移老membership_entries时识别payload中的DERIVED_PARENT来源，拆为树+直接边。证据不足的条目标LEGACY_EXPLICIT保持旧查询结果，不能为了压缩丢掉已发布成员。验收必须包含9月10日新增父行业成员，不把该日75028行全部当新增股票概念。

### 17.6 分离“切片身份”和“结果内容”，处理更大的重复明细

不能直接把多个slice_id改成一个：source_manifest、合同、成员依据或价格锚可能不同，历史发布仍须准确绑定。但可以让不同身份引用同一份已经验证相同的结果内容。

新增`analysis_result_objects`：result_object_id PK、domain、schema_version、semantic_contract、value_hash、row_count、storage_kind、created_at；新增`analysis_slice_result_bindings`：slice_id PK→result_object_id、identity_evidence JSON。一份结果物理保存一次，slice及dependencies继续各自保留。表格中的source/日期/质量哪些属于值，必须逐域明确，不单凭logical_hash字符串就共享。

首轮仅迁移占用大的DUCKDB域：technical、strength、high、member_state、structure/summary。每域新建对应`*_result_rows`，列结构沿原表，物理键把slice_id改为result_object_id，保留trade_date及所有业务维度（high必须含window）；对外仍通过slice绑定读取。旧表迁移完成后可用兼容视图/统一查询解析器提供原slice行形状，禁止双写无限期保留两份。

内容hash包括排序后所有业务键、值、NULL/质量、字段单位/语义schema、价格基准语义、成员结果依据；slice ID和采集任务ID可放身份层。相同数值但不同语义/质量不合并。证据JSON先拆：决定因子解释的内容参与值hash；纯源文件路径/任务时间归身份层。无法可靠拆分时保守不合并，不用删quality换空间。

同一result_object可被多个slice引用，API仍根据选定slice返回其溯源信息。历史成员/价格/合同有改动但结果巧合相同，也须保留各自identity_evidence；共享物理值不意味着两次输入相同。

新日构建先比较该域实际依赖内容摘要，不因整个source_bundle的日期变动就重算所有旧日期。依赖分域：股票技术读日线/复权/交易日历；成员变化不使纯技术失效；树变化只使父板块及其下游失效；算法新版本只重算该域及依赖域，不把全工作台强制重建。

### 17.7 每日计算具体增量边界

| 变化 | 允许重算 | 不应重算/重写 |
|---|---|---|
| 只新增交易日t行情 | t的全A必要基础、t板块聚合/研究；从既有窗口读历史 | 所有旧日技术/成员/结构完整再生成 |
| 只改某概念成员 | 该版本概念及受影响派生板块、该日关联/研究；记录新关系依据 | 无关股票历史技术/全行业树 |
| 只改板块名称 | 属性维度、显示缓存 | 成员边、MA/RPS/新高 |
| 树父关系变化 | 树版本、相关父成员聚合和父板块分析 | 无关叶成员边/全A技术 |
| 修正股票i在d的原始价/量 | 明确依赖窗口受影响的日期和域；全市场RPS在受影响日期需重新排名 | 所有股票全部历史无差别重算 |
| 复权锚变化 | 按既有复权合同判哪些历史价格值受影响，可能比单日更大 | 不得假设只有今天变；也不每日复制原始行情 |
| 更新算法参数 | 新合同的指定范围及下游 | 老发布输出覆盖写 |

滚动N日指标的有限影响范围按公式计算；连续新高/episode是状态递推，需要传播到状态收敛或数据末端，不能一律截N天。若无法证明收敛，重算受影响证券该状态后续序列并记录范围，不升级成全市场全历史任务。

V3 research_stock_states可以每日每股紧凑一行；其日期不同是必要历史，不归零增长要求。sector_member_roles仅保存合格角色；旧全量member_state在旧界面需要时从共享结果或指定日按需读取，不为V3再建一份拒绝关系历史。每日观察清单虽小，也需要全市场参考，不拿20只当宽度/RPS分母。

### 17.8 库外文件：暂存、源包、规范化与备份

先按既有存储catalog及manifest建立引用图，盘点data之外的runtime/cache是否有大文件；本轮目录统计只覆盖data，不能宣布项目全部占用已穷尽。

1. **解包缓存**：extracted是当前最大已见目录。确认为可由已保留源包完整重建、无活动任务读取后可回收。默认保留最近2个已使用bundle的提取结果，其余按需解包；不是按mtime扫目录删除。旧manifest引用路径必须由输入解析器支持“源包+成员路径”重建解析后才能移除，不能删完才发现历史读不了。
2. **原始数据权威副本**：长期优先一份规范化原始日行情分区+源观测证据；新日追加分区。若完整日包用于严格字节复现仍是唯一来源，它暂时受保护。必须明确“业务值可复算”和“原包字节可复现”的区别，未经用户选择不自动放弃后者。
3. **包的去重/增量**：完全相同包按内容hash存一次；不同压缩包先比解包后有效日线内容，不因zip hash不同断言行情全部改变。第一阶段以保留源包、回收冗余解包为主。后续可将原始日线按证券/日期规范化及历史修订另版本保存，确认所有调用方接受后，才将旧包列为可选清理项。
4. **metadata**：按元数据文件内容hash复用冻结对象，不因source_bundle新日期复制相同文件。不同文件共用版本manifest，不硬链接到TDX可变源；TDX始终只读输入。
5. **.phase1_cache**：默认2GiB上限，按最近访问淘汰无活动任务引用的可再生对象；达到90%提示，达到上限先回收后新增。不要每次审计保存全量缓存副本。当前910.5MiB不是马上必须清空。
6. **normalized**：不先拆现有单文件再给每个日期复制全历史；新增输入采用日期分区或既有事实追加读取层，源修订有明确版本；旧单文件在所有读取适配前保留。
7. **备份**：不新增每日自动全库备份/恢复演练。新增操作默认人工触发；已有3305.6MiB按backup_catalog分类。同内容重复副本、无引用演练副本可以列清理候选；保留最新一份有效备份为建议默认，用户固定保留项不删。不得只因文件位于backups就删除。

cache预算/源包保留策略只管理可再生和未引用数据，不能以“超过2GiB”强删受保护原始证据。若所有空间都是受保护对象，报告具体来源和可选取舍，不暂停整个本地研究或自动扩建灾备系统。

### 17.9 旧数据迁移、查询兼容与回收

实施分为“阻止新增重复→迁移归并→可选物理回收”，本轮只出方案。修改V3 §2/§8的“不DROP”约束含义：不丢业务历史/发布身份；允许验证后把冗余物理存储换成共享结果或兼容视图。不得因此获得任意清旧库授权。

**MIG1 关系**：按观测顺序解析6个旧快照，分离边/属性/来源/日期，生成revision区间和旧ID绑定；逐旧快照重建边集合，排序hash及count逐一与旧数据相同。完整payload通过维度+legacy_payload_basis重组，不能丢掉日期、PIT标记、直接/派生来源。保留旧输入观测不同属性，不把相同边hash等同整快照相同。

**MIG2 分析结果**：逐域按实际完整语义内容归组，共享result_object；逐slice重建旧行比较键集合、NULL、指标、证据及原logical digest，全部一致才切读。出现差异只阻塞该域，不去修改expected测试。

**MIG3 接口**：repository导入、attribute_library、history_adapter、hierarchy加载、association、linkage、intersection、publication导出身份等改用`membership_resolver.resolve(snapshot_or_publication)`；先兼容旧ID、新发布再只写新绑定。扫描所有直接SQL使用membership_entries和*_daily的路径，不只修新V3 API。历史页面若读到当前关系即失败。

**MIG4 停旧写**：确认新发布不再INSERT全量旧membership_entries，迁移域不再双写旧daily大表；观察至少3次同输入运行+2个不同日构建。旧物理数据可在无损等价检查通过后一次性删除冗余行/替换表，先给确切对象、可回收估算和引用检查结果。用户仅同意当前文档审计，尚未在本轮授权执行任何删除。

**MIG5 文件回收**：复用既有operations/storage preview能力，清理计划区分“可再生解包”“重复结果”“无用备份”“受保护源包”；默认只选择已验证无引用可再生项。Windows路径解析必须在明确项目目标子目录内，拒绝TDX根、项目根、符号链接越界和运行中对象。

DuckDB逻辑DELETE不保证文件立即缩小；空闲块可被后续写入复用。不要承诺执行VACUUM就缩回预期大小。确需缩小物理库时单独安排停止写入、导出/复制有效对象到新库、核对表/视图/索引/发布/版本绑定再切换；这只是一次压缩迁移，不是长期多级恢复工程。实施前查当前DuckDB版本官方回收方式，禁止热复制正在写入的库。

### 17.10 API和界面追加：可看增长，不新增繁杂运维页

扩展现有GET `/api/operations/storage`，保留旧字段，新增`database_bytes,used_block_bytes,free_block_bytes,rows_by_domain,unique_result_rows,identity_count,relation_revision_count,relation_edge_interval_count,cache_bytes,protected_bytes,reclaimable_bytes,last_build_growth`。重型全表去重统计只在显式审计任务中计算并缓存结果，不能每次打开页面COUNT DISTINCT所有JSON。

扩展已有`POST /api/operations/storage/preview`返回分类候选及不可删原因；不新增“打开页面即清理”。研究页的数据状态仅增加一张“本次新增：行情X行、关系新增Y/移除Z、复用结果K、空间变化M”小卡，详细表在现有数据状态/存储页。无需新一级导航、外部审批角色或恢复仪表盘。

每日builder增加指标：`new_relation_edges,closed_relation_edges,relation_rows_reused,new_fact_rows,reused_result_objects,identity_rows_added,cache_bytes_added,db_file_growth_bytes`。物理字节受空闲块重用/压缩影响，不能简单用行数乘固定字节伪装实测。

### 17.11 必做任务与对V3原阶段的重排

| 任务 | 精确文件/产物 | 依赖及内部验收 |
|---|---|---|
| S00 容量基线 | 新只读storage审计任务，复用workbench_ops/storage登记 | 保存本章同口径计数；区别键重复/值重复/可删 |
| S01 关系分解 | 新workbench_service/membership_resolver.py、relation_repository.py，新增区间/绑定迁移 | repository导入解耦；无变化日0条边写入；单边增删只改对应边 |
| S02 树复用 | hierarchy.py修改摘要和观测绑定、父成员去重解析 | 无关源hash变化不重存节点；旧树仍可查询 |
| S03 结果共享 | slice_coordinator.py/immutable.py及域writer/reader；新增result对象及绑定 | 身份不变、不同slice相同内容物理仅一份；质量不同不合并 |
| S04 增量调度 | 生产daily、history job planner、V3 research_builder | 只新增日/受影响依赖，不重建所有旧日；记录增量范围 |
| S05 库外缓存 | workbench_input/pipeline.py、输入resolver、workbench_ops/storage及backup调用检查 | 可再生解包限额；无热库复制；原始唯一源受保护 |
| S06 迁移验证 | MIG1–3旧发布/旧API全链逐版本对照 | 旧关系/值/身份精确等价、没有最新关系回填历史 |
| S07 止旧写/回收 | MIG4–5精确清单、现有preview操作 | 先观察增量，再给回收计划，执行删除另按明确范围处理 |
| S08 增长验收 | 容量报表+接口/页面证据 | 下节所有用例，数据新增长不再乘任务次数 |

新顺序：U00后立即S00/S01/S02；U01与它们并行；U02–U05算法纯函数可并行开发。**U06正式结果落库需先确定S01的关系绑定和S03的内容复用契约**，防新V3再造重复；U08读服务依赖S01 resolver。S04和U06联调，S06在切正式首页前通过；S05先减少未来解包/备份重复，S07不阻塞算法预览，但不能无限期保留双写。S08与U12共同完成，专项问题单独记录，不被功能单测替代。

§13原U06里的membership_snapshot_id对新发布解析为关系观测绑定；字段可保留兼容名称但必须在dependency_bindings携带revision/attribute/hierarchy，不能只保存一个每日全量快照ID。未来research_run也只增小绑定，不复制关系内容。

### 17.12 定量验收：防止再次无限复制

| 场景 | 必须结果 |
|---|---|
| 72000条边连续5日完全不变 | 72000条基线区间；随后边INSERT/UPDATE均0，只有少量观测/发布绑定 |
| 新增3条、移除2条 | 插入3区间、关闭2区间；不重新插入72000行；旧版本查询完全不变 |
| 名称变、成员不变 | 仅属性版本变化，边写入0 |
| 日期或ZIP/无关源hash变、树语义没变 | 树节点写入0，源观测可新增 |
| A→B→A关系变更 | 版本时间正确，复加入边新有效区间，不丢中间B |
| 文件读空/截断 | 不当作所有股票退出板块 |
| 股票属于两个子行业且都归同父 | 父成员只计一次；直接/派生依据可解释 |
| 同输入同参数构建3次 | 行情/关系/分析物理内容新增0；允许小任务日志，不新增全库副本 |
| 不同slice身份、完全相同输出 | 两个身份、一份结果，旧slice溯源仍各自准确 |
| 同值但质量/合同语义不同 | 不强行合并 |
| 新增一天N只股票、4新高窗口 | 约N条当天技术及4N新高必要结果，不乘历史天数/运行次数；以实际有效样本数解释缺失 |
| 历史修正影响RPS横截面 | 正确重算受影响日期参考总体，不只更新单股分位 |
| 删除解包缓存后读受保护历史 | 能由保留源恢复读取，或清理前明确受保护而拒删 |
| 热榜翻页100次 | 真实热榜持久化行/批次/raw仍0 |
| 主库逻辑去重后文件不缩小 | 报告空闲块与实际空间，不误称失败或重复造备份 |

验收报告同时给“业务事实新增”“身份/日志新增”“重复物理内容新增”“可再生缓存净增”。**重复物理内容新增目标为0，真实历史事实不要求0增长。**关系稳定期是常数边存储+小观测；日行情/结果随交易日线性增长，不应随交易日×任务次数×历史窗口重复放大。不预先承诺固定节省90%；迁移前后相同口径实测才报回收数字。

本专项内部状态：证据审阅完成、改造设计完成；迁移和运行验收未执行。后续实现必须处理，不再只记为“以后再看数据膨胀”。

## 18. 唯一实施顺序与逐任务操作手册

### 18.1 怎么使用：不再让实现者在三套编号之间猜

本文的业务规则、字段、接口已在前文定义；本章只负责把它们编排成可执行工作包，不允许在执行中另创公式。**默认串行顺序固定：P00→P01→P02→P03→P04→P05→P06→P07→P08→P09→P10→P11。**模块内按小任务尾号顺序执行。跳过一个阻塞任务，必须登记本章明确允许的替代路径，不能跳过后仍标整个模块PASS。

工作节奏：完成一个小任务→执行对应自动检查和实际查询/交互检查→内部修正→记录PASS/PARTIAL/BLOCKED→再进入下一任务。无需外部独立审计员，也不需要为每个任务生成一堆新合同文档；使用一个实施台账和按任务归档的简短证据即可。

建议唯一实施台账`docs/V3_IMPLEMENTATION_LEDGER.md`，实施时新建，本轮不创建。每行字段固定为`task_id,status,input_revision,changed_files,test_evidence,product_or_data_evidence,open_issue,next_task`。所有任务首次为NOT_STARTED。引用本规格章节即可，不复制另一份不同规则。

**每次交给其他模型的起步指令**：读取本章、当前任务引用的技术章节、最新AGENTS及台账；确认前置PASS；仅实施当前小任务；不重新规划整套系统；完成后填写证据和下一任务。若工作区同时有其他修改，只审查实际相关差异，不能覆盖。

### 18.2 总览：先做什么、旧模块怎么处理、何时能看效果

| 顺序 | 模块 | 先处理的旧模块 | 完成后得到什么 | 模块放行门 |
|---|---|---|---|---|
| P00 | 基线与契约固定 | 所有旧入口只盘点不改 | 实际输入/存储/接口基线和固定参数 | G00：可对照、不靠口头约定 |
| P01 | 服务与联动止痛 | app.py请求锁、hot-rank、modal/router | 慢网不堵本地、证据不撑表 | G01：故障注入和点击路径通过 |
| P02 | 静态关系增量 | membership导入、行业树、属性查询 | 无变化日不复制成员关系 | G02：新旧每个快照关系等价 |
| P03 | 分析结果共享 | technical/strength/high/member/structure物化 | 多身份共享结果，不重复大明细 | G03：每域旧slice重建等价 |
| P04 | 每日增量和暂存 | daily/history构建、解包缓存 | 每天只写变化部分，暂存有边界 | G04：重复运行不扩大业务数据 |
| P05 | 股票基础特征/信号 | technical/strength/high基础复用 | 可手工验证的SETUP/BREAKOUT/RECOVERY | G05：原始输入到信号链通过 |
| P06 | 板块当前/潜在算法 | 旧强势排名不改义、仅退出新路径 | 双轨板块与确认/失效状态 | G06：潜在不是旧榜尾部 |
| P07 | 成员/清单/研究run | 旧20日代表、旧候选/关联路径 | 各板块对应股票、双清单、可读run | G07：无循环依赖，结果可复现 |
| P08 | 新本地页面/API | 首页、板块联动、个股证据 | **第一版真实数据双轨工作台** | G08：完整用户路径可使用 |
| P09 | 在线事件与盘中成员 | 现有热榜/报价能力、本地估算默认入口 | 在线题材/分布/简图/速览及盘中成员 | G09：来源逐项验证、失败不拖本地 |
| P10 | 旧功能归位与效果跟踪 | 矩阵/主线/五类/交集/本地涨停 | 原功能不丢、提前信号有后续记录 | G10：去留矩阵逐行核查 |
| P11 | 总体验收和旧占用回收 | 已迁移冗余存储、旧写入口 | 新主入口切换及真实增长报告 | G11：功能和增量通过，效果状态诚实 |

可以提前看到的成果：P01修现有交互；P02/P04看到增量写入减少；P08交真实双轨界面。P09在线功能不必等长期效果验证；P10开启观察后，样本尚未到期可以交预览版，不假装已验证预测有效。

仅允许这些并行，不由实现者任意放宽依赖：

- G00之后，P09-01公开源验证可与P02/P03并行（不得触碰同一业务文件）；源adapter和页面正式接入仍按P09前置执行。
- G00后可制作P08布局的明确合成fixture，标“演示数据”；不能以此通过G08。
- G02后可并行开发P05/P06的纯函数并做合成测试，但不得在G03/G04前接正式每日写入。
- P11清理预览可先只读生成，实际回收必须等迁移验证；不能先删再补查询适配。

### 18.3 P00：建立可比较基线（对应U00、S00）

#### P00-01 盘点旧页面、API和读写路径

- **目的/前置**：实施第一步；知道哪些旧能力必须保留，避免换首页时丢功能。读取§2、§13、§17及实际源码。
- **旧模块**：app.py路由、static/v2的router/api/app、repository、production/daily；此任务只读。
- **步骤**：①按§2每行记录当前入口、API、表/文件和调用函数；②搜索所有直接读取membership_entries、各*_daily和写入这些表的位置；③记录后台daily/history/jobs/导入任务分别写什么；④把未知调用方列为未关闭项，不能填“无”。
- **产物**：台账基线附表，包含旧模块→API→读取→写入映射和当前代码版本/相关未提交差异。
- **验收**：§2所有功能都有对应行；成员/切片的所有搜索命中均分类为读、写、测试或废弃；没有未解释生产写入点。通过后进入P00-02。

#### P00-02 记录数据库和库外容量，不做清理

- **目的/前置**：P00-01通过；后续能证明减的是重复，不是业务历史。
- **步骤**：①只读记录每表行数、业务键数、slice/version数及数据库块占用；②按§17.2统计data目录和补查runtime大文件；③对关系边hash、high的window维度、相同结果摘要分组；④记录当前发布引用的对象，标记唯一原始证据。
- **产物**：一次JSON/Markdown容量基线，可复用现有storage审计机制；不复制主库作为“审计证据”。
- **验收**：数字标明采集时间；键重复与内容重复分开；可删除大小未知时写UNKNOWN而非差额；TDX未写入。通过后进入P00-03。

#### P00-03 冻结配置、DTO和可执行夹具

- **目的/前置**：P00-02通过；让不同模型使用同一规则。
- **步骤**：①建立§4所述参数配置，数值逐项对应本文；②定义§10请求/响应schema和中文reason目录；③加入§16合成夹具，明确不是行情样本；④冻结数据类型、NULL、排名并列和版本ID；⑤记录各capability的已有状态，不默认打开NOT_VERIFIED项。
- **产物**：配置、DTO/schema、合成测试数据、台账G00记录。
- **验收**：每个阈值只有一个来源；不存在“代码内另一个默认值”；缺字段/非法枚举测试失败；规格引用能定位。G00通过后P01。

### 18.4 P01：先修现有服务阻塞和证据交互（U01及U09前置）

#### P01-01 缩短数据库锁作用域

- **目的/前置**：G00；避免后续更多在线请求放大卡顿。
- **旧模块/落点**：app.py::request_scope/do_GET、hot_rankings、相关本地补行情调用。保留连接生命周期校验，不粗暴删除全部锁。
- **步骤**：①画出当前GET中本地读、网络等待、补字段三个区段；②将在线路由改为短本地读→释放连接/锁→网络→短批量补字段；③明确写任务与只读连接并发的既有规则；④注入超时、异常和客户端断开，确保连接关闭。
- **产物**：修改后的路由执行边界、并发回归测试、慢源期间本地请求测量。
- **验收**：外部模拟8秒等待期间本地publications/已缓存研究查询不出现同长度等待；无连接泄漏、无跨线程复用错误。进入P01-02。

#### P01-02 修热榜分页和单源失败

- **目的/前置**：P01-01；保留热榜能力但不让它拉全量报价或拖垮其他源。
- **步骤**：①区分上游分页和本地分页；②先确定本页，再批量补本页报价；③total取真实上游总数/完整集合数，未知NULL；④多源独立结果并发且有总超时；⑤保持cache:false、热榜零持久化。
- **产物**：online_hot_rank.py及相关adapter/API回归；合成分页/失败响应。
- **验收**：100条第2页20条的total仍100；源A失败源B显示；翻页不存raw/行/batch；不通过修改旧测试预期掩盖问题。进入P01-03。

#### P01-03 修证据弹窗和返回路径

- **目的/前置**：P01-02；先处理用户已反馈的表格变形。
- **旧模块**：modal.js、app.js、router.js、styles.css；此时不改旧候选算法。
- **步骤**：①所有证据按钮统一button和modal入口，移除该路径的表内展开/href跳转；②实现§12尺寸、X/遮罩/Esc、焦点返回；③记录进入前筛选、页码、滚动；④验证快速点击A/B时旧响应不覆盖新对象。
- **产物**：真实旧页面可见修复、1440宽和窄屏截图/交互记录。
- **验收**：开关证据表格行高不变，关闭后回到原位置；源文本不能执行HTML；所有关闭方式通过。G01→P02。

### 18.5 P02：成员和行业树改为慢变关系（S01、S02、S06关系部分）

#### P02-01 新建关系/属性增量结构与解析器

- **目的/前置**：G01；先有存储能力再迁移旧数据。
- **旧模块**：membership_snapshots/entries保留；新增§17.4表、relation_repository.py和membership_resolver.py。
- **步骤**：①在当前最新迁移号之后登记新迁移；②实现规范边hash、属性hash和source_scope；③实现版本区间查询与ADD/REMOVE差异纯函数；④对同边不同日期、名称变化、source_kind变化分别测试；⑤实现空源/不完整源拒绝更新。
- **产物**：新表、增量writer、统一resolver，尚不切生产旧读。
- **验收**：72000稳定边重复输入不新增边；增3删2只插3闭2；A→B→A历史版本正确；迁移可在空测试库重复运行且不重复创建。进入P02-02。

#### P02-02 导入旧关系并逐快照对照

- **目的/前置**：P02-01；不丢旧日期关系或名称。
- **步骤**：①按旧观测时间和来源分类6个快照（实施时用实际数量）；②分离边、属性、日期、PIT与直接/派生字段；③写revision/attribute及旧ID绑定；④对每个旧ID用resolver重建；⑤比较边hash、计数和重建payload语义，差异逐条解释修正。
- **产物**：旧ID兼容绑定、逐快照比对报告；不删除旧表。
- **验收**：旧日期不读最新关系；9月8/9相同边共享而日期仍不同；同边不同名称不会被抹平；全部实际旧快照通过。进入P02-03。

#### P02-03 树语义复用与父成员去重

- **目的/前置**：P02-02；复用已有行业树，不重造。
- **步骤**：①hierarchy.py区分树语义摘要和源观测摘要；②加载固定树版本求直接/派生父成员并集；③保留源直接父成员，未知来源保守兼容；④测试两个叶行业同股票归同父去重、概念平面无假父关系。
- **产物**：树加载/父成员resolver及缓存key；旧树绑定不变。
- **验收**：无关源hash改变不重写554节点；父成员不重复计数；旧树版本查询等价。进入P02-04。

#### P02-04 接入旧读路径，再关闭旧全量新写

- **目的/前置**：P02-03；不能只有V3读得到增量关系。
- **步骤**：①按P00清单逐个改attribute_library、history_adapter、linkage、intersection、association和发布身份读取为resolver；②新旧路径对照测试；③将repository新发布导入改为增量观测绑定；④确认历史分支仍能解析旧ID，停止新发布向旧membership_entries全量插入。
- **产物**：所有生产消费者适配、旧写停止证据；旧表作为迁移前历史保留待最终回收。
- **验收**：相同成员新交易日边写入0；旧交集/成员查询一致；所有P00登记调用方已处理。G02→P03。

### 18.6 P03：共享分析结果，保留发布身份（S03、S06结果部分）

#### P03-01 建结果对象与切片绑定层

- **目的/前置**：G02；相同结果不因任务/快照ID重复物化。
- **步骤**：①按§17.6定义result_objects、slice_result_bindings及逐域schema；②明确每字段属于业务内容还是身份来源；③实现规范内容hash与精确回读核验；④保留原slice/dependency/publication身份不覆盖。
- **旧模块**：slice_coordinator、immutable；旧域writer尚不一次性全部切换。
- **产物/验收**：同内容不同slice两身份一对象；质量/单位/语义不同不共享；hash命中仍校验结构/行数；通过后P03-02。

#### P03-02 先迁移technical，再strength，再high

- **目的/前置**：P03-01；先在简单稳定域证明兼容，再处理复杂成员证据。
- **步骤**：①technical建result_rows→旧slice逐个导入/对照→切该域读→停该域旧新写；②只有technical通过才对strength重复流程；③再处理high，键必须含window；④每域保留单独验收记录，任一失败不标整步通过。
- **产物**：三域共享reader/writer；旧API相同输入响应对照。
- **验收**：原指标、NULL、质量与身份完全一致；同输入重跑三次物理内容新增0；新高四窗口不合并丢行。通过后P03-03。

#### P03-03 再迁移member_state、structure、summary

- **目的/前置**：P03-02；处理主要大明细及其证据。
- **步骤**：①先分类成员日期/排名动态值与静态属性引用；②逐域采用与P03-02相同导入—对照—切读—停新写顺序；③证据JSON只拆已证明不影响语义的身份字段；④旧代表/主线/关联读取这些域时测试依赖绑定不变。
- **产物**：域级共享结果和保守不合并清单。
- **验收**：旧成员名次/结构命中/历史查询一致；不以删除证据换压缩率；阻塞项明确到域。G03→P04。其他未迁移域仍走旧reader，不要求本步一口气重构全库。

### 18.7 P04：增量调度和可再生缓存（S04、S05）

#### P04-01 规划每日最小失效范围

- **目的/前置**：G03；从根源停止每日旧历史重算。
- **旧模块**：production/daily、history窗口规划、source_freezer；不修改TDX。
- **步骤**：①分离行情、关系、树、参数、复权等依赖摘要；②根据§17.7生成待计算日期/证券/板块/域清单；③普通新日仅追加当天；④历史修订按窗口传播，RPS重排受影响日参考总体，递推状态传播至收敛；⑤为失效计划写解释码。
- **产物**：可查看的build_plan及失效范围单测。
- **验收**：改名称不重算MA；改概念成员不重算无关技术；修历史价不会漏掉RPS横截面；重复输入待算域为空。进入P04-02。

#### P04-02 接增量writer并记录增长

- **目的/前置**：P04-01；计划必须真正控制写入。
- **步骤**：①构建器只执行build_plan中的对象；②复用P02/P03；③各域完成后再绑定发布/快照；④添加§17.10行数、复用、字节指标；⑤同输入重复3次、另选两相邻日期构建验证。
- **产物**：真实输入的增量构建记录，而非只有mock测试。
- **验收**：重跑业务内容新增0；新日不乘旧天数/任务次数；失败不让首页指向半成品。进入P04-03。

#### P04-03 管住解包缓存和全库副本

- **目的/前置**：P04-02；控制已见库外大头，不先删源。
- **步骤**：①input_staging的源包/解包/metadata按引用和可再生性登记；②验证输入resolver能从保留包恢复需要的文件；③按§17.8启用最近2个bundle解包保留与phase1_cache预算；④审查backup调用链，取消新增每日强制备份/演练设计；⑤这里只启用未来边界，旧大文件先给预览。
- **产物**：缓存策略、回收预览和受保护清单。
- **验收**：唯一源不删；活动任务文件不回收；新日期不无条件复制相同metadata；输入读取可恢复；预算满不删除受保护数据。G04→P05。

### 18.8 P05：先算独立股票信号（U02、U03）

#### P05-01 构建一致的基础特征输入

- **目的/前置**：G04（纯函数开发可按18.2提前）；后面板块判断要建立在正确字段上。
- **步骤**：①按run绑定technical/strength/成员/日历而非各表最新值；②补bias、sigma、range、rps变化等§4特征；③报价覆盖、正式A、RS5与RET5严格分开；④缺日使用主交易日历；⑤用逐股原始输入手算核对，不仅喂预聚合特征。
- **产物**：research_features.py及原始输入夹具。
- **验收**：NULL/停牌/除权/零波动/换成员用例通过；没有未来输入；输出单位与DTO一致。进入P05-02。

#### P05-02 实现五种基础信号

- **目的/前置**：P05-01；独立召回提前观察股，不从旧优先池截取。
- **步骤**：①逐个实现BREAKOUT、SETUP、RECOVERY、TREND_BACKGROUND、STRUCTURE_BREAK；②每个条件输出可解释reason；③三值逻辑和风险字段完整性检查；④禁止调用板块或最终清单服务；⑤从真实输入找正/反/缺失例。
- **产物**：stock_attention.py，按信号分组的测试和真实样例。
- **验收**：新高不自动过热、微跌SETUP可见、趋势背景不单独FOCUS；原五类合同未被改写。进入P05-03。

#### P05-03 固定信号解释与初始分布

- **目的/前置**：P05-02；防出现几千条命中后前端再猜如何筛。
- **步骤**：①统计每信号true/false/unknown及主要拒绝码；②核对流动性/风险缺失是否异常吃掉总体；③按本文公式修实现错误，不擅改阈值凑数；④记录需后续验证的参数问题。
- **产物/验收**：真实分布报告、至少每信号一正一反一缺失解释；无隐藏阈值修改；数量不设硬“必须命中”。G05→P06。

### 18.9 P06：再算板块双轨与生命周期（U04、U05）

#### P06-01 聚合板块特征并计算CURRENT

- **目的/前置**：G05；区分今天真强与历史涨得多。
- **步骤**：①由固定成员集聚合m1/b1/rel1/p1，验证市场/类型覆盖；②计算共同成员变化和正式A；③按§5.1判CURRENT/W，单股贡献检查；④给稳定排名和同日强、长期背景分别标签。
- **旧模块**：保留旧sector_cycle/mainline合同；不复用旧20日rank作CURRENT。
- **产物/验收**：sector_attention当前分支；长期第1今天弱不入CURRENT，市场普涨不全部命中，放量下跌不豁免W。进入P06-02。

#### P06-02 实现三个POTENTIAL分支

- **目的/前置**：P06-01；提供真正不同于当日榜的提前观察。
- **步骤**：①从P05全量基础信号聚合early_width/SETUP人数，不读最终清单；②依次实现扩散、蓄势、回暖；③处理共同基础、三值逻辑、分支优先顺序；④强制CURRENT/POTENTIAL互斥；⑤输出等待与失效条件。
- **产物**：潜在资格、排序、分支证据和真实样例。
- **验收**：低q20但扩散改善可入；单一dq5高但宽度恶化不入；输入不足UNKNOWN；不靠前端截旧榜制造潜在池。进入P06-03。

#### P06-03 推进潜在episode

- **目的/前置**：P06-02；跟踪是否真的转强，避免无限“潜在”。
- **步骤**：①按交易日推进首次/持续/暂停/确认/失效/到期；②先判断当前强势确认，再潜在保留；③实现5日期限和2日重置、缺日不计连续；④保留当日资格和生命周期两个字段；⑤固定版本切换的历史边界，不回填过去确认。
- **产物/验收**：sector_signal_state.py及至少10日合成序列；暂停只1个有效日、5日到期不滚动重置、未来结果不修改首日信号。G06→P07。

### 18.10 P07：角色、主关联、短名单和完整研究run（U07、U06）

#### P07-01 计算每个板块的四类成员

- **目的/前置**：G06；解决只有强板块却看不到今天强股的问题。
- **步骤**：①完整成员集中先计算当日排名/分母；②独立判TODAY_LEADER、CURRENT_RESEARCH、EARLY_WATCH；③ALL_MEMBERS直接读resolver与当天行情；④仅前三类合格角色写紧凑结果；⑤每类先筛排序再分页。
- **产物**：research_members.py、角色结果及人数统计。
- **验收**：当日赢家与RET20赢家不同的用例正确；EXTENDED仍在事实领涨榜但不进研究角色；没有提前成员不补旧龙头。进入P07-02。

#### P07-02 计算主备选关联与两条短名单

- **目的/前置**：P07-01；让股票留意理由与当前板块一致。
- **旧模块**：新服务替代新页面对旧association/strength_association和candidate排名的依赖，旧API保留。
- **步骤**：①按真实关系验证LOO共同支持；②CURRENT/EARLY分别选1主2备；③分别生成20上限清单、主板块最多3只、全局去重；④处理暂停/已触发/个体触发；⑤生成移入移出与等待条件，不能等待当天已满足的RECOVERY。
- **产物/验收**：research_association和shortlist分配；主行业不固定、一个弱关联不否决其他有效关联；当前20不挤掉提前20；不足不补位。进入P07-03。

#### P07-03 事务封存并接入已有jobs

- **目的/前置**：P07-02且G03/G04；有完整研究结果才能提供正式读API。
- **步骤**：①登记§8研究表并绑定P02关系/P03共享依赖；②builder按股票→板块→episode→角色→清单顺序计算；③以input_key幂等事务写入，最后COMPLETE；④接BUILD_RESEARCH_V3任务和既有job状态；⑤同输入重复运行和中途失败验证。
- **产物/验收**：完整run、任务入口、失败记录；GET不会触发全市场构建；未完成run不可见；旧发布身份不变；重复业务新增0。G07→P08。

### 18.11 P08：交付可操作的本地双轨工作台（U08、U09）

#### P08-01 接本地API及上下文

- **目的/前置**：G07；后端决定资格和排序，前端只展示。
- **步骤**：①按§10接API01–08/13，校验context/日期/ID；②旧详情/历史读取绑定相同发布；③实现总数、EMPTY/UNAVAILABLE、字段时间与原因；④响应schema测试、分页和查询计划检查。
- **产物/验收**：research_context/research_queries与路由；跨日期拒绝、total不是页长、只返回COMPLETE；一次页查询不拉全市场结果到前端。进入P08-02。

#### P08-02 接首页双栏与板块详情成员

- **目的/前置**：P08-01；这是第一条必须给用户看的新产品路径。
- **步骤**：①首页CURRENT/POTENTIAL各6卡、各3成员；②点击当前卡默认当日领涨，潜在卡默认提前观察；③左板块右成员，窄屏列表/详情返回；④接分页、轨道切换、请求取消、空态；⑤真实run截图，不拿fixture当实测。
- **产物/验收**：从首页两次点击以内看到对应股票理由；切B后A迟到不会覆盖；全页不被表格撑宽；两轨均可空且解释正确。进入P08-03。

#### P08-03 接全局双清单、详情与旧入口兼容

- **目的/前置**：P08-02；候选数量收敛同时保留深度研究。
- **步骤**：①个股页当前/提前各自列表及个体触发；②证据modal分节按需加载；③接等待/失效/移出原因；④旧candidate入口改“全部结构候选”，暂不删旧页面；⑤统一单位/名称/日期及角色排名。
- **产物/验收**：新本地研究预览版；20/20限额和真实详情一致；旧五类可达；关闭/返回保持筛选滚动。G08通过后可交用户看真实效果，随后P09，不能把此时称全部升级完成。

### 18.12 P09：在线数据和盘中成员（O01–O04）

#### P09-01 逐数据集验证公开来源

- **目的/前置**：G00即可提前只读做；正式接入依G08。确认可用数据，不猜会员服务算法。
- **步骤**：①按§22优先验证龙字诀已解析、已留历史探测证据的公开来源，先EXT01/02/03/04/05/06，再EXT07/08/09，各数据集独立；②记录完整URL/参数/响应成功条件/单位/时区/覆盖/分页；③分数据集标CURRENT_PROBE/UNAVAILABLE/STATIC_ONLY；④真实热榜不落fixture，改合成数据；⑤C/D类停止接入，仅记录缺项；⑥仅对缺口或明确有价值增强另评伏羲，不把FY01–17批量验收设为前置。
- **产物/验收**：每数据集映射表和capability结论；七池host/枚举不明不能编造；某源不可用不等于禁止项目联网。**一个核心数据集获当前证据即可进入其对应P09-02子任务**，其它来源继续独立复测并标缺项；EXT11、FY01及API Key均不是EXT01–09的前置门。

#### P09-02 标准化事件并建立批次读取

- **目的/前置**：目标子功能的龙字诀来源获可解析当前证据、G01/G08；只验证本子功能实际消费的源，不能要求所有在线来源共同VERIFIED。
- **步骤**：①按§8.3建事件表并复用既有source/fetch/batch；②写THS/题材adapter和统一DTO；③分别处理连续板、M天N板、涨停/炸板状态；④建立同bundle去重/分页/部分失败；⑤实施内存过期与允许收盘批次存储，不触碰本地run身份。
- **产物/验收**：API09–11数据层；9天5板不算5连板；多题材总数去重；覆盖不足不说全市场；热榜不误入事件持久化。进入P09-03。

#### P09-03 依次接四个事件页面和热榜

- **目的/前置**：P09-02；尽早提供原软件可借鉴的在线事实功能。
- **步骤**：①先情绪速览确认池统计口径；②接最强题材原榜及成员；③利用同一bundle接涨停分布；④接按高度的涨停简图；⑤扩热榜平台/子榜按需切换，复用P01分页修复；⑥每小页完成即独立记录可用/不可用来源，不以少一个源隐去整页。
- **产物/验收**：market子页实际网络和失败场景；不把题材归属次数当涨停家数；本地估算有显式切换；首页本地不等网络12秒。进入P09-04。

#### P09-04 接盘中板块成员与本地背景

- **目的/前置**：P09-03中对应板块来源已可用；仅“盘中实时成员重排”子能力需要独立可用的报价源。没有报价源不阻塞情绪、题材、分布、简图、热榜和P10本地功能。
- **步骤**：①对所选板块批量取完整成员报价，记录报价覆盖和时间跨度；②实现API15固定quote_bundle排序分页；③CLOSE/LIVE字段分组，昨日潜在观察叠今日表现而不改昨日形态；④只取一个板块不足以重排全市场p1时不声称全市场实时强势榜；⑤超时回到明确的收盘背景，不伪造最新行情。
- **产物/验收**：盘中成员列表、覆盖不足提示、来源和截止时间；第一页非简单“前50只取报价”；昨日列表不冒称当日榜。G09按数据集分别记录：缺必要报价时该能力PARTIAL而非虚假PASS；本地和其他在线页仍可继续P10。

### 18.13 P10：归位旧功能，并开始验证提前信号（U10、U11）

#### P10-01 逐项执行旧功能去留矩阵

- **目的/前置**：G08、本次P09各数据集已登记状态；防新界面吞掉旧能力。
- **步骤**：①按§2逐行处理矩阵、主线、代表历史、属性、交集、五类、新高/MA/RPS；②主线标中期背景，原代表标历史代表；③首页停止调用旧强势和旧候选作新优先；④本地涨停估算保留正常切换；⑤每项记录新入口/旧API兼容/实际截图或查询。
- **产物/验收**：所有去留行有处置证据；无“暂时隐藏以后再说”的未登记能力；历史发布可打开。进入P10-02。

#### P10-02 接集合筛选和跨页关联

- **目的/前置**：P10-01；避免板块、股票、交集仍各是孤岛。
- **步骤**：①名称搜索选择2–4板块；②旧集合服务先计算集合，再按research_context角色过滤和分页；③个股主/备板块链接传原上下文；④交集结果打开证据后返回保留选择；⑤旧请求不传新参数时保留原行为。
- **产物/验收**：API14及完整操作路径；不要求用户输入sector_id；集合页总数和成员实际一致。进入P10-03。

#### P10-03 记录前瞻结果与简单基线

- **目的/前置**：P10-02、真实run已经生成；验证“提前”，不只是展示名字。
- **步骤**：①封存潜在episode首次信号；②建立§8.2 outcomes和只读信号的评估任务；③按3/5交易日到期计算CURRENT确认及固定成员收益诊断；④与§14三组同日等量基线比较；⑤区分历史重建、真实前瞻、尚未到期、数据缺失。
- **产物/验收**：PENDING可正常存在；手工构造t+5未来数据后信号hash不变；重复episode不重复算独立样本；不足20信号日/50episode不能声称效果通过。G10可在“跟踪功能通过、效果观察中”状态交预览，随后P11。

### 18.14 P11：整体内部验收、关旧写、回收冗余（U12、S07、S08）

#### P11-01 做真实功能和增长联合验收

- **目的/前置**：G10；不以某一组测试全绿代替产品完成。
- **步骤**：①执行§15、§17.12全部反例；②测真实数据本地API/首屏/快速切换/慢源；③对照P00存储基线，报告真实事实、身份、重复内容、缓存净增；④列每个旧模块和新模块状态；⑤PIT不足/源缺失/算法效果不足分别标，不混为一个“通过”。
- **产物/验收**：功能、数据正确性、性能、存储四项分别判定；同输入重复内容新增0；有严重日期/关系/身份错误则不切主入口。进入P11-02。

#### P11-02 确认所有迁移域已停旧写并准备回收

- **目的/前置**：P11-01；不能长期双写两套库。
- **步骤**：①复查P00所有writer，已迁移域只能写新物理结果；②检查新旧读消费者全部兼容；③生成精确回收清单及被引用保护原因；④分关系旧副本、结果旧副本、解包缓存、备份逐类给行数/字节估计；⑤检查最新旧发布仍能通过resolver/result binding完整读取。
- **产物/验收**：止旧写证明、回收预览；没有以整个data目录/表名前缀批量删除的模糊清单。进入P11-03。

#### P11-03 按明确范围回收，或登记等待用户选择

- **目的/前置**：P11-02且实施时已获得对应回收范围授权；当前仅文档请求不授权删除。
- **步骤**：①只处理验证等价的冗余副本或可再生且无引用缓存；②按§17.9事务和路径边界执行；③重读受影响发布/页面，核对实际行数和空闲块；④唯一原始源/用户保留备份的取舍未获确认则保留并写WAITING_DECISION；⑤物理库压缩非必须，不因未压缩再次造大备份。
- **产物/验收**：删除了什么、仍保留什么、逻辑/物理实际回收多少清楚；无业务历史损失；恢复演练不作为本阶段任务。未执行清理时不能写“空间已回收”，但止增长成果可以独立通过。进入P11-04。

#### P11-04 切新主入口并给最终交接

- **目的/前置**：P11-01数据/功能/存储止增通过，P11-03结果已如实登记。
- **步骤**：①默认首页切到新本地双轨+已验证在线卡；②保留旧研究工具正常入口，不恢复错误旧优先榜；③总结已上线、部分可用、效果观察、待决定回收四类；④列下一阶段仅剩的具体task_id，不写笼统“继续优化”。
- **产物/验收**：用户可从首页进入当前和潜在板块对应股票，能看来源/风险/等待条件；每日重复运行不再复制关系/结果；效果不足仍PREVIEW。G11关闭的是本版工程任务，不是保证未来上涨。

### 18.15 原U/O/S任务对照与不遗漏检查

| 原任务 | 本章执行落点 |
|---|---|
| U00 / S00 | P00-01～03 |
| U01 | P01-01～02 |
| U02 / U03 | P05-01～03 |
| U04 / U05 | P06-01～03 |
| U06 | P07-03（须G03/G04），相关表设计先在P00固定 |
| U07 | P07-01～02 |
| U08 | P08-01、P10-02 |
| U09 | P01-03止痛；P08-02～03完整新界面 |
| U10 | P10-03 |
| U11 | P10-01～02 |
| U12 | P11-01、P11-04 |
| O01 / O02 / O03 / O04 | P09-01 / 02 / 03 / 04 |
| S01 / S02 | P02-01～04 |
| S03 | P03-01～03 |
| S04 / S05 | P04-01～02 / P04-03 |
| S06 | P02-02～04、P03逐域对照、P11-01 |
| S07 / S08 | P11-02～03 / P04-02及P11-01 |

### 18.16 模块完成标准和当前起点

每个任务的证据至少包含：实际输入版本、执行步骤、改动文件、测试结果、一次相应查询/页面结果、未通过项。纯算法任务不强求UI截图；UI任务不能只交源码字符串测试；存储任务不能只交建表成功。

允许PARTIAL：独立在线来源不可用但其他模块正常；评估未到期但跟踪功能正确；数据回收待用户取舍但重复写入已关闭。不得PARTIAL后假称完成的核心缺陷：旧发布读错成员、未来数据污染、结果身份错配、同输入不断重复写、潜在板块没有规定的成员入口。

**下一次真正开始实施时，只从P00-01开始。**本轮仅追加执行手册，P00～P11没有任何一个任务因此被标成已实现。若另一个任务已经实现部分功能，先将其证据逐项对应本章编号，核验后认可已完成部分，不重复重写。

## 19. 2026-09-12执行中续审：接口证据恢复、P04阻塞项与在线聚合补全

### 19.1 本轮审计范围与结论

依据：旧《工作台目标版本：在线事件数据融合改造实施方案V1》、`runtime/longzijue_static_analysis/module_evidence.json`（按模块读取）、all_strings、当前V3、实施台账、P0–P3审计报告、P04-01阶段报告，以及当前build_planner.py、incremental_writer.py、research_v3_schema.yaml。

发现并纠正：旧方案§2.1/§5已列完整外部来源与七池，静态模块也能再次确认；V3§11.1将其降成“host/七池不明”是文档继承遗漏，不应要求后续执行模型重新猜接口。保留的是公开协议与字段证据，不是第三方完整实现或服务端算法。

当前台账P00～P03及P04-01标PASS，P04-02代码/测试文件已存在但本轮读取时尚无完成台账。原P0–P3审计的385通过和迁移一致性属于原审计证据，本轮没有重新跑完整回归、没有重新核验全部生产迁移，不能冒称全量源码无bug。本轮新增问题作为追加审计项，不覆盖他人原PASS记录，也不让历史PASS免除新发现问题。

仅修改本文；未修改实施台账、代码、配置、测试或数据库。纯函数反例通过stdin调用，没有扫描、发布或生产写入。工作区可能随并行实施变化，执行R19时须再次核对当前函数版本。

### 19.2 已完成任务的遗漏及当前P04-02放行边界

| 审计ID | 已有任务/证据 | 本轮发现 | 必须补做/放行标准 |
|---|---|---|---|
| R19-01 | P00-03，research_v3_schema.yaml | Context.run_id/local_date/publication_id/snapshot_id均非空，与NOT_BUILT/无本地在线模式冲突；在线板块/话题/事件DTO尚未完整定义 | P08前新增ResearchContextReady/NotBuilt及独立OnlineContext，或等价判别联合；不能用空串冒充有效run；P09新增独立DTO |
| R19-02 | P04-01 build_planner.py::_future_dates、PRICE_REVISION | lookback=60只排d..d+59；RET60=C[t]/C[t-60]-1在t=d+60仍依赖C[d]。本轮65个合成日历位置反例：d+60的strength未计划 | P04-02正式发布前补端点；按具体指标输入偏移确定影响范围，不能把读取回看长度机械当输出个数。RET60 d+60必须计划，MA60 d+60可不依赖该值 |
| R19-03 | P04-01 members_for | 空集合被`or`当缺失并fallback全证券。本轮显式S1=[]、2只证券，生成2条不真实member_state任务 | 空集合=0成员；缺映射=明确错误/待补映射，禁止隐式笛卡尔积。带日期空集合也不能退回当前成员 |
| R19-04 | P04-01价格/复权分支、PARAMETER_DOWNSTREAM | 价格修订反例market任务=0；复权分支不计划板块/成员/market；下游用固定30日可能漏长期RS/递推影响；未知参数域get(...,())可静默不做 | 建立指标→域→日期→横截面依赖闭包；market/成员/代表/板块等实际消费者逐项证明需算或不需算；未知域拒绝。新增边界测试，不靠对现有6例重复PASS |
| R19-05 | P04-02进行中的incremental_writer.execute | snapshot expected默认来自提交objects；即使仅计划子集，expected==seen仍可成立，未证明全目标快照完整；检查covered_key只比domain/date，未证明frame证券/板块范围 | 快照绑定必须验证全目标计划的完成或复用清单；部分域仅STAGED不得激活；frame业务键和覆盖声明交叉核验，禁止声明股票A任务却写B |
| R19-06 | P04-02接口边界 | planner有quote/sector_base/cycle/mainline/market等域，writer内置共享域只含6域；预计算frame原子写成功不证明daily生产调用真正增量 | 注册执行器矩阵，逐域CALCULATE/REUSE/UNSUPPORTED显式；未注册域不得静默跳过。真实入口从差分到计算再写到绑定测试，不能只传prepared frame完成阶段 |
| R19-07 | P00基线→P02/P03 | 原台账基线映射表仍含已停旧写描述，任务next文字个别与编号不符；多次生产迁移备份记录存在 | 保留历史但追加“当前读写矩阵/证据日期”，核对所有生产调用方；P04-03检查是否形成每小任务一次全库备份习惯，不凭记录就认定自动备份 |
| R19-08 | 后续P09 | V3遗漏lower_limit_pool、市场overview、七池详情及板块/话题API消费路径，部分字段未入表/DTO | 使用§19.3～7，P09验收按数据集/聚合/页面逐行闭合，不只股票热榜通过 |

R19-02/03本轮已用纯函数实际复现；R19-04市场遗漏已复现，其他闭包项为源码检查待逐消费者验算；R19-05/06为进行中代码接口风险，不将未完成实现定性为已发布事故。

当前执行顺序更正：先R19-02/03/04修规划器并内部复验→R19-05/06约束P04-02→原P04-03。R19-01可与之并行但P08前关闭；R19-07随P04-03关闭；R19-08先恢复静态合同，当前网络复测可提前并行，不要求P04执行网络事件采集。**外部接口不属于本地增量writer的强制输入，不能为补接口把热榜/在线请求塞进每日全市场主流程。**

### 19.3 外部接口登记册：已知地址不再丢失

证据等级：STATIC=本轮模块常量确认；HISTORICAL_PROBE=旧V1记载2026-09-11成功探测但本轮未重验原始响应；CURRENT_PROBE=本轮真实请求获得可解析响应。本轮浏览工具尝试pool/detail和market overview被工具安全检查拒绝，**不是服务端404/收费证据**，未取得CURRENT_PROBE。实施P09-01使用项目既有有界HTTP能力复测；不装私有插件、不索取会员token。

所有下表是GET，日期使用Asia/Shanghai主交易日，模板占位符必须URL编码。具体成功码/记录路径以实际响应schema冻结，不根据常量位置猜JSON层级。

| 源ID | 完整URL/查询模板 | 已知证据与用途 |
|---|---|---|
| EXT01 THS_LIMIT_UP | `https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={page}&limit={limit}&field={fields}&filter=HS,GEM2STAR&order_field=330323&order_type=0&date={YYYYMMDD}` | ths_flow_api常量；涨停成员及顶部统计，旧V1记载探测成功 |
| EXT02 THS_LIMIT_DOWN | `https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool?page={page}&limit={limit}&field={fields}&filter=HS,GEM2STAR&order_field=330334&order_type=0&date={YYYYMMDD}` | 同模块常量；跌停成员，不能由涨停池补假跌停明细 |
| EXT03 XGT_PLATES | `https://flash-api.xuangubao.cn/api/surge_stock/plates?date={BEIJING_MIDNIGHT_UNIX_SECONDS}` | xgt_topic_api，旧日期协议记录；题材id/name/description |
| EXT04 XGT_TOPIC_STOCKS | `https://flash-api.xuangubao.cn/api/surge_stock/stocks?date={YYYYMMDD}&normal=true&uplimit=true` | xgt_topic_api；股票与题材多对多，和EXT03同日join |
| EXT05 XGT_EVENT_POOL | `https://flash-api.xuangubao.cn/api/pool/detail?pool_name={pool_name}&date={YYYYMMDD}` | xgt_flow_api明确host及七池常量，见下表 |
| EXT06 THS_MARKET_OVERVIEW | `https://data.10jqka.com.cn/mobileapi/hotspot_focus/market_state/v1/overview` | all_strings及旧V1探测记录；市场概况增强；历史日期能力未知，不自动加date声称支持历史 |
| EXT07 THS_HOT_STOCK | `https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type={hour|day}&list_type={normal|skyrocket}` | api.ths_hot_list及现有adapter；明确四种组合 |
| EXT08 THS_HOT_PLATE | `https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type={concept|industry}` | api.ths_hot_list；板块榜，不是股票榜 |
| EXT09 THS_HOT_TOPIC | `https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/topic?page={page}&page_size=30` | 同模块完整常量page=1/page_size=30，更多页支持待复测 |
| EXT10 EM_HOT_STOCK | `https://gbcdn.dfcfw.com/rank/popularityList.js`；公开入口`https://guba.eastmoney.com/rank/` | 现有eastmoney_hot_rank.py；复用实际参数生成/公开解码，不改平台原排名 |

EXT01/02 `field`字段列表本轮常量证据不足以确定全部字段代码，P09-01先核对响应支持的明文列或既有请求构造，不臆造数字字段清单；page=1/limit=50作为探测预算初值，不宣称龙字诀默认值。源拒绝该参数组合则记录失败并核对协议，不能绕过鉴权。

EXT05七池执行枚举（均在xgt_flow_api静态strings出现，恢复为已知事实）：

| pool_name | 内部pool_type | 页面/语义 | 不允许的推断 |
|---|---|---|---|
| super_stock | SUPER | 强势股池 | 不自动等于涨停 |
| limit_up | LIMIT_UP | 涨停池 | 明确状态后才计封板 |
| limit_up_broken | BROKEN | 炸板池 | 不与全部非涨停混淆 |
| yesterday_limit_up | YESTERDAY_LIMIT_UP | 昨日涨停今日表现 | 不直接当今日涨停或晋级失败 |
| limit_down | LIMIT_DOWN | 跌停池 | 不从负涨幅自行识别精确跌停 |
| new_stock | NEW_STOCK | 新股池 | 不代表新股都涨停 |
| nearly_new | NEARLY_NEW | 次新股池 | 来源选池定义保留，不自行发明上市天数界线 |

七池不是首屏必须发7次：速览先EXT01顶部和必要EXT02；用户切某池才取EXT05相应枚举；“七池总览”显式操作才按最多4并发完成七个请求，分池状态独立。EXT03/04可并发拉取但必须日期一致后聚合，共用12秒总预算和每源8秒预算，单响应上限2MiB、页上限20（达到上限标TRUNCATED）。真实响应需求超过预算时版本化调整，不默默少取称完整。

报价源不是缺省拼URL：继续复用`workbench_online/eastmoney_quotes.py`实际URL生成和quotes_capability，经P09-01验证后登记EXT11；须将该文件实际模板、字段倍率及市场映射复制进后续source_contract，禁止实施者新增腾讯/东财未验证猜测地址。龙虎榜、日历、龙字诀自有鉴权服务不在本轮新增范围。

### 19.4 字段转换恢复及需要新增的DTO/表列

静态字符串能证明字段被引用，不一定证明服务端记录嵌套层级和数值单位；以下分“可确定语义”和“复测后固定倍率”，实现前不能通用猜倍率。

| 来源 | 源字段线索 | 标准字段和处理 |
|---|---|---|
| EXT01/02 | code,name,latest/price,change_rate,amount | security_id/name/price/ret1/amount；change_rate按旧协议百分数÷100需样本确认；price和amount保留原始单位证据 |
| EXT01 | order_amount,currency_value,turnover_rate,open_num,reason_type | seal_amount,float_market_cap,turnover,open_count,source_reason；不拿封单/流通市值当成交额 |
| EXT01/02 | first_limit_up_time,last_limit_up_time；first_limit_down_time,last_limit_down_time | 分别对应上涨/下跌首次末次时间；Unix秒→北京时间；0为NULL，不显示1970年 |
| EXT01顶部 | limit_up_count.today.num/open_num；limit_down_count.today.num | source_limit_count/source_broken_count/source_down_count；实际顶层路径复测固定；msg非空或num为空标阶段提示，不能填0 |
| EXT05 | symbol,stock_chi_name,price,change_percent,turnover_ratio,non_restricted_capital | 明确.SS/.SZ市场映射；名称/价格/涨幅/换手/流通指标；change_percent不能仅凭名字判百分数，复测1只已知行情固定scale |
| EXT05 | first_limit_up,last_limit_up,last_break_limit_up,break_limit_up_times | 首封/末封/最后炸板/开板次数；所属池限定语义，不混作跌停时间 |
| EXT05 | m_days_n_boards_days/boards,limit_up_days,yesterday_limit_up_days | m_days,n_boards,source_limit_days,previous_source_limit_days；连续含义确认前不当consecutive_limit_days |
| EXT05 | surge_reason.related_plates、plate_name | 来源题材说明/关联题材名数组，缺失NULL，不生成事实原因 |
| EXT03/04 | id,name,description；plates、items、fields及股票数组 | 按实际fields列名zip数组，长度不符拒绝；source_topic_id挂成员；不可把数组序号固定成代码/涨幅列 |
| EXT07 | data.stock_list、order、hot_rank_chg、rise_and_fall、rate、tag | platform_rank/rank_change/source_fields，rank_change标SOURCE_PROVIDED；rate不未经证据当收益率 |
| EXT08 | data.plate_list、code,name,hot_value,hot_tag、ETF相关字段 | PlateHotRow，保留source_fields；ETF关联仅元数据，不进入A股成员清单 |
| EXT09 | data.topic_list、title,subtitle,description,jump_url | TopicHotRow及安全外链；无股票成员接口时不伪造题材持仓/成员 |

新增计划DTO：OnlineContext、EventPoolRow、EventHeader、TopicSummary、TopicMember、PlateHotRow、TopicHotRow；禁止把股票MemberRow的required role/rps/primary_sector硬塞到纯在线记录。

§8.3 online_pool_entries需补`float_market_cap DECIMAL(28,2),open_count INTEGER,last_break_time TIMESTAMP,source_reason VARCHAR,source_fields JSON`，均可空；已有price/amount/seal_amount语义保留。顶部聚合不是成员行：新增`online_event_header(batch_id PK,counts JSON,rates JSON,scope JSON,source_notice VARCHAR)`保存允许归档的收盘头，不能把头计数再造N条股票。盘中使用内存同DTO，热榜仍禁止落表。

率字段必须拆`seal_rate`与`broken_rate`：静态limit_count_api中名为limit_up_ratio的示例实际上是broken/(limit+broken)，不能照名字映射为封板率。封板率=limit/(limit+broken)，仅同口径互斥完整时计算；source_rate另保留原语义标记。

### 19.5 请求→聚合→API→页面完整链（补原P09漏项）

| 功能 | 上游调用/聚合 | 本地服务API | 页面与验收 |
|---|---|---|---|
| 速览统计 | EXT01头复用、EXT02明细，EXT06独立增强 | 既有计划events/overview | 同口径头计数与分页去重计数分列，差异有原因；EXT06失败不白屏 |
| 七池详情 | EXT05指定pool，按源symbol去重，不跨池抹掉角色 | events/pools?pool_type=... | 七个枚举均有入口/状态，昨日池展示今日行情和缺失/停牌分组 |
| 涨停简图 | EXT01明确涨停；连续字段与M天N板分开 | events/ladder及新增events/stocks/{id} | 名称价格金额/封单/流通市值/换手/首末封/开板/原因齐列或解释缺失 |
| 最强题材 | EXT03+EXT04同日按题材ID挂接 | events/topics | 源顺序保留，当前/潜在本地背景独立，无映射仍可查 |
| 涨停分布 | 同上题材内明确涨停分桶 | 新增events/distribution | 题材摘要+前5，点击members分页；唯一股票数与归属次数不同 |
| 个股热榜四榜及EM | EXT07四组合按需，EXT10独立 | hot-rankings | 平台排名不重排，源失败各自提示，本页补本地字段 |
| 热门概念/行业 | EXT08两类按需 | **新增GET /api/v3/hot-plates?type=concept|industry** | 独立板块DTO、名称/热度/原顺序；点映射本地板块，否则只看源信息 |
| 热门话题 | EXT09 | **新增GET /api/v3/hot-topics?page=&page_size=30** | 标题摘要/安全链接，不能用股票API假响应；不强制跳第三方软件 |
| 板块精选在线叠加 | topic→EXACT/RELATED本地关系，事件成员∩本地真实成员 | 新增GET /api/v3/research/sectors/{id}/online-context?context_id=&event_bundle_id= | 来源事件数/成员、本地CURRENT/POTENTIAL/宽度/量额分组；RELATED不得混宽度分母 |
| 单股融合 | EventPoolRow/TopicMember+本地固定context | events/stocks/{id}?event_bundle_id=&local_context_id=可选 | 在线事实、共同改善、普通属性分三组，热度只临时字段 |

新增API均继承§10/§11限制。hot-plates/hot-topics同热榜请求时不跨请求缓存、不持久化，不能以改名“板块属性”绕过热榜限制；source_fields只在响应内。首页另发events/overview和紧凑topics摘要，不阻塞home/local，不将两类日期混为一套“今天”。

明确排序冲突：旧V1简图默认“高度↓、末封↑、封单↓、代码↑”；V3§11.4写首封↑。本次采用**高度↓、末封↑NULL最后、封单↓NULL最后、security_id↑**作为默认，另允许sort=FIRST_LIMIT_TIME明确选择首封；这是客户端产品规则，静态ths_flow默认首封不等于最终页面默认。此节优先，P09须有两种排序测试。

以下旧V1内容不恢复：未校准综合加权总分、热榜跨请求15–30秒缓存、9天5板当5连板、异日背景完全禁止同屏、缺字段重新分配权重伪装可比总分。恢复接口/字段不等于恢复旧算法错误。情绪“亢奋/低迷”等滚动分类仍不作为首版必做，先保留真实指标和历史，不临时造阈值补标签。

### 19.6 P04-02追加实现门：先完整，再最小

R19-02～06不是建议未来再看。执行助手在现有任务内追加内部审计和修复记录，不重跑P00全流程、不覆盖旧台账历史。

1. **区分参数含义**：lookback_sessions用于取输入；affected_output_offsets由各指标函数决定；状态递推另有截止/收敛规则。价格C[d]影响RET60[d+60]，而量额A[d]对prior20影响d+1..d+20，不能套一个统一60天常量。
2. **成员映射**：EMPTY、MISSING、KNOWN分开；历史查询必须带关系/树版本。缺失阻塞依赖成员的任务，技术任务可独立运行；不生成“所有证券×所有板块”。
3. **依赖闭包**：新日、价格修订、关系变化、树变化、参数变化、复权变化六类逐项列输入域和下游。RPS横截面变化可能影响其他股票的队列/角色，不能只改原证券；板块历史RS不是30日窗口可概括。旧market/limit/representative等不在executor注册表时明确保留既有入口或注册委托，不能被省略。
4. **对象粒度**：计划可定位股票行，但现有snapshot_entries每(domain,date)只能绑定一个slice。若当天只修A，构建新完整日逻辑结果时须复用同日未受影响B/C的旧结果，不能用只含A的slice替换整天。明确选择整日结果对象重组或分区清单解析，首版采用整日逻辑结果重组、计算只重算A；额外存储另评估，不能丢行换增量数字。
5. **完整性门**：完整snapshot=新完成对象+已验证可复用对象的目标域/日集合；目标由context/消费者决定，不由提交objects自证。子集写入可以STAGED，不能绑定publication。prepared frame行键不能超出计划重算范围，复用行必须有旧slice来源声明；重新组装与重新计算分别计数。
6. **同输入验证**：执行器接真实生产daily路径，至少一新日、一历史修订、一关系变化、同输入三次。新日可能本来需全A技术，不能用“物理去重了”证明未全历史计算；记录读取/计算/写入三组数字。

新增必须反例：d+60收益、显式空成员、缺历史映射、市场聚合随修订更新、未知参数域报错、全市场RPS下游、A单股修订后B仍在日切片、仅技术域不能冒充完整快照、恶意/错误covered_task声明写别证券、报价源超时不阻塞本地增量。测试先证明能抓当前遗漏，再修复；不得只将预期改成当前代码输出。

### 19.7 后续任务补充步骤与当前交接

| 任务 | 追加小步骤 | 验收和时限 |
|---|---|---|
| P00-03补项（不重做） | R19-01 schema补判别模式、在线DTO、EXT登记引用 | P08前必须通过NOT_BUILT/仅在线context测试；新增版本不改旧哈希历史 |
| P04-01补项 | R19-02/03/04反例→依赖矩阵→修正规划 | P04-02正式写绑定前关闭 |
| P04-02当前项 | R19-05/06对象/计划/快照覆盖及真实入口验证 | 全部目标新算/复用可解释后才PASS；原子提交本身不够 |
| P04-03 | 复查备份次数/源包受保护及缓存限额，保持“不要复杂灾备” | 报当前增长而非仅引用昨日基线 |
| P08-01 | 加无研究run响应和独立在线context；扩展未知状态/暂不可用字段 | 不强行造run_id、不能让在线页依赖本地构建 |
| P09-01-A | 从§19.3导入已知端点/七池/字段线索 | 先静态登记，不能再写host未知；不需要从头反编译 |
| P09-01-B | 有界逐源当前复测，固定响应路径/倍率/范围/分页 | STATIC/HISTORICAL_PROBE/CURRENT_PROBE分列；工具拒绝不判源不可用 |
| P09-02-A | 头统计DTO和成员DTO分开；恢复缺失字段及七池语义 | 原始封板率名称误导的反例通过 |
| P09-02-B | topic join、分布、代码去重、收盘批次与盘中内存分离 | 全局数/题材归属次数/来源覆盖分开 |
| P09-03-A | 速览→七池详情→题材→分布→简图→单股事件 | 每功能有API和页面，不能只有四个tab空壳 |
| P09-03-B | THS四股榜+EM+概念/行业+话题 | 每榜独立DTO/路由/失败状态/零持久化证据 |
| P09-04 | 在线板块context与单股context接本地双轨、盘中成员 | 三层依据可见；映射未知照样看源事件；昨日背景标日期 |
| P10/P11 | 按§19.5每行验收并与旧V1功能清单交叉核对 | 不能因股票热榜能用就声称在线聚合全部完成 |

文档间优先级：本§19修正的端点、排序、缺项优先于原§18及更早章节；后追加的§20明确裁决和当前阶段状态优先于本节。未被明确修订的技术约定保持。旧在线V1作为端点历史证据，不重新成为并行实施方案。

**当前交接摘要**：保留P00～P03已有成果；复开P04-01明确问题单，不抹掉旧PASS历史；P04-02暂不以完整发布成功结项，先补规划反例及完整快照门；在线合同立即按已知证据登记，联网验证和聚合功能由P09落地。此次发现既有接口继承遗漏，也有当前规划正确性缺口，不能只补网址后继续原样执行。

## 20. 跨文档全范围复核、合同优先级与执行补漏

### 20.1 复核输入和诚实边界

本轮继续核对：龙字诀最终取舍版（含六会员功能采纳表）、在线事件V1、Sol双线V1、Astra V2/V2修订说明、V3第1–19章、M7–M15 v2.1相关模块/合同，以及实施台账、P0–P3内部审计、P04-01/02报告。重点源码包括V3配置/schema/校验器、planner/writer、现有报价adapter；不把“读过文档目录”说成已逐行审计M0–M15所有源码。

结论：**仍有遗漏和冲突，需要按本章修订，不能宣称全部无遗漏。**本轮补的是全功能覆盖对照和可定位问题，不重新执行385项回归，不修改生产DB，不重写他人台账。任务进度已变化：P04-02现已被执行任务标为PASS；其报告只证明协调器的有限范围，不证明原P04-02规定的每日主流程已经接入。

纯函数实测新增证据：`research_v3_contracts._type_matches`接受`2026-99-99`为date、`NOT A TIMESTAMP`为timestamp、NaN及Infinity为number，四例均返回True。因此P00-03“类型合同已冻结”不能替代输入合法性验收。

### 20.2 合同优先级：执行模型必须按这张表裁决

本项目正常联网、无外部独立审计角色、不新建复杂灾备，这些已由用户明确，不再拿旧里程碑限制反复要求确认。用户最新明确要求优先；然后是本文明确修订；旧阶段文档是实现历史，不是新功能的否决权。

优先级：用户最新明确取舍及项目只读输入/不改历史等有效边界→本章指定裁决→§19修订→§18执行步骤→§17存储修订→V3其余业务规则→被明确保留的旧合同。旧V1/V2/M7–M15计划只用于追溯来源，不能与V3并行指导实现。最新章节仅覆盖其明确修改点，不是随意推翻全部前文。

| 冲突范围 | 旧规定/来源 | V3裁决 | 实施方式与测试处理 |
|---|---|---|---|
| 首页/优先研究 | M15_OVERVIEW_V1_0保留候选原顺序、行业/概念按旧rank | 新首页用CURRENT/POTENTIAL与20/20清单 | 新API合同，旧历史接口保留；新UI测试不能继续断言旧候选顺序 |
| 板块关联 | STOCK_SECTOR_ASSOC_V1要求当前/再加速、RET20门 | 新关联接受潜在角色与短期改善 | 新research_association，不用旧门否决潜在；旧结果继续旧解释 |
| 结构核心 | 原五类CORE/第一版等级 | CORE仅结构含义，不等于今日重点 | 保留旧队列算法，新增研究资格；不改历史等级 |
| 行业/概念范围 | M15首页只行业/概念 | V3正常属性可含风格/地域，来源类型分别排名 | 语义桶仍过滤行情标签；旧UI类型限制不套新榜 |
| 路由/证据 | M15固定子页枚举、抽屉语义；部分旧测试要求details | V3子页、角色选择、居中modal | 扩枚举并兼容旧URL；更新已被明确替代的UI断言，不把它们当回归缺陷 |
| 在线UI准入 | M14个人复开旧文禁止API/UI/生产消费 | V3允许已验证A/B来源在本地工作台正常显示 | 新在线合同/capability记录替代旧UI禁令；不宣布拥有第三方永久许可 |
| 报价观察期 | M14报价10交易日观察/NOT_VERIFIED | 不以旧固定等待期阻塞V3展示；验证单位/市场/来源时间后按能力启用 | 无来源时间仅观察时间展示；严格盘中排名能力另判，不用假时间过门 |
| 热榜历史 | M14早期隔离批次、旧方案短缓存 | 请求时直取，真实热榜不落raw/行/batch/history | 旧历史批次仅解释已有产物，不复活采集器；新测试查零持久化 |
| 当日涨停事实 | M13或最终取舍早期版本本地优先、在线校验 | 已验证在线事件优先；本地规则保留估算/历史切换 | source/basis分开，不能用本地补零掩盖在线缺失 |
| 成员快照/结果物化 | 每日全量成员、每slice全量输出 | 慢变关系和共享result对象 | 保留旧ID映射与等价查询，不让物理表形状束缚新存储 |
| 金额A | M9旧成员量比中位与M10正式A并存 | 明确用正式共同成员总额比 | 这不是废弃所有旧公式，旧代理只诊断，不同名替代 |
| 备份/恢复门 | M15恢复演练、迁移副本等旧流程 | 不作每阶段必需交付/放行条件 | 仅必要事务和明确迁移验证；禁止借旧门每小任务复制全库 |
| 前瞻评估 | 旧Forward只支持五类结构、禁止改历史 | 新板块outcomes独立，可做只读未来结果统计 | 未来数据不进入信号，旧Forward不重写；不以旧“非模型拟合”文字阻止新描述性评估 |

合同冲突处理固定步骤：列旧条款→列对应V3条款→判RETAIN/REPLACE/COMPAT_ONLY/DEFER→确定新contract ID和读写范围→添加新规则正反例及旧历史兼容测试→台账登记。禁止只把旧断言删掉而无替代测试；禁止改已应用SQL哈希或旧输出使新规则“兼容”。新参数/DTO版本化更新，旧证据中的hash保持原样。

### 20.3 全功能需求追踪：采纳的不能静默消失，后置的不能偷偷复活

| 原需求/模块 | V3最终处置与落点 | 补漏验收/任务 |
|---|---|---|
| 市场概况→板块→成员 | 保留渐进路径；当前/潜在双轨 | P08首页两次点击到股票；P09补在线独立卡 |
| 当前强与潜在转强 | 两轨独立，不用旧主线等级替代 | P06三分支/失效、P07对应成员、P10后续结果 |
| 近期强势/昨日首板等标签 | 保留附加标签但不占正常板块席位 | P06/P07剔除后从完整合格正常板块补位，再应用显示上限；不足不凑弱板块 |
| 今日领涨与提前个股 | 四角色、两清单 | P07每卡3只，今天强不等于20日最强；风险股事实榜仍可见 |
| 天眼模式借鉴 | 个股透视：结构/MA/量额/风险/板块/在线事件 | P08/P09/P10共用modal，不能只保留一个股票名字弹窗 |
| 梯队周期借鉴 | 当日事件梯队+昨日涨停今日表现+既有历史晋级 | P09补时间/来源/缺失分母；不只做静态高板列表 |
| 智库借鉴 | 只读属性库/交并排除/结构筛选 | P10名称选择与角色筛选正常可用，非会员私有库复刻 |
| 主线周期借鉴 | 中期主线背景保留，不作为新CURRENT必需门 | P10确认旧主线查询、证据可达；不全量重算旧历史 |
| 题材周期借鉴 | 5/10/20/30矩阵+留存/扩散/历史代表+新信号 | P10以指标切换呈现，不能仅链接旧页面便算升级 |
| 大盘周期借鉴 | 市场广度/涨跌停/金额/新高/趋势覆盖历史 | 旧历史与在线历史分源，缺历史留空，不复制黑盒温度分数 |
| MA、成交额、换手、异常放量 | 已知本地量额/MA复用；换手需可靠当日流通股本或来源 | 补见20.5；不能因technical表无turnover就把该需求删掉 |
| 新高/RPS/内部K线 | 已有20/30/60/100日及图表保留 | P10实际点开历史图；本地OHLC与调整基准一致。新在线K线后置，不恢复外部终端跳转 |
| 在线最强题材/分布/简图/速览 | §19完整链 | P09分别验收，不把四个tab当四项完工 |
| 热榜四股榜/EM/概念/行业/话题 | §19 EXT07–10及独立DTO | 每类榜单至少成功/失败/空态，未知源名次不自己重排 |
| 平台同时上榜、本地研究命中 | 旧在线V1要求，V3未明确落点，现恢复临时筛选 | P09同请求交集；查全榜覆盖后才称完整交集；不保存热榜交集历史 |
| 真实题材原因/炒作说明 | 已验证来源说明，缺失不生成 | P09源描述保留source与更新时间，价格模式不冒充原因 |
| 在线+本地板块精选 | 双轨本地主体+事件证据联动 | §19online-context；热榜仅临时显示，不构成永久入选依据 |
| 导出包/登录会员/投资日历/跳转 | 用户不需要，本版EXCLUDED/DEFER | 不生成隐含前置任务，台账“以后导出合同”不能误成必做 |
| 龙虎榜/AI复盘/训练模型 | 后置，不阻塞当前本地和公开事件 | 后续需单独需求；不以“AI价值”偷偷调用收费模型 |
| 数据膨胀/静态增量 | §17必做 | P02/P03止重复、P04生产接入、P11回收独立验收 |

六会员模块只采纳上述可解释研究组织方法，不恢复会员校验、私有服务或未经证实的服务端算法。此表替代“看起来差不多就保留了”的验收方式。

### 20.4 已执行阶段逐阶段复核及待关闭项

状态词：EVIDENCE_RETAINED=既有成果证据继续有效；REVIEW_REQUIRED=新增问题需专项验；SCOPE_PARTIAL=已证明的范围小于本阶段完整要求。本轮不直接修改原台账行，请执行任务追加复验行，不抹除历史。

| 阶段 | 本轮判断 | 补项与截止 |
|---|---|---|
| P00-01 | EVIDENCE_RETAINED，映射为旧基线 | 追加当前读写矩阵；纠正日报导出“以后确认”与用户明确不做；P10前逐入口核对 |
| P00-02 | EVIDENCE_RETAINED，容量非当前值 | P04/P11重新量化新增和空闲块；不能用迁移前1.6GiB说明当前空间 |
| P00-03 | REVIEW_REQUIRED | 日期/时间/有限数值校验缺陷；R19无run/纯在线DTO；配置是否完整覆盖公式，见C20-01 |
| P01-01 | EVIDENCE_RETAINED但只证明热榜路由解锁 | 新增events/hot-plates/quotes路由都套同网络与DB隔离边界，P09必须故障注入 |
| P01-02 | EVIDENCE_RETAINED于原榜 | 新四榜/板块榜/话题榜、同请求交集的分页和源失败再验，不能用原测试代替 |
| P01-03 | EVIDENCE_RETAINED于当时UI | P08复核路由刷新/返回/键盘焦点/异步防串，旧modal修复不是新页面验收 |
| P02-01 | EVIDENCE_RETAINED，需补边界样例 | 来源完整性/同日多观测/属性单变/A→B→A/重复输入；发布选观测时间不猜交易日最新 |
| P02-02/03 | 6快照及9/10树等价证据保留 | 验证新观测的父派生不依赖legacy快照；不能只有旧迁移样例正确。名称编码检查独立于终端渲染 |
| P02-04 | 旧全量新写关闭证据保留 | 新增所有调用方检查和真实新发布→属性/交集/历史反向查询；历史兼容器不得变成常驻旧新双写 |
| P03-01 | EVIDENCE_RETAINED | 共享内容不能丢身份/质量；迁移后新contract增量输入再次验，不能只证明旧回填 |
| P03-02 technical/strength/high | EVIDENCE_RETAINED | high window维度/元数据兼容已记录；补验修订单一证券后的整日完整结果读取，与R19-05联验 |
| P03-03 member/structure/summary | EVIDENCE_RETAINED | 旧表暂保留不是止增长失败，但P11有退役清单；切勿按“兼容视图行数”当实际物理占用 |
| P04-01 | REVIEW_REQUIRED | R19已复现规划遗漏；先修再测，旧PASS不能遮蔽新增反例 |
| P04-02 | **SCOPE_PARTIAL** | 报告明确未改旧全量build_m8_m9_preview入口，仅真实证券65输入行、两个技术对象临时库验证；原要求的生产daily差分→计算→写→绑定尚未证明。追加P04-02-INTEGRATION，不声称工程止增长已完成 |

P04-02继续工作顺序：R19规划正确性→writer完整性→domain执行委托→真实主入口集成→同输入/新日/历史修订/关系变化验证。P04-03缓存只读盘点可并行，不能用先做缓存清理代替本地增量缺口。真实生产激活需这些门全部通过，但无须重做P02/P03已证明的迁移。

### 20.5 新增规格缺口与明确裁决（C20问题单）

| ID | 缺口/冲突 | 本次明确处理 | 落点/验收 |
|---|---|---|---|
| C20-01 | 校验器只看date正则、timestamp含空格、number类型 | date解析真实日历；timestamp必须合法ISO8601且带时区；所有数值math.isfinite；比例/页码另范围约束。scalar数值也查有限性 | P00-03补验/P08前；上述四反例均拒绝，合法闰日和+08:00通过 |
| C20-02 | 配置与公式不完全一一对应，SETUP/RECOVERY流动性和MA条件易漏 | 建“公式谓词→配置键/固定语义→测试”表；§6所有谓词都执行，不把配置没写requires_liquidity理解成无需流动性 | P05前冻结配置新版本；资金不足SETUP/RECOVERY均false |
| C20-03 | 全部板块ALL被写成“全部正常板块”，语义标签会消失 | CURRENT/POTENTIAL只正常；ALL可type/bucket筛正常或行情标签，默认正常但有明确全部类型选择 | P08/P10；近期强势可检索但不占主关联 |
| C20-04 | 85日预热与保留100日新高能力混淆 | 85仅V3短窗研究初步预算；保留high100必须101有效收盘，连续状态还需已存前态/左截断。planner按域实际需求，不硬截85 | P04/P05；high100不因新builder短窗变全NULL |
| C20-05 | 潜在股票条件消失保留1日，却无股票跟踪状态字段 | 增research_stock_watch_state，PK(run_id,security_id)，signal_start_date、last_qualified_date、miss_sessions、state、prior_run_id、exit_reason；仅跟踪已入清单及暂停对象，非全市场历史长episode | P07；股票暂停与板块暂停独立，不无限保留；一期数据不足标未知 |
| C20-06 | 风险页/移出记录说保留，但shortlist枚举只有3类 | 风险作为独立GET research/risk-items，筛stock_states已知风险并按确认日/证券ID稳定排序，默认20分页；移出GET research/shortlist/changes，比较绑定前run，不写热榜结果 | P07/P08新增DTO/路由；重点退出后仍能看原因，不丢到无入口 |
| C20-07 | CURRENT板块并不总有研究触发，原图易混 | 卡片始终显示当日领涨前3与触发数；触发0明确为0，不能拿领涨补FOCUS；潜在0成员也需原因 | P07/P08回归 |
| C20-08 | 源码eastmoney_quotes只支持SH/SZ且quote_time=NULL，V3要求严格LIVE榜 | 标OBSERVED_QUOTE展示与TIMESTAMPED_RANK能力分开；无源时间只显示来源时间未知的采样表现，不能通过严格同一时刻排名门；BJ独立能力缺失不把全板块失败 | P09-01/04；批次按支持市场分组，未知成员留空并给覆盖，不拒绝整板块 |
| C20-09 | 股价/换手/异常量额未完整落字段 | 复用technical amount_vs_prior20；换手须来源值或明确流通股本与volume单位，不拿成交额/市值伪算。MemberRow添加turnover、turnover_basis、amount_vs_prior20可空，列设置展示 | P05/P08/P09；无股本说明不可用，不硬补0 |
| C20-10 | 题材聚合少明确连续板与跨日晋级分母 | 昨日涨停→今日确认涨停/未涨停/停牌/未知分组；晋级需前日明确连续板与今日事件，同源同范围。9天5板不算连续5 | P09/P10；分母含未知单列，不把未覆盖当未晋级 |
| C20-11 | 成交额聚合数据源时点不足 | 源题材sum同日可得amount并报valid_count/coverage；本地昨日amount单独列背景，不能混进在线今日总额 | P09；同股多题材全局金额去重，题材内各自计 |
| C20-12 | 首屏/详情API cap与total语义混乱 | total=当前查询可分页总数；eligible_total=限额前资格数量；display_limit=本清单上限；候选更多走明确全资格接口，不使20清单翻页到1200 | P08所有列表schema统一，旧total_eligible别名需版本映射 |
| C20-13 | risk/lifecycle为空的CURRENT被schema强制潜在生命周期 | CURRENT无潜在episode时lifecycle=NULL或NOT_APPLICABLE（选择NULL），signal_date为当前资格日；不能捏造QUALIFIED潜在记录 | P00 schema补项/P08；普通CURRENT响应能通过 |
| C20-14 | sector新API的id编码和复合source身份未冻结 | 路径encodeURIComponent，服务端一次解码；源topic_id带source命名空间，避免两源相同id串板块 | P08/P09；带冒号/中文/同数字id反例 |
| C20-15 | 队列/旧member_state与新EARLY宽度可能回接形成循环 | 基础股票信号不调用旧强关联；early_width用未限额基础信号，角色和名单是最后一层 | P05/P06/P07依赖测试，数据量变化不改分母定义 |
| C20-16 | 现有日构建尚未集成，按P04协调器PASS会误放后续 | 新增P04-02-INTEGRATION，明确生产调用、失效范围、复用和绑定全链验收；未接入旧入口不能称止增长完成 | G04之前关闭；与R19-06同一问题关联，不重复造两个修复 |

未在本轮实测的条目是规格/实现缺口或复验要求，不一律声称已发生生产bug。R19与C20有重叠时共享证据和修复，不让同一任务重复实现两次。

C20-01的带时区要求针对API/外部输入合同中的timestamp，不据此批量改写旧数据库时间列；旧库时间由适配器按其已声明时区转换。没有已知时区的历史值标记未知，禁止猜测后冒充可靠时间。

### 20.6 在线报价接口补齐到具体模板，避免继续“参考某文件”

EXT11现有源码模板：`GET https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f2,f3,f6,f12,f13,f14,f47,f168,f170&secids={comma_separated_ids}`。当前源码批量上限50；SH→`1.code`，SZ→`0.code`，BJ未支持。响应读取data.diff：f2价格、f3涨幅百分数÷100、f6金额、f12代码、f13市场、f14名称、f47成交量、f168换手百分数÷100。实际倍率和成交量单位由当前复测确认；源码未返回可靠quote_time，不把f170或采集时间猜成时间字段。

同板块>50成员时按已支持市场拆批，并发<=4，总预算12秒；部分失败返回覆盖和失败批次，不能仅因为BJ存在使SH/SZ全部不可见。这个接口清单是当前代码证据，不代表本轮重新验证了服务可用性。

补充跨源交集能力：source=ALL时两个榜单各自取完整可用集合后按规范证券ID求交；如只取当前页，则只能标“当前页交集”，不能称同时上榜全集。筛“本地研究命中”用当前固定run清单做请求时连接，不写回热榜或研究run。不同时取不需要的其他六类榜，避免一次刷新所有来源。

### 20.7 后续每个模块的新增放行检查

| 模块 | 还须执行的检查 | 不得再据此偷换完成含义 |
|---|---|---|
| P04剩余 | R19闭环+C20-04/16生产集成，缓存只读预览可并行 | “writer能写两行”不等于每日已增量 |
| P05 | C20-01/02/04/09特征与配置对照，MA/股本/复权/缺日 | 读取旧字段不是复核其语义 |
| P06 | 参考总体覆盖、板块类型、早期宽度分母、潜在状态 | 调阈值凑足6块不叫通过 |
| P07 | C20-05/06/07/15，LOO主备选和两清单、暂停状态 | 有SQL表不等于完整关联产品 |
| P08 | C20-03/06/12/13/14、无run/纯在线模式，旧URL兼容 | 为旧M15断言回退新布局不允许 |
| P09 | §19各EXT/池/聚合/API/页面、C20-08/10/11/14 | 合法公开源可用就可按V3启用，旧“在线UI禁用”不再阻塞 |
| P10 | §20.3逐行、六会员借鉴、矩阵/K线/MA/换手入口、真实结果追踪 | 历史样例未到期不能宣称预测完成 |
| P11 | 问题项关闭/有明确受限状态、旧历史兼容、增长和回收分开 | 测试绿不覆盖功能遗漏，旧FULL_PASS不屏蔽新问题 |

新增合同裁决字段写入实施台账：`issue_id,old_clause,v3_clause,decision,affected_task,new_contract_id,evidence,status`。不用增加外部签字或每项单独20页报告。当前任务先读取本章及§19，追加复验记录；不直接继续宣称P04所有门已过。

### 20.8 防止再遗漏的交付清单

每个采纳需求必须有五个可定位项：输入/数据源、计算或转换、存储或明确不落盘、API/页面、验收证据。任一空白不能标整功能完成。每项EXCLUDED/DEFER必须能指出用户取舍或本文明确决定，不能因为实现难就静默后置。

本轮已完成跨文档范围对照和上述确定性反例检查；没有重新逐行证明所有旧源程序正确。文档修订完成不等于代码问题已修。最终交付按模块报告工程可用、来源受限、效果观察、待回收四类，不再用一个“全部FULL_PASS”覆盖不同层次。

## 21. 伏羲同花顺 API 候选补位：不改变龙字诀在线主线（2026-09-13）

### 21.1 来源边界和合同裁决

本章依据[接口索引](https://fuyao.aicubes.cn/llms.txt)与[完整接口文档](https://fuyao.aicubes.cn/llms-full.txt)登记**增强候选**；以各[接口参考页](https://fuyao.aicubes.cn/docs/api-reference/overview/)核对实现时最新约束。§22明确裁决优先于本章任何看似要求“先伏羲、后龙字诀”的表述。**在线产品形态、页面组织、主数据链先参考龙字诀解析实现**：EXT01/02同花顺池、EXT03/04选股通题材与成员、EXT05七池、EXT06市场概况、EXT07/08/09同花顺热榜按各自能力验证。伏羲FY系列只在某项主链缺字段/不可用或确有单独研究价值时按需评估，不批量铺满项目、不把API Key当P09核心门。本项目自行补的东方财富报价EXT11和非龙字诀东财热榜不作为目标版本来源；历史M14证据保留。EXT10东财字段即使属于旧解析线索，也受用户“不使用东方财富接口”的最新选择约束：保留历史记录、目标版不调用。新UI/新服务不用东财；现存旧入口退役/兼容按P10回归。本轮只修文档。

官方文档公开可读≠免鉴权/已获API调用权限。REST基址`https://fuyao.aicubes.cn`，请求头`X-api-key`；HTTP 200仍需检查信封`code`，`code=0`才是业务成功；`2001/2003`认证/权限失败，HTTP 429或`code=4001`限流。密钥仅由本地环境或保密配置注入，绝不写文档、日志、URL、DB和前端；无密钥先做合同与样本验证，不宣称已跑通。数据时间戳是毫秒Unix时间、上海时区解释；区分`data.timestamp`定义中的“上游有效时间”“组装时间”“交易日零点”，不一律当逐股成交时间。单源能力按`DOCUMENTED → AUTHORIZED → CURRENT_PROBE → NORMALIZED → PRODUCT_ENABLED`逐层放行；用户判断“多数可用”是选型依据，实际项目每项仍需当前API key与响应验收。

### 21.2 接口—模块逐项映射与数据缺口

| 新source ID、官方接口 | 具体用途与规范化 | 不可误用/缺口 |
|---|---|---|
| FY01 `GET /api/a-share/prices/snapshot?thscodes=...` | **仅有明确研究用途时**给个股研究卡/板块可见成员按代码批量补价、涨幅、股数、成交额；`thscode`后缀→`SH./SZ./BJ.`，`price_change_ratio_pct/100`存比例，`turnover`是**成交额元**，非换手率；带显式代码时不分页 | 热榜不依赖此接口，也不要求补换手/报价；不省略thscodes去全市场拉；`data.timestamp`是快照最新上游有效时间，非每只股票精确同步时点；**无普通个股换手率** |
| FY02 `GET /api/a-share-index/catalog/ths-index-list?tag=cn_concept|region|tszs|industry`；FY03 `GET /api/a-share-index/constituents/ths-stock-list?thscode=...` | 增设“同花顺板块”命名空间；清单标签分类、按需查单指数当前成员；变化检测后增量更新慢变关系 | 不用同名合并TDX板块；FY03只给**当前**成员，不能回填历史所属；单tag全量，低频缓存而非每页重抓 |
| FY04 `GET /api/a-share-index/prices/snapshot?thscodes=...`；FY05 `GET /api/a-share-index/prices/historical?thscode=...&interval=1d&start=...&end=...` | 板块指数实际涨幅/成交额与历史K线独立展示，与成员中位涨幅/成员成交额求和明确分列；映射`TI`代码后批量请求所见指数 | FY04必须显式代码；FY05单指数、日线、不超过10年；指数成交额口径由源确认，不混成本地成员总额 |
| FY06 `GET /api/a-share/special-data/limit-up-pool?date_ms=...&page=...&size=...`；FY07 `.../limit-down-pool`；FY08 `.../limit-break-pool` | 情绪速览、**完整当日连板梯队**和简图用确认事件集合；交易日用上海零点毫秒，单页1–200，循`pagination.pages/total`有界拉取；源代码+日期+事件类去重，FY06按明确连续板数分组（首板独立） | FY06有`limit_up_reason`、`continue_day_text/cnt`、`seal_money`及涨停时间，但**文档未列换手和成交额**；FY07/08有`turnover_ratio_pct`，FY08另有`turnover`成交额；三池覆盖/更新时间分别标明 |
| FY09 `GET /api/a-share/special-data/limit-up-ladder` | 近30交易日**精选天梯摘录**，附`window.board_caps`和次日`seal_nextday`状态；不是完整梯队的底层来源 | 每板位最多4只，不能单独算完整板位总数、晋级率或板块宽度；完整当日梯队由FY06全部页/已验龙字诀同花顺涨停池生成；跨日晋级率由相邻交易日**完整**事件池匹配生成 |
| FY10 `GET /api/a-share/special-data/hot-stock-list?period=day|hour`；FY11 `.../skyrocket-list?period=day|hour` | 四个股票热榜分别独立Top30；保留`rank/heat/rank_change/rank_trend`原始语义，不改源名次 | 热榜默认只显示代码、名称、名次、热度与来源给出的变化；不要求换手率、报价、成交额或额外字段；`day`在热股为24小时级、飙升为日榜；无同花顺概念/行业/话题热榜接口证明，不用指数涨幅伪造“平台热度” |
| FY12 `GET /api/a-share/special-data/hot-stock-list-history`；FY13 `.../hot-stock-rank-trend?thscode=...` | 用户点击时取历史热股/单股排名趋势，保留来源自然日和榜单缺席状态 | 该历史数据与M14“热榜请求时直取、零持久化”需统一为**请求时读取、不落raw/row/batch/history**；无完整覆盖不推断“未上榜” |
| FY14 `GET /api/a-share/special-data/anomaly-analysis-list`；FY15 `.../anomaly-analysis-stock?thscodes=...` | 有来源的异动标签/原因放入股票证据弹窗，列表按标签查询、个股按可见股票懒取（单次最多50 token） | 来源文字是上游解释，不反推出“必然上涨原因”；不与FY06涨停原因互相覆盖，不做全市场预抓 |
| FY16 `GET /api/a-share/calendar/trading-days`；FY17 `GET /api/meta/tickers/list` | 交易日/股票清单仅作在线对账与代码名称消歧，按源版本/时间低频缓存 | 日历仅最近一年；不能替换TDX原交易日、历史A股资格或已发布本地快照 |

FY01普通报价不含换手率。仅FY07/FY08以及官方竞价`auction_turnover_pct`是明确百分数换手字段，后者仅**竞价阶段**，绝不可冒充全日换手。FY06涨停行的换手率若想补齐，必须有另一个经过验证的**同日期、同口径**来源；没有就NULL+`TURNOVER_UNAVAILABLE`。本地仅有成交股数、没有日期有效流通股本，仍不能反推。金额原值元，统一显示亿/万等中文单位，接口数值不先舍入。参考[股票行情](https://fuyao.aicubes.cn/docs/api-reference/prices/)、[指数](https://fuyao.aicubes.cn/docs/api-reference/a-share-index/)、[涨跌停](https://fuyao.aicubes.cn/docs/api-reference/limit-up-data/)、[热榜](https://fuyao.aicubes.cn/docs/api-reference/hot-list-data/)、[异动](https://fuyao.aicubes.cn/docs/api-reference/anomaly-analysis/)。

### 21.3 页面增强与融合边界

以下FY页面描述仅在§22对应龙字诀主源缺口经验证、或用户确认该项增强有明确价值、且该FY接口已具备权限和当前有效样例后执行；不是P09首版必做清单。已有龙字诀功能首先按§22产品切片交付。

1. 首页只读已有本地run摘要+必要FY01可见股票/FY04可见指数+FY06–08事件摘要；请求独立并行、有单源空态；不因在线失败改CURRENT/POTENTIAL资格，也不把“指数今日涨幅”写成“成员中位涨幅”。
2. 情绪与涨停：FY06–08逐池切页；完整总数来自各池`pagination.total`，独立报告成功/失败/截断。**当日完整梯队以FY06全部页或已验龙字诀同花顺涨停池按连续板数分组**；FY09另设“30日精选天梯，单板位最多4只”，不得混为同一统计总体。昨日FY06完整集合与今日FY06完整集合按代码关联：昨日明确n板且今日明确n+1板为晋级；今日未封、停牌、未覆盖、数据未完成分别列，只有口径/覆盖一致时才公布晋级率。龙字诀源与伏羲源并列可切换，冲突标双来源而非任选非空拼一个事实。盘中/收盘、来源截止时间分开。
3. 板块精选/联动：TDX板块为研究主身份，FY02/03同花顺指数为另一属性视角；跨源关系需要映射证据与版本，不能以同名自动并表。FY04的指数涨跌和FY01成员涨跌同时展示；当前强势板块与潜在转强算法仍本地独立计算，在线事实只做增强证据。点板块才取FY03与成员批量FY01，不预加载全市场DOM。
4. 个股研究弹窗：本地MA/结构/量额与FY01报价、FY14/15异动、FY06事件标签分组；每项显示日期、来源、缺失原因。仅FY07/08对象可显示来源全日换手率，竞价换手另列。没有行情时间不显示“实时同步”。
5. 热度观察：FY10/11四榜先落地，FY12/13点击后懒取；原东方财富热榜与EXT11从新目标版移除。热榜卡首版忠实显示源排名、热度、升降和名称；FY01补报价仅在用户另行明确需要且其研究价值通过验收时作为**可选增强**，缺它热榜照常工作。概念/行业/话题**平台热榜**若龙字诀已解析的公开源合法且复测可用则保留；否则显示不可用，不用FY02指数涨幅或本地强度冒充平台榜。

### 21.4 端内/暂不可用与不纳入首批

`llms-full.txt`中主力资金、部分高频动向、指数概况/成分权重、股票基础信息、个股反查同花顺指数等页面标“后续接入同花顺AI客户端”“当前暂不可使用”或“敬请期待”；即使出现示例路径也不得按已上线接入。财报、估值、基金、期货/期权、在线回测与当前双轨目标无直接前置，DEFER而非自动加入。集合竞价、龙虎榜有文档路径，但用户此前定为低优先；保留后续扩展，不阻塞FY01/06/10。FY02/03已能查当前指数成员，不等于反查指数接口已可用。

### 21.5 按依赖实施，具体任务和放行

本表F01–F07是**选中伏羲补位项后的条件工作包**，并非P09必须串行全部通过的关卡；其列顺序不优先于§22的EXT主线。F00来源裁决可先做，但不得等FY客户端建完才开始EXT01。未触发的FY接口不应新增表、适配器、页面或验收负担。

| 顺序/任务 | 实施点（代码/库/API/页面，仅为后续实施合同） | 验收 |
|---|---|---|
| F00来源裁决 | 对现有EXT01–11、M14东财热榜逐项登记`origin=LONGZIJUE_PARSED|PROJECT_ADDED|FUYAO`；取消EXT11反复重试作为其它源的前置门，先验证龙字诀主线EXT01–09；旧报告保留 | 可证明主线来源留存名单；新目标链对东财调用为0；台账仅追加裁决不改旧BLOCKED事实 |
| F01鉴权/客户端 | 新`workbench_online/fuyao_client`统一X-api-key注入、超时/并发/响应大小、HTTP+业务code、无密钥/429/失权降级；键不落盘 | 用脱敏模拟响应测0/2001/2003/4001、HTTP429、超时/空item/时间戳；没有密钥仅DOCUMENTED，不发伪通过 |
| F02按缺口选伏羲 | **不是P09主线前置**。龙字诀单项主链已能完成时不重复造FY接口；确认缺口与产品收益后，才为选中的FY源建版本化合同，明确参数、倍率、覆盖、TTL、落盘/不落盘 | 每个选中源有“替代缺失什么/增强什么”的理由、API Key能力与少量实际样例；未选中源不进入P09验收清单；涨停池没有换手仍可交简图 |
| F03在线报价替换 | 先移除热榜对旧`fetch_eastmoney_quotes`的依赖；FY01只给有实际用途的可见研究卡/板块成员服务，定位`online_hot_rank.py`与`app.py`旧调用点 | 四热榜不发FY01仍可完整展示来源名次/热度；FY01失败不影响热榜；研究卡分源降级；不调用全市场分页 |
| F04事件与情绪 | FY06–08分页池生成完整当日梯队，FY09单列摘录；相邻交易日FY06完整集合建立晋级转移表，分母只计前日已知且今日覆盖可判对象；扩`online_pool_entries`的`provider/source_trade_date/source_asof/coverage`或等价版本化关联；仅成功且获准归档的**收盘事件**持久化，不复制全市场；内部API事件列表/摘要 | 两页以上仍正确total；昨日首板→今日二板正例、9天5板非连续五板、缺页/停牌/未覆盖不进失败分母；炸板≠未涨停；FY09截断不进全量统计；断源保持本地估算明确标记 |
| F05板块身份与指数 | FY02/03低频现况观察、差分关系；FY04/05按可见指数获取；新增跨源映射表含证据/有效时间/状态，不改TDX原关系 | 同名不同代码不自动合并；成员增删只写变化；指数涨跌/成员中位两列可解释；FY03不能生成伪历史成员 |
| F06四热榜与异动 | FY10/11四榜、FY12/13按需历史、FY14/15股票证据；内部API分页/空态和UI五层导航接入 | 源名次不重排；点击弹窗加载原因；不落热榜raw/row/batch/history；无在线原因不从价格推断 |
| F07融合回归 | P09/P10汇总：关闭东方财富新入口；本地run绑定、所有在线来源状态和跨源证据UI；P11阶段内部审计 | 本地无网正常；API key权限变更不触发本地重算；调用量按可见数据上界；各模块可独立标PASS/DEGRADED/BLOCKED，不能一项端内禁用拖垮全项目 |

API新增/调整仅在各任务实施时定版，例如`/api/v3/online/quotes`、`/api/v3/events/{pool}`、`/api/v3/hot/{type}`、`/api/v3/stocks/{id}/source-evidence`，各路由仍须完成§20.8五点；不把建议路径冒充已存在接口。数据库在线事件只保留V3允许的有界归档与来源证据；FY02/03关系做静态+增量；FY01盘中报价、FY10–13热榜请求时读取不落持久行。FY02/03由同花顺定义的板块体系不得替代TDX原标识，也不得改变旧发布哈希。

本章仅完成文档接口审阅，**未使用用户API key、未发业务鉴权请求、未宣称线上数据已经可用**。下一实施任务先按§22的P09恢复路径验证龙字诀主线，不是先完成F01/F02；伏羲任务按缺口后置，不再因东方财富EXT11的`RemoteDisconnected`阻塞其它来源当前复测。

## 22. P09解阻与龙字诀在线功能优先实施裁决（2026-09-13）

### 22.1 为什么当前卡住，以及裁决范围

现有台账`P09-01-A`仅完成EXT01–11**静态登记**，网络请求0；`P09-01-B-EXT11`和`...-RETRY`两次因东财报价`RemoteDisconnected`标BLOCKED，且后者把“下一次仍重试EXT11，未进入EXT01”写成执行路径。EXT11只曾用于热榜报价附加和盘中报价候选，不是情绪、涨停、题材、简图或热榜源名次的输入。**因此旧BLOCKED证据继续真实有效，但仅对EXT11自身有效；它不是P09-01-B整体或EXT01–09的门。**不得把旧报告改成PASS，也不再重试一个已从目标版移除的东财源。当前应该另起内部`P09-01-B-LZ-EXT01`，按下表逐源推进并在实施台账追加“来源裁决/前置解除”记录，不回填历史行。

本节覆盖§18.12、§19.3/19.7、§20.6/20.7、§21.2–21.5在“必须先伏羲/先报价/全部在线源共同成功/东财再试”的冲突；其它技术边界保留。来源优先级不是源之间无证据任意拼字段，而是**产品主链优先**：同一产品功能优先复制龙字诀的请求→标准化→聚合→页面组织；所需公开源当前验证失败才对该数据集选择伏羲等候选或显示部分可用。源成功时伏羲可作为另列对照，不自动替换主事实，不以同一字段非空优先级静默混合。既有本地估算页仍是显式可切换背景，不冒充在线确认。

### 22.2 按功能拆开的当前执行表

| 内部小任务与依赖 | 龙字诀来源主链、具体结果 | 当前验证与放行 | 伏羲何时才进入 |
|---|---|---|---|
| `P09-01-B-LZ-EXT01`；无EXT11/FY前置 | EXT01同花顺涨停池，核字段选择/分页/高度、首末封、来源原因、顶部统计。先完成涨停简图/梯队最小数据底座 | 复用P09-01-A静态URL和2026-09-11历史探测，进行有界当前请求；拿不到响应记EXT01不可用，不牵连EXT03/07。解析字段倍率+分页覆盖才开放对应UI | EXT01失效且需要涨停基础功能时，**单独**选FY06；不同时先实现FY06–09 |
| `P09-01-B-LZ-EXT02`；与EXT01可独立 | EXT02同花顺跌停池；速览的跌停数与明细 | 单源独立状态；不能因EXT01失败就虚构跌停数 | 仅EXT02缺口选FY07 |
| `P09-01-B-LZ-EXT03/04`；题材需二者同日 | 选股通题材元信息+强势股数组，按题材ID join、股票代码去重；最强题材/涨停分布 | 两源同交易日且字段数组可解析才标题材链READY；任一失败只降级题材链，涨停简图照常 | 伏羲指数目录/成员**不能直接等价**选股通“强势题材与原因”；FY02/03仅可作为不同来源属性参考，不能静默替题材榜 |
| `P09-01-B-LZ-EXT05`；七池按需 | 选股通`pool/detail`的super_stock、limit_up、limit_up_broken、yesterday_limit_up、limit_down、new_stock、nearly_new；情绪池与昨日表现 | 先验请求模板及1个池，再逐池验证；单池失败单池不可用；不要求一次抓7池才开速览 | FY06–08只可能补部分涨/跌/炸池，**不能声称补齐另外四池** |
| `P09-01-B-LZ-EXT06`；独立 | 同花顺市场概况顶部；与本地广度/成交额分源展示 | 一次有界当前样例定计数路径、时间与口径；无该源可先展示已验池与本地广度 | FY源如无同等总体/口径就不冒充市场概况 |
| `P09-01-B-LZ-EXT07`；独立 | 同花顺四类股票热榜，保留源名次/热度/升降，按需切榜 | 一类成功即可交该类榜；热榜不依赖EXT11/FY01、不要求换手/成交额；源顺序不被本地重排 | 仅对应类榜不可用时评FY10/11；不是默认改造全部四榜 |
| `P09-01-B-LZ-EXT08/09`；独立 | 同花顺概念/行业、话题平台热榜；保留源热度与来源标签 | 各榜独立状态；无榜不以本地板块强度冒充 | 目前FY02指数目录和FY04指数行情不是平台热榜等价物，不能替换；保留缺项 |
| `P09-04-QUOTE`；主功能交付后独立 | 盘中板块**实时**成员重排才要时间可靠的行情；历史收盘成员仍走本地run | 无可靠报价时只关闭“盘中实时重排”，不阻断G09其它在线主功能/P10；不给热榜加报价 | 确有价值且API Key权限实测后按需评FY01；没有逐股可靠同一时点也不宣称严格同步排行 |

EXT10东财热榜及EXT11东财报价不进入以上目标链；静态注册记录保留用于解释旧实现。**不使用东方财富**优先于旧M14和§19曾写的EM必做项。注册JSON、能力门/旧URL的工程改动留给实施任务，文档本轮不改配置；执行前必须更新注册合同版本和验收测试，不可直接把旧静态登记当运行许可。

### 22.3 功能实现顺序、失败分支和验收

1. **先开P09-01-B-LZ-EXT01**：沿用已登记公开URL，先核请求参数中的字段列表与合法响应。一次小样本当前请求应保存脱敏元信息和字段/倍率证据，不保存禁止的热榜raw；拿不到合法响应则只记该源受限，转EXT03/04或EXT07验证，不能返回EXT11循环。
2. **优先交可闭环的一个产品切片**：EXT01成功→涨停简图/梯队；EXT03+04成功→最强题材/分布；EXT07成功→股票热榜。切片的数据标准化、内部API、页面、空态、来源时间和测试必须一并完成，不能所有源探测完才开始P09-02。情绪速览按EXT01/02/05/06实际覆盖逐格交付。
3. **历史晋级**：按龙字诀涨停池完整分页按高度分组；相邻日同源完整池匹配才计算晋级率。伏羲FY09每板最多4只仅摘录；FY06全部页可在EXT01失效时作为替代底座，但不得改变源标签或拼出虚假完整分母。
4. **伏羲按缺口单项触发**：写明“主源未覆盖/失败什么→选FY哪个端点→有什么非等价字段→需不需要API Key→何时降级”，只实施被触发项。API Key未配置/无权限只限制该FY项，不冻结EXT链或本地run。未经用户另提需求，普通热榜不加报价、换手、成交额附加列。
5. **G09判定分层**：每个切片独立`AVAILABLE/DEGRADED/UNAVAILABLE`与证据；已验核心链可发布预览，未验链保持明确空态/本地估算显式切换。G09整体可以`DEGRADED_PASS`并列出缺页，不能把未实现模块写成FULL_PASS，也不能一项非核心源失败就整个P09永久BLOCKED。P10本地旧功能归位可在已有来源状态登记后继续，P09待补在线切片仍跟踪。

实施者每完成一个小任务在既有内部台账追加`task_id、source_id、contract_version、request_template、probe_time、coverage、normalized_fields、capability、页面/API入口、验收/失败、next_task`；旧P09-01-B-EXT11 BLOCKED不删除，新增一条“EXT11目标版退役、前置解除”裁决。下一任务**明确为`P09-01-B-LZ-EXT01`**，不是`P09-01-B-EXT11-RETRY`、`F01`或全套FY01–17。

## 23. V3 最终研究清单与板块阶段可见性（2026-09-14）

`FINAL_LOCAL_RESEARCH_CANDIDATES_V1`把原结构候选池收敛为可人工研究的最终清单。入选必须同时满足：研究等级为A+或A、主关联板块类型为INDUSTRY或THEME；随后沿用既有本地综合`priority_score`降序排列，分数已组合板块上下文、个股结构/形态、RPS、趋势、位置、成交额和质量信号。接口返回原结构候选数、合格池数、最终名次和逐项入选原因，最终只取前100。STYLE板块不能作为最终清单的主关联板块。

V3首页以列表展示最终清单，列出名次、代码名称、研究等级、最新价、当日涨幅、成交额、RPS20、综合分、个股结构和主关联板块；每页25只。板块卡片同时展示`sector_daily.primary_pattern`形成的本地结构阶段：`CURRENT_STRENGTH`为主升强势、`STABILIZATION`为企稳、`REACCELERATION`为再加速。该结构阶段与“领先行业”的20日相对强度榜、当日“当前强势”筛选是三个独立且并列展示的合同。

多日主线生命周期仍只使用真实逐日累积数据。删除动态历史并只重建单日后，`mainline_daily`应诚实返回`DATA_INSUFFICIENT`，不得用静态关系或未来数据补造退潮、持续、扩散等多日状态；后续每日一键生成会自然积累所需历史。

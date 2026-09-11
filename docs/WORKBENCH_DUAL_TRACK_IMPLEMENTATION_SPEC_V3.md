# 工作台双线改造 V3：功能去留、双轨板块与个股联动实施规格

日期：2026-09-11。状态：设计内部复审稿，可按任务开发预览版；未实施、未完成算法效果验收。

2026-09-11追加：第17章为数据膨胀专项审计与增量存储实施合同，优先于前文“旧库清理后置”和“全部旧物理表保持不动”的笼统约定。先阻止新增重复，再无损归并已有重复；清理仅在实施阶段完成核验后执行，本轮不修改或删除数据库/数据文件。

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
| 本地涨停/连板/晋级 | 保留为本地估算 | limit_ladder、limit_promotion | 在线页默认公开事件；本地估算切换可查，不能无提示补在线缺失 |
| 最强题材/涨停分布/简图/速览 | 新增/改造在线主视图 | 新事件adapter，已有online基础 | §11逐项定义，来源事件榜与本地研究双轨不混榜 |
| 人气热榜 | 保留并扩榜 | online_hot_rank、THS/EM adapter | 单平台单榜按需；实时无历史，不参与持久化研究选择 |
| 板块精选 | 重定义 | 原排名/在线题材 | 不是第3套榜：即CURRENT/POTENTIAL双轨，可叠在线证据徽标 |
| 数据状态/操作维护 | 保留、不扩建 | data-info/operations | 普通入口靠后；不安排灾备演练、不因维护页未升级阻塞研究页 |
| 每日导出/登录会员/投资日历/外部软件跳转 | 本版不做 | 原采纳取舍 | 不生成任务或依赖 |
| 龙虎榜/新闻原因 | 后置可选 | lh_list/external_evidence能力 | 首版不阻塞；已有源题材说明按源展示，不生成伪造原因 |

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

合同`SECTOR_CURRENT_PREVIEW_1`，事实判断而非次日预测。

基础：NORMAL_ATTRIBUTE、n>=5、quote_coverage>=.70、m1/b1/rel1/p1有效。资格同时满足：m1>0、b1>=.60、rel1>=.003、p1>=.80。必须至少3只上涨，top1_positive_share<=.50；极小样本或单股拉动只进入全部板块并提示，不能凑卡片。

CURRENT不要求连续2天，也不要求RPS20高；`confirmed_days`只是附加标签。q20>=.80标“中期仍强”，不改变当日资格。排序固定为(p1↓,b1↓,rel1↓,amount_A↓,sector_id↑)。行业/概念/风格/地域分别计算p1；综合展示按各类分位排序并标类型，禁止混原始名次。

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
| ADDITIONAL_POOL | 选股通/api/pool/detail静态线索 | 域名、七池枚举及字段未在本轮证明；O01验证完整host与免费访问，否则不实现，不能编造七个pool_name补齐页面 |
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

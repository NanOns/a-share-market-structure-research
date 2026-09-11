# Astra 双线方案复审与可执行升级方案 V2
日期：2026-09-11。状态：设计复审完成；实现、实盘界面验收尚未进行。
本文件保留 Sol V1 的目标，替代其未验证算法和有冲突的实施约定。可独立阅读执行。业务代码、配置和数据库本轮不修改。

## 1. 项目约定与审计结论

项目正常使用网络。每阶段的开发助手负责实现、内部审计、缺陷修正和验收记录，不设第三方或外部独立审计角色。跨模块问题单独登记只是防止漏项，不要求另一个人签字。灾备不设实施阶段；数据库事务、写入原子性、迁移前列检查和失败不提交即可。TDX 输入只读。

Sol 的目标方向成立：当前强度、阶段、研究关注应分别表达；重点清单必须有限；在线事件和本地趋势应该结合。**V1 尚不能直接按其中数字编程上线**：它存在数据前提缺失、规则含糊、因果命名过强、盘中融合矛盾、状态依赖倒置，以及把正常突破误判为过热的风险。仅把候选截到20只，不能证明研究价值已经提高。

产品验收先回答三个问题：
1. 今天弱了的历史强板块是否被及时标出？
2. 清单里每只股票能否说清“现在为什么要看、什么情况撤出”？
3. 从一个板块到成员再回到原列表，是否无需复制代码、输入ID或重做筛选？

## 2. 可复查证据与结论边界

本次读取主库 data/database/market_research.duckdb，使用 read_only=True。最新发布为 m4-8a99c99719061f4f1f166d0b9184506c，日期2026-09-10；关联分析域覆盖不同：technical/strength/sector_cycle/member_state为5日，mainline为4日，structure为3日。数据截至该发布，不等于当前盘中行情。

| 编号 | 证据位置 | 本次确认及影响 |
|---|---|---|
| E01 | src/workbench_service/app.py::_overview_strong_sectors | 读取rank后每类取10，没有当日弱化门；标题与筛选条件不匹配 |
| E02 | app.py::candidates | 按旧等级和priority_score排列candidate_daily；最新A+60、A119、B237、C771，合计1187；没有短名单资格层 |
| E03 | mainline.py::classify_mainline_row | 3/5/10条观察分层；短历史会阻止部分分类，不能由大量OBSERVING直接认定模型毫无区分力 |
| E04 | mainline.py::fading谓词 | 退潮条件要求20日百分位、宽度、金额等共同满足；放量下跌未必满足金额下降，可能漏掉当日恶化 |
| E05 | technical.py::calculate_technical_daily；主库describe | 已有MA5/10/20/60、RET5/10/20/60、前20日量额比；没有V1要求的完整POS、ATR、episode、盘中量能曲线 |
| E06 | highs.py::calculate_high_daily | 新高为收盘价严格大于前N日收盘最高，窗口20/30/60/100；不是含当日高价最高；新高距离允许正值 |
| E07 | representative_state.py::_ranked | 代表按member_rank及RET20排序；代表身份不能直接当今日重点 |
| E08 | association.py 与 strength_association.py | 两套关联路径，语义解析不同；candidates调用旧路径，历史关联用新路径，必须统一展示来源 |
| E09 | app.py::request_scope、do_GET | GET整个处理期持有_db_lock并打开连接；热榜等待外部网络也在此范围，可能堵住其他本地请求 |
| E10 | online_hot_rank.py::_direct_source_view | 先补所有行报价再分页；total取分页后长度；双源顺序执行、一个失败可能使整体失败 |
| E11 | router.js、index.html | 已有页面导航和详情组件；应扩展现有壳，不必另造一套独立前端 |
| E12 | 024_m14_online.sql | 已有data_sources、online_fetch_runs、online_batches、online_evidence等，重建注册中心会形成重复身份 |
| E13 | 主库聚合 | sector_member_state_daily为3365740行、31切片；主库1.6GiB。规模异常值得专项排查，但切片多不证明全是可删除重复 |
| E14 | config/workbench_universe.yaml | 当前展示包含沪深北A股、科创；源事件池不一定覆盖同一范围 |
| E15 | runtime/longzijue_static_analysis/module_evidence.json | 可支持来源和客户端聚合推理；不能证明第三方服务器内部如何选出题材/热榜 |

未做的验证：本轮没有重跑全市场扫描、没有加载真实浏览器做交互测试、没有证明新算法盈利能力。此前接口探测作为历史访问证据，不把一次成功说成免费永久稳定。开发时仅对所用公开接口做少量实际请求复核。

## 3. 纠正V1的关键设计

### 3.1 四个独立维度，不把质量、走势、关注强行塞进一个状态

每对象输出 quality、phase、risk_flags、attention_bucket。质量不足可以与“已确认今日走弱”并存；未知历史不能遮蔽今天已经发生的风险。
- quality：READY/PARTIAL/UNAVAILABLE，并给缺失字段。
- phase：启动观察、趋势延续、回撤观察、恢复观察、走弱、暂无形态。
- risk_flags：偏离过大、当日冲高回落、量价背离、板块收缩、数据过时等。
- attention_bucket：FOCUS/WATCH/RISK/NONE。

初版不同时推出十几种生命周期名称。首次、再加速需要序列状态，后续升级为子标签。不得从日线宣称“派发”“主力出货”；改成可观测的“高位放量转弱”。“绝对高位”没有可直接验证的统计定义，页面显示窗口、距离和偏离。

### 3.2 新高不自动危险，低位不自动值得看

取消RET20≥25%且靠近新高这一组合的普适一票否决。新高、累计涨幅、价格高低单独均不能证明延伸过度。使用均线偏离与自身波动共同衡量，并把阈值明确标为预览参数。保留稳健趋势和突破研究，避免变成单一低位反弹筛选器。

### 3.3 近期弱化独立于长期主线

今日转弱立即从“当前增强”移走，可以显示“长期仍强、今日转弱”。确认退潮需要连续观测，不以一天弱势断言长期结束。广泛下跌日允许首页只有风险和少量对象，不为凑满卡片强行放宽资格。

### 3.4 当前本地结果不是历史全貌

原始日线可能足够计算历史技术值，但分析快照仅5日；历史成员及事件可能不可追溯。一次性从现有日线补需要的滚动输入可以做；不得为补状态强制每天重建全年全市场成员明细。当前成员重建历史必须注明RECONSTRUCTED，不当作当时已知归属。

## 4. 时间、价格、身份合同

### 4.1 两种页面模式

CLOSE：选择发布及收盘日期D；本地值绑定该发布/切片。在线历史事件绑定D及事件批次。仅同日同语义字段可以数值合并。

LIVE：在线D盘中报价/事件 + 最近本地收盘D-1研究背景。两者可以在同一行展示；current_quote和local_context分别带日期。MA和RPS标“上个收盘”；不与实时价直接相除，不重写为今日形态。若另算盘中临时指标，先把价格转为一致复权基准，另列provisional字段。

在线未验证报价时，价格/成交额显示本地截止日，不写“最新”。上午累计成交额不能与全天20日均额据此判缩量；没有同分钟历史曲线时，只展示金额，不计算盘中量能确认分。

### 4.2 请求上下文

context包含mode、publication_id、snapshot_id、local_trade_date、online_trade_date、observed_at、event_bundle_id、algorithm_version、mapping_version。切换发布/日期清空过期选择和请求；后端校验日期一致性。LIVE可无本地发布进入事件页面，背景字段明确缺失。历史页面绝不默默补今天的热榜。

### 4.3 基础指标

设C为同一复权锚收盘，A为原始元成交额，所有窗口按交易日历，缺行不跳过。
- retN=C[t]/C[t-N]-1，需要N+1个有效收盘。
- maN=mean(C[t-N+1:t])；bias20=C/ma20-1。
- dist_prior_high20=C/max(C[t-20:t-1])-1，与现有新高字段一致。
- pos_close60=(C-min(C[t-59:t]))/(max-min)；分母零为NULL，不与旧POS字段混用。
- sigma20=std(log(C[i]/C[i-1]), ddof=0)，20个收益；零波动为NULL。
- extension_z20=log(C/ma20)/(sigma20*sqrt(20))。这是波动归一的描述量，不是概率。
- amount_vs_prior20=A[t]/mean(A[t-20:t-1])，不使用旧含当日amount_ratio20替代。
- gain_concentration3=sum(max(log_return,0),最近3日)/sum(max(log_return,0),最近20日)，分母零NULL，避免净收益趋零使集中度爆炸。
- 连续天数遇缺失不视为连续，输出censored；不把NULL转0。
- RPS沿用strength.py版本及排名总体；不能只在20只重点内重算RPS。

板块无官方指数OHLC时，显示“成员涨幅中位”“上涨占比”；不拿每日成员收益中位数冒充官方指数价格，也不在其上声称板块POS60。板块金额继续使用已建sector_amount.py共同成员口径；若质量不足显示不可用。

## 5. 本地板块研究规则（可执行预览合同）

规则版本建议SECTOR_ATTENTION_PREVIEW_1；下列数字为工程初始值，不是已经验证的市场规律。执行助手用固定样例和真实样本内部审计后决定保留或版本化修改。

输入必需：同日成员ret1中位m、有效上涨宽度b、有效/目标成员覆盖cov；有历史时再加共同成员宽度变化db3、rps5/rps20、昨日/前日状态。可选：正式金额A、留存、在线事件。

1. 质量：cov<0.70则不得FOCUS；基础报价仍显示。样本不足5只的板块独立小样本标签。
2. 今日走弱W：m<0且b<0.35；或db3<=-0.20且m<0。只要证据充足即可触发，不要求金额下降。
3. 连续走弱：W连续2个有效交易日，进入WEAKENING；历史不足只称“今日走弱”。
4. 当前增强S：m>0且b>=0.55；确认增强为S连续2日。
5. 启动观察：S且最近5日首次S（前5日完整）；历史不足称“当前增强，首次未知”。
6. 扩张支持：db3>=0.10；量能支持：共同成员口径的当日成交额/前20日平均成交额>=1.20（比值，不是元金额A）；分子分母成员集一致、20日前窗完整，质量不满足则UNKNOWN，不阻止展示基础阶段。db3使用t与t-3共同有效成员的上涨占比之差，不能用成员变动制造扩散；rps5改善为同合同排名总体的RPS5[t]-RPS5[t-1]。
7. 长期趋势标签：rps20>=0.80，仅为背景；不能抵消W。
8. 回撤观察：已有趋势背景、当日m<=0、b>=0.35且未连续走弱；无完整序列不称“首次健康回撤”。
9. 恢复观察：之前确认回撤且今日S；无历史回撤不称再加速。

展示优先：质量提示单独输出；已知W进入风险/转弱区。FOCUS要求基础可用、S或已有序列确认的恢复、没有已知严重风险；回撤为WATCH，待股票级支撑确认才可进入重点。不是所有下跌板块都无研究价值，但不能写成“今天强”。

板块组内排序用可审查字典序：(确认级别降序、db3有效且降序、rps5改善降序、正式金额确认、sector_id)。不使用V1未定义的六分量加权分。首页展示上限6个，完整精选上限20；不足不补弱对象。行业父子不强制消失，首页可折叠同一父行业，展开显示被折叠的子行业。

## 6. 个股研究资格、序列与短名单

### 6.1 候选召回

集合=五类结构命中 ∪ 技术触发 ∪ 正常板块阶段成员中的强度改善者。在线事件新进入者在LIVE的临时区加入；热榜只用于当前浏览筛选，不输入持久化短名单，防止间接保存热榜来源行。不能只从旧candidate_daily选，否则召回不了旧算法漏掉的早期对象。

基础门：A股、当天实际有效行情、非已确认退市；停牌和无有效报价只在观察库。流动性预览门为前20日金额中位>=2000万元，金额缺失为未知；这是使用偏好初值，可调整，不宣称小金额证券无价值。

### 6.2 位置风险预览

EXTENDED_PREVIEW=(bias20>=0.15 且 extension_z20>=1.5)。严重偏离成立则FOCUS退出、RISK保留。POS/new_high/RET20作为解释而非独立否决。未满足完整输入不得声称位置安全；仅缺长历史分位不阻塞基础版本。

冲高回落、跳空等功能只有同基准OHLC齐全才启用；初版不强行补ATR、不复制别处未经定义的“脉冲”字段。统计分位250日等长窗作为后续增强，不作启动前置条件。

### 6.3 可解释触发

- 突破观察：C[t]>max(C[t-20:t-1])、C>=MA20、amount_vs_prior20>=1.20、无严重偏离。没有RET20必须大于3%的门，允许前期下跌后形成新结构。
- 趋势跟踪：C>=MA20、MA20[t]>MA20[t-5]、RPS20>=0.70、无严重偏离；缺少短期触发进入WATCH。
- 回撤观察：有效趋势episode中自峰值回撤>=2%、C>=0.98*MA20且未确认破坏；暂不称健康。
- 恢复触发：前一日为回撤episode，今日C>前3日最高收盘、C>=MA5、金额比>=1.20，且未严重偏离。
- 结构破坏：C<0.98*MA20连续2有效日；一日仅警示。复权锚不一致拒绝计算。

板块对齐是支持字段，不要求所有股票一定有源题材；没有映射不等于无价值。若唯一有效共振板块确认走弱，FOCUS降WATCH；有其他真实有效关联则保留解释，不用任一弱板块一票否决。

### 6.4 首次回撤必须有记忆

episode在第6.3节趋势跟踪的价格/均线/RPS条件由false→true且连续2日确认时开始，位置风险单独记录、不作为趋势起点开关。start_date记录第一日，confirmed_at记录第二日，不能回填首日为当时已确认。记录episode_id、start_date、peak_date、peak_close、pullback_count、pullback_start、last_state、history_complete。
- 创新峰更新peak；
- 从峰值首次达到2%回撤时pullback_count加1，持续回撤不重复加；
- 恢复触发结束本次回撤，并将本次恢复收盘设为下一段局部峰值基准；后续新高更新此局部峰值，重新回撤2%才加1，不能恢复后仍距旧总峰值2%就翌日重复计数。趋势总峰值另存用于展示；
- 确认结构破坏结束episode；
- 输入从半途开始时标LEFT_CENSORED，不称“首次”；
- 模型版本变更重算所需序列，不把模型切换当市场新启动。

开发先实现基础阶段，再在完成序列内部审计后展示“首次回撤/再启动”标签。板块序列独立，不能套用虚构的板块价格峰值。

### 6.5 短名单不是凑数

默认FOCUS最多20、WATCH最多30、RISK最多20；均为容量偏好，不是算法配额。可为0。
FOCUS要求有效触发、基础/位置字段完整、无已知严重风险。按(触发今天新发生优先、触发已确认优先、有效板块支持、金额确认、RPS5变化、证券ID)排序；阶段不设硬5/5/5配额。
每个确认主关联板块默认最多3只，未映射对象每只独立，不全部挤进“未知板块”。先全局去重再限额；被限额者可WATCH，绝不放宽硬门补位。
连续日输出新增/保留/移出，移出给触发失效、位置偏离、板块转弱、容量候补等原因。不要把榜单小幅抖动包装为新机会。

五类结构原接口和证据保留，原CORE仅称“结构核心”；新FOCUS称“今日重点”，二者不做枚举替换。近期强势等标签仍可查询，不能占“正常所属板块”。

## 7. 在线完整功能与聚合约定

| 模块 | 来源协议候选（以实际无鉴权复核为准） | 客户端实现与页面 |
|---|---|---|
| 最强题材 | flash-api.xuangubao.cn/api/surge_stock/plates?date=北京时间零点Unix秒；stocks?date=YYYYMMDD&normal=true&uplimit=true | fields按名称映射数组，题材ID多对多挂接；保留原事件榜和本地研究精选两个视图，不把原“最强”全改成早期 |
| 涨停分布 | 同上题材成员，同花顺事件状态辅助 | 题材卡片→高度分组→成员；全局唯一股票数与题材归属次数分开 |
| 涨停简图 | data.10jqka.com.cn/dataapi/limit_up/limit_up_pool | date/page/limit/field/filter/order参数冻结；板高降序、末封时间升序、缺时间末尾；封单和成交额分列 |
| 情绪速览 | 同花顺涨停/跌停池聚合头；选股通/api/pool/detail的7个pool_name | 每池独立状态；今日封板num、炸板open_num；率=封板/(封板+炸板)，分母0为NULL |
| 人气热榜 | dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock，type=hour/day，list_type=normal/skyrocket，stock_type=a | 四榜按需请求，保留order/rate/hot_rank_chg/tag；同花顺和东方财富分别排名 |
| 热门板块/话题 | 同域plate?type=concept/industry；topic?page=1&page_size=30 | 板块DTO和证券DTO分开，话题内容转纯文本/安全链接 |
| 板块精选 | 在线事件及本地有效阶段 | 来源事件榜保留；研究精选使用第5节规则；热榜只临时叠加，不落入持久化选择结果 |

关键边界：
1. M天N板不是连续N板；保存m_days、n_boards、consecutive_limit_days三个字段。只有连续日事件或明确连续字段才能称“连板”。9天5板不能放进“五连板”。
2. 选股通up_limit=false可能是大阳线，也可能炸板，不能直接推断BREAK；炸板来自独立池或明确状态。
3. 未出现在源精选池不证明板块没有事件；源覆盖不全时“不在榜”不能当退潮信号。
4. 同花顺HS/GEM2STAR及ST过滤必须实测，不能声称覆盖全部沪深北。统计卡明确“来源口径”；北交所缺失不能补0。跨源计数不能简单相加。
5. 页数达到上限仍有数据时标TRUNCATED；只抓前200不能说完整。空列表在状态成功、日期匹配、分页完整时可为真实空，其余为未知。
6. 涨停原因显示“来源题材说明”，保留来源。涨价与同题材共现不证明因果。
7. 源股价涨幅百分数转换一次：THS change_rate/100，XGT px_change_rate已是比例；元金额不混亿元。缺成交额时不能用换手×市值当真实成交额。
8. 每源8秒、总聚合12秒预览预算，最大并发4，零自动重试风暴；超时子源独立返回，后台任务也有超时。浏览器取消不等于服务器网络被取消。
9. 热榜本次不跨HTTP请求缓存结果、不落日志正文/DB/文件；请求内可以共享。翻页重新请求会变动，明确“实时榜单”；用has_more与upstream_total，未知总量为NULL，不用当前页长度冒充总数。
10. 盘中事件流只代表最近一次采样的状态，不能承诺逐笔事件时间线。

## 8. 本地—在线映射

online_security_map复用既有表。证券按来源明确市场+代码匹配，并校验证券类型；上市状态未知不当退市。
新增source_sector_mappings允许同一外部题材映射多个本地板块：mapping_version/source_id/source_sector_id/local_sector_id为主键，附relation_type(EXACT/RELATED)、evidence、status。名称相同仅是候选，不自动合并成员。
只有EXACT且成员范围验证可比才计算融合宽度；RELATED只能显示关联，不能把本地全板块成员与源精选成员混做一个分母。映射未知显示源题材，不要求用户每天维护映射才能用页面。

## 9. 数据库与计算改造

### 9.1 复用，不重建基础平台

复用analysis_slices、analysis_snapshot_entries、现有source、online_batches、online_fetch_runs、jobs。新增迁移编号在实施时读取最新清单再分配，已执行SQL不原地编辑。切片复用必须包含domain/date/contract/price_basis/universe/membership及依赖内容；同一日期不同算法的行不是自动重复。

| 新表 | 键/字段 | 索引及读取 |
|---|---|---|
| research_runs | run_id PK；mode、trade_date、local_snapshot_id、event_bundle_id可空、algorithm_version、mapping_version、status、created_at | 日期+status；只完成结果可展示 |
| online_event_bundles | bundle_id PK；trade_date、source_batch_bindings JSON、observed_at、coverage JSON、status | 仅保存允许落库的事件批次集合；不含热榜，分页引用固定集合 |
| research_stock_states | run_id+security_id PK；phase、quality、risk_flags JSON、trigger、extension_z20、bias20、reason_codes JSON、evidence_ref | run_id+phase；基础本地结果每股紧凑一行，不复制OHLC历史 |
| research_sector_states | run_id+sector_id PK；phase、today_state、quality、breadth、reason_codes、source_refs | run_id+phase |
| research_episode_state | run_id+security_id PK；episode_id/start/peak/date/count/history_complete、last_state | run_id+security_id；只记录模型状态 |
| research_shortlist | run_id+list_type+entity_type+entity_id PK；rank、primary_sector_id、selection_reason、previous_list_state | UNIQUE(run_id,list_type,entity_type,rank) |
| online_pool_entries | batch_id+pool_type+source_code PK；security_id、event_state、first/last_time、price/amount/turnover可空、quality | batch_id+pool_type；source/date通过batch/fetch追溯 |
| online_topic_entries | batch_id+source_topic_id PK；name、description、source_order | batch_id |
| online_topic_members | batch_id+source_topic_id+source_code PK；security_id、up_limit、m_days、n_boards、reason | batch_id+source_topic_id |
| source_sector_mappings | 见第8节 | source_id/source_sector_id/mapping_version |

batch引用source、contract和观察时间，不用trade_date+security_id单独主键覆盖多来源和盘中修订。事件收盘批次允许修订，旧run引用旧batch。收盘bundle记录各来源batch_id及独立成功/缺失状态，不要求不同来源完全同秒。盘中LIVE事件bundle仅在服务端有界内存保存：预览TTL两分钟、最多16个且总计32MiB，过期或容量淘汰返回HTTP 409 CONTEXT_EXPIRED，引导整组刷新，禁止静默换批；此缓存仅限事件数据，不适用于热榜。热榜禁止写上述表，包括以其候选集生成的持久化精选结果。

以上字段S为VARCHAR、D为DATE、TS为TIMESTAMP、量额DOUBLE、计数INTEGER、布尔BOOLEAN；raw金额元。所有百分比存比例。关键键非空；未知数值NULL而非0。新增表写入同事务完成run，不引入灾备服务。

### 9.2 计算边界

全市场RPS、市场宽度和完整板块宽度需要参考总体，不能只算20只。可减少的是重复全历史重建与多份物化。
每日：读取新增日线+必要窗口→共享MA/收益/量额→板块聚合→阶段→短名单。
首次：仅补算法所需滚动窗口与少量序列状态，不同时生成全年股票×板块×队列证据。短名单详情按需查询。
发现候选不能只依赖旧候选池；低成本全市场召回仍保留。长历史高分位/ATR增强以后再做，不阻塞首个可用版本。
每次构建统计输入证券/日期、读取行数、新写行数、复用行数、耗时；重复输入第二次运行不增加结果。旧数据清理单独处理，当前不设硬盘故障演练。

## 10. 接口与UI落点

保留现有/v2前端壳，新增api/v3命名代表研究语义版本，不意味着重写框架。API新增：
- GET /api/v3/research/context：mode、可选publication；返回第4节上下文及能力。
- GET /api/v3/home：run_id、mode；本地卡和在线卡可分请求，不等待最慢源。
- GET /api/v3/research/shortlist：run_id、list_type、page、page_size<=50。
- GET /api/v3/research/sectors：run_id、phase、page。
- GET /api/v3/research/stocks/{id}、/sectors/{id}：首屏摘要。
- GET /api/v3/research/sectors/{id}/members：context、role、page；按全板块先排名再筛选。
- GET /api/v3/research/stocks/{id}/evidence?section=：只加载所选证据。
- GET /api/v3/events/overview、/ladder、/topics、/topics/{id}/members、/pools：绑定同一event_bundle_id；新刷新新bundle，不能跨页混批。
- GET /api/v3/hot-rankings：source、list_type、page；不接历史batch参数。
- GET /api/v3/search/suggest?q=：股票/板块自动完成。
- 交叉筛选复用现有POST /api/sector-intersection/query，加名称选择控件。

通用分页返回total或NULL、has_more、page、page_size、items；错误BAD_QUERY/CONTEXT_EXPIRED/SOURCE_UNAVAILABLE分别给可恢复交互。列表行返回selection_reason、warning、字段时间；不是只返回一堆合同号。

页面布局：
- 首页：一行市场概况；最多6个当前板块；默认10只重点，可展开到20；“今日转弱/偏离提醒”不与机会混排。
- 情绪与涨停：最强题材、分布、简图、速览四个子页，共享事件批次。最强题材忠实保留事件榜，不把全部高板股隐藏。
- 板块研究：精选默认；周期矩阵/主线/属性/交集可达，不把已有功能塞进开发审计入口。
- 个股研究：重点/候补/风险；五类结构、新高RPS保留正常入口。
- 热度观察：平台→榜单→成员，不一次请求全部来源和榜单。

点击股票或板块打开一个共用详情容器；宽屏右侧抽屉，窄屏居中弹窗。X、遮罩、Esc均关闭；焦点回原行；浏览器后退恢复筛选、滚动、上下文；点击抽屉中的关联对象替换内容并提供返回，不叠三层弹窗。
表内保留名称/代码、价格、当日涨幅、成交额、阶段、关联板块、入选原因。证据≤3条主要理由+风险，深入指标折叠。格式共用format.js；金额万/亿/万亿，自适应保留有效精度。所有源文本用textContent。
首屏目标本地P95<=1.5s、响应<=200KiB；在线区独立占位最长12s；每页<=50、题材摘要每项<=5成员，摘要字节预算不能通过删掉必要来源时间达成。

必须先修E09：网络请求不持有数据库连接或全局_db_lock。先短时读本地标识→释放→请求在线→短时批量补背景。核验慢源期间/api/publications等仍可返回。E10同时修分页总量、先分页后补行情、来源并发与部分成功。

## 11. 分阶段任务、改动点与内部审计

阶段状态PLAN→IMPLEMENTING→INTERNAL_REVIEW→PASS/PARTIAL/BLOCKED。每阶段记录输入版本、完成项、缺陷、人工/自动证据、下一步；执行助手自行复核，无外部签字。一次验收包括输出和界面，不以测试数量代替产品结果。

| 阶段/任务 | 改什么与产物 | 内部验收/依赖 |
|---|---|---|
| A0-1 | 读取最新源码/DB/合同，登记E01–15及问题清单 | 重现历史强今日弱、1187候选、慢源锁；不批量清库 |
| A0-2 | 在文档冻结context、字段来源、参数预览状态 | CLOSE/LIVE各一份例子，Sol文件保留 |
| A1-1 | app.py网络与DB锁分离；hot_rank分页修复 | 注入慢源，本地接口无网络级等待；一源失败另一源仍显示 |
| A1-2 | dashboard改准确标题、显示当日弱化；新增预览短名单入口 | 原列表仍可查；界面可看到收敛前后差异，不假称新算法完成 |
| A1-3 | router/index/app.js接共用详情和名称搜索 | 一次点击到成员，返回保留筛选；先验交互后扩算法 |
| B1-1 | workbench_online新增事件adapter，扩THS四榜/板块榜；复用base | 无登录公开请求样例；字段、单位、空列表、分页、时区测试 |
| B1-2 | 新建事件标准化/聚合服务，批次与来源范围 | 9天5板非5连板；ST/BJ覆盖清楚；一股多题材去重 |
| B1-3 | 事件简图/分布/速览/最强题材UI可见切片 | 先不依赖本地全阶段也能用；网络失败不白屏 |
| C1-1 | 新research_features模块复用technical/strength/highs；补bias/sigma/episode输入 | 同复权锚、零波动/缺行/分母0、未复用旧POS误名 |
| C1-2 | 新sector_attention实现第5节，读sector_cycle与正式amount | 放量下跌能识别；长期强和今日弱可并存；未知事件不否决 |
| C1-3 | 新stock_attention实现第6节基础规则，旧五类合同保留 | 新高但低偏离不被误剔；弱反弹不因低位优先 |
| C2-1 | episode序列与短名单分配、变化理由 | 半途历史不称首次；连续回撤只计1次；不足20允许空位 |
| C2-2 | 新表迁移和run登记，复用已有jobs调度 | 输入重复运行不增写；持久化不含热榜贡献；只完成run可见 |
| D1-1 | 统一新关联查询，协调association两路径 | 主/备选及拒绝原因一致；RELATED不混分母 |
| D1-2 | 本地+在线板块精选，显示模式与字段时间 | LIVE昨日背景可用；历史不混今日；无映射事件仍能查 |
| D1-3 | 首页、股票、板块三页挂正式短名单 | 重点<=20、候补<=30；每行一句可解释入选理由 |
| E1-1 | 代表/正反样本复核，轻量时段回放、参数敏感性 | 不强求每阶段有固定命中数；标明历史成员重建限制 |
| E1-2 | 全路径UI/慢网/刷新/无本地发布检查 | 热榜无持久化；X/遮罩/后退；现有深度功能仍可达 |
| E1-3 | 内部问题关闭、切主入口、版本说明 | 未通过模块隐藏/预览，不阻止已通过模块可用；不搞整套灾备流程 |

依赖：A0→A1；A0→B1；A0→C1→C2；B1+C2→D1→E1。B1上线必须先通过A1-1的锁分离；事件表及bundle迁移归B1-2，研究表迁移归C2-2，不能等C2才存B1事件。A1的可见反馈应尽早完成；在线功能不必等待全部本地阶段。D1融合不能先于真实源与本地状态基础。

## 12. 内部验收必须覆盖的反例

| 用例 | 预期 |
|---|---|
| RPS20高，今日m<0且b=0.2，金额放大 | 今日转弱；不因放量逃过检测 |
| 收盘新高，bias20仅3%，趋势稳健 | 不因新高自动判过热 |
| 暴跌后低位反弹、MA20仍降 | 不因“低位”进入重点 |
| 同股票不同真实有效板块，一个弱一个强 | 分别解释，不能任一弱就全部否决 |
| 连续5日回撤 | 一个回撤episode；不能计5次 |
| 历史起点已在上升途中 | FIRST未知而非假首次 |
| 全天量额背景+10点盘中成交 | 不计算全天相对量能确认 |
| 源当前空且覆盖不明 | 未知；不是0事件或退潮 |
| 上游只返回前200但还有下一页 | 标不完整，不声称市场总数 |
| 合格只有7只 | 重点7，不补满20 |
| 热榜换页且价格请求很慢 | 本地服务可用，total语义正确，不持久化 |
| 旧候选未含、技术新触发命中 | 可以召回 |
| 档位/权重参数±20% | 输出数量、换手率、误删样例变化有报告，不假装稳定 |
| 同输入同版本重算 | 同结果，新增持久化0 |
| 修改算法版本 | 新run，不将版本差异说成个股新启动 |

历史内部复核应同时包含上涨、下跌、横盘、除权、停牌、新股、突破和长趋势。至少30个正反例起步；可用历史不足时减少“首次/连续”等展示能力，不能造数据。价格前瞻结果若用于后续研究效果评估，须固定规则后另算，严格隔离特征与未来窗口，历史成员非PIT时明确偏差。本版不以收益保证验收。

## 13. 专项问题登记与最终状态

- AUD-LOCAL-01：强度与重点语义错位；范围首页/候选/代表/关联；证据E01–08；验收第12节反例及真实清单。
- AUD-PERF-01：GET全局锁+在线请求+分页；证据E09–10；验收慢网本地接口并行和正确总量。
- AUD-DATA-01：事件身份/覆盖/时间；证据E12–15；验收同日双源、修订、LIVE背景与热榜零持久化。
- AUD-STORAGE-01：多切片与重算成本；证据E13；先记录域/算法/依赖/有效引用，证明重复再定清理方案。独立于当前页面可用性。
以上全部由内部助手跟踪，无外部审计角色。磁盘备份、异地灾备和多级恢复不进入本方案工作包。

审计结论：Sol V1作为方向稿保留，直接实施条件不足。本V2给出可执行预览规则、数据和UI落点；工程可以按任务推进，参数效果仍须内部样例验证。最重要的交付顺序是先出现可用页面与正确当日解释，再逐步增加序列判断，避免再一次只交付大量表、合同和含糊标签。

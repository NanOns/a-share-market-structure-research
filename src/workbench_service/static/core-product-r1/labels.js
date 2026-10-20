export const entries=[['home','今日总览'],['sectors','板块研究'],['stocks','个股研究'],['focus','关注跟踪'],['forward','Forward研究'],['market','市场与事件'],['diagnostics','数据与诊断']];
// Preserve dated owner states rather than hiding distinct rotation transitions.
export const labels={value:'数值',close:'收盘价',amount:'成交额（元）',volume:'成交量（股）',open:'开盘价',high:'最高价',low:'最低价',trade_date:'交易日期',source_security_key:'证券代码',security_name:'证券名称',list_date:'上市日期',scenario:'研究情景',scenario_status:'情景状态',state:'研究状态',final_eligibility:'资格判断',qualification_state:'资格四态',state_freshness:'状态时效',health:'健康度',maturity:'成熟度',primary_industry:'主行业',supporting_concepts:'关联概念',relative_sector_state:'相对板块状态',sector_context_state:'板块背景',sector_context_quality:'背景质量',structure_health:'结构健康',support_state:'支撑状态',acceptance_state:'接受状态',basic_breakout_state:'基础突破',basic_pullback_state:'基础回踩',basic_recovery_state:'基础恢复',active_anchor_id:'当前锚点',retest_count:'回测次数',sector_name:'板块名称',sector_id:'板块身份',member_count:'成员数',algorithm_state:'算法状态',output_state:'轮动状态',effective_event:'有效事件',primary_scenario:'主要情景',counterevidence:'反证',signal_type:'信号类型',eligibility_state:'资格状态',priority_bucket:'优先级',research_rank:'研究复核序号',priority_score:'优先级分值',priority_reasons:'排序原因',component:'数据组件',row_count:'记录数',quality:'质量',enrollment_id:'样本身份',horizon:'观察会话数',outcome_status:'结算状态',due_date:'到期日期',T0:'入组日期'};
export const states={NEW_CONFIRMED:'新增确认',LAUNCH_CONFIRM:'启动确认',RECOVERY_TURN:'恢复转向',CONFIRMED:'已确认',PREWATCH:'预观察',TRUE:'符合',FALSE:'不符合',FRESH:'当前有效',STALE:'状态过期',KNOWN:'已知',OBSERVED:'已观测',MATURE:'成熟',DEVELOPING:'发展中',EARLY:'早期',DAMAGED:'受损',WEAKENING:'走弱',WATCH:'观察',UNKNOWN:'无法判定',RANKABLE:'可排序',NOT_RANKABLE:'不可排序',rankable:'可排序',not_rankable:'不可排序','core structure intact':'核心结构未破','rps20 delta3 positive':'二十会话相对强度改善','ret5 positive':'五会话收益为正','not extended':'未显著延伸','distance from prior low20 observed':'与前二十会话低点距离可算','rotation in':'轮动进入','rotation accepted':'轮动接受','rotation expanding':'轮动扩散','rotation pulse':'轮动脉冲','maturity developing':'成熟度：发展中','health none':'健康度：已评估无变化','health watch':'健康度：观察','rs5 positive':'五会话相对强度为正','rs20 positive':'二十会话相对强度为正',CORE_STRUCTURE_INTACT:'核心结构未破',RPS20_DELTA3_POSITIVE:'二十会话相对强度改善',RET5_POSITIVE:'五会话收益为正',NOT_EXTENDED:'未显著延伸',DISTANCE_FROM_PRIOR_LOW20_OBSERVED:'与前二十会话低点距离可算',ROTATION_ROTATION_IN:'轮动进入',ROTATION_ROTATION_ACCEPTED:'轮动接受',ROTATION_ROTATION_EXPANDING:'轮动扩散',ROTATION_ROTATION_PULSE:'轮动脉冲',MATURITY_DEVELOPING:'成熟度：发展中',HEALTH_NONE:'健康度：已评估无变化',HEALTH_WATCH:'健康度：观察',RS5_POSITIVE:'五会话相对强度为正',RS20_POSITIVE:'二十会话相对强度为正',DATA_UNAVAILABLE:'观察来源不足',DEGRADED:'质量降级',QUALITY_DEGRADED:'质量降级',SOURCE_INCOMPLETE:'来源未发布',SOURCE_INSUFFICIENT:'必要来源不足',NOT_GRANTED:'尚未授权',NOT_AUTHORIZED:'尚未授权',NOT_ELIGIBLE:'不满足资格条件',DATA_INSUFFICIENT:'必需数据不足',NOT_DUE:'尚未到期',NOT_OBSERVED:'当日未观测',UNKNOWN_IDENTITY_REASON:'证券身份待核验',EXISTING_VERIFIED_IDENTITY:'已有证券（代码沿用）',CONFIRMED_CURRENT_IDENTITY:'正式身份来源已确认',CURRENT_IDENTITY_PRESENT:'当前身份记录存在',CURRENT_IDENTITY_UNKNOWN:'当前身份记录待确认',CONFIRMED_IPO:'当日确认上市',NEW_CODE_UNLINKED:'新代码关系未确认',ENGINEERING_NOT_READY:'待工程接入',PENDING:'待到期',RIGHT_CENSORED:'右删失',READY:'可读取',EMPTY_VALID:'当前无符合项',FULL_PASS:'通过',PASS:'通过',DEGRADED_PASS:'降级通过',NONE:'NONE（判定完整性待核）',NOT_APPLICABLE:'不适用',OPERATIONAL_PRODUCTION_ACTIVE:'正式研究运营',VALIDATION_ONGOING:'持续验证中',PARTIAL:'部分接入',NOT_GRANTED_STATUS:'尚未准入',DATA_PENDING:'等待新数据',WAIT_NEXT_ACCEPTED_INPUT:'等待下一已接收交易日',NOT_IMPLEMENTED:'尚未实现'};
export const missingReasons={
 FORMAL_RADAR_PRIORITY_NOT_PUBLISHED:'正式 Radar 优先级尚未生产；数字仅为已接受变化事件数',
 FIRST_OBSERVED_ON_CURRENT_TRADE_DATE:'身份来源记录为当日首次观测',
 LISTED_ON_CURRENT_TRADE_DATE:'身份来源记录为当日上市',
 DATED_IDENTITY_PREDATES_CURRENT_TRADE_DATE:'身份来源记录的上市日期早于当前交易日',
 DATED_CODE_STATUS_NOT_REPORTED_BY_IDENTITY_OWNER:'身份来源未提供可验证的代码状态',
 NO_AUTHORIZED_COHORT_OWNER:'正式前瞻样本尚未准入：缺少经批准的验证队列负责人',
 DATED_SECTOR_D2_MATURITY_OWNER_NOT_PRESENT:'尚无当日正式板块成熟度记录',
 DATED_SECTOR_D2_HEALTH_OWNER_NOT_PRESENT:'尚无当日正式板块健康度记录',
 DATED_OPERATIONAL_FORWARD_OWNER:'正式 Forward 首次捕获来源尚未接入',
 DATED_OPERATIONAL_RISK_CHANGE_OWNER_NOT_PRESENT:'正式风险变化来源尚未接入',
 OPERATIONAL_OWNER_UNKNOWN:'正式运营来源尚未发布，无法判定',
 OWNER_REPORTED_UNKNOWN_VALIDITY:'来源记录的有效性为无法判定',
 OWNER_REPORTED_UNKNOWN_MEMBERSHIP:'来源记录的关注层级为无法判定',
 NO_RECORDED_EPISODE_END_DATE:'来源未记录 Episode 结束日期',
 FULL_ROTATION_NOT_INDEPENDENTLY_ACCEPTED:'轮动状态仍在验证，不能视为完整轮动判定',
 NO_DATED_FOCUS_OBSERVATION_FIELD:'该对象没有已发布的定日期观察字段',
 ACCEPTED_IDENTITY_SYMBOL_NOT_VERIFIED:'当前代码与接受身份记录未能完全对应',
 NO_T0_MARKET_QUOTE:'当日未观测到有效行情；不能据此判断退市',
 IPO_TWO_SOURCE_CONFIRMATION_NOT_PROVEN:'上市日身份缺少两项独立来源确认',
 CURRENT_SYMBOL_BOUND_TO_DIFFERENT_SECURITY_ID:'当前代码记录对应其他证券身份，关系尚未确认',
 NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER:'缺少已授权的 Cohort 期限结算 Owner',
 MODEL_OR_PERMISSION_NOT_READY:'模型结果或显示权限尚未准入',
 NOT_OBSERVABLE_FROM_DAILY:'日线数据不能观察盘中封板过程',
 PREFIX_NOT_BOUND:'历史连板前缀未绑定，无法确认精确板数',
 NO_FORMAL_IDENTITY:'正式证券身份记录缺失',
 NO_DATED_SOURCE:'没有当前日期已发布的来源',
 NO_TARGET_ACCEPTED_CORE_FACTS:'当前日期没有已接受的核心事实',
 REQUIRED_INPUT_UNKNOWN_OR_ZERO_HIGH:'所需输入无法判定，或前期高点为零',
 NO_UNIQUE_TDX_LEAF_INDUSTRY:'通达信未提供唯一末级行业',
 REQUIRED_INPUT_UNKNOWN:'所需输入缺失或无法判定',
 INSUFFICIENT_HISTORY:'有效历史长度不足',
 PRIOR20_AMOUNT_UNAVAILABLE:'前二十会话成交额缺失或不可用',
 REQUIRED_INPUT_UNKNOWN_OR_ZERO_ATR:'所需输入无法判定，或 ATR 为零',
 CLOSED_PERIOD_OR_INPUT_UNAVAILABLE:'已收盘周期数据或必需输入不可用',
 REQUIRED_TDX_LOO_CONTEXT_UNKNOWN:'通达信逐证券剔除后的行业背景无法判定',
 MA10_WINDOW_OR_ENDPOINT_UNAVAILABLE:'十会话均线窗口或端点数据不可用',
 INSUFFICIENT_SESSION_HISTORY:'可用交易会话历史不足',
 RETURN_OR_UNIVERSE_UNKNOWN:'收益或证券范围无法判定',
 POS250_WINDOW_OR_DENOMINATOR_UNAVAILABLE:'二百五十会话位置窗口或分母不可用',
 CORRECTED_MARKET_AXES_NOT_YET_BOUND:'尚未绑定修正后的市场四轴',
 ATR_OR_PRICE_INPUT_UNAVAILABLE:'ATR 或价格输入不可用',
 EXACT_DATED_RPS_ENDPOINT_UNKNOWN:'精确日期的 RPS 端点无法判定',
 DATED_MARKET_REFERENCE_UNPROVEN:'日期对应的市场参照尚未核实',
 NO_QUALIFIED_RANK_INPUT:'符合资格的排名输入缺失'
};
Object.assign(labels,{code_status:'证券代码状态',identity_status:'代码身份'});
Object.assign(labels,{listing_status:'上市状态',ipo_confirmation_status:'IPO 确认状态',first_seen_status:'证券首见状态',owner_code_status:'Owner 原始代码状态',identity_link_status:'代码身份链接'});
Object.assign(states,{NEW_CODE_OBSERVED:'当前代码首次观测',LISTED_TODAY:'当日上市',LISTED_BEFORE:'此前已上市',NOT_YET_LISTED:'尚未上市',FIRST_OBSERVED_TODAY:'当日首次观测',OBSERVED_BEFORE:'此前已观测',CONFIRMED_IPO:'IPO 已确认',IPO_NOT_INDEPENDENTLY_CONFIRMED:'IPO 尚未独立确认',NOT_IPO_TODAY:'非当日 IPO',CURRENT_CODE_LINKED:'当前代码已链接',HISTORICAL_CODE_ALIAS_LINKED:'历史代码别名已链接'});
Object.assign(states,{PROXY_RECONSTRUCTED:'代理重建（仅研究）'});
Object.assign(labels,{input_provenance:'输入来源依据',ma10:'十会话均线',ma20:'二十会话均线',ret5:'五会话收益',rps20:'二十会话相对强度',owner:'来源负责人',core_price_damage:'核心价格损伤',delta3:'三会话变化',dq5:'五会话宽度变化',episode_invalidation_contract_id:'Episode 失效合同',followup_complete:'后续确认状态'});
export function translate(value){if(value===null||value===undefined)return '—';if(typeof value==='boolean')return value?'是':'否';if(Array.isArray(value))return value.length?`${value.length} 项`:'无';if(typeof value==='object')return '查看详情';if(typeof value==='number')return Number.isInteger(value)?String(value):value.toFixed(3);if(/^(?:[0-9a-f]{24,}|SEC-[0-9A-F]+)$/.test(String(value)))return '查看来源标识';return states[value]||String(value);}
export const reasons={market:'市场四轴尚缺当前日期的已绑定产物，定点计算由任务 05 完成。',focus:'已提供真实冻结源重建；实际价格路径与到期结果可查，结构谓词缺失会保留不可判定。旧账尚未完成核对。' ,stocks:'Core successor、状态与高级画像均按页面顶部所示目标日绑定；历史 Owner 记录按其自身日期保留。',profile_identity:'部分高级画像对象不在当前日行情池，已隔离登记。'};

Object.assign(labels,{"algorithmic_support_sector": "算法支撑板块", "anchor_view_asof_t": "当日锚点视图", "rotation_structure_enrichment": "轮动结构增强", "structure_events": "结构事件", "base_seed_retention": "基础种子保持", "base_seed_width_adjusted": "调整后种子宽度", "basket_cumulative_return": "篮子累计变化", "breadth_delta1": "宽度单会话变化", "breadth_delta3": "宽度三会话变化", "breadth_ret1": "单会话上涨宽度", "breadth_ret20": "二十会话上涨宽度", "breadth_ret5": "五会话上涨宽度", "breadth_retention": "宽度保持", "dq5": "五会话相对强度变化", "entered_count": "新增成员数", "episode_accepted": "轮动阶段已接受", "episode_terminated": "轮动阶段已结束", "ma20_delta1": "均线宽度单会话变化", "ma20_delta3": "均线宽度三会话变化", "ma20_width": "二十会话均线宽度", "mdd20": "二十会话最大回撤", "membership_ready": "成员关系就绪", "negative_out_consecutive_evaluable_sessions": "连续负向退出可评估会话", "net_entered_count": "净新增成员数", "participation_proxy": "参与度代理", "pos60": "六十会话位置", "prior_maturity_state": "前序成熟状态", "prior_rotation_state": "前序轮动状态", "pulse_active": "脉冲有效", "pulse_age_sessions": "脉冲会话数", "rank_velocity3": "三会话排名速度", "sector_member_count": "板块成员数", "sector_price_retention_core": "核心价格保持", "sector_quote_coverage": "行情覆盖度", "sector_rs1": "单会话相对强度", "sector_rs20": "二十会话相对强度", "sector_rs20_pct": "二十会话相对强度分位", "sector_rs5": "五会话相对强度", "sector_rs5_pct": "五会话相对强度分位", "sector_rs60": "六十会话相对强度", "sector_rs60_pct": "六十会话相对强度分位", "seed_retention": "种子保持", "seed_width": "种子宽度", "strong_member": "强势成员", "strong_member_retention": "强势成员保持", "strong_member_retention_1": "强势成员单会话保持", "strong_prev": "前序强势成员", "top1_concentration": "首位集中度", "top3_concentration": "前三集中度", "yesterday_dq5": "前序五会话强度变化"});

Object.assign(labels,{"raw_qualification": "原始资格判断", "detector_statuses": "检测器状态", "matched_predicates": "已满足条件", "unknown_predicates": "缺失条件", "transition_reasons": "状态变更原因", "tracking": "研究状态跟踪", "validity": "状态有效性", "market_age": "市场会话年龄", "expiry_count": "过期计数", "downgrade_count": "降级计数", "improvement_baseline": "改善基线", "boundary_event": "边界事件"});
Object.assign(states,{CLOSED:"已关闭",ACTIVE:"进行中",OPEN:"开放",IMPLEMENTED:"已实现",INVALID:"已失效",VALID:"有效"});

Object.assign(labels,{trend_axis:'趋势轴',breadth_axis:'宽度轴',participation_axis:'参与轴',stress_level:'压力轴',stress_change:'压力方向'});

Object.assign(states,{STRONG:'偏强',WEAK:'偏弱',IMPROVING:'改善',DETERIORATING:'恶化',STABLE:'稳定',THIN:'偏低',NORMAL:'正常',EXPANDING:'扩张',LOW:'低',ELEVATED:'升高',HIGH:'高',DECLINING:'回落',RISING:'上升',RISK_ON:'积极环境',RISK_OFF:'风险环境',NEUTRAL:'中性环境',RECOVERY_ATTEMPT:'尝试恢复',CAPITULATION:'集中释放'});

Object.assign(labels,{sector_type:'板块类型'});Object.assign(states,{INDUSTRY:'行业',THEME:'概念'});

Object.assign(labels,{event:"跟踪变化",membership:"关注层级",end_date:"退出日期",parent_episode_id:"前序Episode",path_state:"路径状态",outcome_status:"结算状态"});
Object.assign(states,{NEW:"新增关注",PERSISTENT:"持续关注",EXITED:"退出关注",REENTERED:"再次关注",UPGRADED:"关注升级",WEAKENED:"转弱",INVALIDATED:"失效",DATA_UNAVAILABLE:"来源暂缺",CURRENT:"确认层",EARLY:"预观察层"});

Object.assign(labels,{
amount:'成交额',amount_state:'成交额状态',anchor:'结构锚点',anchors:'锚点列表',atr_normalized_position:'ATR标准化位置',breadth:'市场宽度',broken_limit:'炸板',compression:'波动压缩',confirmation:'确认状态',contracts:'版本合同',corrected_history:'事后修正历史',current_loo:'当前留一法基准',date_token:'日期版本',emergence:'涌现',entered:'进入',episode_id:'关注周期身份',event:'事件',exhaustion:'衰竭',exited:'退出',factor_timeline:'因子时间线',facts_events:'事实事件',focus_timeline:'关注时间线',followup:'后续观察',four_axes:'市场四轴',frozen_sector:'冻结板块篮子',hypothesis:'研究假设',indices:'市场指数',invalid_if:'失效条件',jobs:'运行任务',ladders:'涨停梯队',legacy:'历史模块',limits:'涨跌停',loo:'留一法基准',ma:'移动均线',ma_structure:'均线结构',market_regime:'市场环境',member_preview:'成员预览',membership:'关注资格',navigation:'页面导航',next_discriminator:'下一判别条件',observation:'日观察',overlap:'成分重叠',parent_episode_id:'前序关注周期',path_state:'路径状态',price:'价格',rank_velocity:'排名变化速度',relative:'相对强度',relative_state:'相对强度状态',retention:'留存率',risk:'风险',risk_changes:'风险变化',rotation_changes:'轮动变化',rps20_matrix:'二十会话强度矩阵',sector_changes:'板块变化',sector_facts:'板块事实',sector_lifecycle:'板块生命周期',sector_market:'板块与市场比较',sector_three:'板块三日前比较',shadow:'独立观察验证',sources:'数据来源',stock_changes:'个股变化',stock_market:'个股与市场比较',stock_previous:'个股前日比较',strict_pit:'严格当时可知回放',structure_events:'结构事件',supporting_evidence:'支持证据',technical_scanner:'技术扫描',tracking:'跟踪状态',turnover:'换手率',turnover_state:'换手状态',unique_member_share:'独有成员占比',validity:'有效性',waiting_for:'等待条件',why_now:'当前变化原因',raw_qualification:'原始资格',matched_predicates:'已满足判定',unknown_predicates:'不可判定条件',transition_reasons:'状态迁移原因',boundary_event:'边界事件',detector_statuses:'检测器状态',market_age:'市场会话年龄',expiry_count:'失效计数',downgrade_count:'降级计数',improvement_baseline:'改善基线',anchor_view_asof_t:'当日锚点视图',core_price_damage:'核心价格损伤',atr20:'二十会话平均真实波幅',atr5:'五会话平均真实波幅',clv:'收盘位置',amount_ratio5:'五会话成交额比',volume_ratio5:'五会话成交量比',sector_member_count:'板块成员数',vol5:'五会话波动',vol20:'二十会话波动',tr:'真实波幅',rel_market_1:'一会话市场相对收益',rel_market_3:'三会话市场相对收益',rel_market_5:'五会话市场相对收益'
});

Object.assign(labels,{atr_ratio:'真实波幅比',bias20_atr:'二十会话均线ATR偏离',core_extension_risk:'核心延伸风险',core_participation_result:'核心参与度结果',dist_high20_atr:'距二十会话高点ATR距离',drawdown20_state:'二十会话回撤状态',drawdown60_state:'六十会话回撤状态',hh_progress:'高点推进',ll_progress:'低点推进',hhv5:'五会话最高值',hhv20:'二十会话最高值',hhv60:'六十会话最高值',llv5:'五会话最低值',llv20:'二十会话最低值',llv60:'六十会话最低值',minimum_liquidity:'最低流动性',near_high20_state:'临近二十会话高点状态',near_high60_state:'临近六十会话高点状态',pos250:'二百五十会话位置',prior60_percentile:'前六十会话百分位',prior_high5:'前五会话最高值',prior_high20:'前二十会话最高值',prior_high60:'前六十会话最高值',prior_low5:'前五会话最低值',prior_low20:'前二十会话最低值',prior_low60:'前六十会话最低值',range_ratio:'区间振幅比',regime_ui:'市场环境显示',rotation_structure_enrichment:'轮动结构补充',rps20_delta3:'二十会话RPS三日变化',rps5_delta1:'五会话RPS单日变化',rps5_delta3:'五会话RPS三日变化',severe_extension:'严重延伸',slope20:'二十会话斜率',slope60:'六十会话斜率',vol_ratio:'波动比',algorithmic_support_sector:'算法支持板块'});

Object.assign(labels,{amount_ratio20:'二十会话成交额比',compression_state:'波动压缩状态',ma5:'五会话均线',ma10:'十会话均线',ma20:'二十会话均线',ma60:'六十会话均线',ma_structure_state:'均线结构状态',monthly_trend_state:'月线趋势状态',pos60:'六十会话位置',position_state:'价格位置状态',relative_market_state:'市场相对强度状态',ret1:'单会话收益',ret3:'三会话收益',ret5:'五会话收益',ret20:'二十会话收益',rps5:'五会话相对强度分位',rps20:'二十会话相对强度分位',trend_state:'趋势状态',volume_ratio20:'二十会话成交量比',volume_state:'成交量状态',weekly_trend_state:'周线趋势状态'});

Object.assign(labels,{path_resolution:'路径判定完整度',best_confirmed_state:'已确认路径事实',price_path:'实际价格路径',target_trade_date:'目标交易日',return_close:'锚点以来收盘变化',mfe:'最大向上偏离',mae:'最大向下偏离',drawdown_current:'当前回撤',mdd_close:'收盘最大回撤'});
Object.assign(states,{PARTIAL:'部分证据已确认',UNAVAILABLE:'尚缺判定证据',WAIT_CONFIRMATION:'等待确认',BREAKOUT_CONFIRMED:'突破已确认',STRUCTURE_DAMAGED:'结构已失效',EXITED_FOLLOW_UP:'退出后跟踪',POST_EXIT_OBSERVATION:'退出后持续观察',NOT_DUE:'尚未到期',TARGET_INPUT_UNSEALED:'目标日输入尚未封存',COMPLETE_ACTUAL_PATH:'完整实际价格路径'});
Object.assign(labels,{kind:'锚点类型',anchor_id:'锚点身份'});
Object.assign(states,{COMPRESSING:'压缩',ENROLLED:'进入关注周期',UPGRADE_IMMEDIATE:'即时升级'});
Object.assign(states,{WEAKENING:'走弱',EXHAUSTED:'衰竭',MEDIUM:'中等',EXTREME:'极端'});
Object.assign(labels,{amount:'成交额（元）',volume:'成交量（股）'});
Object.assign(states,{FIRST_FOCUS:'首次关注',CURRENT_UPGRADE:'当日关注升级',EXIT_EFFECTIVE:'生效退出',REQUIRED_FACTS_UNKNOWN_PRESERVE:'必需事实缺失，保留原判定',PREWATCH:'预观察资格',SEED:'种子资格'});
Object.assign(states,{EXPANDED:'放大',VERY_EXPANDED:'显著放大',CONTRACTED:'收缩',VERY_DRY:'显著萎缩',EXPANDING_EXTREME:'极端扩张',COMPRESSING_STRONG:'强压缩',HIGH_PARTICIPATION_EFFECTIVE_ADVANCE:'高参与度有效推进',HIGH_PARTICIPATION_LOW_EFFICIENCY:'高参与度低效率',HIGH_PARTICIPATION_REVERSAL:'高参与度反转',NORMAL_PARTICIPATION:'正常参与度',LOW_PARTICIPATION_ADVANCE:'低参与度推进',LOW_PARTICIPATION_DECLINE:'低参与度下跌',SHALLOW:'浅回撤',MODERATE:'中等回撤',DEEP:'深回撤',BULL_ALIGNED:'多头排列',BEAR_ALIGNED:'空头排列',BULL_TRANSITION:'多头过渡',BEAR_TRANSITION:'空头过渡',MIXED:'混合排列',MONTHLY_FLAT:'月线横盘',MONTHLY_DOWN:'月线下行',MONTHLY_UP:'月线上行',WEEKLY_FLAT:'周线横盘',WEEKLY_DOWN:'周线下行',WEEKLY_UP:'周线上行',BELOW:'低于前高',ABOVE_PRIOR_HIGH:'高于前高',NEAR:'接近前高',HIGH_ZONE:'高位区',MID_HIGH:'中高位区',EXTENDED:'延伸区',MID_ZONE:'中位区',MID_LOW:'中低位区',LOW_ZONE:'低位区',UPTREND_STRONG:'强上行趋势',SIDEWAYS_STRONG:'强横盘',DOWNTREND_STRONG:'强下行趋势',DOWNTREND:'下行趋势',SIDEWAYS_WEAK:'弱横盘',UPTREND:'上行趋势'});

Object.assign(states,{ROTATION_PULSE:'轮动脉冲',ROTATION_IN:'轮动进入',ROTATION_ACCEPTED:'轮动已接受',ROTATION_EXPANDING:'轮动扩散',ROTATION_REACCELERATING:'轮动再加速',ROTATION_OUT:'轮动退出',ROTATION_FAILED:'轮动失败',RECONSTRUCTED:'重建研究',CLOSED_ONLY_READY:'已结束周期',AS_OF_PARTIAL_READY:'截至当日形成中'});

Object.assign(labels,{quoted_count:'有行情成员数'});

Object.assign(states,{BULLISH_IMPULSE:'上涨结构脉冲'});
Object.assign(labels,{anchor_ordinal:'同股同日独立锚点序号'});

Object.assign(labels,{rule_id:'规则',rule_version:'规则版本',entity_type:'对象类型',evidence_class:'证据Lane',membership_basis:'成员口径',reason_codes:'原因代码',missing_inputs:'缺失输入',source_hashes:'来源摘要',input_cutoff:'输入截断时刻',captured_at:'采集时刻',frozen_at:'冻结时刻',nominal_return:'名义收益',horizon_sessions:'观察期限'});
Object.assign(states,{PENDING_FUTURE_SESSION:'未来交易会话',DUE_SOURCE_NOT_ACCEPTED:'到期日来源尚未接受',SOURCE_GAP:'已接受来源缺口',NO_QUOTE:'已核实无有效报价',SUSPENDED:'停牌',SETTLED:'已结算',RETROSPECTIVE_RESEARCH:'历史研究',LIVE_OOS:'在线前瞻观察',LATE_OBSERVED_NOT_PIT:'晚到且非当时可知'});

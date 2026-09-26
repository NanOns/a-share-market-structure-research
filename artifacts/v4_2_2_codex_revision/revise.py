from pathlib import Path
import re,hashlib,os,json,shutil,difflib
SRC=Path('D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925.md')
OUT=SRC.with_name(SRC.stem+'_codex修改版.md')
LOG=SRC.with_name(SRC.stem+'_codex修改版_修改说明.md')
BASE=Path(__file__).parent
original=SRC.read_text(encoding='utf-8-sig'); doc=original; changes=[]
def sec(start,end,body,reason):
    global doc
    a=doc.index(start); b=doc.index(end,a+len(start)); old=doc[a:b]
    doc=doc[:a]+body.strip()+'\n\n---\n\n'+doc[b:]
    changes.append((start.strip('# '),reason,len(old),len(body)))
def rep(a,b):
    global doc
    if a not in doc: raise ValueError('missing: '+a[:100])
    doc=doc.replace(a,b)

sec('# 大A市场结构研究系统','# 0. ','''# 大A市场结构研究系统 V4.2.2 codex修改版

> 文档编号：DA-MSR-V4.2.2-CODEX-REV1  
> 日期：2026-09-25  
> 状态：DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK / IMPLEMENTATION_NOT_VERIFIED  
> 原件：A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925.md；本文件由原件副本逐章修改，原件不变。  
> 代码基线：codex/algorithm-v3-incremental-upgrade @ 3ef5bf63455447dd605534dc4c1717eb238a86f5。  
> 最高任务：全市场每日状态理解、变化发现、可解释研究、持续跟踪和前瞻验证。

本版统一当前规范，保留原产品目标及无冲突章节，不把文档修改等同代码验收、真实数据验证或长期统计支持。§78 是唯一阶段表；§87A 是字段登记；§72 是参数治理。历史附录只解释沿革，不发出实施指令。遇到未预期冲突，登记 CONTRACT_CONFLICT 并只暂停受影响能力。

允许先做基线盘点、源能力验证和算法合同设计；对应模块实现前须具有其 Rule AST、参数实例、独立测试向量及数据合同。新增阈值均是 ENGINEERING_CANDIDATE，不是市场规律。

所有 TDX 根目录只读；下载、staging、归档、备份和临时文件均在项目管理目录，原子写入。原项目 Phase 0 必须有 FULL_PASS / DEGRADED_PASS / BLOCKED 回执，BLOCKED 范围不得进入 scanner。各阶段记录合同、证据、接受结果和下一阶段。M14 仅按已批准 dataset source contracts、能力门、有界请求运行，hot-rank direct mode 禁止持久化原始/行/批次/历史快照。跨域审计独立跟踪。
''','更正版本、授权边界、真实验收与文档状态')
sec('# 0C.','# 1. 审计意见裁决','''# 0C. 本版合同状态

产品目标保留；数据/算法按本文统一。实现、外部源覆盖、历史公司行为与真实 Forward 仍需阶段证据。所有页面字段必须进入 §87A 字段族及逐字段机器注册表。

# 0D. 依赖顺序

Source/Identity → Facts/Factors → Core Profile → Replay A → Seed → Sector/Rotation → PREWATCH 原始资格 → Confirmation/Structure detector facts → Final State → Events/Radar/Cohorts/Settlement → Replay B、实时 Shadow → 工程稳定与最低 Forward → Migration Replay → Focus/UI 切换。

开发阶段与每日拓扑不同：§78 约束交付，§13A/77B 约束运行。Settlement 在 Shadow 前交付；历史 replay 不计真实观察天数。

# 0E. 审计处置

上一轮 A01–A12、本轮 B01–B10 和全文新增修订见配套修改说明。状态为 DOCUMENT_REVISED，不自动 CLOSED；代码、真实数据、独立审计、Forward 分别验收。

BaoStock 可复用已有有效调用回执，但能调用不等于全市场覆盖、无限额度或全部历史字段可信。缺能力证据只限制该补充 dataset，不阻断 TDX 主链。''','清除旧CLOSED声明和过期流程')
rep('| Trade Status | BaoStock + 本地 TDX可观察状态 | 二者冲突则降级 | 不把缺失当停牌 |','| Trade Status | accepted local security master + TDX/calendar facts | BaoStock 独立 cross-check | 缺失不是停牌，冲突只标补充告警 |')
rep('| ST | BaoStock `isST` + 本地证券元数据 | 冲突进入质量告警 | 不静默改变 Universe |','| ST | accepted local security master 日期有效身份 | BaoStock 仅 cross-check | 未知则对应规则 UNKNOWN |')
sec('## 4.6 Historical Reconstruction Identity','## 4.7 Prior-Session','''## 4.6 Historical Reconstruction Identity

唯一枚举：evidence_origin=PIT_OBSERVED / RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED / DIAGNOSTIC_NON_PIT；execution_mode=PRODUCTION / SHADOW / REPLAY。

PIT_OBSERVED 是运行时真实冻结的源消费集合与结果，生产和 Shadow 均可；事后按 T0 有效/知识时间重建为 RECONSTRUCTED_ASOF；用后来更正为 RECONSTRUCTED_CORRECTED；任何必要时序条件无法证明为 DIAGNOSTIC_NON_PIT。

分别保存 universe_basis、membership_basis、price_basis、quality；不要把 CURRENT_MEMBERSHIP/PRICE_ONLY 混进 origin。每个输出按实际依赖的最弱证据降级。正式观察 cohort 只接受 PIT_OBSERVED，按 Shadow/Production 分层；历史重建只能作工程 replay、案例、参数初检，不合并真实 Forward。''','统一证据枚举')
sec('## 4.7 Prior-Session','## 4.8 Model','''## 4.7 Prior-Session State 与 Same-Day Revision Parent

t 首次创建计算 lineage 时，冻结同模型上一市场交易日 accepted publication id、revision、logical digest 为 prior_session_state_head。t 的所有同日 revision 使用相同前驱；same_day_revision_parent 只用于修订差异。

T-1 未确认、T r1/r2/r3 均确认，则三者都是 NEW_CONFIRMED。若 r2 撤销资格，追加事件 observation RETRACTED；当前投影按 r2，原实时 enrollment 保留并标 SOURCE_CORRECTION，不伪造市场失效。

T-1 后来更正不改变已冻结 T；要传播则新建 CORRECTED_RECONSTRUCTION lineage 有序重算。上一市场日未发布时记录 gap，不能跨多日称“昨日”；纯事实可发布，状态暂停升级/退出，补齐有序状态或显式初始化边界后恢复。''','冻结前驱、修订撤销和历史更正')
rep('Shadow 必须读取 Shadow 自己的 prior-session state，不能把 Legacy 前态当 V4 前态。','''Shadow 必须读取 Shadow 自己的 prior-session state，不能把 Legacy 前态当 V4 前态。

model_contract_id 绑定代码/AST/参数/源语义摘要；参数变更必须新模型身份。state_lineage_id 与执行 namespace 分开：同模型 Shadow→Production 经 migration manifest 显式继承最后 Shadow 前态与 episode mapping，不制造 FIRST/REENTRY。不同模型产生 MODEL_BOUNDARY 和新 cohort。旧 episode follow-up、pending outcome 独立保留结算。''')
sec('## 5.2 Canonical Trading Status','## 5.3 Historical','''## 5.2 Canonical Trading Status

trading_status=ACTUAL_TRADED / SUSPENDED / DATA_GAP / UNKNOWN。RESUMED 是事件，DELISTING 是 lifecycle 字段；涨跌停独立为 limit_status。确认停牌需日期有效证据；无 bar 不等于停牌，换手/金额不填零。

收益窗口、状态计数和 Forward horizon 分别按 §10A0/31/46A，不能用一个“有效会话”代替不同时间尺度。''','拆分交易状态轴')
sec('# 6A. 双时间 PIT','# 7. Canonical','''# 6A. 双时间 PIT 与实际消费版本

可修订事实保存 effective_from/to、provider_available_at（可未知）、observed_at、ingested_at、source_revision_id、supersedes_revision_id、source_identity。available_at 旧别名只指 system_available_at=max(observed_at,ingested_at)，不能填供应商公开时间。

AS_RECORDED 读取 publication_consumed_sources 冻结的 key/revision/digest，不扫描最新事实。构建要求 effective_from<=T0<effective_to（空结束为无穷）、system_available_at<=cutoff；同 key 选 cutoff 内更正链唯一末端。分叉、内容冲突或无确定顺序为 SOURCE_REVISION_CONFLICT，不随意取最大时间。

原始行、tombstone、版本关系 append-only；消费 manifest 与 accepted head 原子提交。供应商早已公开但系统迟到的数据不属于过去 AS_RECORDED。知识时间重建与实际观察分开。

验收：T+10 才到的 effective=T-5 行、多版本、删除、乱序、分叉。旧 publication 与原 Forward enrollment digest 不变，当前修订显式变化。''','PIT消费清单与双时间修订选择')
rep('turnover_rate\nturnover_quality\n\nfact_digest','fact_digest')
sec('## 7.4 `stock_daily_profile`','## 7.5 `stock_bar_weekly`','''## 7.4 `stock_daily_profile`

主键(publication_id,security_id)，trade_date 复合 FK。Core 字段仅为 §10A.3 Core Profile V1；不含 basic_breakout/pullback/recovery 或 sector relative。

Participation 在 V4-06，Context/Structure 在 V4-13，Why Now 在 V4-15。组件状态独立为 NOT_IMPLEMENTED/PENDING_SOURCE/READY/PARTIAL/UNKNOWN_DATA/DEGRADED/NOT_APPLICABLE。全产品目标不要求 V4-04 完成后续能力。

Core digest 只绑定 Core；combined view digest 绑定完整 context token。异步 turnover 仅存 stock_profile_enrichments，不能改变 stock_fact_daily。''','同步画像schema与分层')
rep('base_seed_count\nbase_seed_width_raw\nbase_seed_width_adjusted\n','base_seed aggregates 存 PASS B sector_seed_aggregates，不属于预计算 native facts\n')
rep('why_now_digest\n```','```\n\nWhy Now 单独存 D 阶段 state_events/Radar，不进入 B 的摘要。')
rep('不得通过此表直接改写 Core maturity / eligibility。','''不得通过此表直接改写 Core maturity / eligibility。

Core、sector aggregates、structure observations、state transitions、Radar/enrollment 均绑定 publication_id 与模型。Anchor 原值不可变，validity 存 observation。enrichment_revision 为每个 publication 全局 manifest revision，包含各证券/provider 的具体 revision；唯一键(publication_id,enrichment_revision,security_id,provider)。周期 bar 唯一键(publication_id,security_id,period_start_date,period_view,price_basis)，保存 adjustment identity，不覆盖旧周期版本。''')
rep('turnover\n= optional','turnover\n= supplemental-only，非 Core qualification input')
sec('## 9.4 历史回填','## 9.5 绑定状态','''## 9.4 历史回填

最低覆盖：目标日前60个实际成交且 strict-bound 样本，加目标日；优选此前250样本。基准排除当日，确认停牌才能跳过，未知网络缺失不能跳过。最大回看250市场会话，不足窗口只降级该指标。

任务 checkpointable/idempotent/budget-aware；每请求 timeout、并发、重试预算、熔断写入 source contract。已有回执可复用，不做无界测速，不阻断 Core。''','统一历史样本口径')
sec('## 9.6 Turnover Factor','## 9.7 Turnover','''## 9.6 Turnover Factor

contract_id=TURNOVER_CONTEXT_V1。priorN 为 t 前最近 N 个确认实际成交且严格绑定样本；未知缺失不能跳过，N=5/20/60，最大回看250市场日。ma5=prior5均值，median20=prior20中位数，ratio20=turn[t]/median20（分母<=0为UNAVAILABLE）；pctN=100*(count(prior<turn[t])+0.5*count(prior=turn[t]))/N。delta3=turn[t]-turn[t-3]，市场日期端点缺失为UNKNOWN。

全部为 supplemental，不进入 Core eligibility、正式排序或 Focus activation。单位由 source contract 冻结。''','精确换手窗口、分位与分母')

sec('# 10A0. Algorithm Freeze Gate','# 10A. 全市场','''# 10A0. 原子因子、三值逻辑与冻结门

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

本文章节规则实例化为RULE_AST_FROZEN，经schema及独立正反向向量验收才TEST_VECTOR_PASS。旧V3/V3.3通过§34精确extraction manifest冻结，不能仅说沿用思想。''','完整原子因子、窗口与算法门')
sec('# 10B. Trend State 算法','# 10N. A股','''# 10B. Trend State 算法

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
''','完整Core与高级字段有序规则、唯一枚举')
sec('# 13. 防反馈计算 DAG','# 14. PASS A','''# 13. 防反馈计算 DAG

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
''','明确detector先于state，消除隐藏反馈和后置失效')
sec('## 14.2 Hard Safety','## 14.4 输出','''## 14.2 Hard Safety

contract_id=BASE_SEED_V1。safety=research_universe AND actual_bar AND price_identity_READY AND minimum_liquidity AND NOT core_price_damage AND NOT severe_extension。三值归约后FALSE拒绝，UNKNOWN待评估，TRUE才检查路径。minimum_liquidity=prior20 mean amount>=20,000,000 CNY；金额单位先通过source contract。本版为工程候选，不冒充已验证最佳阈值。

## 14.3 Seed Rule Paths

POSITION_OK=(bias20_atr<3)；STRUCTURE_IMPROVING=(compression_state in {COMPRESSING,COMPRESSING_STRONG})；RELATIVE_CHANGE_IMPROVING=(delta3>=3)；RELATIVE_CHANGE_STRONG=(delta3>=10)；TREND_TRANSITION_EARLY=(ma_structure_state=BULL_TRANSITION OR (C[t-1]<=MA20[t-1] AND C[t]>MA20[t]))。

S1=POSITION_OK AND STRUCTURE_IMPROVING AND RELATIVE_CHANGE_IMPROVING。
S2=POSITION_OK AND RELATIVE_CHANGE_STRONG AND TREND_TRANSITION_EARLY。
base_seed_state=safety AND (S1 OR S2)。这些谓词只读Core，严格三值逻辑，不读高级Anchor。

seed_participation_annotation按core_participation_result：有效推进SUPPORTED，反转/低效CONFLICTING，其余NEUTRAL，未知UNKNOWN。不计新路径、不影响资格；turnover只另作补充说明，不进入正式排序。
''','补齐Seed谓词和纯Core安全门')
sec('# 15. PASS B','# 17. Sector','''# 15. Sector Native 与聚合合同

contract_id=SECTOR_FACTORS_V1。对日期t的真实成员M_t构建可评估集合E_t，quote_coverage=|E_t|/|M_t|；未知成员来源为UNKNOWN。Core sector最低成员5、coverage>=0.8，低于门限不产生正式sector资格。

sector_rsN=成员retN中位数，sector_rsN_pct按同日eligible板块midrank（§10A0公式），rank_velocityK=percentile[t]-percentile[t-K]，dq5=rs5_pct[t]-rs5_pct[t-3]。排名跨日Universe变化要保存两个snapshot；同分同分位，展示tie-break用sector_id。

breadth_ret1=count(ret1>0)/count(ret1 known)；ma20_width=count(C>MA20)/count(MA20 known)。deltaK只在M_t∩M_(t-K)且两端该指标均可评估的共同成员上分别重算再相减；保存common_count与coverage。成员新增/删除单独记录membership_entered/exited，不算市场强弱进出。

strong成员=RPS20>=80且可评估；retention=|strong_prev∩strong_now|/|strong_prev|，分母0为NOT_APPLICABLE。未知当前结果标unknown_retention_count，不当退出；Core需要全部该分母成员可观察，否则该retention UNKNOWN。Seed留存同理；PREWATCH仅用t-1成员在t日Core谓词是否仍满足，不读取C[t]最终集合。

sector_participation_proxy=median(成员amount_ratio20)，与Amount A明确不同；top1/top3_concentration为金额份额，分母是同日可评估成员金额总和，零分母UNKNOWN。正式Core本版不用未关闭的Amount A，也不用turnover。

# 16. 小板块调整

contract_id=SEED_WIDTH_V1。n=BaseSeed可评估成员数，k=TRUE数；n=0 UNKNOWN。raw=k/n；adjusted=(p+z²/(2n)-z*sqrt(p*(1-p)/n+z²/(4n²)))/(1+z²/n)，z=1.96。

Wilson式只作为样本量惩罚的排序启发式，不声称成员独立、统计置信覆盖或上涨概率；板块成员相关，不能据此作概率结论。保存k/n/unknown_count/raw/adjusted，coverage门先于排序。''','板块共同成员、retention分母、金额代理和Wilson解释')
sec('# 17. Sector PREWATCH','# 19. 板块重叠','''# 17. Sector PREWATCH / WARM / CONFIRMED

contract_id=SECTOR_QUALIFICATION_V1。sector_safety=membership_READY AND member_count>=5 AND quote_coverage>=0.8。
prewatch_raw=sector_safety AND dq5>=3 AND (breadth_delta3>0 OR ma20_delta3>0) AND adjusted_seed_width>=0.05。不要求市场上涨；UNKNOWN不当FALSE。此原始谓词不排除更高阶段，最终D2按最高已确认资格选成熟度。
warm_raw、confirmed_raw来自§34已提取验收的纯Core legacy合同；未就绪时该能力NOT_IMPLEMENTED，不从POTENTIAL/CURRENT标签猜测规则。若legacy资格依赖未关闭Amount A，则该路径不能作为正式资格，保留diagnostic；其他独立路径不受影响。

# 18. Sector 三轴

contract_id=SECTOR_AXES_V1。emergence：HIGH（dq5>=10 AND breadth_delta3>=0.05 AND adjusted_seed_width>=0.1）；MEDIUM（dq5>=3 AND (breadth_delta3>0 OR ma20_delta3>0)）；LOW（其余可评估）。confirmation_axis保存confirmed_raw/warm_raw/coverage，不读D2。
exhaustion：HIGH（rs20_pct>=80 AND dq5<=−5 AND breadth_delta3<=−0.05）；MEDIUM（rs20_pct>=80 AND dq5<0）；LOW。extension share作为并列事实，不重复计价。required未知则对应轴UNKNOWN，不用其他轴掩盖。
''','补齐Sector资格与轴规则并隔离legacy未闭合依赖')
sec('## 20.3 ALGORITHMIC_SUPPORT_SECTOR','## 20.4 Historical','''## 20.3 ALGORITHMIC_SUPPORT_SECTOR

contract_id=LOO_CONTEXT_V1。在真实membership内，对目标股排除后重算sector native、seed aggregates、B0/B2原始资格以及其所需的历史比较。不得只减计数而保留原rank/median/状态。历史状态若用于context也从排除目标的独立lineage重算；无法重算时不使用该项。
按LOO confirmed_raw、warm_raw、emergence(HIGH>MEDIUM>LOW)、adjusted_seed_width降序，再sector_id升序选择。过滤quality非READY。保存全部候选及选择理由；没有合格者NULL/NOT_APPLICABLE，数据不足UNKNOWN。Context最多一份，不能提升stock hard eligibility。
''','LOO重算范围、历史状态与确定性选择')
sec('## 21A.4 Rotation Inputs','## 21A.12 页面展示','''## 21A.4 Rotation Core Rules

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
''','完整Rotation跨日状态与防反馈拓扑')
sec('## 22.1 PREWATCH Eligibility','# 23. PREWATCH','''## 22.1 PREWATCH Eligibility

contract_id=STOCK_PREWATCH_V1。raw_qualification=base_seed_state AND mandatory_core_quality_READY。C只输出原始资格，不读D2 validity。D2在§31结合已冻结研究episode的当日硬失效，产生final_eligibility。Sector Context只在D3影响解释和独立context排序键，不能成为硬门。
''','消除PREWATCH读取后置validity')
sec('# 24. Priority Bucket','# 25. Staleness','''# 24. Priority Bucket

contract_id=PRIORITY_V1。stock emergence=HIGH(delta3>=10)、MEDIUM(delta3>=3)、LOW；structure=HIGH(COMPRESSING_STRONG)、MEDIUM(COMPRESSING或BULL_TRANSITION)、LOW。risk使用core_extension_risk。
顺序A：emergence HIGH AND structure HIGH AND risk LOW；B：emergence HIGH AND structure>=MEDIUM AND risk<=MEDIUM；C：emergence MEDIUM AND structure HIGH AND risk LOW；D：其余eligible。排序键缺失放该桶末尾并显示UNKNOWN，不改变资格。
确认股票的桶：A=confirmed_raw且risk LOW且structure HIGH；B=confirmed_raw且risk<=MEDIUM；C=confirmed_raw且risk HIGH；D=其他可展示已确认对象。risk EXTREME/hard damage 是否final eligible由§31决定，不允许用桶覆盖硬门。
''','精确分桶和缺失排序')
sec('# 27. Market Regime','# 29. Regime','''# 27. Market Regime 四轴

contract_id=MARKET_REGIME_V1。趋势使用§49A市场参考日路径，trend_axis=STRONG(指数C>MA20且MA20比5日前上升)、WEAK(反向)、NEUTRAL；不足UNKNOWN。
breadth_axis按全市场共同成员breadth_delta3：>0.05 IMPROVING、<−0.05 DETERIORATING、其余STABLE。participation_axis按全市场成员amount_ratio20中位数：>=1.2 EXPANDING、<0.8 THIN、其余NORMAL。
stress_level以有效limit规则覆盖>=0.8为前提，down_limit_count/evaluable_count>=0.05 HIGH、>=0.01 ELEVATED、否则LOW；不可用UNKNOWN。stress_change按同成员比率日差：>0 RISING、<0 DECLINING、=0 STABLE，未知UNKNOWN。

# 28. Regime UI Mapping

first-true：必需轴UNKNOWN→UNKNOWN；trend WEAK且stress HIGH→CAPITULATION；trend WEAK且breadth IMPROVING且stress_change DECLINING→RECOVERY_ATTEMPT；trend STRONG且breadth非DETERIORATING且stress LOW→RISK_ON；trend WEAK或stress HIGH→RISK_OFF；其余NEUTRAL。
映射候选连续2个可评估市场会话才切标签，CAPITULATION立即；数据缺失显示UNKNOWN及last_known，不把旧标签说成当日判断。该映射只解释，不切换资格参数。
''','Regime四轴完整算法、stress change和hysteresis')
sec('# 31. 状态转移规则','# 34. V3','''# 31. Final State Reducer

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
''','状态reducer完整优先级、数据缺失、同日冲突、expiry与重入')
rep('作为：\n\n```text\nConfirmation Engine\n```','''作为 Confirmation detector facts，输入时点依 §13A，最终事件在D2之后生成。

LEGACY_ADAPTER_V1：V4-00A提取基线每条保留函数的路径/符号/源码hash、调用图、参数、输入单位/时间、输出与UNKNOWN语义，在V4-11生成精确AST与黄金向量。当前源码不是未来变量；一经提取绑定model_contract_id。若发现内部读取Final State、Focus或在线补充，拆成纯函数或保持diagnostic，不能直接入正式D0。未提取模块只阻断其场景，不阻断F0/Core。''')
sec('## 34A.5 Event Classification','## 34A.6 首页','''## 34A.5 Event Classification

contract_id=STATE_EVENT_V1。仅对D2和冻结prior_session_state_head做diff；first-true：有效前态缺失→FIRST_OBSERVED；关联旧episode本日硬失效→CONFIRMATION_INVALIDATED；本日确认且该episode曾确认、上一可见状态已弱化/退出→RECONFIRMED；本日确认且前态未确认→NEW_CONFIRMED；持续确认且primary_scenario按冻结优先表更高→SCENARIO_UPGRADED；旧确认而health/资格变弱→CONFIRMATION_WEAKENED；均确认且无变化→PERSISTENT_CONFIRMED；其余NONE。

scenario变化非升级时单独SCENARIO_CHANGED，不伪称更强。成熟度与health不得互相比较枚举。多事件分别保留，primary_event按上述序，仅用于展示，不能删除其他轴的反证。每(publication_id,entity_type,entity_id,event_type)唯一。
''','事件互斥、reconfirmed与新确认重叠')
sec('## 34A.10 Priority','## 34A.2A Confirmation','''## 34A.10 Priority

确认对象复用唯一PRIORITY_V1的确认分桶和稳定排序。不得在此重新维护另一套优先级或参数。''','删除重复分桶')
sec('# 37. Near-Miss','# 38. Near-Miss','''# 37. Near-Miss：AST 失败谓词

contract_id=NEAR_MISS_V1。先按正常Hard Safety求值，硬失败对象只展示风险解释，不排入“差一点可入选”。对S1/S2完全可评估路径，distance=(FALSE叶谓词个数, 按固定predicate_id顺序的单位归一化shortfall向量)，词典序比较，不把不同单位相加。
连续谓词shortfall=max(0,threshold−value)/scale（方向相反则反向），scale由参数合同冻结且>0；离散FALSE为1，TRUE为0。取路径最小词典序距离；所有路径含UNKNOWN则distance=NULL、UNRESOLVED，不把未知当0。页面列具体未满足/未知谓词，不能将Near-Miss当收益分数。
''','修复Near-Miss未知和跨单位距离')
sec('## 41A.2 Anchor Type','# 41B. Bullish','''## 41A.2 Anchor Type 与选择

contract_id=STRUCTURE_EVENT_V1。V1支持PRIOR_HIGH/BREAKOUT_LEVEL、RANGE_UPPER、BULLISH_IMPULSE_BODY/LOW、MA20_DYNAMIC/MA60_DYNAMIC、PIVOT_LOW、GAP_ZONE；每类须有明确来源事件，不能看图事后随意画线。
PRIOR_HIGH=此前20日最高价；RANGE_UPPER仅当此前20日range/ATR<=4且slope20绝对值<=0.1，取此前20日高；impulse按§41B；dynamic MA来源于此前注册的上涨事件，其公式冻结，每观察日生成新值不改旧值。
PIVOT_LOW采用左右各2日低点确认，最早在pivot_date+2实际可评估会话才能注册，available_date为确认日不能倒填；GAP_ZONE需L[t]>H[t-1]，区间[H[t-1],L[t]]，注册日不能参与回测支撑。

## 41A.3 Anchor 冻结

固定Anchor原坐标及事件不回写；每日换基视图按§41A0。动态MA不得伪称固定支撑价。每个Anchor分别跟踪；active_anchor按是否未失效、与C距离/ATR升序、anchor_date降序、anchor_id升序选择供页面展示；研究episode invalid_if使用创建时绑定的Anchor，不能随active_anchor切换。
平台/前高基于历史复权坐标建立时，使用逆仿射变换存anchor_basis_trade_date raw坐标，并保存原变换摘要；不是把历史最高raw直接用于当前坐标。
''','Anchor类型算法、pivot确认延迟、多Anchor与冻结选择')
sec('# 41B. Bullish','# 41C. Support','''# 41B. Bullish Impulse

contract_id=STRUCTURE_EVENT_V1。body=C-O，body_atr=body/ATR20[t-1]，range_atr=(H-L)/ATR20[t-1]；昨日ATR换到当前价格坐标后计算，避免今日大振幅抬高自身阈值。CLV按§10A0。
core_bullish_impulse=(body_atr>=1 AND range_atr>=1 AND CLV>=0.7 AND amount_ratio20>=1.2 AND rel_market_1>0)。数据不足UNKNOWN，一字板CLV未知不能靠该分支确认。turnover只能生成独立补充说明。
记录open/body_mid/close/low/high；BODY区间[O,(O+C)/2]，LOW区间[L,L]，最早次日开始测试。价格区间只是研究Anchor，不映射买点。所有新增阈值写入§72候选参数实例。
''','中阳排除自归一化偏移和补充污染')
sec('# 41C. Support','# 41E. Structure','''# 41C. Support / Acceptance 状态机

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
''','日线支撑FSM、retest间隔、破位时间、retention分母')
sec('# 41F. Daily Profile','# 42. Focus','''# 41F. Profile 分阶段

Core字段在V4-04，Turnover在V4-06，Structure/Anchor/Support在V4-12，Context/Structure投影在V4-13，Why Now在V4-15。API在Core阶段允许组件NOT_IMPLEMENTED；完整产品验收才要求已承诺的后置组件就绪。字段登记只用§87A，禁止另列“第一阶段必须全部高级状态”。
''','删除残留第一阶段全部实现要求')
sec('# 45. 独立 Validation Cohort','# 50. Forward','''# 45. 独立 Validation Cohort

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

contract_id=MARKET_BENCHMARK_V1。Core历史市场参考retN：在起点t-N已符合Universe且N+1窗口完整的股票等权endpoint return均值，保存起点Universe/可观察集合/coverage；缺失超过20% UNKNOWN，不能只凭现在存活证券补池。市场趋势路径为连续这些ret1链乘，标daily-rebalanced research index，非交易所指数，不与单一股票收益混名。

Forward市场基准：T0冻结可评估Research Universe，等权固定份额，每股收益按同基准换算，B_j=sum(w_i*(P_i,j/P_i,0))。不因后来变强/退市重选或再归一化剩余成员。完整endpoints才正式OBSERVED；成员终点缺失则benchmark UNKNOWN并披露范围，不能使股票absolute_return失效。
Sector基准同式，T0按§20确定sector，冻结成员和等权份额；对stock relative_sector排除目标股票，n<2不提供；SECTOR signal直接使用自身冻结篮子。identity含member/weight/source/adjustment digest。
relative_market_return=stock_R−market_B_return；relative_sector_return同理。sector endpoint/path以同一固定篮子计算；日线无法知道成员盘中极值是否同步，故SECTOR的MFE/MAE采用close-only并独立命名MFE_CLOSE/MAE_CLOSE，不能把成员high求和冒充板块intraday高点。板块和股票outcome分开统计。

# 49B. Matched Controls 与分析

contract_id=CONTROL_ASSIGNMENT_V1。T0符合相同Hard Safety、非当日PREWATCH final eligible且非本事件实体为池；优先同primary industry（必须T0可知），缺行业允许全市场并标MATCH_SCOPE_MARKET。距离为prior20 mean amount的log值、vol20、RPS20各自同日百分位差绝对值之和，固定顺序tie-break security_id。每signal最多3个最近对照，允许不同signal复用；不足保存实际数量，不用未来补选。冻结features/assignment digest。
后来对照入选只追加crossed_signal_at，ITT主分析保留。CLEAN_CONTROL只作为明确标识的事后敏感性子集，禁止用于主要增量结论或切换门；不得因“剔除了未来入选者”宣称因果优势。按security、signal_date、sector重叠分层披露；无预注册相关性处理时只提供描述统计，不给概率/显著性保证。
''','重建完整Forward、修正MDD、结算前置、benchmarks和control')
sec('# 51A. Evidence Origin','# 53. 三道','''# 51A. Evidence 与执行方式

统一使用§4.6枚举：PIT_OBSERVED+SHADOW可进入真实Shadow cohort；RECONSTRUCTED_ASOF+REPLAY不可冒充观察。

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
''','可执行切换政策、统计事件计数、降级回执映射')
rep('作为正式 Focus source。','作为正式 Focus source。') if '作为正式 Focus source。' in doc else None
sec('# 70A. Inherited Audit Register','# 71. 当前','''# 70A. Inherited Audit Register

| 项目 | 状态 | 权限与关闭条件 |
|---|---|---|
| AUD-AMOUNT-A-06 | OPEN/EVIDENCE_REQUIRED | amount_a_value/quality/contract_id分开；OPEN时只diagnostic，不进正式资格/排序/Focus。独立单位/共同成员/20日分母/覆盖/集中度实算及跨域引用验收后新合同启用 |
| Focus真实Forward缺口 | OPEN/FORWARD_REQUIRED | 保留原专项的精确范围和证据；旧新episode并存等真实样本继续跟踪，文档/合成通过不自动关闭 |
| 历史Universe/membership | CAPABILITY_SCOPED | current replay只diagnostic；按source证据升级 |
| 本轮全文修订 | DOCUMENT_REVISED | 代码和真实样本按模块独立验收，不能以文档自检关闭生产审计 |

sector_participation_proxy=median(member amount_ratio20)可依SECTOR_FACTORS_V1使用，必须另名，不称Amount A。若legacy M10路径需要Amount A而未通过，则该路径diagnostic，不暗换代理以维持正式资格。其他独立Core路径仍可运行。
''','Amount A数值与质量分离、显式消费者权限')
sec('# 72. 参数注册表','# 74. 性能','''# 72. 参数注册表

contract_id=PARAMETER_REGISTRY_V1，初始parameter_set_id=V422_CODEX_ENGINEERING_01。本文新增规则中的数值均为候选默认值，包含窗口、阈值、计数、coverage、分桶边界、显示cap及排序scale；实现时提取到对应algorithm contract的命名参数，不散落代码。符号阈值没有赋值的模块不得静默选值。

每个参数保存id、contract_scope、value、unit、min/max与边界是否含等号、status、reason、introduced_version、approved_at、supersedes。通用epsilon用于浮点比较仅1e-12（单位随比较字段），金额/价格制度舍入单独按源/制度contract，不用此epsilon识别涨跌停。

初始关键参数：MA窗口5/10/20/60；slope deadband 0.1 ATR；minimum_liquidity 20,000,000 CNY prior20均额；RPS改善3/强改善10百分点；sector最少5成员/coverage0.8；Wilson z1.96；exit连续2会话；seed expiry10可评估会话；support浅收盘破0.5ATR/硬破1.5ATR/触碰带0.25ATR；Shadow20连续市场日/5个信号日/30个股票事件T5。

状态ENGINEERING_CANDIDATE→SHADOW_FROZEN→PROVISIONAL→SUPPORTED或RETIRED。值变更必须新parameter_set_id和model_contract_id，重新冻结cohort；旧值与旧outcome不改。候选默认值不因本文件存在而成为最佳或有效算法。现有Legacy阈值从基线源码提取保留，不用新增默认值覆盖Legacy。

Legacy contract提取、source units/历史制度表与性能预算属于测量型参数，须有真实回执再冻结；不是让实施者发明事实。未就绪只限制其模块，基础盘点和纯Core合同工作可继续。

# 73. 禁止实现硬编码与参数偷换

代码从参数实例读取；正文数值是可审阅候选参数说明。构建验收生成参数使用清单，每个AST literal必须有parameter_id或明确数学常数/枚举说明。所有尺度scale>0，整型窗口/计数必须正整数，coverage在[0,1]，排序边界有序。无该实例或digest不匹配拒绝affected计算，不回退到某个全局默认。
''','统一新增候选阈值治理，不把参数化当作没有定义')
sec('# 77A.','# 77C.','''# 77A. 历史初始化

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
''','全流水线、原子提交、outbox、结算和可选源解耦')

stages=[
('00A','Baseline Freeze','当前HEAD、DB备份/恢复回执、accepted/Focus head、旧输出及继承审计；只读盘点不依赖未来AST'),
('00B','Security Lifecycle / Universe / PIT','日期有效身份、知识时间、历史覆盖与不支持范围'),
('00C','Publication / Revision / Namespace','冻结前驱、消费manifest、修订事件与原子接受、namespace迁移'),
('00D','TDX VIPDATA Source Contract','有界下载、隔离staging、manifest、校验、archive与overlap'),
('00E','Historical Adjustment / Coordinates','仿射调整、公司行为、历史可见性、Anchor与outcome比较坐标'),
('00F','BaoStock Supplemental Contract','字段单位/strict binding/有界请求；可复用有效回执，不阻断Core'),
('00G','Algorithm Contract Framework','AST/schema/参数实例、字段producer注册、纯函数Legacy提取规范'),
('00H','Capability / Performance / Rollback','能力scope、预算、失败回执、恢复演练；Phase 0最终回执'),
('01','TDX History Bootstrap','Raw archive、历史Universe和重叠核验；历史不足可scope降级'),
('02','Canonical Daily / PIT Periods','Raw/Adjusted、closed/asof周期、Price Limit规则表和覆盖'),
('03','Pure-Core Factors','CORE_FACTOR_V1、市场/sector native primitives、benchmark基础价格路径'),
('04','Full-Market Core Profile','§10B–10I全部Core字段，不依赖高级Anchor/Sector Context/BaoStock'),
('05','Replay Gate A','DATA_FACTOR_REPLAY_PASS及能力scope，失败只阻断affected后继'),
('06','Supplemental Enrichment','Turnover历史/绑定/补充组件；与Core后继无硬依赖'),
('07','Stock Base Seed','BASE_SEED_V1与原始资格'),
('08','Sector / Rotation Core','共同成员、B0/B1/B2、纯Core legacy sector资格adapter'),
('09','Stock PREWATCH','STOCK_PREWATCH_V1原始资格与priority primitives'),
('10','State Reducer','RESEARCH_STATE_V1接口与独立向量；最终集成须等D0/D1交付'),
('11','Confirmation / Events','Legacy精确AST提取/黄金样例、D0 facts与D2后event diff，隔离Amount A路径'),
('12','Structure / Anchor / Support','D1算法、换基、breakout/pullback/recovery、支持/接受'),
('13','Profile Advanced Projection','Context/LOO/Structure投影与完整DAG集成'),
('14','Replay Gate B','ALGORITHM_STATE_REPLAY_PASS：完整D0/D1/D2时序与修订'),
('15','Radar / Cohorts / Settlement','字段全量登记、事件样本、控制分配、市场/板块benchmark、due planner、价格结算、结果修订、Why Now及readback'),
('16','Realtime Shadow Dual-Run','PIT_OBSERVED+SHADOW，真实冻结日账本并每日运行settlement，旧系统继续production'),
('17','Shadow UI','同context token，展示完整已实现组件，不写production Focus'),
('17G','Shadow Stable / Provisional Forward Gate','§52A两门，样本不足延长观察；禁止以historical replay凑天数'),
('18','Migration Replay Gate','MIGRATION_REPLAY_PASS：前態继承、旧episode/未结算工作、namespace和rollback'),
('19','Focus Source Cutover','仅§52A三门通过后，accepted V4 source进入生产Focus'),
('20','Default UI Cutover','默认V4，Legacy下沉diagnostic，明确PROVISIONAL'),
('21','Continued Forward Observation','继续累计Shadow/Production各自分层证据；不在此首次开发结算器'),
('22','Independent Audit','数据/算法/发布/迁移/UI/Forward/rollback独立验收；开放项不自动关闭')]
stage_table='| 阶段 | 唯一名称 | 交付与准入 |\n|---|---|---|\n'+'\n'.join(f'| V4-{n} | {name} | {detail} |' for n,name,detail in stages)
sec('# 78.','# 79.','''# 78. 唯一实施阶段表

阶段按下面顺序交付，V4-06可选分支不是V4-07前置。算法实现前先完成该模块AST/参数/向量；纯基础盘点不受全局算法冻结阻断。V4-10可实现reducer接口和独立向量，但完整运行必须等V4-11/12，再于V4-14验收，不能把接口测试当完整DAG通过。

'''+stage_table+'''

每张卡记录input commit、适用合同、source/capability、allowed/forbidden files、schema migration、fields/producer/time、UNKNOWN行为、旧行为保护、独立test vectors、集成/E2E/replay、rollback、evidence receipt、acceptance scope及next stage。卡模板允许CONTRACT_DESIGN任务，不允许假称DRAFT算法已验收。''','唯一阶段表、结算前置、reducer交付与集成区分')
sec('# 79.','# 80.','''# 79. Phase 与 Priority

P0表示受影响正式能力不可越过，不表示全项目一次实现。以§78的稳定阶段ID引用，不再保留另一套阶段名称；V4-05 Replay A在Core之后，V4-14在完整算法集成之后，V4-18在真实Shadow门之后。所有DEGRADED必须携带scope，BLOCKED scope不可进入其scanner/consumer。
''','删除旧阶段引用')
sec('## 81.4 Contract Completeness DoD','# 82.','''## 81.4 Contract Completeness DoD

允许先拆基线与合同设计卡；对应实现卡开工前必须有该模块字段注册、AST/参数实例、producer/time semantics、source能力/UNKNOWN及独立向量。没有则该模块CONTRACT_INCOMPLETE，不能由实现者悄悄补语义。
整体上线前所有承诺组件与用户可见字段须覆盖§87A机器注册表，且通过完整DAG、发布一致性、source degradation、真实Shadow/Forward与迁移门。文档检查不替代代码测试、实测性能或统计证据。
''','消除全局冻结门自阻塞')
sec('# 83. 风险与失败回滚','# 84. 术语表','''# 83. 风险与失败回滚

§52A是唯一切换政策。“样本不足/尚未证明增量”不能当作已失败或改候选阈值的理由。Shadow P0、无法解释的系统异常、超事前冻结运行预算则NO_CUTOVER并登记独立审计；修订算法/参数要新模型和cohort。
切换后保留legacy可恢复运行能力；失败时切读/写source namespace，保留V4不可变历史、outbox和未完成outcome。停止不合法新副作用，已接受的事件不删除；恢复旧系统时按预演manifest处理切换期间空档，不能只恢复一个数据库备份而丢失用户pin/后续观察。
''','统一失败与无优势政策，补完整rollback语义')

# Replace duplicate mapping references with authoritative contract families.
fields=[]
def field(names,authority,cid,phase,unknown):
    fields.append((names,authority,cid,phase,unknown))
field('trend_state; weekly_trend_state; monthly_trend_state','TDX adjusted/closed periods','TREND_STATE_V1','04','required缺失UNKNOWN')
field('position_state; near_high20_state; near_high60_state; drawdown20_state; drawdown60_state; pos60/250; bias20_atr; dist_high20_atr','Core price/ATR','POSITION_STATE_V1','04','分母0/历史不足UNKNOWN；pos250独立')
field('ma_structure_state','Core MA','MA_STRUCTURE_V1','04','UNKNOWN')
field('relative_market_state; RPS5/20; delta1/3; rel_market_1/3/5','historical Universe/market','RELATIVE_STATE_V1 + CORE_FACTOR_V1','03/04','non-PIT只diagnostic')
field('compression_state','range/ATR/vol/liquidity','COMPRESSION_STATE_V1','04','UNKNOWN')
field('amount_state; volume_state; core_participation_result','TDX amount/volume/OHLC','AMOUNT_VOLUME_STATE_V1','04','UNKNOWN')
field('core_extension_risk; core_price_damage','Pure-Core price/amount','EXTENSION_RISK_V1 + CORE_FACTOR_V1','03/04','UNKNOWN')
field('trading_status; limit_status; resumed_event; lifecycle_status','local identity/calendar/制度表','TRADING_STATUS_V1 / PRICE_LIMIT_RULE_V1','02','UNKNOWN；补充不得覆盖')
field('turnover_state; turnover_ratio20; turnover_pct20/60; turnover_ma5; turnover_delta3; supplemental_participation_context; supplemental_extension_note','BaoStock strict binding','TURNOVER_CONTEXT_V1','06','PENDING/UNAVAILABLE/UNKNOWN_DATA')
field('base_seed_state; matched_seed_paths; seed_participation_annotation','Core','BASE_SEED_V1','07','Kleene三值')
field('sector_emergence; sector_rs5/20; rank_velocity; dq5; breadth_delta; ma20_width; seed_width; retention; entered/exited; top1/top3_concentration; sector_participation_proxy','PIT common member/Core Seed','SECTOR_FACTORS_V1 / SEED_WIDTH_V1 / SECTOR_AXES_V1','08','覆盖低UNKNOWN，0分母NA')
field('amount_a_value; amount_a_quality; amount_a_contract_id','独立Amount A审计','AUD-AMOUNT-A-06','08','OPEN只diagnostic，禁止正式consumer')
field('rotation_core_state; sector_price_retention_core; rotation_episode_id; rotation_structure_enrichment','B0/历史/固定篮子；structure仅D3','ROTATION_CORE_V1','08/13','UNKNOWN保留last_known')
field('primary_industry; supporting_concepts; algorithmic_support_sector; relative_sector_state; sector_context_state; sector_context_quality','PIT membership/完整LOO','LOO_CONTEXT_V1','13','无合格NA，数据不足UNKNOWN')
field('stock_prewatch; raw_qualification; final_eligibility','A/C/D2','STOCK_PREWATCH_V1 / RESEARCH_STATE_V1','09/10','UNKNOWN不计eligible')
field('maturity_stage; health_state; validity_state; tracking_state; scenario; state_freshness; expiry; reentry','raw资格/D0/D1/冻结前態','RESEARCH_STATE_V1','10','STALE/UNKNOWN不制造退出')
field('confirmation_event_type; primary_scenario; matched_scenarios; source_model_boundary','Legacy manifest/D2 diff','LEGACY_ADAPTER_V1 / STATE_EVENT_V1','11','FIRST_OBSERVED或NA')
field('active_anchor_id; anchor_view_asof_t; basic_breakout_state; basic_pullback_state; basic_recovery_state; structure_health; structure_events','frozen Anchor/price detector','STRUCTURE_EVENT_V1','12','NOT_IMPLEMENTED/NA/UNKNOWN分开')
field('support_state; acceptance_state; impulse_retention_1/3; retest_count','D1路径','SUPPORT_STATE_V1 / RETENTION_V1','12','PENDING/UNKNOWN/NA分开')
field('market_regime_axes; stress_level; stress_change; regime_ui','Core market/制度coverage','MARKET_REGIME_V1','03/04','UNKNOWN及last_known')
field('waiting_for; invalid_if; why_now; conflict_panel; hypothesis_set','frozen AST/事件/证据模板','NEAR_MISS_V1 / STATE_EVENT_V1 / HYPOTHESIS_V1','15','UNRESOLVED/INCOMPLETE，不强造文本')
field('eligibility_rank; priority_bucket; priority_rank; display_rank; overlap_cluster_id; also_in_sectors','完整eligible + event filter','PRIORITY_V1 / DISPLAY_V1','15','unknown排序末尾，cap不改资格')
field('daily_eligibility_ledger; statistical_signal_event; enrollment_id; controls; forward_outcome; benchmark; MFE; MAE; MDD','frozen T0/未来事实隔离结算','COHORT_V1 / CONTROL_ASSIGNMENT_V1 / FORWARD_PRICE_PATH_V1 / MARKET_BENCHMARK_V1','15','按到期/缺失/停牌/退市分开')
field('focus_activation; Focus timeline/path/outcome','accepted Core/原Focus契约','现有Focus版本清单 + migration manifest','19','Shadow不写production')
field('profile component statuses; quality; source_asof; context token; diagnostic counters','冻结manifest/组件能力','PUBLICATION_V1 / QUALITY_V1','00C/04/15','unknown和NOT_IMPLEMENTED分开')
registry='| 字段/字段族 | 权威输入 | Algorithm Contract | 阶段 | 缺失/降级 |\n|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join((a,b,c,' / '.join('V4-'+x for x in d.split('/')),e))+' |' for a,b,c,d,e in fields)
sec('# 87A. Field','# 88. 外部','''# 87A. Field → Algorithm Contract Registry

以下字段族是规范登记；实现前展开为逐字段schema，包含data type、unit、producer、required/optional、time、output digest和显示标签。不得由页面发明未注册资格字段。算法contract+参数实例唯一；表中多个contract代表派生链，不代表任选。

'''+registry+'''

只读投影允许同义UI标签，但API枚举/字段不得另起一套；旧relative_state→relative_market_state、extension_risk→core_extension_risk、rotation_state→rotation_core_state为显式schema迁移映射，旧publication原样保留。
''','重建字段登记、补漏字段、正确阶段号')
sec('# 附录 B：','# 历史附录 C：','''# 附录 B：任务卡索引

阶段与依赖只引用§78，不再复制第二套阶段表。任务卡必须带stage_id、contract ids/digests、input commit、source/capability scope、allowed/forbidden files、migration、required tests、独立证据、rollback、acceptance result和next_stage。
''','移除旧版附录阶段表')
sec('# 附录 G：','# 最终合同签署状态','''# 附录 G：codex修改版变更追踪

本版在原件副本直接替换冲突章节，保留产品目标与未冲突说明；详细逐章变更、审计项映射、原件/输出SHA256和自检结果见同目录《codex修改版_修改说明》。DOCUMENT_REVISED不代表IMPLEMENTATION_PASS，也不关闭Amount A/Focus真实Forward等独立审计。
''','取消自动关闭声明')
doc=doc[:doc.index('# 最终合同签署状态')]+'''# 本次修订签署状态

DOCUMENT = DA-MSR-V4.2.2-CODEX-REV1
STATUS = DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK
IMPLEMENTATION / REAL_DATA / FORWARD = NOT_VERIFIED_BY_THIS_DOCUMENT_EDIT
TDX = READ_ONLY_INPUT
BAOSTOCK = SUPPLEMENTAL_ONLY
STAGES = SECTION_78_ONLY
SETTLEMENT = V4-15_BEFORE_SHADOW
INHERITED_AUDITS = OPEN_UNTIL_INDEPENDENT_EVIDENCE

**文档结束**
'''
# Additional issues discovered outside the two audit tables.
sec('## 3C.3 未完成周期','## 3C.4 周/月','''## 3C.3 周/月 AS-OF

contract_id=PERIOD_ASOF_V1。使用冻结exchange calendar确定周期最后市场交易日，不用自然周五/月末猜测。CLOSED_ONLY只纳入period_last_session<=T0且当期所需日线/确认停牌证据完整、source在cutoff可见的周期；T0恰为周期最后交易日且数据已接受时可纳入，不能无端滞后一周期。
AS_OF_PARTIAL由period首会话至T0实际bar聚合，保存max_source_trade_date、period_view、asof_trade_date和IN_PROGRESS/CLOSED。所有必需日线价格先换到同一观察坐标再聚合，amount/volume保持原始单位，不调整成交量后混加。
整周期停牌没有actual OHLC则UNKNOWN/NO_ACTUAL_BAR，不制造零K线；部分停牌可按actual bar聚合但保存calendar_count/actual_count/suspended_count，未知缺口则该bar PARTIAL且不进正式closed trend。
同一因子必须声明固定period_view，不能按结果好坏挑选。趋势V1只用CLOSED_ONLY，图表可以并列partial。历史删掉T0之后日线/公司行为与知识时间晚到行，T0输出应不变。
''','周期结束边界、停牌与调整坐标')
rep('至少 250 个有效 session turnover history','优选 250 个此前有效 session turnover history；最低运行窗口按 §9.4')
rep('否则先完成 250 session，再后台补齐更早范围。','否则先完成 §9.4 的最低60个此前有效样本，再后台扩展；不阻断Core。')
rep('fallback = realized_volatility normalized distance','fallback = NONE；ATR不足时该归一化字段UNKNOWN（CORE_FACTOR_V1）')
rep('minimum_liquidity = TRUE','minimum_liquidity = TRUE') if 'minimum_liquidity = TRUE' in doc else None
rep('turnover ratio\nturnover percentile','turnover ratio（supplemental-only）\nturnover percentile（supplemental-only）')
rep('同一个股票：','同一个股票（未正式退出、无模型边界时）：')
rep('PREWATCH\n→ WARM\n→ CONFIRMED\n→ WEAKENING','maturity: PREWATCH → CONFIRMED（有独立股票WARM合同后才有WARM）\nhealth: STABLE → WEAKENING')
rep('一个 `security_id` 当日只能有一个 canonical result row。','每个 (publication_id,security_id) 只能有一个 canonical result row；同日不同revision分别保留。')
rep('第一版 primary scenario 沿用当前 V3.3 已存在的确定性场景优先级','第一版 primary scenario 使用 §34 extraction manifest 冻结的V3.3场景优先级')
rep('CONFIRMED → WEAKENING','maturity=CONFIRMED，health→WEAKENING') if 'CONFIRMED → WEAKENING' in doc else None
rep('STRESS = DECLINING','stress_change = DECLINING') if 'STRESS = DECLINING' in doc else None
rep('当日 TDX 未更新 | 不发布新 accepted trading day','当日 TDX 必需覆盖未通过 | 不发布该scope的新 accepted trading day')
rep('UNBOUND | 数据质量告警','UNAVAILABLE / BINDING_MISMATCH | 数据质量告警')
rep('今日确认候选','今日新确认 / 确认变化')

# Strengthen source/governance sections without changing external systems.
pos=doc.index('# 4. Source / Publication')
doc=doc[:pos]+'''# 3F. Source 接受与交易制度边界

source package、local snapshot、parser版本共同确定输入身份；相同zip hash但parser版本变化必须新parse artifact，不能因hash相同直接跳过重算。source manifest要绑定目标trade_date和冻结来源cutoff，较新包可用于重建历史但不能伪称过去实际观察。
TDX官网页面只证明提供日线包，不证明历史退市全集/公司行为全集。历史身份不能从文件第一/最后bar推断上市/退市日；板块/PIT成员未知按scope降级。TDX本地在用户更新时可能变化，读取前后size/mtime/hash核验，不稳定重试有界次数或SOURCE_MUTATING，正式分析只读项目快照。
ZIP处理拒绝绝对路径、..逃逸、符号链接/reparse point逃逸、异常压缩比/总解压大小；临时和最终路径必须都在项目目录，fsync/close后原子promote。URL只能来自获准public source contract及允许重定向host，不把官网“覆盖vipdoc”的客户端说明当本项目写权限。
有界请求的timeout/最大bytes/重试/并发/每日预算在V4-00D/F能力回执中冻结；已有实测可复用，缺失预算拒绝该网络作业，不运行无界探测。上游429按Retry-After/退避，不无限重试。

PRICE_LIMIT_RULE_V1必须基于目标日期官方制度版本表及本地可验证身份，保存board/security_type/ST/listing_phase、规则生效区间、参考价来源、tick、rounding、无涨跌幅限制例外。previous_close字段区分上次成交收盘与交易所当日涨跌幅参考价，除权等日期不能直接把昨日raw close代入。无权威参考价/规则则limit_status UNKNOWN；不是用BaoStock补作Core authority。制度表的当前或历史事实不能由本方案臆造，V4-02提交官方来源与独立样本后才启用对应规则，其他Pure-Core能力依赖scope运行。

---

'''+doc[pos:]
changes.append(('3F Source / Price Limit','补充源并发快照、zip隔离、解析身份、有界请求和涨跌幅参考价证据',0,0))
pos=doc.index('# 42. Focus Tracker')
doc=doc[:pos]+'''# 41G. 解释、展示和独立证据

HYPOTHESIS_V1：模板必须绑定可验证predicate_id、支持/反对/UNKNOWN证据及下一判别/过期AST。证据不足不强造第二个解释，标HYPOTHESIS_SET_INCOMPLETE。价格衍生的多个Domain不是统计独立观测；不能按Domain数或解释数量累加“把握”。Supplemental解释包含自身revision，不混入Core why_now。

DISPLAY_V1：先从完整qualified ledger生成全部事件，事件改变检测以冻结前態为准。首页只展示非PERSISTENT有实质事件的对象；市场卡与数据等待说明不受“仅变化对象”限制。先按风险失效、确认/升级、新PREWATCH、其他变化排序，再各自PRIORITY_V1 tuple、stable entity_id。跨行业/概念合并板块池，最多15；独立股票最多30，允许0，正常5–10/10–20只是预期负荷而非下限。
股票全首页去重，已在板块卡展示者独立列表不重复计入负荷；板块卡最多5个变化成员，详情完整分页。风险退出即使final_eligibility=FALSE仍进入RISK_CHANGE事件流，不能被eligible-only排序删除。eligible_count、changed_count、displayed_count分别显示。
sector_overlap_jaccard=|M_a∩M_b|/|M_a∪M_b|，空并集NA；J>=0.8建立边，按稳定id连通分量生成展示cluster_id，明确传递聚类不保证所有两两J>=0.8。聚类仅去重展示，不合并计算资格；各板块统计仍独立。

---

'''+doc[pos:]
changes.append(('41G 解释与展示','补充证据不独立、风险退出展示、去重及Jaccard聚类',0,0))
# Update frozen context and database receipt details.
rep('所有响应：','所有V4研究响应携带§4.9完整context token和以下来源信息：')
rep('revision\ndata_as_of\nturnover_as_of','core_revision\nmodel_namespace\noptional_enrichment_revision\ndata_as_of\nturnover_as_of')
rep('如果股票没有进入 PREWATCH：','如果股票未进入 PREWATCH，先区分NOT_ELIGIBLE、UNKNOWN、NOT_IMPLEMENTED和NOT_IN_RESEARCH_UNIVERSE；下面只说明已完成评估且为FALSE的示例：')
rep('即使不在任何候选池，也必须有 Daily Profile。','Research Universe中即使不在候选池也必须有Daily Profile；搜索池外证券仍显示身份/排除理由和可用Raw事实，不伪称全套研究算法已评估。')
rep('股票 vs 主板块','股票 vs T0冻结研究板块（收益基准）/ 当前LOO支持板块（当日解释），两者分开')
rep('Source Identity','Source Identity') if 'Source Identity' in doc else None

# Normalize current version prose while retaining historical appendices verbatim.
cut=doc.index('# 历史附录 D：')
main,hist=doc[:cut],doc[cut:]
main=re.sub(r'V4\.2\.1|V4\.1', '本版',main)
main=main.replace('本版本版','本版')
main=main.replace('V4-00/V4-03 必须证明','V4-00A盘点，V4-14集成时必须证明')
main=main.replace('→ V4-21','→ V4-21')
main=main.replace('PIT_OBSERVED_FORWARD','PIT_OBSERVED')
main=main.replace('relative_state','relative_market_state').replace('relative_market_market_state','relative_market_state')
main=main.replace('extension_risk','core_extension_risk').replace('core_core_extension_risk','core_extension_risk')
main=main.replace('rotation_state','rotation_core_state').replace('rotation_core_core_state','rotation_core_state')
doc=main+hist
doc=doc.replace('V4.1 中与这些规则冲突的描述，以 V4.2 为准。','本历史附录不构成当前规范；当前合同仅按本修改版正文。')
# Historical only facts are labeled, with no duplicate end markers.
doc=doc.replace('**文档结束**','').rstrip()+'\n\n**文档结束**\n'
doc=re.sub(r'\n{4,}','\n\n\n',doc)

# Working draft only; final publication follows checks below.
(BASE/'draft.md').write_text(doc,encoding='utf-8')
(BASE/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'draft_lines':len(doc.splitlines()),'source_lines':len(original.splitlines()),'section_edits':len(changes)},ensure_ascii=False))
# Second pass over the assembled full document, not just audited sections.
rep('# 0. V4.2 为什么必须在 本版 之上继续升级','# 0. 升级背景与产品问题')
rep('mandatory universe/membership facts','mandatory universe facts；membership只对sector/context能力必需，stock Core不以membership缺失全局阻断')
rep('amount_a\namount_delta3','amount_a_value / amount_a_quality（独立审计diagnostic）\nsector_participation_proxy / proxy_delta3')
rep('在V4-11生成精确AST与黄金向量','按首次消费者阶段（sector V4-08、stock confirmation V4-11）生成精确AST与黄金向量')
rep('完整DAG、发布一致性、source degradation','完整DAG、发布一致性、source degradation')
rep('REP','REP') if False else None
sec('# 11. Passive Resilience','# 12. Evidence','''# 11. Passive Resilience 与 Active Emergence

ACTIVE_EMERGENCE、PASSIVE_RESILIENCE唯一算法为§10E；本节解释其含义，不另设第二套资格规则。相对市场上涨不等于个股上涨；低Beta防御和主动改善不能仅凭单日跌得少区分。系统同时列ret1/relative_market/delta3/结构事实，不能用模板推断资金意图。
rel_market_vol_adj=rel_market_1/vol20，vol20<=0/未知为UNKNOWN，作为诊断而非单独硬资格。Beta residual与全面中性化不进入V1。价格衍生证据相关性必须披露，不重复算独立支持。
''','删除Passive/Active重复定义及零波动风险')
sec('# 25. Staleness','# 26. Event Priority','''# 25. Staleness

保存prewatch_age_sessions、last_positive_change_date、days_since_emergence_improvement、waiting_condition_progress，市场日龄与可评估会话龄分开。PRIORITY_V1排序在同等emergence/structure等键后把staleness较低者前置，不另行暗改资格或桶。到期只按§32，原始T0结果永不删除。
''','明确staleness排序而非未定义衰减分')
sec('## 59.2 停牌','## 59.3 ST','''## 59.2 停牌

确认停牌不填ret=0/turnover=0，不当数据缺失；Core连续市场会话窗口遇停牌按CORE_FACTOR_V1返回不足，不跳过日期；Turnover自身历史按TURNOVER_CONTEXT_V1允许跳过确认停牌；Forward按FORWARD_PRICE_PATH_V1固定市场horizon。三者明确分开，不能共享一个无语义的rolling工具。
''','停牌与窗口口径统一')
sec('# 60. Research Radar 排名','# 61. Display','''# 60. Research Radar 排名

contract_id=PRIORITY_V1。完整eligible集合按STOCK_PREWATCH/STOCK_CONFIRMED/SECTOR_PREWATCH/SECTOR_WARM/SECTOR_CONFIRMED分别rank；RISK_CHANGE与NEAR_MISS独立，不要求当前eligible。
Stock键：bucket(A到D)、emergence(HIGH到LOW)、structure(HIGH到LOW)、delta3降序、risk(LOW到EXTREME)、days_since_improvement升序、prior20_amount降序、stable_id升序。Sector键：emergence、rank_velocity3降序、breadth_delta3降序、ma20_delta3降序、adjusted_seed_width降序、exhaustion升序、stable_id升序。每个键missing排该层末位且显示UNKNOWN，不改变已成立资格。
eligibility_rank即完整资格集合内此序，priority_rank同义alias不另算分；display_rank按DISPLAY_V1事件过滤/cap计算。turnover、未关闭Amount A、未来outcome与manual pin均不进这些正式键。
''','唯一排序键、风险事件与unknown处理')
rep('PARTICIPATION context\npriority\nrisk flag\nhypothesis discriminator','PARTICIPATION supplemental context\ndiagnostic-only priority view\ndiagnostic risk note\nhypothesis discriminator') if 'PARTICIPATION context\npriority\nrisk flag\nhypothesis discriminator' in doc else None
rep('min dwell','exit hysteresis连续计数（无强制升级等待）')
rep('sector_breadth_ex_target','sector_breadth_ex_target') if False else None

# Precise common facts and identity rules needed by downstream consumers.
pos=doc.index('# 8. Data Quality')
doc=doc[:pos]+'''## 7.13 公共字段和实体完整性

PUBLICATION_V1：每个revision有不同opaque publication_id；UNIQUE(namespace,trade_date,core_revision)，trade_date复合FK防串日；parent/predecessor引用都按id冻结。currency=CNY、price/amount/volume单位分别存source contract，OHLC有限且positive，low<=open/close<=high，volume/amount非负；违例不静默修正。
QUALITY_V1：value、quality、reason、source_digest分开，不把UNKNOWN字符串存入数值列。事实族保留raw字段；派生字段保存contract/parameter/input digest。只有最终visibility由accepted head决定，事务失败的staging不被读API/统计消费。
security_id不是单纯symbol：带exchange与lifecycle identity，改名不改实体，代码复用另建实体；日期有效identity不足则UNKNOWN。Core actual_bar=(trading_status=ACTUAL_TRADED且OHLC/身份/日期通过)。
sector_seed_aggregates等B产物单独schema，不放进F0 native表假装已有；structure_health按关联事件优先级BROKEN→DAMAGED、HELD_CONFIRMED→STABLE、RECLAIMED→IMPROVING、其余有效→STABLE、缺数据→UNKNOWN，未交付组件NOT_IMPLEMENTED。

---

'''+doc[pos:]
changes.append(('7.13 公共身份与字段','publication revision唯一性、数值/质量分离、证券代码复用、structure_health',0,0))

# Explicit calendar, comparison window and affine math, without inventing source corporate actions.
pos=doc.index('### 复权失败降级')
doc=doc[:pos]+'''### 调整数学与历史截断

已验证同一artifact的affine系数A[j],B[j]满足Q[j]=A[j]*raw[j]+B[j]。以观察日t为坐标时P[j|t]=(A[j]*raw[j]+B[j]-B[t])/A[t]，A[t]>0；多artifact系数不可混算。差值/ATR只乘正尺度，不加beta；价格水平变换才加beta，收益必须在统一坐标重新算而非直接“转换百分比”。Anchor先确定其原始基准，再用对应线性坐标映射，不把系数用于不匹配的raw基准。
公司行为仅使用effective<=t且在所选消费manifest内可见的事件；即使full-series系数能消去未来行动，也必须单独证明重锚等价、来源可见性及没有后来更正泄漏。现金分红的加法项使简单“价格比总会消因子”不成立。
独立预期值来自可核验本地源样本/数学向量，不仅比较digest。真实事件源缺证据仍按下面scope降级，不能用在线adjustment补作Core。

'''+doc[pos:]
changes.append(('3B.6 调整数学','明确affine重锚、ATR差值转换、禁止混用基准',0,0))
pos=doc.index('# 52A. 切换政策')
doc=doc[:pos]+'''## 51A.1 观察起点与防事后重跑选样

V4-00C冻结每日scheduled cutoff和观察发布deadline（Asia/Shanghai且存UTC时间），daily_observation_slot=(model_contract_id,state_lineage_id,trade_date)。只有该slot的第一次合规accepted可创建真实enrollment；deadline之后补跑或更换参数属于reconstruction，不允许择优标PIT_OBSERVED。延期/源不可得则记录MISSED_OBSERVATION_SLOT，不悄悄重置日期。已有实时结果的同日修订仍存observations，但不能新增第二套原始样本。
source/provider_available、system_available、computed_at、accepted_at、observation_deadline分别记录；“同一trade_date”不等于“当时已知”。切换门使用完整slot日志、P0日志和model identity，禁止只挑通过的20天。

'''+doc[pos:]
changes.append(('51A.1 观察时点','增加固定观察slot/deadline，阻止盘后择优重跑制造Forward',0,0))

# Clarify algorithms referring to cross-sectional or historical membership sets.
rep('按同日eligible板块midrank','按同日source/type/member/coverage合格的全体板块（非算法已入选集合）midrank')
rep('在起点t-N已符合Universe且N+1窗口完整的股票等权endpoint return均值','在起点t-N已符合Universe、按各因子窗口可评估股票的等权endpoint return均值')
rep('strong_member_retention_1>=0.5','strong_member_retention_1>=0.5')
rep('强度5/20/60','强度5/20/60') if False else None
rep('固定PREWATCH[t-1]','固定PREWATCH[t-1]') if False else None

# Write draft again after full-pass corrections.
(BASE/'draft.md').write_text(doc,encoding='utf-8')
(BASE/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'final_draft_lines':len(doc.splitlines()),'edits':len(changes)},ensure_ascii=False))
sec('# 3. V4.2 唯一主链','# 3A. V4.2 数据源权威矩阵','''# 3. V4.2 唯一主链

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

''','删除旧图中turnover进入Core单链的歧义，统一拓扑与独立结算')
rep('本日确认且该episode曾确认、上一可见状态已弱化/退出','本日确认且该episode或其明确关联的parent_episode曾确认、上一可见状态已弱化/退出')
pos=doc.index('# 25. Staleness')
doc=doc[:pos]+'排序枚举显式序：risk LOW<MEDIUM<HIGH<EXTREME；emergence/structure LOW<MEDIUM<HIGH；bucket A<B<C<D。排序方向按§60，不按字符串字典序。UNKNOWN单列末位，不等于最低风险。\n\n'+doc[pos:]
(BASE/'draft.md').write_text(doc,encoding='utf-8')
(BASE/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')

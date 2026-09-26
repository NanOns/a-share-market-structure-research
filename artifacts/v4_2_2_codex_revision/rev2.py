from pathlib import Path
import re, os, hashlib, json, difflib
P=Path('D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md')
L=P.with_name(P.stem+'_REV2修改说明.md')
B=Path(__file__).parent/'rev2'
B.mkdir(exist_ok=True)
raw=P.read_bytes(); s=raw.decode('utf8'); old=s; edits=[]
def replace(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b)
def section(a,b,new,issue):
 global s
 i=s.index(a); j=s.index(b,i+len(a)); s=s[:i]+new.strip()+'\n\n'+s[j:]; edits.append((issue,a))
replace('DA-MSR-V4.2.2-CODEX-REV1','DA-MSR-V4.2.2-CODEX-REV2')
replace('V4.2 相比 本版 不是“小版本补丁”，而是把系统从：','当前 REV2 合同延续 V4.2.2 的升级目标，把系统从：')
replace('sector_relative_market_state','relative_sector_state')
replace('§10B–10I全部Core字段，不依赖高级Anchor/Sector Context/BaoStock','§10B–10G + §10I 的Pure-Core字段；明确排除§10H Turnover，不依赖BaoStock/Sector Context/Advanced Structure')
replace('Turnover历史/绑定/补充组件；与Core后继无硬依赖','§10H TURNOVER_CONTEXT_V1、stock_profile_enrichments、supplemental_participation_context；与Core后继无硬依赖')
replace('可修订事实保存 effective_from/to、provider_available_at（可未知）、observed_at、ingested_at、source_revision_id、supersedes_revision_id、source_identity。','统一元结构 REVISIONABLE_FACT_META_V1 包含 effective_from、effective_to、provider_available_at（可未知）、observed_at、ingested_at、system_available_at、source_revision_id、supersedes_revision_id、source_identity。security_lifecycle_history、sector_membership_observations、security identity revisions、ST/board/security_type historical identity 明确 EMBEDS REVISIONABLE_FACT_META_V1；schema展开全部字段，不允许仅注释继承。')
start=s.index('## 7.10 `security_lifecycle_history`'); end=s.index('## 7.11',start)
block=s[start:end].replace('source_contract_id\n```','source_contract_id\nprovider_available_at\nobserved_at\ningested_at\nsystem_available_at\nsource_revision_id\nsupersedes_revision_id\nsource_identity\n```\n\nEMBEDS REVISIONABLE_FACT_META_V1（§6A）；主键为稳定fact_key加source_revision_id，fact_key必须区分实体、事实属性及有效区间，修订不得覆盖旧行。system_available_at=max(observed_at,ingested_at)，source_identity与publication_consumed_sources逐revision关联。\n\n验收：T+10录入effective_from=T-30的lifecycle correction，AS_RECORDED(T)及其historical_evaluable_universe digest不变；RECONSTRUCTED_CORRECTED(T)可在独立lineage变化，保存不同Universe digest和更正来源。')
s=s[:start]+block+s[end:]
section('# 49A. Benchmark Contract','# 49B.', '''# 49A. 市场参考与Forward基准分离

## 49A.1 MARKET_RELATIVE_REFERENCE_V1

Core历史市场参考retN：在起点t-N已符合Universe、按CROSS_SECTION_SESSION_WINDOW_V1可评估股票的等权endpoint return均值，保存起点Universe/可观察集合/coverage；沿用缺失超过20% UNKNOWN的工程候选门，不能只凭现在存活证券补池。市场趋势路径为连续ret1链乘，标daily-rebalanced research index。它只服务rel_market、市场趋势、Market Regime及Core历史比较；RPS自身仍是§10A0横截面retN排名，不以市场参考收益参与排名公式。

identity包含contract_id、parameter_set_id、historical Universe、会话窗口及实际消费source digest。不得用Forward的T0固定篮子替换本字段，也不把N日endpoint均值误称为日再平衡路径的N日累计收益。

## 49A.2 FORWARD_MARKET_BENCHMARK_V1

仅服务Forward relative_market_return、T+N基准路径和control outcome comparison。T0冻结可评估Research Universe、等权初始资金权重w_i（sum=1）与固定持有份额；B_j=sum(w_i*P_i,j/P_i,0)，价格均按同一evaluation basis转换，R_B=B_N-1。不因后来强弱、停牌、退市删成员或再归一化剩余权重。

identity包含独立contract_id、T0成员/初始权重、adjustment identity、benchmark_constituent_policy及参数digest；禁止与MARKET_RELATIVE_REFERENCE_V1共用identity。Core消费者不得读取未来evaluation source。

benchmark_constituent_policy=FORWARD_CONSTITUENT_POLICY_V1：每成员/会话互斥记录ACTUAL_ENDPOINT、CONFIRMED_SUSPENSION、DATA_MISSING、DELISTED、IDENTITY_UNKNOWN或ADJUSTMENT_UNKNOWN及证据；多问题保留reason集合，主状态按IDENTITY_UNKNOWN→ADJUSTMENT_UNKNOWN→DELISTED→CONFIRMED_SUSPENSION→DATA_MISSING→ACTUAL_ENDPOINT优先，避免重复计权。退市有可核验终值另存terminal-value状态，不擅自归零。

字段必须包含benchmark_endpoint_coverage（实际或已核验终值的原始权重和）、benchmark_missing_weight（其补集）、benchmark_suspended_weight、benchmark_delisted_weight、benchmark_unknown_weight、benchmark_quality、benchmark_valuation_coverage、benchmark_marked_weight。主状态权重互斥；missing_weight包含全部无实际终值成员，不能再与其子项相加。unknown_weight为DATA_MISSING/IDENTITY_UNKNOWN/ADJUSTMENT_UNKNOWN权重和。

确认停牌可用最近已验证实际收盘在当前evaluation basis下的等价价格作MARKED_SUSPENSION估值，保持原权重、记录quote_age和价格日期；这不是实际可成交终值，不填ret=0。公司行为换基不可验证时不能carry。DATA_MISSING/身份或复权未知/无终值退市不自动carry、不填0、不删除。

全篮子实际终值齐全时benchmark_quality=OBSERVED；只有已核验的停牌估值补齐且满足事前覆盖门时为MARKED_ESTIMATE，单独输出relative_market_return_marked，禁止混入OBSERVED主统计。剩余不可估值时保留observed_contribution=sum_known(w_i*P_i,j/P_i,0)、各缺失权重和PARTIAL_UNVALUED；该贡献不是完整收益，完整relative_market_return不可用，但不阻断absolute_return、controls绝对路径及已具备证据的其他capability。各日path质量独立，endpoint通过不代表MDD全路径通过。

minimum_endpoint_weight_coverage、maximum_suspension_quote_age及质量到消费者权限矩阵在V4-00G注册ENGINEERING_CANDIDATE，V4-00H以停牌、退市、真实缺口、公司行为样本验收后冻结；REV2不擅定95%/98%/99%。门未冻结只阻断对应估值基准消费者，不阻断独立Core/absolute结算。覆盖达标不能使不可估值价格凭空有效，也不能把MARKED_ESTIMATE改为OBSERVED。

必测5000成员中4999有终值、1确认停牌：若停牌价格可换基且冻结覆盖/quote-age门通过，应有MARKED_ESTIMATE及marked相对结果，不能因单个无实际终值无条件使全能力失效；若换基失败则只限制受影响结果并披露原因。另测终值退市、未知身份、实际缺口、不可换基及所有成员齐全，证明原权重未变。

## 49A.3 板块及Rotation篮子

FORWARD_SECTOR_BENCHMARK_V1沿用§49A.2明确的固定权重、估值和质量规则，但使用独立sector/member identity；T0按§20确定sector并冻结篮子。股票relative_sector排除目标，n<2不提供；SECTOR信号使用自身篮子。relative_market_return=stock_R−market_R_B，relative_sector_return同理；估值版本单独后缀_marked。股票和板块outcome分开统计。

日线不能知道成员盘中极值是否同步，板块仅提供MFE_CLOSE/MAE_CLOSE，不把成员high求和冒充盘中高点。Rotation的pulse篮子采用ROTATION_PULSE_BASKET_V1，复用固定篮子的数学及身份校验，仅消费当日cutoff可见数据，绝不调用未来Forward结果；其篮子为Pulse日前已知成员，按Pulse前一会话同基准价格建立初始等权资金权重。缺失、估值结果作为质量输入，正式retention仅用其冻结允许质量。

''','C02')
replace('FORWARD_PRICE_PATH_V1 / MARKET_BENCHMARK_V1','FORWARD_PRICE_PATH_V1 / FORWARD_MARKET_BENCHMARK_V1 / FORWARD_SECTOR_BENCHMARK_V1')
replace('RELATIVE_STATE_V1 + CORE_FACTOR_V1','RELATIVE_STATE_V1 + CORE_FACTOR_V1 + MARKET_RELATIVE_REFERENCE_V1')
replace('候选规则：pulse=(dq5>=10 AND breadth_delta1>=0.05)；retained=(冻结篮子累计收益>0 AND strong_member_retention_1>=0.5)；failed=', '''候选规则：pulse=(dq5>=10 AND breadth_delta1>=0.05)。EARLY_RETENTION与MATURE_RETENTION独立：

- Pulse日冻结base_seed_set=A[pulse]合格成员、breadth_positive_set（当日ret1>0的篮子成员）及篮子identity。base_seed_retention=冻结seed集合中今日仍满足A资格的数量/冻结seed数；breadth_retention=冻结positive集合中今日同基准收盘>=Pulse日收盘的数量/冻结positive数。分母为0返回NOT_APPLICABLE，非空集合存在未知资格/价格则对应比率UNKNOWN，不删除未知成员或重算分母；中途退板仍跟踪冻结集合。
- early_retained=(frozen_basket_cumulative_return>0) AND (base_seed_retention>=early_seed_retention_min OR breadth_retention>=early_breadth_retention_min) AND breadth_delta1>=early_breadth_delta_min AND top1_concentration<=early_top1_concentration_max。NOT_APPLICABLE的OR路径作为不可用分支，另一分支TRUE可成立；两分支均不可用则UNKNOWN。真正UNKNOWN按§10A0三值逻辑。strong_prev为0不影响early分支。
- mature_retained=early_retained AND strong_member_retention_1>=mature_strong_retention_min；strong_prev=0时mature_retained为NOT_APPLICABLE，不阻断IN/ACCEPTED，不能据此进入EXPANDING/REACCELERATING。strong retention仅作为成熟WARM/CONFIRMED的解释，不修改其Legacy资格。
- 上述阈值在§72注册ENGINEERING_CANDIDATE，V4-00G定义参数、对应V4-08阶段冻结后才正式消费；不沿用未裁决的0.5作为early门。单龙头集中且无breadth扩散时不能通过early的联合门。

failed=''')
replace('今日pulse且retained→','今日pulse且mature_retained→')
replace('已有至少2个后续会话且retained、','已有至少2个后续会话且mature_retained、')
replace('pulse后至少2会话且retained且','pulse后至少2会话且early_retained且')
replace('pulse后至少1会话且retained→','pulse后至少1会话且early_retained→')
replace('1. 必要输入未知→UNKNOWN，暂停该episode计数不伪造退出。','1. 当前候选分支的必要输入未知→UNKNOWN，暂停该episode计数不伪造退出；mature专用输入不全局传播到early分支，NOT_APPLICABLE成熟分支跳过，已知强留存不达标禁止成熟升级。')
replace('## 21A.4A 输入时点','必测R1：strong_prev=0但pulse后篮子正收益、Seed与breadth维持，允许IN/ACCEPTED；R2：老强势strong retention下降且breadth恶化，不允许EXPANDING/REACCELERATING；R3：单龙头高集中且无扩散，不允许ACCEPTED/EXPANDING。各例保存参数实例、分支真值及独立预期。\n\n## 21A.4A 输入时点')
replace('- MA_N=最近N市场会话收盘均值；本版要求连续实际bar，确认停牌也不填0/不跳日凑数，缺失为INSUFFICIENT_CONTIGUOUS_HISTORY。','- MA_N及MA/ATR/HHV/LLV/技术结构类窗口的口径为WINDOW_SEMANTICS_OPEN_DECISION，按下述三窗口合同在V4-00G裁决；不得继续把严格连续actual bar当已冻结规则。')
replace('严格连续窗口是保守工程基线，不代表停牌的经济收益为0。Forward另有路径规则。300市场日warm-up只是规划目标，各字段实际首个可用日独立报告。','''WINDOW_SEMANTICS_OPEN_DECISION：V4-00G冻结TECHNICAL_BAR_WINDOW_V1、CROSS_SECTION_SESSION_WINDOW_V1、FORWARD_SESSION_WINDOW_V1及field→window映射。

技术窗口比较Option A（最近N市场会话且实际bar完整）与Option B（最近N根已验证交易bar，仅跳过确认停牌）；Option B记录每字段start/end、calendar_span、actual_count、suspended_count，未知数据缺口不能假装停牌跳过。ATR的previous close、slope偏移、量额/波动窗口、prior high与周/月技术指标都必须逐字段声明索引与窗口类型，不能把t会话索引和k实际bar索引混用。上述技术公式中的切片在裁决前仅表示候选逻辑。

CROSS_SECTION_SESSION_WINDOW_V1用于RPS、retN、relative市场比较，按市场会话保持相同起止日期；endpoint停牌、区间停牌与vol连续收益各自质量处理在V4-00G显式冻结，不静默沿用技术跳日语义。FORWARD_SESSION_WINDOW_V1用于市场日T+N到期，保留§46A/47既定停牌和结算规则；不因技术窗口裁决改变horizon。

必测单日停牌、连续5日停牌、复牌、涨停低/无成交、非停牌数据缺失、新股不足窗口；对比Profile completeness、Trend continuity、RPS comparability、PREWATCH eligibility后记录选择、参数digest及反例。窗口未冻结仅允许对照诊断，不得验收依赖该窗口的正式因子/画像/Seed；基线盘点可继续。300市场日warm-up仍只是规划目标，各字段首个可用日独立报告。''')
replace('Core连续市场会话窗口遇停牌按CORE_FACTOR_V1返回不足，不跳过日期；','Core技术窗口为WINDOW_SEMANTICS_OPEN_DECISION，按§10A0在V4-00G比较并冻结技术bar/横截面session口径；')
section('# 52A. 切换政策 CUTOVER_V1','# 52B.', '''# 52A. 切换政策 CUTOVER_V2

切换按capability授予生产权限，不要求先证明长期优势。SHADOW_STABLE_PASS[capability]=同一model_contract_id连续20个市场会话按期accepted，0时序泄漏/duplicate episode corruption/Core identity/P0 state violation，rollback drill通过。漏日/不可评估会话不计连续；P0或该能力模型/参数变更重置其窗口，共享依赖变更影响所有消费者。

STOCK_PROVISIONAL_FORWARD_GATE：至少5个不同signal_date、30个不同股票正向入选逻辑事件（FIRST_PREWATCH/REENTRY_PREWATCH/NEW_CONFIRMED）的T5 OBSERVED，同模型、settlement无P0；同一逻辑事件的revision不重复计，INVALIDATION不凑数。controls/benchmark覆盖和质量分层回执必须披露，估值结果不能充当OBSERVED样本。

SECTOR_PROVISIONAL_FORWARD_GATE按子能力分别冻结：SECTOR_STAGE记录SECTOR_FIRST_PREWATCH、SECTOR_NEW_WARM、SECTOR_NEW_CONFIRMED；ROTATION记录ROTATION_PULSE、ROTATION_ACCEPTED、ROTATION_FAILED。逐事件类型保存unique_episode_count、unique_signal_dates、matured_events、T5价格路径质量及状态结果；同episode不同事件可以分别展示，不可相加冒充不同episode样本。FAILED必须完整纳入失败观察但不能补足正向接受样本门，PULSE不能代替ACCEPTED覆盖。

sector_min_unique_signal_dates、sector_min_unique_episodes、sector_min_matured_events_by_type、rotation_min_accepted_episodes及required_forward_quality在§72登记ENGINEERING_CANDIDATE，V4-00G定义、V4-00H冻结接受政策；REV2不临时拍定最低数值。没有冻结门或样本不足则该scope=SHADOW_ONLY。SECTOR_RISK_CHANGE单独验证事件完整性/风险提示正确性及相关sector路径样本，不能借股票30例自动取得生产资格。

production_permission[capability]=SHADOW_STABLE_PASS[capability] AND 对应FORWARD_GATE[capability] AND MIGRATION_REPLAY_PASS[capability] AND required_dependency_permissions。capability至少区分STOCK_CORE、STOCK_SECTOR_DEPENDENT、SECTOR_STAGE、ROTATION、SECTOR_RISK_CHANGE；共享源可读但未经接受的算法输出不能作为已生产能力的硬依赖。STOCK_CORE通过而Sector不足时，独立Stock路径可production，Sector/Rotation保持Shadow；依赖未通过Sector的Stock路径仍Shadow，不放宽原资格。

Cutover Receipt必含capability、status、shadow_sessions、unique_signal_dates、matured_events（按类型）、forward_quality、migration_gate、production_permission、dependency_scope、parameter_digest。UI按模块标production/shadow，Focus仅接受其source capability已许可的accepted publication，混合页面共享context身份但不混淆权限；禁止用GLOBAL V4 PASS整体切换。

必测stock gate PASS、sector insufficient：Stock独立路径permission=TRUE，Sector/Rotation=FALSE/SHADOW_ONLY，Sector依赖Stock路径不获得权限。反向情形也按依赖图判断。切换后证据标PROVISIONAL；无明确优势不等于严重退化，不自动阻断。严重退化仍按合同/数据失败、系统性状态异常或事前运行预算定义，不用后验收益挑阈值。

''','C06')
replace('§52A两门，样本不足延长观察；禁止以historical replay凑天数','§52A按capability的稳定门/Forward门，样本不足仅该scope延长观察；禁止historical replay凑天数')
replace('仅§52A三门通过后，accepted V4 source进入生产Focus','仅§52A对应capability三门及依赖通过后，该accepted V4 source进入生产Focus')
replace('默认V4，Legacy下沉diagnostic，明确PROVISIONAL','仅已获production_permission的模块默认V4；其余保持Legacy生产/明确Shadow，按scope标PROVISIONAL')
replace('AST/schema/参数实例、字段producer注册、纯函数Legacy提取规范','AST/schema/参数实例、字段producer注册、Legacy提取规范；冻结三类窗口语义，注册基准缺失策略、retention和分能力切换参数')
replace('能力scope、预算、失败回执、恢复演练；Phase 0最终回执','能力scope、预算、失败回执、恢复演练；验收基准缺失策略及覆盖门、冻结分能力切换政策；Phase 0最终回执')
replace('初始parameter_set_id=V422_CODEX_ENGINEERING_01','初始parameter_set_id=V422_CODEX_ENGINEERING_02（REV1实例保留，不覆盖）')
replace('# 73. 禁止实现硬编码与参数偷换','''REV2待冻结注册项：minimum_endpoint_weight_coverage、maximum_suspension_quote_age、benchmark quality→consumer permissions；early_seed_retention_min、early_breadth_retention_min、early_breadth_delta_min、early_top1_concentration_max、mature_strong_retention_min；三类窗口field映射；sector_min_unique_signal_dates、sector_min_unique_episodes、sector_min_matured_events_by_type、rotation_min_accepted_episodes、required_forward_quality。均有contract_scope、单位、状态和owner stage；未赋值不能取得正式消费者权限，按§49A/52A降级。窗口裁决结果亦进入parameter/model digest。

# 73. 禁止实现硬编码与参数偷换''')
replace('STAGES = SECTION_78_ONLY','STAGES = SECTION_78_ONLY\nWINDOW_DECISION = OPEN_TO_V4_00G\nCUTOVER = CAPABILITY_SCOPED')
replace('# 附录 G：codex修改版变更追踪','# 附录 G：codex修改版变更追踪\n\n当前生效版本为REV2，C01–C06及P2定点变更见同目录《codex修改版_REV2修改说明》。既有《修改说明》保留为REV1历史记录，其中输出SHA256仅对应REV1；不得将历史说明当作当前验收。')
replace('# 历史附录 D：V4.1 → V4.2 迁移说明','# 历史附录 D：V4.1 → V4.2 迁移说明\n\n以下历史附录仅留存版本背景；其中“必须/应该/下一阶段”等不是REV2当前实施指令。当前权威为REV2正文与§78。')

# Preserve exact pre-edit bytes and atomically update the user-requested existing document.
headings=re.findall(r'^#{1,6}\s+(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)(?=[.\s])',s,re.M)
refs=re.findall(r'§\s*(\d+[A-Z]?\d*(?:\.[\dA-Z]+)*)',s)
assert not set(refs)-set(headings)
assert len(headings)==len(set(headings))
fence=False
for line in s.splitlines():
 if line.startswith('```'):
  if fence: assert line.strip()=='```'
  fence=not fence
assert not fence
patterns=['§10B–10I全部Core字段','contract_id=MARKET_BENCHMARK_V1','retained=(冻结篮子累计收益>0 AND strong_member_retention_1>=0.5)','Core连续市场会话窗口遇停牌','sector_relative_market_state','V4.2 相比 本版','完整endpoints才正式OBSERVED','Focus/UI切换=上述两门']
assert all(x not in s for x in patterns)
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
backup=B/'REV1_before_REV2.md'; assert not backup.exists(); backup.write_bytes(raw)
diff=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='REV1',tofile='REV2'))
(B/'REV1_to_REV2.diff').write_text(diff,encoding='utf8')
def atomic(p,data):
 t=p.with_name('.'+p.name+'.rev2.tmp'); assert not t.exists()
 with t.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
 os.replace(t,p); assert p.read_bytes()==data
assert P.read_bytes()==raw
atomic(P,s.encode('utf8'))
rows=[('C01','YES','N/A','N/A','§78、§87A、Profile分层明确排除§10H'),('C02','YES（策略参数待阶段冻结）','NOT VERIFIED','NOT VERIFIED','§49A分离合同、固定权重及估值质量；无未解释剩余缺失的伪完整收益'),('C03','YES（阈值待阶段冻结）','NOT VERIFIED','NOT VERIFIED','§21A early/mature分支及R1–R3案例'),('C04','YES','NOT VERIFIED','N/A','§6A统一元结构、§7.10显式字段及晚到更正验收'),('C05','OPEN TO V4-00G','NOT VERIFIED','N/A','§10A0/59.2/72/78三类窗口及比较验收'),('C06','YES（子门参数待阶段冻结）','NOT VERIFIED','NOT VERIFIED','§52A/78生产权限按能力及依赖闭包')]
log=f'''# V4.2.2 CODEX-REV2 定点修改说明

日期：2026-09-25。依据用户要求，直接修改现有 [codex修改版](<{P.as_posix()}>)，未改动最初V4.2.2源文件。本文依据复审意见核对C01–C06与P2，不重写其他架构。版本为DA-MSR-V4.2.2-CODEX-REV2，状态仍DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK / IMPLEMENTATION_NOT_VERIFIED。

REV1修改前SHA256：`{sha(raw)}`。
REV2修改后SHA256：`{sha(s.encode('utf8'))}`。
[REV1备份](<{backup.resolve().as_posix()}>)；[定点差异](<{(B/'REV1_to_REV2.diff').resolve().as_posix()}> )。原有《修改说明》是REV1历史回执，旧输出hash不代表现行REV2。

## C01–C06 closure matrix

| ID | Contract Fixed | Code Implemented | Real Data Verified | Forward Verified | 修改位置与内容 |
|---|---|---|---|---|---|
'''
for i,c,r,f,desc in rows: log+=f'| {i} | {c} | NOT IN THIS TASK | {r} | {f} | {desc} |\n'
log+='''
## 裁决说明

- C02采纳两个市场contract分离，但RPS本身保持横截面收益排名，不错误宣称RPS减去了市场收益。Forward确认停牌可用同基准验证价格估值，输出MARKED_ESTIMATE及独立marked相对结果；真实数据未知不能靠覆盖率或剩余权重归一化伪造完整篮子收益。覆盖率、quote-age和消费者权限待V4-00G/00H冻结。absolute结果独立。
- C03早期留存不再强制要求已有强成员；冻结Pulse日Seed/positive成员分母，使用独立扩散与集中度门。成熟分支仍要求强成员留存。阈值未在本次臆定，R1–R3作为实现前测试要求，不宣称已运行真实算法。
- C04历史身份关系显式嵌入revision元字段；晚到更正必须分离AS_RECORDED与corrected lineage。
- C05保留开放裁决，技术bar索引与横截面/Forward会话索引分离；受影响正式模块须在窗口冻结后验收，基础盘点可继续。
- C06股票、板块阶段、轮动和风险变化分别登记证据；Stock生产依赖未通过Sector时不能借独立Stock gate越权。UI/Focus按source capability切换，不能GLOBAL PASS。
- P2统一relative_sector_state、修复“相比本版”残句、更新当前REV2标识，并明确历史附录不发出当前实施指令。

## 文档结构QA与旧冲突搜索

文档编号章节无重复，全部显式§引用有目标；代码围栏正确闭合。以下旧冲突字符串全文搜索均为0：

'''
log+='\n'.join('- `'+x+'`：0处。' for x in patterns)
log+=f'''

V4-04阶段表与字段注册均不包含turnover；V4-06明确承接§10H。市场参考、Forward市场基准、Forward板块基准及Rotation pulse篮子有不同contract id，身份字段显式包含合同及输入digest。原有DAG、revision、MDD/MFE/MAE、observation slot、独立审计约束未被撤回。

行数：REV1 {len(old.splitlines())} → REV2 {len(s.splitlines())}。本轮检查为文本结构、冲突搜索与人工合同核对，非代码/真实数据/Forward验收；5000成员、R1–R3、晚到更正、停牌窗口及分能力切换案例已写入对应章节，尚待实施验证。

## 阶段回执

阶段DOCUMENT_REVISION_REV2；证据为本说明、前后hash、备份和定点diff；接受结果DOCUMENT_REVISED。下一阶段按§78核对V4-00A基线，V4-00G/00H按依赖顺序冻结开放窗口、策略参数和能力门。C01–C06的文档修补不自动关闭独立数据、算法效果或发布验收项。
'''
assert not L.exists(); atomic(L,log.encode('utf8'))
(B/'qa.json').write_text(json.dumps({'document_sha256':sha(P.read_bytes()),'old_conflicts':{x:0 for x in patterns},'references':'PASS','fences':'PASS','duplicates':'NONE','implementation':'NOT_VERIFIED'},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'updated':str(P),'revision_notes':str(L),'before_lines':len(old.splitlines()),'after_lines':len(s.splitlines()),'sha256':sha(P.read_bytes())},ensure_ascii=False))

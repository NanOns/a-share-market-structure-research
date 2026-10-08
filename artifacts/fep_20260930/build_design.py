from pathlib import Path
import os, json, hashlib
ROOT=Path.cwd(); BASE=ROOT/'artifacts/fep_20260930'
def atomic(p,text):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name('.'+p.name+'.tmp')
 with t.open('wb') as f:f.write(text.encode('utf8'));f.flush();os.fsync(f.fileno())
 os.replace(t,p)
module=r'''# FEP R1｜未来条件期望与研究优先级层

文档编号：DA-MSR-V4.2.2-FEP-R1；日期：2026-09-30。
状态：DESIGN_REVISED / PARAMETER_AND_IMPLEMENTATION_GATES_PENDING。
这是R0的完整替代模块设计，保留其研究目标，不把R0内“必须”直接当用户授权或已冻结合同。合并只接受下述设计边界，不意味着代码、数据、概率校准或生产排序已通过。
现行实现参考HEAD为0581731c1284e82380fa115156f1dc0a16a38bd4；R0所列68276e4…已不是当前HEAD。以实施时accepted manifest和最新分阶段修订为实现权威，不能用早期REV2文本覆盖后续已接受的窗口/字段修复。

## FEP.1 产品定位与权限

FEP回答：在当前可知特征和明确训练人群内，历史可观察结果分布及冻结模型对收益、超额、路径风险和结构演化的估计是什么。它不承诺确定方向、可成交收益、个股获利概率或自动交易。
原Forward继续是未来实际结果权威；FEP是独立ex-ante输出。不修改Core Facts、Profile、Seed、raw/final eligibility、State、Radar完整候选集合、Validation enrollment及outcomes。所谓趋势预测仅在目标、风险集、数据和模型均通过对应门时启用。
M14禁止概率主张仍只适用于M14；FEP不借M14网络增强生成概率，FEP校准估计也不得给M14产品背书。无资格的回放/薄样本只显示诊断与支持度，不能借模型名宣称预测已有效。

| 能力 | 预测人群/单位 | 必需依赖 | 缺失时 |
|---|---|---|---|
| FEP_STOCK_ENTRY_CORE | 每个合规入选逻辑事件；FIRST_PREWATCH、REENTRY、NEW_CONFIRMED分层 | accepted Core/对应状态事件、ENTRY observation、相应已结算target | 仅该target UNKNOWN |
| FEP_STOCK_DAILY_CORE | 每股每市场日首次accepted存量landmark | 独立DAILY_LANDMARK观察及同权威settlement接口 | 无此label来源则NOT_ENABLED，不能套ENTRY模型 |
| FEP_MARKET_WIDE | 冻结Universe中每股每日 | MARKET_WIDE observation及覆盖审计 | 分能力延期，不把候选事件推广到全市场 |
| FEP_STOCK_SECTOR | 上述stock scope的独立扩展 | PIT membership/LOO/sector features；sector target需冻结sector benchmark | 不阻断stock price-only |
| FEP_SECTOR / FEP_ROTATION | sector entry、rotation episode分别 | accepted对应事件、固定篮子、可用labels | 未accepted的V4-08候选不冒充生产输入 |
| FEP_MARKET | 每市场日一个观察单位 | 冻结市场benchmark/状态和独立market label来源 | 不能复制到股票行扩样 |

Mandatory按(target,feature_variant,entity,observation_scope)声明。Absolute/path不要求Sector Benchmark；market excess只要求Market Benchmark；sector excess再要求Sector Benchmark。Market Regime、周/月、结构和Turnover均只对声明它的variant必需；缺失不静默给同一模型换输入。Pure-Core与Supplemental各有feature_contract/model_namespace。第一交付为Stock ENTRY条件统计；其它能力合同可开发但逐项授予权限。

## FEP.2 无反馈的执行图与冻结时点

```text
accepted Core / State / Radar -> immutable dependency manifest -> FEP observation + feature snapshot
existing settlement authority -> append-only label revisions -> as-of dataset -> fit/calibration -> model registry
snapshot + already active model set -> independent prediction slot -> FEP projection / evaluation
PRIORITY_V1 complete candidates + approved FEP axis -> separately gated PRIORITY_V2 view
```

Core接受事务只提交既有manifest/outbox或供只读reconciler扫描，不等待特征计算、训练和推理成功。FEP物化只读冻结revision集合；不得读latest head重算旧T0。FEP自己的outbox、资源预算、重试和接受事务独立，积压可恢复，失败不回滚Core。
物理snapshot_created_at可晚于Core accepted_at；逻辑输入仍按T0 cutoff。依赖某个尚未accepted的State sidecar时等它在截止内接受，超过FEP deadline只能生成reconstruction。不得把计算时间晚到改成输入早已可知。
Manifest列全体source/publication/algorithm/parameter/Universe/membership/calendar/adjustment identity与可选enrichment revision；纯Core的enrichment使用NONE token。相同publication不同补充revision不是同一feature snapshot。

## FEP.3 三条时间链与防事后选择

区分feature_cutoff、label_event_end、label_due_at、label_system_available_at、dataset_cutoff、fit_started/finished、calibration_finished、model_accepted_at、activation_effective_at、prediction_started/finished/accepted、prediction_deadline；UTC保存，交易日按冻结Asia/Shanghai市场日历。

真实预测必须同时满足：
1. 所选输入revision.system_available_at<=feature_cutoff，且实际消费manifest匹配；物化时间不代替知识时间。
2. 所选label revision及其全部派生依赖available_at<=dataset_cutoff<=fit_started；label_due_at<=dataset_cutoff，label_event_end不晚于允许边界。后到更正即使原标签早已成熟，也不允许进入更早模型。
3. fit_finished<=calibration_finished<=model_accepted_at<=activation_effective_at<=prediction_started<=prediction_finished<=prediction_accepted_at<=prediction_deadline；无校准的描述统计使用显式NOT_APPLICABLE且calibration_finished=fit_finished。
4. activation在当日slot的model_selection_cutoff前冻结，prediction_started还须不早于依赖接受。不能看当日推理/事后结果再选model_set。
5. observation_slot=(namespace,entity,observation_scope,signal_key,trade_date)固定首个合规accepted observation；prediction_slot=(observation_slot,model_family_scope,target,horizon)固定当时active model set。首个合规接受结果是FIRST_OBSERVED；失败/漏跑也写slot receipt，不挑最好revision。

后续source/label/model修订只追加observation/revision，保留supersedes及原始slot；可重建corrected视图，但不改原始预测/评分分母。今天训练模型回放旧publication属于HISTORICAL_SIMULATION，不能仅凭PIT features标为真实预测；历史fold还须逐fold按当时可见label revision训练。输入evidence_origin、execution_mode、prediction_evidence三轴分开。
长期训练输出激活前须检查模型新鲜度；训练使用的已观测校准labels也受dataset cutoff约束。回放固定容器/库/CPU线程、参数、随机种子和浮点规范；数值容差验证与canonical digest分别记录，不能用粗舍入掩盖排序变化。

## FEP.4 Observation与Label单位

observation_id表示逻辑采样单位，不是UI行或publication revision。ENTRY按事件唯一，DAILY_LANDMARK按实体/日唯一；相同episode的多事件不同target分层，不能伪称独立episodes。feature revision和label revision各自append-only。
全量目标人群先登记observation及期望targets，成功、UNKNOWN、OOD、缺失、漏预测均保留。UI Top-K、Focus与pin不能决定登记或结算。新增DAILY/MARKET_WIDE observation经独立任务请求同一Forward服务，不往Validation Cohort补造入选事件，不复制价格公式。
dataset为long form：一个observation revision × target × horizon × chosen label revision；每target独立quality/maturity/training_eligibility。一个sector label缺失不能删除同observation的absolute label。
样本权重默认日期平权：日期d下n_d个合格单位，w_i=1/(D*n_d)；scope单独计算，不同scope不拼。权重、日期/episode去重及统计estimand进入contract。每次筛掉不可观测标签都保留原始全量分母与reason ledger。

## FEP.5 Target注册与公式

以下价格值来自FORWARD_PRICE_PATH_V1及对应benchmark，FEP只投影。百分收益存ratio，显示乘100；ATR为统一观察坐标的价格单位，不能直接用收益百分比除ATR元。P0、Hj/Lj/Pj和A0=T0 ATR20均转同evaluation basis，A0>0。

| target | 定义 | 合格风险集/quality |
|---|---|---|
| ABS_RETURN_N / POSITIVE_ABS_N | R_N / I(R_N>0) | endpoint OBSERVED，0为FALSE，不把UNKNOWN设0 |
| MARKET_EXCESS_N / POSITIVE_MARKET_EXCESS_N | R_N−R_market,N / I(excess>0) | 两者同horizon、冻结benchmark OBSERVED |
| SECTOR_EXCESS_N | R_N−R_sector_ex_target,N | T0确定sector且LOO固定篮子OBSERVED |
| MFE_N / MAE_N / PATH_MDD_CLOSE_N | 复用§46A，T+1..N未来路径，含T0峰值 | path完整性单独验收 |
| MFE_ATR_N | max(0,max_j(Hj−P0))/A0 | 同基准A0与完整path |
| MAE_ATR_N | min(0,min_j(Lj−P0))/A0 | 同上 |
| PATH_MDD_ATR_N | min_j(Pj−max(P0..Pj))/A0，j=0..N | 不是MDD_ratio/(A0/P0) |
| FIRST_EXIT_PREWATCH_N | 首次CONFIRMED/INVALIDATED/EXPIRED，否则NONE | T0在PREWATCH、同episode、N内无观察缺口；同日按冻结reducer优先级 |
| ANY_CONFIRM_N / ANY_INVALIDATE_N / ANY_EXPIRE_N | T0之后至N有该事件则1 | 独立可重叠，确认后失效可同时为1，不能强制概率和1 |
| TREND_TRANSITION_N | 冻结trend enum的T0→T+N矩阵 | endpoint State合同一致且两端可评估；UP/DOWN/FLAT/UNKNOWN原始类不任意合并 |

N∈{1,3,5,10,20}；每target maturity按所需N会话与源接受时间。V1为防早事件产生训练长短偏差，首次事件target也统一等到N及观察质量齐全才进入训练；事件发生可提前记录但不提前混入完整N类样本。
FIRST_EXIT为吸收式首事件，K类加NONE概率和=1，确认后的失效不改变首类；ANY事件则允许重叠。CONFIRMED起始状态不能被当PREWATCH首次确认风险集。再入新episode不回填旧标签。
BREAKOUT_SUCCESS/FAILED、TREND_ACCELERATE/FLATTEN/BREAK、RPS_CONTINUE/DECAY、breadth/regime/rotation continuation为REGISTERED_NOT_ENABLED：E1必须另交start risk set、endpoint/first passage、逐状态转移表、阈值、producer及缺失规则，机器合同和独立向量通过才打开；不能仅靠名字发概率。
SECTOR使用MFE_CLOSE/MAE_CLOSE及独立target_id，不能用成员high之和。MARKED_ESTIMATE只在明确估值target namespace下研究，不混OBSERVED训练/评分。收益分布直接建模excess label，不能用两个中位数、概率之差冒充超额分布；MFE/MAE边际分位数不构成可成交盈亏比。

## FEP.6 缺失、删失与可识别性

PENDING/行政RIGHT_CENSORED、SUSPENDED_AT_HORIZON、MATURED_DATA_MISSING、DELISTED、IDENTITY_UNKNOWN、ADJUSTMENT_UNKNOWN分别保留。退市无终值不填−100%/0；非随机缺失不能仅“披露”便声称消除偏差。
V1连续价格目标采用complete-case描述估计，明确estimand是该scope中结果可观察子集。记录按日期/行业/状态/风险的missing coverage及与全量feature分布差异；代表性门不通过则只显示observed-subset诊断，不给全候选期望或Priority权限。未知部分若无可识别界限不能编造敏感性上下界。
结构事件可独立有可用label，不随价格整行删除。FIRST_EXIT中未满N且无首事件为删失不是NONE；观察缺口后首事件不可保证第一时标UNKNOWN。若以后采用IPCW/生存/competing-risk方法，另冻结可识别假设、估计窗口、权重截断和失配验收，不把停牌退市默认成独立删失。

## FEP.7 Feature Registry与单位

唯一映射来源是accepted字段注册表及manifest，不从R0英语别名猜值。数值必须finite；值与quality分开，全部字段nullable以表达缺失，但模型required字段不合格必须UNKNOWN；可选值填补和missing indicator只能由训练fold内冻结transform完成。禁止将NOT_IMPLEMENTED当低值。

| feature字段族 | producer/源 | 单位与允许scope | cutoff/quality |
|---|---|---|---|
| slope20/60, ret5/20, hh_progress,ll_progress | v4 accepted factors；TDX | ATR尺度/ratio/bool；Core variants | frozen publication，按实际字段合同 |
| pos60, bias20_atr, dist_high20_atr, core_extension_risk | accepted Core Profile/factors | ratio/ATR/enum；Core | 不从prior60_percentile模糊别名补字段 |
| rps5/20, delta1/3, rel_market_1/3/5 | accepted historical Universe相对因子 | RPS百分位单位按registry映射统一至0..100；delta百分点；return ratio | 禁止用未来Universe重算 |
| vol5/20, vol_ratio, ATR5/20, atr_ratio, range_ratio, core_price_damage | accepted Core factors | ratio、价格、bool；Core | 坐标/窗口digest必须一致 |
| amount_ratio5/20, volume_ratio5/20 | accepted TDX原量额因子 | ratio；Core | 不从BaoStock替换Core |
| trend_state,position_state,ma_structure_state,relative_market_state,compression_state | accepted Profile | enum；Core | 实际enum版本hash |
| maturity_stage,health_state,scenario,event_type,prewatch_age_sessions | accepted State/Event producer（后置阶段） | enum/会话数；ENTRY或DAILY | 防止target未来state混入 |
| market axes,stress_level/change,regime_ui | accepted market regime | 各enum及registry数值单位；声明market variant | 可选variant不可静默改名 |
| relative_sector_state,sector_rank,emergence,rotation_core_state,dq5,breadth_delta1/3,ma20_delta3,seed_width,top1_concentration | accepted B/context/LOO | enum/百分点/比例明确逐字段；Sector variant | membership+各sidecar digest；未accepted禁正式用 |
| turnover_ratio20,pct20/60,delta3 | accepted supplemental strict binding | ratio；percentile当前源0..1必须显式转换；Supplemental variant | enrichment_revision非空 |
| basic_breakout/pullback/recovery,support/acceptance,anchor_distance_atr,retest_count | accepted D1结构产物 | enum/ATR/count；Structure variant | Anchor原坐标及可用日，未来hold禁止 |
| market/sector breadth continuation输入 | 对应T0已知market/sector facts | 按专用variant字段schema | 不读取未来continuation label |

E1产生机器field rows，逐field保存producer、field path、type、unit、nullable、requiredness、window、quality allowlist、availability expression、allowed scopes、consumer contract。上表未验证存在的具体字段标NOT_IMPLEMENTED；不能为了覆盖R0列表临时发明因子。全字段逐一映射验收完成前，E1不记DATASET_COMPLETE。特征schema本身及转换artifact进入digest。

## FEP.8 条件统计的确定算法

CONDITIONAL_EXPECTANCY_V1以(entity_type,observation_scope,signal_type,target,horizon,feature_variant,evidence_origin,label_quality_policy,contract versions)为不可跨越的base partition。FIRST_EXIT类统计与连续收益分开。
固定backoff：L4=base+regime+trend+position+risk；L3=base+regime+trend+risk；L2=base+regime；L1=base。按L4→L1第一个满足support门的层，不能按收益正负选层；不再跨base取“全局最好率”。缺失分类只用显式MISSING bin且单独验证，不等同正常值。Sector context条件另立variant不混Core。
统计使用FEP.4日期平权，mean=sum(w*y)，positive empirical rate=sum(w*I(y>0))；weighted empirical quantile定义为累计权重首次>=q的最小有序y，完整记录方法，无隐式软件默认。类频率含NONE，归一化到1。只报观察频率，未经校准/代表性门不得叫个股未来概率。
support_state由rows、unique dates、non-overlap date blocks、entities、episodes、positive/negative或各class计数共同裁决。单股大量重叠行或一天数千股票不能制造独立支持；Market每日期一行。n_eff不得仅用Kish权重公式假装已修正相关性。分布p25/p75为结果离散度，不叫模型置信区间。

## FEP.9 模型、校准与OOS实验

先条件统计，再regularized logistic / multinomial / Huber / quantile；tree仅可选challenger，不是E5或原V4-16的前置门。模型Registry、baseline artifact和prediction日志在E1/E2已有，不能等E4才创建。
按市场日期组切分，同日横截面不可分到两折；严格Train→内部时间选参→独立Calibration→一次性Outer Test。所有scaler、imputer、winsor、bins、feature selection、OOD reference都只fit所属训练段。禁止默认随机CV或用测试结果决定条件backoff/阈值。
每边界按真实label_event_end及label_system_available_at purge：训练/校准/选择各自不得消费后段才可知的标签；至少与目标最大观察跨度相匹配，最终记录排除清单而非仅声称gap=N。共享episode/重叠观察区间在边界明确分组清除；不要求同实体永远不能出现在未来测试，任务是未来预测而非新实体泛化。单向训练没有未来训练块时不机械双向embargo；若日后双向split须另合同，不沿用V1。
Calibrator用独立时间段，概率模型各class最低事件数不足则UNCALIBRATED。Sigmoid/isotonic等方法、bins、有效期和权重事前注册；Brier/LogLoss是proper scores但不单独证明校准，还看reliability/分组支持及不确定性。回归不存在“概率校准必需”伪门，分别验证quantile覆盖与损失。
冻结primary target/horizon/metric、实验预算及一次性outer窗口；已用来调整模型的Shadow不再作为独立promotion证据。保留所有失败试验；new lineage不洗掉旧测试已被看过的事实。未来新窗口或预注册顺序检验才能重新举证。
风险输出必须与收益同屏。quantiles应有序，MFE>=0，MAE/MDD<=0；嵌套horizon同一风险集的首事件CIF不减、MFE不减、MAE/MDD不增。收益均值不要求单调。独立模型若违反这些结构，不静默裁剪：用预注册训练内约束/rearrangement，保存raw与coherent两版、重验校准；否则COHERENCE_FAILED，只诊断。

## FEP.10 OOD、drift、解释

OOD规则分schema/未知category硬失败、required缺失、单变量训练支持区间、联合支持与新制度状态；训练reference immutable。方法/threshold未冻结不能输出OOD_OK。NO_TRIGGER只表示检测器未报警，不保证分布相同。drift分别监测输入、模型输出及成熟label残差，label延迟时不伪称已测concept drift。
confidence不产出神秘总分：输出support_state、calibration_state、ood_state、coherence_state、missingness_representativeness、interval_method和训练窗口。feature contribution只解释模型计算，不当成因果/资金意图。跨horizon、跨model冲突完整保留，不挑最好周期。

## FEP.11 Priority和UI/API

默认原PRIORITY_V1完全不变，FEP展示/Shadow排序独立。PRIORITY_V2若晋级，先固定展示scope与risk-event频道，再保留V1 bucket及已冻结emergence/structure/risk关键次序，只在预注册同层tie-break用FEP tuple；不能把高风险失效股票隐藏。收益、风险、结构分别轴，不合总分。
FEP state按first-true：必需quality/support/calibration/OOD/coherence不满足→UNKNOWN；horizon/模型冲突或positive收益且风险超限→CONFLICTING；relative lower/median等事前指定统计量过正门且风险可接受→POSITIVE；同一统计量低于负门→NEGATIVE；其余NEUTRAL。精确统计量、horizon、阈值、tie-break在E5预注册，未冻结只有各轴原值、state=NOT_FROZEN。不能看到成绩后决定用mean还是median。
production权限拆成DESCRIPTIVE_DISPLAY、MODEL_DISPLAY、PRIORITY_USE，并按实体/scope/target/horizon/variant/model_set授权；Core production不自动许可FEP。GLOBAL FEP PASS无效。FEP失败恢复原PRIORITY_V1，不影响Core/UI/Focus既有source。
评估须同日同候选集合、同K、同coverage及同可观察label与PRIORITY_V1成对比较；被OOD拒绝样本保留，报告全scope覆盖与拒绝切片。按日期先算loss/spread，再用保留横截面的时间块和实体/episode敏感性分析；block长度预注册覆盖重叠风险，行IID区间不作证据。旧Core入选Forward gate不能代替FEP OOS gate。
页面显示训练人群、实际backoff条件、horizon、样本日期/blocks、结果质量、model版本、预测as-of与未启用原因。概率仅在相应MODEL_DISPLAY授权且校准有效时出现，避免百分位小数制造精度；例子数字均非真实预测。MFE/MAE是研究路径，非可执行盈亏。
API拟新增/api/v4/expectancy/context?publication_id=…作为bootstrap，返回冻结model_set/prediction_run/revision及所有依赖；随后stock/sector/market/model/evaluation请求使用现有完整context token加expectancy_model_set_id、prediction_run_id、prediction_revision。不存在返回NOT_READY，错配返回CONTEXT_MISMATCH，不偷换latest。token只代表一致性，不代表授权；服务端另校验capability grant。只读API不触发训练、在线下载或重新计算。

## FEP.12 数据库与发布完整性

配套《FEP_R1_SCHEMA_DESIGN_20260930.sql》是未部署设计DDL，放docs/design，不放运行migration目录，不执行数据库操作。已有v4.publications publication_id为revision身份；FK对接当前schema，不沿用R0缺失revision语义。
包括contracts/field registry、observations及revision、feature snapshots及values、settlement source binding/target revision、dataset membership、training artifacts、model registry/sets/activations、prediction slots/runs/results、evaluation/quality报告与priority projection。具体PK/FK/index/check见附件，目标JSON不是跨实体无约束“万能结果表”。
所有事实表append-only；current指针为可重建投影；接受通过FEP独立事务验证同entity/scope/target/horizon/feature/model/manifest兼容性和时间链，写acceptance receipt后再更新可见head。DB constraints能保证局部关系；涉及JSON AST/accepted上游/时间跨表的validation必须实现为接受服务/触发器且有故意串对象的反例，不能仅靠调用者自觉。
Label Source Binding只由既有settlement authority adapter产生，含上游row key/revision/digest。V4-15尚未实现时source FK adapter是明确阶段门；本DDL不会伪造一个已存在的Forward表。禁止FEP自己重新结算价格；structured label来自冻结未来State/Event lineage及首事件reducer。
训练artifacts只从本地受信路径读取，路径在项目产物目录、hash与manifest核对；不能自动反序列化外部pickle。保存dependency lock、schema版本、transform/calibrator/OOD引用、CPU/线程/seed、模型格式及退休原因。撤销权限append新activation/gate事件，不删除历史预测。

## FEP.13 参数冻结与开放项

FEP_POLICY_V1登记：parameter_id、value或UNSET、unit、范围、owner stage、reason、fit/calibration来源、introduced/supersedes、effective_at及status。机械数学常数与市场经验阈值分开。

| 参数族 | owner | 冻结证据与不满足处置 |
|---|---|---|
| 观察scope、slot deadline、model selection cutoff、采样权重 | E1 | 现有盘后时序/manifest样本；未冻结不收真实预测 |
| minimum rows/dates/blocks/entities/episodes/class counts、missingness门 | E2 | 不看收益的规模/可观测性盘点、时间块模拟；未冻结只诊断 |
| training rolling/expanding window、retrain cadence、purge interval规则、实验预算 | E3 | 预注册训练/校准可行性及fold反例；未冻结不train正式模型 |
| calibration method/bins/expiry、OOD支持/联合方法、coherence policy | E3 | 独立calibration窗口与盲测设计；未冻结不发MODEL_DISPLAY |
| PRIMARY target/horizon/metric、block length、promotion最小OOS日期/事件与改进/风险界限 | E3/E5 | 看最终测试前冻结；未冻结不晋级 |
| Priority tuple、同层定义、K/coverage、POSITIVE/NEGATIVE/risk门 | E5 | PRIORITY_V1成对评估设计；未冻结不影响原排序 |
| CPU/内存/批次数/运行截止、保留/归档/恢复预算 | E1/E5 | 本机性能与恢复实测；超限只停FEP |

本次不以拍定100例/60天/0.6概率等代替证据。UNSET是显式门而非实现可自由选数；设计可并入但对应正式消费尚不具备权限。

## FEP.14 唯一阶段映射（主合同§78同步）

E1–E5是V4-15之后的可选支线，不是V4-16至22的总前置门。每卡保存input commit、适用最新合同、required input、允许文件、schema/向量、资源、接受scope、rollback与next；不立即执行实现。

| 阶段 | 输入与工作 | 接受产物/反例 | 下一步与降级 |
|---|---|---|---|
| V4-15E1 | V4-15相应settlement/state接口；observations、manifest、label source adapter、registry/slots、DDL迁移 | DATASET_ENGINEERING_PASS；串entity/FK、late revision、错deadline、重复slot、完整分母测试 | E2；不足样本仍可工程验收，生产预测未开放 |
| V4-15E2 | E1；条件统计/固定backoff/基础artifact registry | BASELINE_ENGINEERING_PASS；精确weighted quantiles、scope隔离、thin sample；描述Shadow | 可先E5接展示，也可E3，不等tree |
| V4-15E3 | E2；线性/概率/quantile、隔离校准、OOD/coherence、实验注册 | MODEL_ENGINEERING_PASS；fold泄漏/预处理/calibration反例、baseline比较 | E5 Shadow；真实证据不够不晋级 |
| V4-15E4 | E3可选tree挑战 | CHALLENGER_ENGINEERING_PASS或NO_INCREMENT；失败也留档 | 不替换champion，不阻断E5 |
| V4-15E5 | E2 baseline即可；E3模型可选 | 展示/API/完整prediction ledger、Priority Shadow、独立rollback与按能力OOS门 | FEP按scope逐级授权；主线独立继续 |

V4-16记录Core与FEP独立Shadow状态；FEP尚未接入时Core可正常运行。E1必须用可重建manifest建立早期特征证据，历史回补不得冒充真实slot。E0_DATASET/E1_MODEL等验收等级在此改名FEP_DATA/FEP_ENGINEERING/FEP_SHADOW/FEP_PRIORITY，避免和任务号E1混淆。

## FEP.15 实现文件映射（仅计划）

| 已有可核查入口 | 复用边界 | 拟新增（均未实现） |
|---|---|---|
| src/v4/accepted_input.py、profile_core.py、factors/、base_seed.py | 校验accepted输入/算法字段，不照抄固定旧cutoff | src/v4/expectancy/snapshots.py、observation.py |
| config/v4_03_field_registry_v1.json、v4_04_field_registry_v2.json、v4_08_sector_field_registry_v1.json | 逐字段alias/unit/quality映射；08候选必须验收后消费 | config/fep_feature_registry_v1.json、target/policy registries |
| src/workbench_db/migrations/v4_postgres/001…018，publication FK及append-only guard | 延续migration完整性和独立回滚；不修改既有ledger | 下一可用序号_fep_*.sql（实施时分配，禁止现在抢019） |
| 主合同V4-15 Forward接口（尚未交付）；src/focus_tracker/price_path.py | 仅参考坐标经验，Focus不是FEP Label Authority | src/v4/expectancy/labels.py、datasets.py及V4-15 source adapter |
| src/workbench_service/app.py及现有context机制 | 检查路由适配再接，不能称已有FEP API | src/workbench_service/expectancy_service.py |
| 既有tests/v4_03、v4_04、v4_08的合同向量 | 复用验证方式，不用旧通过代替FEP验收 | tests/fep/{temporal,dataset,targets,validation,publication,priority}_test.py |
| 无现成FEP训练/registry | CPU独立服务、artifact签名、恢复 | src/v4/expectancy/{baseline,training,calibration,registry,inference,evaluation,priority}.py |

## FEP.16 测试矩阵与接受边界

1. Label 9月1日到期、10月1日更正：9月30日dataset不可读更正版；10月模型回放9月slot不得FIRST_OBSERVED。
2. Same publication、enrichment r1/r2产生不同snapshot；纯Core unchanged；错误entity/target/horizon/model_set组合必须拒绝。
3. PREWATCH第2日确认第4日失效：FIRST_EXIT=CONFIRMED，ANY_CONFIRM=1且ANY_INVALIDATE=1；N未满不能NONE。
4. P0=100,A0=2，收盘100→120→110：MDD_ATR=−5，MDD_ratio/(A0/P0)=−4.1666667，禁止混名；A0=0 UNKNOWN。
5. 100只股票同日20个重叠窗口不得称2000独立样本；Market同日一行；同日期所有实体在同fold。
6. 缺sector benchmark仅sector target禁用；有price label无structure则分别计；退市/缺口仍在分母。
7. scaler fit到test、calibrator复用fit、标签穿fold边界、OOD reference用全库、future State作feature均触发LEAKAGE_BLOCKED。
8. L4负收益但support足不能为正收益回退；L4不足只能按冻结顺序回退，展示真实条件。
9. E4缺失不阻断E2→E5或Core V4-16；FEP资源超限恢复PRIORITY_V1；主publication hash不变。
10. OOD拒绝一半候选后Top-K改善不能按原scope全覆盖算PASS；成对V1基线、同K/coverage、风险与不确定性同时报告。
11. 模型在deadline之后接受、次日物化输入、模型缺失、重复slot、retracted artifact、旧context readback/回滚，按真实/重建与权限分开。
12. 新champion只影响future activation slot；历史prediction/readback/原始cohort、Focus手工选择不变。

本次仅执行文档/设计反例检查；这些完整功能测试是E1–E5验收要求，不声称已运行。独立审计项在报告中逐项处置，设计修复不自动关闭真实数据/统计效力/实现审计。

## FEP.17 方法依据

训练预处理与校准应隔离，参考[scikit-learn数据泄漏说明](https://scikit-learn.org/stable/common_pitfalls.html)及[校准文档](https://scikit-learn.org/stable/modules/calibration.html)。这里采用严格时间fold而不是默认随机CV。首事件与累计发生率需先明确竞争事件定义，参考[竞争风险方法文档](https://scikit-survival.readthedocs.io/en/v0.24.0/user_guide/competing-risks.html)。这些方法资料不证明本项目在A股有增量预测能力。
'''
atomic(BASE/'FEP_R1_DRAFT.md',module)
print('draft written',len(module.splitlines()))

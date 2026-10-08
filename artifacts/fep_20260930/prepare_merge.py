from pathlib import Path
import re,os,hashlib,difflib,json
B=Path(__file__).parent; ROOT=Path.cwd()
P=Path('D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md')
old=P.read_text(encoding='utf8'); s=old
assert hashlib.sha256(P.read_bytes()).hexdigest()=='744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd'
def rep(a,b):
 global s
 assert a in s,a[:60];s=s.replace(a,b)
changes=[]
def add(section,text):
 global s
 pat=r'^# '+re.escape(section)+r'\. [^\n]*\n'
 m=re.search(pat,s,re.M); assert m,section
 n=re.search(r'^# ',s[m.end():],re.M); assert n
 pos=m.end()+n.start(); s=s[:pos]+text.strip()+'\n\n'+s[pos:];changes.append(section)
rep('DA-MSR-V4.2.2-CODEX-REV2','DA-MSR-V4.2.2-CODEX-REV3-FEP')
rep('> 日期：2026-09-25','> 日期：2026-09-30')
rep('> 最高任务：全市场每日状态理解、变化发现、可解释研究、持续跟踪和前瞻验证。','> 最高任务：全市场每日状态理解、变化发现、可解释研究、持续跟踪、前瞻验证及受能力门约束的未来条件期望。\n> 本轮：FEP R1多方设计审计后并入；当前代码核对HEAD=0581731c1284e82380fa115156f1dc0a16a38bd4。原代码基线仅保留沿革，不代表当前实现。')
rep('本版统一当前规范，保留原产品目标及无冲突章节','本版以REV2为保留基线，追加§90 FEP R1并同步相关章节；后续已接受的分阶段修订仍按其适用范围优先，本次不重写accepted heads或历史证据。FEP仅获得设计并入状态，未取得训练、模型展示或Priority生产权限。\n\n本版统一当前规范，保留原产品目标及无冲突章节')
rep('明天上涨概率多少？','无条件保证明天涨跌或把模型概率当作买卖指令？')
add('2','新增研究问题：在明确人群、训练窗口和证据质量下，未来收益/超额/风险/结构演化的条件分布是什么？历史观察频率与经授权校准的模型条件概率按§90展示；未经支持不能宣称精确个股胜率。此处显式修订REV2一概排除概率问答的产品措辞，M14原禁概率边界不变。')
add('3','FEP是accepted后旁路：冻结T0 manifest→feature snapshot；历史已可见settlement labels→dataset/model；snapshot+事前active model→prediction。其输出只进入独立展示/经授权Priority投影，不回写上图Core DAG。详细约束见§90 FEP.2。')
# subsection placement helper
def subadd(section,text):
 global s
 m=re.search(r'^## '+re.escape(section)+r'\s[^\n]*\n',s,re.M);assert m,section
 n=re.search(r'^#{1,2} ',s[m.end():],re.M);assert n
 pos=m.end()+n.start();s=s[:pos]+text+'\n\n'+s[pos:];changes.append(section)
subadd('4.9','FEP扩展保留完整现有token，增加expectancy_model_set_id、prediction_run_id、prediction_revision及冻结依赖digest；首次查询由§90 FEP.11 context bootstrap返回，错配不回落latest。token不替代生产权限校验。')
add('45','FEP observation/dataset是独立训练人群：ENTRY可引用原cohort事件，DAILY/MARKET_WIDE须单独登记并请求同一settlement权威；禁止往原Validation Cohort补造入选事件或按UI Top-K删样本。身份与排除分母见§90 FEP.4。')
add('46','FEP仅引用本阶段权威outcome revision；新增label projection不重复价格结算。其dataset按真实label available_at选择版本，不仅按成熟日；结构事件与价格targets分别质量，详§90 FEP.3–6。V4-15未交付不能声称已有可训练标签源。')
rep('统计只用于：','原Forward验证统计用于：')
add('50','新增FEP将历史已结算且当时可见的结果用于事前条件统计/冻结模型研究，按§90独立权限运行。不是用未来重写资格或自动寻参挑赢家；概率/校准/缺失选择/相关样本与Priority增量证据均受专门门约束。')
add('51','FEP验收按FEP_DATA / FEP_ENGINEERING / FEP_SHADOW / FEP_PRIORITY分层；设计并入不等于其中任一实现或实证门已通过，工程开发可在关闭生产权限下推进。见§90 FEP.14。')
add('52A','CUTOVER_V2增加FEP DESCRIPTIVE_DISPLAY、MODEL_DISPLAY、PRIORITY_USE分能力scope授权；原Stock/Sector gate不自动授予FEP，FEP未通过也不阻断原能力。模型本身需独立真实预测OOS证据而非只看旧入选信号outcome。')
add('52B','FEP能力矩阵按entity/observation_scope/target/horizon/feature_variant/model_set细分：Sector/Turnover不可用只限制其variant/target；无模型、薄样本、OOD、未冻结参数保留UNKNOWN及完整slot分母。FEP失败降回原PRIORITY_V1，Core照常。')
add('60','本节PRIORITY_V1及完整资格集合保持不变。FEP默认Shadow独立轴，只有§90的PRIORITY_USE门通过后才启用明确版本PRIORITY_V2投影；不得隐式覆盖本节排序，不隐去风险失效事件。')
add('69','FEP API为拟新增只读路由/api/v4/expectancy/{context,stock,sector,market,model,evaluation}，bootstrap和一致性按§90 FEP.11；无accepted批次返回结构化NOT_READY，禁止读取时训练/下载。')
add('72','FEP参数独立FEP_POLICY_V1，所有sample/calibration/OOD/promotion/window/priority候选按§90 FEP.13的owner及证据冻结；UNSET不授权正式消费。本修订不覆盖既有已接受阶段参数。')
add('77B','FEP只在本节accepted后消费不可变manifest/outbox，失败不加入Core同步必成链。异步snapshot、单独预测deadline、整批接受、slot模型绑定和FEP head CAS按§90；主头与旧cohort不受FEP重试/回滚影响。')
stage_rows='''| V4-15E1 | FEP Dataset / Identity / Registry | V4-15对应接口可用后独立支线；observation、feature/target、完整分母、as-of revision、model registry、slot与设计DDL落地 |
| V4-15E2 | Conditional Statistics Baseline | E1后；桶内日期平权、确定backoff/support；baseline可直接接E5 |
| V4-15E3 | Interpretable Models / Calibration | E2后可选；时序训练/校准/OOD/coherence与实验注册，不是原主线前置门 |
| V4-15E4 | Optional Tree Challenger | E3后可选；不要求成功或替换champion才能做E5 |
| V4-15E5 | FEP Projection / Priority Shadow | E2 baseline即可，E3/4可选；独立预测ledger/API/回滚，按能力积累OOS授权 |
'''
pos=s.index('| V4-16 |');s=s[:pos]+stage_rows+s[pos:];changes.append('78')
add('78','上述E1–E5是可选支线而非V4-16至22的顺序前置条件，详细输入/产物/验收见§90 FEP.14。V4-16可在FEP NOT_READY下照常Core Shadow；不得等待未来真实样本才开展其它独立工程。')
add('80','FEP新增时序/统计/故障矩阵见§90 FEP.16：迟到label/model、无模型slot、无label分母、fold泄漏、ATR量纲、条件权重、同日确认后失效、scope降级、成对Priority评估及原Core digest不变。文档反例通过不代替这些实施测试。')
add('81','FEP DoD要求§90的machine field/target mapping、设计DDL到正式迁移的跨表validator、独立数值向量、时序与恢复集成、真实OOS和分能力接受回执。当前只完成设计并入；所有生产许可保持未授予。')
add('83','FEP回滚撤销其activation/capability并恢复PRIORITY_V1；保留原预测、模型、labels及失效试验，不回滚Core或删除Focus人工工作。没有active model也必须保留计划slot与漏跑回执。')
add('84','FEP=未来条件期望与研究优先级层；Observation Population=冻结的采样人群；Prediction Slot=预先约束的预测机会；FIRST_EXIT与ANY_EVENT为不同target。Outcome=事后事实，Expectancy=事前估计；其余定义见§90。')
add('85','FEP独立审计/生产权限不由Core阶段PASS继承；dataset、transform、calibration与一次性测试均有不可变lineage。M14、TDX只读及无自动交易约束不变。')
add('86','完整架构增加accepted后FEP支线，输入为当时可知特征和过去已可用labels，输出为可解释期望轴；原验证/Focus/主线继续独立运行。§90替代FEP R0草稿，不重写旧accepted实现。')
add('87','FEP链路映射：accepted facts/state→冻结feature；V4-15 outcomes→as-of target/dataset；E2/E3模型→独立prediction；E5→详情/Shadow priority。每个箭头携带source/time/quality/contract identity，逐项按§90登记。')
add('87A','FEP新增registry由§90 FEP.7/12及配套设计DDL定义：feature snapshot/value、observation revision、target/source binding、dataset eligibility ledger、dataset rows、model/set/activation、planned slot/model binding、prediction run/row、quality/evaluation、priority projection。缺少机器field-to-producer映射或cross-table validator时E1不得PASS；本文列族不冒充已存在实现。')
rep('当前生效版本为REV2，C01–C06及P2定点变更','当前生效版本为REV3-FEP；REV2中C01–C06及P2定点变更')
rep('STATUS = DOCUMENT_REVISED / READY_FOR_BASELINE_AND_CONTRACT_WORK','STATUS = DOCUMENT_REVISED / FEP_DESIGN_INTEGRATED / IMPLEMENTATION_NOT_VERIFIED')
rep('**文档结束**','')
module=(B/'FEP_R1_DRAFT.md').read_text(encoding='utf8')
module=module.replace('# FEP R1｜未来条件期望与研究优先级层','# 90. FEP R1｜未来条件期望与研究优先级层',1)
s=s.rstrip()+'\n\n'+module+'\n**文档结束**\n'
def atomic(p,t):
 tmp=p.with_name('.'+p.name+'.tmp')
 with tmp.open('wb') as f:f.write(t.encode('utf8'));f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
atomic(B/'FINAL_REV3_FEP_DRAFT.md',s)
atomic(B/'REV2_to_REV3_FEP.diff',''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='REV2',tofile='REV3-FEP')))
atomic(B/'merge_map.json',json.dumps(changes,ensure_ascii=False,indent=2))
print('final draft',len(s.splitlines()),'lines; sections',len(changes))

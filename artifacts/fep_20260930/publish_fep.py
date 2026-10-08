from pathlib import Path
import os,re,json,hashlib,shutil
ROOT=Path.cwd(); B=Path(__file__).parent
DESK=Path('D:/Users/lps/Desktop')
P=DESK/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md'
R0=DESK/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R0_20260930.md'
REV2=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md'
FINAL=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV3_FEP_20260930.md'
MODULE=DESK/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R1_20260930.md'
AUDIT=DESK/'V4_2_2_FEP_CROSS_AUDIT_AND_INTEGRATION_20260930.md'
SQL=ROOT/'docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql'
SQLDESK=DESK/SQL.name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
oldhash='744B75906D932D6B11E01A1CD90F6A8DE082CC23B673E876E219642620DD30FD'
assert sha(P)==sha(REV2)==oldhash
r0hash=sha(R0)
doc=(B/'FINAL_REV3_FEP_DRAFT.md').read_text(encoding='utf8')
module=(B/'FEP_R1_DRAFT.md').read_text(encoding='utf8')
qa=json.loads((B/'qa.json').read_text(encoding='utf8'))
assert qa['status']=='DOCUMENT_QA_AND_HAND_VECTORS_PASS'
reports=[ROOT/'docs/audits'/x for x in ['FEP_STATISTICS_REVIEW_20260930.md','FEP_TEMPORAL_REVIEW_20260930.md','FEP_INTEGRATION_REVIEW_20260930.md','FEP_INTEGRATION_SECOND_REVIEW_20260930.md']]
assert 'DESIGN_ACCEPTABLE_FOR_INTEGRATION' in reports[0].read_text(encoding='utf8')
assert 'DESIGN_INTEGRATION_PASS_WITH_IMPLEMENTATION_GATES' in reports[3].read_text(encoding='utf8')
assert 'DESIGN_REVIEW_PASS_WITH_IMPLEMENTATION_GATES' in reports[1].read_text(encoding='utf8'), 'final temporal review required'
def atomic(p,data):
 p.parent.mkdir(exist_ok=True,parents=True)
 t=p.with_name('.'+p.name+'.fep.tmp');assert not t.exists()
 with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(t,p);assert p.read_bytes()==data
def write_new(p,data):
 assert not p.exists(),str(p)
 atomic(p,data)
def link(label,p,line=None):
 return f'[{label}](<{p.resolve().as_posix()}{":"+str(line) if line else ""}>)'
def line_for(h):
 for i,l in enumerate(doc.splitlines(),1):
  if l.startswith('## '+h+' ') or l.startswith('# '+h+'. '):return i
 return 1

# Verify write destinations before altering the current desktop file.
for x in [FINAL,MODULE,AUDIT,SQLDESK,ROOT/'docs/design/FEP_R1_MODULE_DESIGN_20260930.md',ROOT/'docs/audits/FEP_CROSS_AUDIT_AND_INTEGRATION_20260930.md']:
 assert not x.exists(),str(x)
write_new(B/'REV2_before_FEP_20260930.md',P.read_bytes())
finalhash=hashlib.sha256(doc.encode('utf8')).hexdigest().upper()
audit=f'''# V4.2.2 FEP 多方交叉审计、修订与合并回执

日期：2026-09-30；阶段：FEP_DESIGN_CROSS_AUDIT_AND_INTEGRATION。

结论：经过统计、时序与工程集成三个独立方向初审，以及修订稿第二轮交叉复核，设计阻断已在FEP R1与主合同映射中修正，允许作为受明确实施门约束的设计追加到V4.2.2。当前版本 `DA-MSR-V4.2.2-CODEX-REV3-FEP`。本次接受范围为DESIGN_INTEGRATED，不代表模型、数据、校准或Priority生产许可。

## 输入与实际状态

| 输入 | 身份 |
|---|---|
| FEP R0 | `{r0hash}` |
| REV2主合同 | `{oldhash}`，与桌面及仓库证据副本一致 |
| 核对仓库HEAD | `0581731c1284e82380fa115156f1dc0a16a38bd4` |
| R0引用旧HEAD | `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`，不当当前实现状态 |
| 合并后主合同 | `{finalhash}` |
| 设计DDL | `{sha(SQL)}`；27张FEP设计表，未执行/部署 |

已核对accepted范围与最新阶段任务：V4-15统一Forward结算与FEP尚属后续交付；accepted工程不等于完整历史PIT训练样本。新设计不会改写已有accepted heads、已接受参数或后续阶段修订。

## 多方结论

| 方向 | 原始问题记录 | 修订后结论 |
|---|---:|---|
| 统计与算法 | 14项（10 P1 / 4 P2） | DESIGN_ACCEPTABLE_FOR_INTEGRATION |
| 时序与泄漏 | 8项（6 P1 / 2 P2） | DESIGN_REVIEW_PASS_WITH_IMPLEMENTATION_GATES |
| 工程与主合同集成 | 9项（8 P1 / 1 P2） | DESIGN_INTEGRATION_PASS_WITH_IMPLEMENTATION_GATES |

这些是31条独立审计记录，部分描述同一跨域问题，不虚称31个互不重复缺陷。二轮新增3个设计问题：条件桶权重未归一化、无模型无法登记漏预测、无标签无法保留dataset排除分母，均已定点修复。原审计条目保留OPEN_IMPLEMENTATION_EVIDENCE，不自动关闭真实数据、效果或发布项。

## 主要遗漏与实际修复

1. 标签到期与当时可见时间分离；训练冻结具体label revision、dataset cutoff和完整模型接受/激活/预测deadline链。
2. 入选事件、每日存量、全市场和板块/市场训练人群分开，不能用事件样本替全市场预测。
3. FIRST_EXIT与ANY_EVENT分开：先确认后失效可以同时发生；完整期内无事件增加NONE，删失不当negative。
4. 技术特征原T0身份不变，label保持独立到期坐标；ATR量纲明确，MDD_ATR不能用百分回撤除ATR比例冒名。
5. 条件统计的支持度含日期块、实体、episode及事件数；选桶后在桶内重算日期平权，不把行数等同独立证据。
6. 训练、选参、校准、最终测试与所有预处理/OOD参考按时间分离，保留全试验和一次性测试边界。
7. Sector/Benchmark按target依赖，E1–E5改可选旁路，Tree不成为原V4-16必经门。
8. FEP异步读取冻结manifest，预测slot、model binding和完整expected ledger分离；模型/标签缺失也留失败分母。
9. Priority与PRIORITY_V1在同日同候选集成对验证，风险事件保留；只有独立capability授予后才用FEP排序。
10. 显式修订原产品概率边界、context/API、旁路outbox、阶段表、字段注册、回滚与DoD，避免只追加一章留下跨章冲突。

## 审计条目处置矩阵

DESIGN_FIXED仅表示语义在正文/DDL设计中修正。所有条目的Code/Real Data/Model Forward列均为NOT_VERIFIED；字段逐一机器映射、跨表接受服务、参数与真实预测证据需对应E1–E5门验收。

| 审计ID | 修订位置 | 文档处置 | 实施/真实证据 |
|---|---|---|---|
'''
maps={
'STAT-01':'FEP.5','STAT-02':'FEP.1','STAT-03':'FEP.6','STAT-04':'FEP.3','STAT-05':'FEP.9','STAT-06':'FEP.8','STAT-07':'FEP.8','STAT-08':'FEP.5','STAT-09':'FEP.9','STAT-10':'FEP.11','STAT-11':'FEP.9','STAT-12':'FEP.5','STAT-13':'FEP.10','STAT-14':'FEP.5',
'TEMP-01':'FEP.3','TEMP-02':'FEP.3','TEMP-03':'FEP.2','TEMP-04':'FEP.5','TEMP-05':'FEP.4','TEMP-06':'FEP.9','TEMP-07':'FEP.5','TEMP-08':'FEP.3',
'FEP-I01':'FEP.1','FEP-I02':'FEP.14','FEP-I03':'FEP.2','FEP-I04':'FEP.12','FEP-I05':'FEP.3','FEP-I06':'2','FEP-I07':'FEP.11','FEP-I08':'FEP.7','FEP-I09':'FEP.11',
'R2-STAT-WEIGHT':'FEP.8','R2-I01':'FEP.12','R2-I02':'FEP.12'}
for issue,section in maps.items():
 audit+=f'| {issue} | {link(section,P,line_for(section))} | DESIGN_FIXED | NOT_VERIFIED / 对应阶段门 |\n'
audit+='''
## 验证与开放门

- 主合同编号章节无重复，显式§引用无悬空，Markdown代码围栏闭合；E1–E5唯一阶段映射已同步。
- 设计DDL表引用名称检查通过；FK、唯一键和expected slot/label ledger经设计复核。未运行PostgreSQL解析/建表/约束反例，数据库设计通过不等于migration执行通过。
- 独立可手算反例共9项通过：桶内权重/均值/频率、日期平权、ATR回撤与百分回撤差异、首事件与任意事件、迟到label过滤。它们验证公式设计，不是FEP实现测试。
- 待冻结：sample/date/block/event门、训练与校准窗口、OOD、模型有效期、预测deadline、晋级标准、Priority tuple与资源预算。未赋值参数有显式权限门，不能实施时随意补数。
- 待实现：逐field机器producer/unit/quality映射、V4-15权威binding、跨表时序/对象validator、事务readback、模型artifact验证、训练/真实Shadow/完整OOS。

## 主合同修改说明

在原正文同步23处章节/子章节连接，覆盖产品目标、主链、context、cohort/Forward、证据、按能力切换、排序/API、参数、每日outbox、阶段、测试、DoD、回滚、术语及registry；最后新增§90作为FEP R1正文。详细差异保存于产物目录。

仓库REV2证据文件不改；桌面现行codex修改版原子更新为REV3-FEP，并另存仓库REV3_FEP最终副本。R0原稿保留，R1为审计后的独立替代模块设计。历史审计“需修改”结论按最后复核记录解释，不删除首轮发现。

## 交付与证据

'''
for label,p in [('更新后的最终方案',P),('仓库REV3-FEP最终副本',FINAL),('独立FEP R1模块',MODULE),('设计DDL（未执行）',SQLDESK),('REV2修改前备份',B/'REV2_before_FEP_20260930.md'),('逐章diff',B/'REV2_to_REV3_FEP.diff'),('文档QA与数值反例',B/'qa.json')]:
 audit+='- '+link(label,p)+'\n'
audit+='\n独立审计原始报告：\n\n'
for p in reports:audit+='- '+link(p.name,p)+'\n'
audit+='''
## 最终阶段回执

合同依据为用户要求“先交叉/多方审计，最后追加主方案”、AGENTS.md及现行基线。证据为独立报告、修订后复核、差异与QA。接受范围DESIGN_INTEGRATED_WITH_IMPLEMENTATION_GATES；生产许可UNGRANTED。本次仅写文档及设计产物，没有运行scanner、模型训练、数据库迁移或交易；原TDX输入只读。

下一阶段：保持当前工程主线按最新accepted阶段推进；在对应V4-15接口准备好后，依据§78及§90启动FEP可选E1支线，先冻结字段/target/slot/参数与权威数据映射，再独立验收。样本积累不阻断独立工程开发。
'''
write_new(FINAL,doc.encode('utf8'))
write_new(MODULE,module.encode('utf8'))
write_new(ROOT/'docs/design/FEP_R1_MODULE_DESIGN_20260930.md',module.encode('utf8'))
write_new(SQLDESK,SQL.read_bytes())
write_new(AUDIT,audit.encode('utf8'))
write_new(ROOT/'docs/audits/FEP_CROSS_AUDIT_AND_INTEGRATION_20260930.md',audit.encode('utf8'))
assert sha(P)==oldhash
atomic(P,doc.encode('utf8'))
assert sha(P)==sha(FINAL)==finalhash
assert sha(REV2)==oldhash and sha(R0)==r0hash
receipt={'status':'FEP_DESIGN_INTEGRATED_WITH_IMPLEMENTATION_GATES','date':'2026-09-30','final_sha256':finalhash,'rev2_unchanged':True,'r0_unchanged':True,'document':str(P),'audit':str(AUDIT),'module':str(MODULE),'model_permission':'UNGRANTED'}
atomic(B/'publication_receipt.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode('utf8'))
print(json.dumps(receipt,ensure_ascii=False))

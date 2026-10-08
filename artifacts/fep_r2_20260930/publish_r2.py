from pathlib import Path
import os,json,hashlib,difflib,zipfile
ROOT=Path.cwd(); B=Path(__file__).parent; D=Path('D:/Users/lps/Desktop')
P=D/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md'
R1M=D/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R1_20260930.md'
EX=D/'V4_2_2_FEP_R1_EXTERNAL_CROSS_AUDIT_R1_20260930.md'
R2M=D/'A_SHARE_RESEARCH_SYSTEM_V4_2_2_FORWARD_EXPECTANCY_PRIORITY_MODULE_R2_20260930.md'
R2SQL=D/'FEP_R2_SCHEMA_DESIGN_20260930.sql'
REPORT=D/'V4_2_2_FEP_R2_PATCH_DISPOSITION_AND_QA_20260930.md'
PACK=D/'V4_2_2_FEP_R2_EXTERNAL_REAUDIT_PACKAGE_20260930.zip'
REPOFINAL=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
old=P.read_bytes(); assert sha(old)=='93552EF08304AB7D9F841045123EDAA1A31C8847AF68D8462C211D6B385EDE5F'
module=(B/'FEP_R2_MODULE_DRAFT.md').read_bytes();sql=(B/'FEP_R2_SCHEMA_DESIGN_20260930.sql').read_bytes();final=(B/'FINAL_REV4_FEP_R2_DRAFT.md').read_bytes()
qa=json.loads((B/'R2_QA.json').read_text(encoding='utf8'))
assert qa['status']=='R2_DOCUMENT_SQL_AST_AND_HAND_SCENARIOS_PASS'
integration=ROOT/'docs/audits/FEP_R2_INTEGRATION_REVIEW_20260930.md'
temporal=ROOT/'docs/audits/FEP_R2_TEMPORAL_REVIEW_20260930.md'
assert 'PATCH_VERIFIED' in integration.read_text(encoding='utf8')
assert 'DESIGN_REMEDIATED' in temporal.read_text(encoding='utf8')
original_reports=[ROOT/'docs/audits'/n for n in ['FEP_STATISTICS_REVIEW_20260930.md','FEP_TEMPORAL_REVIEW_20260930.md','FEP_INTEGRATION_REVIEW_20260930.md','FEP_INTEGRATION_SECOND_REVIEW_20260930.md']]
history={p:sha(p.read_bytes()) for p in [R1M,EX,ROOT/'docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql',ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV3_FEP_20260930.md']}
def atomic(p,b):
 p.parent.mkdir(exist_ok=True,parents=True);t=p.with_name('.'+p.name+'.tmp');assert not t.exists()
 with t.open('wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(t,p);assert p.read_bytes()==b
def new(p,b):assert not p.exists(),p;atomic(p,b)
def l(label,p):return f'[{label}](<{p.resolve().as_posix()}>)'
main_diff=''.join(difflib.unified_diff(old.decode('utf8').splitlines(True),final.decode('utf8').splitlines(True),fromfile='REV3-FEP',tofile='REV4-FEP-R2'))
module_diff=''.join(difflib.unified_diff(R1M.read_text(encoding='utf8').splitlines(True),module.decode('utf8').splitlines(True),fromfile='FEP-R1',tofile='FEP-R2'))
sql_diff=''.join(difflib.unified_diff((ROOT/'docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql').read_text(encoding='utf8').splitlines(True),sql.decode('utf8').splitlines(True),fromfile='FEP-SCHEMA-R1',tofile='FEP-SCHEMA-R2'))
report=f'''# FEP R2 外部审计定点处置、修改说明与QA

日期：2026-09-30。适用输入为线上审计 `DA-MSR-V4.2.2-FEP-EXTERNAL-AUDIT-R1`，SHA256 `{sha(EX.read_bytes())}`。

当前状态：R2_PATCHED / EXTERNAL_REAUDIT_PENDING / IMPLEMENTATION_NOT_VERIFIED。
线上R1唯一外部结论 `EXTERNAL_DESIGN_ACCEPTANCE_BLOCKED_PENDING_R2` 保留。本次逐项修复并交付复核证据，不自行授予外部PASS。FEP最终设计冻结、migration及E1正式任务卡继续等外部R2复审；V4现行主工程线不受FEP门阻断。

## 核对结论

五个P1均成立。上轮内部设计复核漏掉了正文和Schema之间的逐fold选择、细粒度授权和CAS结构差异，本次修正该接受范围。R1的时序、统计、backoff权重、首事件、独立人群、无模型/无label分母及旁路架构全部保留。R2是定点更新，不重新设计预测目标或Core。

| 外部项 | R2修改 | 文档/DDL处置 | 实现及外部验收 |
|---|---|---|---|
| P1-01 / R2-01 | expected ledger取消全局selected revision；新增fold+partition cutoff/selection；训练row复合FK绑定同fold revision+digest，三时间触发器参考 | DESIGN_REMEDIATED；早fold r1、晚fold r2可以独立表达 | DB运行未验；外部pending |
| P1-02 / R2-02 | permission_keys明确scope+target+horizon+feature_contract+model_set+capability；activation、acceptance、API与Priority共享grant_key | DESIGN_REMEDIATED；T5授权不蕴含T20授权 | 真实权限/服务未验；外部pending |
| P1-03 / R2-03 | deployment_heads、prior activation/version、变更receipt、CAS参考函数；冲突整事务回滚，只有head受控UPDATE | DESIGN_REMEDIATED；初始/替换/撤销/重投都有结构与反例 | PL/pgSQL、并发/角色未验；外部pending |
| P1-04 / R2-04 | source_fact_available_at、label_training_mature_at、label_revision_available_at分别保存；删错误due CHECK | DESIGN_REMEDIATED；T2事实已知/T5成熟合法，T3不能训练 | 权威adapter及成熟质量未验；外部pending |
| P1-05 / R2-05 | ENTRY只能事件日注释；今日全Radar PRIORITY_USE必须DAILY_LANDMARK/candidate-day同日预测及预注册覆盖门 | DESIGN_REMEDIATED；旧ENTRY不能长期作为今日预测 | daily label/coverage及排序未验；外部pending |
| P2-01 / R2-06 | 完整原始四份多方报告、外审、R2复核、diff、QA及hash manifest收入ZIP | EVIDENCE_PACKAGED | 外部可上传复核；未声称已push GitHub |
| P2-02 | 当前32张事实/历史表逐表显式guard；future migration必须清单测试；head单独受控触发器 | DESIGN_REMEDIATED | 未实际DB建表 |
| P2-03 | 主Header分ORIGINAL DESIGN BASELINE与CURRENT AUDITED IMPLEMENTATION HEAD | DOCUMENT_FIXED | 当前核对HEAD仍0581731c… |

## 内部复核新增小项

- Priority projection与权限回执以projection_id/run_id复合FK关联，不能借其它run的receipt。
- CHAMPION-only生产展示/排序明确；同集合baseline/challenger不继承该生产授权。
- CAS必需参数NULL入口拒绝、重投比较用IS DISTINCT FROM，避免SQL UNKNOWN放过不同请求；相同request_id严格一致回读。
- 每fold各partition日期/observation/同实体episode隔离；episode身份包含scope+entity，不能将不同股票同号误判为同episode。
- FIT、TUNE、CALIBRATION、OUTER_TEST各自phase_started_at和phase_manifest明确；TEST评分截止可晚于模型拟合，TEST label不进入该模型训练/选择/校准。

## 实際修改与版本

- 主文更新为DA-MSR-V4.2.2-CODEX-REV4-FEP-R2，§90替换为R2，并同步Header、当前版本声明和注册表引用。
- 模块独立文件为FEP R2；DDL版本FEP_SCHEMA_DESIGN_V2，新增fold选择、permission/head/receipt及验证参考。
- R1原始模块/DDL、REV3仓库证据及原始审计文件保留；桌面现行主文采用备份后原子更新。R1修订记录是历史，不代表当前最终外部冻结。
- 此次只写文档和未部署设计SQL，不启动训练、scanner、数据库migration或生产切换。

## QA结果与准确边界

PostgreSQL SQL语法由pglast v8.4解析通过：{qa['sql_statements']}条语句；{qa['ddl_tables']}张表；{qa['foreign_keys_checked']}条本地/外部引用定义已检查，本地FK目标列及唯一键匹配；{qa['immutable_fact_tables']}张事实/历史表显式guard，deployment_heads独立受控。
文档编号、§引用、围栏及当前版本声明检查通过。手工可算/关系情景检查涵盖per-fold r1/r2、T2事实/T5成熟、T5/T20权限区别及旧version并发请求只接受一次。上述是设计反例，不冒充SQL事务运行测试。

PL/pgSQL解析器不支持自定义fep schema rowtype，故未将函数体执行/依赖、权限与并发标PASS；也没有在实际PostgreSQL建表。E1必须在外部设计接受后于隔离环境验证角色、FK、触发器、事务回滚、并发与故意串对象反例。代码实施、真实数据及Forward效果均NOT_VERIFIED。

## 文件身份

| 文件 | SHA256 |
|---|---|
| 修改前REV3-FEP | `{sha(old)}` |
| 修改后REV4-FEP-R2 | `{sha(final)}` |
| FEP R2模块 | `{sha(module)}` |
| FEP R2 Schema | `{sha(sql)}` |

## 复核包与下一阶段

'''
for label,p in [('更新后的主方案',P),('R2独立模块',R2M),('R2设计SQL',R2SQL),('完整外部复审包',PACK),('内部集成复核',integration),('内部时序复核',temporal)]:report+='- '+l(label,p)+'\n'
report+='''
ZIP包含文件清单与每文件SHA256，不含数据库、TDX数据、模型artifact或凭据。原始四份审计报告完整保留首轮发现及后续结论；新增R2报告也明确其内部复核范围，不冒充另一位外部模型的PASS。

下一阶段：将该包交线上模型进行R2定点复审；外部接受前仅继续设计修订与不受影响的V4主线。其后待V4-15接口就绪，再冻结实施参数/机器映射与正式E1任务卡。本说明不作为解除外部门的替代证据。
'''
targets=[R2M,R2SQL,REPORT,PACK,REPOFINAL,ROOT/'docs/design/FEP_R2_MODULE_DESIGN_20260930.md',ROOT/'docs/design/FEP_R2_SCHEMA_DESIGN_20260930.sql',ROOT/'docs/audits/FEP_R2_EXTERNAL_PATCH_DISPOSITION_20260930.md']
assert all(not p.exists() for p in targets)
new(B/'REV3_before_R2.md',old)
new(B/'REV3_to_REV4_R2.diff',main_diff.encode('utf8'));new(B/'MODULE_R1_to_R2.diff',module_diff.encode('utf8'));new(B/'SCHEMA_R1_to_R2.diff',sql_diff.encode('utf8'))
new(R2M,module);new(R2SQL,sql);new(REPOFINAL,final)
new(ROOT/'docs/design/FEP_R2_MODULE_DESIGN_20260930.md',module);new(ROOT/'docs/design/FEP_R2_SCHEMA_DESIGN_20260930.sql',sql)
new(REPORT,report.encode('utf8'));new(ROOT/'docs/audits/FEP_R2_EXTERNAL_PATCH_DISPOSITION_20260930.md',report.encode('utf8'))
# Build a self-contained review bundle before updating current desktop baseline.
entries={
 'CURRENT/MAIN_REV4_FEP_R2.md':final,'CURRENT/FEP_MODULE_R2.md':module,'CURRENT/FEP_SCHEMA_R2.sql':sql,
 'CURRENT/R2_PATCH_DISPOSITION.md':report.encode('utf8'),'QA/R2_QA.json':(B/'R2_QA.json').read_bytes(),
 'DIFF/MAIN_REV3_to_REV4.diff':main_diff.encode('utf8'),'DIFF/MODULE_R1_to_R2.diff':module_diff.encode('utf8'),'DIFF/SCHEMA_R1_to_R2.diff':sql_diff.encode('utf8'),
 'EXTERNAL/R1_EXTERNAL_CROSS_AUDIT.md':EX.read_bytes(),
 'HISTORY/MAIN_REV3_FEP.md':old,'HISTORY/FEP_MODULE_R1.md':R1M.read_bytes(),'HISTORY/FEP_SCHEMA_R1.sql':(ROOT/'docs/design/FEP_R1_SCHEMA_DESIGN_20260930.sql').read_bytes(),
 'HISTORY/R1_INTEGRATION_RECEIPT.md':(ROOT/'docs/audits/FEP_CROSS_AUDIT_AND_INTEGRATION_20260930.md').read_bytes(),
}
for p in original_reports+[integration,temporal]:entries['RAW_AUDITS/'+p.name]=p.read_bytes()
entries['README.md']=('''# FEP R2 外部定点复审包

先读CURRENT/R2_PATCH_DISPOSITION.md，再核对EXTERNAL原审计、三个CURRENT文件及DIFF。
RAW_AUDITS含四份R1多方原始报告和两份R2内部复核，保留原始发现与后续结论。
QA只证明文档/SQL语法/结构和手工情景，未实际执行数据库。
状态：EXTERNAL_REAUDIT_PENDING；不授予FEP最终冻结/migration/E1/生产许可。
MANIFEST.json为每个包内文件的SHA256与字节数；manifest不把自身纳入hash。
''').encode('utf8')
manifest={'status':'EXTERNAL_REAUDIT_PENDING','files':{n:{'sha256':sha(b),'bytes':len(b)} for n,b in entries.items()}}
entries['MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
t=PACK.with_name('.'+PACK.name+'.tmp')
with zipfile.ZipFile(t,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in entries.items():z.writestr(name,data)
os.replace(t,PACK)
with zipfile.ZipFile(PACK) as z:
 assert z.testzip() is None
 for n,info in manifest['files'].items():assert sha(z.read(n))==info['sha256']
assert P.read_bytes()==old;atomic(P,final)
assert P.read_bytes()==REPOFINAL.read_bytes()==final
for p,h in history.items():assert sha(p.read_bytes())==h
receipt={'status':'R2_PATCHED_EXTERNAL_REAUDIT_PENDING','main_sha256':sha(final),'package_sha256':sha(PACK.read_bytes()),'package_files':len(entries),'historical_inputs_unchanged':True,'model_permission':'UNGRANTED','sql_runtime':'NOT_EXECUTED'}
atomic(B/'R2_PUBLICATION_RECEIPT.json',json.dumps(receipt,ensure_ascii=False,indent=2).encode('utf8'))
print(json.dumps(receipt,ensure_ascii=False))

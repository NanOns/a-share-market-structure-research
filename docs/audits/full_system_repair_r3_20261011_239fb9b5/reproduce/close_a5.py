from pathlib import Path
import json,hashlib,os,subprocess
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
def write(name,value):
    p=OUT/name;t=p.with_suffix('.tmp');raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,bytes) else value;t.write_bytes(raw);os.replace(t,p)
files=['src/workbench_analysis/full_loo_v3_3.py','config/full_current_loo_candidate_02.json','tests/test_audit_repair_loo_r3.py']
for name in files:
    p=ROOT/name;p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
write('a5_junit.xml',(BASE/'a5_junit.xml').read_bytes())
write('A5_REPAIR_RESULT.json',dict(contract_id='TODAY_RESEARCH_FULL_CURRENT_LOO_V3_3_CANDIDATE_02',base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),issue='FA-017',source_bindings=[dict(path=n,sha256=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()) for n in files],test_count=10,cases=['n1 empty UNKNOWN','no-related FALSE','no-members FALSE','n2/n6 independent market/sector medians','overlap global removal','unrelated surviving sector','market initial empty/target-only controlled reject','mixed-date reject before shortcut'],evidence='a5_junit.xml',acceptance='CANDIDATE_ENGINEERING_PASS_EXTERNAL_PENDING',formal_consumer_enabled=False,current_production_incident_proven=False,next='Independent candidate recheck; formal operational LOO authority unchanged'))
ledger=json.loads((OUT/'EFFECTIVE_AUDIT_ITEMS_R3.json').read_bytes())
for row in ledger['issues']:
    if row.get('audit_item_id',row.get('id'))=='FA-017':row.update(status='CANDIDATE_ENGINEERING_FIXED_EXTERNAL_PENDING',repair_evidence='A5_REPAIR_RESULT.json')
write('EFFECTIVE_AUDIT_ITEMS_R3.json',ledger)
report=OUT/'REPAIR_REPORT_R3.md';write('REPAIR_REPORT_R3.md',(report.read_text(encoding='utf8')+'''\n## A5

候选 LOO 升级 CANDIDATE_02：市场非空而剔除后成员全空，相关关系明确 UNKNOWN / SECTOR_EMPTY_AFTER_EXCLUSION；无相关关系 FALSE；市场全空使用唯一受控异常。空分支前校验共同单日，防止绕过输入校验。10项边界与既有重叠测试通过。仅候选域，不覆盖正式运营 LOO 或声称线上事故已确认。
''').encode())
write('reproduce/close_a5.py',Path(__file__).read_bytes())

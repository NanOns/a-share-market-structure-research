from pathlib import Path
import hashlib,json,os,sys,gzip
ROOT=Path('G:/codex work/大A交易');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,bytes) else value
    t=p.with_suffix(p.suffix+'.tmp');t.write_bytes(raw);os.replace(t,p)
old=ROOT/'docs/audits/full_system_audit_r2_20261011_58faf74e'
external=Path('D:/Users/lps/Desktop/阶段任务/V4_FULL_SYSTEM_R2_INDEPENDENT_REAUDIT_20261011.md')
write('INDEPENDENT_REAUDIT_INPUT.md',external.read_bytes())
protected={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'data/v4').glob('*HEAD.json')}
historical={str(p.relative_to(ROOT)):sha(p) for parent in (old,ROOT/'docs/audits/full_system_audit_r1_20261011_a2eadda') for p in parent.rglob('*') if p.is_file()}
write('STAGE_CONTRACT.json',dict(contract_id='FULL_SYSTEM_REPAIR_R3_V1',base_head='239fb9b545ac25305af02a645a77d82246cbb71a',external_input_sha256=sha(external),protected_heads=protected,historical_audits=historical,scope=['AR2-E01','A1','A2','A3','A4','A5','A6','B1','B2','B3'],external_acceptance='NOT_GRANTED',production_takeover=False,global_status='AUDIT_INCOMPLETE',next='Execute independent work packages; real-source and explicit-permission gates retained'))
ledger=json.loads((old/'INDEPENDENT_AUDIT_ITEMS_R2.json').read_bytes())
write('LEDGER_SOURCE_BINDING.json',dict(path=str((old/'INDEPENDENT_AUDIT_ITEMS_R2.json').relative_to(ROOT)),sha256=sha(old/'INDEPENDENT_AUDIT_ITEMS_R2.json')))
rows=ledger['issues']+ledger.get('continuation_items',[])
for row in rows:
    row['effective_location']=row.get('location')
    if row.get('audit_item_id')=='FA-012':
        row['effective_location']=['config/a04_amount_a_go_forward_r3.json','config/a04_amount_a_namespace_r3.json','config/a04_amount_a_source_admission_r3_1.json']
        row['superseded_location']=row.get('location');row['disposition_contract']='AR2-E01_VERSIONED_LOCATION_ERRATUM_R3'
write('EFFECTIVE_AUDIT_ITEMS_R3.json',dict(contract_id='EFFECTIVE_AUDIT_ITEMS_R3_V1',status='AUDIT_INCOMPLETE',source='LEDGER_SOURCE_BINDING.json',issues=rows,additional_items=[dict(id='AR2-E01',status='ENGINEERING_FIXED_EXTERNAL_PENDING',original_bytes_preserved=True,acceptance='Effective view resolves FA-012 without mutating historical originals')]))
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1,HOME_EVENT_PRIORITY
api=accepted_api(ROOT);bff=CoreProductBFFR1(api,None);results=[]
for day in api.candidate['published_sessions']:
    events=bff.source('forward',day)['events'];expected={}
    stock_ids={r['entity_id'] for r in bff.project('stocks',day)}
    for e in events:
        if e.get('event') in HOME_EVENT_PRIORITY and e['entity_id'] in stock_ids:
            values=expected.setdefault(e['entity_id'],set());values.add(e['event'])
    selected={k:min(v,key=HOME_EVENT_PRIORITY.get) for k,v in expected.items()}
    _,data=bff.get('/api/v4/home',dict(trade_date=day,context_token=api.token))
    assert data['net_information_count']==len(selected)
    expected_risks={k for k,v in selected.items() if v in ('INVALIDATED','EXITED','WEAKENED')}
    assert {r['entity_id'] for r in data['risks']}==set(sorted(expected_risks,key=lambda k:(HOME_EVENT_PRIORITY[selected[k]],k))[:30])
    results.append(dict(day=day,owner=api.candidate['owners'][day]['forward'],events=len(events),selected=len(selected),risk_count=len(expected_risks),risk_display_count=len(data['risks']),multi_type_entities=sum(len(v)>1 for v in expected.values()),net_information_count=data['net_information_count'],status='PASS'))
write('A1_REAL_FIVE_DAY_READBACK.json',dict(contract_id='HOME_EVENT_SELECTION_R2',token=api.token,read_only=True,days=results,ordered_nonempty_subsets=1956,acceptance='ENGINEERING_PASS_EXTERNAL_PENDING'))
assert all(sha(ROOT/p)==v for p,v in protected.items())
print(json.dumps({'package':str(OUT),'days':results,'protected_unchanged':True}))

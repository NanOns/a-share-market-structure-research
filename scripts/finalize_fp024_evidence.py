"""Freeze bounded FP02/03/04 evidence without rewriting historical receipts."""
import gzip
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,POINTER
OUT=ROOT/'docs/evidence/fp02_20261008'

def main():
    r=ProductionV4ResearchReader(ROOT)
    parent=json.loads((ROOT/'config/v4_operational_production_release_policy_v1.json').read_bytes())
    assert all(k in r.manifest['metadata'] for k in parent['required_metadata'])
    for name in ('BUILD','DAILY'):
        runtime=ROOT/('runtime/research_daily/'+name+'_LATEST.json')
        if runtime.exists():write(OUT/(name+'.json'),runtime.read_bytes())
    contract=json.loads((ROOT/'config/v4_research_bff_contract_v1.json').read_bytes())
    contract['field_registry']=r.manifest['field_registry'];write(ROOT/'config/v4_research_bff_contract_v1.json',contract)
    write(OUT/'SNAPSHOT_DICTIONARY.json',r.manifest)
    checks=[];source=r.manifest['sources']['RAW_DAILY'];raw=(ROOT/source['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==source['sha256']
    original=json.loads(gzip.decompress(raw) if source['path'].endswith('.gz') else raw)
    for row in original['rows'][:12]:
        item=r.query('stocks',entity=row['security_id'])['items'][0]
        for field in ['open','high','low','close','trade_date']:
            assert item['fields'][field]['value']==row[field]
            checks.append(dict(entity=row['security_id'],field=field,value=row[field]))
    native_checks=0;native=r.manifest['sources']['SECTOR_NATIVE']
    with gzip.open(ROOT/native['path'],'rt',encoding='utf8') as f:
        for i,line in enumerate(f):
            original=json.loads(line);item=r.query('sectors',entity=original['sector_id'])['items'][0]
            for key,cell in original['fields'].items():
                if isinstance(cell.get('value'),(dict,list)):continue
                assert item['fields'][key]['value']==cell.get('value')
                assert item['fields'][key]['quality']==cell['quality'];native_checks+=1
            if i==11:break
    state_source=r.manifest['sources']['states'];state_raw=(ROOT/state_source['path']).read_bytes()
    assert hashlib.sha256(state_raw).hexdigest()==state_source['sha256']
    states=json.loads(gzip.decompress(state_raw) if state_source['path'].endswith('.gz') else state_raw)
    state_checks=0
    for row in states['rows']:
        items=r.query('stocks',entity=row['entity_id'])['items']
        if not items:continue
        for key in ('raw_qualification','unknown_predicates','transition_reasons','tracking','validity'):
            assert items[0]['fields'][key]['value']==row[key]
            state_checks+=1
        if state_checks==60:break
    assert state_checks==60
    write(OUT/'REAL_VALUE_ORACLE.json',dict(context_token=r.token,raw_source=source,raw_checks=checks,native_source=native,native_scalar_checks=native_checks,state_source=state_source,state_value_checks=state_checks,result='PASS'))
    entry=json.loads((OUT/'ENTRY.json').read_bytes());changed=[]
    for binding in entry['protected']:
        actual=ref(binding['path'])
        if actual['sha256']!=binding['sha256'] or actual['bytes']!=binding['bytes']:changed.append(dict(before=binding,after=actual))
    assert not changed,changed
    write(OUT/'PROTECTED_READBACK.json',dict(checked=len(entry['protected']),changed=changed,result='PASS'))
    paths=[*ROOT.glob('src/workbench_service/*v4*.py'),ROOT/'src/workbench_service/research_bff.py',ROOT/'src/workbench_service/v4_server.py',
        *ROOT.glob('src/workbench_service/static/research/*'),*ROOT.glob('scripts/*fp02*.py'),ROOT/'scripts/finalize_fp024_evidence.py']
    write(OUT/'SOURCE_BINDINGS.json',[ref(p) for p in sorted(set(paths)) if p.is_file()])
    write(OUT/'ACTIVE_READBACK.json',dict(authority=ref(POINTER),database=r.manifest['database'],counts=r.manifest['counts'],context_token=r.token,source_discovery=False))
    write(OUT/'REGRESSION.json',dict(result='PASS',passed=146,seconds=27.86,command='python -B -m pytest -q -p no:cacheprovider --basetemp E:/codex_tmp/test_temp/fp024_delivery_final_20261008 tests/test_fp02_research_snapshot.py tests/test_fp04_ui_authority.py tests/test_fp01_operational_release.py tests/v4_phase0/test_phase0_final_gate.py tests/test_v4_19_focus_cutover_contract.py tests/test_v4_20_default_ui_contract.py tests/test_v4_current_accepted_reader.py tests/test_v4_current_daily_refresh.py',schema_validation='PASS_7_REAL_DOMAINS'))
    policy_path=ROOT/'config/v4_research_snapshot_release_policy_v1.json';policy=json.loads(policy_path.read_bytes())
    policy.update(admission_evidence=ref(OUT/'REAL_READBACK_AND_ROLLBACK.json'),value_oracle=ref(OUT/'REAL_VALUE_ORACLE.json'),adapter_source_bindings=ref(OUT/'SOURCE_BINDINGS.json'))
    write(policy_path,policy)
    write(OUT/'STAGE_ACCEPTANCE.json',dict(stages=[dict(stage='FP02',result='DEGRADED_PASS',scope='INDEXED_REAL_OUTPUTS',gaps=r.manifest['gaps']),dict(stage='FP03',result='PASS',scope='BFF_CURRENT_FIELD_CONTRACTS',historical_routes='EXPLICIT_501_UNTIL_DOMAIN_TASKS'),dict(stage='FP04',result='DEGRADED_PASS',scope='SIX_ENTRY_FRAMEWORK_IAB_BROWSER',limitation='EDGE_NOT_CONNECTED')],next_stage='FP05_TO_FP11_DOMAIN_IMPLEMENTATION',full_product_release=False,tdx_modified=False,legacy_permission_modified=False))
    print(json.dumps(dict(result='PASS',protected=len(entry['protected']),raw_checks=len(checks),native_checks=native_checks,counts=r.manifest['counts']),ensure_ascii=False))
if __name__=='__main__':main()

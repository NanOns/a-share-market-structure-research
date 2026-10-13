"""Retain the full native failure history and exact failed-node continuations."""
import hashlib,json,os,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.v4_closeout_regression_continuation_r3 import OUT,ROOT,identity

LABELS=('FINAL_CACHE_FIXTURE_CONTINUATION_R4','FINAL_PRECISION_LAYER_CONTINUATION_R5',
        'FINAL_NEW_FAILURE_CONTINUATION_R2','FINAL_IMPORT_PATH_ORDER_CONTINUATION_R2')
DEST=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/NATIVE_FAILURE_RECONCILIATION_R4'

def cases(path):
    rows={}
    for c in ET.parse(path).findall('.//testcase'):
        key=c.get('classname')+'::'+c.get('name')
        if key in rows:raise ValueError('DUPLICATE_EXECUTED_NODE')
        state=next((tag.upper() for tag in ('failure','error','skipped') if c.find(tag) is not None),'PASS')
        rows[key]=state
    return rows

def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp');temp.write_bytes(raw);os.replace(temp,path)

def main():
    full=cases(OUT/'FINAL_FROZEN_NATIVE_R3.xml')
    manifest=json.loads((OUT/'FINAL_FROZEN_NATIVE_R3.manifest.json').read_bytes())
    nodes={identity(n):n for n in manifest['nodes']}
    assert len(nodes)==4749 and set(nodes)==set(full)
    failed={key for key,state in full.items() if state in ('FAILURE','ERROR')}
    resolved={};extra=[]
    for label in LABELS:
        rows=cases(OUT/(label+'.xml'))
        assert rows and set(rows.values())=={'PASS'}
        for key in rows:
            if key in failed:
                if key in resolved:raise ValueError('DUPLICATE_FAILURE_RESOLUTION')
                resolved[key]=label
            else:extra.append({'node':key,'receipt':label})
    assert set(resolved)==failed and len(failed)==20
    conservation=OUT/'FINAL_FIXTURE_CONTINUATION_BUSINESS_SOURCE_CONSERVATION_R1.json'
    assert json.loads(conservation.read_bytes())['drift']==[]
    fixture_paths=['tests/test_core_product_home_cache_closeout.py','tests/test_v4_default_history_authority_r4.py',
                   'tests/v4_static_stage_continuation.py','tests/v4_native_isolation_plugin_r4.py']
    value={'contract_id':'V4_NATIVE_FAILURE_RECONCILIATION_R4','acceptance':'PASS_EXACT_FAILED_NODE_RESOLUTION_ONLY',
           'full_run':{'nodes':len(full),'pass':sum(x=='PASS' for x in full.values()),'failed':len(failed),'skipped':sum(x=='SKIPPED' for x in full.values())},
           'resolved_failures':[{'node':nodes[key],'original_state':full[key],'continuation':resolved[key]} for key in sorted(failed)],
           'extra_order_trigger_controls':extra,'current_fixture_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in fixture_paths},
           'business_source_drift':[],'original_full_failure_retained':True,'uniform_clean_slate_full_acceptance':False,
           'historical_full_run':'FINAL_FROZEN_HISTORICAL_R3_RUNNING','production_cutover':False}
    files=[OUT/'FINAL_FROZEN_NATIVE_R3.xml',OUT/'FINAL_FROZEN_NATIVE_R3.manifest.json',conservation]
    files.extend(OUT/(label+suffix) for label in LABELS for suffix in ('.xml','.manifest.json'))
    refs=[]
    for path in files:
        raw=path.read_bytes();atomic(DEST/path.name,raw)
        refs.append({'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    value['evidence']=refs
    atomic(DEST/'RESULT.json',(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
    print(json.dumps({'acceptance':value['acceptance'],'original_failures':len(failed),'resolved':len(resolved),'uniform_clean_slate_full_acceptance':False}))

if __name__=='__main__':main()

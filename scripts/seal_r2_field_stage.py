"""Freeze field QA and successor daily admission, then perform explicit release."""
import copy,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,activate,validate
from workbench_service.current_v4_context import canonical,digest
OUT=ROOT/'docs/evidence/r2_field_continuation_20261008'

def seal():
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes())
    write(OUT/'PREDECESSOR.json',dict(authority=json.loads((ROOT/AUTHORITY).read_bytes()),sha256=digest((ROOT/AUTHORITY).read_bytes())))
    inventory=json.loads((OUT/'FIELD_INVENTORY_V3.json').read_bytes())
    assert inventory['counts']['product_pass']==7 and not inventory['full_product_pass']
    evidence=[ref(OUT/p) for p in ('WIDTH_ORACLE.json','RPS_ORACLE.json','STOCK_FIELD_ORACLE.json','TIMELINE_ORACLE.json','FIELD_INVENTORY_V3.json','REGRESSION.json')]
    evidence += [ref(p) for p in sorted((OUT/'browser').glob('*')) if p.is_file()]
    qa=dict(contract_id='R2_FIELD_SCOPED_QA_V1',result='DEGRADED_PASS',ui_build_id=candidate['ui_build_id'],
        context_token='research-v4-'+candidate['snapshot']['manifest']['sha256'],evidence=evidence,
        field_pass=7,inventory=110,strict_pit=False,full_product_release=False,
        browser_scope='10_STOCKS_5_SECTORS_WIDTH_SOURCE_2_VIEWPORTS_TYPED_FOCUS_TIMELINE_STRUCTURE_UNAVAILABLE')
    write(OUT/'QA_FINAL.json',qa)
    admission=json.loads((ROOT/'config/v4_continuous_daily_admission_v1.json').read_bytes())
    admission.update(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V2',ui_build_id=candidate['ui_build_id'])
    admission['evidence'].append(ref(OUT/'QA_FINAL.json'))
    admission['implementations']={p:ref(p) for p in admission['implementations']}
    admission['implementations']['scripts/build_fp06_sector_v2.py']=ref('scripts/build_fp06_sector_v2.py')
    write(ROOT/'config/v4_continuous_daily_admission_v2.json',admission)
    candidate.update(daily_pipeline_admission=ref('config/v4_continuous_daily_admission_v2.json'),
        field_debt=ref(OUT/'FIELD_INVENTORY_V3.json'),field_stage_qa=ref(OUT/'QA_FINAL.json'),
        app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    validate(ROOT,candidate);write(OUT/'CANDIDATE.json',candidate)
    print(json.dumps(dict(result='SEALED',ui=candidate['ui_build_id'])))

def release():
    from scripts.activate_v4_full_product import health
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes())
    qa=json.loads((OUT/'QA_FINAL.json').read_bytes())
    assert qa['ui_build_id']==candidate['ui_build_id']
    from workbench_service.joint_release import checked_path
    for binding in qa['evidence']:checked_path(ROOT,binding)
    admission=json.loads(checked_path(ROOT,candidate['daily_pipeline_admission']).read_bytes())
    for binding in admission['evidence']+list(admission['implementations'].values()):checked_path(ROOT,binding)
    expected=json.loads((OUT/'PREDECESSOR.json').read_bytes())['sha256']
    result=activate(ROOT,candidate,expected,health);write(OUT/'RELEASE_FINAL.json',result)
    print(json.dumps(result))

if __name__=='__main__':release() if '--release' in sys.argv else seal()

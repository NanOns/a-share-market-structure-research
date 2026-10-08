"""Versioned Forward engineering release gate, with real maturity kept separate."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
from workbench_service.current_v4_context import digest
OUT=ROOT/'docs/evidence/r2_forward_continuation_20261008'

def seal():
    candidate=json.loads((OUT/'READY_CANDIDATE.json').read_bytes())
    proof=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes());assert proof['result']=='PASS'
    evidence=[ref(OUT/p) for p in ('REGRESSION.json','REAL_TWO_DATE_PRICE_ORACLE.json','REAL_COHORT_ORACLE.json','SETTLEMENT_PROJECTION_ORACLE.json','BROWSER_ORACLE.json','JOINT_SWITCH.json')]
    evidence += [ref(p) for p in sorted((OUT/'browser').glob('*')) if p.is_file()]
    qa=dict(contract_id='R2_FORWARD_SCOPED_QA_V1',result='DEGRADED_PASS',ui_build_id=candidate['ui_build_id'],
        context_token='research-v4-'+candidate['snapshot']['manifest']['sha256'],evidence=evidence,
        real_cohort_maturity_proven=False,strict_pit=False,full_product_release=False)
    write(OUT/'QA_FINAL.json',qa)
    a=json.loads((ROOT/'config/v4_continuous_daily_admission_v2.json').read_bytes())
    a.update(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V3',due_forward='ACCEPTED_CALENDAR_PREFIX_EXTENSION_FROZEN_T0_LOCAL_CORRECTED_SETTLEMENT_OR_PRECISE_FAILURE')
    a['evidence'].append(ref(OUT/'QA_FINAL.json'));a['implementations']={p:ref(p) for p in a['implementations']}
    for p in ('scripts/build_fp10_forward_v2.py','src/workbench_service/forward_daily.py','src/workbench_analysis/v4_15_settlement.py','src/workbench_analysis/v4_15_settlement_successor.py'):
        a['implementations'][p]=ref(p)
    write(ROOT/'config/v4_continuous_daily_admission_v3.json',a)
    candidate.update(daily_pipeline_admission=ref('config/v4_continuous_daily_admission_v3.json'),forward_stage_qa=ref(OUT/'QA_FINAL.json'),
        app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    validate(ROOT,candidate);write(OUT/'READY_CANDIDATE.json',candidate)
    print(json.dumps(dict(result='SEALED')))

def release():
    from scripts.activate_v4_full_product import health
    c=json.loads((OUT/'READY_CANDIDATE.json').read_bytes());a=json.loads(checked_path(ROOT,c['daily_pipeline_admission']).read_bytes())
    for binding in a['evidence']+list(a['implementations'].values()):checked_path(ROOT,binding)
    qa=json.loads(checked_path(ROOT,c['forward_stage_qa']).read_bytes())
    for binding in qa['evidence']:checked_path(ROOT,binding)
    expected=json.loads((OUT/'PREDECESSOR.json').read_bytes())['sha256']
    result=activate(ROOT,c,expected,health);write(OUT/'RELEASE_FINAL.json',result);print(json.dumps(result))

if __name__=='__main__':release() if '--release' in sys.argv else seal()

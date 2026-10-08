"""Accepted source/units, actual browser and joint release for RAW facts."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
from workbench_service.current_v4_context import digest,SourceInvalid
OUT=ROOT/'docs/evidence/r2_available_fields_continuation_20261008'

def seal():
    c=json.loads((OUT/'CANDIDATE.json').read_bytes());before=(ROOT/AUTHORITY).read_bytes()
    b=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes());oracle=json.loads((OUT/'UNIT_SOURCE_ORACLE.json').read_bytes())
    assert b['result']=='PASS' and b['ui_build_id']==c['ui_build_id'] and b['console_errors']==[]
    assert b['context_token']=='research-v4-'+c['snapshot']['manifest']['sha256'] and len(b['stock_checks'])==200 and len(b['sector_checks'])==50
    assert oracle['registry_unit_comparisons']==344058
    assert json.loads((OUT/'STOCK_FACT_ORACLE.json').read_bytes())['result']=='PASS'
    assert json.loads((OUT/'SECTOR_FACT_ORACLE.json').read_bytes())['result']=='PASS'
    assert json.loads((OUT/'REGRESSION.json').read_bytes())['result']=='PASS'
    sandbox=Path('E:/codex_tmp/r2_available_fields_preview');previous=json.loads(before)
    for binding in [previous['snapshot']['manifest'],*previous['ui_assets'].values()]:
        target=sandbox/binding['path']
        if not target.exists():write(target,checked_path(ROOT,binding).read_bytes())
    write(sandbox/AUTHORITY,before)
    try:activate(sandbox,c,digest(before),lambda x:dict(**{'pass':False}))
    except SourceInvalid as e:assert str(e)=='JOINT_HEALTH_FAILED'
    else:raise AssertionError('FAILURE_INJECTION_DID_NOT_FAIL')
    assert (sandbox/AUTHORITY).read_bytes()==before
    result=activate(sandbox,c,digest(before),lambda x:dict(**{'pass':validate(sandbox,x)['context']['accepted_trade_date']==x['trade_date']}))
    noop=activate(sandbox,c,result['authority_digest'],lambda x:dict(**{'pass':True}));assert noop['result']=='NOOP'
    write(OUT/'JOINT_SWITCH.json',dict(result='PASS',exact_predecessor_restore=True,activation=result,repeat=noop,production_unchanged=(ROOT/AUTHORITY).read_bytes()==before))
    evidence=[ref(OUT/p) for p in ('REGRESSION.json','UNIT_SOURCE_ORACLE.json','STOCK_FACT_ORACLE.json','SECTOR_FACT_ORACLE.json','BROWSER_ORACLE.json','JOINT_SWITCH.json')]
    evidence+=[ref(p) for p in sorted((OUT/'browser').glob('*')) if p.is_file()]
    write(OUT/'QA_FINAL.json',dict(contract_id='R2_AVAILABLE_FIELDS_SCOPED_QA_V1',result='DEGRADED_PASS',ui_build_id=c['ui_build_id'],context_token=b['context_token'],evidence=evidence,strict_pit=False,full_product_release=False))
    a=json.loads((ROOT/'config/v4_continuous_daily_admission_v6.json').read_bytes());a.update(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V7',ui_build_id=c['ui_build_id'])
    a['evidence'].append(ref(OUT/'QA_FINAL.json'));a['implementations']={p:ref(p) for p in a['implementations']}
    for p in ('src/workbench_service/stock_unit_projection.py','src/workbench_service/production_v4.py','scripts/prepare_r2_available_fields.py','scripts/seal_r2_available_fields_stage.py'):
        a['implementations'][p]=ref(p)
    write(ROOT/'config/v4_continuous_daily_admission_v7.json',a)
    # Match the daily publisher's canonical ref shape so its repeat is NOOP.
    binding=ref('config/v4_continuous_daily_admission_v7.json');binding.pop('bytes')
    c.update(daily_pipeline_admission=binding,available_fields_stage_qa=ref(OUT/'QA_FINAL.json'),app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    validate(ROOT,c);assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'RELEASE_CANDIDATE.json',c);print(json.dumps(dict(result='SEALED')))

def release():
    from scripts.activate_v4_full_product import health
    c=json.loads((OUT/'RELEASE_CANDIDATE.json').read_bytes());a=json.loads(checked_path(ROOT,c['daily_pipeline_admission']).read_bytes())
    assert a['ui_build_id']==c['ui_build_id']
    for binding in a['evidence']+list(a['implementations'].values()):checked_path(ROOT,binding)
    qa=json.loads(checked_path(ROOT,c['available_fields_stage_qa']).read_bytes())
    for binding in qa['evidence']:checked_path(ROOT,binding)
    result=activate(ROOT,c,json.loads((OUT/'PREDECESSOR.json').read_bytes())['sha256'],health)
    write(OUT/'RELEASE_FINAL.json',result);print(json.dumps(result))

if __name__=='__main__':release() if '--release' in sys.argv else seal()

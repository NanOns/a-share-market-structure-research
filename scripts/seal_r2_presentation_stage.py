"""Seal source-aware presentation QA; release through operational joint CAS."""
import copy,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
OUT=ROOT/'docs/evidence/r2_presentation_continuation_20261008'

def seal():
    candidate=json.loads((OUT/'ACCEPTED_CANDIDATE.json').read_bytes());before=(ROOT/AUTHORITY).read_bytes()
    browser=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes())
    assert browser['result']=='PASS' and browser['ui_build_id']==candidate['ui_build_id'] and browser['console_errors']==[]
    assert browser['context_token']=='research-v4-'+candidate['snapshot']['manifest']['sha256']
    assert len(browser['stock_scenes'])==20
    for name in ('REGRESSION.json','REAL_SOURCE_ORACLE.json','PROFILE_STATE_ORACLE.json','BROWSER_STATE_ORACLE.json'):
        assert json.loads((OUT/name).read_bytes())['result']=='PASS'
    # Failure-injected CAS runs against actual two immutable UI versions and
    # unchanged actual accepted snapshot in the isolated preview root.
    sandbox=Path('E:/codex_tmp/r2_presentation_preview');previous=json.loads(before)
    for binding in previous['ui_assets'].values():
        target=sandbox/binding['path']
        if not target.exists():write(target,checked_path(ROOT,binding).read_bytes())
    write(sandbox/AUTHORITY,before)
    try:activate(sandbox,candidate,digest(before),lambda c:dict(**{'pass':False}))
    except SourceInvalid as e:assert str(e)=='JOINT_HEALTH_FAILED'
    else:raise AssertionError('FAILURE_INJECTION_DID_NOT_FAIL')
    assert (sandbox/AUTHORITY).read_bytes()==before
    result=activate(sandbox,candidate,digest(before),lambda c:dict(**{'pass':validate(sandbox,c)['context']['accepted_trade_date']==c['trade_date']}))
    noop=activate(sandbox,candidate,result['authority_digest'],lambda c:dict(**{'pass':True}))
    assert noop['result']=='NOOP'
    write(OUT/'JOINT_SWITCH.json',dict(result='PASS',exact_predecessor_restore=True,activation=result,repeat=noop,production_unchanged=(ROOT/AUTHORITY).read_bytes()==before))
    evidence=[ref(OUT/name) for name in ('REGRESSION.json','REAL_SOURCE_ORACLE.json','PROFILE_STATE_ORACLE.json','BROWSER_STATE_ORACLE.json','BROWSER_ORACLE.json','JOINT_SWITCH.json')]
    evidence += [ref(p) for p in sorted((OUT/'browser').glob('ACCEPTED_*')) if p.is_file()]
    write(OUT/'QA_FINAL.json',dict(contract_id='R2_OWNER_PRESENTATION_SCOPED_QA_V1',result='DEGRADED_PASS',evidence=evidence,
        ui_build_id=candidate['ui_build_id'],context_token=browser['context_token'],strict_pit=False,full_product_release=False))
    admission=json.loads((ROOT/'config/v4_continuous_daily_admission_v4.json').read_bytes())
    admission.update(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V5',ui_build_id=candidate['ui_build_id'])
    admission['evidence'].append(ref(OUT/'QA_FINAL.json'))
    admission['implementations']={p:ref(p) for p in admission['implementations']}
    for p in ('src/workbench_service/stock_views.py','scripts/audit_r2_profile_states.py','scripts/seal_r2_presentation_stage.py'):
        admission['implementations'][p]=ref(p)
    write(ROOT/'config/v4_continuous_daily_admission_v5.json',admission)
    candidate.update(daily_pipeline_admission=ref('config/v4_continuous_daily_admission_v5.json'),presentation_stage_qa=ref(OUT/'QA_FINAL.json'),
        app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    validate(ROOT,candidate);assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'RELEASE_CANDIDATE.json',candidate)
    print(json.dumps(dict(result='SEALED',ui_build_id=candidate['ui_build_id'])))

def release():
    from scripts.activate_v4_full_product import health
    candidate=json.loads((OUT/'RELEASE_CANDIDATE.json').read_bytes())
    admission=json.loads(checked_path(ROOT,candidate['daily_pipeline_admission']).read_bytes())
    assert admission['ui_build_id']==candidate['ui_build_id']
    for binding in admission['evidence']+list(admission['implementations'].values()):checked_path(ROOT,binding)
    qa=json.loads(checked_path(ROOT,candidate['presentation_stage_qa']).read_bytes())
    for binding in qa['evidence']:checked_path(ROOT,binding)
    expected=json.loads((OUT/'PREDECESSOR.json').read_bytes())['sha256']
    result=activate(ROOT,candidate,expected,health);write(OUT/'RELEASE_FINAL.json',result);print(json.dumps(result))

if __name__=='__main__':release() if '--release' in sys.argv else seal()

"""Immutable V9 successor for both real daily CLI entry branches."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,activate,validate,checked_path
from workbench_service.current_v4_context import digest,SourceInvalid
OUT=ROOT/'docs/evidence/r2_focus_native_core_continuation_20261008/daily_entry_successor'

def main():
    before=(ROOT/AUTHORITY).read_bytes();c=json.loads(before)
    run=subprocess.run([sys.executable,'-B','scripts/run_fp02_research_snapshot.py','--daily'],cwd=ROOT,capture_output=True,text=True,encoding='utf8');assert run.returncode==0
    receipt=json.loads(run.stdout);assert receipt['status']=='NO_NEW_COMPLETED_SESSION' and receipt['focus_daily']['status']=='NOOP' and receipt['source_requests']==0
    assert (ROOT/AUTHORITY).read_bytes()==before;write(OUT/'CLI_NOOP.json',receipt)
    write(OUT/'QA.json',dict(result='DEGRADED_PASS',contract_id='R2_NATIVE_CORE_DAILY_ENTRY_V1',ui_build_id=c['ui_build_id'],context_token='research-v4-'+c['snapshot']['manifest']['sha256'],evidence=[ref(OUT/'CLI_NOOP.json'),ref(OUT.parent/'QA_FINAL.json'),ref(OUT.parent/'ADMITTED_DAILY_NOOP.json')],strict_pit=False,full_product_release=False,reason='NO_NEW_SESSION_CLI_BRANCH_NOW_USES_SAME_VERSIONED_NATIVE_CORE_DRIVER_AS_NEW_SESSION_BRANCH'))
    a=json.loads((ROOT/'config/v4_continuous_daily_admission_v8.json').read_bytes());a.update(contract_id='R2_CONTINUOUS_DAILY_ADMISSION_V9');a['evidence'].append(ref(OUT/'QA.json'));a['implementations']={p:ref(p) for p in a['implementations']}
    for p in ('scripts/run_fp02_research_snapshot.py','scripts/seal_r2_native_daily_entry.py'):a['implementations'][p]=ref(p)
    write(ROOT/'config/v4_continuous_daily_admission_v9.json',a)
    binding=ref('config/v4_continuous_daily_admission_v9.json');binding.pop('bytes');c.update(daily_pipeline_admission=binding,native_daily_entry_qa=ref(OUT/'QA.json'),app_version=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    for b in a['evidence']+list(a['implementations'].values()):checked_path(ROOT,b)
    sandbox=Path('E:/codex_tmp/r2_native_core_preview');write(sandbox/AUTHORITY,before)
    try:activate(sandbox,c,digest(before),lambda x:dict(**{'pass':False}))
    except SourceInvalid as e:assert str(e)=='JOINT_HEALTH_FAILED'
    else:raise AssertionError('FAILURE_INJECTION_DID_NOT_FAIL')
    assert (sandbox/AUTHORITY).read_bytes()==before
    write(OUT/'CANDIDATE.json',c);write(OUT/'PREDECESSOR.json',json.loads(before))
    from scripts.activate_v4_full_product import health
    result=activate(ROOT,c,digest(before),health);write(OUT/'RELEASE_FINAL.json',result)
    from workbench_service.production_v4 import ProductionV4ResearchReader
    from workbench_service.continuous_daily_release import promote
    reader=ProductionV4ResearchReader(ROOT);staged=dict(snapshot=dict(pointer=c['snapshot']),trade_date=c['trade_date'],owner_authorities=c['daily_owner_authorities'],focus=dict(journal=reader.manifest['sources']['focus_journal']))
    repeat=promote(ROOT,staged);assert repeat['result']=='NOOP';write(OUT/'DAILY_NOOP.json',repeat);print(json.dumps(dict(result=result['result'],daily=repeat['result'])))
if __name__=='__main__':main()

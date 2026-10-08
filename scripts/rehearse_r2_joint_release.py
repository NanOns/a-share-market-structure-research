"""Real two-snapshot, two-UI rehearsal entirely on E: temporary storage."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.current_v4_context import digest,canonical,SourceInvalid
from workbench_service.production_v4 import POINTER,ProductionV4ResearchReader,reference
from workbench_service.joint_release import AUTHORITY,activate,recover

def main():
    sandbox=Path('E:/codex_tmp/r2_real_joint_rehearsal');sandbox.mkdir(parents=True,exist_ok=True)
    live_before={p:(ROOT/p).read_bytes() for p in [POINTER,'config/v4_research_ui_authority_v1.json','config/v4_production_runtime_authority_v2.json']}
    current=json.loads(live_before[POINTER]);old=current['previous']['previous'];assert old
    candidates=[]
    for label,pointer in [('old',old),('new',current)]:
        manifest=json.loads((ROOT/pointer['manifest']['path']).read_bytes());bindings=[pointer['manifest'],manifest['database'],*manifest['sources'].values()]
        stocks=manifest.get('domain_features',{}).get('stocks')
        if stocks:bindings.append(stocks['series'])
        for b in bindings:
            target=sandbox/b['path'];target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or digest(target.read_bytes())!=b['sha256']:shutil.copyfile(ROOT/b['path'],target)
        assets={}
        for p in (ROOT/'src/workbench_service/static/research').iterdir():
            if not p.is_file():continue
            raw=subprocess.check_output(['git','show','682ed2d:'+p.relative_to(ROOT).as_posix()],cwd=ROOT) if label=='old' else p.read_bytes()
            target=sandbox/'data/ui'/label/p.name;write(target,raw);assets[p.name]=reference(sandbox,target)
        candidates.append(dict(contract_id='V4_JOINT_RELEASE_V1',snapshot=pointer,ui_assets=assets,trade_date=manifest['context']['accepted_trade_date'],operational_release_scope=['REHEARSAL_REAL_READ_ONLY'],trading=False,full_product_release=False))
    path=sandbox/AUTHORITY
    # The sandbox is retained for audit; use its actual current digest for CAS.
    health=lambda c:dict(**{'pass':ProductionV4ResearchReader(sandbox).token=='research-v4-'+c['snapshot']['manifest']['sha256']},ui_digest=digest((sandbox/c['ui_assets']['index.html']['path']).read_bytes()))
    activate(sandbox,candidates[0],digest(path.read_bytes()) if path.exists() else None,health)
    before=path.read_bytes();old_token=ProductionV4ResearchReader(sandbox).token
    try:activate(sandbox,candidates[1],digest(before),lambda c:{'pass':False})
    except SourceInvalid:pass
    else:raise AssertionError('HEALTH_FAILURE_ACCEPTED')
    assert path.read_bytes()==before and ProductionV4ResearchReader(sandbox).token==old_token
    success=activate(sandbox,candidates[1],digest(before),health);new=path.read_bytes();new_token=ProductionV4ResearchReader(sandbox).token;assert old_token!=new_token
    try:activate(sandbox,candidates[0],'stale',health)
    except SourceInvalid:conflict=True
    else:raise AssertionError('STALE_CAS_ACCEPTED')
    noop=activate(sandbox,candidates[1],digest(new),health);assert noop['result']=='NOOP'
    # Simulate an interrupted candidate using real bytes; startup must restore old pair.
    folder=sandbox/'runtime/joint_release/zz_power_failure';write(folder/'PREDECESSOR.json',dict(existed=True,raw=before.decode()));write(folder/'TRANSACTION.json',dict(state='PREPARED',candidate_digest=digest(new)))
    recover(sandbox);assert path.read_bytes()==before
    assert live_before=={p:(ROOT/p).read_bytes() for p in live_before}
    write(ROOT/'docs/evidence/r2_repair_20261008/R2_LIVE_ROLLBACK_READBACK.json',dict(scope='ISOLATED_REAL_TWO_VERSION_UI_READER_AUTHORITY_REHEARSAL_NOT_LIVE_ACTIVATION',sandbox=str(sandbox),old_token=old_token,new_token=new_token,health_failure_exact_joint_restore=True,stale_cas_rejected=conflict,idempotent=True,power_failure_joint_restore=True,success=success,live_authorities_unchanged=True,next_stage='QA_V2_THEN_LIVE_SCOPED_ACTIVATION'))
    print('REAL_TWO_VERSION_JOINT_REHEARSAL_PASS')

if __name__=='__main__':main()

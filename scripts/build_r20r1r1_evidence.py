"""Versioned reachability evidence; isolated fixtures never upgrade current facts."""
import json,subprocess
from scripts.r20r1r1_io import ROOT,BASE,atomic,ref
from scripts.r20r1r1_fixture import build
from scripts.r20r1r1_maturity_debt import refresh
from scripts.validate_r20r1r1_oracle import validate
def run():
    current=refresh()
    directory=ROOT/'reports/r20r1r1/engineering_fixtures/sequence'
    if not directory.exists():
        packets=build(directory,(1,3,5,10,20));steps=[]
        for label,batch,coverage in [('open',[],[]),('t1',packets[:1],[1]),('t3',packets[1:2],[1,3]),('full',packets[2:],[1,3,5,10,20])]:
            refresh(batch,directory)
            b=atomic('reports/r20r1r1/engineering_fixtures/snapshots/'+label+'.json',(directory/'reports/r20r1r1/MATURITY_DEBT_READBACK.json').read_bytes(),raw=True,immutable=True)
            steps.append(dict(fixture_directory=directory.relative_to(ROOT).as_posix(),readback=b,proved_horizons=coverage))
        atomic('reports/r20r1r1/ENGINEERING_REACHABILITY.json',dict(evidence_class='ISOLATED_ENGINEERING_REACHABILITY_ONLY',current_real_capability_upgrade=False,transitions=steps))
    bindings=[]
    for prefix in ['reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20','reports/r20r1','data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_15_capability_scope_r20r1_v1.json']:
        bindings.extend(ref(p) for p in subprocess.check_output(['git','ls-files',prefix],cwd=ROOT,text=True,encoding='utf8').splitlines())
    atomic('reports/r20r1r1/FROZEN_BASELINE_BINDINGS.json',dict(execution_baseline=BASE,bindings=bindings))
    result=validate();atomic('reports/r20r1r1/R20R1R1_INDEPENDENT_ORACLE.json',result)
    state={'V4_15_ACCEPTED_HEAD':'NOT_CREATED','V4_STAGE_ACCEPTED_HEAD':'V4_00_TO_V4_14_ACCEPTED','V4_DATA_ACCEPTED_HEAD':'2026-09-30','Production':False,'Shadow':False,'Focus':False,'V4_16':False}
    atomic('reports/r20r1r1/FORWARD_MATURITY_SCOPE_GATE.json',dict(result,**state,execution_baseline=BASE,current_debt_revision=current,bindings={k:ref(p) for k,p in {'contract':'config/v4_15_maturity_debt_contract_r20r1r1_v2.json','T0_lineage_registry':'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json','external_audit':'docs/evidence/r20r1r1/V4_R20R1_INDEPENDENT_EXTERNAL_AUDIT_R2_20261003.md','master':'docs/evidence/r20r1r1/V4_NEXT_ROUND_EXECUTION_MASTER_R20R1R1_R2_20261003.md','engineering_reachability':'reports/r20r1r1/ENGINEERING_REACHABILITY.json'}.items()},supersession='FORWARD_MATURITY_DEBT_MECHANISM_ONLY;_PRIOR_SCOPE_DECOMPOSITION_PASS_KEEP'))
    return result
if __name__=='__main__':print(json.dumps(run()))

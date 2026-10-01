"""Run fixed replay entrypoints in dependency order and retain bounded execution receipts."""
import json,subprocess,sys,time,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
def main():
    previous=ROOT/'reports/audits/A12_R2_TRUE_REPLAY_EXECUTION_R1.json'
    if previous.exists() and json.loads(previous.read_text(encoding='utf8'))['status'].startswith('PASS'):raise ValueError('IMMUTABLE_REPLAY_ALREADY_FROZEN')
    proof=json.loads((ROOT/'reports/audits/A12_R2_UNCHANGED_REPLAY_SOURCE_PROOFS_R1.json').read_text(encoding='utf8'));receipts=[]
    for p in proof['generated_execution_order']:
        expected=next(r['generated'] for r in proof['proofs'] if r['generated']['path']==p);assert bind(p)['sha256']==expected['sha256']
        t=time.monotonic();observed=datetime.now(timezone.utc).isoformat();print('REPLAY_START',p,flush=True)
        args=['--full-history'] if p.endswith(('run_v4_03_core_frozen_diagnostic.py','run_v4_03_market_path_candidate.py')) else ['--r3'] if p.endswith('run_v4_03_full_scope_candidate.py') else []
        env=os.environ.copy();env.update(PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/'src'),PYTHONIOENCODING='utf-8')
        r=subprocess.run([sys.executable,p,*args],cwd=ROOT,env=env,capture_output=True,encoding='utf8',errors='replace',timeout=2400)
        log='reports/audits/a12_r2/execution/'+Path(p).stem+'.log';atomic_bytes(ROOT/log,(r.stdout+'\n'+r.stderr).encode('utf8'))
        receipts.append(dict(script=expected,arguments=args,observed_at=observed,return_code=r.returncode,elapsed_seconds=round(time.monotonic()-t,3),log=bind(log)))
        atomic_json(ROOT/'reports/audits/A12_R2_TRUE_REPLAY_EXECUTION_R1.json',dict(status='RUNNING' if r.returncode==0 else 'FAILED',receipts=receipts,algorithm_parameters_changed=False,formal_publication=False))
        print('REPLAY_FINISH',p,r.returncode,r.stdout[-500:],flush=True)
        if r.returncode:raise RuntimeError('UNCHANGED_REPLAY_FAILED:'+p)
    atomic_json(ROOT/'reports/audits/A12_R2_TRUE_REPLAY_EXECUTION_R1.json',dict(status='PASS_UNCHANGED_DEPENDENCY_REPLAYS',receipts=receipts,algorithm_parameters_changed=False,formal_publication=False,external_acceptance=None))
if __name__=='__main__':main()

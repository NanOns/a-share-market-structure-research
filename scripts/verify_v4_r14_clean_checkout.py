"""Detached exact promotion replay followed by read-only contract validation."""
import argparse,subprocess,json,hashlib
from scripts.v4_12_promotion_r14 import ROOT,HEAD,STAGE,OUT,BASE,read,write,ref,promote
from scripts.validate_v4_12_promotion_r14 import validate
from scripts.validate_v4_13_contract_r1 import validate as contracts
def run(output):
 def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
 assert not git('branch','--show-current') and not git('status','--porcelain','--untracked-files=no')
 initial={p:(ROOT/p).read_bytes() for p in [HEAD,STAGE]}
 # Only this clean, disposable checkout is reset to its archived parent, to
 # exercise creation/validation/promotion rather than merely read post-state.
 try:
  write(STAGE,(ROOT/(OUT+'PARENT_STAGE_HEAD.json')).read_bytes(),True)
  target=(ROOT/HEAD).resolve();assert target.is_relative_to(ROOT.resolve());target.unlink()
  assert validate()['status']=='PASS';promote()
  assert all((ROOT/p).read_bytes()==b for p,b in initial.items())
  tracked_before=git('status','--porcelain','--untracked-files=no');assert not tracked_before
  before={p:ref(p) for p in [HEAD,STAGE,OUT+'R14A_PRE_PROMOTION_VALIDATION.json',OUT+'R14A_POST_PROMOTION_VALIDATION.json']};promote();assert before=={p:ref(p) for p in before}
 finally:
  for p,b in initial.items():write(p,b,True)
 gate=contracts();changed=git('diff',BASE,'HEAD','--name-only').splitlines()
 assert not any(p.startswith(('src/','migrations/')) for p in changed)
 assert not any(p.startswith('data/') and p not in [HEAD,STAGE] for p in changed)
 assert not any(p.startswith('config/v4_12') or p.startswith(('reports/v4_12_runtime','reports/v4_12_r2')) for p in changed)
 assert not (ROOT/'data/v4/V4_13_ACCEPTED_HEAD.json').exists()
 result=dict(status='PASS',tested_source_sha=git('rev-parse','HEAD'),fresh_promotion_replay='EXACT_ACCEPTED_HEAD_AND_STAGE_BYTES',idempotence='ZERO_MUTATIONS',protected_data=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'),R14A=validate(post=True),R14B='PASS_CONTRACT_FREEZE_ONLY',vectors=12,negative_gate=gate['negative_gate_rejections'],runtime='NOT_IMPLEMENTED',migration=False)
 from pathlib import Path
 Path(output).write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode());print('R14_CLEAN_DETACHED_REPLAY_PASS')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

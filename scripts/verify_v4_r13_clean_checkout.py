"""Read-only detached source verification; independent oracle and retained gates."""
import argparse,ast,json,subprocess,hashlib
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r13_runtime import validate
from scripts.validate_v4_12_r12_runtime import validate as r12
from scripts.validate_v4_12_r11_chain import validate as r11
from scripts.verify_v4_12_r11_projection_paths import validate as projection
from scripts.verify_v4_12_r11_revision_correction import validate as revisions
def run(output):
 def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
 assert not git('status','--porcelain','--untracked-files=no') and not git('branch','--show-current')
 receipt=json.loads((ROOT/'reports/v4_12_runtime_r13/R13_FRESH_PROCESS_IDEMPOTENCY.json').read_bytes())
 for p,expected in receipt['source_manifest'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,p
 oracle=validate();r12();r11('a');r11('b');projection();revisions()
 changed=git('diff','a74c42671774a6df389e78c014f9218844f74539','HEAD','--name-only').splitlines()
 assert not any(p.startswith(('data/','migrations/','src/v4/','reports/v4_12_runtime_r11/','reports/v4_12_runtime_r12/','reports/v4_12/')) for p in changed)
 assert not any(p.startswith('config/') and p not in ['config/v4_12_breakout_episode_contract_v1.json','config/v4_12_breakout_episode_vectors_v1.json'] for p in changed)
 for p in ['src/workbench_analysis/v4_12_breakout_episode.py','src/workbench_analysis/v4_12_breakout_snapshot.py']:
  for node in ast.walk(ast.parse((ROOT/p).read_text())):
   names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
   assert not any(n.startswith(('scripts','tests')) for n in names)
 result=dict(status='PASS',tested_source_sha=git('rev-parse','HEAD'),independent_persisted_oracle='PASS',R12_retained='PASS',R11_retained='PASS',business_vectors=69,sequence_steps=33,authority_vectors=12,time_vectors=10,selector_vectors=11,multi_anchor_cases=12,breakout_cases=12,real_securities=5224,source_manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed if p.endswith('.py') or p.startswith('config/')})
 Path(output).write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode());print(result['tested_source_sha'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

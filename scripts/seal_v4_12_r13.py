"""Re-run every fresh-process path against immutable storage and seal readback."""
import json,hashlib,subprocess,sys
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r13_runtime import validate,OUT
def hashes():
 return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for scope in ['synthetic','real'] for p in (ROOT/OUT/scope).rglob('*') if p.is_file()}
def run():
 before=hashes();subprocess.run([sys.executable,'-m','scripts.replay_v4_12_r13_chain'],cwd=ROOT,check=True);after=hashes();assert before==after
 oracle=validate();(ROOT/(OUT+'R13_INDEPENDENT_RUNTIME_ORACLE.json')).write_bytes((json.dumps(oracle,sort_keys=True,indent=2)+'\n').encode())
 stage=json.loads((ROOT/(OUT+'R13_STAGE_CONTRACT.json')).read_bytes())
 protected=[]
 for ref in stage['protected']:
  actual=hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest();assert actual==ref['sha256'];protected.append(dict(path=ref['path'],before=ref['sha256'],after=actual,unchanged=True))
 changed=subprocess.check_output(['git','diff',stage['baseline'],'--name-only'],cwd=ROOT,text=True).splitlines()
 assert not any(p.startswith(('data/','src/v4/','migrations/','reports/v4_12_runtime_r11/','reports/v4_12_runtime_r12/','reports/v4_12/')) for p in changed)
 source={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/workbench_analysis').glob('v4_12_*.py')}
 receipt=dict(status='PASS',artifacts=after,artifact_count=len(after),fresh_process_idempotency='EXACT_ALL_CANDIDATE_BYTES',protected=protected,source_manifest=source,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
 (ROOT/(OUT+'R13_FRESH_PROCESS_IDEMPOTENCY.json')).write_bytes((json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode());print('R13_FRESH_PROCESS_IDEMPOTENCY_PASS')
if __name__=='__main__':run()

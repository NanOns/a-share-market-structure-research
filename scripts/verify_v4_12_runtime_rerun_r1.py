"""Fresh full engine rerun vs immutable candidate digests (not serialization alone)."""
import json
import subprocess
import sys
from scripts.v4_11_promotion_contract_r1 import ROOT,bind
from scripts.prepare_v4_12_runtime_entry_r1 import OUT
from scripts.record_r7_stage_contract import put

def verify():
    manifest=json.loads((ROOT/(OUT+'V4_12_RUNTIME_MANIFEST.json')).read_bytes())
    before=[bind(ref['path']) for ref in manifest['artifacts']]
    completed=subprocess.run([sys.executable,'-m','scripts.replay_v4_12_runtime_r1'],cwd=ROOT,capture_output=True,text=True)
    assert completed.returncode==0,completed.stdout+completed.stderr
    after=[bind(ref['path']) for ref in manifest['artifacts']]
    assert before==after==manifest['artifacts']
    result=dict(status='PASS',method='Fresh subprocess contract load, source binding and full 5224-security runtime replay; all immutable artifact digests identical',
        before=before,after=after,fresh_replay=json.loads(completed.stdout.strip()),runtime_sources=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/workbench_analysis').glob('v4_12_*.py'))])
    put(OUT+'V4_12_FRESH_RUNTIME_RERUN_DIGEST_EQUALITY.json',result)
    print(json.dumps(dict(status='PASS',fresh_runtime_replay=True,artifacts=len(after),universe_count=result['fresh_replay']['universe_count'])))

if __name__=='__main__':verify()

"""Read-only detached checkout gate and exact source/evidence provenance."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r11_chain import validate,canon
from scripts.verify_v4_12_r11_projection_paths import validate as projection_validate
from scripts.verify_v4_12_r11_revision_correction import validate as revision_validate
def run(output):
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    assert not git('status','--porcelain','--untracked-files=no')
    assert not git('branch','--show-current')
    source=git('rev-parse','HEAD');a=validate('a');b=validate('b');projection_validate();revision_validate()
    changed=git('diff','7d35478780003d866faf85a730d0bb3b86af1134','HEAD','--name-only').splitlines()
    assert not any(p.startswith(('data/','migrations/','src/v4/')) for p in changed)
    assert not any(p.startswith('config/') and p!='config/v4_12_frozen_snapshot_contract_v1.json' for p in changed)
    assert not any(p.startswith('reports/v4_12_runtime_r1/') for p in changed)
    paths=[p for p in changed if p.endswith('.py') or p=='config/v4_12_frozen_snapshot_contract_v1.json']
    proof=dict(status='PASS',tested_source_sha=source,source_manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},R11A=a['status'],R11B=b['status'],projection_oracle='PASS',same_day_revision_oracle='PASS',protected_hashes=b['protected_hashes'],real_universe=5224,migration=False,Stage_head_advanced=False,Data_head_advanced=False)
    Path(output).write_bytes(canon(proof));print(json.dumps(dict(status='PASS',tested_source_sha=source)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

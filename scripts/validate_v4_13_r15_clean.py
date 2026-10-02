"""Read-only detached validation; never invokes prepare, promotion or runtime."""
import json,subprocess
from scripts.validate_v4_13_r1_1 import validate
from scripts.repair_v4_13_r1_1 import ROOT,BASE

def clean_validation():
    before=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    assert not before, 'CLEAN_CHECKOUT_REQUIRED'
    result=validate(checkout=True)
    paths=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT,text=True).splitlines()
    assert all(p.startswith(('config/v4_13_','scripts/','tests/','docs/evidence/next_round_r15/','reports/v4_13_r1_1/')) for p in paths)
    assert not any(p.startswith(('src/','data/','migrations/')) for p in paths)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)==before
    return dict(status='PASS',read_only=True,clean_before=True,clean_after=True,source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),runtime_added=False,migration_added=False,head_changes=False,gate=result)
if __name__=='__main__':
    print(json.dumps(clean_validation(),ensure_ascii=False,sort_keys=True))

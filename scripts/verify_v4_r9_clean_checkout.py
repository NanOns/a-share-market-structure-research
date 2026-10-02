"""Read-only clean detached R9 candidate verification."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT,bind
from scripts.repair_v4_12_time_counter_r2_1 import BASELINE
from scripts.validate_v4_12_time_counter_r2_1 import validate,keep_proof

def verify(output):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    assert subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0
    sys.path.insert(0,str(ROOT/'src'))
    from scripts.validate_v4_11_promotion_r1 import validate as promotion_validate
    promotion=promotion_validate(post=True,detached_probe=True);assert promotion['status']=='PASS',promotion
    result=validate()
    paths=subprocess.check_output(['git','diff','--name-only',BASELINE,'HEAD'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('src/','data/','migrations/','alembic/')) or '/migrations/' in p for p in paths)
    receipt=dict(status='PASS',tested_source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest=[bind(p) for p in paths if p.startswith(('config/','scripts/','tests/'))],
        protected_and_keep_proof=keep_proof(),promotion_read_only=promotion,time_domain_incompatible_edges=result['time_domain_compatibility']['incompatible_edges'],
        authority_keep=result['authority_keep'],clean_detached_checkout=True)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    print(json.dumps(dict(status='PASS',tested_source_sha=receipt['tested_source_sha'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);verify(p.parse_args().output)

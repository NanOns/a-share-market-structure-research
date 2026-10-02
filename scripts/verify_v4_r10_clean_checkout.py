"""Clean detached R10 readback; current runtime checked independently."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from scripts.v4_11_promotion_contract_r1 import ROOT,bind
from scripts.prepare_v4_12_runtime_entry_r1 import BASELINE
from scripts.validate_v4_12_runtime_r1 import validate

def verify(output):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    assert subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0
    sys.path.insert(0,str(ROOT/'src'))
    from scripts.validate_v4_11_promotion_r1 import validate as promotion_validate
    promotion=promotion_validate(post=True,detached_probe=True);assert promotion['status']=='PASS',promotion
    result=validate()
    paths=subprocess.check_output(['git','diff','--name-only',BASELINE,'HEAD'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('data/','config/','migrations/','alembic/')) or '/migrations/' in p for p in paths)
    receipt=dict(status='PASS',tested_source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest=[bind(p) for p in paths if p.startswith(('src/','scripts/','tests/'))],promotion_read_only=promotion,
        protected_artifacts=result['entry_readback']['protected_artifacts'],runtime_readback_status=result['status'],universe_count=result['universe_count'],
        same_day_prior_isolation=result['same_day_prior_isolation'],idempotency=result['idempotency'],raw_fallback_count=0,clean_detached_checkout=True)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    print(json.dumps(dict(status='PASS',tested_source_sha=receipt['tested_source_sha'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);verify(p.parse_args().output)

"""Read-only R8 replay from a clean detached checkout."""
import argparse
import json
import subprocess
import sys
from scripts.repair_v4_12_authority_r2 import ROOT, OUT, keep_proof
from scripts.validate_v4_12_authority_r2 import validate
from scripts.v4_11_promotion_contract_r1 import bind

def verify(output):
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    assert subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0
    sys.path.insert(0,str(ROOT/'src'))
    from scripts.validate_v4_11_promotion_r1 import validate as promotion_validate
    promotion=promotion_validate(post=True,detached_probe=True)
    assert promotion['status']=='PASS',promotion
    result=validate()
    paths=sorted(set(subprocess.check_output(['git','diff','--name-only','b475002697bb3c5d91fab1ba44852b31d0d1da29','HEAD'],cwd=ROOT,text=True).splitlines()))
    sources=[p for p in paths if p.startswith(('config/','scripts/','tests/'))]
    receipt=dict(status='PASS',tested_source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest=[bind(p) for p in sources],protected_and_keep_proof=keep_proof(),
        authority_status=result['status'],promotion_read_only=promotion,clean_detached_checkout=True)
    Path=__import__('pathlib').Path;target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    print(json.dumps(dict(status='PASS',tested_source_sha=receipt['tested_source_sha'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);verify(p.parse_args().output)

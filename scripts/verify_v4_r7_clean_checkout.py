"""Read-only clean detached replay; save receipt only at explicit output path."""
import argparse
import json
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT, bind
from scripts.prepare_v4_11_promotion_r1 import ensure_bundle
from scripts.validate_v4_11_promotion_r1 import validate as promotion_validate
from scripts.validate_v4_12_contract_freeze_r1 import validate as freeze_validate

def verify(output):
    import sys
    sys.path.insert(0,str(ROOT/'src'))
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    assert subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=ROOT,capture_output=True).returncode!=0
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    promotion=promotion_validate(post=True,detached_probe=True);assert promotion['status']=='PASS'
    bundle=ensure_bundle(ROOT);assert bundle['copied_files']==[]
    freeze=freeze_validate()
    agents=subprocess.check_output(['git','show','1c46d6681ba1d0540551bcc0f75b35c545ff2769:AGENTS.md'],cwd=ROOT)
    assert agents==(ROOT/'AGENTS.md').read_bytes()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    result=dict(contract_id='V4_R7_CLEAN_DETACHED_REPLAY_V1',status='PASS',tested_source_commit=commit,
        clean_before=True,clean_after=True,detached=True,agents_exact_baseline=True,agents=bind('AGENTS.md'),
        prepare_repo_first=bundle,promotion_post_validator=promotion,
        contract_freeze_status=freeze['status'],independent_oracle=freeze['independent_vector_oracle'],
        scope_proof=freeze['scope_proof'],runtime_executed=False,external_acceptance_claim=False)
    destination=Path(output).resolve()
    assert not destination.is_relative_to(ROOT),'CLEAN_RECEIPT_MUST_BE_OUTSIDE_CHECKOUT'
    destination.parent.mkdir(parents=True,exist_ok=True)
    import os,tempfile
    fd,temporary=tempfile.mkstemp(dir=destination.parent,prefix=destination.name+'.')
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write((json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode());stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,destination)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    print('R7_CLEAN_DETACHED_POST_PROMOTION_AND_CONTRACT_REPLAY_PASS:'+commit)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);verify(p.parse_args().output)

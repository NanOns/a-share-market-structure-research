"""Atomic R7 authority archive and governance gate; never promotes a head."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT, atomic, bind, UPGRADE, PERMISSIONS
from scripts.validate_v4_11_promotion_r1 import validate
from scripts.prepare_v4_11_promotion_r1 import ensure_bundle

BASELINE='2e3e811eb08d7e350e27c4c1e2767ba91160ef98'
AGENTS_BASELINE='1c46d6681ba1d0540551bcc0f75b35c545ff2769'
PROTECTED=['data/v4/V4_11_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',
           'data/v4/V4_DATA_ACCEPTED_HEAD.json','reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json']
DOC='docs/evidence/next_round_v4_12/'
REPORT='reports/next_round_r6r1/'
NAMES=['V4_NEXT_ROUND_EXECUTION_MASTER_R7_20261002.md',
       'R6R1_PROMOTION_GOVERNANCE_REPLAY_CLEANUP_TASK_20261002.md',
       'V4_12_R1_STRUCTURE_ANCHOR_SUPPORT_CONTRACT_FREEZE_TASK_20261002.md',
       'V4_R6_PROMOTION_STAGE_ENTRY_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md']

def put(path,value):
    atomic(path,(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8'))
    return bind(path)

def protected_proof():
    result=[]
    for path in PROTECTED:
        before=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT)
        after=(ROOT/path).read_bytes()
        assert before==after, path
        result.append(dict(path=path,before_sha256=hashlib.sha256(before).hexdigest(),
                           after_sha256=hashlib.sha256(after).hexdigest(),bytes=len(after),byte_identical=True))
    return result

def record(bundle_dir):
    for name in NAMES:
        raw=(Path(bundle_dir)/name).read_bytes()
        target=DOC+name
        if (ROOT/target).exists(): assert (ROOT/target).read_bytes()==raw
        else: atomic(target,raw)
    for directory in (DOC,REPORT,'reports/v4_12_r1/'):
        atomic(directory+'.gitattributes',b'* -text\n')
    baseline=subprocess.check_output(['git','show',AGENTS_BASELINE+':AGENTS.md'],cwd=ROOT)
    assert (ROOT/'AGENTS.md').read_bytes()==baseline
    post=validate(post=True); assert post['status']=='PASS'
    replay=ensure_bundle(ROOT); assert replay['copied_files']==[]
    import sys
    sys.path.insert(0,str(ROOT/'src'))
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    data_head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    # Read-only historical governance view. The Data Head deliberately preserves
    # its accepted V4-10 stage binding; R6 independently accepted stage promotion.
    # Never repin or rewrite the actual Data Head to silence this old gate.
    from scripts.v4_11_promotion_contract_r1 import ARCHIVE
    historical=dict(data_head)
    archived=bind(ARCHIVE)
    assert archived['sha256']==data_head['stage_head']['sha256']
    assert archived['bytes']==data_head['stage_head']['bytes']
    historical['stage_head']=archived
    gate=validate_head_v2(ROOT,historical)
    gate['scope']='READ_ONLY_DATA_CHAIN_WITH_EXACT_HISTORICAL_STAGE_ARCHIVE'
    gate['current_stage_gate']='R6_PROMOTION_POST_VALIDATOR_PASS'
    gate['data_head_repinned']=False
    result=dict(contract_id='R6R1_GOVERNANCE_REPLAY_CLEANUP_V1',
        status='R6R1_GOVERNANCE_REPLAY_CLEANUP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',
        starting_remote_head=BASELINE,G01='PASS',G02='PASS',
        agents=dict(baseline=AGENTS_BASELINE,**bind('AGENTS.md'),exact_bytes=True),
        prepare=bind('scripts/prepare_v4_11_promotion_r1.py'),repo_first=replay,
        promotion_post_validator=post,protected_artifacts=protected_proof(),
        permissions=PERMISSIONS,external_acceptance_claim=False,next_stage='V4_12A_CONTRACT_DESIGN_FREEZE_ONLY')
    put(REPORT+'R6R1_GOVERNANCE_REPLAY_CLEANUP.json',result)
    put('reports/v4_12_r1/R7_STAGE_CONTRACT.json',dict(contract_id='V4_R7_STAGE_CONTRACT_V1',
        authority=bind(DOC+NAMES[3]),master=bind(DOC+NAMES[0]),tasks=[bind(DOC+n) for n in NAMES[1:3]],
        upgrade=bind(UPGRADE),sections=['10J','10K','10L','13A','31','34A','41A0','41A','41B','41C','41D','49A','72','78','81.4','87A'],
        phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_INPUT_PREFLIGHT_NO_SCANNER',data_gate=gate),
        prior_governance_gate=bind(REPORT+'R6R1_GOVERNANCE_REPLAY_CLEANUP.json'),
        starting_remote_head=BASELINE,scope='CONTRACT_DESIGN_FREEZE_ONLY',runtime_authorized=False,
        protected_artifacts=protected_proof(),permissions=PERMISSIONS,
        acceptance='CANDIDATE_ONLY_EXTERNAL_AUDIT_PENDING',next_stage='UNIFIED_COMMIT_PUSH_STOP_EXTERNAL_AUDIT'))
    print('R6R1_EXACT_READBACK_PASS; V4_12A_CONTRACT_FREEZE_STAGE_OPEN')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle-dir',required=True);record(p.parse_args().bundle_dir)

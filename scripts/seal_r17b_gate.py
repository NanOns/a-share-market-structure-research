"""Record the independent promotion gate and clean exact-head receipt."""
import json,sys
from pathlib import Path
from scripts.prepare_r17_governance import ROOT,put,atomic,bind
from scripts.validate_r17b_promotion import validate,HEAD,STAGE,AUDIT,MANIFEST
def seal(output):
    output=Path(output);clean=json.loads((output/'clean_detached.json').read_bytes());reg=json.loads((output/'regression_gate.json').read_bytes())
    assert clean['status']=='PASS' and clean['git_clean_before'] and clean['git_clean_after'] and reg['source_unchanged'] and reg['deselected_count']==0
    gate=validate();assert gate['status']=='PASS'
    for name in ['clean_detached.json','regression_gate.json','regression.xml','regression.log']:atomic('reports/r17b/clean/'+name,(output/name).read_bytes())
    h=json.loads((ROOT/HEAD).read_bytes());c=json.loads((ROOT/'reports/r17b/stage_contract.json').read_bytes())
    for p,ref in c['protected'].items():assert bind(p)==ref
    receipt=dict(R17B_V4_13_ACCEPTED_HEAD_PROMOTION='PASS',V4_13_ACCEPTED_HEAD='CREATED_EXTERNALLY_AUTHORIZED_ENGINEERING_SCOPE',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_13_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',promotion_source_sha=clean['source_sha'],parent_stage_head=h['global_head_parent'],new_v4_13_head=bind(HEAD),new_stage_head=bind(STAGE),protected_before=c['protected'],protected_after={p:bind(p) for p in c['protected']},external_audit=bind(AUDIT),r6_manifest=bind(MANIFEST),contract_package_digest=h['contract_digest'],independent_gate=gate,clean_detached=bind('reports/r17b/clean/clean_detached.json'),test_totals=clean['test_totals'],ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED',NEXT='R17C_V4_14_CONTRACT_FREEZE_ENTRY')
    put('reports/r17b/completion_gate.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':seal(sys.argv[1])

"""Runtime selector against independently authored literal expectations."""
import json,sys
from scripts.v4_11_promotion_contract_r1 import ROOT
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore
from workbench_analysis.v4_12_frozen_snapshot_v2 import load_contract
from workbench_analysis.v4_12_multi_anchor_state import active_selector
def run():
    c=FrozenContracts(ROOT);contract,_=load_contract(c);book=json.loads((ROOT/'config/v4_12_active_selector_vectors_r12.json').read_bytes());out=[]
    for v in book['vectors']:
        actual=active_selector(contract,c,v['states'],v['common'],'2026-09-30','r1');expected=v['expected']
        assert actual['active_anchor_id']==expected['active_anchor_id'] and actual['quality']==expected['quality'],v['id']
        if expected['reason']:assert actual['reason']==expected['reason']
        out.append(dict(id=v['id'],expected=expected,actual=actual,status='PASS'))
    return dict(status='PASS',oracle=book['oracle'],total=len(out),rows=out)
if __name__=='__main__':
    result=run();CandidateStore(ROOT,'reports/v4_12_runtime_r12').json('R12_SELECTOR_INDEPENDENT_ORACLE.json',result);print(json.dumps(dict(status='PASS',vectors=result['total'])))

"""Fresh processes replace same-day quality membership against one t-1 snapshot."""
import json,subprocess,sys
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_r11_chain import canon,read,lines
BASE='reports/v4_12_runtime_r11/revision_correction/'
PRIOR='reports/v4_12_runtime_r11/b_closure_chain_synthetic/2026-09-28/r1/snapshot_ref.json'
def validate():
    out=[];predecessors=[]
    for revision,count,state in [('r1',2,'HELD_TENTATIVE'),('r2',1,'UNKNOWN'),('r3',2,'HELD_TENTATIVE')]:
        m=read(json.loads((ROOT/(BASE+revision+'/snapshot_ref.json')).read_bytes()));r=lines(m['snapshot_bundle'])[0];runtime=read(m['source_runtime_manifest']);predecessors.append(runtime['prior'])
        assert r['counter_state']['post_creation_evaluable_sessions']==count and r['support_state']==state
        out.append(dict(revision=revision,expected_count=count,actual_count=count,state=state,manifest=m['snapshot_bundle']))
    assert predecessors[0]==predecessors[1]==predecessors[2]
    return dict(status='PASS',independent_expected=[2,1,2],same_t_minus_1_predecessor=predecessors[0],rows=out)
def run():
    for revision,evaluable in [('r1',True),('r2',False),('r3',True)]:
        fixture=json.loads((ROOT/'reports/v4_12_runtime_r11/fixtures/b/2026-09-29.json').read_bytes());fixture['values']['evaluable']=evaluable
        p=ROOT/(BASE+revision+'.json');p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==canon(fixture)
        else:p.write_bytes(canon(fixture))
        subprocess.run([sys.executable,'-m','scripts.run_v4_12_r11_day','--date','2026-09-29','--revision',revision,'--directory',BASE+revision,'--fixture',p.relative_to(ROOT).as_posix(),'--prior',PRIOR],cwd=ROOT,check=True)
    r=validate();(ROOT/'reports/v4_12_runtime_r11/R11_SAME_DAY_QUALITY_CORRECTION.json').write_bytes(canon(r));return r
if __name__=='__main__':print(json.dumps(dict(status=(validate() if '--validate-only' in sys.argv else run())['status'])))

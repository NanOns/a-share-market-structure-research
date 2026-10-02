"""R15R1 read-only lineage cleanup gate, keeping accepted business semantics."""
import json,subprocess
from copy import deepcopy
from scripts.repair_v4_13_r1_1 import ROOT,read,ref
from scripts.validate_v4_13_r1_1 import validate,load_bundle,validate_lineage
BASE='c7b2cb92c5fb12127a941d5af102742fe0d5e965'
PROTECTED=['AGENTS.md','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
def normalized(obj):
    obj=deepcopy(obj)
    for key in ['introduced_in','derived_from','definition_replaces','supersedes']:obj.pop(key,None)
    def strip(x):
        if isinstance(x,dict):
            if 'path' in x and 'sha256' in x:
                x.pop('sha256');x.pop('bytes',None);x.pop('byte_count',None)
            for v in x.values():strip(v)
        elif isinstance(x,list):
            for v in x:strip(v)
    strip(obj);return obj

def gate(clean=False):
    before=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    if clean:assert before==b''
    result=validate(checkout=clean);matrix=[]
    for p in sorted((ROOT/'config').glob('v4_13_*_v1_1.json')):
        path=p.relative_to(ROOT).as_posix();current=read(path);old=json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT))
        assert normalized(current)==normalized(old), 'BUSINESS_SEMANTICS_CHANGED:'+path
        validate_lineage(current)
        if 'supersedes' in current:assert current['supersedes']==old['supersedes']
        matrix.append(dict(path=path,contract_id=current['contract_id'],business_semantics='EXACT_KEEP',lineage='PASS'))
    protected=[]
    for path in PROTECTED:
        baseline=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT);assert (ROOT/path).read_bytes()==baseline
        protected.append(dict(**ref(path),before_sha256=ref(path)['sha256'],after_sha256=ref(path)['sha256'],exact_unchanged=True))
    changed=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT,text=True).splitlines()
    assert not any(p.startswith(('src/','data/','migrations/')) for p in changed)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)==before
    return dict(R15R1_VERSION_LINEAGE_CLEANUP='PASS',V4_13_CONTRACT_COMPLETENESS=result['V4_13_CONTRACT_COMPLETENESS'],V4_13_RUNTIME='NOT_IMPLEMENTED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',baseline=BASE,source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),C01_C04='PASS_KEEP',contracts=matrix,protected=protected,independent_vectors=len(result['vectors']),negative_business_gates=len(result['negative_gates']),clean_before=clean,clean_after=clean,read_only=True,production=False,shadow=False,focus=False,global_mandatory_adoption=False,stage='V4_00_TO_V4_12_ACCEPTED',data='2026-09-30',runtime_added=False,migration_added=False,external_acceptance='PENDING')
if __name__=='__main__':
    import sys
    print(json.dumps(gate('--clean' in sys.argv),ensure_ascii=False,sort_keys=True))

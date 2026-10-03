"""Recover explicitly requested historical bytes; never select archives at read time."""
from pathlib import Path
import hashlib,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='f12315bf8e3142aa44e9068c5895004c35c4e23c'
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
DOC='docs/evidence/r17/'
NAMES=['V4_R16R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','V4_R17A_CROSS_STAGE_ACCEPTED_CHAIN_HISTORICAL_VALIDATOR_REPAIR_TASK_20261003.md','V4_R17B_V4_13_ACCEPTED_HEAD_PROMOTION_TASK_20261003.md','V4_R17C_V4_14_REPLAY_GATE_B_CONTRACT_FREEZE_ENTRY_TASK_20261003.md','V4_NEXT_ROUND_EXECUTION_MASTER_R17_20261003.md']
def atomic(path,raw):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.r17.tmp');tmp.write_bytes(raw);os.replace(tmp,p)
def put(path,value):atomic(path,(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
def bind(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def prepare():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    for n in NAMES:atomic(DOC+n,(Path('D:/Users/lps/Desktop/阶段任务')/n).read_bytes())
    for p in [DOC,'reports/r17a/','reports/r17b/','reports/r17c/','data/v4/stage_head_archive/r17/']:atomic(p+'.gitattributes',b'* -text\n')
    wanted=['529c532bd5553ace00fa4813aef07979cfce4e1f18fa5ea66f38fcddd8ed16cb','80c58f2f4ed35baa1fd2b27e6af8b400fadfbefe4ed5d85819d9349c3315e2ac','f7607601de402f2b2bdada84dffdefbacad7f9f66e252c57dfdf045060e90e99','6620089e9a1ca550e89c2c0bb177887528c8e7d160a44c584664f04b91a1c48e']
    raw=subprocess.check_output(['git','show',BASE+':'+STAGE],cwd=ROOT);h=hashlib.sha256(raw).hexdigest()
    p='data/v4/stage_head_archive/r17/'+h+'.json';atomic(p,raw)
    entries=[dict(original_namespace=dict(path=STAGE,sha256=h,bytes=len(raw)),archive=bind(p),accepted_stage_range=json.loads(raw)['accepted_stage_range'],source_commit=BASE,scope='EXACT_HISTORICAL_PROMOTION_STATE_ONLY')]
    for commit in subprocess.check_output(['git','log','--format=%H',BASE,'--',STAGE],cwd=ROOT,text=True).splitlines():
        raw=subprocess.check_output(['git','show',commit+':'+STAGE],cwd=ROOT);h=hashlib.sha256(raw).hexdigest()
        if h not in wanted:continue
        p='data/v4/stage_head_archive/r17/'+h+'.json';atomic(p,raw)
        entries.append(dict(original_namespace=dict(path=STAGE,sha256=h,bytes=len(raw)),archive=bind(p),accepted_stage_range=json.loads(raw)['accepted_stage_range'],source_commit=commit,scope='EXACT_HISTORICAL_PROMOTION_STATE_ONLY'))
        wanted.remove(h)
    assert not wanted,wanted
    sources=[]
    for p in ['src/workbench_analysis/dm01_accepted_chain_v1.py','tests/v4_09/test_stock_prewatch.py']:
        raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT);a='reports/r17a/source_archive/'+p;atomic(a,raw)
        sources.append(dict(original_namespace=dict(path=p,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),archive=bind(a),source_commit=BASE,scope='HISTORICAL_PRODUCER_AUTHORITY_ONLY'))
    fresh=json.loads((ROOT/'reports/v4_12_runtime_r1/V4_12_FRESH_RUNTIME_RERUN_DIGEST_EQUALITY.json').read_bytes())
    for ref in fresh['runtime_sources']:
        if hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256']:continue
        for commit in subprocess.check_output(['git','log','--format=%H',BASE,'--',ref['path']],cwd=ROOT,text=True).splitlines():
            raw=subprocess.check_output(['git','show',commit+':'+ref['path']],cwd=ROOT)
            if hashlib.sha256(raw).hexdigest()!=ref['sha256']:continue
            a='reports/r17a/source_archive/r10/'+ref['path'];atomic(a,raw)
            sources.append(dict(original_namespace=ref,archive=bind(a),source_commit=commit,scope='HISTORICAL_PRODUCER_AUTHORITY_ONLY'));break
        else:raise ValueError('EXACT_HISTORICAL_RUNTIME_SOURCE_NOT_FOUND')
    p='src/workbench_analysis/dm01_publication_history_reader_v1.py'
    raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT);a='reports/r17a/source_archive/'+p;atomic(a,raw)
    sources.append(dict(original_namespace=dict(path=p,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),archive=bind(a),source_commit=BASE,scope='HISTORICAL_PRODUCER_AUTHORITY_ONLY'))
    p='data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json';raw=(ROOT/p).read_bytes();git_raw=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
    assert raw.replace(b'\r\n',b'\n')==git_raw
    a='reports/r17a/source_archive/static/'+p;atomic(a,raw)
    static=[dict(original_namespace=bind(p),archive=bind(a),source_commit=BASE,git_blob_sha256=hashlib.sha256(git_raw).hexdigest(),git_blob_bytes=len(git_raw),representation='EXACT_ARCHIVED_ACCEPTED_BYTES_WITH_PROVEN_GIT_LF_REPRESENTATION',authority='V4_STAGE_ACCEPTED_HEAD.v4_02_go_forward_pit_binding')]
    registry=dict(contract_id='V4_HISTORICAL_MOVING_HEAD_REGISTRY_R17_V1',version='1.0.0',baseline=BASE,resolution='EXPLICIT_PATH_SHA_BYTES_RANGE_GIT_ONLY',entries=entries,source_archives=sources,static_byte_archives=static)
    put('config/v4_historical_moving_head_registry_r17_v1.json',registry)
    put('reports/r17a/stage_contract.json',dict(contract_id='R17A_CROSS_STAGE_GOVERNANCE_REPAIR_V1',baseline=BASE,master=bind(DOC+NAMES[-1]),task=bind(DOC+NAMES[1]),external_audit=bind(DOC+NAMES[0]),scope='HISTORICAL_VALIDATORS_ONLY_NO_ACCEPTED_ALGORITHM_CHANGE',protected={p:bind(p) for p in ['AGENTS.md',STAGE,'data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json']},next='R17B_AFTER_PASS_AND_CLEAN_DETACHED_VALIDATION'))
    print(bind('config/v4_historical_moving_head_registry_r17_v1.json'))
if __name__=='__main__':prepare()

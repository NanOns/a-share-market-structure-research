"""Real child processes with isolated roots and injected source/admission only."""
from pathlib import Path
import json,os,subprocess,sys
import pytest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.tdx_official_daily_source import sha256_file

WORKER=r'''
from pathlib import Path
import json,os,sys,time
from workbench_analysis import operational_successor_release_v1 as release
from workbench_analysis.operational_successor_v1 import digest
root=Path(sys.argv[1]);candidate=json.loads((root/'candidate.json').read_bytes())
release.validate=lambda *a:True;release.verify_policy=lambda *a:True
try:
 result=release.promote(root,candidate,candidate['predecessor']['sha256'],lambda c:(time.sleep(.3) or dict(status='PASS',context_token=digest(c),accepted_trade_date=c['accepted_trade_date'])))
except (OSError,ValueError) as e:result=dict(status='CONFLICT',error=str(e))
print(json.dumps(dict(result,pid=os.getpid(),isolated_root=str(root))))
'''

def test_two_real_process_publishers_exactly_one_commit(tmp_path):
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    atomic_json(tmp_path,head,dict(accepted_trade_date='2026-10-08',evidence_kind='ISOLATED_INJECTION'))
    old=sha256_file(head);predecessor=head.parent/'predecessors'/(old+'.json')
    atomic_json(tmp_path,predecessor,json.loads(head.read_bytes()))
    candidate=dict(accepted_trade_date='2026-10-09',predecessor=dict(path=str(predecessor),sha256=old),evidence_kind='ISOLATED_INJECTION')
    atomic_json(tmp_path,tmp_path/'candidate.json',candidate)
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    processes=[subprocess.Popen([sys.executable,'-c',WORKER,str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env) for _ in range(2)]
    results=[]
    try:
        for p in processes:
            out,err=p.communicate(timeout=30);assert p.returncode==0,err
            results.append(json.loads(out))
    finally:
        for p in processes:
            if p.poll() is None:p.kill();p.wait()
    assert sorted(r['status'] for r in results)==['CONFLICT','PUBLISHED']
    assert json.loads(head.read_bytes())==candidate
    receipt=json.loads((tmp_path/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
    assert receipt['state']=='COMMITTED' and receipt['predecessor']['sha256']==old
    print(json.dumps(dict(evidence_kind='ISOLATED_INJECTION',results=results,transaction=receipt)))


def test_prepared_crash_and_repeated_rollback_restart(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_release_v1 as release
    from workbench_analysis.operational_successor_v1 import digest
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    atomic_json(tmp_path,head,dict(accepted_trade_date='2026-10-08',fixture=True));before=head.read_bytes()
    p=head.parent/'predecessors'/(sha256_file(head)+'.json');atomic_json(tmp_path,p,json.loads(before))
    candidate=dict(accepted_trade_date='2026-10-09',fixture=True)
    transaction=tmp_path/'runtime/dynamic_daily/publication_transaction.json'
    atomic_json(tmp_path,transaction,dict(state='PREPARED',predecessor=dict(path=str(p),sha256=sha256_file(p)),candidate_token=digest(candidate)))
    release.recover(tmp_path);release.recover(tmp_path)
    assert head.read_bytes()==before
    assert json.loads(transaction.read_bytes())['state']=='RECOVERED_PRE_CAS'

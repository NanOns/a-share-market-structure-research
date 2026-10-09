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


def test_disk_write_failure_before_cas_preserves_last_good(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_release_v1 as release
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    atomic_json(tmp_path,head,dict(accepted_trade_date='2026-10-08'));before=head.read_bytes();old=sha256_file(head)
    pre=head.parent/'predecessors'/(old+'.json');atomic_json(tmp_path,pre,json.loads(before))
    candidate=dict(accepted_trade_date='2026-10-09',predecessor=dict(path=str(pre),sha256=old))
    monkeypatch.setattr(release,'validate',lambda *a:True);monkeypatch.setattr(release,'verify_policy',lambda *a:True)
    original=release.atomic_json
    def no_space(root,path,payload):
        if Path(path)==head:raise OSError('ISOLATED_ENOSPC')
        return original(root,path,payload)
    monkeypatch.setattr(release,'atomic_json',no_space)
    with pytest.raises(OSError,match='ISOLATED_ENOSPC'):release.promote(tmp_path,candidate,old,lambda _:None)
    assert head.read_bytes()==before
    release.recover(tmp_path);assert head.read_bytes()==before


def test_rollback_write_failure_recovers_in_fresh_process(tmp_path,monkeypatch):
    """Failure during rollback must leave a recoverable journal, not COMMITTED."""
    from workbench_analysis import operational_successor_release_v1 as release
    head=tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    atomic_json(tmp_path,head,dict(accepted_trade_date='2026-10-08'))
    before=head.read_bytes();old=sha256_file(head)
    pre=head.parent/'predecessors'/(old+'.json');atomic_json(tmp_path,pre,json.loads(before))
    candidate=dict(accepted_trade_date='2026-10-09',predecessor=dict(path=str(pre),sha256=old))
    monkeypatch.setattr(release,'validate',lambda *a:True)
    monkeypatch.setattr(release,'verify_policy',lambda *a:True)
    original=release._atomic_write
    def failed_rollback(path,*args,**kwargs):
        if Path(path)==head:raise OSError('ISOLATED_ROLLBACK_WRITE_FAILURE')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(release,'_atomic_write',failed_rollback)
    with pytest.raises(OSError,match='ISOLATED_ROLLBACK_WRITE_FAILURE'):
        release.promote(tmp_path,candidate,old,lambda _:dict(status='FAIL'))
    transaction=tmp_path/'runtime/dynamic_daily/publication_transaction.json'
    assert json.loads(transaction.read_bytes())['state']=='CAS_COMPLETE_READBACK_PENDING'
    assert json.loads(head.read_bytes())==candidate
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result=subprocess.run([sys.executable,'-c',
        'from pathlib import Path;import sys;from workbench_analysis.operational_successor_release_v1 import recover;recover(Path(sys.argv[1]));recover(Path(sys.argv[1]))',
        str(tmp_path)],capture_output=True,text=True,env=env,timeout=30)
    assert result.returncode==0,result.stderr
    assert head.read_bytes()==before
    assert json.loads(transaction.read_bytes())['state']=='RECOVERED_EXACT_PREDECESSOR'
    print(json.dumps(dict(case='ROLLBACK_WRITE_FAILURE_FRESH_PROCESS_RECOVERY',evidence_kind='ISOLATED_INJECTION',exit_code=result.returncode,predecessor_sha256=old)))


def test_process_crash_releases_kernel_lock(tmp_path):
    """A stale lock file cannot retain ownership after its owning process dies."""
    from workbench_analysis.operational_daily_storage_v1 import exclusive_lock
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    worker='from pathlib import Path;import sys,time;from workbench_analysis.operational_daily_storage_v1 import exclusive_lock\nroot=Path(sys.argv[1])\nwith exclusive_lock(root,root/"worker.lock"):\n print("LOCKED",flush=True)\n time.sleep(60)'
    process=subprocess.Popen([sys.executable,'-c',worker,str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        assert process.stdout.readline().strip()=='LOCKED'
        with pytest.raises(OSError):
            with exclusive_lock(tmp_path,tmp_path/'worker.lock'):pass
    finally:
        process.kill();process.wait(timeout=10)
    with exclusive_lock(tmp_path,tmp_path/'worker.lock'):
        assert (tmp_path/'worker.lock').is_file()
    print(json.dumps(dict(case='KERNEL_LOCK_OWNER_CRASH_RECOVERY',evidence_kind='ISOLATED_INJECTION',crashed_pid=process.pid)))

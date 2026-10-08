import json
import pytest
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.joint_release import activate,recover,AUTHORITY

def candidate(root,version):
    def binding(name,data):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);raw=canonical(data);path.write_bytes(raw)
        return dict(path=name,sha256=digest(raw))
    db=binding(f'data/{version}/db',{'real_test':version})
    manifest=binding(f'data/{version}/manifest',dict(context={'accepted_trade_date':'2026-09-30'},database=db,sources={}))
    ui=binding(f'data/{version}/index.html',{'ui':version})
    return dict(contract_id='V4_JOINT_RELEASE_V1',snapshot={'manifest':manifest},ui_assets={'index.html':ui},trade_date='2026-09-30',operational_release_scope=['test'],trading=False)

def test_joint_health_failure_exact_restore_and_noop(tmp_path):
    a=candidate(tmp_path,'a');b=candidate(tmp_path,'b');health=lambda c:{'pass':True}
    receipt=activate(tmp_path,a,None,health);p=tmp_path/AUTHORITY;old=p.read_bytes()
    assert receipt['activation_performed']
    with pytest.raises(SourceInvalid,match='HEALTH'):activate(tmp_path,b,digest(old),lambda c:{'pass':False})
    assert p.read_bytes()==old
    assert activate(tmp_path,a,digest(old),health)['result']=='NOOP'
    with pytest.raises(SourceInvalid,match='CAS'):activate(tmp_path,b,'stale',health)
    assert p.read_bytes()==old

def test_concurrent_release_lock_and_digest_mismatch(tmp_path):
    a=candidate(tmp_path,'a');p=tmp_path/AUTHORITY;p.parent.mkdir(parents=True)
    lock=p.with_suffix('.lock');lock.write_text('held')
    with pytest.raises(SourceInvalid,match='BUSY'):activate(tmp_path,a,None,lambda c:{'pass':True})
    lock.unlink();a['ui_assets']['index.html']['sha256']='bad'
    with pytest.raises(SourceInvalid,match='DIGEST'):activate(tmp_path,a,None,lambda c:{'pass':True})
    assert not p.exists()

def test_power_interruption_recovers_previous_pair(tmp_path):
    a=candidate(tmp_path,'a');b=candidate(tmp_path,'b');p=tmp_path/AUTHORITY;p.parent.mkdir(parents=True)
    old=canonical(a);p.write_bytes(canonical(b));folder=tmp_path/'runtime/joint_release/interrupted';folder.mkdir(parents=True)
    (folder/'TRANSACTION.json').write_bytes(canonical(dict(state='PREPARED',candidate_digest=digest(p.read_bytes()))))
    (folder/'PREDECESSOR.json').write_bytes(canonical(dict(existed=True,raw=old.decode())))
    recover(tmp_path);assert p.read_bytes()==old

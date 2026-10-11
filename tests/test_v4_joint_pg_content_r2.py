from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.joint_release import activate,recover,validate,AUTHORITY
from workbench_db.v4_native import connection
from tests.test_v4_snapshot_identity_r2 import build


def candidate(root,version):
    descriptor=build(root/version)
    def binding(name,data):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);raw=canonical(data);path.write_bytes(raw)
        return dict(path=name,sha256=digest(raw))
    db=binding(f'data/{version}/snapshot.pg.json',descriptor)
    manifest=binding(f'data/{version}/manifest.json',dict(context={'accepted_trade_date':'2026-10-09'},database=db,sources={}))
    ui=binding(f'data/{version}/index.html',{'engineering':version})
    return dict(contract_id='V4_JOINT_RELEASE_V2_PG_CONTENT',snapshot={'manifest':manifest},ui_assets={'index.html':ui},trade_date='2026-10-09',operational_release_scope=['ISOLATED_TEST_ONLY'],trading=False),descriptor


def test_pg_joint_cas_health_failure_and_old_version_integrity(tmp_path):
    first,old=candidate(tmp_path,'first');second,new=candidate(tmp_path,'second')
    activate(tmp_path,first,None,lambda c:{'pass':True});path=tmp_path/AUTHORITY;before=path.read_bytes()
    with pytest.raises(SourceInvalid,match='HEALTH'):
        activate(tmp_path,second,digest(before),lambda c:{'pass':False})
    assert path.read_bytes()==before
    validate(tmp_path,first);validate(tmp_path,second)
    assert activate(tmp_path,first,digest(before),lambda c:pytest.fail('no-op health'))['result']=='NOOP'
    with pytest.raises(SourceInvalid,match='CAS'):
        activate(tmp_path,second,'stale',lambda c:pytest.fail('bad cas health'))


def test_joint_rejects_content_corruption_before_pointer_write(tmp_path):
    first,_=candidate(tmp_path,'first');second,new=candidate(tmp_path,'second')
    activate(tmp_path,first,None,lambda c:{'pass':True});path=tmp_path/AUTHORITY;before=path.read_bytes()
    with connection(new['schema']) as pg:
        pg.execute('ALTER TABLE objects DISABLE TRIGGER immutable_snapshot');pg.execute("UPDATE objects SET name='tampered'")
    with pytest.raises(ValueError,match='CONTENT_IDENTITY_MISMATCH'):
        activate(tmp_path,second,digest(before),lambda c:pytest.fail('corrupt candidate health'))
    assert path.read_bytes()==before;validate(tmp_path,first)


def test_joint_revalidates_content_after_health_before_commit(tmp_path):
    first,_=candidate(tmp_path,'first');second,new=candidate(tmp_path,'second')
    activate(tmp_path,first,None,lambda c:{'pass':True});path=tmp_path/AUTHORITY;before=path.read_bytes()
    def health(c):
        with connection(new['schema']) as pg:
            pg.execute('ALTER TABLE metadata DISABLE TRIGGER immutable_snapshot');pg.execute("UPDATE metadata SET value='tampered'")
        return {'pass':True}
    with pytest.raises(ValueError,match='CONTENT_IDENTITY_MISMATCH'):
        activate(tmp_path,second,digest(before),health)
    assert path.read_bytes()==before;validate(tmp_path,first)


def test_pg_joint_concurrent_cas_one_writer(tmp_path):
    first,_=candidate(tmp_path,'first');a,_=candidate(tmp_path,'a');b,_=candidate(tmp_path,'b')
    activate(tmp_path,first,None,lambda c:{'pass':True});path=tmp_path/AUTHORITY;expected=digest(path.read_bytes())
    def attempt(c):
        try:return activate(tmp_path,c,expected,lambda x:{'pass':True})['activation_performed']
        except SourceInvalid as exc:
            assert str(exc) in ('JOINT_RELEASE_BUSY','JOINT_CAS_CONFLICT');return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[a,b]))
    assert results.count(True)==1
    validate(tmp_path,json.loads(path.read_bytes()))


def test_pg_joint_interrupted_prepared_recovery(tmp_path):
    first,_=candidate(tmp_path,'first');second,_=candidate(tmp_path,'second')
    activate(tmp_path,first,None,lambda c:{'pass':True});path=tmp_path/AUTHORITY;before=path.read_bytes()
    folder=tmp_path/'runtime/joint_release/interrupted';folder.mkdir(parents=True)
    raw=canonical(second);path.write_bytes(raw)
    (folder/'PREDECESSOR.json').write_bytes(canonical(dict(existed=True,raw=before.decode())))
    (folder/'TRANSACTION.json').write_bytes(canonical(dict(state='PREPARED',candidate_digest=digest(raw))))
    recover(tmp_path)
    assert path.read_bytes()==before;validate(tmp_path,first)

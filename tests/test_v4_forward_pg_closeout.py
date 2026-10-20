"""Real PG storage invariants; legacy bytes remain read-only evidence."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import pytest
from workbench_db.v4_forward_pg_r1 import ForwardFactStore
from workbench_db.v4_native import connection

def test_legacy_migration_exact_bytes_and_native_restart(tmp_path):
    original=tmp_path/'forward/t0_freezes/a.json'
    original.parent.mkdir(parents=True)
    raw=b'{"T0": "2026-09-29", "members": ["a"]}\n'
    original.write_bytes(raw)
    store=ForwardFactStore(tmp_path,'forward')
    refs=store.refs('t0_freezes')
    assert len(refs)==1 and store.read(refs[0])==json.loads(raw)
    assert original.read_bytes()==raw
    with connection(store.schema,dsn=store.dsn,read_only=True) as pg:
        payload,digest=pg.execute('SELECT payload,source_sha256 FROM forward_facts').fetchone()
        assert payload.encode()==raw and digest==hashlib.sha256(raw).hexdigest()
    restarted=ForwardFactStore(tmp_path,'forward')
    assert restarted.read(refs[0])==json.loads(raw)

def test_concurrent_identity_conflict_one_winner(tmp_path):
    store=ForwardFactStore(tmp_path,'forward')
    def append(value):
        try:return ('APPENDED',store.append('outcomes','e',{'value':value}))
        except ValueError as exc:return ('REJECTED',str(exc))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(append,[1,2]))
    assert sorted(r[0] for r in results)==['APPENDED','REJECTED']
    assert len(store.refs('outcomes'))==1
    assert store.read(store.refs('outcomes')[0])['value'] in (1,2)

def test_immutability_transaction_rollback(tmp_path):
    import psycopg
    store=ForwardFactStore(tmp_path,'forward')
    ref=store.append('outcomes','e',{'value':1})
    with pytest.raises(psycopg.Error,match='FORWARD_FACTS_APPEND_ONLY'):
        with connection(store.schema,dsn=store.dsn) as pg:
            pg.execute("UPDATE forward_facts SET payload='{}'")
    assert store.read(ref)=={'value':1}

def test_descriptor_identity_rejects_wrong_database(tmp_path):
    store=ForwardFactStore(tmp_path,'forward')
    ref=store.append('outcomes','e',{'value':1})
    path=tmp_path/ref['path'];document=json.loads(path.read_bytes())
    document['database_identity']['database_oid']+=1
    raw=json.dumps(document).encode();path.write_bytes(raw)
    forged=dict(ref,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):store.read(forged)

def test_candidate_schema_binding_does_not_overwrite_predecessor_descriptor(tmp_path):
    store=object.__new__(ForwardFactStore)
    store.root=Path(tmp_path).resolve()
    store.folder=store.root/'forward'
    store.schema='v4_forward_candidate'
    store.database_identity={'database':'test_db','database_oid':1,'host':'127.0.0.1','port':5432}
    key='same-fact-key'
    legacy=store.folder/'outcomes'/(hashlib.sha256(key.encode()).hexdigest()+'.pg.json')
    legacy.parent.mkdir(parents=True,exist_ok=True)
    prior=json.dumps({'contract_id':'V4_FORWARD_PG_FACT_STORE_R1','schema':'v4_forward_predecessor'},separators=(',',':')).encode()
    legacy.write_bytes(prior)

    binding=store._binding('outcomes',key,'a'*64)

    assert binding['path']!=legacy.relative_to(store.root).as_posix()
    assert legacy.read_bytes()==prior
    descriptor=json.loads((store.root/binding['path']).read_bytes())
    assert descriptor['schema']==store.schema
    assert descriptor['fact_key']==key

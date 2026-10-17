"""Real PG storage invariants; legacy bytes remain read-only evidence."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import pytest
import workbench_db.v4_forward_pg_r1 as forward_pg
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


def test_forward_pg_owner_read_uses_reader_dsn(monkeypatch, tmp_path):
    identity = dict(database='market_research', database_oid=16384, host='127.0.0.1', port=5432)
    payload = {'value': 1}
    payload_raw = forward_pg.canonical(payload)
    payload_sha = hashlib.sha256(payload_raw).hexdigest()
    fact_key = 'owner-1'
    descriptor = dict(contract_id=forward_pg.CONTRACT, engine='postgresql', database_identity=identity,
                      schema='v4_forward_test', kind='outcomes', fact_key=fact_key, payload_sha256=payload_sha)
    descriptor_raw = forward_pg.canonical(descriptor)
    descriptor_path = tmp_path/'forward/outcomes'/(hashlib.sha256(fact_key.encode()).hexdigest()+'.pg.json')
    descriptor_path.parent.mkdir(parents=True)
    descriptor_path.write_bytes(descriptor_raw)
    binding = dict(path=descriptor_path.relative_to(tmp_path).as_posix(),
                   sha256=hashlib.sha256(descriptor_raw).hexdigest(), bytes=len(descriptor_raw))

    class FakePg:
        def execute(self, query, params=()):
            if 'SELECT current_database()' in query:
                return Result((identity['database'], identity['database_oid'], identity['host'], identity['port']))
            if 'SELECT payload,payload_sha256 FROM forward_facts' in query:
                return Result((payload_raw.decode(), payload_sha))
            raise AssertionError('unexpected SQL')

    class Result:
        def __init__(self, row): self.row = row
        def fetchone(self): return self.row

    @contextmanager
    def reader_connection(schema, *, dsn, read_only):
        assert schema == 'v4_forward_test'
        assert dsn == 'configured-reader'
        assert read_only is True
        yield FakePg()

    monkeypatch.setattr(forward_pg, 'connection', reader_connection)
    monkeypatch.setattr(forward_pg, 'configured_reader_dsn', lambda: 'configured-reader')
    store = object.__new__(ForwardFactStore)
    store.root = tmp_path.resolve()
    store.folder = (tmp_path/'forward').resolve()
    store.schema = 'v4_forward_test'
    store.database_identity = identity
    store.dsn = 'writer-must-not-be-used-for-read'

    assert store.read(binding) == payload


def test_forward_pg_owner_read_has_no_writer_dsn_fallback(monkeypatch, tmp_path):
    store = object.__new__(ForwardFactStore)
    store.root = tmp_path.resolve()
    store.folder = (tmp_path/'forward').resolve()
    store.schema = 'v4_forward_test'
    store.database_identity = {}
    store.dsn = 'writer-only'
    monkeypatch.setattr(forward_pg, 'configured_reader_dsn',
                        lambda: (_ for _ in ()).throw(RuntimeError('V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK')))
    monkeypatch.setattr(forward_pg, 'connection', lambda *a, **k: pytest.fail('connection must not open'))

    with pytest.raises(RuntimeError, match='V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK'):
        store.refs('outcomes')

"""Real PG request consistency and tamper detection with full content checks."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_fp02_research_snapshot import reader
from workbench_service.production_v4 import snapshot_request_scope
from workbench_service.research_bff import ResearchBFF
from workbench_db import v4_snapshot_pg_r2 as native
from workbench_db.v4_native import connection
from psycopg import sql

def spy(monkeypatch):
    calls=[];original=native.verify
    def verify(pg,descriptor):
        calls.append(descriptor['logical_digest'])
        return original(pg,descriptor)
    monkeypatch.setattr(native,'verify',verify)
    return calls

def test_one_full_verified_snapshot_for_list_validation_and_rows(reader,monkeypatch):
    calls=spy(monkeypatch);bff=ResearchBFF(reader.root)
    monkeypatch.setattr(bff,'current',lambda:reader)
    code,payload=bff.get('/api/v4/stocks',{'limit':'3'})
    assert code==200 and payload['total']==7
    assert [r['entity_id'] for r in payload['items']]==['SEC0','SEC1','SEC2']
    assert len(calls)==1
    code,second=bff.get('/api/v4/stocks',{'offset':'3','limit':'3'})
    assert code==200 and [r['entity_id'] for r in second['items']]==['SEC3','SEC4','SEC5']
    assert len(calls)==2

def test_tamper_between_requests_is_not_hidden_by_verification_cache(reader,monkeypatch):
    bff=ResearchBFF(reader.root);monkeypatch.setattr(bff,'current',lambda:reader)
    assert bff.get('/api/v4/stocks',{})[0]==200
    with connection(reader.pg_descriptor['schema']) as pg:
        pg.execute('ALTER TABLE objects DISABLE TRIGGER immutable_snapshot')
        pg.execute("UPDATE objects SET payload='{}' WHERE domain='stocks' AND id='SEC0'")
        pg.execute('ALTER TABLE objects ENABLE TRIGGER immutable_snapshot')
    code,payload=bff.get('/api/v4/stocks',{})
    assert code==400 and payload['code']=='PG_SNAPSHOT_CONTENT_IDENTITY_MISMATCH'

def test_threads_verify_independent_repeatable_read_snapshots(reader,monkeypatch):
    calls=spy(monkeypatch)
    def query(offset):
        with snapshot_request_scope():
            reader.query('sources',{})
            return reader.query('stocks',{'offset':str(offset),'limit':'1'})['items'][0]['entity_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(query,(0,6)))==['SEC0','SEC6']
    assert len(calls)==2
